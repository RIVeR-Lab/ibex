---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Control modes

IBEX has three control modes. Each answers three questions differently: who decides what the
vehicle does, what moves the controls, and who checks the result and corrects it.

| Mode | Who decides | What moves the controls | Who checks and corrects |
| --- | --- | --- | --- |
| Manual | Human | Human, by hand and foot | Human |
| Teleoperation | Human | Kairos P4S4 | Human |
| Autonomy | IBEX | Kairos P4S4 | IBEX, with a human supervising |

## Manual

Manual operation is a human driver sitting inside of the vehicle controlling the steering
via directly handling the steering wheel, controlling the brake via directly pressing it
with their foot and the throttle via pressing that with their foot and changing gears as
they see fit through directly moving the transmission with their hands.

TODO(verify): state that the VIM is disarmed in manual mode. The actuators are live
whenever it is armed, and they have been hard to back-drive.

## Teleoperation

Teleoperation is a human driver controlling the performance of the vehicle where they
themselves are not manually making the changes but instead using direct teleoperation to
have a drive-by-wire system do it. In the case of Ibex this looks like a human operator
using a logitech game controller to command the kairos P4S4 to make changes to the vehicle
state. Kairos has direct control of the actuation of the steering wheel through the steering
ring that is attached via mounting brackets to the steering wheel. And a human operator uses
the right joy stick to move it around. The brake and the throttle are both attached to the
P4S4 and have attachments that move the actual pedals up and down depending on the value
sent to them. These are actuated when the human operator moves the left joy stick on the
controller. The transmission also has a connection to a motor on the P4S4 system and is
able to be modified when the game controller gives the shift command.

Open points:

- TODO(verify): the actuators page says throttle and brake act through cables onto the stock
  controls, and the brake interface is unrecorded. Align the wording once confirmed.
- Add how the operator sees the vehicle's response (from the cab, by line of sight, or by
  camera), the right-bumper deadman, and what releasing it does (the two-stage stop).

## Autonomy

Autonomous operation is the vehicle travelling from its starting point to a goal set by a
human operator, using its own decision-making, with no human input to the steering, brake,
throttle, or transmission. The operator sets the goal and supervises the run. A safety
operator can take control at any time through teleoperation, the emergency stop, or
disarming the vehicle integration module (VIM). IBEX tracks its own position using its
onboard state estimation. It perceives the terrain and obstacles around it using lidar and
the hyperspectral traversability model, then plans a route to the goal using its navigation
software. A vehicle control layer converts the planned speed and turning commands into
throttle, brake, steering, and gear values, sent to the Kairos P4S4 through the same path
used in teleoperation. Unlike teleoperation, where the operator watches the vehicle and
corrects it, in autonomous mode IBEX measures its own speed and steering and corrects them
itself.

Takeover is through teleop, the e-stop, or the VIM, not by grabbing the controls.

## Autonomy integration: what exists and what doesn't

| Layer | Status |
| --- | --- |
| Actuation | Done: the P4S4 moves all four controls on command |
| Vehicle control (speed to throttle and brake, turn rate to steering, gear logic) | Not built |
| Navigation (planning and path following) | Planned on an off-the-shelf stack (Nav2) |
| Terrain reasoning | The hyperspectral traversability model |

Constraints the vehicle control layer has to work within:

- **No speed feedback from Kairos** except GPS velocity at 10 Hz. Speed must come from state
  estimation (lidar odometry plus IMU).
- **No steering feedback** (`steerang` echoes the command), unless probing finds an encoder.
- **Kairos freezes actuators when motion is disabled**, so autonomy stops must use the
  two-stage stop.
- **Park is Neutral**, so the vehicle must be held with the brake at a goal.
- The bridge is the single point where the steering sign convention is converted: autonomy
  publishes `/vehicle_control` with positive = left, like Nav2.
