---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Workstation setup

Get a machine from bare Ubuntu to a built Ibex workspace. Budget a few hours the first
time — most of it is vendor SDK installation.

Follow the sections in order. Sections 1–4 are required for any work on Ibex. Section 5
is only needed if you are working with the hyperspectral cameras or point spectrometers,
which is most people.

> `last-verified` on this page is unset because it has not yet been run start to finish on
> a clean machine. If you are the first person to do that, correct what is wrong and set
> the date.

## 1. Prerequisites

| Requirement | Version |
| --- | --- |
| OS | Ubuntu 22.04 |
| ROS 2 | Humble |
| Build tool | colcon |
| Git | any modern version, with submodule support |

Ubuntu 22.04 and Humble are not optional. The IMEC HSI Mosaic library was built for
Ubuntu 18 and is already being coaxed into working on 22.04 via symlinks (section 5);
a newer Ubuntu adds another layer of that problem.

## 2. Clone the repository

The `ibex` repository is a container, not a colcon workspace. It lives inside a
workspace's `src/` directory.

```bash
mkdir -p ~/ibex_ws/src
cd ~/ibex_ws/src
git clone --recurse-submodules https://github.com/RIVeR-Lab/ibex.git
```

`--recurse-submodules` populates the four submodule packages. The six packages committed
directly into the repository arrive with the normal clone.

If you already cloned without it, the submodule directories under `packages/` will be
empty:

```bash
cd ~/ibex_ws/src/ibex
git submodule update --init --recursive
```

Confirm all four are populated:

```bash
git submodule status --recursive
```

A `-` prefix means the submodule is still uninitialized. A `+` prefix means it is checked
out at a different commit than this repository pins.

## 3. Install ROS 2 dependencies

```bash
cd ~/ibex_ws
sudo rosdep init   # first time on this machine only
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

rosdep does not cover the vendor SDKs. Those are section 5.

## 4. Build

```bash
cd ~/ibex_ws
colcon build
source install/setup.bash
```

colcon discovers every package under `packages/` and resolves build order from the
dependency graph. Build from `~/ibex_ws`, never from inside the repository.

To build one package:

```bash
colcon build --packages-select <package-name>
```

Make the workspace available in every new shell:

```bash
echo "source ~/ibex_ws/install/setup.bash" >> ~/.bashrc
```

Verify:

```bash
ros2 pkg list | grep <expected-package>
```

TODO(verify): add a concrete smoke test here — a driver launch or an expected executable
list that confirms a good build rather than just a completed one.

## 5. Vendor SDK installation

Five libraries are required for the hyperspectral and spectrometer hardware:

| Library | Version |
| --- | --- |
| IMEC HSI Mosaic | 1.12.0.0 |
| Ximea SDK | LTS v4.32.0.0 |
| Pleora eBUS SDK | 6.5.3 |
| Photon Focus SDK | 2025.1.0_Linux64 |
| Vimba X SDK | 2026-2 |

Three of these ship in this repository under [`docs/place_in_opt/`](../../place_in_opt/).
The other two are downloaded from the vendor.

> TODO(verify): `docs/place_in_opt/` and `docs/installer_archive/` hold vendor SDK trees
> and installers as loose committed files, which every clone pays for. Decide between Git
> LFS and external fetching, then rewrite this section accordingly. Tracked in
> [open-questions.md](../99-appendix/open-questions.md).

### 5.1 IMEC HSI Mosaic, Pleora, Photon Focus

Copy the *contents* of [`docs/place_in_opt/`](../../place_in_opt/) into `/opt`. The folder
contains `imec/`, `pleora/`, and `PFSDK_2025.1.0_Linux64/`.

Copy the contents, not the folder itself. You need superuser privileges to write to
`/opt`:

```bash
sudo nautilus
```

### 5.2 Ximea SDK

Download LTS v4.32.0.0 from <https://www.ximea.com/software-downloads>, then place the
`.tgz` in `/opt/imec/hsi-mosaic/resources/installers`.

```bash
cd /opt/imec/hsi-mosaic/resources/installers
tar -xzf XIMEA_Linux_sp.tgz
cd package
sudo ./install
```

Raise the USB buffer limit for the current session:

```bash
echo 0 | sudo tee /sys/module/usbcore/parameters/usbfs_memory_mb
```

`0` means unlimited, which is the intent here — the Ximea camera will drop frames at the
default limit.

Make it persist across reboots:

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

Verify with the camera connected:

```bash
/opt/XIMEA/bin/xiSample
```

### 5.3 Vimba X SDK

Download `VimbaX_Setup-2026-2-Linux64.tar.gz` from
<https://www.alliedvision.com/en/support/software-downloads/vimba-x-sdk/vimba-x>.

```bash
cd ~/Downloads
sudo tar -xzf VimbaX_Setup-2026-2-Linux64.tar.gz -C /opt
```

Run the GenTL installation scripts:

```bash
cd /opt/VimbaX_2026-2/cti
sudo ./Install_GenTL_Path.sh
sudo ./Set_GenTL_Path.sh
```

Install the ROS 2 driver. Download `ros-humble-vimbax-camera-driver-1.0.0-amd64.deb` from
<https://github.com/alliedvision/vimbax_ros2_driver/releases/tag/v1.0.0>:

```bash
sudo apt install ./ros-humble-vimbax-camera-driver-1.0.0-amd64.deb
```

Verify by opening the viewer:

```bash
/opt/VimbaX_2026-2/bin/VimbaXViewer
```

### 5.4 Confirm the `/opt` layout

```
/opt/imec
/opt/XIMEA
/opt/pleora
/opt/PFSDK_2025.1.0_Linux64
/opt/VimbaX_2026-2
```

### 5.5 Pleora symlinks for HSI Mosaic

HSI Mosaic was built for Ubuntu 18 and references the old Pleora library filenames. The
eBUS SDK 6.5.3 shipped for Ubuntu 22 uses the same headers as 6.1.1 did for Ubuntu 18, so
symlinks under the old names redirect HSI Mosaic to the current libraries.

Use 6.5.3. eBUS SDK 7.0.0 is not compatible with this approach.

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

> TODO(verify): confirm `7155` is the correct build number for all seven libraries with
> `ls /opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/libPv*.so.6.5.3.*`. If HSI Mosaic still
> fails to load a `libPv*` object after this, a link name or build number is wrong.

```bash
cd /opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam/bin/Linux64_x64

