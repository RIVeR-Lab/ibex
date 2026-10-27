"""GraphReckoner: fixed-interval primary pose chain, with lidar/gps
attached via transient residual nodes .

Interface is deliberately callback-shaped (add_primary / add_lidar /
add_gps / add_imu / get_estimate) so a ROS2 node can be a thin wrapper:
timer -> add_primary, each subscription -> its add_* method.
"""

# ================================================ #
#
# NOTE: This file is deprecated CAO 27 OCT 2026
#       and was replaced with RTAB Map
#
# ================================================ #



import numpy as np
import gtsam
import gtsam_unstable
import utm

from .factors import (make_nhc_factor, make_rate_tie_factor, make_rate_cv_factor,
                       make_lidar_drift_factor, make_gps_odom_offset_factor, make_gravity_align_factor)
from . import symbols as S

GRAVITY = 9.81

# =========================================== #

def _state_to_pose3(state):
    """x, y, z, roll, pitch, yaw -> gtsam.Pose3"""
    x, y, z, roll, pitch, yaw = state
    return gtsam.Pose3(gtsam.Rot3.Ypr(yaw, pitch, roll), gtsam.Point3(x, y, z))


def _pose3_to_state(pose):
    """gtsam.Pose3 -> x, y, z, roll, pitch, yaw"""
    rot = pose.rotation()
    return np.array([pose.x(), pose.y(), pose.z(), rot.roll(), rot.pitch(), rot.yaw()])


def _sigmas_xyzrpy_to_gtsam(std_xyzrpy):
    """Reorder (x, y, z, roll, pitch, yaw) into
    gtsam's Pose3 tangent order, which is rotation-first:
    (roll, pitch, yaw, x, y, z)."""
    x, y, z, roll, pitch, yaw = std_xyzrpy
    return np.array([roll, pitch, yaw, x, y, z])


def _bias_noise_sigmas(gyro_bias_walk_std, accel_bias_walk_std, dt):
    """Build the 6 sigmas for a BetweenFactorConstantBias's random-walk
    noise, from separate gyro (rad/s) and accel (m/s^2) bias-walk
    stds
 
    Each std is scaled by sqrt(dt), consistent with modeling bias as a
    random walk (variance grows linearly with time, so std grows as
    sqrt(time))
    """
    accel_sigma = accel_bias_walk_std * np.sqrt(dt)
    gyro_sigma = gyro_bias_walk_std * np.sqrt(dt)
    return np.array([accel_sigma] * 3 + [gyro_sigma] * 3)



# =========================================== #




