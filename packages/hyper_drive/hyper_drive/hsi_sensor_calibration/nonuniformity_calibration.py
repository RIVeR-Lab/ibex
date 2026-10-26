#!/usr/bin/env python3
"""
nonuniformity_calibration.py

Capture dark and nonuniformity (white) references for one hyperspectral camera
and write them into that camera's HSI Mosaic context.

    python3 nonuniformity_calibration.py --camera ximea
    python3 nonuniformity_calibration.py --camera imec
    python3 nonuniformity_calibration.py --camera ximea --frames 50
    python3 nonuniformity_calibration.py --camera imec --context /path/to/context

Each reference is the per-pixel mean of --frames captures (default 30).

The context is loaded from, and written back to, config/<camera>/context in the
package source tree (override with --context). The existing context is backed up
to ~/hsi_context_backups/ first. Rebuild afterwards so the new context is
installed:  cd ~/ibex_ws && colcon build --packages-select hyper_drive

Camera settings must match how synchronous_cubes runs the camera. The dark
reference is stored for the camera's actual integration time, so if you change
a camera's exposure later you must recalibrate.
"""

import os
import sys

# LD_LIBRARY_PATH must be set before the process starts. If it isn't already,
# re-launch this script once with the correct environment.
_lib_paths = [
    '/opt/imec/hsi-mosaic/bin',
    '/opt/imec/hsi-mosaic/resources/installers/package/api/X64',
    '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib',
    '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam/bin/Linux64_x64',
    '/opt/XIMEA/CamTool',
    '/opt/PFSDK_2025.1.0_Linux64/lib',
]

if not os.environ.get('_IMEC_ENV_SET'):
    current = os.environ.get('LD_LIBRARY_PATH', '')
    os.environ['LD_LIBRARY_PATH'] = ':'.join(filter(None, _lib_paths + [current]))
    os.environ['GENICAM_ROOT_V3_1'] = '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam'
    os.environ['GENICAM_ROOT_V3_4'] = '/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam'
    os.environ['_IMEC_ENV_SET'] = '1'
    os.execv(sys.executable, [sys.executable] + sys.argv)

import argparse
import shutil
import tempfile
import time

import numpy as np
sys.path.append('/opt/imec/hsi-mosaic/python_apis')

import hsi_common as HSI_COMMON
import hsi_camera as HSI_CAMERA
import hsi_mosaic as HSI_MOSAIC


# ---------------------------------------------------------------------------
# Per-camera settings. These must match synchronous_cubes.
# ---------------------------------------------------------------------------
CAMERAS = {
    'imec': {
        'manufacturer': HSI_CAMERA.Manufacturer.EM_IMEC,
        'roi': dict(x=1, y=1, width=639, height=510),
        'integration_ms': 60.0,
        'frame_rate_hz': 15.0,
        'flip_horizontal': True,
        'flip_vertical': False,
        'saturation': 7100,   # values above this are unreliable on this sensor
    },
    'ximea': {
        'manufacturer': HSI_CAMERA.Manufacturer.EM_XIMEA,
        'roi': dict(x=0, y=0, width=2045, height=1085),
        'integration_ms': 10.0,
        'frame_rate_hz': 15.0,
        'flip_horizontal': False,
        'flip_vertical': False,
        'saturation': 1023,   # 10-bit full scale
    },
}

BACKUP_ROOT = os.path.expanduser('~/hsi_context_backups')


