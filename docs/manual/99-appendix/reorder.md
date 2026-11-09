---
status: draft
owner: TODO(verify)
last-verified: 2026-11-06
---

# Reorder

Identifiers, vendors, and ordering notes for everything on the vehicle, consolidated from
the hardware pages.

**This is the ordering view.** For what each component does, follow the manual page in the
last column.

> **This is not the dissertation parts list.** That is `bom.csv`, which covers the
> integration build — brackets, wiring, enclosures, tools, recovery gear — and overlaps
> this page on only three items. The two cover almost disjoint sets and both are needed.

## Before ordering a replacement

**Three components carry calibration tied to their serial number.** Swapping the hardware
invalidates the calibration, and a replacement needs new context files before it produces
usable data:

| Component | Tied to |
| --- | --- |
| IMEC SWIR camera | `config/imec/context/` and its `calibration_file/` |
| Ximea VNIR camera | `config/ximea/context/` and its `calibration_file/` |
| Both Ibsen spectrometers | On-board calibration coefficients read at driver startup |

The hyperspectral calibration workflow runs on Windows with the vendor GUI — see
`packages/hyper_drive/config/imec/README.md`. Budget that time into any replacement.

**Two components have a documented failure history.** The Kairos P4S4 was returned to the
manufacturer for a broken internal GPS cable, and the VATRER pack's LCD display is the
most frequently reported failure in its vendor reviews.

## Base vehicle

| Item | Identifier | Vendor | Manual page |
| --- | --- | --- | --- |
| Yamaha Wolverine X-4 850 R-Spec | 2022 model year | Yamaha, via Foxboro dealer | [specifications.md](../03-base-vehicle/specifications.md) |
| Vehicle battery | Renegade U1-35 AGM, 12 V 35 Ah | TODO(verify) | [batteries.md](../03-base-vehicle/batteries.md) |

> TODO(verify): the Wolverine's VIN and the Foxboro dealer's contact details. The dealer is
> referenced in [troubleshooting.md](../03-base-vehicle/troubleshooting.md) without a phone
> number.

> TODO(verify): the Renegade's full part number. "U1-35 AGM" is the group size and
> chemistry, not an orderable SKU.

## Perception

| Item | Identifier | Vendor | Manual page |
| --- | --- | --- | --- |
| Ouster lidar | OS1-64, serial **122540007570** | Ouster | [ouster-os1-64.md](../04-subsystems/perception/hardware/ouster-os1-64.md) |
| SICK 2D lidar | picoScan 150 — **variant unknown** | SICK | [sick-picoscan-150.md](../04-subsystems/perception/hardware/sick-picoscan-150.md) |
| SWIR hyperspectral camera | IMEC Snapshot SWIR 9, sensor ID **12.12.10.8** | IMEC | [imec-swir-hsi.md](../04-subsystems/perception/hardware/imec-swir-hsi.md) |
| VNIR hyperspectral camera | Ximea **MQ022HG-IM-SM5X5-NIR2**, sensor ID **13.7.8.4** | Ximea | [ximea-vnir-hsi.md](../04-subsystems/perception/hardware/ximea-vnir-hsi.md) |
| RGB camera | Allied Vision **Alvium 1800 U-507C**, GUID `DEV_1AB22C025217` | Allied Vision; bought via Edmund Optics | [alvium-rgb-camera.md](../04-subsystems/perception/hardware/alvium-rgb-camera.md) |
| 360° camera | Insta360 X4 | Insta360 | [insta360-x4.md](../04-subsystems/perception/hardware/insta360-x4.md) |
| VIS-NIR spectrometer | Ibsen PEBBLE, serial **58944** | Ibsen Photonics | [ibsen-vis-nir-spectrometer.md](../04-subsystems/perception/hardware/ibsen-vis-nir-spectrometer.md) |
| NIR spectrometer | Ibsen PEBBLE, serial **60044** | Ibsen Photonics | [ibsen-nir-spectrometer.md](../04-subsystems/perception/hardware/ibsen-nir-spectrometer.md) |

### Optics

| Item | Identifier | Fitted to |
| --- | --- | --- |
| SWIR lens | Navitar, 25 mm, **f/2.8**, exit pupil 65 mm | IMEC |
| VNIR lens | Edmund Optics, 25 mm, **f/1.4**, exit pupil 31.7 mm | Ximea |
| Alvium lens | TODO(verify) — C-mount, unrecorded | Alvium |

