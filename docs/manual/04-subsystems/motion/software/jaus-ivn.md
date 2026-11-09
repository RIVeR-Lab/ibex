---
status: draft
owner: TODO(verify)
last-verified: 2026-11-08
---

# JAUS_IVN

Kairos's Intelligent Vehicle Navigation software. **Runs on the P4S4 itself**, not on the
OCU, and holds the controller's persistent configuration. Serves
[Motion](../README.md).

> **This is where the P4S4's configuration actually lives.** Shepherd on the OCU is the
> route to it, not the thing itself — see
> [Where configuration lives](#where-configuration-lives).

## Source

| | |
| --- | --- |
| Vendor | Kairos Autonomi |
| Runs on | The Pronto4 / P4S4 unit |
| Reached via | VNC, from Shepherd's Assets tab on the OCU |
| Versions seen | 1.00.23 and 1.08.32, in vendor bulletin screenshots |
| In our repo | No — vendor software |

> TODO(verify): which version is installed on IBEX's P4S4. The two bulletin screenshots
> differ, and the Operation tab's layout changed between them.

## Where configuration lives

Four layers, and conflating them causes confusion:

| | Runs on | Role |
| --- | --- | --- |
| `shared_link_bridge` | **Volta** | Runtime commands over SharedLink UDP |
| **Shepherd** | **The OCU** | Operator app. Provides the **VNC button** that opens a session into the P4S4 |
| **JAUS_IVN** | **The P4S4** | The configuration application |
| **Dynamic Knowledge Store (DKS)** | **The P4S4** | Where persisted values are stored |

So the accurate statement is: **Volta commands the P4S4; the P4S4 configures itself
through JAUS_IVN, and the OCU is how you get to it.**

> TODO(verify): **does the OCU have to be the VNC client?** If Shepherd's VNC button opens
> an ordinary VNC session to the P4S4, any VNC client on the router network could
> potentially reach it — including Volta, at `192.168.200.220`. That would remove the
> dependency on a discontinued Panasonic CF-53 for configuration work.
>
> Shepherd may do more than plain VNC — asset discovery or tunnelling — so this needs
> testing rather than assuming. **It is worth testing**, because the CF-53 is currently a
> single point of failure for maintaining the vehicle. See
> [reorder.md](../../../99-appendix/reorder.md).

## Tabs

From the vendor bulletin's screenshots:

| Tab | Contains |
| --- | --- |
| Application | |
| JAUS Comms | |
| Mission | |
| **Payload & Data** | **The Dynamic Knowledge Store**, payload data, safety descriptors |
| **Operation** | Operational options, vehicle status, discrete devices, e-stop, telemetry |
| Payload Detail | |
| **P4S4 – ServoPod** | **Direct actuator control** — Steering, Brake, Throttle, Trans, Clutch, PWM4 |
| P4S4 – Drive | |

> TODO(verify): the tabs left blank. More vendor documentation is expected and will fill
> them in.

### P4S4 – ServoPod

Direct numeric control of each actuator, used during calibration. Text areas for
**Steering, Brake, Throttle, Trans, Clutch, PWM4**, each with a slider showing its range.

Also carries **Servopod Access** controls: `Calibrate` and `Force Zero` for steering,
`Clear Buffer`, `Packet Actv`, and engine controls `Enable Veh`, `Disable Veh`,
`Start Pulse`, `Motor Pwr On`, `Motor Pwr Off`.

> **This tab moves actuators directly.** Treat it as live whenever the VIM is armed — see
> [estop-chain.md](../../../01-safety/estop-chain.md).

### Operation — operational options

Checkboxes seen in the bulletin, with IBEX's state unrecorded:

| Option | In the screenshot |
| --- | --- |
| Park on Deadman Loss | checked |
| Enable Vehicle on Auto Mode | checked |
| Calibrate Steering Before Pathing | checked |
| **Bidirectional Shifting** | **checked** — see below |
| Park on Pause | unchecked |
| Ignore Park on e-stop | unchecked |

> TODO(verify): record IBEX's actual settings for all six. **"Park on Deadman Loss" in
> particular is safety-relevant** and interacts with the deadman behaviour documented in
> [estop-chain.md](../../../01-safety/estop-chain.md).

The Operation tab also exposes engine telemetry — temperature, odometer, RPM, battery
voltage, fuel level, oil pressure — and a velocity state sensor with roll, pitch, and yaw
rates.

> TODO(verify): whether any of that telemetry reaches SharedLink and therefore
> `/kairos_values`. If it does, it is a candidate input for state estimation — see
> [ibex-state.md](../../state-estimation/software/ibex-state.md#the-control-input-is-not-connected).

## Transmission calibration

**Source: Kairos Autonomi Bulletin BUL-023, *IVN DKS Settings Calibration*, v.01.00.01.**

### When this is needed

Whenever the mechanical relationship between the transmission actuator and the vehicle's
shifter changes:

- The transmission actuator connected, replaced, remounted, or its cable re-routed
- The shift linkage adjusted — including the routine adjustment in
  [maintenance.md](../../../03-base-vehicle/maintenance.md)
- Commanded gears no longer engaging reliably

**IBEX needed this after the P4S4's transmission motor was mechanically coupled to the
vehicle's transmission.** The factory default values were set for a different
installation and no longer mapped to real gear positions.

### Safety

**This procedure runs with the engine running and the transmission being shifted through
every gear.** It is not a bench task.

| | |
| --- | --- |
| Safety operator | **In the driver's seat, seat belt secured**, clear of all controls including the steering wheel, and positioned to reach the brake pedal |
| Engine | Running |
| Starting gear | Park — or Neutral on a vehicle without Park |
| Transmission cable | Connected |
| VIM | Must be armed for the actuator to move. Treat the actuator as live throughout |

Complete the normal inspections and preparation for the robot and OCU first — see
[checklists.md](../../../01-safety/checklists.md) and
[power-on.md](../../../02-operations/power-on.md).

### Prerequisites

| | |
| --- | --- |
| Cable | The P4S4's ethernet moved from the router to the OCU |
| Consequence | **Volta cannot reach the P4S4 while that cable is in the OCU** |
| Afterwards | **Move it back**, or `shared_link_bridge` will not connect |

**Record the existing DKS values before changing anything.** They live only in the P4S4,
and there is no backup.

### Step 1 — Open JAUS_IVN

1. In **Shepherd**, on the **Assets** tab, select the robot asset.
2. Click the **VNC** button.
3. In the VNC window, restore **JAUS_IVN**.

### Step 2 — Identify the shifting values

On the **P4S4 – ServoPod** tab:

1. Type `0` into the **Trans** text area and press Enter. **This fully extends the
   transmission cable**, which is the Park position.
2. Increment the Trans value and press Enter after each change, until the vehicle
   **solidly** shifts to the next gear. The bulletin's example steps 0 → 2 → 4 → 6 and so
   on until Reverse engages.
3. Note the value and which gear it produced — for example, `25` for Reverse from Park,
   `32` for Neutral from Reverse.
4. Repeat until you have a value for each of:

| | Transition |
| --- | --- |
| i | to Reverse from Park — use Reverse from Neutral if the vehicle has no Park |
| ii | to Neutral from Reverse |
| iii | to Forward, i.e. Drive |
| iv | to Neutral from Forward |
| v | to Reverse from Neutral |
| vi | to Reverse from **both** Park and Reverse |
| vii | to Neutral from **both** Reverse and Forward |

**"Solidly" is the operative word.** A value that shifts intermittently will fail in the
field.

> TODO(verify): **the Wolverine has two forward gears, High and Low.** The procedure
> provides a single `calForward`. Establish which gear IBEX's `calForward` selects and
> whether the P4S4 can reach the other at all. This is not addressed in the bulletin and
> matters for low-speed, high-torque work on soft ground.

### Step 3 — Enter and persist the values

On the **Payload & Data** tab, in the **Dynamic Knowledge Store** area:

1. Scroll to and expand the **Transmission** section.
2. Expand the entry you are setting, starting with **`calReverseFromPark`**.
3. **Click and hold** the **Current** value until it highlights.
4. Type the value identified in Step 2.
5. Press **Enter**.
6. Click the **Persist Data** button.

**Repeat 2–6 for each of the eight keys:**

| DKS key | Value |
| --- | --- |
| `calPark` | **0** — or the Neutral-from-Reverse value if the vehicle has no Park |
| `calReverseFromPark` | Reverse from Park |
| `calNeutralFromReverse` | Neutral from Reverse — or Reverse from Neutral if no Park |
| `calForward` | Forward / Drive |
| `calNeutralFromForward` | Neutral from Forward |
| `calReverseFromNeutral` | Reverse from Neutral |
| `calReverse` | Reverse from both Park and Reverse |
| `calNeutral` | Neutral from both Reverse and Forward |

> **`Persist Data` is what writes the value.** Typing and pressing Enter alone does not
> survive a power cycle.

### Step 4 — Verify the values were retained

Still on **Payload & Data**, in the **Dynamic Knowledge Store** area:

1. Scroll to and expand the **Transmission** section.
2. Click **Load DKS from JDR**. This refreshes the displayed values from storage.
3. Expand and confirm all eight keys hold the values you entered.

**This step is not optional.** It is the only confirmation that `Persist Data` worked.

### Step 5 — Finish

1. Close the VNC window.
2. **Move the P4S4's ethernet cable back to the router.**
3. Confirm `shared_link_bridge` connects — see
   [running-the-system.md](../../../02-operations/running-the-system.md).

> TODO(verify): **record IBEX's actual eight values here** once known. A configuration
> that exists in exactly one place, on a device with no backup, is a single point of
> failure — and re-deriving them means repeating this whole procedure with the engine
> running.

## Bidirectional shifting

**Push/pull cables have directional slack**, and that slack can change where a gear
engages depending on which direction the cable is moving. Kairos's answer is two values
for the same destination, one per approach direction.

| Mode | Uses | Accuracy |
| --- | --- | --- |
| **Bidirectional** — checked | `calReverseFromPark` **and** `calReverseFromNeutral` | **More accurate** |
| Non-directional — unchecked | `calReverse` alone | Less accurate |

The option is on the P4S4, in JAUS_IVN, under **Operation → Operational Options →
Bidirectional Shifting**.

**This is why Step 2 collects seven values for what looks like four gears.** The
directional pairs exist to absorb cable slack, and the non-directional values exist as the
fallback when the option is off.

> TODO(verify): confirm whether IBEX runs bidirectional or non-directional. It determines
> which of the eight DKS keys are actually in use, and therefore which matter most to get
> right. The bulletin's screenshot shows it checked, but that is the vendor's example, not
> our vehicle.

## Related pages

- [shepherd.md](shepherd.md) — the OCU application that opens the VNC session
- [kairos-p4s4-ocu.md](../hardware/kairos-p4s4-ocu.md) — the OCU, and the shared cable
- [kairos-p4s4.md](../hardware/kairos-p4s4.md) — the controller this runs on
- [actuators.md](../hardware/actuators.md) — the transmission actuator being calibrated
- [maintenance.md](../../../03-base-vehicle/maintenance.md) — shift linkage adjustment,
  which can invalidate these values
- [estop-chain.md](../../../01-safety/estop-chain.md) — the VIM arms the actuators
