---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Running the system

Brings up the software stack on Volta and runs a session.

Starts after [power-on.md](power-on.md) is complete. Ends before
[power-off.md](power-off.md) begins.

**This page owns the order.** For what an individual launch file contains, its arguments
and its parameters, see [launch-files.md](../05-reference/launch-files.md). For recording
data, see [data-collection.md](data-collection.md).

## Before you begin

- [ ] [power-on.md](power-on.md) complete, including the VIM armed at step 9
- [ ] Workspace built — see
      [workstation-setup.md](../00-onboarding/workstation-setup.md)
- [ ] Pre-run checklist complete — see [checklists.md](../01-safety/checklists.md)
- [ ] If the vehicle will move: perimeter clear, spotters in position, everyone knows
      where the VIM pause switch is

## 1. Connect to Volta

Volta normally runs headless and is reached over SSH.

To switch it into headless mode from a remote machine, with the local display connected:

```bash
sudo systemctl disable --now gdm3 && sudo /etc/NX/nxserver --restart
```

To switch it back to headed, run this and then reconnect the display:

```bash
sudo systemctl enable --now gdm3
```

> TODO(verify): record how Volta is normally reached — its hostname or address, which user
> account, and whether NoMachine is the expected remote desktop route or only a fallback.
> [network.md](../05-reference/network.md) owns the addressing.

Source the workspace in every shell you open:

```bash
source ~/ibex_ws/install/setup.bash
```

## 2. Bring up the system

The normal path is one command. It starts the sensors and publishes the static transforms:

```bash
ros2 launch ibex_bringup system_bringup.launch.py
```

Then bring up vehicle control:

```bash
ros2 launch ibex_bringup control.launch.py
```

Starting this after the P4S4 is already armed is safe. The actuators do not move on their
own — commanded motion requires the deadman to be held, so an armed P4S4 with the
controller just started will sit still until someone holds the deadman. See
[estop-chain.md](../01-safety/estop-chain.md).

> TODO(verify): confirm which sensors `system_bringup.launch.py` actually starts. The
> individual launches in section 5 include drivers that may or may not be inside it —
> notably the hyperspectral cameras, which need USB permissions set first.

## 3. Verify the stack is up

```bash
ros2 node list
ros2 topic list
ros2 topic hz /ouster/points
```

> TODO(verify): write the actual expected output — the node list for a healthy bringup and
> the nominal rate for the topics worth checking. "Run `ros2 node list`" is only useful to
> someone who already knows what should be in it. This is also the check
> [workstation-setup.md](../00-onboarding/workstation-setup.md) needs for its build smoke
> test.

Confirm the transform tree is populated:

```bash
ros2 run tf2_tools view_frames
```

Frame names and extrinsics: [tf-frames.md](../05-reference/tf-frames.md).

## 4. Run the session

Recording bags, naming them, and the `metadata.yaml` convention are in
[data-collection.md](data-collection.md).

### Viewing camera output

```bash
ros2 run image_view image_view --ros-args -r image:=/visualizer/imec/false_color
ros2 run image_view image_view --ros-args -r image:=/visualizer/ximea/false_color
ros2 run image_view image_view --ros-args -r image:=/visualizer/
```

The third topic is incomplete as recorded and is left as-is.

### Foxglove

The bridge runs on Volta; Studio runs on whichever machine you are viewing from.

On Volta:

```bash
ros2 launch foxglove_bridge foxglove_bridge_launch.xml port:=8765
```

On your viewing machine:

```bash
foxglove-studio
```

Installation for both is in
[workstation-setup.md](../00-onboarding/workstation-setup.md).

## 5. Individual launches

Use these when debugging one subsystem, not for a normal session. Starting a driver that
`system_bringup.launch.py` already started will produce duplicate nodes.

### Kairos controller

`shared_link_bridge` runs on Volta and speaks the SharedLink protocol to the P4S4 directly.
It is used in place of the vendor's Shepherd application, which runs on the OCU and is not
part of the current control path.

```bash
ros2 launch shared_link_bridge bringup.launch.py
```

### Ouster OS1-64

If you need to find the sensor:

```bash
avahi-browse -lrt _roger._tcp
```

Then launch. It takes a moment to come up:

```bash
ros2 launch ouster_ros driver.launch.py \
  params_file:=$HOME/ibex_ws/src/ibex/packages/ibex_bringup/config/ibex_ouster_sensor_config.yaml \
  viz:=false
```

Do not use the XML launch file. It writes a metadata file into the current working
directory:

```bash
# avoid
ros2 launch ouster_ros sensor.launch.xml sensor_hostname:=<hostname> viz:=false
```