> **The declared f-number is an input to band-centre computation**, not only a record of
> the aperture. A different lens changes the reported wavelengths. See
> [ximea-vnir-hsi.md](../04-subsystems/perception/hardware/ximea-vnir-hsi.md#nominal-versus-effective-band-centres).

### Supporting hardware

| Item | Identifier | Notes |
| --- | --- | --- |
| Frame grabber | Pleora `iPORT-CL-U3-PT03-CL0UP04-128xU`, unit `28B702142385` | Serves the IMEC |
| USB-SPI bridges | FTDI **FT4222H**, USB ID `0403:601c`, ×2 | One per spectrometer |
| Reflectance reference | Spectralon puck — **grade unrecorded** | Roof-mounted |
| Fibre optic cables | TODO(verify) — ×2, unrecorded | Spectrometers |

> TODO(verify): the Spectralon's nominal reflectance and whether it came with a
> calibration certificate. Both determine what the spectrometers' white reference is worth.

## Motion

| Item | Identifier | Vendor | Manual page |
| --- | --- | --- | --- |
| Drive-by-wire controller | Kairos Pronto 4 Series 4 (**P4S4**) | Kairos Autonomi | [kairos-p4s4.md](../04-subsystems/motion/hardware/kairos-p4s4.md) |
| Vehicle Interface Module | VIM | Kairos Autonomi | [vehicle-integration-module.md](../04-subsystems/motion/hardware/vehicle-integration-module.md) |
| Operator Control Unit | Panasonic Toughbook **CF-53** | — | [kairos-p4s4-ocu.md](../04-subsystems/motion/hardware/kairos-p4s4-ocu.md) |
| Actuators | TODO(verify) | Kairos Autonomi | [actuators.md](../04-subsystems/motion/hardware/actuators.md) |

> **The CF-53 is long discontinued.** It runs Shepherd, which is Windows-only and supplied
> by Kairos. Replacing it means confirming with Kairos which Windows versions Shepherd
> supports before sourcing a machine.

> TODO(verify): Kairos Autonomi's ordering contact and support channel. They handled the
> P4S4's GPS cable repair, so a relationship exists — the contact is simply not recorded.

## Compute and network

| Item | Identifier | Manual page |
| --- | --- | --- |
| Onboard computer | ASUS NUC 14 Performance, **`NUC14SRLU9`**, SKU `NUC14SRKU9B00RU`, serial `T6ARQL00F662AJP` | [compute.md](../05-reference/compute.md) |
| Router | TP-Link **Archer A7** | [network.md](../05-reference/network.md) |

The NUC's internals, which are user-replaceable:

| | Fitted | Chassis maximum |
| --- | --- | --- |
| RAM | 64 GB DDR5 | **64 GB** — thermally limited, no headroom |
| Storage | 4 TB NVMe fitted, 8 TB understood | 3 × M.2 2280, up to 4 TB each |
| GPU | NVIDIA RTX 4070 Laptop | Not replaceable |

> TODO(verify): the storage question is open — `df` shows one 3.6 TB device while 8 TB is
> understood to be fitted. See
> [compute.md](../05-reference/compute.md#storage--and-a-discrepancy-worth-resolving).

## Power

Every item below is traced in the power budget appendix. See
[power/](../04-subsystems/power/README.md).

### Battery and charging

| Item | Identifier | Vendor | Notes |
| --- | --- | --- | --- |
| System battery | VATRER **`D-51.2V-105AH-JR-KB`** | Vatrer Power | $1,579.99 listed; 10-year warranty |
| Charger | 58.4 V LiFePO₄, 18–20 A | Supplied with the battery | Rating recorded two ways |
| LCD monitor | 2.8 in, supplied with the battery | Vatrer Power | **Most-reported failure item** |

**Vatrer contact:** `brand@vatrerpower.com`, +1 (660) 260-0222, 9 am – 5 pm EST.
Warranty registration at `vatrerpower.com/pages/register-warranty`.

> TODO(verify): was the warranty registered? A 10-year warranty on a $1,580 item is worth
> having active.

### Conversion and distribution

| Item | Identifier | Role |
| --- | --- | --- |
| Buck converter | Cllena, 51.2 → 12 V / 30 A | Bank A — P4S4, router, SICK |
| Buck converter | Cllena, 51.2 → 24 V / 20 A | Ouster and fans |
| Buck converter | Cllena, 51.2 → 24 V / 20 A | Inverter feed |
| Buck converter | Drok, variable, 51.2 → 6 V | Spectrometers and SWIR camera |
| Buck converter | Drok, adjustable, 51.2 → 19.6 V | Volta |
| Inverter | MEAN WELL **TS-1000-124**, 24 VDC → 120 VAC | **Capacity-limited to ≤480 W** by the Cllena ahead of it |
| Distribution block | RECOIL **DS21-516** | Bank A |
| Main bus bar | Red Wolf two-piece stud, 150 A / 48 V | |
| Fan speed controller | Gebildet PWM | Two enclosure fans |

### Protection and soft-start

| Item | Rating |
| --- | --- |
| Solid-state relay | okpac **SOM040100**, 100 V / 40 A MOSFET |
| Inrush thermistors | 10 Ω / 15 A NTC, **× 3 in series** |
| Pre-charge resistor | 220 Ω / 25 W |
| Zener clamp | 12 V, clamping to a measured 14.6 V |
| Timer relay | Drok, 6–30 V input |
| Main fuse | 35 A automotive |
| Bank A input fuse | 25 A |
| E-stop and latch buttons | 660 V, DC-13, **10 A thermal** |
| Bus bars 1 and 3 | 40 A |

> **The e-stop's 10 A thermal rating is below the pack's 13.9 A average draw.** Whether
> that matters depends on wiring that is not yet traced — see
> [estop-chain.md](../01-safety/estop-chain.md). **Resolve before ordering a
> replacement**, since a higher-rated switch may be the correct part.

## Consumables and spares worth holding

| Item | Why |
| --- | --- |
| Engine oil and filter | 50 hr / 200 mi service — [maintenance.md](../03-base-vehicle/maintenance.md) |
| Fuses, 35 A and 25 A | Single points of failure with no redundancy |
| Inrush thermistors | Wear items; three in series means any one failing opens the pre-charge path |
| Insta360 lens guards | Highest and most exposed component on the vehicle |
| VATRER LCD monitor | The only state-of-charge indication, and the most-reported failure |

> TODO(verify): confirm what the lab actually stocks. None of this is recorded, and the
> first four are cheap enough that not holding them is a false economy.

## Vendor contacts

| Vendor | Contact | For |
| --- | --- | --- |
| Vatrer Power | `brand@vatrerpower.com` · +1 (660) 260-0222 | System battery |
| Kairos Autonomi | TODO(verify) | P4S4, VIM, actuators, Shepherd |
| Ouster | TODO(verify) | OS1-64 |
| IMEC | TODO(verify) | SWIR camera, HSI Mosaic SDK |
| Ximea | TODO(verify) | VNIR camera, Ximea SDK |
| Allied Vision | TODO(verify) | Alvium, Vimba X SDK |
| Ibsen Photonics | TODO(verify) | Spectrometers |
| SICK | TODO(verify) | picoScan 150 |
| Yamaha — Foxboro dealer | TODO(verify) | Base vehicle service |

> TODO(verify): **this table is the single most useful thing to fill in on this page.**
> Eight of nine contacts are unrecorded, and most were established during procurement.
> Purchase records or the lab's ordering history would recover them quickly.

## Open items

| Item | |
| --- | --- |
| **Eight vendor contacts unrecorded** | Everything else here is identifiable; the contacts are not |
| **SICK picoScan variant** | Cannot be reordered or specified without it |
| **Alvium lens** | Unrecorded entirely |
| **Spectralon grade and certificate** | Determines what the white reference is worth |
| **Actuator part numbers** | Three actuators, none identified |
| **Fibre optic cables** | Two, unrecorded |
| **SICK motor base** | Not in the power budget either — may not be fitted |
| **Lead times** | Nothing recorded for any item |

## Related

- `bom.csv` — the dissertation parts list, covering the integration build
- [power/](../04-subsystems/power/README.md) — where the power chain is traced
- [compute.md](../05-reference/compute.md) — the NUC in detail
- [vendor-accounts.md](vendor-accounts.md) — portal and SDK-download accounts, names and
  URLs only
- Each hardware page's **Reorder** section, which this consolidates
