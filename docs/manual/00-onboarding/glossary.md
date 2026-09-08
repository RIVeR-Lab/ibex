---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Glossary

One line per term, plus a link to the page that owns it. Definitions here are deliberately
short — this page exists so you can decode a sentence, not so you can learn a subsystem.

Terms marked TODO(verify) are ones nobody has pinned down yet. Several are vendor
abbreviations from Kairos documentation; those are tracked in
[open-questions.md](../99-appendix/open-questions.md).

## Platform and vehicle

| Term | Meaning |
| --- | --- |
| **IBEX** | The integrated research vehicle: the Wolverine base plus all autonomy, sensing, compute, and power hardware. Written in full caps as an acronym. TODO(verify): what the letters expand to. |
| **Wolverine** | The Yamaha Wolverine X-4 850 R-Spec (2022) side-by-side that IBEX is built on. Used when talking about the unmodified base vehicle. See [03-base-vehicle/](../03-base-vehicle/). |
| **UTV** / **side-by-side** | Utility task vehicle. The vehicle class the Wolverine belongs to. |
| **RIVeR Lab** | The lab at Northeastern that owns IBEX. TODO(verify): expansion of the acronym. |
| **DEVCOM** | U.S. Army Combat Capabilities Development Command. Funding source. TODO(verify): correct acknowledgment wording. |
| **EXP** | The Northeastern building whose high bay is IBEX's primary indoor test space. See [field-sites.md](../02-operations/field-sites.md). |
| **Olin** | A secondary field test site. See [field-sites.md](../02-operations/field-sites.md). |
| **SOP** | Standard operating procedure. The agreed safety standard governing vehicle use in the EXP high bay. See [01-safety/sop.md](../01-safety/sop.md). |

## Motion and drive-by-wire

| Term | Meaning |
| --- | --- |
| **P4S4** | Kairos Pronto 4 Series 4. The drive-by-wire system that actuates throttle, brake, steering, and transmission. See [kairos-p4s4.md](../04-subsystems/motion/hardware/kairos-p4s4.md). |
| **Kairos Autonomi** | Manufacturer of the P4S4 and the Shepherd application. |
| **OCU** | Operator Control Unit. The rugged laptop the operator uses to teleoperate or oversee IBEX. |
| **Shepherd** | The Kairos application running on the OCU. Not in our repository. See [shepherd.md](../04-subsystems/motion/software/shepherd.md). |
| **SharedLink** / **djSharedLink** | The Kairos communication protocol between the P4S4 and a controlling computer. Wrapped for ROS 2 by `shared_link_bridge`. |
| **Deadman** | A control that must be held for drive input to be accepted. Releasing it stops commanded motion. |
| **Back-drivable** | Whether an actuator can be moved by hand while engaged. The P4S4 has known problems here — see [estop-chain.md](../01-safety/estop-chain.md). |
| **E-stop** | Emergency stop. IBEX has several, and they do not all cut the same things. See [estop-chain.md](../01-safety/estop-chain.md). |
| **JAUS** | Joint Architecture for Unmanned Systems. A protocol standard Shepherd can be configured against. |
| **Mobius** | An Autonomous Solutions Inc. product referenced in Kairos documentation. TODO(verify): relationship to Shepherd. |
| **IVN** | Referenced in Kairos documentation as a communication configuration. TODO(verify). |
| **VAK** | Named in Kairos documentation as ASI's Mobius vehicle control unit executable. TODO(verify). |
| **djDRIVEWB**, **djMimic**, **djBasis** | Kairos software components named in the Shepherd overview. TODO(verify). |

## Compute and networking

| Term | Meaning |
| --- | --- |
| **Volta** / **River-Volta** | The ASUS NUC 14 Performance that serves as IBEX's onboard compute. |
| **NUC** | Next Unit of Computing. Intel's small-form-factor PC line. |
| **Link-local** / **APIPA** | Automatic Private IP Addressing. Self-assigned addresses in `169.254.0.0/16`, used between Volta and the Ouster. Not stable across sessions. See [network.md](../05-reference/network.md). |
| **mDNS** | Multicast DNS. Resolves `.local` hostnames without a DNS server — how the Ouster is addressed reliably despite a shifting IP. |
| **MTU** | Maximum transmission unit. Packet size limit on an interface. |
| **Jumbo frames** | An MTU above the standard 1500 bytes, typically 9000. Relevant to high-rate point cloud traffic. |

## Sensing

