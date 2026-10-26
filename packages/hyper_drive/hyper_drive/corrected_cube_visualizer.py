#!/usr/bin/env python3

import numpy as np
import cv2

# Messages
from sensor_msgs.msg import Image
from hyper_drive_interfaces.msg import MultipleDataCubes

# ROS Imports
import rclpy
from rclpy.node import Node
import ros2_numpy

# Corrected-cube visualizer.
# Mirror of synchronous_cube_visualizer.py, but subscribes to the ambient-light
# corrected cubes ('corrected_cubes') and publishes under '/visualizer_corrected/...'
# so it can run SIDE BY SIDE with the raw visualizer for comparison.
#
# Display note: normalize_band() does a per-band min-max contrast stretch, so it
# adapts automatically to the reflectance-scale values of the corrected cubes
# (which are NOT raw counts). No fixed scaling assumptions are baked in, so the
# same normalization used for raw cubes works here.
#
# IMPORTANT: this decodes msg_cube.data with np.frombuffer(..., dtype=np.float32),
# which requires the PUBLISHER to serialize data as raw float32 bytes, e.g.
#   ros_cube.data = array.array('f', np.ascontiguousarray(cube, np.float32).tobytes())
# If the correction node instead assigns a numpy array / list to .data, this
# decode will produce garbage. See notes accompanying this file.


