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

class SyncCubeVisualizer(Node):
    def __init__(self):
        super().__init__('sync_cube_visualizer')

        self.ximea_band_pubs = []
        self.imec_band_pubs = []

        # Subscribe to synchronous cubes
        self.cubes_sub = self.create_subscription(
            MultipleDataCubes,
            '/synchronous_cubes',
            self.callback_cubes,
            10
        )

        # False color publishers
        self.pub_ximea_false_color = self.create_publisher(Image, '/visualizer/ximea/false_color', 10)
        self.pub_imec_false_color = self.create_publisher(Image, '/visualizer/imec/false_color', 10)

        # Band grid publishers
        self.pub_ximea_grid = self.create_publisher(Image, '/visualizer/ximea/band_grid', 10)
        self.pub_imec_grid = self.create_publisher(Image, '/visualizer/imec/band_grid', 10)

        self.get_logger().info('Sync Cube Visualizer started, waiting for data...')

        # RGB publisher
        self.pub_vimba = self.create_publisher(Image, '/visualizer/vimba', 10)

    def normalize_band(self, band: np.ndarray) -> np.ndarray:
        '''
        Contrast stretch a single band to 8-bit
        '''
        band_min = band.min()
        band_max = band.max()
        if band_max == band_min:
            return np.zeros_like(band, dtype=np.uint8)
        normalized = (band - band_min) / (band_max - band_min) * 255
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
        Map 3 evenly spaced bands to R, G, B for a false color image
        False color band mapping:
        XIMEA (24 bands, visible/NIR 662-933nm):
        Red   > band 0  (~663nm, visible red edge)
        Green > band 12 (~817nm, NIR)
        Blue  > band 23 (~933nm, NIR)
        
        IMEC (9 bands, SWIR 1122-1655nm):
        Red   > band 0  (~1122nm, SWIR)
        Green > band 4  (~1211nm, SWIR)
        Blue  > band 8  (~1655nm, SWIR)
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
        Extract, visualize and publish a single DataCube
        '''
        # cube = np.reshape(
        #     np.array(msg_cube.data),
        #     (msg_cube.width, msg_cube.height, msg_cube.lam)
        # ).astype(np.float32)
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
                    f'/visualizer/{label.lower()}/band_{i}',
                    10
                )
                band_pubs_ref.append(pub)
            self.get_logger().info(f'{label}: Created publishers for {num_bands} bands')

        # Publish each individual band
        # for i in range(num_bands):
        #     self.publish_band(cube[:, :, i], band_pubs_ref[i])
        self.publish_band(cube[:,:,6], band_pubs_ref[6])

        # Publish false color and grid
        self.publish_false_color(cube, false_color_pub)
        # self.publish_band_grid(cube, grid_pub, label)

        self.get_logger().info(
            f'{label} | bands: {num_bands} | '
            f'min: {cube.min():.1f} max: {cube.max():.1f} mean: {cube.mean():.1f}'
        )

    def callback_cubes(self, msg: MultipleDataCubes):
        '''
        Receive synchronous cubes and publish visualizations for each camera
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

        # In synchronous_cube_visualizer.py callback_cubes:
        if msg.im.width > 100:
            self.pub_vimba.publish(msg.im)

def main(args=None):
    rclpy.init(args=args)
    visualizer = SyncCubeVisualizer()
    try:
        rclpy.spin(visualizer)
    finally:
        visualizer.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()