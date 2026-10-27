"""Fixed gtsam single-character symbol prefixes."""

# ================================================ #
#
# NOTE: This file is deprecated CAO 27 OCT 2026
#       and was replaced with RTAB Map
#
# ================================================ #





POSE = 'x'              # primary pose nodes (timer-driven backbone)
VELOCITY = 'v'          # velocity nodes, one per primary pose
RATE = 'r'              # angular rate (roll_dot, pitch_dot) chain

LIDAR_DRIFT = 'd'       # latent lidar-odometry drift chain
LIDAR_RESIDUAL = 'l'    # transient residual pose nodes, one per lidar reading

GPS_RESIDUAL = 'g'      # transient residual pose nodes, one per gps reading

ODOM_OFFSET = 'o'       # latent odom-origin-in-UTM chain (easting, northing, yaw), grows per gps reading
GRAVITY_ALIGN = 'w'     # latent odom-tilt-vs-true-level chain (roll, pitch), grows per stationary reading

IMU_BIAS_OUSTER = 'b'   # Ouster IMU bias chain
IMU_BIAS_INSTA = 'c'    # Insta360 IMU bias chain

# Sanity check: fail loudly at import time if any collide,
_ALL = [POSE, VELOCITY, RATE, LIDAR_DRIFT, LIDAR_RESIDUAL, GPS_RESIDUAL,
        ODOM_OFFSET, GRAVITY_ALIGN, IMU_BIAS_OUSTER, IMU_BIAS_INSTA]
assert len(_ALL) == len(set(_ALL)), "Duplicate gtsam symbol prefix in symbols.py"