def default_context_path(camera):
    """config/<camera>/context in the source tree, relative to this script.

    This script lives in hyper_drive/hyper_drive/hsi_sensor_calibration/, so the
    package's config/ directory is two levels up.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, '..', '..', 'config', camera, 'context'))


def capture_averaged_frame(device, num_frames, label):
    """Capture num_frames frames and return a frame holding their per-pixel mean.

    The mean is written into the last frame actually acquired, not into a freshly
    allocated one, so the frame keeps the metadata AcquireFrame filled in (such as
    the integration time). A fresh AllocateFrame has no such metadata, which is a
    likely reason an earlier averaging attempt failed.
    """
    fmt = HSI_CAMERA.GetOutputFrameDataFormat(device)
    frame = HSI_COMMON.AllocateFrame(fmt)
    acc = None

    for i in range(num_frames):
        _, frame = HSI_CAMERA.AcquireFrame(device, frame=frame)
        arr = HSI_COMMON.FrameAsArray(frame)
        if acc is None:
            acc = np.zeros(arr.shape, dtype=np.float64)
        acc += arr  # adds a copy of the current data; the buffer is reused next loop
        print(f'  {label}: captured frame {i + 1}/{num_frames}', end='\r')
    print()

    mean = acc / num_frames

    # Overwrite the last acquired frame's pixel data with the mean.
    arr = HSI_COMMON.FrameAsArray(frame)
    arr[...] = mean.astype(arr.dtype)

    # Make sure the write actually reached the SDK's frame buffer.
    check = HSI_COMMON.FrameAsArray(frame)
    if not np.allclose(check, mean.astype(arr.dtype)):
        raise RuntimeError(
            f'{label}: writing the averaged data into the frame did not take effect '
            f'(FrameAsArray is not a writable view of the frame). '
            f'Re-run with --frames 1 to fall back to a single capture.')
    return frame, mean


def report(label, mean, saturation):
    print(f'  {label}: min {mean.min():.1f}  max {mean.max():.1f}  mean {mean.mean():.1f}')
    n_sat = int(np.count_nonzero(mean >= saturation))
    if n_sat:
        print(f'  [warn] {label}: {n_sat} pixels at or above saturation ({saturation}). '
              f'Reduce illumination; a saturated white reference corrupts the flat-field.')


def find_saved_context(save_dir):
    """SaveContext(ctx, path) has been seen to write into path/context rather than
    path itself. Return whichever directory actually holds the saved context."""
    nested = os.path.join(save_dir, 'context')
    if os.path.isdir(nested) and os.listdir(nested):
        return nested
    if os.listdir(save_dir):
        return save_dir
    raise RuntimeError(f'SaveContext wrote nothing under {save_dir}')


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--camera', required=True, choices=sorted(CAMERAS))
    ap.add_argument('--frames', type=int, default=30,
                    help='frames averaged per reference (default 30)')
    ap.add_argument('--context', default=None,
                    help='context directory (default: config/<camera>/context in the source tree)')
    ap.add_argument('--integration', type=float, default=None,
                    help='override integration time in ms (must match synchronous_cubes)')
    ap.add_argument('--frame-rate', type=float, default=None,
                    help='override frame rate in Hz')
    args = ap.parse_args()

    if args.frames < 1:
        ap.error('--frames must be at least 1')

    cfg = CAMERAS[args.camera]
    integration_ms = args.integration if args.integration is not None else cfg['integration_ms']
    frame_rate_hz = args.frame_rate if args.frame_rate is not None else cfg['frame_rate_hz']
    context_path = os.path.abspath(os.path.expanduser(args.context or default_context_path(args.camera)))

    # Check the context exists before touching the camera.
    if not os.path.isdir(context_path):
        sys.exit(f'Context not found at {context_path}. Pass --context with the correct path.')
    print(f'Camera:  {args.camera}')
    print(f'Context: {context_path}')
    print(f'Frames per reference: {args.frames}')

    HSI_COMMON.InitializeLogger('/tmp', HSI_COMMON.LoggerVerbosity.LV_INFO)

    dev_list = HSI_CAMERA.EnumerateConnectedDevices(manufacturer=cfg['manufacturer'])
    if not dev_list:
        sys.exit(f'No {args.camera} camera found. Check it is connected and not open '
                 f'in another process (e.g. synchronous_cubes).')

    device = HSI_CAMERA.OpenDevice(dev_list[0])
    context = None
    started = False
    try:
        HSI_CAMERA.SetRegionOfInterestArray(device, [HSI_COMMON.RegionOfInterest(**cfg['roi'])])
        HSI_CAMERA.Initialize(device)

        r_params = HSI_CAMERA.GetRuntimeParameters(device)
        r_params.frame_rate_hz = frame_rate_hz
        r_params.exposure_time_ms = integration_ms
        r_params['flip_horizontal'] = cfg['flip_horizontal']
        r_params['flip_vertical'] = cfg['flip_vertical']
        HSI_CAMERA.SetRuntimeParameters(device, r_params)
        HSI_CAMERA.Start(device)
        started = True

        actual = HSI_CAMERA.GetRuntimeParameters(device)
        actual_integration_ms = actual.exposure_time_ms
        print(f'Integration time: requested {integration_ms} ms, actual {actual_integration_ms} ms')
        print(f'Frame rate:       {actual.frame_rate_hz} Hz')
        print(f'The dark reference will be stored for {actual_integration_ms} ms.')

        context = HSI_MOSAIC.LoadContext(context_path)

        # --- Dark reference ---
        input('\nCover the lens completely, then press Enter...')
        dark_frame, dark_mean = capture_averaged_frame(device, args.frames, 'dark')
        report('dark', dark_mean, cfg['saturation'])
        HSI_MOSAIC.ContextSetDarkFieldReferences(context, [dark_frame])
        if not HSI_MOSAIC.ContextIntegrationTimeInDark(context, actual_integration_ms):
            raise RuntimeError(
                f'The context has no dark reference for {actual_integration_ms} ms after '
                f'setting it. The averaged frame may have lost its integration-time '
                f'metadata. Nothing has been saved. Re-run with --frames 1 to compare.')
        print('  dark reference set')

        # --- White reference / nonuniformity ---
        # Use DC light (halogen or sunlight) if possible. Under fluorescent light
        # the 120 Hz flicker varies between frames; averaging reduces it but does
        # not remove it.
        input('\nPoint the camera at a uniform white target, then press Enter...')
        white_frame, white_mean = capture_averaged_frame(device, args.frames, 'white')
        report('white', white_mean, cfg['saturation'])
        if white_mean.mean() <= dark_mean.mean():
            raise RuntimeError('The white reference is no brighter than the dark reference. '
                               'Was the lens still covered? Nothing has been saved.')
        HSI_MOSAIC.ContextSetNonUniformity(context, dark_frame, white_frame)
        print('  nonuniformity set')

        status = HSI_MOSAIC.ContextGetStatus(context)
        print(f'\nContext status: {status}')

        # --- Save ---
        stamp = time.strftime('%Y%m%d-%H%M%S')
        backup_path = os.path.join(BACKUP_ROOT, f'{args.camera}_context_{stamp}')
        answer = input(f'\nReplace {context_path}\n'
                       f'(the current context will be backed up to {backup_path})? [y/N] ')
        if answer.strip().lower() != 'y':
            print('Not saved.')
            return

        # Save to a scratch directory first, then move the result into place. This
        # works whether SaveContext writes into the given directory or into a
        # 'context' folder inside it.
        with tempfile.TemporaryDirectory() as scratch:
            HSI_MOSAIC.SaveContext(context, scratch)
            saved = find_saved_context(scratch)

            os.makedirs(BACKUP_ROOT, exist_ok=True)
            shutil.copytree(context_path, backup_path)
            shutil.rmtree(context_path)
            shutil.copytree(saved, context_path)

        print(f'Backup:  {backup_path}')
        print(f'Saved:   {context_path}')

        # Re-load the saved context to confirm it is complete.
        check = HSI_MOSAIC.LoadContext(context_path)
        try:
            print(f'Re-loaded context status: {HSI_MOSAIC.ContextGetStatus(check)}')
            ok = HSI_MOSAIC.ContextIntegrationTimeInDark(check, actual_integration_ms)
            print(f'Dark reference for {actual_integration_ms} ms: {bool(ok)}')
        finally:
            HSI_MOSAIC.DeallocateContext(check)

        print('\nRebuild so the new context is installed:')
        print('  cd ~/ibex_ws && colcon build --packages-select hyper_drive && source install/setup.bash')

    finally:
        if context is not None:
            HSI_MOSAIC.DeallocateContext(context)
        if started:
            HSI_CAMERA.Pause(device)
            HSI_CAMERA.Stop(device)
        HSI_CAMERA.CloseDevice(device)


if __name__ == '__main__':
    main()