| Term | Meaning |
| --- | --- |
| **HSI** | Hyperspectral imaging, or a hyperspectral imager. Captures many narrow spectral bands per pixel rather than three. |
| **VNIR** | Visible and near infrared. The shorter-wavelength half of IBEX's hyperspectral coverage. |
| **SWIR** | Short-wave infrared. The longer-wavelength half. |
| **NIR** | Near infrared. |
| **Cube** | A hyperspectral data cube: two spatial dimensions plus a spectral dimension. |
| **Point spectrometer** | Measures a full spectrum at a single point rather than across an image. |
| **IMEC** | Vendor of the SWIR hyperspectral camera. Also the HSI Mosaic software. |
| **Ximea** | Vendor of the VNIR hyperspectral camera. |
| **Ibsen** | Vendor of the Pebble NIR and Pebble VIS-NIR point spectrometers. |
| **DISB** | The Ibsen spectrometer board the driver talks to over SPI. TODO(verify): expansion. |
| **Allied Vision** | Vendor of the Alvium RGB camera. Also the Vimba X SDK. |
| **Alvium** | The Allied Vision RGB camera model on IBEX. |
| **Insta360** | Vendor of the X4 dual-fisheye 360° camera. |
| **Ouster** | Vendor of the OS1-64 3D lidar. |
| **OS1-64** | The Ouster lidar: 64 channels, 360° horizontal, 42.4° vertical. See [ouster-os1-64.md](../04-subsystems/perception/hardware/ouster-os1-64.md). |
| **SICK picoScan 150** | A second lidar on the platform. |
| **BMI085** | The Bosch IMU built into the OS1-64. |
| **Traversability** | Whether terrain can be driven over. The downstream product much of the sensing feeds. |

## Radiometry and spectral terms

What the hyperspectral cameras and point spectrometers actually measure. Units matter
here — several of these differ only by what they are normalized against.

| Term | Meaning |
| --- | --- |
| **Solid angle** | The three-dimensional equivalent of an angle: how wide a cone of directions is, measured as the patch it covers on a sphere centered on the viewpoint. Measured in steradians (sr); a full sphere is 4π sr. A plane angle measures spread across a flat plane; a solid angle measures spread through space. |
| **Radiant intensity** | Radiant power per unit solid angle, W·sr⁻¹. Used for point-like sources. |
| **Irradiance** | Radiant power per unit area arriving at a surface, W·m⁻². What the scene receives. |
| **Illumination** | General term for the light falling on a scene. Irradiance is the radiometric measure of it; the photometric counterpart, weighted for human vision, is illuminance in lux. |
| **Radiance** | The brightness of one patch of a scene along one direction: radiant power per unit projected area per unit solid angle, W·m⁻²·sr⁻¹. Because it is normalized by both area and solid angle, it is a property of the patch itself and does not change with distance from it. This is the quantity a camera samples, one line of sight per pixel. |
| **Spectral radiance** | Radiance resolved by wavelength, W·m⁻²·sr⁻¹·nm⁻¹. Instead of one brightness value, a full brightness-per-wavelength curve for the patch. This is what a hyperspectral camera records: one value per band, per pixel. |
| **Reflectance** | The fraction of incident radiant power a surface reflects. Dimensionless, 0 to 1, and wavelength-dependent — spectral reflectance is the curve. A property of the material rather than the lighting, which is why it is usually the target quantity: getting there from measured radiance requires calibration. |
| **Spectral range** | The span of wavelengths a sensor covers — the endpoints. Tells you where on the electromagnetic spectrum you are sensing. VNIR is conventionally around 400–1000 nm and SWIR around 1000–2500 nm; IBEX's actual coverage is narrower and is recorded on the individual hardware pages. |
| **Spectral resolution** | How finely the spectral range is divided: the width of each band, often given as FWHM, and the number of contiguous bands. Determines how much detail is resolvable within the range. |
| **Spatial resolution** | Fineness along the scene dimensions — the ground area one pixel covers. Determines the smallest distinguishable object. |
| **FWHM** | Full width at half maximum. The width of a spectral band measured where response falls to half its peak. The standard way of stating spectral resolution. |
| **GSD** | Ground sampling distance. The ground area a single pixel covers. |
| **IFOV** | Instantaneous field of view. The angular cone a single detector element sees; combined with range, it gives GSD. |
| **Intensity** (lidar) | Return signal strength in a lidar point cloud. Unrelated to radiant intensity above, despite the shared name — the OS1-64 reports a per-point intensity field. |

## Software packages

Ten packages under `packages/`. Four are git submodules.

