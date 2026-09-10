import os
import array
import numpy as np
import matplotlib.pyplot as plt
import rclpy
from rclpy.node import Node
from std_msgs.msg import Header
from ament_index_python.packages import get_package_share_directory
from hyper_drive_interfaces.msg import MultipleDataCubes, DataCube
from spectrometer_interfaces.msg import Spectra
#from spectrometer_drivers.msg import Spectra

class LightMeasure(Node):
    def __init__(self):
        super().__init__('light_measure')

        #processed spectra values
        self.S_raw_ximea = 0
        self.S_raw_imec = 0
        
        self.S_dark_ximea = 0
        self.S_dark_imec = 0

        self.S_white_ximea = 0
        self.S_white_imec = 0


        # Subscriptions
        self.cubes_sub = self.create_subscription(
            MultipleDataCubes,
            '/synchronous_cubes',
            self.cubes_callback,
            10
        )

        self.spectra_sub = self.create_subscription(
            Spectra,
            '/combined_spectra',
            self.spectra_callback,
            10
        )


        # Publisher
        self.pub_corrected_cubes = self.create_publisher(MultipleDataCubes, 'corrected_cubes', 10)

        # Load reference data
        pkg_path = get_package_share_directory('hyper_drive')
        npy_path = os.path.join(pkg_path, 'bag_files', 'numpy_files')

        # White reference (point spectrometer only).
        # NOTE: camera white/dark references (C_ref calibration) have been
        # removed -- the XIMEA and IMEC cubes are flat-fielded upstream by the
        # vendor pipeline (dark reference + nonuniformity from the context
        # files), so this node only applies the ambient-illumination correction.
        self.S_white_spectra = np.load(os.path.join(npy_path, 'point_spectra_white_ref.npy')).flatten()

        # Dark reference (point spectrometer only)
        #self.S_dark_spectra = np.load(os.path.join(self.ros_pack.get_path('hyper_drive'), 'Bag_Files', 'Numpy_Files', 'dark_spectra.npy')).flatten()
        self.S_dark_spectra = np.array([915.0, 879.0, 917.0, 903.0, 905.0, 927.0, 887.0, 902.0, 927.0, 903.0, 927.0, 903.0, 924.0, 923.0, 887.0, 935.0, 898.0, 932.0, 907.0, 930.0, 882.0, 905.0, 929.0, 914.0, 900.0, 925.0, 902.0, 910.0, 933.0, 928.0, 942.0, 905.0, 909.0, 886.0, 905.0, 881.0, 934.0, 890.0, 905.0, 910.0, 890.0, 912.0, 913.0, 922.0, 929.0, 904.0, 928.0, 915.0, 901.0, 915.0, 893.0, 920.0, 918.0, 907.0, 923.0, 907.0, 901.0, 885.0, 918.0, 891.0, 903.0, 903.0, 918.0, 893.0, 882.0, 899.0, 898.0, 900.0, 914.0, 888.0, 879.0, 909.0, 896.0, 885.0, 881.0, 894.0, 906.0, 896.0, 906.0, 906.0, 908.0, 884.0, 896.0, 913.0, 920.0, 884.0, 913.0, 901.0, 894.0, 916.0, 917.0, 907.0, 911.0, 908.0, 900.0, 907.0, 886.0, 903.0, 877.0, 896.0, 894.0, 880.0, 879.0, 903.0, 897.0, 868.0, 908.0, 882.0, 894.0, 883.0, 881.0, 896.0, 881.0, 864.0, 891.0, 875.0, 884.0, 867.0, 888.0, 891.0, 883.0, 893.0, 895.0, 901.0, 906.0, 878.0, 870.0, 858.0, 906.0, 900.0, 893.0, 893.0, 905.0, 892.0, 877.0, 899.0, 875.0, 867.0, 904.0, 883.0, 875.0, 863.0, 863.0, 896.0, 879.0, 863.0, 890.0, 923.0, 885.0, 883.0, 886.0, 876.0, 890.0, 895.0, 851.0, 880.0, 881.0, 869.0, 879.0, 879.0, 881.0, 891.0, 871.0, 866.0, 863.0, 899.0, 886.0, 895.0, 900.0, 882.0, 887.0, 889.0, 890.0, 865.0, 893.0, 911.0, 886.0, 868.0, 891.0, 882.0, 887.0, 881.0, 880.0, 879.0, 3529.0, 2400.0, 2254.0, 3798.0, 1732.0, 1623.0, 3441.0, 3612.0, 1893.0, 2749.0, 4119.0, 1243.0, 3024.0, 1914.0, 2927.0, 2422.0, 3687.0, 1449.0, 3228.0, 2562.0, 2337.0, 2914.0, 2843.0, 2664.0, 1904.0, 1882.0, 4240.0, 1662.0, 2988.0, 2736.0, 2825.0, 1753.0, 2632.0, 2976.0, 1388.0, 1683.0, 3227.0, 1256.0, 2609.0, 3972.0, 2570.0, 1734.0, 3853.0, 2542.0, 2928.0, 2516.0, 3188.0, 2631.0, 2696.0, 1636.0, 2841.0, 3072.0, 2986.0, 2293.0, 1052.0, 3395.0, 3388.0, 4060.0, 2203.0, 3528.0, 2555.0, 2440.0, 2328.0, 3630.0, 2240.0, 3646.0, 1748.0, 2677.0, 1756.0, 2128.0, 3469.0, 2736.0, 3335.0, 3793.0, 1924.0, 2762.0, 2269.0, 1982.0, 3367.0, 1041.0, 3933.0, 2383.0, 2449.0, 2322.0, 3467.0, 2190.0, 2678.0, 3003.0, 2380.0, 2386.0, 2085.0, 3664.0, 3435.0, 1321.0, 2724.0, 2674.0, 3417.0, 2579.0, 1771.0, 3049.0, 1805.0, 1814.0, 1903.0, 3862.0, 1631.0, 3238.0, 2053.0, 3458.0, 3092.0, 2282.0, 2808.0, 1210.0, 1973.0, 3092.0, 2840.0, 3256.0, 2000.0, 2391.0, 1641.0, 3656.0, 2513.0])
        
        # Lambdas
        self.spec_lamba = np.load(os.path.join(npy_path, 'spec_lamba.npy')).flatten()
        self.static_wavelengths_ximea = np.load(os.path.join(npy_path, 'ximea_lamba.npy')).flatten()
        self.static_wavelengths_imec = np.load(os.path.join(npy_path, 'imec_lamba.npy')).flatten()

        #constants
        self.S_norm = 100000

    def spectra_callback(self, msg):
        data = np.array(msg.data)
        wavelengths = list(msg.wavelengths)
        
        dark_data = np.array(self.S_dark_spectra)
        white_data = np.array(self.S_white_spectra)
        spec_lamb = list(self.spec_lamba)

        ximea_wavelengths_index = []
        imec_wavelengths_index = []
        ximea_spec_lamba = []
        imec_spec_lamba = []


        '''
        np.argmin(np.abs(np.array(wavelengths)-i))
        '''
        #find corresponding wavelength values closest to ideal/static wavelength vals ximea 
        for i in self.static_wavelengths_ximea:
            ximea_wavelengths_index.append(np.argmin(np.abs(np.array(wavelengths)-i)))

        #find corresponding wavelength values closest to ideal/static wavelength vals for imec
        #in order to find corresponding index in data
        for i in self.static_wavelengths_imec:
            imec_wavelengths_index.append(np.argmin(np.abs(np.array(wavelengths)-i)))

        #find corresponding wavelength values closest to ideal/static wavelength vals for dark 
        #and white S_ximea, in order to find corresponding index in data
        for i in self.static_wavelengths_ximea:
            ximea_spec_lamba.append(np.argmin(np.abs(np.array(spec_lamb)-i)))

        #find corresponding wavelength values closest to ideal/static wavelength vals for dark 
        #and white S_ximea, in order to find corresponding index in data
        for i in self.static_wavelengths_imec:
            imec_spec_lamba.append(np.argmin(np.abs(np.array(spec_lamb)-i)))        
                
        # We can probably cut the list comprehensions with numpy # TODO
        self.S_raw_ximea = data[ximea_wavelengths_index]
        self.S_raw_imec = data[imec_wavelengths_index]
        self.S_dark_ximea = dark_data[ximea_spec_lamba]
        self.S_dark_imec = dark_data[imec_spec_lamba]
        self.S_white_ximea = white_data[ximea_spec_lamba]
        self.S_white_imec = white_data[imec_spec_lamba]

        # Debug plotting of the S references. Disabled by default: at ~20 Hz
        # this accumulated lines on one figure every callback (a memory/CPU
        # leak) and was never shown. Set self.debug_plot = True to inspect.
        if getattr(self, 'debug_plot', False):
            plt.clf()
            plt.plot(self.static_wavelengths_ximea, self.S_dark_ximea, label="S_dark_ximea")
            plt.plot(self.static_wavelengths_ximea, self.S_white_ximea, label="S_white_ximea")
            plt.plot(self.static_wavelengths_imec, self.S_dark_imec, label="S_dark_imec")
            plt.plot(self.static_wavelengths_imec, self.S_white_imec, label="S_white_imec")
            plt.legend()
            plt.pause(0.001)

    def cubes_callback(self, msg):
        '''
        This references Technical Note Ambient Light Sensor documents.

        Camera C_ref (white/dark) calibration is intentionally NOT done here:
        the XIMEA and IMEC cubes on /synchronous_cubes are already flat-fielded
        upstream by the vendor pipeline (dark reference + nonuniformity from the
        context files). This node applies only the ambient-illumination
        correction, dividing each already-corrected cube by S_ref:

        S_raw:   raw spectral data (point spectrometer, per camera band)
        S_dark:  dark spectral data
        S_white: white spectral data

        S_ref = (S_raw - S_dark) / (S_white - S_dark) * S_norm
        corrected_cube = raw_cube / S_ref     (per band, guarded against S_ref==0)
        '''
        # Raw cubes as float arrays (already vendor-corrected upstream)
        raw_ximea = np.asarray(msg.cubes[0].data, dtype=np.float64)
        raw_imec = np.asarray(msg.cubes[1].data, dtype=np.float64)

        # --- S_ref: ambient illumination reference, per camera band ---
        den_ximea = np.subtract(self.S_white_ximea, self.S_dark_ximea)
        den_imec = np.subtract(self.S_white_imec, self.S_dark_imec)

        S_ref_ximea = np.divide(
            np.subtract(self.S_raw_ximea, self.S_dark_ximea), den_ximea,
            out=np.zeros_like(np.asarray(den_ximea, dtype=np.float64)),
            where=den_ximea != 0,
        ) * self.S_norm

        S_ref_imec = np.divide(
            np.subtract(self.S_raw_imec, self.S_dark_imec), den_imec,
            out=np.zeros_like(np.asarray(den_imec, dtype=np.float64)),
            where=den_imec != 0,
        ) * self.S_norm

        print(f'S_ref_ximea - Max: {np.max(S_ref_ximea)} Min: {np.min(S_ref_ximea)}')
        print(f'S_ref_imec - Max: {np.max(S_ref_imec)} Min: {np.min(S_ref_imec)}')

        # --- Reshape raw cubes to (width, height, lam) ---
        ximea_cube = np.reshape(raw_ximea, (msg.cubes[0].width, msg.cubes[0].height, msg.cubes[0].lam))
        imec_cube = np.reshape(raw_imec, (msg.cubes[1].width, msg.cubes[1].height, msg.cubes[1].lam))

        # --- Ambient correction: divide each band by its S_ref (guarded) ---
        corrected_ximea = np.divide(
            ximea_cube, S_ref_ximea,
            out=np.zeros_like(ximea_cube),
            where=S_ref_ximea != 0,
        )
        corrected_imec = np.divide(
            imec_cube, S_ref_imec,
            out=np.zeros_like(imec_cube),
            where=S_ref_imec != 0,
        )

        #what is the max and min value in the data cube before and after correction?
        print(f'Raw ximea - Max: {np.max(raw_ximea)} Min: {np.min(raw_ximea)}')
        print(f'Corrected ximea - Max: {np.max(corrected_ximea)} Min: {np.min(corrected_ximea)}')
        print(f'Raw imec - Max: {np.max(raw_imec)} Min: {np.min(raw_imec)}')
        print(f'Corrected imec - Max: {np.max(corrected_imec)} Min: {np.min(corrected_imec)}')

        #pass values to publish function
        self.publish_cube(corrected_ximea, corrected_imec, msg.cubes[0], msg.cubes[1])

    def publish_cube(self, ximea_cube: np.ndarray, imec_cube: np.ndarray, ximea_msg: MultipleDataCubes, imec_msg: MultipleDataCubes):
        '''
        Publish hyperspectral datacubes
        '''

        # Mark that we've received a new cube
        ros_ximea = DataCube()
        ros_imec = DataCube()
        ros_cubes = MultipleDataCubes()

        # Create header
        h = Header()
        h.stamp = self.get_clock().now().to_msg()

        #ximea DataCube
        ros_ximea.header = h
        # DataCube.data (float32[]) must be array.array('f'), NOT a numpy float32
        # ndarray -- the message setter rejects ndarrays (np.float32 scalars are
        # not Python floats). Matches how synchronous_cubes publishes.
        clean_ximea = np.nan_to_num(ximea_cube.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        ros_ximea.data = array.array('f', np.ascontiguousarray(clean_ximea, dtype=np.float32).tobytes())
        ros_ximea.width, ros_ximea.height, ros_ximea.lam = tuple(ximea_cube.shape)
        ros_ximea.qe = ximea_msg.qe 
        ros_ximea.fwhm_nm = ximea_msg.fwhm_nm
        ros_ximea.central_wavelengths = ximea_msg.central_wavelengths

        #imec DataCube
        ros_imec.header = h
        clean_imec = np.nan_to_num(imec_cube.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        ros_imec.data = array.array('f', np.ascontiguousarray(clean_imec, dtype=np.float32).tobytes())
        ros_imec.width, ros_imec.height, ros_imec.lam = tuple(imec_cube.shape)
        ros_imec.qe = imec_msg.qe
        ros_imec.fwhm_nm = imec_msg.fwhm_nm
        ros_imec.central_wavelengths = imec_msg.central_wavelengths

        #combined cubes data message (MultipleDataCubes msg)
        ros_cubes.cubes = [ros_ximea, ros_imec]

        #publish
        self.pub_corrected_cubes.publish(ros_cubes)

    def shutdown(self):
        print('SHUTTING DOWN')
        return

def main(args=None):
    rclpy.init(args=args)
    light_measure = LightMeasure()
    try:
        rclpy.spin(light_measure)
    finally:
        light_measure.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
