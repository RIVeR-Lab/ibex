# IBEX

Multi-modal control off-road hyperspectral sensing and navigation platform built on a modified Yamaha Wolverine X4 850 R-Spec UTV.

<!-- Optional: badges, a photo of the platform, DEVCOM funding acknowledgment -->

## Overview

This platform brings together various systems in the effort of deploying a multi-modal off road vehicle. IBEX through the utilization of the Kairos Pronto 4 Series 4 off the shelf autonomy stack allows for multi-modal control. The system combines the ability to control the throttle, brake, transmission and steering wheel, with sensing capabilities from the hyperspectral array mounted to the roof of the vehicle. This array includes two hyperspectral cameras, that cover the range of 450nm-1700 (visible near infrared to shortwave infrared), two point spectrometers covering 500nm-1700nm, a 3D lidar, as well as two high powered RGB cameras, one with a dual fisheye lens for visualizaiton in the front and the back.
This repo contains all of the code required for operating the vehicle as well as maintianing the data stream from the vehicle.

This is the **top-level IBEX repository**. It does not contain source code directly —
instead, the ROS 2 packages that make up the system live under `Packages/`. Most are
included as **git submodules** (some are forks maintained by the lab, some track
upstream); a few packages are committed directly into the repo. You must clone
recursively (see Installation) or the submodule directories under `Packages/` will be
empty.

## Repository Structure

```
ibex/
├── Data/            # rosbag files
├── Docs/            # documentation, hardware notes, datasheets, IBEX user manual
├── Packages/        # ROS 2 packages: git submodules (forks + upstream) and some committed directly
├── .gitignore
├── .gitmodules      # submodule definitions (URL + path for each package)
├── README.md
└── command_sheet.md # quick-reference commands
```

### Packages

| Package | Type | Purpose | Upstream |
|---------|------|---------|----------|
| `Packages/hyper_drive` | in-repo | Hyperspectral camera driver | https://github.com/RIVeR-Lab/hyper_drive/tree/dev/ros2 |
| `Packages/hyper_drive_interface` | in-repo | message/service definitions for hyper_drive | https://github.com/RIVeR-Lab/hyper_drive/tree/dev/ros2 |
| `Packages/ibex_bringup` | in-repo | top-level launch / system bringup | — |
| `Packages/ibex_state` | in-repo | platform state estimation / publishing | — |
| `Packages/insta360_ros_drivers` | submodule (fork) | Insta360 X4 360° camera driver | https://github.com/RIVeR-Lab/insta360_ros_driver |
| `Packages/kiss-icp` | submodule (upstream) | LiDAR odometry front-end | https://github.com/PRBonn/kiss-icp/tree/1ffa7d7512f10bfc8b1185095011fa31184019e3|
| `Packages/ouster-ros` | submodule (fork) | Ouster OS1-64 LiDAR driver | https://github.com/RIVeR-Lab/ouster-ros |
| `Packages/shared_link_bridge` | submodule (fork) | Kairos P4S4 driver | https://github.com/RIVeR-Lab/shared_link_bridge |
| `Packages/spectrometer_drivers` | in-repo | Ibsen VNIR/NIR point spectrometer driver nodes | — |
| `Packages/spectrometer_interfaces` | in-repo | Message/service definitions for spectrometer_drivers | — |

Pinned submodule commits (from `git submodule status` / `.gitmodules`): `insta360_ros_drivers @ 15d0c2b`,
`kiss-icp @ 1ffa7d7`, `ouster-ros @ a46cda1`. `shared_link_bridge` [TODO: add pinned SHA].

<!-- "Type" tells a reader whether a folder is a submodule (and if a fork) or a package
committed directly into this repo. hyper_drive and hyper_drive_interface are committed
directly here but are derived from / kept in sync with an external reference package —
note that reference source and how updates flow. For the forked submodules, note which
branch is authoritative and why the fork exists (e.g. patches not yet upstreamed). The
canonical list of submodules is .gitmodules; anything under Packages/ not listed there
is committed directly. -->

## Prerequisites