> TODO(verify): replace the `$HOME` path with a package-relative one, something like
> `$(ros2 pkg prefix ibex_bringup)/share/ibex_bringup/config/...`, once it is confirmed
> that the config is installed into the share directory. The source cheat sheet hardcodes
> `/home/river`, which breaks for any other user.

Note that the Ouster's integration config lives in `ibex_bringup`, not inside the
`ouster-ros` submodule. That is deliberate — see the fork rule in
[_templates/README.md](../_templates/README.md).

### KISS-ICP odometry

```bash
ros2 launch kiss_icp odometry.launch.py topic:=/ouster/points
```

The package is `kiss_icp` with an underscore; the submodule directory is `kiss-icp` with a
hyphen.

### Insta360

```bash
ros2 launch insta360_ros_driver insta_bringup.launch.py equirectangular:=true
```

### Hyperspectral and RGB cameras

Set the USB buffer limit, unless the systemd unit from
[workstation-setup.md](../00-onboarding/workstation-setup.md) is installed and has already
done it:

```bash
echo 0 | sudo tee /sys/module/usbcore/parameters/usbfs_memory_mb
```

Find the camera's bus and device numbers, then grant access:

```bash
lsusb
sudo chmod 777 /dev/bus/usb/XXX/XXX
```

```bash
ros2 launch hyper_drive synchronous_cameras_launch.py
```

> The `chmod` resets on every replug and reboot. See
> [workstation-setup.md](../00-onboarding/workstation-setup.md) for the udev approach used
> for the spectrometers.

### Point spectrometers

```bash
sudo chmod 777 /dev/bus/usb/XXX/XXX
ros2 launch spectrometer_drivers ibsen_launch.py
```

> TODO(verify): confirm whether `ibsen_launch.py` brings up both the NIR and the VIS-NIR
> spectrometer or only one, and if only one, how the second is started.

### State estimation

```bash
ros2 launch ibex_state graph_frontender.launch.py
```

Runs the GTSAM factor graph. Configuration is in
`packages/ibex_state/config/graph_frontender_config.yaml`.

> TODO(verify): confirm what this expects to be running first. The graph consumes
> KISS-ICP odometry, the Ouster IMU, and GPS arriving through `shared_link_bridge`, so it
> presumably needs all three up. Record the required inputs and what happens if one is
> absent.

### Not currently launched

- **SICK picoScan 150** — currently unused. It is powered by the Kairos box and comes up
  at [power-on.md](power-on.md) step 3, but no driver is run against it. If that changes,
  the launch command belongs here.

## 6. Stopping the system

**Do this before [power-off.md](power-off.md).** Nothing should be capturing when power is
removed — that applies to the hyperspectral cameras, the point spectrometers, and the
Ouster alike.

1. Stop recording first, if a bag is running.
2. `Ctrl-C` each launch, in reverse order of starting. Camera and spectrometer drivers
   first, then odometry, then control, then the sensors.
3. Confirm nothing is left:

   ```bash
   ros2 node list
   ```

   An empty result means the stack is down.

4. Disarm at the VIM and continue with [power-off.md](power-off.md).

> TODO(verify): confirm whether `Ctrl-C` is sufficient for every driver, or whether any of
> them — `hyper_drive` in particular, given the Pleora and IMEC stacks underneath it — needs
> a graceful shutdown to release the hardware cleanly. If any driver can leave a camera in
> a bad state, that belongs here and on that package's software page.

## Known issues

- **CycloneDDS breaks the Alvium.** Do not set
  `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, despite the VimbaX documentation recommending
  it. The camera initializes and never streams. Our launch files use the default FastRTPS.
- **The XML Ouster launch file litters.** It writes a metadata file into whatever directory
  you ran it from. Use the Python launch file.
- **`min_scan_valid_columns_ratio` must be non-zero.** The Ouster config sets it to 0.1
  rather than the upstream default of 0.0, or KISS-ICP errors. See
  [ouster-ros.md](../04-subsystems/perception/software/ouster-ros.md).

## Related

- [power-on.md](power-on.md) and [power-off.md](power-off.md) — the sequences that bracket
  this
- [data-collection.md](data-collection.md) — recording and the metadata convention
- [launch-files.md](../05-reference/launch-files.md) — what each launch file contains
- [ros-graph.md](../05-reference/ros-graph.md) — topics, types, and rates
- [tf-frames.md](../05-reference/tf-frames.md) — the frame tree
- [`command_sheet.md`](../../../command_sheet.md) — flat copy-paste reference at the repo
  root
