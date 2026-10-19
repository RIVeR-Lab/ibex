import os
import sys

# Set up library paths before importing IMEC modules.
# LD_LIBRARY_PATH must be set before the process starts, so if it's not
# already configured, re-launch this script once with the correct environment.
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
    # Re-execute this script with the updated environment
    os.execv(sys.executable, [sys.executable] + sys.argv)

import numpy as np
sys.path.append('/opt/imec/hsi-mosaic/python_apis')

import hsi_common as HSI_COMMON
import hsi_camera as HSI_CAMERA
import hsi_mosaic as HSI_MOSAIC

# =====================================================================
# XIMEA calibration -- single-frame dark + nonuniformity (white).
# Adds dark-field + nonuniformity references to the EXISTING XIMEA context
# so synchronous_cubes emits flat-fielded XIMEA cubes (like the SWIR one).
#
# >>> THREE VALUES BELOW MUST BE CONFIRMED FOR YOUR SETUP <<<
# They are camera-specific and I could not read them from the logs. Getting
# any of them wrong will bake a MISALIGNED reference into the context.
# =====================================================================

# 1) XIMEA manufacturer enum. The IMEC script used EM_IMEC; the XIMEA value is
#    almost certainly EM_XIMEA but CONFIRM the spelling (see grep in notes).
#    If wrong, EnumerateConnectedDevices below returns nothing and the assert
#    fires -- a loud, safe failure, not silent corruption.
MANUFACTURER = HSI_CAMERA.Manufacturer.EM_XIMEA  # <-- VERIFY

# 2) XIMEA ROI. MUST match the ROI synchronous_cubes sets for the XIMEA device
#    (its SetRegionOfInterestArray call), or the reference frame geometry won't
#    match the live cubes. Copy the exact x/y/width/height from synchronous_cubes.
#    Left as None on purpose so the script refuses to run until you fill it in.
XIMEA_ROI = None  # <-- REQUIRED, e.g. HSI_COMMON.RegionOfInterest(x=..., y=..., width=..., height=...)

# 3) Context path. Load the EXISTING XIMEA context and save back to it. Point at
#    your SOURCE tree (so a rebuild installs it), and BACK IT UP first. Confirm
#    the path for your current layout -- the package dir has moved before.
CONTEXT_PATH = '/home/river/ibex_ws/src/ibex/packages/hyper_drive/config/ximea/context'  # <-- CONFIRM

# XIMEA runtime settings -- these MUST match how synchronous_cubes runs XIMEA,
# because the dark reference is integration-time-specific. From the live
# C/R PARAMS: 10 ms exposure, 15 Hz, no flips.
INTEGRATION_TIME_MS = 10.0
FRAME_RATE_HZ = 15.0
FLIP_HORIZONTAL = False
FLIP_VERTICAL = False