class GraphReckoner:
    def __init__(self, wheelbase = 1.2,
                 init_time=0.0,
                 init_state=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                 prior_noise_std=0.001,
                 dyn_noise_std=(0.005, 0.005, 1.0, 1.0, 1.0, 0.001),
                 lidar_noise_std=(0.05, 0.05, 0.05, 0.02, 0.02, 0.02),
                 lidar_drift_prior_std=(0.01, 0.01, 0.01, 0.005, 0.005, 0.005),
                 lidar_drift_process_noise_std=(0.01, 0.01, 0.01, 0.005, 0.005, 0.005),
                 imu_configs=None, init_velocity=(0.0, 0.0, 0.0), gravity=GRAVITY,
                 init_velocity_noise_std=1.0,
                 nhc_noise_std=(0.001, 0.001),
                 enable_lidar=True, enable_IMUs=True, enable_NHC=True,
                 enable_rate=True, enable_gps=True,
                 rate_prior_std=(1.0, 1.0),
                 rate_process_noise_std=(0.5, 0.5),
                 rate_tie_noise_std=(0.01, 0.01),
                 gps_sigma_at_best_quality=1.5,
                 gps_sigma_at_worst_quality=15.0,
                 lag_seconds=5.0,
                 residual_prop_noise_std=(0.01, 0.01, 1.0, 1.0, 1.0, 0.01),
                 gps_prop_noise_std=(0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
                 fallback_vel_noise_std=5.0,
                 odom_offset_prior_std=(50.0, 50.0, np.pi),
                 odom_offset_process_noise_std=(1e-4, 1e-4, 1e-4),
                 gravity_align_prior_std=(0.5, 0.5),
                 gravity_align_process_noise_std=(1e-4, 1e-4),
                 gravity_align_stationary_vel_thresh=0.05,
                 gravity_align_stationary_rate_thresh=0.02,
                 gravity_align_min_update_interval=2.0,
                 debugging=False,
                ):
        """Implements a GTSAM-based factor graph for IBEX state estimation"""

        self.wheelbase = wheelbase
        self.gravity = gravity
        self.last_primary_time = init_time

        self.enable_lidar = enable_lidar
        self.enable_IMUs = enable_IMUs
        self.enable_NHC = enable_NHC
        self.enable_rate = enable_rate
        self.enable_gps = enable_gps
        self.uses_velocity = enable_IMUs or enable_NHC or enable_rate

        self.dyn_noise_std = dyn_noise_std
        self.dyn_noise = gtsam.noiseModel.Diagonal.Sigmas(_sigmas_xyzrpy_to_gtsam(dyn_noise_std))
        self.residual_prop_noise = gtsam.noiseModel.Diagonal.Sigmas(_sigmas_xyzrpy_to_gtsam(residual_prop_noise_std))
        self.gps_prop_noise = gtsam.noiseModel.Diagonal.Sigmas(_sigmas_xyzrpy_to_gtsam(gps_prop_noise_std))
        self.nhc_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array(nhc_noise_std))
        # GPS position noise is quality-dependent -- see _gps_position_noise
        # -- rather than a single fixed sigma.
        self.gps_sigma_at_best_quality = gps_sigma_at_best_quality
        self.gps_sigma_at_worst_quality = gps_sigma_at_worst_quality
        self._utm_zone = None  # (zone_number, zone_letter), locked from the first GPS fix

        self.lidar_measurement_noise = gtsam.noiseModel.Diagonal.Sigmas(_sigmas_xyzrpy_to_gtsam(lidar_noise_std))
        self.lidar_drift_prior_noise = gtsam.noiseModel.Diagonal.Sigmas(_sigmas_xyzrpy_to_gtsam(lidar_drift_prior_std))
        self.lidar_drift_process_noise = gtsam.noiseModel.Diagonal.Sigmas(_sigmas_xyzrpy_to_gtsam(lidar_drift_process_noise_std))
        self._lidar_drift_process_noise_std = np.array(lidar_drift_process_noise_std)
        self.fallback_vel_noise = gtsam.noiseModel.Isotropic.Sigma(3, fallback_vel_noise_std)

        self.odom_offset_prior_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array(odom_offset_prior_std))
        self.odom_offset_process_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array(odom_offset_process_noise_std))

        # gravity_align (roll, pitch) is a true physical constant -- odom's
        # tilt relative to gravity-level never changes once odom is defined
        # at startup -- so, like odom_offset/lidar drift, its chain-link
        # noise is a fixed near-zero value (a marginalization device), not
        # scaled by sqrt(dt) the way a real random walk would be.
        self.gravity_align_prior_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array(gravity_align_prior_std))
        self.gravity_align_process_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array(gravity_align_process_noise_std))
        self.gravity_align_stationary_vel_thresh = gravity_align_stationary_vel_thresh
        self.gravity_align_stationary_rate_thresh = gravity_align_stationary_rate_thresh
        self.gravity_align_min_update_interval = gravity_align_min_update_interval
        self._last_gravity_align_update_time = None

        self.debugging = debugging

        # Set up based on enabled sensors
        if enable_IMUs:
            imu_configs = imu_configs or {}
            self.imu_names = list(imu_configs.keys())
            self.imu_pim = {}
            self.imu_bias_prefix = {}
            self.imu_bias_walk_std = {}
            self.imu_body_R_sensor = {}
            self.gravity_align_measurement_noise = {}
            self._last_accel = {}
            prefixes = {}
            for name in self.imu_names:
                if 'ouster' in name:
                    prefixes[name] = S.IMU_BIAS_OUSTER
                elif 'insta' in name:
                    prefixes[name] = S.IMU_BIAS_INSTA
                else:
                    raise ValueError(
                        f"No fixed symbol prefix configured for IMU '{name}' -- "
                        f"add one to symbols.py rather than assigning ad hoc."
                    )
            for name in self.imu_names:
                cfg = imu_configs[name]
                params = gtsam.PreintegrationParams.MakeSharedU(gravity)
                params.setGyroscopeCovariance(np.eye(3) * cfg.get('gyro_noise_std', 0.01) ** 2)
                params.setAccelerometerCovariance(np.eye(3) * cfg.get('accel_noise_std', 0.05) ** 2)
                params.setIntegrationCovariance(np.eye(3) * cfg.get('integration_noise_std', 1e-4) ** 2)
                body_P_sensor_xyzrpy = cfg.get('body_P_sensor_xyzrpy')
                if body_P_sensor_xyzrpy is not None:
                    params.setBodyPSensor(_state_to_pose3(body_P_sensor_xyzrpy))
                    self.imu_body_R_sensor[name] = _state_to_pose3(body_P_sensor_xyzrpy).rotation().matrix()
                else:
                    self.imu_body_R_sensor[name] = np.eye(3)
                self.imu_pim[name] = gtsam.PreintegratedImuMeasurements(params, gtsam.imuBias.ConstantBias())
                self.imu_bias_prefix[name] = prefixes[name]
                self.imu_bias_walk_std[name] = (
                    cfg.get('gyro_bias_walk_std', 0.0005),
                    cfg.get('accel_bias_walk_std', 0.001),
                )
                # Reuses each IMU's own accel noise (already configured for
                # preintegration) as the gravity-leveling factor's measurement
                # noise, rather than introducing a separate parameter.
                self.gravity_align_measurement_noise[name] = gtsam.noiseModel.Isotropic.Sigma(
                    3, cfg.get('accel_noise_std', 0.05))

        if enable_rate:
            self.rate_prior_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array(rate_prior_std))
            self.rate_process_noise_std = np.array(rate_process_noise_std)  # scaled by sqrt(dt) at point of use
            self.rate_tie_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array(rate_tie_noise_std))

        # Graph / smoother setup
        self.graph = gtsam.NonlinearFactorGraph()
        self.initial = gtsam.Values()
        self.timestamps = gtsam_unstable.FixedLagSmootherKeyTimestampMap()
        isam_params = gtsam.ISAM2Params()
        isam_params.relinearizeSkip = 1
        self.smoother = gtsam_unstable.IncrementalFixedLagSmoother(lag_seconds, isam_params)

        self.pose_index = 0
        self.drift_index = 0
        self.lidar_res_index = 0
        self.gps_res_index = 0
        self.odom_offset_index = 0
        self.gravity_align_index = 0
        self._lidar_drift_initialized = False
        self._odom_offset_initialized = False
        self._gravity_align_initialized = False

        self.pending_residuals = []  # list of (key, t, kind) awaiting a propagation link to the next primary

        # Init graph
        key0 = gtsam.symbol(S.POSE, 0)
        pose0 = _state_to_pose3(init_state)
        # pose0 stays tight and matches whatever convention the backbone's
        # sensors use (KISS-ICP's own lidar-odometry frame, which starts at
        # an arbitrary, non-gravity-aware identity) -- deliberately NOT
        # corrected for gravity here. Correcting for gravity by loosening
        # this prior was tried and reverted: it fights the (already tight,
        # by design) lidar_drift_prior_noise, which assumes drift_0 starts
        # near identity to match that same KISS-ICP convention. Instead,
        # gravity_align (see add_primary) is a fully separate latent
        # correction applied only when producing aligned_odom output/GPS
        # measurements, leaving this backbone chain and its raw odom frame
        # untouched.
        prior_noise = gtsam.noiseModel.Diagonal.Sigmas(np.array([prior_noise_std] * 6))
        self.graph.add(gtsam.PriorFactorPose3(key0, pose0, prior_noise))
        self.initial.insert(key0, pose0)
        self.timestamps.insert((key0, init_time))

        if self.uses_velocity:
            vel0_key = gtsam.symbol(S.VELOCITY, 0)
            vel0 = np.array(init_velocity, dtype=float)
            vel_prior_noise = gtsam.noiseModel.Isotropic.Sigma(3, init_velocity_noise_std)
            self.graph.add(gtsam.PriorFactorVector(vel0_key, vel0, vel_prior_noise))
            self.initial.insert(vel0_key, vel0)
            self.timestamps.insert((vel0_key, init_time))

        if enable_IMUs:
            bias_prior_noise = gtsam.noiseModel.Isotropic.Sigma(6, 0.1)
            for name in self.imu_names:
                bkey = gtsam.symbol(self.imu_bias_prefix[name], 0)
                self.graph.add(gtsam.PriorFactorConstantBias(bkey, gtsam.imuBias.ConstantBias(), bias_prior_noise))
                self.initial.insert(bkey, gtsam.imuBias.ConstantBias())
                self.timestamps.insert((bkey, init_time))

        if enable_rate:
            r0_key = gtsam.symbol(S.RATE, 0)
            r0 = np.zeros(2)
            self.graph.add(gtsam.PriorFactorVector(r0_key, r0, self.rate_prior_noise))
            self.initial.insert(r0_key, r0)
            self.timestamps.insert((r0_key, init_time))

        self._push()
        est = self.smoother.calculateEstimate()
        self.state = _pose3_to_state(est.atPose3(key0))
        if self.uses_velocity:
            self.velocity = est.atVector(vel0_key)



        
        if self.debugging:
            print("[__init__] Finished init")




    #------------------# Helpers #------------------#

    def _push(self):
        """Push accumulated graph/initial/timestamps into the smoother
        and reset the accumulators. Called after every add_* method
        
        IncrementalFixedLagSmoother is designed for
        frequent small incremental updates.
        """
        self.smoother.update(self.graph, self.initial, self.timestamps)
        if self.debugging:
            print("[_push] Smoother updated")

        self.graph = gtsam.NonlinearFactorGraph()
        if self.debugging:
            print("[_push] New graph made")

        self.initial = gtsam.Values()
        if self.debugging:
            print("[_push] New values")

        self.timestamps = gtsam_unstable.FixedLagSmootherKeyTimestampMap()
        if self.debugging:
            print("[_push] New timestamps")

    def _ensure_gravity_align_key(self, t, est):
        """Returns the key to attach this tick's gravity_align evidence
        to -- either the existing chain extended by one link, or a fresh
        (re-)bootstrapped root. Called from both add_primary's
        stationarity-gated chain growth and add_gps's ternary
        odom_offset factor -- whichever fires first is what actually
        creates the root node, the same lazy-init reasoning as
        add_lidar's drift chain (an untouched, prior-only node segfaults
        ISAM2's marginalization).

        Also handles re-bootstrapping: gravity_align only grows when
        stationary, so a stretch of continuous motion longer than
        lag_seconds (an entirely normal drive, not a rare edge case)
        lets the fixed-lag smoother marginalize the previously-tracked
        node out from under us before anything renews it. ISAM2 doesn't
        support re-inserting a value for an already-marginalized key, so
        when that's detected (via est.exists), this starts over at a
        fresh index with a new loose prior rather than chaining onto (or
        crashing on) the stale one.
        """
        prev_key = gtsam.symbol(S.GRAVITY_ALIGN, self.gravity_align_index) if self._gravity_align_initialized else None
        if prev_key is not None and est.exists(prev_key):
            self.gravity_align_index += 1
            curr_key = gtsam.symbol(S.GRAVITY_ALIGN, self.gravity_align_index)
            self.graph.add(gtsam.BetweenFactorVector(
                prev_key, curr_key, np.zeros(2), self.gravity_align_process_noise))
            self.initial.insert(curr_key, est.atVector(prev_key))
            self.timestamps.insert((curr_key, t))
            return curr_key

        if self._gravity_align_initialized:
            self.gravity_align_index += 1
        curr_key = gtsam.symbol(S.GRAVITY_ALIGN, self.gravity_align_index)
        g0 = np.zeros(2)
        self.graph.add(gtsam.PriorFactorVector(curr_key, g0, self.gravity_align_prior_noise))
        self.initial.insert(curr_key, g0)
        self.timestamps.insert((curr_key, t))
        self._gravity_align_initialized = True
        return curr_key

    def _latlon_to_utm(self, lat, lon):
        """Projects a raw lat/lon (degrees) fix into UTM easting/northing
        (meters), locking the zone/letter to whatever the very first GPS
        fix picked and forcing every later fix into that same zone.
        Without forcing, a vehicle operating near a UTM zone boundary
        would see its *natural* zone flip as it crosses, causing
        easting/northing to jump by hundreds of km instantaneously --
        catastrophic for odom_offset's continuity. Forcing one zone for
        the whole run avoids that; the cost is a small amount of
        additional projection scale distortion if operating near a zone
        edge (bounded, well under GPS's own noise floor at ground-vehicle
        operating ranges -- see UTM's own 0.9996 central-meridian scale
        factor, which already budgets for this).
        """
        if self._utm_zone is None:
            easting, northing, zone_number, zone_letter = utm.from_latlon(lat, lon)
            self._utm_zone = (zone_number, zone_letter)
            return easting, northing
        zone_number, zone_letter = self._utm_zone
        easting, northing, _, _ = utm.from_latlon(
            lat, lon, force_zone_number=zone_number, force_zone_letter=zone_letter)
        return easting, northing

    def _is_valid_gps_fix(self, lat, lon, quality, sat_count):
        """Rejects placeholder/no-fix sentinel readings before they can
        latch the UTM zone or seed odom_offset -- a bogus "fix" (e.g. a
        driver publishing its default-initialized fields before it's ever
        received real data) would otherwise be trusted exactly like a
        real, merely-noisy one (see _latlon_to_utm's zone-locking
        rationale, which assumes the first fix is coarse but roughly
        right -- not literally a sentinel). UNVALIDATED heuristic, same
        caveat as _gps_position_noise: needs the receiver's actual no-fix
        sentinel convention to replace this with a real check.
        """
        if quality is not None and quality <= 0:
            return False
        if sat_count is not None and sat_count <= 0:
            return False
        if lat == 0.0 and lon == 0.0:
            return False
        return True

    def _gps_position_noise(self, quality, sat_count):
        """Placeholder quality -> position-sigma heuristic: linear
        interpolation between best/worst-case sigma over auto_gps_quality's
        documented 0-100 range. UNVALIDATED -- needs either the receiver's
        accuracy spec or logged stationary-scatter calibration data to
        replace this with a real model. sat_count is accepted but not
        currently used; kept in the signature so it's easy to fold in once
        a real model is available.
        """
        if quality is None:
            sigma = self.gps_sigma_at_worst_quality
        else:
            q = np.clip(quality, 0.0, 100.0) / 100.0
            sigma = self.gps_sigma_at_worst_quality + q * (
                self.gps_sigma_at_best_quality - self.gps_sigma_at_worst_quality)
        return gtsam.noiseModel.Isotropic.Sigma(2, sigma)

    def _predict_dynamics(self, v, delta, dt, vz=0.0, roll_rate=0.0, pitch_rate=0.0):
        """Bicycle relative-motion model (x, y, yaw), and z/roll/pitch use 
        constant-velocity/rate extrapolation. vz/roll_rate/pitch_rate default
        to 0.0.

        dy is hardcoded 0 (no lateral-slip term) -
        """
        dx = v * dt
        dy = 0.0
        dz = vz * dt
        droll = roll_rate * dt
        dpitch = pitch_rate * dt
        dyaw = (v / self.wheelbase) * np.tan(delta) * dt
        return dx, dy, dz, droll, dpitch, dyaw



    #------------------# Sensor Methods #------------------#

    def add_imu(self, imu_name, omega, accel, dt):
        """Accumulate one IMU sample into the running preintegration for
        `imu_name`, and record it as that IMU's latest raw sample for
        gravity_align's stationarity-gated leveling factor (see add_primary).
        """
        self.imu_pim[imu_name].integrateMeasurement(accel, omega, dt)
        self._last_accel[imu_name] = accel


    def add_lidar(self, t_lidar, lidar_state_xyzrpy):
        """lidar_state_xyzrpy: raw lidar-odometry global pose reading,
        (x, y, z, roll, pitch, yaw).  Creates a residual node + drift-chain step immediately;
        the propagation link to the next primary is deferred (see
        pending_residuals, resolved in add_primary).
        """
        if not self.enable_lidar:
            return

        if self.debugging:
            print(f"[add_lidar] accepted t_lidar={t_lidar:.3f}, pose={lidar_state_xyzrpy}", flush=True)


        est = self.smoother.calculateEstimate()

        self.lidar_res_index += 1
        res_key = gtsam.symbol(S.LIDAR_RESIDUAL, self.lidar_res_index)

        lidar_pose = _state_to_pose3(lidar_state_xyzrpy)

        if not self._lidar_drift_initialized:
            # First real lidar reading -- create the drift chain's root
            # node now (with its prior), rather than at __init__ time.
            # Deliberately deferred: a drift node created at construction
            # but never touched (e.g. lidar hasn't started publishing
            # yet) sits as an isolated prior-only variable in the Bayes
            # tree, which crashed gtsam's IncrementalFixedLagSmoother
            # (segfault inside ISAM2::marginalizeLeaves) the first time
            # it tried to marginalize with no other factor ever having
            # touched it. Deferring creation to first real use avoids
            # that isolated-node state ever existing.
            drift_curr_key = gtsam.symbol(S.LIDAR_DRIFT, 0)
            d0 = gtsam.Pose3()
            self.graph.add(gtsam.PriorFactorPose3(drift_curr_key, d0, self.lidar_drift_prior_noise))
            self.initial.insert(drift_curr_key, d0)
            self.timestamps.insert((drift_curr_key, t_lidar))
            self._lidar_drift_initialized = True
        else:
            self.drift_index += 1
            drift_prev_key = gtsam.symbol(S.LIDAR_DRIFT, self.drift_index - 1)
            drift_curr_key = gtsam.symbol(S.LIDAR_DRIFT, self.drift_index)

            dt_drift = max(t_lidar - self.last_primary_time, 1e-3)
            drift_process_noise = gtsam.noiseModel.Diagonal.Sigmas(
                _sigmas_xyzrpy_to_gtsam(self._lidar_drift_process_noise_std) * np.sqrt(dt_drift)
            )
            self.graph.add(gtsam.BetweenFactorPose3(drift_prev_key, drift_curr_key, gtsam.Pose3(), drift_process_noise))
            prev_drift_est = est.atPose3(drift_prev_key)
            self.initial.insert(drift_curr_key, prev_drift_est)
            self.timestamps.insert((drift_curr_key, t_lidar))

        self.graph.add(make_lidar_drift_factor(res_key, drift_curr_key, lidar_pose, self.lidar_measurement_noise))
        self.initial.insert(res_key, lidar_pose)
        self.timestamps.insert((res_key, t_lidar))

        self.pending_residuals.append((res_key, t_lidar, 'lidar'))
        if self.debugging:
            print(f"[add_lidar] residual node l{self.lidar_res_index} created, pending_residuals size={len(self.pending_residuals)}", flush=True)
        self._push()

    def add_gps(self, t_gps, lat, lon, quality=None, sat_count=None):
        """lat/lon: raw GPS fix in degrees. quality (0-100, see
        _gps_position_noise) and sat_count feed the (placeholder) position
        noise heuristic. No altitude in this message, so odom_offset is
        SE(2)-only (easting_offset, northing_offset, yaw) -- z is left
        entirely to lidar/IMU dead reckoning, unconstrained by GPS.
        """
        if not self.enable_gps:
            return

        if not self._is_valid_gps_fix(lat, lon, quality, sat_count):
            # Rejected before touching anything else -- no factors/nodes
            # created, and (critically) _latlon_to_utm's zone-lock and
            # odom_offset's seed are never influenced by a bogus reading.
            if self.debugging:
                print(f"[add_gps] rejected invalid fix (lat={lat}, lon={lon}, "
                      f"quality={quality}, sat_count={sat_count})", flush=True)
            return

        est = self.smoother.calculateEstimate()

        if t_gps < self.last_primary_time:
            # Stale reading
            return

        easting, northing = self._latlon_to_utm(lat, lon)

        self.gps_res_index += 1
        res_key = gtsam.symbol(S.GPS_RESIDUAL, self.gps_res_index)

        if self.debugging:
            print(f"[add_gps] accepted t_gps={t_gps:.3f}, lat={lat}, lon={lon}, "
                  f"utm=({easting:.2f}, {northing:.2f})", flush=True)

        # Unlike lidar (which directly observes an odom-frame pose), a raw
        # GPS fix only becomes comparable to the backbone after passing
        # through gravity_align + odom_offset -- there's no direct
        # odom-frame reading to seed res_key's translation from, so seed
        # the whole node (translation and rotation) from the current
        # backbone estimate and let the new factor below pull it.
        curr_pose_key = gtsam.symbol(S.POSE, self.pose_index)
        seed_pose = est.atPose3(curr_pose_key)

        gravity_align_key = self._ensure_gravity_align_key(t_gps, est)

        # odom_offset only grows on real GPS readings, so an outage longer
        # than lag_seconds (a tunnel, dense foliage, etc. -- not a rare
        # edge case) lets the fixed-lag smoother marginalize the
        # previously-tracked node out from under us before anything
        # renews it. As with gravity_align (see _ensure_gravity_align_key),
        # ISAM2 doesn't support re-inserting a value for an
        # already-marginalized key, so that's detected via est.exists and
        # handled by re-bootstrapping at a fresh index with a new loose
        # prior rather than chaining onto (or crashing on) the stale one.
        odom_offset_prev_key = gtsam.symbol(S.ODOM_OFFSET, self.odom_offset_index) if self._odom_offset_initialized else None
        if odom_offset_prev_key is not None and est.exists(odom_offset_prev_key):
            self.odom_offset_index += 1
            odom_offset_curr_key = gtsam.symbol(S.ODOM_OFFSET, self.odom_offset_index)
            self.graph.add(gtsam.BetweenFactorPose2(
                odom_offset_prev_key, odom_offset_curr_key, gtsam.Pose2(), self.odom_offset_process_noise))
            self.initial.insert(odom_offset_curr_key, est.atPose2(odom_offset_prev_key))
            self.timestamps.insert((odom_offset_curr_key, t_gps))
        else:
            # First real GPS reading, or re-bootstrapping after the chain
            # aged out -- create a fresh root node with a loose prior (same
            # segfault risk as the drift chain if a node exists before
            # anything touches it -- see add_lidar). Seed translation from
            # (measured UTM - current pose's xy) so the initial guess is in
            # the right ballpark despite the loose prior; yaw is
            # unobservable from a single fix (no heading in this message)
            # so seeded at 0.
            if self._odom_offset_initialized:
                self.odom_offset_index += 1
            odom_offset_curr_key = gtsam.symbol(S.ODOM_OFFSET, self.odom_offset_index)
            offset0 = gtsam.Pose2(easting - seed_pose.x(), northing - seed_pose.y(), 0.0)
            self.graph.add(gtsam.PriorFactorPose2(odom_offset_curr_key, offset0, self.odom_offset_prior_noise))
            self.initial.insert(odom_offset_curr_key, offset0)
            self.timestamps.insert((odom_offset_curr_key, t_gps))
            self._odom_offset_initialized = True

        gps_noise = self._gps_position_noise(quality, sat_count)
        utm_xy = gtsam.Point2(easting, northing)
        self.graph.add(make_gps_odom_offset_factor(
            res_key, gravity_align_key, odom_offset_curr_key, utm_xy, gps_noise))

        # The new factor above only constrains res_key's translation --
        # rotation is otherwise completely unconstrained until add_primary
        # later adds the propagation BetweenFactor, which ISAM2 correctly
        # rejects as an indeterminate/underconstrained system the moment
        # _push() tries to solve. This weak prior's translation sigmas are
        # enormous (the new factor already owns that info) and rotation
        # sigmas are loose but finite, just enough to keep the linear
        # system full rank in the meantime.
        # TODO: update with heading/velocity from GPS sensor
        weak_prior_noise = gtsam.noiseModel.Diagonal.Sigmas(
            _sigmas_xyzrpy_to_gtsam((1e3, 1e3, 1e3, 1.0, 1.0, 1.0))
        )
        self.graph.add(gtsam.PriorFactorPose3(res_key, seed_pose, weak_prior_noise))
        self.initial.insert(res_key, seed_pose)
        self.timestamps.insert((res_key, t_gps))

        self.pending_residuals.append((res_key, t_gps, 'gps'))
        if self.debugging:
            print(f"[add_gps] residual node g{self.gps_res_index} created, pending_residuals size={len(self.pending_residuals)}", flush=True)
        self._push()




    #------------------# Main Methods #------------------#

    def add_primary(self, t, v, delta):
        """Timer callback: create the next primary pose node, connect it
        to the previous one via the dynamics factor (+ IMU factor if
        enabled) over the true elapsed dt, then resolve every pending
        lidar/gps residual by connecting it to this new node via its own
        dynamics-propagation factor. 
        
        v, delta: the control input to use
        for the primary dynamics factor and (per-residual) the
        propagation factors -- current commanded input is used as a
        constant approximation across the whole window, since we don't
        track a full control-input history here.
        """

        if self.debugging:
            print("[add_primary] Starting add_primary")

        prev_key = gtsam.symbol(S.POSE, self.pose_index)
        prev_vel_key = gtsam.symbol(S.VELOCITY, self.pose_index) if self.uses_velocity else None
        self.pose_index += 1
        curr_key = gtsam.symbol(S.POSE, self.pose_index)
        curr_vel_key = gtsam.symbol(S.VELOCITY, self.pose_index) if self.uses_velocity else None

        if self.debugging:
            print("[add_primary] symbols made")

        dt = t - self.last_primary_time
        if dt <= 0:
            raise ValueError(f"add_primary called with non-increasing time (dt={dt})")

        # Fetch the estimate before building the dynamics prediction --
        # needed now to read the previous node's velocity/rate for the
        # constant-velocity/rate extrapolation below. Nothing is solved
        # between here and the second use of `est` later in this method,
        # so one fetch covers both.
        est = self.smoother.calculateEstimate()
        prev_pose = est.atPose3(prev_key)

        if self.debugging:
            print("[add_primary] Estimate made")

        if self.uses_velocity:
            v_world_prev = est.atVector(prev_vel_key)
            R_prev = prev_pose.rotation().matrix()
            v_body_prev = R_prev.T @ v_world_prev  # world -> prev's own body frame
            vz_prev = v_body_prev[2]
        else:
            vz_prev = 0.0
        if self.debugging:
            print("[add_primary] Velocity")

        if self.enable_rate:
            r_prev_key_for_dyn = gtsam.symbol(S.RATE, self.pose_index - 1)  # matches prev_key's index
            roll_rate_prev, pitch_rate_prev = est.atVector(r_prev_key_for_dyn)
        else:
            roll_rate_prev, pitch_rate_prev = 0.0, 0.0
        if self.debugging:
            print("[add_primary] Rate")

        dx, dy, dz, droll, dpitch, dyaw = self._predict_dynamics(
            v, delta, dt, vz=vz_prev, roll_rate=roll_rate_prev, pitch_rate=pitch_rate_prev)
        dyn_pose = gtsam.Pose3(gtsam.Rot3.Ypr(dyaw, dpitch, droll), gtsam.Point3(dx, dy, dz))
        self.graph.add(gtsam.BetweenFactorPose3(prev_key, curr_key, dyn_pose, self.dyn_noise))
        if self.debugging:
            print("[add_primary] Dynamics")

        imu_factor_added = False
        if self.enable_IMUs:
            for name in self.imu_names:
                pim = self.imu_pim[name]

                if pim.deltaTij() <= 0.0:
                    prev_bias_key = gtsam.symbol(self.imu_bias_prefix[name], self.pose_index - 1)
                    curr_bias_key = gtsam.symbol(self.imu_bias_prefix[name], self.pose_index)
                    gyro_walk_std, accel_walk_std = self.imu_bias_walk_std[name]
                    bias_noise = gtsam.noiseModel.Diagonal.Sigmas(_bias_noise_sigmas(gyro_walk_std, accel_walk_std, dt))
                    self.graph.add(gtsam.BetweenFactorConstantBias(
                        prev_bias_key, curr_bias_key, gtsam.imuBias.ConstantBias(), bias_noise))
                    prev_bias_est = est.atConstantBias(prev_bias_key)
                    self.initial.insert(curr_bias_key, prev_bias_est)
                    self.timestamps.insert((curr_bias_key, t))
                    if self.debugging:
                        print("[add_primary] IMU excluded")
                    continue

                imu_factor_added = True

                prev_bias_key = gtsam.symbol(self.imu_bias_prefix[name], self.pose_index - 1)
                curr_bias_key = gtsam.symbol(self.imu_bias_prefix[name], self.pose_index)
                self.graph.add(gtsam.ImuFactor(prev_key, prev_vel_key, curr_key, curr_vel_key, prev_bias_key, pim))

                gyro_walk_std, accel_walk_std = self.imu_bias_walk_std[name]
                bias_noise = gtsam.noiseModel.Diagonal.Sigmas(_bias_noise_sigmas(gyro_walk_std, accel_walk_std, dt))
                self.graph.add(gtsam.BetweenFactorConstantBias(
                    prev_bias_key, curr_bias_key, gtsam.imuBias.ConstantBias(), bias_noise))

                prev_bias_est = est.atConstantBias(prev_bias_key)
                self.initial.insert(curr_bias_key, prev_bias_est)
                self.timestamps.insert((curr_bias_key, t))
                pim.resetIntegrationAndSetBias(prev_bias_est)

                if self.debugging:
                    print("[add_primary] IMU added")
        if self.debugging:
            print("[add_primary] IMU")

        if self.uses_velocity and not imu_factor_added:
            # No real IMU factor this tick (either enable_IMUs is False, or
            # every enabled IMU had zero data) -- add a loose fallback tie
            # so prev_vel_key -> curr_vel_key stays well-posed.
            self.graph.add(gtsam.BetweenFactorVector(prev_vel_key, curr_vel_key, np.zeros(3), self.fallback_vel_noise))
            if self.debugging:
                print("[add_primary] Fallback IMU")

        if self.enable_NHC:
            self.graph.add(make_nhc_factor(curr_key, curr_vel_key, self.nhc_noise))
        if self.debugging:
            print("[add_primary] NHC")

        if self.enable_rate:
            r_prev_key = gtsam.symbol(S.RATE, self.pose_index - 1)
            r_curr_key = gtsam.symbol(S.RATE, self.pose_index)
            rate_cv_noise = gtsam.noiseModel.Diagonal.Sigmas(self.rate_process_noise_std * np.sqrt(dt))
            self.graph.add(make_rate_tie_factor(prev_key, curr_key, r_prev_key, dt, self.rate_tie_noise))
            self.graph.add(make_rate_cv_factor(r_prev_key, r_curr_key, rate_cv_noise))
            r_prev_est = est.atVector(r_prev_key)
            self.initial.insert(r_curr_key, r_prev_est)
            self.timestamps.insert((r_curr_key, t))
        if self.debugging:
            print("[add_primary] Rate 2")

        # gravity_align: only trust the accelerometer(s) as pure gravity
        # when the vehicle was (near-)stationary over this interval --
        # otherwise real acceleration/rotation would get folded into the
        # tilt estimate. Gated on the previous tick's already-resolved
        # velocity/rate rather than this tick's (which isn't known until
        # after the solve below) -- an approximation, but the window is
        # short (one primary period) so it's a reasonable proxy for "was
        # stationary during this tick".
        #
        # Also rate-limited by gravity_align_min_update_interval, separate
        # from the stationarity check: a parked vehicle satisfies
        # is_stationary on *every* primary tick indefinitely, and without
        # this gate the chain would grow once per tick (6+ Hz) for the
        # entire time it sits still -- unlike lidar-drift/odom_offset,
        # which grow only on discrete sensor events (lidar/GPS readings),
        # this chain has no such natural rate limit of its own. Chaining
        # many near-zero-noise BetweenFactors together that fast, then
        # continuously marginalizing them, is a known way to ill-condition
        # ISAM2's incremental solve. gravity_align is a true constant, so
        # occasional check-ins are exactly as informative as constant ones.
        if self.enable_IMUs and self._last_accel:
            speed_prev = np.linalg.norm(v_world_prev) if self.uses_velocity else 0.0
            rate_mag_prev = np.linalg.norm([roll_rate_prev, pitch_rate_prev])
            is_stationary = (speed_prev < self.gravity_align_stationary_vel_thresh
                              and rate_mag_prev < self.gravity_align_stationary_rate_thresh)
            due_for_update = (self._last_gravity_align_update_time is None
                               or t - self._last_gravity_align_update_time >= self.gravity_align_min_update_interval)
            if is_stationary and due_for_update:
                gravity_align_curr_key = self._ensure_gravity_align_key(t, est)

                for name in self.imu_names:
                    accel_sensor = self._last_accel.get(name)
                    if accel_sensor is None:
                        continue
                    accel_body = self.imu_body_R_sensor[name] @ accel_sensor
                    self.graph.add(make_gravity_align_factor(
                        curr_key, gravity_align_curr_key, accel_body, self.gravity,
                        self.gravity_align_measurement_noise[name]))
                self._last_gravity_align_update_time = t
                if self.debugging:
                    print(f"[add_primary] gravity_align updated at index {self.gravity_align_index}")

        # Resolve pending lidar/gps residuals: connect each to curr_key
        # via its own dynamics-propagation factor over (t - t_residual).
        for res_key, t_res, kind in self.pending_residuals:
            dt_res = t - t_res
            if dt_res < 0:
                raise ValueError(f"pending {kind} residual timestamp is after this primary's time")
            ddx, ddy, ddz, ddroll, ddpitch, ddyaw = self._predict_dynamics(
                v, delta, dt_res, vz=vz_prev, roll_rate=roll_rate_prev, pitch_rate=pitch_rate_prev)
            prop_pose = gtsam.Pose3(gtsam.Rot3.Ypr(ddyaw, ddpitch, ddroll), gtsam.Point3(ddx, ddy, ddz))
            prop_noise = self.gps_prop_noise if kind == 'gps' else self.residual_prop_noise
            self.graph.add(gtsam.BetweenFactorPose3(res_key, curr_key, prop_pose, prop_noise))
        self.pending_residuals = []
        if self.debugging:
            print("[add_primary] Resolve")

        # Initial guesses for the new primary pose/velocity
        curr_pose_guess = prev_pose.compose(dyn_pose)
        self.initial.insert(curr_key, curr_pose_guess)
        self.timestamps.insert((curr_key, t))
        if self.debugging:
            print("[add_primary] Initial values")

        if self.uses_velocity:
            prev_vel = est.atVector(prev_vel_key)
            R_prev = prev_pose.rotation().matrix()
            R_curr = curr_pose_guess.rotation().matrix()
            v_body = R_prev.T @ prev_vel
            vel_guess = R_curr @ v_body
            self.initial.insert(curr_vel_key, vel_guess)
            self.timestamps.insert((curr_vel_key, t))
        if self.debugging:
            print("[add_primary] Velocity 2")

        self._push()
        if self.debugging:
            print("[add_primary] Push")

        est = self.smoother.calculateEstimate()
        self.state = _pose3_to_state(est.atPose3(curr_key))
        if self.uses_velocity:
            self.velocity = est.atVector(curr_vel_key)
        if self.debugging:
            print("[add_primary] Estimate completed")

        self.last_primary_time = t
        return self.state.copy()





    #------------------# Publisher Methods #------------------#

    def get_estimate(self):
        return self.state.copy()

    def get_covariance(self):
        """Marginal covariance of the current primary pose, permuted from
        gtsam's rotation-first tangent order (roll, pitch, yaw, x, y, z)
        into our external (x, y, z, roll, pitch, yaw) convention, to match
        self.state.
        """
        curr_key = gtsam.symbol(S.POSE, self.pose_index)
        cov_gtsam = self.smoother.getISAM2().marginalCovariance(curr_key)

        perm = [3, 4, 5, 0, 1, 2]
        return cov_gtsam[np.ix_(perm, perm)]

    def _gravity_align_rot(self, roll, pitch):
        """R_level_from_odom: rotates odom-frame vectors into aligned_odom
        (odom rotated in place about its own origin so +z is antiparallel
        to gravity). Yaw is left at 0 -- gravity alone can't observe it,
        and aligned_odom is meant to only correct tilt, not spin odom's
        arbitrary yaw reference.
        """
        return gtsam.Rot3.Ypr(0.0, pitch, roll)

    def get_aligned_state(self):
        """Current primary pose, composed with the current gravity_align
        estimate, expressed in aligned_odom (see add_primary's gravity_align
        docstring). Falls back to the raw (uncorrected) estimate until
        gravity_align has any real evidence, or if its previously-tracked
        node has aged out of the fixed-lag window since its last update
        (e.g. mid-drive, before add_primary's next stationary check
        re-bootstraps it -- see _ensure_gravity_align_key) -- this is
        called every tick regardless of update timing, so it can't assume
        the tracked key still exists.
        """
        curr_key = gtsam.symbol(S.POSE, self.pose_index)
        est = self.smoother.calculateEstimate()
        pose = est.atPose3(curr_key)
        gravity_align_key = gtsam.symbol(S.GRAVITY_ALIGN, self.gravity_align_index)
        if not self._gravity_align_initialized or not est.exists(gravity_align_key):
            return _pose3_to_state(pose)

        roll, pitch = est.atVector(gravity_align_key)
        gravity_align_pose = gtsam.Pose3(self._gravity_align_rot(roll, pitch), gtsam.Point3(0.0, 0.0, 0.0))
        return _pose3_to_state(gravity_align_pose.compose(pose))

    def get_aligned_covariance(self):
        """Marginal covariance of get_aligned_state(), fully propagating
        both the pose's own uncertainty and gravity_align's -- including
        their cross-covariance, via ISAM2's current factors reconstructed
        as a one-off gtsam.Marginals -- rather than treating gravity_align
        as a known constant. Falls back to get_covariance() until
        gravity_align has any real evidence, or if its previously-tracked
        node has aged out of the fixed-lag window (see get_aligned_state).
        """
        curr_key = gtsam.symbol(S.POSE, self.pose_index)
        gravity_align_key = gtsam.symbol(S.GRAVITY_ALIGN, self.gravity_align_index)
        est = self.smoother.calculateEstimate()
        if not self._gravity_align_initialized or not est.exists(gravity_align_key):
            return self.get_covariance()

        marginals = gtsam.Marginals(self.smoother.getISAM2().getFactorsUnsafe(), est)
        joint_cov = marginals.jointMarginalCovariance(gtsam.KeyVector([curr_key, gravity_align_key])).fullMatrix()

        pose = est.atPose3(curr_key)
        gravity_align = est.atVector(gravity_align_key)

        def aligned_state(pose_, gravity_align_):
            roll, pitch = gravity_align_
            gravity_align_pose = gtsam.Pose3(self._gravity_align_rot(roll, pitch), gtsam.Point3(0.0, 0.0, 0.0))
            return _pose3_to_state(gravity_align_pose.compose(pose_))

        eps = 1e-6
        J = np.zeros((6, 8))
        for i in range(6):
            d = np.zeros(6); d[i] = eps
            J[:, i] = (aligned_state(pose.retract(d), gravity_align)
                       - aligned_state(pose.retract(-d), gravity_align)) / (2 * eps)
        for i in range(2):
            d = np.zeros(2); d[i] = eps
            J[:, 6 + i] = (aligned_state(pose, gravity_align + d)
                           - aligned_state(pose, gravity_align - d)) / (2 * eps)

        return J @ joint_cov @ J.T

    def get_odom_offset(self):
        """Current odom_offset estimate: (easting_offset, northing_offset,
        yaw) of the odom origin in UTM. Returns None until the first real
        GPS reading has initialized the chain (see add_gps), or if its
        previously-tracked node has aged out of the fixed-lag window since
        its last update (e.g. a GPS outage longer than lag_seconds, before
        the next real fix re-bootstraps it -- see add_gps) -- this is
        called on every publish tick regardless of update timing, so it
        can't assume the tracked key still exists.
        """
        if not self._odom_offset_initialized:
            return None
        key = gtsam.symbol(S.ODOM_OFFSET, self.odom_offset_index)
        est = self.smoother.calculateEstimate()
        if not est.exists(key):
            return None
        offset = est.atPose2(key)
        return np.array([offset.x(), offset.y(), offset.theta()])

    def get_odom_offset_covariance(self):
        """Marginal covariance of get_odom_offset(), in (x, y, theta) order
        -- gtsam.Pose2's tangent space is already (x, y, theta), unlike
        Pose3's rotation-first convention, so no permutation is needed here
        (contrast get_covariance()). Returns None until the chain exists,
        or if its previously-tracked node has aged out (see
        get_odom_offset).
        """
        if not self._odom_offset_initialized:
            return None
        key = gtsam.symbol(S.ODOM_OFFSET, self.odom_offset_index)
        if not self.smoother.calculateEstimate().exists(key):
            return None
        return self.smoother.getISAM2().marginalCovariance(key)

    def get_latlon(self):
        """Vehicle's current position in lat/lon (degrees): composes the
        current aligned pose with the current odom_offset estimate and
        inverts the UTM projection from _latlon_to_utm. Read-only
        convenience on top of the existing state -- returns None until
        odom_offset has real evidence (see add_gps), or if its
        previously-tracked node has aged out (see get_odom_offset).
        """
        if not self._odom_offset_initialized:
            return None
        offset_key = gtsam.symbol(S.ODOM_OFFSET, self.odom_offset_index)
        est = self.smoother.calculateEstimate()
        if not est.exists(offset_key):
            return None
        x, y, z, roll, pitch, yaw = self.get_aligned_state()
        offset = est.atPose2(offset_key)
        easting, northing = offset.transformFrom(gtsam.Point2(x, y))
        zone_number, zone_letter = self._utm_zone
        return utm.to_latlon(easting, northing, zone_number, zone_letter)