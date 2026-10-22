#!/usr/bin/env python3
"""
fnumber_test.py -- does the declared f-number change IMEC SWIR cube VALUES, or only band labels?

Captures N raw frames from the IMEC camera once, then pushes the SAME raw frames through
copies of the active context that differ ONLY in optical_setup.xml <f_number>:
    f2p8/context   active context as-is (f/2.8, dark + non-uniformity references)
    f0/context     identical copy with f_number = 0 (what the Hyper-Drive dataset declared)
    noref/context  (optional, --include-noref) f/2.8 copy with dark_references/ and
                   non_uniformity/ removed, i.e. processed like the dataset in that respect
Each copy is a folder named "context" with no dots in the path, mirroring the layout the
driver uses (a first run failed to load copies named like "ctx_f2.8").

Outputs (in --out): raw frames, cubes per context, band centers per context, summary.txt.

Run on the Ibex ROS 2 machine with the IMEC camera connected and the hyper_drive driver
STOPPED (the camera can only be opened by one process). See fnumber_test_procedure.md.

Offline mode (no camera): --frame-xml PATH loads a saved raw frame (.raw.xml + .raw)
instead of capturing, e.g. the context's own non_uniformity/white_reference.raw.xml.
A uniform white frame tests only one spectrum, so treat offline results as preliminary.

NOTE: written from the HSI Mosaic Python calls used in hyper_drive (synchronous_cubes.py,
light_reference.py); not yet run against hardware.
"""
import os
import sys

# Same library environment as hyper_drive/hsi_sensor_calibration/light_reference.py
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

import re
import shutil
import argparse
import numpy as np

sys.path.append('/opt/imec/hsi-mosaic/python_apis')
import hsi_common as C   # noqa: E402
import hsi_camera as CAM  # noqa: E402
import hsi_mosaic as M   # noqa: E402

ROI = dict(x=1, y=1, width=639, height=510)   # matches synchronous_cubes.py


def make_context_copy(src, dst, f_number=None, strip_refs=False):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    if f_number is not None:
        path = os.path.join(dst, 'optical_setup', 'optical_setup.xml')
        text = open(path).read()
        text, n = re.subn(r'<f_number>[^<]*</f_number>', f'<f_number>{f_number}</f_number>', text)
        assert n == 1, f'expected one <f_number> in {path}, found {n}'
        open(path, 'w').write(text)
    if strip_refs:
        for sub in ('dark_references', 'non_uniformity'):
            shutil.rmtree(os.path.join(dst, sub), ignore_errors=True)
    assert os.path.isdir(os.path.join(dst, 'calibration_file')), \
        f'{dst} has no calibration_file/ -- the source context is incomplete'


def open_camera(exposure_ms, fps):
    devices = CAM.EnumerateConnectedDevices(manufacturer=CAM.Manufacturer.EM_IMEC)
    assert len(devices) > 0, 'No IMEC camera found (is the hyper_drive driver still running?)'
    dev = CAM.OpenDevice(devices[0])
    CAM.SetRegionOfInterestArray(dev, [C.RegionOfInterest(**ROI)])
    CAM.Initialize(dev)
    r = CAM.GetRuntimeParameters(dev)
    r.frame_rate_hz = fps
    r.exposure_time_ms = exposure_ms
    r['flip_horizontal'] = True    # same as the driver
    r['flip_vertical'] = False
    CAM.SetRuntimeParameters(dev, r)
    CAM.Start(dev)
    actual = CAM.GetRuntimeParameters(dev)
    print(f'Camera: requested {exposure_ms} ms @ {fps} Hz, '
          f'actual {actual.exposure_time_ms} ms @ {actual.frame_rate_hz} Hz')
    return dev


def acquire(dev, frame):
    ret = CAM.AcquireFrame(dev, frame=frame)
    if isinstance(ret, tuple) and len(ret) == 2:
        frame = ret[1]
    return frame


def load_saved_frame(xml_path):
    '''Load a saved raw frame (.raw.xml) with the SDK. Name of the call is not confirmed
    for the Python API, so try the likely ones and report what exists if none work.'''
    for name in ('LoadFrame', 'commonLoadFrame'):
        fn = getattr(C, name, None)
        if fn is None:
            continue
        ret = fn(xml_path)
        frame = ret[1] if isinstance(ret, tuple) and len(ret) == 2 else ret
        return frame
    raise SystemExit('No frame-loading function found in hsi_common. Available names:\n  '
                     + '\n  '.join(n for n in dir(C) if 'oad' in n or 'rame' in n))


def try_load(ctx_path):
    '''Load a context, or explain what is in the folder if the SDK refuses it.'''
    try:
        return M.LoadContext(ctx_path)
    except AssertionError as e:
        print(f'\n[ERROR] LoadContext failed for {ctx_path}: {e}')
        for root, _, files in os.walk(ctx_path):
            for f in files:
                print('   ', os.path.relpath(os.path.join(root, f), ctx_path))
        print('Check the HSI log files in the --out folder for the file the SDK could not read.')
        raise


def run_context(ctx_path, frame, raws):
    ctx = try_load(ctx_path)
    print(f'  context status: {M.ContextGetStatus(ctx)}')
    pipe = M.Create(ctx)
    params = M.GetConfigurationParameters(pipe)
    params.spatial_median_filter_enable = False      # same as the driver
    M.SetConfigurationParameters(pipe, params)
    M.Initialize(pipe)
    fmt = M.GetOutputDataFormat(pipe)
    cube = C.AllocateCube(fmt)
    M.Start(pipe)
    cubes = []
    for raw in raws:
        arr = C.FrameAsArray(frame)
        arr[:] = raw                                  # same raw data into the frame buffer
        M.PushFrame(pipe, frame)
        M.GetCube(pipe, cube, timeout_ms=1000)
        cubes.append(np.array(C.CubeAsArray(cube, BSQ=False), dtype=np.float32, copy=True))
    bands = np.asarray(fmt['bands_nm'], dtype=np.float64)
    M.Pause(pipe)
    M.Stop(pipe)
    C.DeallocateCube(cube)
    M.DeallocateContext(ctx)
    return np.stack(cubes), bands


