#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import Joy

GAP_MS = 150   # ~3x the autorepeat period at 20 Hz
AGE_MS = 50

class JoyMonitor(Node):
    def __init__(self):
        super().__init__('joy_monitor')
        self.last = None
        self.create_subscription(Joy, '/joy', self.cb, 50)

    def cb(self, msg):
        now = self.get_clock().now()
        age = (now - Time.from_msg(msg.header.stamp)).nanoseconds / 1e6
        if self.last is not None:
            gap = (now - self.last).nanoseconds / 1e6
            if gap > GAP_MS:
                self.get_logger().warn(f'/joy gap: {gap:.0f} ms')
        if age > AGE_MS:
            self.get_logger().warn(f'/joy stale: {age:.0f} ms old')
        self.last = now

def main():
    rclpy.init()
    rclpy.spin(JoyMonitor())

if __name__ == '__main__':
    main()