class CorrectedCubeVisualizer(Node):
    def __init__(self):
        super().__init__('corrected_cube_visualizer')

        self.ximea_band_pubs = []
        self.imec_band_pubs = []

        # Subscribe to CORRECTED cubes (relative topic; the correction node
        # publishes 'corrected_cubes'). Use a leading slash only if the
        # correction node is in the global namespace.
        self.cubes_sub = self.create_subscription(
            MultipleDataCubes,
            'corrected_cubes',
            self.callback_cubes,
            10
        )

        # False color publishers (namespaced so they don't collide with the raw visualizer)
        self.pub_ximea_false_color = self.create_publisher(Image, '/visualizer_corrected/ximea/false_color', 10)
        self.pub_imec_false_color = self.create_publisher(Image, '/visualizer_corrected/imec/false_color', 10)

        # Band grid publishers
        self.pub_ximea_grid = self.create_publisher(Image, '/visualizer_corrected/ximea/band_grid', 10)
        self.pub_imec_grid = self.create_publisher(Image, '/visualizer_corrected/imec/band_grid', 10)

        self.get_logger().info('Corrected Cube Visualizer started, waiting for data...')

    def normalize_band(self, band: np.ndarray) -> np.ndarray:
        '''
        Contrast stretch a single band to 8-bit.
        Per-band min-max, so it adapts to reflectance-scale corrected data.
        NaN/inf-safe: corrected data can contain non-finite values from divisions.
        '''
        finite = np.isfinite(band)
        if not finite.any():
            return np.zeros(band.shape, dtype=np.uint8)
        band = np.where(finite, band, 0.0)
        band_min = band[finite].min()
        band_max = band[finite].max()
        if band_max == band_min:
            return np.zeros(band.shape, dtype=np.uint8)
        normalized = (band - band_min) / (band_max - band_min) * 255
        normalized = np.clip(normalized, 0, 255)
        return normalized.astype(np.uint8)

    def publish_band(self, band: np.ndarray, pub):
        '''
        Normalize and publish a single band as a grayscale image
        '''
        normalized = self.normalize_band(band)
        rgb = cv2.cvtColor(normalized, cv2.COLOR_GRAY2RGB)
        ros_image = ros2_numpy.msgify(Image, rgb, encoding='rgb8')
        ros_image.header.stamp = self.get_clock().now().to_msg()
        ros_image.header.frame_id = 'camera'
        pub.publish(ros_image)

    def publish_false_color(self, cube: np.ndarray, pub):
        '''
        Map 3 evenly spaced bands to R, G, B for a false color image.
        Same band selection as the raw visualizer (first, middle, last band).
        '''
        num_bands = cube.shape[2]
        r_idx = 0
        g_idx = num_bands // 2
        b_idx = num_bands - 1

        r = self.normalize_band(cube[:, :, r_idx])
        g = self.normalize_band(cube[:, :, g_idx])
        b = self.normalize_band(cube[:, :, b_idx])

        false_color = np.stack([r, g, b], axis=2)
        ros_image = ros2_numpy.msgify(Image, false_color, encoding='rgb8')
        ros_image.header.stamp = self.get_clock().now().to_msg()
        ros_image.header.frame_id = 'camera'
        pub.publish(ros_image)

    def publish_band_grid(self, cube: np.ndarray, pub, label: str):
        '''
        Arrange all bands into a single grid image for overview
        '''
        num_bands = cube.shape[2]
        grid_row = []
        for i in range(num_bands):
            band = self.normalize_band(cube[:, :, i])
            labeled = cv2.putText(
                band.copy(), f'{label}B{i}',
                (5, 20), cv2.FONT_HERSHEY_SIMPLEX,
                0.5, 255, 1
            )
            grid_row.append(labeled)

        grid = np.concatenate(grid_row, axis=1)
        grid_rgb = cv2.cvtColor(grid, cv2.COLOR_GRAY2RGB)
        ros_image = ros2_numpy.msgify(Image, grid_rgb, encoding='rgb8')
        ros_image.header.stamp = self.get_clock().now().to_msg()
        ros_image.header.frame_id = 'camera'
        pub.publish(ros_image)

    def process_cube(self, msg_cube, band_pubs_ref, false_color_pub,
                     grid_pub, label: str):
        '''
        Extract, visualize and publish a single DataCube.
        Decodes .data as raw float32 bytes (see file header note on serialization).
        '''
        cube = np.frombuffer(msg_cube.data, dtype=np.float32).reshape(
            (msg_cube.height, msg_cube.width, msg_cube.lam)
        )

        num_bands = msg_cube.lam

        # Create per-band publishers if number of bands has changed
        if len(band_pubs_ref) != num_bands:
            band_pubs_ref.clear()
            for i in range(num_bands):
                pub = self.create_publisher(
                    Image,
                    f'/visualizer_corrected/{label.lower()}/band_{i}',
                    10
                )
                band_pubs_ref.append(pub)
            self.get_logger().info(f'{label}: Created publishers for {num_bands} bands')

        # Publish band 6 (matches the raw visualizer's single-band choice)
        band_to_show = min(6, num_bands - 1)
        self.publish_band(cube[:, :, band_to_show], band_pubs_ref[band_to_show])

        # Publish false color
        self.publish_false_color(cube, false_color_pub)

        # Use nan-aware stats for logging since corrected data may contain non-finite values
        finite = cube[np.isfinite(cube)]
        if finite.size:
            self.get_logger().info(
                f'{label} | bands: {num_bands} | '
                f'min: {finite.min():.3f} max: {finite.max():.3f} mean: {finite.mean():.3f}'
            )
        else:
            self.get_logger().warn(f'{label} | bands: {num_bands} | all values non-finite')

    def callback_cubes(self, msg: MultipleDataCubes):
        '''
        Receive corrected cubes and publish visualizations for each camera
        '''
        if len(msg.cubes) < 2:
            self.get_logger().warn(f'Expected 2 cubes, got {len(msg.cubes)}')
            return

        # Process XIMEA cube (index 0)
        self.process_cube(
            msg.cubes[0],
            self.ximea_band_pubs,
            self.pub_ximea_false_color,
            self.pub_ximea_grid,
            'XIMEA'
        )

        # Process IMEC cube (index 1)
        self.process_cube(
            msg.cubes[1],
            self.imec_band_pubs,
            self.pub_imec_false_color,
            self.pub_imec_grid,
            'IMEC'
        )


def main(args=None):
    rclpy.init(args=args)
    visualizer = CorrectedCubeVisualizer()
    try:
        rclpy.spin(visualizer)
    finally:
        visualizer.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