def compare(name_a, a, name_b, b, bands_a, bands_b, lines):
    lines.append(f'\n=== {name_b} vs {name_a} ===')
    lines.append(f'cube shapes: {a.shape} vs {b.shape}')
    lines.append('band  center_a   center_b   d_center   ratio_median  ratio_p5  ratio_p95  max|rel diff|')
    floor = np.percentile(np.abs(a), 10)              # skip near-zero pixels in ratios
    for k in range(a.shape[-1]):
        xa, xb = a[..., k].ravel(), b[..., k].ravel()
        ok = (np.abs(xa) > floor) & np.isfinite(xa) & np.isfinite(xb)
        ratio = xb[ok] / xa[ok]
        rel = np.abs(xb[ok] - xa[ok]) / np.abs(xa[ok])
        lines.append(f'{k:4d}  {bands_a[k]:9.2f}  {bands_b[k]:9.2f}  {bands_b[k]-bands_a[k]:8.2f}   '
                     f'{np.median(ratio):11.5f}  {np.percentile(ratio, 5):8.5f}  '
                     f'{np.percentile(ratio, 95):9.5f}  {rel.max():12.5f}')
    lines.append(f'identical arrays: {np.array_equal(a, b)}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--context', required=True,
                    help='active IMEC context, e.g. ~/ibex_ws/src/ibex/packages/hyper_drive/config/imec/context')
    ap.add_argument('--out', default='~/fnumber_test', help='output directory')
    ap.add_argument('--frames', type=int, default=10, help='raw frames to capture')
    ap.add_argument('--exposure', type=float, default=60.0, help='ms; must match the dark reference (60)')
    ap.add_argument('--fps', type=float, default=15.0)
    ap.add_argument('--frame-xml', default=None,
                    help='offline: saved raw frame (.raw.xml) to use instead of the camera')
    ap.add_argument('--include-noref', action='store_true',
                    help='also process with dark/non-uniformity references removed')
    args = ap.parse_args()

    src = os.path.abspath(os.path.expanduser(args.context))
    out = os.path.abspath(os.path.expanduser(args.out))
    os.makedirs(out, exist_ok=True)
    C.InitializeLogger(out, C.LoggerVerbosity.LV_INFO)

    contexts = {'f2p8': dict(f_number=2.8), 'f0': dict(f_number=0)}
    if args.include_noref:
        contexts['noref'] = dict(f_number=2.8, strip_refs=True)
    ctx_dirs = {name: os.path.join(out, name, 'context') for name in contexts}

    # Pre-flight: make sure the SDK can load the source and every copy BEFORE using the camera.
    print('checking that the source context loads ...')
    M.DeallocateContext(try_load(src))
    for name, kw in contexts.items():
        if os.path.exists(os.path.join(out, name)):
            shutil.rmtree(os.path.join(out, name))
        os.makedirs(os.path.join(out, name))
        make_context_copy(src, ctx_dirs[name], **kw)
        M.DeallocateContext(try_load(ctx_dirs[name]))
        print(f'made and loaded {name}')

    dev = None
    if args.frame_xml:
        frame = load_saved_frame(os.path.abspath(os.path.expanduser(args.frame_xml)))
        raws = np.array(C.FrameAsArray(frame), dtype=np.float32, copy=True)[None]
        print(f'offline mode: loaded {args.frame_xml}')
    else:
        dev = open_camera(args.exposure, args.fps)
        frame = C.AllocateFrame(CAM.GetOutputFrameDataFormat(dev))
        input(f'\nPoint the camera at the test scene and hold still, then press Enter '
              f'to capture {args.frames} frames...')
        raws = []
        for i in range(args.frames):
            frame = acquire(dev, frame)
            raws.append(np.array(C.FrameAsArray(frame), dtype=np.float32, copy=True))
        raws = np.stack(raws)
    np.save(os.path.join(out, 'raw_frames.npy'), raws)
    sat = (raws >= 7100).mean() * 100
    print(f'raw frames: {raws.shape}, min {raws.min():.0f}, max {raws.max():.0f}, '
          f'{sat:.2f}% at/above saturation (7100)')

    results = {}
    for name in contexts:
        print(f'processing with {name} ...')
        cubes, bands = run_context(ctx_dirs[name], frame, raws)
        np.save(os.path.join(out, f'cubes_{name}.npy'), cubes)
        np.save(os.path.join(out, f'bands_{name}.npy'), bands)
        results[name] = (cubes, bands)

    if dev is not None:
        CAM.Pause(dev)
        CAM.Stop(dev)
        CAM.CloseDevice(dev)

    source = f'offline frame {args.frame_xml}' if args.frame_xml else f'{len(raws)} live frames, {args.exposure} ms'
    lines = [f'f-number test, {source}, source context {src}',
             f'raw saturation: {sat:.2f}% of pixels >= 7100']
    base, base_bands = results['f2p8']
    for name, (cubes, bands) in results.items():
        if name != 'f2p8':
            compare('f2p8', base, name, cubes, base_bands, bands, lines)
    text = '\n'.join(lines)
    print('\n' + text)
    open(os.path.join(out, 'summary.txt'), 'w').write(text + '\n')
    print(f'\nSaved to {out}')


if __name__ == '__main__':
    main()