- **OS:** Ubuntu 22.04
- **ROS 2:** Humble
- **Build tool:** colcon
- Git (with submodule support — any modern Git)
- Installtion of hyperspectral dependencies mentioned below in installation dependencies 
- Installtion of point spectrometer dependencies mentioned below in installation dependencies 

## 

## Installation

### 1. Create a colcon workspace and clone into it

This repo is a container, not a colcon workspace itself, so it lives inside a workspace's
`src/` directory. Create the workspace first, then clone into it. Because most packages
are git submodules, clone recursively:

```bash
mkdir -p ~/ibex_ws/src
cd ~/ibex_ws/src
git clone --recurse-submodules https://github.com/RIVeR-Lab/ibex.git
```

`--recurse-submodules` fetches the submodule packages under `Packages/`; the packages
committed directly into the repo come down as part of the normal clone. Both end up
populated.

**Already cloned without `--recurse-submodules`?** The submodules will be empty — pull
them in from inside the repo:

```bash
cd ~/ibex_ws/src/ibex
git submodule update --init --recursive
```

### 2. Install dependencies

[TODO: system-level deps that rosdep won't cover — e.g. the spectrometer driver needs
FTDI's libft4222 plus a udev rule. See Docs/<spectrometer note>.]

#### Installing Required Libraries

The following five libraries are required:

| Library | Version |
|---|---|
| IMEC HSI Mosaic | 1.12.0.0 |
| Ximea SDK | LTS v4.32.0.0 |
| Pleora SDK | 6.5.3 |
| Photon Focus SDK | 2025.1.0_Linux64 |
| Vimba X SDK | 2026-1 |

##### IMEC HSI Mosaic
Go to the [/ibex/docs](https://github.com/RIVeR-Lab/ibex/tree/dev/docs) and copy the contents of the `/place_in_opt` folder into `/opt`. The `/place_in_opt` should contain `/imec`, `/pleora`, and `/PFSDK_2025.1.0_Linux64`.

> **Note:** Copy the *contents* of the folder, not the folder itself. You will need superuser privileges to edit `/opt`. Run the following command to open the file explorer with superuser privileges:
> ```bash
> sudo nautilus
> `

##### Ximea SDK
Download the Ximea SDK (LTS v4.32.0.0)
- **URL:** https://www.ximea.com/software-downloads

Place the downloaded `.tgz` installer inside `/opt/imec/hsi-mosaic/resources/installers`

Follow the installation instructions on the website:
```bash
cd /opt/imec/hsi-mosaic/resources/installers
tar -xzf XIMEA_Linux_sp.tgz
cd package
sudo ./install
```

Run the following command to increase the USB buffer size for current login session:
```bash
echo 0 | sudo tee /sys/module/usbcore/parameters/usbfs_memory_mb
```

The below command will make inscreased USB buffer size permanent for all restarts:
```bash
sudo bash -c 'cat > /etc/systemd/system/usbfs-memory.service << EOF
[Unit]
Description=Set USB memory limit for XIMEA cameras

[Service]
Type=oneshot
ExecStart=/bin/sh -c "echo 0 > /sys/module/usbcore/parameters/usbfs_memory_mb"

[Install]
WantedBy=multi-user.target
EOF'
sudo systemctl enable usbfs-memory.service
sudo systemctl start usbfs-memory.service
```

To verify the XIMEA camera is working first connect the camera and then run the below command:
```bash
/opt/XIMEA/bin/xiSample
```

##### Vimba X SDK
Download the Vimba X SDK (VimbaX Setup-2026-2-Linux64.tar.gz) from:
- **URL:** https://www.alliedvision.com/en/support/software-downloads/vimba-x-sdk/vimba-x

Navigate to your Downloads and extract the file to `/opt`:
```bash
cd /Downloads
sudo tar -xzf VimbaX_Setup-2026-2-Linux64.tar.gz -C /opt
```

Run the GenTL installation scripts:
```bash
cd /opt/VimbaX_2026-2/cti
sudo ./Install_GenTL_Path.sh
sudo ./Set_GenTL_Path.sh
```

Install the ROS2 driver. Download `ros-humble-vimbax-camera-driver-1.0.0-amd64.deb` from:
- **URL:** https://github.com/alliedvision/vimbax_ros2_driver/releases/tag/v1.0.0
```bash
sudo apt install ./ros-humble-vimbax-camera-driver-1.0.0-amd64.deb
```

Verify the Vimba X SDK is working by opening the viewer:
```bash
/opt/VimbaX_2026-1/bin/VimbaXViewer
```

---

After installation, verify that the following directories exist in `/opt`:
```
/opt/imec
/opt/XIMEA
/opt/pleora
/opt/PFSDK_2025.1.0_Linux64
/opt/VimbaX_2026-1
```

---

##### OPTIONAL: Register IMEC Libraries with ldconfig

Skip this step on initial setup and only perform it if HSI Mosaic can't find its needed shared object (`.so`) files as indicated by the log in terminal when launching the nodes. The most common error is a Python `OSError` referencing `libhsi_api.so`, `libEbTransportLayerLib.so`, or similar.

The IMEC Python API uses `find_library()` which searches the ldconfig cache rather than `LD_LIBRARY_PATH`. The libraries must be registered with ldconfig for the API to load correctly:

```bash
sudo bash -c 'cat > /etc/ld.so.conf.d/imec.conf << EOF
/opt/imec/hsi-mosaic/bin
/opt/imec/hsi-mosaic/resources/installers/package/api/X64
/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib
/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam/bin/Linux64_x64
/opt/XIMEA/CamTool
/opt/PFSDK_2025.1.0_Linux64/lib
/opt/VimbaX_2026-1/api/lib
EOF'
sudo ldconfig
```

Verify with:
```bash
ldconfig -p | grep hsi_api
```
You should see `libhsi_api.so.1.0` listed.

#### Install Point Spectrometer Dependecies
Each spectrometer connects over an **FTDI FT4222H USB-to-SPI bridge**
(USB ID `0403:601c`). The driver talks to the Ibsen DISB board directly over
SPI, so the Ibsen protocol is implemented in the driver itself — there is no
separate "Ibsen SDK" to install. The only external library needed is FTDI's.

The C++ streamer links against FTDI's `libft4222` (which has the D2XX driver
built in on Linux — there is no separate `libftd2xx.so`).

##### Download

FTDI's direct download links expire, and `wget` against their CDN is often
blocked with `403 Forbidden`. Download through a browser instead:

1. Go to <https://ftdichip.com/software-examples/ft4222h-software-examples/>
2. Under **Linux Examples**, download the Linux `.tgz`
   (x86_64 / ARMv6-hf, includes C examples).
3. It will come out as a `.zip` file so you will need to go to the directory you download it into and unzip it for the next steps.

If you must use the command line, spoof a browser user-agent:

```bash
wget --user-agent="Mozilla/5.0 (X11; Linux x86_64)" \
     --referer="https://ftdichip.com/software-examples/ft4222h-software-examples/" \
     "<current-url-from-the-page>"
```

##### Install

```bash
tar zxvf libft4222-linux-*.tgz
sudo ./install4222.sh
sudo ldconfig
```

This places the library in `/usr/local/lib` and headers in
`/usr/local/include`. Verify:

```bash
ls /usr/local/lib | grep -i ft4222      # libft4222.so -> libft4222.so.x.y.z.w
ls /usr/local/include/libft4222.h /usr/local/include/ftd2xx.h
```

##### Make the library findable at runtime

Building may succeed while running fails with
`libft4222.so: cannot open shared object file`, because `/usr/local/lib` is not
always on the dynamic loader's search path. Add it once:

```bash
echo "/usr/local/lib" | sudo tee /etc/ld.so.conf.d/ftdi.conf
sudo ldconfig
ldconfig -p | grep ft4222               # should now list libft4222.so
```

##### USB permissions (udev rule)

By default a normal user cannot open the raw FT4222 USB device, so the driver
enumerates the devices but reads **blank descriptions** and reports
`NUMBER OF DEVICES: 0`. Grant access with a udev rule instead of running as
root:

```bash
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="601c", MODE="0666", GROUP="dialout"' | \
  sudo tee /etc/udev/rules.d/99-ftdi-ft4222.rules

sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then **unplug and replug** the spectrometers so the new permissions apply.

> A one-off `sudo chmod 666 /dev/bus/usb/<BUS>/<DEV>` also works but resets on
> every replug/reboot — use the udev rule for a persistent fix.

> **Note on `ftdi_sio`:** on some systems the kernel's `ftdi_sio` serial driver
> claims the device and exposes it as `/dev/ttyUSB*`, which blocks D2XX access.
> If `ls /dev/ttyUSB*` shows a device appearing when you plug in the
> spectrometer, unbind or blacklist `ftdi_sio` for these devices. On this setup
> `ftdi_sio` does **not** grab the FT4222, so no action was needed — check
> before doing anything global, since unbinding affects all FTDI serial
> devices.

#### Install ROS 2 Dependencies
Resolve ROS 2 package dependencies with rosdep:

```bash
cd ~/ibex_ws
sudo rosdep init   # first time only
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

### 3. Build

```bash
cd ~/ibex_ws
colcon build
source install/setup.bash
```

colcon discovers every package under `Packages/` and resolves build order from the
dependency graph. To build a single package instead:

```bash
colcon build --packages-select <package-name>
```

> Add the source line to your `~/.bashrc` so the workspace is available in every shell:
> ```bash
> echo "source ~/ibex_ws/install/setup.bash" >> ~/.bashrc
> ```

### 4. Verify the build

```bash
ros2 pkg list | grep <expected-package>
```

[TODO: a concrete smoke-test — e.g. launching a driver or listing expected executables.]

### 5: Connect the Cameras

> **The IMEC camera must be connected and disconnected in a specific order:**
> - **Connecting:** 1. Connect USB to computer; 2. Connect power
> - **Disconnecting:** 1. Disconnect power; 2. Disconnect USB from computer

The Ximea and Alvium cameras can be connected via USB in any order.

> **Recommended:** Plug each camera into a separate USB controller/bus where possible and do not plug into USB splitters. All three cameras combined have a data throughput of roughly 250MBps at 10 fps. A low USB bandwidth can cause dropped frames.

#### USB Camera Permissions

After connecting all cameras, set the correct USB permissions.

##### Option A — Temporary (per session)

This resets when the device is unplugged or the machine reboots, so it's mainly useful for a quick test:

```bash
# List connected USB devices and find the bus and device numbers
lsusb

# Set permissions for each camera (repeat for all three)
sudo chmod 777 /dev/bus/usb/[bus_number]/[device_number]
```

Run the `chmod` command three times — once for each camera (Pleora/IMEC, Ximea, Allied Vision).

##### Option B — Permanent (udev rule, recommended)

A udev rule reapplies the permissions automatically every time a camera is plugged in or the machine boots, so you never have to run `chmod` again. udev matches on the device's vendor/product IDs rather than bus/device numbers (which change on every reconnect), so the rule is stable.

First, find each camera's vendor and product ID with `lsusb`. Each line looks like:

```
Bus 002 Device 005: ID 24c2:1234 XIMEA ...
```

The `ID` field is `vendorID:productID` — here `24c2` is the vendor and `1234` is the product.

Create a rules file:

```bash
sudo nano /etc/udev/rules.d/99-hsi-cameras.rules
```

Add one line per camera, substituting the IDs you found (the `idProduct` line is optional — including it makes the rule specific to that exact model; omitting it applies to every device from that vendor):

```
# Pleora / IMEC
SUBSYSTEM=="usb", ATTR{idVendor}=="xxxx", ATTR{idProduct}=="xxxx", MODE="0666"
# Ximea
SUBSYSTEM=="usb", ATTR{idVendor}=="24c2", ATTR{idProduct}=="xxxx", MODE="0666"
# Allied Vision
SUBSYSTEM=="usb", ATTR{idVendor}=="xxxx", ATTR{idProduct}=="xxxx", MODE="0666"
```

`MODE="0666"` grants read/write to all users, which is the equivalent of your `chmod 777` for a character device (execute permission is meaningless here, so `0666` is the correct value rather than `0777`). If you'd rather scope access to a group instead of all users, use `MODE="0660", GROUP="plugdev"` and add your user to that group:

```bash
sudo usermod -aG plugdev $USER
```

Reload the rules and reapply them without rebooting:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then unplug and replug each camera (or reboot) so the new permissions take effect. Verify with:

```bash
ls -l /dev/bus/usb/[bus_number]/[device_number]
```

You should see `crw-rw-rw-` in the permissions column, confirming the rule applied.

### 6: Start and View Camera Output

In a terminal while in your workspace, launch all three cameras:

```bash
ros2 launch hyper_drive synchronous_cameras_launch.py
```

Or launch a single camera:
```bash
# IMEC
ros2 launch hyper_drive hyper_drive_launch.py camera_model:=imec frame_rate:=10 integration_time:=70

# Ximea
ros2 launch hyper_drive hyper_drive_launch.py camera_model:=ximea frame_rate:=30 integration_time:=15

# Vimba
ros2 run vimbax_camera_driver vimbax_camera_node
```

#### Viewing Camera Output

Use `ros2 run image_view image_view` to view individual topics. This renders much more smoothly than `rqt_image_view`, especially for high-rate or large-resolution streams:

```bash
# Raw RGB stream from the Alvium
ros2 run image_view image_view --ros-args -r image:=/camera/image_raw

# False-color composite of the XIMEA hyperspectral cube
ros2 run image_view image_view --ros-args -r image:=/visualizer/ximea/false_color

# False-color composite of the IMEC hyperspectral cube
ros2 run image_view image_view --ros-args -r image:=/visualizer/imec/false_color

# A specific band (e.g. band 6) of either camera
ros2 run image_view image_view --ros-args -r image:=/visualizer/ximea/band_6
ros2 run image_view image_view --ros-args -r image:=/visualizer/imec/band_6
```

To see all available topics:
```bash
ros2 topic list
```

> **Note:** `ros2 topic hz` on `/synchronous_cubes` sometimes fails to detect publication even when the topic is actively publishing.

## Usage

See `command_sheet.md` for a quick reference of common commands.

[TODO: a few representative launch commands, e.g.:]

```bash
# Example: spectrometer reference channel
ros2 launch spectrometer_drivers ibsen_launch.py
```

Recorded runs live in `Data/`; per-subsystem setup and field-test procedures are in `Docs/`.

## Working with Submodules

Update all submodules to the commits currently pinned by this repo:

```bash
git submodule update --init --recursive
```

Pull the latest changes from each submodule's tracked branch (only if you intend to
advance the pins):

