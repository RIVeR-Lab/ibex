import os
import sys
import cv2
import time
import typing
import traceback
import numpy as np
import threading
from bs4 import BeautifulSoup
#from numba import jit, prange
from pathlib import Path
import matplotlib.pyplot as plt
import array
from concurrent.futures import ThreadPoolExecutor

# Messages
from std_msgs.msg import Header
from sensor_msgs.msg import Image
from hyper_drive_interfaces.msg import DataCube
from hyper_drive_interfaces.msg import MultipleDataCubes
from hyper_drive_interfaces.srv import AdjustParam

# ROS Imports
import rclpy
from rclpy.node import Node
from rclpy.logging import get_logging_directory
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from collections import deque
from ament_index_python.packages import get_package_share_directory
import ros2_numpy

### Set parameters to find the HSI mosaic binaries
os.environ['PATH'] += os.pathsep + r'/opt/imec/hsi-mosaic/bin'
# Also add them to the path
sys.path.append('/opt/imec/hsi-mosaic/python_apis')

# Import IMEC specific libraries
import hsi_common as HSI_COMMON
import hsi_camera as HSI_CAMERA
import hsi_mosaic as HSI_MOSAIC

class DataCubesGenerator(Node):
    def __init__(self):        # Setup logging to roslog location

        super().__init__('data_cubes_generator')

        # Setup logging
        log_dir = get_logging_directory()
        log_dir_str = str(log_dir)
        self.get_logger().info(f'Logging camera info to {log_dir_str}')
        HSI_COMMON.InitializeLogger(log_dir_str, HSI_COMMON.LoggerVerbosity.LV_INFO)
        self.get_logger().info('Loading Context ...')

        # Lock for camera setting updates
        self.lock = threading.Lock()

        # Reusable 2-worker pool so XIMEA and IMEC acquisition can overlap.
        # Created once (not per frame) to avoid thread-spawn overhead each cycle.
        self.acq_executor = ThreadPoolExecutor(max_workers=2)

        # Single worker that publishes cube N while cube N+1 is being acquired.
        # pub_future is the publish currently in flight (at most one at a time).
        self.pub_executor = ThreadPoolExecutor(max_workers=1)
        self.pub_future = None
        self.last_loop_start = None

        # Undistortion maps, built on the first frame of each camera
        self.x_undistort_maps = None
        self.i_undistort_maps = None
        self.remap_multichannel = True
        # Setup callback for data
        self.package_share_dir = get_package_share_directory('hyper_drive')

        self.declare_parameter('sleep', 0.001)
        self.sleep_time = self.get_parameter('sleep').get_parameter_value().double_value

        #ximea
        self.declare_parameter('x_frame_rate', 30)
        self.x_frame_rate = self.get_parameter('x_frame_rate').get_parameter_value().integer_value

        self.declare_parameter('x_integration_time', 15)
        self.x_integration_time = self.get_parameter('x_integration_time').get_parameter_value().integer_value

        #imec
        self.declare_parameter('i_frame_rate', 10)
        self.i_frame_rate = self.get_parameter('i_frame_rate').get_parameter_value().integer_value

        self.declare_parameter('i_integration_time', 70)
        self.i_integration_time = self.get_parameter('i_integration_time').get_parameter_value().integer_value

        #frequency of publishing
        self.declare_parameter('time_wait', 0)
        self.time_wait = self.get_parameter('time_wait').get_parameter_value().integer_value * 60

        # Set up service
        self.param_server = self.create_service(AdjustParam, 'adjust_param', self.adjust_param_callback)
        
        # Create publisher to send datacubes on
        self.pub_cube = self.create_publisher(MultipleDataCubes, 'synchronous_cubes', 10)
        #subscribe to Vimba raw image
        # The RGB subscription gets its own callback group so, with the multi-threaded
        # executor in main(), RGB frames keep arriving while timer_callback is busy
        # acquiring. Recent frames are buffered so each cube set can be paired with
        # the RGB frame captured closest to it.
        self.rgb_group = MutuallyExclusiveCallbackGroup()
        self.sub_img = self.create_subscription(Image, f'/camera/image_raw', self.image_callback, 10,
                                                callback_group=self.rgb_group)
        self.raw_img = Image()
        self.rgb_buffer = deque(maxlen=30)
        
        # Load camera parameters
        self.parse_parameters('ximea')
        self.parse_parameters('imec')
        # Initialize the ximea and imec cameras
        self.initialize_camera('ximea')
        self.initialize_camera('imec')
        # Ximea Explicit Allocate based on Output-Data-Format
        x_dataformat = HSI_CAMERA.GetOutputFrameDataFormat (self.x_device)
        self.x_frame = HSI_COMMON.AllocateFrame(x_dataformat)
        # Imec Explicit Allocate based on Output-Data-Format
        i_dataformat = HSI_CAMERA.GetOutputFrameDataFormat(self.i_device)
        self.i_frame = HSI_COMMON.AllocateFrame(i_dataformat)
        self.setup_context('ximea')
        self.setup_context('imec')
        self.time_future = self.get_clock().now().nanoseconds / 1e9 + self.time_wait

        HSI_CAMERA.Start(self.x_device)
        HSI_CAMERA.Start(self.i_device)

        # Timer callback to run camera
        self.timer = self.create_timer(self.sleep_time, self.timer_callback)

    #callback to handle vimba raw image
    def image_callback(self, msg: Image) -> None:
        self.raw_img = msg
        self.rgb_buffer.append(msg)

    @staticmethod
    def stamp_ns(stamp) -> int:
        return stamp.sec * 1_000_000_000 + stamp.nanosec

    def nearest_rgb(self, target_ns):
        '''
        Return the buffered RGB frame whose header stamp is closest to target_ns,
        and its offset from target_ns in milliseconds.
        '''
        frames = list(self.rgb_buffer)
        if not frames:
            return self.raw_img, float('nan')
        best = min(frames, key=lambda m: abs(self.stamp_ns(m.header.stamp) - target_ns))
        return best, (self.stamp_ns(best.header.stamp) - target_ns) / 1e6

    def initialize_camera(self, model) -> None:
        # Rate at which to generate composite data cubes
        # Look for connected cameras an choose appropriate model (assumes we only have 1 IMEC and 1 XIMEA)
        if model == 'ximea':
            integration_range = (0.021000, 999.995000)
            dev_list = HSI_CAMERA.EnumerateConnectedDevices(manufacturer=HSI_CAMERA.Manufacturer.EM_XIMEA)
            roi = [HSI_COMMON.RegionOfInterest(x=0, y=0, width=2045, height=1085)]

            # Connect to the first available camera of the specified model type
            self.get_logger().info(f'looking for device:: {dev_list[0]}')
            self.x_device = HSI_CAMERA.OpenDevice(dev_list[0])
            HSI_CAMERA.SetRegionOfInterestArray(self.x_device, roi)
            self.get_logger().info(f'Region-of-Intereset Set to: {roi}')
            self.get_logger().info(f'Initializing Camera...')
            HSI_CAMERA.Initialize(self.x_device)
            # Get/Set Camera Configuration Parameters (example)
            c_params = HSI_CAMERA.GetConfigurationParameters(self.x_device)
            self.get_logger().info(f'C PARAMS>')
            self.get_logger().info(f'{c_params}')

            r_params = HSI_CAMERA.GetRuntimeParameters(self.x_device)
            self.get_logger().info(f'{r_params}')
            # Set the frame rate and exposure time before the camera starts
            # These values can be adjusted later through a callback
            r_params.frame_rate_hz = self.x_frame_rate
            r_params.exposure_time_ms = self.x_integration_time
            # Set these parameters on the device
            HSI_CAMERA.SetRuntimeParameters(self.x_device, r_params)
            self.get_logger().info(f'R PARAMS>')
            self.get_logger().info(f'{r_params}')
        
        elif model == 'imec':
            integration_range = (0.010000, 90)
            dev_list = HSI_CAMERA.EnumerateConnectedDevices(manufacturer=HSI_CAMERA.Manufacturer.EM_IMEC)
            roi = [HSI_COMMON.RegionOfInterest(x=1, y=1, width=639, height=510)]

            # Connect to the first available camera of the specified model type
            self.get_logger().info(f'looking for device:: {dev_list[0]}')
            self.i_device = HSI_CAMERA.OpenDevice(dev_list[0])
            HSI_CAMERA.SetRegionOfInterestArray(self.i_device, roi)
            self.get_logger().info(f'Region-of-Intereset Set to: {roi}')
            self.get_logger().info(f'Initializing Camera...')
            HSI_CAMERA.Initialize(self.i_device)
            # Get/Set Camera Configuration Parameters (example)
            c_params = HSI_CAMERA.GetConfigurationParameters(self.i_device)
            self.get_logger().info(f'C PARAMS>')
            self.get_logger().info(f'{c_params}')
            
            r_params = HSI_CAMERA.GetRuntimeParameters(self.i_device)
            self.get_logger().info(f'{r_params}')
            # Set the frame rate and exposure time before the camera starts
            # These values can be adjusted later through a callback
            r_params.frame_rate_hz = self.i_frame_rate
            r_params.exposure_time_ms = self.i_integration_time
            r_params['flip_vertical'] = False
            r_params['flip_horizontal'] = True
            # Set these parameters on the device
            HSI_CAMERA.SetRuntimeParameters(self.i_device, r_params)
            self.get_logger().info(f'R PARAMS>')
            self.get_logger().info(f'{r_params}')

    def restart_camera(self) -> None:
        '''
        Restart camera in the event there is an error setting the runtime parameters
        '''
        self.get_logger().error('ERROR IN CAMERA MAIN LOOP! Waiting 5 seconds and reinitializing the camera')
        HSI_CAMERA.Pause(self.x_device)
        HSI_CAMERA.Stop(self.x_device)
        HSI_CAMERA.CloseDevice(self.x_device)

        HSI_CAMERA.Pause(self.i_device)
        HSI_CAMERA.Stop(self.i_device)
        HSI_CAMERA.CloseDevice(self.i_device)

        # Sleep 5 seconds
        time.sleep(5)
        # Restart the camera
        self.initialize_camera('ximea')
        self.initialize_camera('imec')


    def setup_context(self, model) -> None:
        '''
        Load HSI Context files and prepare to run demosaicing pipeline
        '''
        # ROS2: Get package share directory instead of using rospkg
        package_share_dir = get_package_share_directory('hyper_drive')
        # Build path to config file
        dn_context = os.path.join(package_share_dir,'config',model,'context')
        version = HSI_MOSAIC.GetAPIVersion()
        self.get_logger().info(f'VERSION :: {version}')
        self.get_logger().info(str(Path(dn_context).absolute()))
        assert Path(dn_context).exists()
        self.my_context = HSI_MOSAIC.LoadContext(dn_context)
        self.get_logger().info(f'Context = {self.my_context}')
        status = HSI_MOSAIC.ContextGetStatus(self.my_context)
        self.get_logger().info(str(status))
        
        if model == 'ximea':
            self.x_pipeline = HSI_MOSAIC.Create(self.my_context)
            self.get_logger().info(str(self.x_pipeline))
            self.params = HSI_MOSAIC.GetConfigurationParameters(self.x_pipeline)
            self.params.spatial_median_filter_enable = False
            self.params.spatial_resampling_width = 407    # XIMEA output width  (default 407)
            self.params.spatial_resampling_height = 215   # XIMEA output height (default 215)
            self.get_logger().info(f'Configuration Params : {self.params}')
            HSI_MOSAIC.SetConfigurationParameters(self.x_pipeline, self.params)
            self.get_logger().info(f'Initializing Pipeline')

            HSI_MOSAIC.Initialize(self.x_pipeline)

            outputdataformat = HSI_MOSAIC.GetOutputDataFormat(self.x_pipeline)
            self.get_logger().info(f'Output Data Format = {outputdataformat}')
            self.use_pipeline_band_centres('ximea', outputdataformat)
            self.x_cube = HSI_COMMON.AllocateCube(outputdataformat)
            self.get_logger().info(f'Starting Pipeline ...')

            HSI_MOSAIC.Start(self.x_pipeline)

        elif model == 'imec':
            self.i_pipeline = HSI_MOSAIC.Create(self.my_context)
            self.get_logger().info(str(self.i_pipeline))
            self.params = HSI_MOSAIC.GetConfigurationParameters(self.i_pipeline)
            self.params.spatial_median_filter_enable = False
            self.get_logger().info(f'Configuration Params : {self.params}')
            HSI_MOSAIC.SetConfigurationParameters(self.i_pipeline, self.params)
            self.get_logger().info(f'Initializing Pipeline')

            HSI_MOSAIC.Initialize(self.i_pipeline)

            outputdataformat = HSI_MOSAIC.GetOutputDataFormat(self.i_pipeline)
            self.get_logger().info(f'Output Data Format = {outputdataformat}')
            self.use_pipeline_band_centres('imec', outputdataformat)
            self.i_cube = HSI_COMMON.AllocateCube(outputdataformat)
            self.get_logger().info(f'Starting Pipeline ...')

            HSI_MOSAIC.Start(self.i_pipeline)

    def use_pipeline_band_centres(self, model, outputdataformat) -> None:
        '''
        Replace the nominal XML band centres with the ones the pipeline reports
        for the cube it actually produces (bands_nm). These include the shift
        from the lens's cone of light and are the true centres of the published
        bands. FWHM and QE stay at their nominal per-band XML values, since the
        pipeline does not report effective ones.
        '''
        bands_nm = getattr(outputdataformat, 'bands_nm', None)
        if bands_nm is None:
            bands_nm = outputdataformat['bands_nm']
        bands_nm = [float(b) for b in bands_nm]

        nominal = self.x_central_wave if model == 'ximea' else self.i_central_wave
        if len(bands_nm) != len(nominal):
            self.get_logger().warn(
                f'{model}: pipeline outputs {len(bands_nm)} bands but the XML has {len(nominal)} '
                f'selected bands; per-band FWHM/QE may not line up with the cube.')

        if model == 'ximea':
            self.x_central_wave = bands_nm
        elif model == 'imec':
            self.i_central_wave = bands_nm
        self.get_logger().info(
            f'{model}: publishing {len(bands_nm)} band centres '
            f'({bands_nm[0]:.2f}-{bands_nm[-1]:.2f} nm)')

    def parse_parameters(self, model) -> None:
        '''
        Load parameter for camera from manufacturer provided XML file
        for publication in datacube messages
        '''
        # Get an instance of RosPack with the default search paths
        # ROS2: Get package share directory instead of using rospkg
        package_share_dir = get_package_share_directory('hyper_drive')
        # Build path to config file
        param_path = os.path.join(package_share_dir, 'config', f'{model}.xml')
        with open(param_path, 'r') as f:
            data = f.read()
            Bs_data = BeautifulSoup(data, "xml")
            if model == 'ximea':
                self.x_central_wave = []
                self.x_fwhm = []
                self.x_QE = []
            elif model == 'imec':
                self.i_central_wave = []
                self.i_fwhm = []
                self.i_QE = []
            # Read only the physical filter bands (<band> elements) that the
            # pipeline outputs (selected="true"), taking each band's first-order
            # peak. A plain find_all("wavelength_nm") also matched the <virtual_band>
            # entries of every spectral correction matrix in the file, so the lists
            # held the physical bands plus each matrix's copy (XIMEA 25 + 24 + 24 = 73,
            # IMEC 9 + 9 + 9 = 27).
            bands = []
            for band in Bs_data.find_all("band"):
                if band.get('selected', 'true') != 'true':
                    continue
                peak = band.find("peak", attrs={"order": "1"}) or band.find("peak")
                bands.append((float(peak.find("wavelength_nm").getText()),
                              float(peak.find("fwhm_nm").getText()),
                              float(peak.find("QE").getText())))

            # The XML lists bands in mosaic tile order; the cube is in ascending
            # wavelength order, so sort to match.
            bands.sort(key=lambda b: b[0])
            for wavelength, fwhm, qe in bands:
                if model == 'ximea':
                    self.x_central_wave.append(wavelength)
                    self.x_fwhm.append(fwhm)
                    self.x_QE.append(qe)
                elif model == 'imec':
                    self.i_central_wave.append(wavelength)
                    self.i_fwhm.append(fwhm)
                    self.i_QE.append(qe)
            # Get calibration coefficients
            coefficients = []
            for coefficient in Bs_data.find_all("coefficients"):
                coefficients.append(np.array([float(z) for z in coefficient['values'].split()]))
            self.coefficients = np.array(coefficients)
        
    def adjust_param_callback(self, request, response):
        '''    Listen to user parameter requests    '''     
        frame_time = 1/(request.frame_rate) * 1000    
        self.get_logger().info(f'Incoming message: {request}')

        # Check the time bounds are OK
        if request.camera_model == 'imec':
            cam = self.i_device
            integration_range = (0.010000, 90)

        if request.camera_model == 'ximea':
            cam = self.x_device
            integration_range = (0.021000, 999.995000)

        if (integration_range[0] < request.integration_time < integration_range[1]) & (request.integration_time < frame_time):
            return self.set_camera_params(cam, request.integration_time, request.frame_rate, response)
        else:
            self.get_logger().error('INVALID INTEGRATION TIME REQUESTED!')
            response.success = False
            return response

    def set_camera_params(self, camera, exposure_time: float, frame_rate: float, response):
        try:
            # Pause the camera        
            print(f'Exposure time: {exposure_time} Frame Rate: {frame_rate}')
            # Proposing to try 3 steps
            with self.lock:         
                #Step-1: Set frame rate to a very low value eg. 1 fps            
                HSI_CAMERA.Pause(camera)
                # Get r-params
                r_params = HSI_CAMERA.GetRuntimeParameters(camera)
                print(r_params)
                r_params.frame_rate_hz = 1            
                self.get_logger().info(f'Update Runtime Params: {HSI_CAMERA.SetRuntimeParameters(camera, r_params)}')       
                # #Step-2: Set integration time            
                r_params = HSI_CAMERA.GetRuntimeParameters(camera)
                r_params.exposure_time_ms = exposure_time            
                self.get_logger().info(f'Update Runtime Params: {HSI_CAMERA.SetRuntimeParameters(camera, r_params)}')     
                # #Step-3: Set frame rate            
                r_params = HSI_CAMERA.GetRuntimeParameters(camera)
                r_params.frame_rate_hz = frame_rate           
                self.get_logger().info(f'Update Runtime Params: {HSI_CAMERA.SetRuntimeParameters(camera, r_params)}')      
                HSI_CAMERA.Start(camera)
                time.sleep(0.1)
                response.success = True
                return response      

        except Exception as e:
            self.get_logger().error(traceback.format_exc())
            self.get_logger().error(str(e))
            self.get_logger().error('Error setting user parameter!')
            response.success = False
            return response



    def undistort(self, cube, model):
        imec_K = [[571.0648167, 0, 96.21785],
                  [0, 572.4372833, 77.75815],
                  [0, 0, 1]]
        imec_distort = [-0.715016666666667, 18.2009666666667, -0.003883333333333, -0.002716666666667, -234.22125]

        ximea_K = [[929.0870667, 0, 193.47025],
                   [0, 928.9873333, 114.0106],
                   [0, 0, 1]]
        ximea_distort = [0.12115, -5.45603333333333, 0.0021, -0.004283333333333, 100.424166666667]
    
        # The pixel remapping depends only on the intrinsics and the image size, so
        # the maps are built once per camera and reused. cv2.undistort rebuilt them
        # on every call, once per band, every frame. The result is a new array, so
        # the SDK's cube buffer is left untouched.
        height, width, bands = cube.shape

        if model == 'imec':
            if self.i_undistort_maps is None or self.i_undistort_maps[0] != (height, width):
                map1, map2 = cv2.initUndistortRectifyMap(np.array(imec_K), np.array(imec_distort), None,
                                                         np.array(imec_K), (width, height), cv2.CV_16SC2)
                self.i_undistort_maps = ((height, width), map1, map2)
            _, map1, map2 = self.i_undistort_maps

        elif model == 'ximea':
            if self.x_undistort_maps is None or self.x_undistort_maps[0] != (height, width):
                map1, map2 = cv2.initUndistortRectifyMap(np.array(ximea_K), np.array(ximea_distort), None,
                                                         np.array(ximea_K), (width, height), cv2.CV_16SC2)
                self.x_undistort_maps = ((height, width), map1, map2)
            _, map1, map2 = self.x_undistort_maps

        # Remap all bands in one call where OpenCV supports it, otherwise band by band
        if self.remap_multichannel:
            try:
                return cv2.remap(cube, map1, map2, cv2.INTER_LINEAR)
            except cv2.error:
                self.remap_multichannel = False
                self.get_logger().warn('Multi-channel remap not supported by this OpenCV; remapping band by band')

        undistorted = np.empty_like(cube)
        for lam in range(bands):
            undistorted[:, :, lam] = cv2.remap(cube[:, :, lam], map1, map2, cv2.INTER_LINEAR)
        return undistorted

    def publish_cubes(self, x_cube: np.ndarray, i_cube: np.ndarray, x_stamp, i_stamp):
        '''
        Publish hyperspectral datacubes
        '''
        t0 = time.time()
        x_cube = self.undistort(x_cube, 'ximea')
        i_cube = self.undistort(i_cube, 'imec')
        t1 = time.time()
        #Messages
        x_ros_cube = DataCube()
        i_ros_cube = DataCube()
        ros_cubes = MultipleDataCubes()
        t2 = time.time()
        # Headers carry each camera's capture time, not the publish time
        x_header = Header()
        x_header.stamp = x_stamp.to_msg()
        i_header = Header()
        i_header.stamp = i_stamp.to_msg()

        x_ros_cube.header = x_header
        t3 = time.time()
        #x_ros_cube.data = x_cube.astype(np.float32).flatten().tolist()
        x_ros_cube.data = array.array('f', np.ascontiguousarray(x_cube, dtype=np.float32).tobytes())
        t4 = time.time()
        # x_ros_cube.data = x_cube.astype(np.float32).flatten().tolist()
        x_ros_cube.height, x_ros_cube.width, x_ros_cube.lam = tuple(x_cube.shape)
        x_ros_cube.qe = self.x_QE
        x_ros_cube.fwhm_nm = self.x_fwhm
        x_ros_cube.central_wavelengths = self.x_central_wave
        t5 = time.time()

        i_ros_cube.header = i_header
        t6 = time.time()
        #i_ros_cube.data = i_cube.astype(np.float32).flatten().tolist()
        i_ros_cube.data = array.array('f', np.ascontiguousarray(i_cube, dtype=np.float32).tobytes())
        t7 = time.time()
        # i_ros_cube.data = i_cube.astype(np.float32).flatten().tolist()
        i_ros_cube.height, i_ros_cube.width, i_ros_cube.lam = tuple(i_cube.shape)
        i_ros_cube.qe = self.i_QE
        i_ros_cube.fwhm_nm = self.i_fwhm
        i_ros_cube.central_wavelengths = self.i_central_wave
        t8 = time.time()
        ros_cubes.cubes = [x_ros_cube, i_ros_cube]
        t9 = time.time()

        # RGB frame captured closest to the midpoint of the two HSI captures
        hsi_ns = (x_stamp.nanoseconds + i_stamp.nanoseconds) // 2
        raw_img, rgb_offset_ms = self.nearest_rgb(hsi_ns)
        ros_cubes.im = raw_img
        #ros_cubes.im = ros_numpy.msgify(Image, self.raw_img, encoding="8UC3")
        t10 = time.time()
        self.pub_cube.publish(ros_cubes)
        t11 = time.time()

        self.get_logger().info(
        f'Undistort:{t1-t0:.3f} '
        f'MsgCreate:{t2-t1:.3f} '
        f'Header:{t3-t2:.3f} '
        f'XData:{t4-t3:.3f} '
        f'XMeta:{t5-t4:.3f} '
        f'IHeader:{t6-t5:.3f} '
        f'IData:{t7-t6:.3f} '
        f'IMeta:{t8-t7:.3f} '
        f'CubeAssign:{t9-t8:.3f} '
        f'ImAssign:{t10-t9:.3f} '
        f'Publish:{t11-t10:.3f} '
        f'| Sync: IMEC-XIMEA {(i_stamp.nanoseconds - x_stamp.nanoseconds) / 1e6:+.1f} ms, '
        f'RGB-HSI {rgb_offset_ms:+.1f} ms'
        )

    def _acquire_cube(self, device, frame, pipeline, cube, label):
        '''
        Acquire, push, and retrieve one camera's cube. Runs on a worker thread.

        IMPORTANT: this must NOT touch self.lock. The caller (timer_callback)
        holds the lock for the whole parallel section; threading.Lock is not
        reentrant, so acquiring it here would deadlock. Each worker only touches
        its own camera's handles, so there is no shared state to guard between
        the two workers. This only overlaps in wall-clock time if the SDK calls
        release the GIL while waiting on hardware.
        '''
        t_start = time.time()
        HSI_CAMERA.AcquireFrame(device, frame=frame)
        # Capture time: the moment the frame is delivered, before any processing
        capture_stamp = self.get_clock().now()
        HSI_MOSAIC.PushFrame(pipeline, frame)
        HSI_MOSAIC.GetCube(pipeline, cube, timeout_ms=1000)
        py_cube = HSI_COMMON.CubeAsArray(cube, BSQ=False)
        return label, py_cube, time.time() - t_start, capture_stamp

    def timer_callback(self):
        '''
        Run central processing loop for camera
        '''

        try:
            # Send a software Tigger to the camera and grab the Frame
            # HSI_CAMERA.Trigger(self.device)
            current_time = self.get_clock().now().nanoseconds / 1e9
            if current_time > self.time_future:
                self.time_future = current_time + self.time_wait
                # Hold the lock across the whole parallel acquisition so a
                # concurrent set_camera_params() (which pauses/reconfigures a
                # camera) cannot run mid-acquisition. The two cameras fan out to
                # worker threads INSIDE the lock and are joined (.result())
                # before the lock releases -- workers never take the lock.
                with self.lock:
                    t0 = time.time()
                    x_future = self.acq_executor.submit(
                        self._acquire_cube, self.x_device, self.x_frame,
                        self.x_pipeline, self.x_cube, 'XIMEA')
                    i_future = self.acq_executor.submit(
                        self._acquire_cube, self.i_device, self.i_frame,
                        self.i_pipeline, self.i_cube, 'IMEC')

                    # .result() blocks until each worker finishes and re-raises
                    # any worker exception here, so the except-block below still
                    # catches failures and triggers restart_camera(). Both joins
                    # happen inside the with-block, so the lock is held until
                    # both cameras are done.
                    _, x_py_cube, x_dt, x_stamp = x_future.result()
                    _, i_py_cube, i_dt, i_stamp = i_future.result()
                    t_acq = time.time() - t0

                    # CubeAsArray can return a view of the SDK's cube buffer, which
                    # the next GetCube overwrites. Copy before handing the cubes to
                    # the publish thread so it never reads a half-updated buffer.
                    x_py_cube = x_py_cube.copy()
                    i_py_cube = i_py_cube.copy()

                # Publishing happens outside the lock and on its own thread, so cube N
                # is undistorted and published while cube N+1 is being acquired.
                # Wait for the previous publish first, so at most one is in flight
                # and messages go out in order.
                t3 = time.time()
                if self.pub_future is not None:
                    try:
                        self.pub_future.result()
                    except Exception:
                        self.get_logger().error('Publishing failed:\n' + traceback.format_exc())
                t_wait = time.time() - t3
                self.pub_future = self.pub_executor.submit(self.publish_cubes, x_py_cube, i_py_cube, x_stamp, i_stamp)

                # Loop period: time between the starts of consecutive acquisitions
                if self.last_loop_start is not None:
                    period = t0 - self.last_loop_start
                    rate = f'Loop:{period:.3f} ({1/period:.1f} Hz)'
                else:
                    rate = 'Loop: first frame'
                self.last_loop_start = t0

                self.get_logger().info(f'Cube shapes XIMEA: {x_py_cube.shape}, IMEC: {i_py_cube.shape}, VIMBA: {self.raw_img.width}x{self.raw_img.height}')
                self.get_logger().info(f'Acquire XIMEA:{x_dt:.3f} Acquire IMEC:{i_dt:.3f} Parallel acquire:{t_acq:.3f} (serial would be ~{x_dt+i_dt:.3f}) Wait for previous publish:{t_wait:.3f} {rate}')

        except Exception as e:
            self.get_logger().error(traceback.format_exc())
            self.get_logger().error('Exception in main capture loop')
            self.restart_camera()

    def shutdown(self):
        '''
        Custom shutdown behavior
        '''
        self.get_logger().info('Cleaning up node for the cameras')
        self.pub_executor.shutdown(wait=True)
        self.acq_executor.shutdown(wait=True)
        HSI_CAMERA.Pause(self.x_device)
        HSI_CAMERA.Stop(self.x_device)
        HSI_CAMERA.CloseDevice(self.x_device)
        HSI_MOSAIC.Pause(self.x_pipeline)
        HSI_MOSAIC.Stop(self.x_pipeline)
        HSI_COMMON.DeallocateCube(self.x_cube)
        HSI_COMMON.DeallocateFrame(self.x_frame)
        HSI_MOSAIC.DeallocateContext(self.my_context)  # ← fixed from self.context
        HSI_CAMERA.Pause(self.i_device)
        HSI_CAMERA.Stop(self.i_device)
        HSI_CAMERA.CloseDevice(self.i_device)
        HSI_MOSAIC.Pause(self.i_pipeline)
        HSI_MOSAIC.Stop(self.i_pipeline)
        HSI_COMMON.DeallocateCube(self.i_cube)
        HSI_COMMON.DeallocateFrame(self.i_frame)

def main(args=None):
    rclpy.init(args=args)
    data_cubes_processor = DataCubesGenerator()
    try:
        # Two threads: one for the timer/service (default callback group), one for
        # the RGB subscription, so RGB frames are received during acquisition.
        executor = MultiThreadedExecutor(num_threads=2)
        executor.add_node(data_cubes_processor)
        executor.spin()
    finally:
        data_cubes_processor.shutdown()
        data_cubes_processor.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()