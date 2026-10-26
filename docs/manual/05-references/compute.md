---
status: draft
owner: TODO(verify)
last-verified: 2026-10-22
---

# Compute — Volta

The onboard computer. Everything in [Perception](../04-subsystems/perception/),
[State estimation](../04-subsystems/state-estimation/), and the ROS side of
[Motion](../04-subsystems/motion/) runs here.

**Reference page.** Volta belongs to no subsystem — like `ibex_bringup`, it is
cross-cutting. For its network interfaces see [network.md](network.md); for its power rail
see [power/](../04-subsystems/power/README.md).

## Identity

| | |
| --- | --- |
| Hostname | `volta` |
| User | `river` |
| Manufacturer | ASUSTeK Computer Inc. |
| Marketing name | ASUS NUC 14 Performance |
| Product name | `NUC14SRLU9` |
| SKU | `NUC14SRKU9B00RU` |
| Version | `90AR0042-M001F0` |
| Serial | `T6ARQL00F662AJP` |
| OS | Ubuntu 22.04 LTS, ROS 2 Humble |

> ASUS validates this unit for **Ubuntu 24.04 LTS**; 22.04 is not on its supported list.
> That is a deliberate choice — ROS 2 Humble targets 22.04 — but it means driver support
> for the Killer Wi-Fi and the I226-V NIC is outside what the vendor tested.

## Specifications

| | |
| --- | --- |
| CPU | Intel Core Ultra 9 185H |
| Topology | **16 cores / 22 threads** — 6 P-cores, 8 E-cores, 2 low-power E-cores |
| Clocks | 400 MHz – 5100 MHz |
| cTDP | 40–85 W |
| Memory | **62 GiB usable** (64 GB installed), DDR5 |
| Swap | 2 GiB |
| Discrete GPU | **NVIDIA GeForce RTX 4070 Laptop** — PCI `01:00.0`, device `2820` |
| Integrated GPU | Intel Arc — PCI `00:02.0`, device `7d55` |
| Wired NIC | Intel I226-V, 2.5 GbE |
| Wireless | Intel Killer Wi-Fi 6E AX1690i, Bluetooth 5.3 |
| Dimensions | 270 × 180 × 60 mm |
| Weight | 2.6 kg |

**64 GB is the maximum ASUS validates** for this chassis — the datasheet notes it is
limited by thermals rather than by the memory controller. There is no headroom to add RAM.

### There is a discrete GPU, and nothing currently uses it

An **RTX 4070 Laptop GPU** is fitted. No node in the stack uses it — KISS-ICP is
CPU-only, `ibex_state` runs GTSAM on the CPU, and `hyper_drive`'s processing is numpy and
OpenCV.

That matters for the traversability work: the hardware for training and for real-time
inference is already on the vehicle.

> TODO(verify): confirm the NVIDIA driver and CUDA are installed and working
> (`nvidia-smi`). A fitted GPU with no driver is a different situation from a fitted GPU
> with one, and neither is recorded.

