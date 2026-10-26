import os
import array
import numpy as np
from collections import deque
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from hyper_drive_interfaces.msg import MultipleDataCubes, DataCube
from spectrometer_interfaces.msg import Spectra

class LightMeasure(Node):
    def __init__(self):
        super().__init__('light_measure')

        #processed spectra values (set by spectra_callback)
        self.S_raw_ximea = None
        self.S_raw_imec = None

        #indices of the live spectrum nearest each camera band (set on first spectra message)
        self.ximea_wavelengths_index = None
        self.imec_wavelengths_index = None

        #recent spectra as (stamp_ns, S_raw_ximea, S_raw_imec), about 2 s at 20 Hz, so
        #each cube can be paired with the spectrum measured closest to its capture time
        self.spectra_buffer = deque(maxlen=40)
        self.spectra_clock_warned = False

        #band centres are checked against the incoming cubes once, on the first message
        self.bands_checked = False

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

        #raw data
        # White reference
        self.C_white_ximea = np.load(os.path.join(npy_path, 'vnir_white_ref.npy')).astype(np.float32).flatten()
        self.C_white_imec = np.load(os.path.join(npy_path, 'swir_white_ref.npy')).astype(np.float32).flatten()
        self.S_white_spectra = np.load(os.path.join(npy_path, 'point_spectra_white_ref.npy')).astype(np.float32).flatten()

        # Dark reference
        self.C_dark_ximea = np.load(os.path.join(npy_path, 'vnir_dark_ref.npy')).astype(np.float32).flatten()
        self.C_dark_imec = np.load(os.path.join(npy_path, 'swir_dark_ref.npy')).astype(np.float32).flatten()
        self.S_dark_spectra = np.array([915.0, 879.0, 917.0, 903.0, 905.0, 927.0, 887.0, 902.0, 927.0, 903.0, 927.0, 903.0, 924.0, 923.0, 887.0, 935.0, 898.0, 932.0, 907.0, 930.0, 882.0, 905.0, 929.0, 914.0, 900.0, 925.0, 902.0, 910.0, 933.0, 928.0, 942.0, 905.0, 909.0, 886.0, 905.0, 881.0, 934.0, 890.0, 905.0, 910.0, 890.0, 912.0, 913.0, 922.0, 929.0, 904.0, 928.0, 915.0, 901.0, 915.0, 893.0, 920.0, 918.0, 907.0, 923.0, 907.0, 901.0, 885.0, 918.0, 891.0, 903.0, 903.0, 918.0, 893.0, 882.0, 899.0, 898.0, 900.0, 914.0, 888.0, 879.0, 909.0, 896.0, 885.0, 881.0, 894.0, 906.0, 896.0, 906.0, 906.0, 908.0, 884.0, 896.0, 913.0, 920.0, 884.0, 913.0, 901.0, 894.0, 916.0, 917.0, 907.0, 911.0, 908.0, 900.0, 907.0, 886.0, 903.0, 877.0, 896.0, 894.0, 880.0, 879.0, 903.0, 897.0, 868.0, 908.0, 882.0, 894.0, 883.0, 881.0, 896.0, 881.0, 864.0, 891.0, 875.0, 884.0, 867.0, 888.0, 891.0, 883.0, 893.0, 895.0, 901.0, 906.0, 878.0, 870.0, 858.0, 906.0, 900.0, 893.0, 893.0, 905.0, 892.0, 877.0, 899.0, 875.0, 867.0, 904.0, 883.0, 875.0, 863.0, 863.0, 896.0, 879.0, 863.0, 890.0, 923.0, 885.0, 883.0, 886.0, 876.0, 890.0, 895.0, 851.0, 880.0, 881.0, 869.0, 879.0, 879.0, 881.0, 891.0, 871.0, 866.0, 863.0, 899.0, 886.0, 895.0, 900.0, 882.0, 887.0, 889.0, 890.0, 865.0, 893.0, 911.0, 886.0, 868.0, 891.0, 882.0, 887.0, 881.0, 880.0, 879.0, 3529.0, 2400.0, 2254.0, 3798.0, 1732.0, 1623.0, 3441.0, 3612.0, 1893.0, 2749.0, 4119.0, 1243.0, 3024.0, 1914.0, 2927.0, 2422.0, 3687.0, 1449.0, 3228.0, 2562.0, 2337.0, 2914.0, 2843.0, 2664.0, 1904.0, 1882.0, 4240.0, 1662.0, 2988.0, 2736.0, 2825.0, 1753.0, 2632.0, 2976.0, 1388.0, 1683.0, 3227.0, 1256.0, 2609.0, 3972.0, 2570.0, 1734.0, 3853.0, 2542.0, 2928.0, 2516.0, 3188.0, 2631.0, 2696.0, 1636.0, 2841.0, 3072.0, 2986.0, 2293.0, 1052.0, 3395.0, 3388.0, 4060.0, 2203.0, 3528.0, 2555.0, 2440.0, 2328.0, 3630.0, 2240.0, 3646.0, 1748.0, 2677.0, 1756.0, 2128.0, 3469.0, 2736.0, 3335.0, 3793.0, 1924.0, 2762.0, 2269.0, 1982.0, 3367.0, 1041.0, 3933.0, 2383.0, 2449.0, 2322.0, 3467.0, 2190.0, 2678.0, 3003.0, 2380.0, 2386.0, 2085.0, 3664.0, 3435.0, 1321.0, 2724.0, 2674.0, 3417.0, 2579.0, 1771.0, 3049.0, 1805.0, 1814.0, 1903.0, 3862.0, 1631.0, 3238.0, 2053.0, 3458.0, 3092.0, 2282.0, 2808.0, 1210.0, 1973.0, 3092.0, 2840.0, 3256.0, 2000.0, 2391.0, 1641.0, 3656.0, 2513.0], dtype=np.float32)

        # Lambdas
        self.spec_lamba = np.load(os.path.join(npy_path, 'spec_lamba.npy')).flatten()
        self.static_wavelengths_ximea = np.load(os.path.join(npy_path, 'ximea_lamba.npy')).flatten()
        self.static_wavelengths_imec = np.load(os.path.join(npy_path, 'imec_lamba.npy')).flatten()

        #integration times (ms)
        self.C_integ_dark_ximea = 10.0
        self.C_integ_white_ximea = 10.0
        self.C_integ_raw_ximea = 10.0

        self.C_integ_dark_imec = 60.0
        self.C_integ_white_imec = 60.0
        self.C_integ_raw_imec = 60.0

        #constants
        self.C_norm = 1
        self.S_norm = 100000

        #print min/max of each cube every frame (costs a few ms per frame)
        self.print_stats = True

        #C_ref denominators: (C_white * CI_raw/CI_white - C_dark * CI_raw/CI_dark) / C_norm
        #these do not change between frames, so they are calculated once here
        self.C_den_ximea = ((self.C_white_ximea * (self.C_integ_raw_ximea/self.C_integ_white_ximea)) - (self.C_dark_ximea * (self.C_integ_raw_ximea/self.C_integ_dark_ximea))) / self.C_norm
        self.C_den_imec = ((self.C_white_imec * (self.C_integ_raw_imec/self.C_integ_white_imec)) - (self.C_dark_imec * (self.C_integ_raw_imec/self.C_integ_dark_imec))) / self.C_norm

        #pixels where white <= dark (dead pixels or a contaminated white reference) are output as 0
        self.C_valid_ximea = self.C_den_ximea > 0
        self.C_valid_imec = self.C_den_imec > 0

        #find wavelength values in the stored dark/white spectra closest to ideal/static wavelength vals for ximea
        ximea_spec_lamba = []
        for i in self.static_wavelengths_ximea:
            ximea_spec_lamba.append(np.argmin(np.abs(self.spec_lamba-i)))

        #find wavelength values in the stored dark/white spectra closest to ideal/static wavelength vals for imec
        imec_spec_lamba = []
        for i in self.static_wavelengths_imec:
            imec_spec_lamba.append(np.argmin(np.abs(self.spec_lamba-i)))

        #dark and white spectra at the camera band wavelengths (constant)
        self.S_dark_ximea = self.S_dark_spectra[ximea_spec_lamba]
        self.S_dark_imec = self.S_dark_spectra[imec_spec_lamba]
        self.S_white_ximea = self.S_white_spectra[ximea_spec_lamba]
        self.S_white_imec = self.S_white_spectra[imec_spec_lamba]

        #S_ref denominators: (S_white - S_dark), constant
        self.S_den_ximea = np.subtract(self.S_white_ximea, self.S_dark_ximea)
        self.S_den_imec = np.subtract(self.S_white_imec, self.S_dark_imec)

    def spectra_callback(self, msg):
        data = np.array(msg.data, dtype=np.float32)

        #find corresponding wavelength values closest to ideal/static wavelength vals.
        #the spectrometer's wavelength axis does not change, so this only runs on the first message
        if self.ximea_wavelengths_index is None:
            wavelengths = np.array(msg.wavelengths)

            #ximea
            self.ximea_wavelengths_index = []
            for i in self.static_wavelengths_ximea:
                self.ximea_wavelengths_index.append(np.argmin(np.abs(wavelengths-i)))

            #imec
            self.imec_wavelengths_index = []
            for i in self.static_wavelengths_imec:
                self.imec_wavelengths_index.append(np.argmin(np.abs(wavelengths-i)))

        self.S_raw_ximea = data[self.ximea_wavelengths_index]
        self.S_raw_imec = data[self.imec_wavelengths_index]

        #measurement time of this spectrum, on the same clock as the cube stamps.
        #if the spectrometer's header stamp is unset or on another clock, use the
        #time it was received instead
        receive_ns = self.get_clock().now().nanoseconds
        stamp = self.stamp_ns(msg.header.stamp)
        if abs(stamp - receive_ns) > 1_000_000_000:
            if not self.spectra_clock_warned:
                self.get_logger().warn(
                    f'Spectra header stamps are {(stamp - receive_ns) / 1e9:+.1f} s from ROS time '
                    f'(unset or another clock?). Matching spectra by receive time instead.')
                self.spectra_clock_warned = True
            stamp = receive_ns
        self.spectra_buffer.append((stamp, self.S_raw_ximea, self.S_raw_imec))

    @staticmethod
    def stamp_ns(stamp) -> int:
        return stamp.sec * 1_000_000_000 + stamp.nanosec

    def nearest_spectrum(self, target_ns):
        '''
        Return the buffered spectrum measured closest to target_ns, and its offset
        from target_ns in milliseconds.
        '''
        spectra = list(self.spectra_buffer)
        stamp, S_raw_ximea, S_raw_imec = min(spectra, key=lambda sp: abs(sp[0] - target_ns))
        return S_raw_ximea, S_raw_imec, (stamp - target_ns) / 1e6

    def check_band_centres(self, msg):
        '''
        Warn once if the band centres in the incoming cubes differ from the
        ximea_lamba / imec_lamba files used to sample the spectrometer.
        '''
        self.bands_checked = True
        for name, cube, static in (('ximea', msg.cubes[0], self.static_wavelengths_ximea),
                                   ('imec', msg.cubes[1], self.static_wavelengths_imec)):
            published = np.array(cube.central_wavelengths, dtype=np.float64)
            if published.size != static.size:
                self.get_logger().warn(f'{name}: cubes report {published.size} band centres but '
                                       f'{name}_lamba.npy has {static.size}')
            elif np.max(np.abs(published - static)) > 0.5:
                self.get_logger().warn(f'{name}: cube band centres differ from {name}_lamba.npy by up to '
                                       f'{np.max(np.abs(published - static)):.2f} nm; regenerate the .npy')

    def cubes_callback(self, msg):
        '''
        This references Technical Note Ambient Light Sensor documents

        C_raw: a raw measurement together with the integration time CI_raw
        C_white: a white reference measurement together with the integration time CI_white
        C_dark: a dark reference measurement together with the integration time CI_dark

        C_ref = (C_raw - C_dark) / (C_white * CI_raw/CI_white - C_dark * CI_raw/CI_dark) * C_norm

        S_raw: raw spectral data
        S_dark: dark spectral data
        S_white: white spectral data

        S_ref = (S_raw - S_dark) / (S_white - S_dark) * S_norm

        C_ref_correct = C_ref / S_ref   (reflectance, corrected for ambient light)
        '''
        #wait until the first spectrum has arrived
        if self.S_raw_ximea is None:
            self.get_logger().warn('Waiting for /combined_spectra before correcting cubes...', throttle_duration_sec=5.0)
            return

        if not self.bands_checked:
            self.check_band_centres(msg)

        raw_ximea = np.frombuffer(msg.cubes[0].data, dtype=np.float32)
        raw_imec = np.frombuffer(msg.cubes[1].data, dtype=np.float32)

        #spectrum measured closest to each camera's capture time
        S_raw_ximea, _, spec_offset_ximea = self.nearest_spectrum(self.stamp_ns(msg.cubes[0].header.stamp))
        _, S_raw_imec, spec_offset_imec = self.nearest_spectrum(self.stamp_ns(msg.cubes[1].header.stamp))

        #the camera references must match the live cubes element for element
        if raw_ximea.size != self.C_den_ximea.size or raw_imec.size != self.C_den_imec.size:
            self.get_logger().error(
                f'Cube size does not match the camera references (ximea {raw_ximea.size} vs {self.C_den_ximea.size}, '
                f'imec {raw_imec.size} vs {self.C_den_imec.size}). Re-capture the references.', throttle_duration_sec=5.0)
            return

        #calculating S_ref_ximea
        S_ref_ximea = np.divide(np.subtract(S_raw_ximea, self.S_dark_ximea), self.S_den_ximea, out=np.zeros_like(self.S_den_ximea), where=self.S_den_ximea!=0) * self.S_norm

        #calculating S_ref_imec
        S_ref_imec = np.divide(np.subtract(S_raw_imec, self.S_dark_imec), self.S_den_imec, out=np.zeros_like(self.S_den_imec), where=self.S_den_imec!=0) * self.S_norm

        #calculating C_ref for ximea
        C_ref_ximea = np.divide(np.subtract(raw_ximea, self.C_dark_ximea), self.C_den_ximea, out=np.zeros_like(self.C_den_ximea), where=self.C_valid_ximea)
        C_ref_ximea = np.reshape(C_ref_ximea, (msg.cubes[0].height, msg.cubes[0].width, msg.cubes[0].lam))
        C_ref_correct_ximea = np.divide(C_ref_ximea, S_ref_ximea, out=np.zeros_like(C_ref_ximea), where=S_ref_ximea!=0)

        #calculating C_ref for imec
        C_ref_imec = np.divide(np.subtract(raw_imec, self.C_dark_imec), self.C_den_imec, out=np.zeros_like(self.C_den_imec), where=self.C_valid_imec)
        C_ref_imec = np.reshape(C_ref_imec, (msg.cubes[1].height, msg.cubes[1].width, msg.cubes[1].lam))
        C_ref_correct_imec = np.divide(C_ref_imec, S_ref_imec, out=np.zeros_like(C_ref_imec), where=S_ref_imec!=0)

        #max and min values of S_ref and of the data cubes before and after correction
        if self.print_stats:
            print(f'S_ref_ximea - Max: {np.max(S_ref_ximea)} Min: {np.min(S_ref_ximea)}')
            print(f'S_ref_imec - Max: {np.max(S_ref_imec)} Min: {np.min(S_ref_imec)}')
            print(f'Raw ximea - Max: {np.max(raw_ximea)} Min: {np.min(raw_ximea)}')
            print(f'Corrected ximea - Max: {np.max(C_ref_correct_ximea)} Min: {np.min(C_ref_correct_ximea)}')
            print(f'Raw imec - Max: {np.max(raw_imec)} Min: {np.min(raw_imec)}')
            print(f'Corrected imec - Max: {np.max(C_ref_correct_imec)} Min: {np.min(C_ref_correct_imec)}')

        #timing: how far each spectrum is from its cube, and how old the cubes are
        #by the time they have been corrected
        now_ns = self.get_clock().now().nanoseconds
        age_ms = (now_ns - self.stamp_ns(msg.cubes[0].header.stamp)) / 1e6
        self.get_logger().info(
            f'Sync: SPEC-XIMEA {spec_offset_ximea:+.1f} ms, SPEC-IMEC {spec_offset_imec:+.1f} ms | '
            f'XIMEA capture to corrected: {age_ms:.0f} ms')

        #pass values to publish function
        self.publish_cube(C_ref_correct_ximea, C_ref_correct_imec, msg.cubes[0], msg.cubes[1], msg.im)

    def publish_cube(self, ximea_cube: np.ndarray, imec_cube: np.ndarray, ximea_msg: DataCube, imec_msg: DataCube, rgb_img):
        '''
        Publish hyperspectral datacubes
        '''

        # Mark that we've received a new cube
        ros_ximea = DataCube()
        ros_imec = DataCube()
        ros_cubes = MultipleDataCubes()

        #ximea DataCube (header keeps the camera's capture time from synchronous_cubes)
        ros_ximea.header = ximea_msg.header
        np.nan_to_num(ximea_cube, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
        ros_ximea.data = array.array('f', ximea_cube.tobytes())
        ros_ximea.height, ros_ximea.width, ros_ximea.lam = tuple(ximea_cube.shape)
        ros_ximea.qe = ximea_msg.qe
        ros_ximea.fwhm_nm = ximea_msg.fwhm_nm
        ros_ximea.central_wavelengths = ximea_msg.central_wavelengths

        #imec DataCube
        ros_imec.header = imec_msg.header
        np.nan_to_num(imec_cube, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
        ros_imec.data = array.array('f', imec_cube.tobytes())
        ros_imec.height, ros_imec.width, ros_imec.lam = tuple(imec_cube.shape)
        ros_imec.qe = imec_msg.qe
        ros_imec.fwhm_nm = imec_msg.fwhm_nm
        ros_imec.central_wavelengths = imec_msg.central_wavelengths

        #combined cubes data message (MultipleDataCubes msg)
        ros_cubes.cubes = [ros_ximea, ros_imec]

        #RGB frame that synchronous_cubes paired with these cubes
        ros_cubes.im = rgb_img

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