ln -s libGCBase_gcc48_v3_1.so libGCBase_gcc42_v3_1.so
ln -s liblog4cpp_gcc48_v3_4.so liblog4cpp_gcc42_v3_1.so
ln -s libNodeMapData_gcc48_v3_4.so libNodeMapData_gcc42_v3_1.so
```

### 5.6 Point spectrometer dependencies

Each Ibsen spectrometer connects over an FTDI FT4222H USB-to-SPI bridge, USB ID
`0403:601c`. The driver implements the Ibsen protocol itself and talks to the DISB board
directly over SPI, so there is no Ibsen SDK to install. The only external library needed
is FTDI's `libft4222`, which has the D2XX driver built in on Linux.

**Download.** FTDI's direct links expire and `wget` against their CDN often returns
`403 Forbidden`. Use a browser:

1. Go to <https://ftdichip.com/software-examples/ft4222h-software-examples/>
2. Under **Linux Examples**, download the Linux `.tgz` (x86_64 / ARMv6-hf, includes C
   examples)
3. It arrives as a `.zip`; unzip it before continuing

If you must use the command line, spoof a browser user-agent:

```bash
wget --user-agent="Mozilla/5.0 (X11; Linux x86_64)" \
     --referer="https://ftdichip.com/software-examples/ft4222h-software-examples/" \
     "<current-url-from-the-page>"
```

**Install.**

```bash
tar zxvf libft4222-linux-*.tgz
sudo ./install4222.sh
sudo ldconfig
```

This puts the library in `/usr/local/lib` and headers in `/usr/local/include`. Verify:

```bash
ls /usr/local/lib | grep -i ft4222      # libft4222.so -> libft4222.so.x.y.z.w
ls /usr/local/include/libft4222.h /usr/local/include/ftd2xx.h
```

**Make it findable at runtime.** The build can succeed while running fails with
`libft4222.so: cannot open shared object file`, because `/usr/local/lib` is not always on
the dynamic loader's search path:

```bash
echo "/usr/local/lib" | sudo tee /etc/ld.so.conf.d/ftdi.conf
sudo ldconfig
ldconfig -p | grep ft4222               # should now list libft4222.so
```

**USB permissions.** A normal user cannot open the raw FT4222 device, so the driver
enumerates devices, reads blank descriptions, and reports `NUMBER OF DEVICES: 0`. Add a
udev rule rather than running as root:

```bash
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="601c", MODE="0666", GROUP="dialout"' | \
  sudo tee /etc/udev/rules.d/99-ftdi-ft4222.rules