```bash
git submodule update --remote
```

After updating submodule pointers, commit the new pins in this repo:

```bash
git add Packages/<name>
git commit -m "Bump <name> to <short-sha>"
```

**Editing code inside a submodule:** commit and push inside the submodule (`Packages/<name>`)
first, then commit the updated pointer here in `ibex`. A change isn't captured by the
top-level repo until you commit the moved pointer.

## Calibrating Hyperspectral Cameras
More information [here](https://github.com/RIVeR-Lab/hyper_drive/tree/dev/ros2#step-5-calibrate-the-imec-camera)

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `Packages/` subdirectories are empty after clone | Cloned without `--recurse-submodules`. Run `git submodule update --init --recursive`. |
| colcon finds no packages | The repo must be cloned inside the workspace's `src/` (i.e. `~/ibex_ws/src/ibex`). Build from `~/ibex_ws`, not from inside the repo. |
| `colcon build` fails on a missing dependency | Run the rosdep step; some drivers need system libs not covered by rosdep — see `Docs/`. |
| A submodule is on the wrong commit after pulling | Run `git submodule update --init --recursive` to reset submodules to the repo's pinned commits. |
| [TODO: known IBEX-specific gotcha] | [TODO] |

Imec, Pleora, and Photon Focus libraries can be installed separately from the corresponding vendor websites:

<details>
<summary><b>IMEC HSI Mosaic</b></summary>

- **URL:** https://imecinternational.sharepoint.com/sites/hsisupport
- **Contact:** hsisupport@imec.be (contact for portal access)
- Navigate to: `Camera > Software > HSI Mosaic` and download the Linux installer
- Extract and copy HSI-Mosaic to `/opt`

> The default installer installs version 2.11.10.0. Contact support to request version 1.12.0.0.

</details>

<details>
<summary><b>Pleora SDK</b></summary>

- **URL:** https://supportcenter.pleora.com/s/article/eBUS-SDK-6-x-x-Software-and-Release-Notes-Dwnload
- **Contact:** support@pleora.com (contact for access)
- **Account:** Email reichenberg.a@northeastern.edu for login credentials
- Place the downloaded `.tgz` installer inside `/opt/imec/hsi-mosaic/resources/installers`
- Install to the `/opt` folder

---

### Required Symbolic Links for HSI Mosaic

> **Note:** HSI Mosaic was developed for Ubuntu 18 and is not natively compatible with Ubuntu 22. The Pleora eBUS SDK 6.5.3 is Ubuntu 22 compatible, but HSI Mosaic still references the old library filenames. Symbolic links redirect HSI Mosaic to the updated libraries. This works because Pleora eBUS SDK 6.5.3 (Ubuntu 22) uses the same headers as 6.1.1 (Ubuntu 18).
>
> Pleora eBUS SDK 7.0.0 is **not** compatible with this approach — use version 6.5.3.

#### In `/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib`

Run the following commands:

```bash
cd /opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib

ln -s libPvBase.so.6.5.3.7155 libPvBase.so.6.1.1.5002
ln -s libPvBuffer.so.6.5.3.7155 libPvBuffer.so.6.1.1.5002
ln -s libPvDevice.so.6.5.3.7155 libPvDevice.so.6.1.1.5002
ln -s libPvGenICam.so.6.5.3.7155 libPvGenICam.so.6.1.1.5002
ln -s libPvSerial.so.6.5.3.7155 libPvSerial.so.6.1.1.5002
ln -s libPvStream.so.6.5.3.7155 libPvStream.so.6.1.1.5002
ln -s libPvSystem.so.6.5.3.7155 libPvSystem.so.6.1.1.5002
```

#### In `/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam/bin/Linux64_x64`

Run the following commands:

```bash
cd /opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam/bin/Linux64_x64

ln -s libGCBase_gcc48_v3_1.so libGCBase_gcc42_v3_1.so
ln -s liblog4cpp_gcc48_v3_4.so liblog4cpp_gcc42_v3_1.so
ln -s libNodeMapData_gcc48_v3_4.so libNodeMapData_gcc42_v3_1.so
```

</details>

<details>
<summary><b>Photon Focus SDK</b></summary>

- **URL:** https://www.photonfocus.com/support/software/
- Place the downloaded `.tgz` installer inside `/opt/imec/hsi-mosaic/resources/installers`
- Untar to the `/opt` folder

</details>

<details>
<summary><b>Vimba X</b></summary>

- **URL:** https://www.alliedvision.com/en/support/software-downloads/vimba-x-sdk/vimba-x
- **Note on middleware:** The VimbaX driver documentation recommends CycloneDDS:
```bash
sudo apt install ros-humble-rmw-cyclonedds-cpp
```
However, on Ubuntu 22.04 using this middleware by setting `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` explicitly in the launch file will break VimbaX's subscriber discovery. The camera initializes but never starts streaming. The launch files in this package therefore use the default FastRTPS middleware and no issues have been observed so far.

</details>

## Documentation

Hardware notes, datasheets, team-handoff documentation, and the **IBEX user manual**
live in `Docs/`. [TODO: link the user manual directly once its path is set, e.g.
`Docs/user-manual/README.md`.]

`command_sheet.md` (repo root) is a quick-reference cheat sheet for common commands.

## Acknowledgments

[TODO: DEVCOM funding, RIVeR Lab / Northeastern, contributors.]

## License

[TODO: license or "Internal — RIVeR Lab" if not open-sourced.]