| Package | Type | Purpose |
| --- | --- | --- |
| `hyper_drive` | in-repo | Hyperspectral camera driver. |
| `hyper_drive_interfaces` | in-repo | Message and service definitions for `hyper_drive`. |
| `ibex_bringup` | in-repo | Top-level launch and system bringup. Belongs to no single subsystem — see [launch-files.md](../05-reference/launch-files.md). |
| `ibex_state` | in-repo | Platform state estimation and publishing. |
| `spectrometer_drivers` | in-repo | Ibsen VNIR and NIR point spectrometer driver nodes. |
| `spectrometer_interfaces` | in-repo | Message and service definitions for `spectrometer_drivers`. |
| `ouster-ros` | submodule, RIVeR-Lab fork | Ouster OS1-64 lidar driver. |
| `insta360_ros_driver` | submodule, RIVeR-Lab fork | Insta360 X4 camera driver. |
| `shared_link_bridge` | submodule, RIVeR-Lab fork | Kairos P4S4 driver. Implements the SharedLink protocol for ROS 2. |
| `kiss-icp` | submodule, tracks upstream | Lidar odometry front-end. Not a fork — points at `PRBonn/kiss-icp`. |

## State estimation

| Term | Meaning |
| --- | --- |
| **ICP** | Iterative Closest Point. Aligns two point clouds by repeatedly matching nearest points. |
| **KISS-ICP** | "Keep It Small and Simple" ICP. Lidar odometry with minimal tuning. Produces relative pose estimates from consecutive scans. |
| **GTSAM** | Georgia Tech Smoothing and Mapping. Factor graph optimization library. TODO(verify): which package depends on it — it is not one of the ten. |
| **Factor graph** | An optimization structure where measurements constrain estimated poses. The back end of the pose pipeline. |
| **Preintegration** | Summarizing many IMU readings into one constraint between poses, so the optimizer does not carry every sample. |
| **Odometry** | Pose estimated by accumulating incremental motion. Drifts over time. |

## ROS 2 and build

| Term | Meaning |
| --- | --- |
| **ROS 2 Humble** | The ROS distribution IBEX targets. Paired with Ubuntu 22.04. |
| **colcon** | The build tool. Run from `~/ibex_ws`, never from inside the repository. |
| **rosdep** | Resolves declared package dependencies. Does not cover the vendor SDKs. |
| **ament** | The ROS 2 build system colcon drives. |
| **Workspace** | `~/ibex_ws`. Contains `src/`, `build/`, `install/`, `log/`. The repository lives at `src/ibex`. |
| **Monorepo** | One repository holding many packages, as opposed to one repository each. |
| **Submodule** | A repository referenced from inside another at a pinned commit. Empty until initialized. See [workstation-setup.md](workstation-setup.md). |
| **Pin** | The specific submodule commit the parent repository records. |
| **Fork** | A copy of an upstream repository the lab maintains its own changes on. |
| **Git LFS** | Large File Storage. An extension for versioning large binaries outside normal git objects. Under consideration for the vendor SDK trees. |
| **Bag** / **rosbag** | A recorded log of ROS messages. See [bag-schema.md](../05-reference/bag-schema.md). |
| **tf** / **tf2** | The ROS transform system. Tracks relationships between coordinate frames over time. |
| **REP-103** | The ROS convention fixing axis orientations and units: x forward, y left, z up. |
| **REP-105** | The ROS convention fixing frame semantics: `map`, `odom`, `base_link`, and how they relate. |
| **Static transform** | A frame relationship that does not change, published once from fixed values. Most of IBEX's mounting geometry. |

## Coordinate frames

Frame names appearing throughout the manual. The tree and its extrinsics live in
[tf-frames.md](../05-reference/tf-frames.md).

| Frame | Meaning |
| --- | --- |
| **World frame** | A fixed, non-moving reference that stays put while the vehicle moves through it. The stage: the vehicle drives around inside it, and past scans stay pinned where they were observed rather than following the vehicle. |
| `map` | A globally consistent world frame. Does not drift, but can jump when a global correction is applied — so it is unsuitable for anything requiring smooth motion. |
| `odom` | A locally smooth, continuous world frame. Never jumps, but drifts without bound over distance. Use it for short-horizon control; use `map` for global position. |
| `base_link` | The vehicle body frame. The reference everything else resolves against. |
| `front_bumper` | Intermediate frame in the chain toward the sensor rack. |
| `sensor_rack` | The roof-mounted structure carrying the sensors. |
| `os_mount` | The Ouster's mounting frame. Carries the lidar's tilt. |
| `os_sensor` / `os_lidar` | Frames the Ouster reports points in. Tilted — do not read raw z as height above ground. |

## Electrical and mechanical