> TODO(verify): the 330 W power budget was taken as a flat worst case. If the GPU is idle,
> real draw is well below that — and if it starts being used, draw rises toward it. See
> [power/](../04-subsystems/power/README.md#the-three-levers-in-order).

## Storage — and a discrepancy worth resolving

The machine is understood to have **8 TB** fitted. `df` shows one mounted NVMe:

| Device | Size | Used | Available | Mounted |
| --- | --- | --- | --- | --- |
| `/dev/nvme1n1p2` | 3.6 T | 1.5 T | **2.0 T** | `/` |
| `/dev/nvme1n1p1` | 511 M | 6.1 M | 505 M | `/boot/efi` |

**Only 2.0 TB is actually available**, on the root filesystem, which is 43% full.

The device is `nvme1n1`, which implies an `nvme0n1` exists and **is not mounted**. The
chassis has three M.2 slots.

> TODO(verify): find the rest. `lsblk` and `sudo fdisk -l` will show every device whether
> mounted or not. If a second drive is fitted and unmounted, mounting it and writing bags
> there solves two problems at once — see below.

### Recording to the root filesystem is the wrong default

Bags currently have nowhere else to go, and **filling `/` breaks the operating system**,
not just the recording. With 2.0 TB free and 43% already used, that is not a remote risk.

> TODO(verify): mount the second drive at something like `/data` and record there.

### Storage, not battery, limits spectral sessions

| Profile | Rate | Space for | Battery | **Binds on** |
| --- | --- | --- | --- | --- |
| Navigation | 32 MB/s | 17.4 h | 5 h | Battery |
| Spectral | 177 MB/s | **3.1 h** | 5 h | **Storage** |
| Everything | 400 MB/s | **1.4 h** | 5 h | **Storage** |

**A spectral collection session runs out of disk before it runs out of battery**, on the
current 2.0 TB. That inverts the planning assumption in
[bag-schema.md](bag-schema.md) and [field-sites.md](../02-operations/field-sites.md),
which both plan around the ~5 hour battery figure.

With the full 8 TB available the picture flips back — 12.6 h and 5.6 h respectively — and
battery becomes the constraint again. **So resolving the storage question is not
housekeeping; it decides how long a session can be.**

## Thermal limits

| | Range |
| --- | --- |
| **Operating** | **0 to 35 °C** |
| Storage | −40 to 60 °C |
| Humidity | 0–92% non-condensing |

**35 °C is the tightest operating ceiling on the vehicle** — tighter than the battery's
60 °C discharge limit, tighter than any sensor. And it is ambient *inside the enclosure*,
which runs hotter than outside air.

That is why there are two PWM-controlled fans in the Compute and Sensing box. They are run
at roughly 12 V against a 24 V rating to limit noise, drawing about 20 W of a possible
35 W — see [power/](../04-subsystems/power/README.md#there-is-active-cooling).

> **Running the fans harder in heat costs about 15 W**, which is under 5 minutes of
> endurance across a whole session. There is no power argument for throttling them on a
> hot day.

**The seasonal limits swap:**

| | Limiting component | Why |
| --- | --- | --- |
| Summer | **Volta** | 35 °C operating ceiling, in an enclosure |
| Winter | **The battery** | −10 °C storage floor, and heating only runs on charger input |

See [system-battery.md](../04-subsystems/power/system-battery.md#temperature-limits).

> TODO(verify): log CPU package temperature during a summer session (`sensors`). The
> ceiling is a datasheet figure; what the enclosure actually reaches is unknown.

## Power

| | |
| --- | --- |
| Vendor adapter | 19.5 VDC, 16.9 A, **330 W** |
| On IBEX | Drok buck, 51.2 V → **19.6 V** |
| Budgeted | 330 W flat, worst case |
| Share of payload | **~363 W at the battery — just over half** |

The vehicle feeds 19.6 V against the adapter's 19.5 V. That is within tolerance and not a
concern.

**Volta is the single largest load on the vehicle.** Measuring its true average draw — the
Drok converter has an onboard display — is the highest-value refinement available to the
power budget.

## Network interfaces

Three, and confusing them is a common cause of a failed session.

| Interface | Address | Purpose |
| --- | --- | --- |
| `enp46s0` | 169.254.223.140 | **Ouster only**, direct cable |
| `enxc8a362bd9823` | 192.168.200.199 | IBEX router, via the USB-C dock |
| `wlo1` | 192.168.0.107 | Lab wireless |

Full detail, including the dual-homing issue, is in [network.md](network.md).

The onboard RJ45 is the Intel I226-V; the dock hangs off the Thunderbolt 4 Type-C port.

## Access

### Over the network

```bash
ssh river@192.168.200.199      # on IBEX wireless
ssh river@192.168.0.107        # on lab wireless
ssh river@volta.local          # mDNS, same segment only
```

**Which address works depends on which network you joined** — see
[network.md](network.md#volta-is-dual-homed).

NoMachine is the graphical route. Connect to the IBEX network, open NoMachine, and look
for `volta`.

> If NoMachine will not connect, verify it is advertising the **network** interface's
> address and not the lidar's link-local one. Binding to `enp46s0` advertises an address
> nothing can route to.

### Headless and headed modes

Volta normally runs **headless** behind the rig, with no monitor.

> **Every mode switch must be run over SSH, never from a terminal inside NoMachine.**
>
> Each switch toggles `gdm3` or restarts the NX server — the exact display server a
> NoMachine terminal lives in. Running it from inside NoMachine drops your own session
> mid-command and locks you out. SSH is an independent channel and is unaffected.

**To headless:**

```bash
sudo systemctl disable --now gdm3 && sudo /etc/NX/nxserver --restart
```

Both commands are required. Running only the first leaves NoMachine unable to accept a
connection; recover by SSHing in and running the second alone.

On reconnecting, NoMachine may ask whether to create a new display. **Say yes** — that is
the virtual display you will work in.

**To headed:**

```bash
sudo systemctl enable --now gdm3
```

Then attach the monitor and reconnect. If the monitor stays dark:

```bash
xrandr --query                              # find the connector name
xrandr --output <CONN> --auto               # e.g. HDMI-1, DP-1
xrandr --output <CONN> --mode 1920x1080 --primary
```

**Before dropping into headless, write down the hostname and current addresses** while you
still have access:

```bash
hostname
hostname -I
```

SSH must be enabled for any of this to work, which survives reboots once set:

```bash
sudo systemctl enable --now ssh
```

## Files that live here and should not

Two pieces of live configuration sit in `/home/river/` rather than in the repository, so
both would be lost with the machine:

| File | What it is |
| --- | --- |
| `allied_vision_config.xml` | The Alvium camera's settings, passed to `vimbax_camera` |
| `fastdds_ibex_config.xml` | The DDS profile applied to every node on the vehicle |

> TODO(verify): move both into package `config/` directories and point the launch files at
> the installed share paths. See
> [launch-files.md](launch-files.md#config-files).

Also here, by convention rather than necessity:

| Path | Contents |
| --- | --- |
| `~/ibex_ws/` | The workspace |
| `~/ibex_ws/rosbag_library/` | Calibration bags — see [bag-schema.md](bag-schema.md) |
| `~/imec_light_reference/context` | Where `light_reference.py` writes a new context |

## Open items

| Item | |
| --- | --- |
| **The missing storage** | 8 TB expected, 2.0 TB available. `lsblk` will say where the rest is |
| **Bags are written to `/`** | Filling the root filesystem breaks the OS |
| **GPU driver status** | An RTX 4070 is fitted; whether CUDA works is unrecorded |
| **Measured power draw** | Budgeted flat at 330 W; the Drok displays the real figure |
| **Enclosure temperature in summer** | 35 °C ceiling, never logged |
| **Two configs outside the repo** | Not version-controlled |

## Related

- [network.md](network.md) — the three interfaces in detail
- [power/](../04-subsystems/power/README.md) — the 19.6 V rail and the payload budget
- [bag-schema.md](bag-schema.md) — what recording costs, and for how long
- [workstation-setup.md](../00-onboarding/workstation-setup.md) — building the workspace
- [power-on.md](../02-operations/power-on.md) and
  [power-off.md](../02-operations/power-off.md) — bringing Volta up and down in sequence
- [ros-graph.md](ros-graph.md) — what runs on it