def main():
    if XIMEA_ROI is None:
        sys.exit('XIMEA_ROI is not set. Copy the exact ROI synchronous_cubes '
                 'uses for the XIMEA device into XIMEA_ROI, then re-run.')

    # Initialize logger
    HSI_COMMON.InitializeLogger('/tmp', HSI_COMMON.LoggerVerbosity.LV_INFO)

    # Find and connect to the XIMEA camera
    dev_list = HSI_CAMERA.EnumerateConnectedDevices(manufacturer=MANUFACTURER)
    assert len(dev_list) > 0, ('No XIMEA camera found -- check MANUFACTURER enum '
                               'and that the SWIR camera is not the only one connected')

    device = HSI_CAMERA.OpenDevice(dev_list[0])
    HSI_CAMERA.SetRegionOfInterestArray(device, [XIMEA_ROI])
    HSI_CAMERA.Initialize(device)

    # Set requested runtime parameters (match synchronous_cubes' XIMEA config)
    r_params = HSI_CAMERA.GetRuntimeParameters(device)
    r_params.frame_rate_hz = FRAME_RATE_HZ
    r_params.exposure_time_ms = INTEGRATION_TIME_MS
    r_params['flip_horizontal'] = FLIP_HORIZONTAL
    r_params['flip_vertical'] = FLIP_VERTICAL
    HSI_CAMERA.SetRuntimeParameters(device, r_params)
    HSI_CAMERA.Start(device)

    # Query what the camera actually applied -- the dark reference is tied to the
    # ACTUAL integration time, so make sure it matches what synchronous_cubes runs.
    r_params_actual = HSI_CAMERA.GetRuntimeParameters(device)
    actual_integration_ms = r_params_actual.exposure_time_ms
    print(f'Requested integration: {INTEGRATION_TIME_MS}ms')
    print(f'Actual hardware integration time: {actual_integration_ms}ms')
    print(f'Actual hardware frame rate: {r_params_actual.frame_rate_hz}Hz')
    if abs(actual_integration_ms - INTEGRATION_TIME_MS) > 1e-3:
        print(f'  [warn] actual integration ({actual_integration_ms}ms) differs from '
              f'requested ({INTEGRATION_TIME_MS}ms); the dark reference will be stored '
              f'for the ACTUAL value -- make sure synchronous_cubes runs XIMEA at the '
              f'same integration time.')

    # Load existing XIMEA context (keeps its sensor calibration + optical setup)
    context = HSI_MOSAIC.LoadContext(CONTEXT_PATH)

    # --- DARK REFERENCE: single frame, lens capped ---
    input('\nCover the XIMEA lens completely, then press Enter...')
    print('Capturing single dark reference frame...')
    dark_frame = HSI_COMMON.AllocateFrame(HSI_CAMERA.GetOutputFrameDataFormat(device))
    result, dark_frame = HSI_CAMERA.AcquireFrame(device, frame=dark_frame)

    arr = HSI_COMMON.FrameAsArray(dark_frame)
    print(f'Dark frame - min: {arr.min():.1f} max: {arr.max():.1f} mean: {arr.mean():.1f}')

    HSI_MOSAIC.ContextSetDarkFieldReferences(context, [dark_frame])
    print('Dark reference set')

    has_dark = HSI_MOSAIC.ContextIntegrationTimeInDark(context, actual_integration_ms)
    print(f'Dark reference for {actual_integration_ms}ms: {bool(has_dark)}')

    # --- WHITE / NONUNIFORMITY: single frame, uniform white target ---
    # NOTE: capture under DC light or sunlight if possible. Under 120 Hz
    # fluorescent flicker a single white frame freezes one phase of the ripple
    # into the correction -- the known XIMEA/VNIR noise source.
    input('\nPoint XIMEA at a uniform white surface, then press Enter...')
    print('Capturing single white reference frame...')
    white_frame = HSI_COMMON.AllocateFrame(HSI_CAMERA.GetOutputFrameDataFormat(device))
    result, white_frame = HSI_CAMERA.AcquireFrame(device, frame=white_frame)

    arr = HSI_COMMON.FrameAsArray(white_frame)
    print(f'White frame - min: {arr.min():.1f} max: {arr.max():.1f} mean: {arr.mean():.1f}')

    HSI_MOSAIC.ContextSetNonUniformity(context, dark_frame, white_frame)
    print('Nonuniformity correction set')

    # --- SAVE CONTEXT ---
    HSI_MOSAIC.SaveContext(context, CONTEXT_PATH)
    print(f'Context saved to {CONTEXT_PATH}')

    # Verify
    status = HSI_MOSAIC.ContextGetStatus(context)
    print(f'Context status: {status}')

    has_dark = HSI_MOSAIC.ContextIntegrationTimeInDark(context, actual_integration_ms)
    print(f'Dark reference for {actual_integration_ms}ms: {bool(has_dark)}')

    print('Searching for stored dark reference integration time (5-15ms)...')
    found = False
    for t in [x * 0.1 for x in range(50, 150)]:
        if HSI_MOSAIC.ContextIntegrationTimeInDark(context, t):
            print(f'Dark reference found at: {t:.1f}ms')
            found = True
            break
    if not found:
        print('Dark reference not found in 5-15ms range')

    # Cleanup
    HSI_MOSAIC.DeallocateContext(context)
    HSI_CAMERA.Pause(device)
    HSI_CAMERA.Stop(device)
    HSI_CAMERA.CloseDevice(device)
    print('Done')


if __name__ == '__main__':
    main()
