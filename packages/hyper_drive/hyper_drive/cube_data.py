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
import time

# Messages
from std_msgs.msg import Header
from sensor_msgs.msg import Image
from hyper_drive_interfaces.msg import DataCube
from hyper_drive_interfaces.srv import AdjustParam

# ROS Imports
import rclpy
from rclpy.node import Node
from rclpy.logging import get_logging_directory
from ament_index_python.packages import get_package_share_directory
import ros2_numpy

### Set parameters to find the HSI mosaic binaries
#os.environ['PATH'] += os.pathsep + r'/opt/imec/hsi-mosaic/bin'
# Also add them to the path
sys.path.append('/opt/imec/hsi-mosaic/python_apis')
# Import IMEC specific libraries
import hsi_common as HSI_COMMON
import hsi_camera as HSI_CAMERA
import hsi_mosaic as HSI_MOSAIC

class Publisher(Node):

    def __init__(self):
        super().__init__('publisher')

        # Setup logging
        log_dir = get_logging_directory()
        log_dir_str = str(log_dir)
        self.get_logger().info(f'Logging camera info to {log_dir_str}')
        HSI_COMMON.InitializeLogger(log_dir_str, HSI_COMMON.LoggerVerbosity.LV_INFO)
        self.get_logger().info('Loading Context ...')

        # Setup callback for data
        self.package_share_dir = get_package_share_directory('hyper_drive')
        self.lock = threading.Lock()

        # Setup parameters
        self.declare_parameter('camera_model', '')
        self.model = self.get_parameter('camera_model').get_parameter_value().string_value
        
        self.declare_parameter('frame_rate', 60)
        self.frame_rate = self.get_parameter('frame_rate').get_parameter_value().integer_value

        self.declare_parameter('integration_time', 10)
        self.integration_time = self.get_parameter('integration_time').get_parameter_value().integer_value

        # for troubleshooting (remove later)
        self.get_logger().info(f'Camera Model: {self.model}')
        self.get_logger().info(f'Camera Frame Rate: {self.frame_rate}')
        self.get_logger().info(f'Camera Integration Time: {self.integration_time}')

        # Setup service
        self.param_server = self.create_service(AdjustParam, 'adjust_param', self.adjust_param_callback)

        # Create publisher to send datacubes on
        self.pub_raw = self.create_publisher(Image, 'raw_data', 10)
        self.pub_cube = self.create_publisher(DataCube, 'cube_data', 10)

        # Load camera parameters
        self.parse_parameters()

        # Initialize the camera
        self.initialize_camera()

        # Explicitly Allocate based on Output-Data-Format
        data_format = HSI_CAMERA.GetOutputFrameDataFormat(self.device)
        self.frame = HSI_COMMON.AllocateFrame(data_format)

        self.get_logger().info('Camera Output Data Format: {}'.format(data_format))
        self.setup_context()
        self.get_logger().info('Pipeline Started. Getting Cubes.')

        HSI_CAMERA.Start(self.device)
        # Timer callback to run camera
        frame_period = 0.001
        self.timer = self.create_timer(frame_period, self.timer_callback)

    def image_callback(self, msg: Image) -> None:
        self.img = msg

    def initialize_camera(self) -> None:
        # Rate at which to generate composite data cubes
        # Look for connected cameras an choose appropriate model (assumes we only have 1 IMEC and 1 XIMEA)
        if self.model == 'ximea':
            self.integration_range = (0.021000, 999.995000)
            self.dev_list = HSI_CAMERA.EnumerateConnectedDevices(manufacturer=HSI_CAMERA.Manufacturer.EM_XIMEA)
            self.roi = [HSI_COMMON.RegionOfInterest(x=0, y=0, width=2045, height=1085)]

        elif self.model == 'imec':
            self.integration_range = (0.010000, 90)
            self.dev_list = HSI_CAMERA.EnumerateConnectedDevices(manufacturer=HSI_CAMERA.Manufacturer.EM_IMEC)
            self.roi = [HSI_COMMON.RegionOfInterest(x=1, y=1, width=639, height=510)]

        self.get_logger().info('Found number of devices = {}'.format(len(self.dev_list)))

        # Connect to the first available camera of the specified model type
        self.get_logger().info('looking for device:: {}'.format(self.dev_list[0]))
        self.device = HSI_CAMERA.OpenDevice(self.dev_list[0])
        HSI_CAMERA.SetRegionOfInterestArray(self.device, self.roi)
        self.get_logger().info("Region-of-Intereset Set to: {}".format(self.roi))
        self.get_logger().info('Initializing Camera...')
        HSI_CAMERA.Initialize(self.device)
        # Get/Set Camera Configuration Parameters (example)
        self.c_params = HSI_CAMERA.GetConfigurationParameters(self.device)

        self.get_logger().info("C PARAMS>")
        self.get_logger().info(str(self.c_params))

        self.r_params = HSI_CAMERA.GetRuntimeParameters(self.device)
        self.get_logger().info(str(self.r_params))
        # Set the frame rate and exposure time before the camera starts
        # These values can be adjusted later through a callback
        self.r_params.frame_rate_hz = self.frame_rate
        self.r_params.exposure_time_ms = self.integration_time
        # Flip the frame of the IMEC camera to match housing pattern
        if self.model == 'imec':
            self.r_params['flip_vertical'] = False
            self.r_params['flip_horizontal'] = True
        # Set these parameters on the device
        HSI_CAMERA.SetRuntimeParameters(self.device, self.r_params)
        self.get_logger().info("R PARAMS>")
        self.get_logger().info(str(self.r_params))

    def restart_camera(self) -> None:
        '''
        Restart camera in the event there is an error setting the runtime parameters
        '''
        self.get_logger().error('ERROR IN CAMERA MAIN LOOP! Waiting 5 seconds and reinitializing the camera')
        HSI_CAMERA.Pause(self.device)
        HSI_CAMERA.Stop(self.device)
        HSI_CAMERA.CloseDevice(self.device)
        # Sleep 5 seconds
        rclpy.spin_once(self, timeout_sec=5)
        # Restart the camera
        self.initialize_camera()


    def setup_context(self) -> None:
        '''
        Load HSI Context files and prepare to run demosaicing pipeline
        '''
        # ROS2: Get package share directory instead of using rospkg
        package_share_dir = get_package_share_directory('hyper_drive')
        # Build path to config file
        dn_context = os.path.join(package_share_dir,'config',self.model,'context')
        #####################################################################
        version = HSI_MOSAIC.GetAPIVersion()
        self.get_logger().info(f'VERSION :: {version}')
        self.get_logger().info(str(Path(dn_context).absolute()))
        assert Path(dn_context).exists()
        self.my_context = HSI_MOSAIC.LoadContext(dn_context)
        # self.context = self.my_context (throws error: can't set attribute context)
        self.get_logger().info(f'Context = {self.my_context}')
        status = HSI_MOSAIC.ContextGetStatus(self.my_context)
        self.get_logger().info(str(status))
        self.pipeline = HSI_MOSAIC.Create(self.my_context)
        self.get_logger().info(str(self.pipeline))
        self.params = HSI_MOSAIC.GetConfigurationParameters(self.pipeline)
        self.params.spatial_median_filter_enable = False
        self.get_logger().info(f'Configuration Params : {self.params}')
        HSI_MOSAIC.SetConfigurationParameters(self.pipeline, self.params)
        self.get_logger().info('Initializing Pipeline')
        HSI_MOSAIC.Initialize(self.pipeline)

        outputdataformat = HSI_MOSAIC.GetOutputDataFormat(self.pipeline)
        self.get_logger().info(f'Output Data Format = {outputdataformat}')

        self.cube = HSI_COMMON.AllocateCube(outputdataformat)

        self.get_logger().info('Starting Pipeline')
        HSI_MOSAIC.Start(self.pipeline)


    def parse_parameters(self) -> None:
        '''
        Load parameter for camera from manufacturer provided XML file
        for publication in datacube messages
        '''
        # ROS2: Get package share directory instead of using rospkg
        package_share_dir = get_package_share_directory('hyper_drive')
        # Build path to config file
        param_path = os.path.join(package_share_dir, 'config', f'{self.model}.xml')
        # Log the path being used
        self.get_logger().info(f"Loading parameters from: {param_path}")
        with open(param_path, 'r') as f:
            data = f.read()
            Bs_data = BeautifulSoup(data, "xml")
            self.central_wave = []
            self.fwhm = []
            self.QE = []
            for band in Bs_data.find_all("wavelength_nm"):
                self.central_wave.append(float(band.getText()))
            for band in Bs_data.find_all("fwhm_nm"):
                self.fwhm.append(float(band.getText()))
            for band in Bs_data.find_all("QE"):
                self.QE.append(float(band.getText()))
            # Get calibration coefficients
            coefficients = []
            for coefficient in Bs_data.find_all("coefficients"):
                coefficients.append(np.array([float(z) for z in coefficient['values'].split()]))
            self.coefficients = np.array(coefficients)
        
    def adjust_param_callback(self, request, response):
        '''    Listen to user parameter requests    '''     
        frame_time = 1/(request.frame_rate) * 1000    
        self.get_logger().info(f'Incoming message: {request}')
        try:
            # Pause the camera        
            if (self.integration_range[0] < request.integration_time < request.integration_range[1]) & (request.integration_time < frame_time):
                print(f'Exposure time: {request.integration_time} Frame Rate: {request.frame_rate}')
                # Proposing to try 3 steps
                with self.lock:         
                    #Step-1: Set frame rate to a very low value eg. 1 fps            
                    HSI_CAMERA.Pause(self.device)
                    # Get r-params
                    self.r_params = HSI_CAMERA.GetRuntimeParameters(self.device)
                    print(self.r_params)
                    self.r_params.frame_rate_hz = 1            
                    self.get_logger().info(f'Update Runtime Params: {HSI_CAMERA.SetRuntimeParameters(self.device, self.r_params)}')       
                    # #Step-2: Set integration time            
                    self.r_params = HSI_CAMERA.GetRuntimeParameters(self.device)
                    self.r_params.exposure_time_ms = request.integration_time            
                    self.get_logger().info(f'Update Runtime Params: {HSI_CAMERA.SetRuntimeParameters(self.device, self.r_params)}')       
                    # #Step-3: Set frame rate            
                    self.r_params = HSI_CAMERA.GetRuntimeParameters(self.device)
                    self.r_params.frame_rate_hz = request.frame_rate            
                    self.get_logger().info(f'Update Runtime Params: {HSI_CAMERA.SetRuntimeParameters(self.device, self.r_params)}')       
                    HSI_CAMERA.Start(self.device)
                    rclpy.spin_once(Publisher, timeout_sec=0.1)
                    response.success = True
                    return response       
            else:
                self.get_logger().error('INVALID INTEGRATION TIME REQUESTED!')
                HSI_CAMERA.Start(self.device)
        except Exception as e:
            self.get_logger().error(traceback.print_exc())
            self.get_logger().error(str(e))
            self.get_logger().error('Error setting user user parameter!')
            response.success = False
            return response
    

    def publish_raw(self, raw: np.ndarray) -> None:
        '''
        Publish the raw image pulled from the camera photodetector
        '''
        ros_image = ros2_numpy.msgify(Image, raw, encoding="32FC1")
        self.pub_raw.publish(ros_image)

    def undistort(self, cube):
        #criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1)

        imec_K = [[571.0648167, 0, 96.21785],
                  [0, 572.4372833, 77.75815],
                  [0, 0, 1]]
        imec_distort = [-0.715016666666667, 18.2009666666667, -0.003883333333333, -0.002716666666667, -234.22125]

        vimba_K = [[917.8051167, 0, 244.883],
                   [0, 918.8520833, 205.2639333],
                   [0, 0, 1]]
        vimba_distort = [-0.212233333333333, 1.44273333333333, 0.001516666666667, -0.041533333333333, -10.8958666666667]

        ximea_K = [[929.0870667, 0, 193.47025],
                   [0, 928.9873333, 114.0106],
                   [0, 0, 1]]
        ximea_distort = [0.12115, -5.45603333333333, 0.0021, -0.004283333333333, 100.424166666667]
    
        if self.model == 'imec':
            for lam in range(cube.shape[2]):
                undistorted_img = cv2.undistort(cube[:, :, lam], np.matrix(imec_K), np.array(imec_distort))
                cube[:, :, lam] = undistorted_img

        elif self.model == 'ximea':
            for lam in range(cube.shape[2]):
                undistorted_img = cv2.undistort(cube[:, :, lam], np.matrix(ximea_K), np.array(ximea_distort))
                cube[:, :, lam] = undistorted_img

        elif self.model == 'vimba':
            for lam in range(cube.shape[:2]):
                undistorted_img = cv2.undistort(cube[:, :, lam], np.matrix(vimba_K), np.array(vimba_distort))
                cube[:, :, lam] = undistorted_img
        
        self.get_logger().info(f'CUBE SHAPE: {cube.shape}')

    def publish_cube(self, cube: np.ndarray):
        '''
        Publish hyperspectral datacubes
        '''
        t_a = time.time()
        self.undistort(cube)
        # Mark that we've received a new cube
        ros_cube = DataCube()
        # Create header
        h = Header()
        h.stamp = self.get_clock().now().to_msg()
        ros_cube.header = h
        t_b = time.time()
        t0 = time.time()
        ros_cube.data = cube.astype(np.float32).flatten().tolist()
        t1 = time.time()
        self.get_logger().info(
            f'cube flatten={t1-t0:.6f}s'
        )
        t_c = time.time()
        ros_cube.height, ros_cube.width, ros_cube.lam = tuple(cube.shape)
        ros_cube.qe = self.QE
        ros_cube.fwhm_nm = self.fwhm
        ros_cube.central_wavelengths = self.central_wave
        t_d = time.time()
        self.pub_cube.publish(ros_cube)
        t_e = time.time()
        self.get_logger().info(f'Undistort Cube:{t_b-t_a:.3f} convert to message:{t_c-t_b:.3f} metadata:{t_d-t_c:.3f} publish:{t_e-t_d:.3f}')

    
    def timer_callback(self):
        # run central processing loop for camera

        try:
            # Send a software Tigger to the camera and grab the Frame
            # HSI_CAMERA.Trigger(self.device)
            with self.lock:
                t0 = time.time()
                HSI_CAMERA.AcquireFrame(self.device, frame=self.frame)
                t1 = time.time()
                # tmp = HSI_COMMON.FrameAsArray(self.frame) # internally convert frame to numpy array
                # Publish raw image
                # self.publish_raw(tmp)
                HSI_MOSAIC.PushFrame(self.pipeline, self.frame)
                t2 = time.time()
                HSI_MOSAIC.GetCube(self.pipeline, self.cube, timeout_ms=1000)
                t3 = time.time()
                raw = HSI_COMMON.CubeAsArray(self.cube, BSQ=False)
                py_cube = np.empty((168, 211, 9), dtype=np.float32)
                np.copyto(py_cube, raw)
                self.get_logger().info(
                    f"OWNDATA={py_cube.flags.owndata}, "
                    f"WRITEABLE={py_cube.flags.writeable}, "
                    f"ALIGNED={py_cube.flags.aligned}"
                )
                self.get_logger().info(f'Cube dtype: {py_cube.dtype}, shape: {py_cube.shape}, contiguous: {py_cube.flags["C_CONTIGUOUS"]}')
                self.get_logger().info(str(py_cube.flags))

                self.publish_cube(py_cube)
                t4 = time.time()
                self.get_logger().info(f'Acquire:{t1-t0:.3f} Push:{t2-t1:.3f} GetCube:{t3-t2:.3f} Publish:{t4-t3:.3f}')
        except Exception as e:
            self.get_logger().error(traceback.print_exc())
            self.get_logger().error('Exception in main capture loop')
            self.restart_camera()

        test_array = np.ones((168, 211, 9), dtype=np.float32)
        t_test = time.time()
        test_bytes = test_array.tobytes()
        self.get_logger().info(f'Fresh array tobytes: {time.time()-t_test:.4f}s')
            

def main(args=None):
    rclpy.init(args=args)
    publisher = Publisher()
    rclpy.spin(publisher)
    publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()