| Term | Meaning |
| --- | --- |
| **System battery** | The 48 V 105 Ah Vatrer battery in the rear of the vehicle powering the research payload. Distinct from the vehicle battery. Note: the SOP's Appendix A still lists a Lossigy unit — that entry is stale. See [04-subsystems/power/](../04-subsystems/power/). |
| **Vehicle battery** | The 12 V battery under the hood that starts the Wolverine. See [batteries.md](../03-base-vehicle/batteries.md). |
| **VRLA** | Valve-regulated lead-acid. The battery type the Wolverine ships with. |
| **AGM** | Absorbed glass mat. A sealed lead-acid construction. The Renegade replacement battery is one. |
| **Renegade** | Brand of the AGM replacement vehicle battery. Has charging rules that differ from ordinary batteries — see [batteries.md](../03-base-vehicle/batteries.md). |
| **Vatrer** | Brand of the 48 V system battery. |
| **Buck converter** | Steps a higher DC voltage down to a lower one. How 48 V becomes the 12 V rails. |
| **Rail** | A distribution branch at a given voltage. Each component is fed by one — recorded on its hardware page. |
| **Inrush current** | The brief current surge when a circuit is first energized, well above steady-state draw. What the thermistors below exist to limit. |
| **NTC thermistor** | Negative temperature coefficient thermistor. Resistance falls as it heats, so it limits inrush current when cold and then gets out of the way. It must cool back to room temperature before it can limit again — the reason power cycling has a mandatory wait. See [power-off.md](../02-operations/power-off.md). |
| **Wheel chock** | A wedge placed against a tire to stop the vehicle rolling. Required whenever IBEX is parked in the high bay. |
| **Ultramatic** | Yamaha's V-belt continuously variable transmission with all-wheel engine braking. |
| **YFI** | Yamaha Fuel Injection. |
| **On-Command** | Yamaha's selectable drive system: 2WD, 4WD, and full differential lock. |
| **Diff lock** | Locks left and right wheels to the same speed. Traction at the cost of turning. |

## Vendor SDKs

Installation for all of these is in [workstation-setup.md](workstation-setup.md).

| Term | Meaning |
| --- | --- |
| **HSI Mosaic** | IMEC's hyperspectral software. Built for Ubuntu 18; needs symlinks to run on 22.04. |
| **Pleora eBUS SDK** | Transport layer the IMEC camera depends on. Version 6.5.3 specifically. |
| **Photon Focus SDK** | Vendor SDK in the hyperspectral chain. |
| **Vimba X** | Allied Vision's SDK for the Alvium camera. |
| **GenTL** | GenICam Transport Layer. The standard interface layer camera SDKs expose. |
| **FT4222H** | The FTDI USB-to-SPI bridge each Ibsen spectrometer connects through. USB ID `0403:601c`. |
| **D2XX** | FTDI's direct driver interface, built into `libft4222` on Linux. |
| **`ftdi_sio`** | The kernel serial driver that can claim an FTDI device and block D2XX access. |
| **udev rule** | A persistent device permission rule. Preferred over `chmod`, which resets on replug. |

## University and compliance

Terms from the SOP and the University's safety and waste processes. The SOP is the
authority for all of these — see [sop.md](../01-safety/sop.md).

| Term | Meaning |
| --- | --- |
| **IER** | The Northeastern lab the SOP is written around. RIVeR operates within it. TODO(verify): expansion, and RIVeR's exact relationship to it. |
| **OARS** | The Northeastern office that manages the EXP building and reviews SOP addenda. TODO(verify): expansion. |
| **Public Safety** | The Northeastern department that opens the high bay garage door, handles the ballasts, and clears the sidewalk for vehicle movement. |
| **SciShield** | The University's lab safety platform. Hosts the required safety training and the hazardous waste request system. |
| **Padir Lab** | The lab name IBEX's waste requests are filed under in SciShield. See [hazardous-waste.md](../01-safety/hazardous-waste.md). |
| **Policy 614** | Northeastern's Policy on Use of Vehicles for University Purposes. Applies to IBEX because it is a University vehicle. |
| **LOTO** | Lockout/tagout. Isolating an energy source and marking it so it cannot be re-energized while someone is working on it. |
| **Ballasts** | The barriers in front of the high bay garage door. Lowered and replaced by Public Safety around any vehicle movement. |
| **Air exchange delay** | The wait between driving a vehicle into the high bay and closing the door, so exhaust clears. Duration is still being determined by carbon monoxide sampling. |
| **SAA** | Satellite Accumulation Area. Where filled hazardous waste containers are staged for pickup. |
| **Lincoln MKZ** | The other autonomous vehicle sharing the EXP high bay, owned by a different lab. Covered by the same SOP but not by this manual. |
| **Addendum** | How a new vehicle is added to the SOP's scope, subject to OARS and Provost's Office approval. |

## Places and contacts

| Term | Meaning |
| --- | --- |
| **High bay** | The large open test space in EXP. |
| **MOM's Foxboro** | The dealer service department used for Wolverine mechanical work. See [troubleshooting.md](../03-base-vehicle/troubleshooting.md). |
| **U-Haul auto transport** | The trailer type used to move IBEX. The vehicle is too large for a standard 5' × 9' trailer. See [transport.md](../02-operations/transport.md). |