sudo udevadm control --reload-rules
sudo udevadm trigger
```

Unplug and replug the spectrometers so the new permissions apply.

> A one-off `sudo chmod 666 /dev/bus/usb/<BUS>/<DEV>` also works but resets on every
> replug and reboot. Use the udev rule.

> **On `ftdi_sio`:** on some systems the kernel's `ftdi_sio` serial driver claims the
> device and exposes it as `/dev/ttyUSB*`, blocking D2XX access. If `ls /dev/ttyUSB*`
> shows a device appearing when you plug in a spectrometer, unbind or blacklist
> `ftdi_sio` for these devices. On the current setup `ftdi_sio` does not grab the FT4222,
> so no action was needed — check before doing anything global, since unbinding affects
> all FTDI serial devices.

### 5.7 Optional: register IMEC libraries with ldconfig

Skip this on initial setup. Do it only if HSI Mosaic cannot find its shared objects, which
shows up as a Python `OSError` referencing `libhsi_api.so`,
`libEbTransportLayerLib.so`, or similar when launching the nodes.

The IMEC Python API uses `find_library()`, which searches the ldconfig cache rather than
`LD_LIBRARY_PATH`, so the libraries have to be registered:

```bash
sudo bash -c 'cat > /etc/ld.so.conf.d/imec.conf << EOF
/opt/imec/hsi-mosaic/bin
/opt/imec/hsi-mosaic/resources/installers/package/api/X64
/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib
/opt/pleora/ebus_sdk/Ubuntu-22.04-x86_64/lib/genicam/bin/Linux64_x64
/opt/XIMEA/CamTool
/opt/PFSDK_2025.1.0_Linux64/lib
/opt/VimbaX_2026-2/api/lib
EOF'
sudo ldconfig
```

Verify:

```bash
ldconfig -p | grep hsi_api
```

`libhsi_api.so.1.0` should be listed.

## 6. Foxglove

Used for visualizing live and recorded data. Two pieces, installed in different places.

### foxglove_bridge — on Volta

The bridge runs on the robot and serves data to Studio over the network:

```bash
sudo apt install ros-humble-foxglove-bridge
```

### Foxglove Studio — on whichever machine you view from

1. Go to <https://foxglove.dev/download>.
2. Download the package matching your system architecture.
3. Install it:

   ```bash
   sudo apt install ./foxglove-studio-*.deb
   ```

Later updates come through apt normally:

```bash
sudo apt update && sudo apt install foxglove-studio
```

Launching both is covered in
[running-the-system.md](../02-operations/running-the-system.md).

## 7. Working with submodules

Reset all submodules to the commits this repository pins:

```bash
git submodule update --init --recursive
```

Advance a submodule to the latest commit on its tracked branch. Only do this when you
intend to move the pin:

```bash
git submodule update --remote
```

Commit the new pin in `ibex` after updating a pointer:

```bash
git add packages/<name>
git commit -m "Bump <name> to <short-sha>"
```

**Editing code inside a submodule:** commit and push inside `packages/<name>` first, then
commit the moved pointer in `ibex`. A change is not captured by the top-level repository
until the pointer commit lands.

Three of the four submodules are RIVeR-Lab forks and one tracks upstream directly, which
changes where your commits should go. See the Fork status section on each package's
software page under [`04-subsystems/`](../04-subsystems/).

## 8. Acquiring the vendor SDKs directly

The copies under `docs/place_in_opt/` are the normal path. Use this section if you need a
fresh download or a different version.

### IMEC HSI Mosaic

- URL: <https://imecinternational.sharepoint.com/sites/hsisupport>
- Portal access: contact hsisupport@imec.be
- Navigate to `Camera > Software > HSI Mosaic` and download the Linux installer
- Extract and copy `HSI-Mosaic` to `/opt`

The default installer provides 2.11.10.0. We use 1.12.0.0 — request it from support.

TODO(verify): record why 1.12.0.0 is required over the newer default. Someone will
otherwise install the default and lose a day.

### Pleora eBUS SDK

- URL: <https://supportcenter.pleora.com/s/article/eBUS-SDK-6-x-x-Software-and-Release-Notes-Dwnload>
- Support: support@pleora.com
- Account: credentials are in the lab password manager
- Place the `.tgz` in `/opt/imec/hsi-mosaic/resources/installers` and install to `/opt`

Use 6.5.3. See section 5.5 for why the version matters.

### Photon Focus SDK

- URL: <https://www.photonfocus.com/support/software/>
- Place the `.tgz` in `/opt/imec/hsi-mosaic/resources/installers` and untar to `/opt`

### Vimba X

- URL: <https://www.alliedvision.com/en/support/software-downloads/vimba-x-sdk/vimba-x>

The VimbaX documentation recommends CycloneDDS as the ROS middleware. Do not set it.
Setting `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` explicitly in a launch file breaks
VimbaX's subscriber discovery on Ubuntu 22.04 — the camera initializes and never starts
streaming. Our launch files use the default FastRTPS middleware.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `packages/` subdirectories are empty after clone | Cloned without `--recurse-submodules`. Run `git submodule update --init --recursive`. |
| colcon finds no packages | The repository must sit at `~/ibex_ws/src/ibex`. Build from `~/ibex_ws`, not from inside the repository. |
| `colcon build` fails on a missing dependency | Run the rosdep step in section 3. Some drivers need system libraries rosdep does not cover — see section 5. |
| A submodule is on the wrong commit after pulling | `git submodule update --init --recursive` resets submodules to the pinned commits. |
| Python `OSError` on `libhsi_api.so` when launching HSI nodes | The IMEC libraries are not in the ldconfig cache. Do section 5.7. |
| `libft4222.so: cannot open shared object file` at runtime | `/usr/local/lib` is not on the loader path. See section 5.6. |
| Spectrometer driver reports `NUMBER OF DEVICES: 0` | Missing udev rule, or the device was not replugged after adding it. See section 5.6. |

## Next steps

- [day-one.md](day-one.md) — the reading path for your first day
- [glossary.md](glossary.md) — terms and acronyms used throughout the manual
- [`command_sheet.md`](../../../command_sheet.md) — quick reference for common commands
- [02-operations/running-the-system.md](../02-operations/running-the-system.md) — bringing
  up the stack on the vehicle
