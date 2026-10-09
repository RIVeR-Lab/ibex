---
status: draft
owner: TODO(verify)
last-verified: TODO(verify)
---

# Network

Every IP address, interface, and port on IBEX.

**Reference page.** For what rides on each segment see
[ros-graph.md](ros-graph.md); for powering the devices see
[04-subsystems/power/](../04-subsystems/power/README.md).

## Three segments, and they do not overlap

| Segment | Subnet | Carries | Physical |
| --- | --- | --- | --- |
| **Link-local** | 169.254.0.0/16 | Ouster point cloud and IMU | Direct cable, Volta to sensor |
| **IBEX router** | 192.168.200.0/24 | Drive-by-wire commands, SICK, operator access | TP-Link Archer A7, wired and wireless |
| **Lab wireless** | 192.168.0.0/24 | Volta's wireless, upstream connectivity | The lab's own network |

**Volta sits on all three.** That is deliberate for the first two and a liability for the
third — see [Volta is dual-homed](#volta-is-dual-homed).

## Address map

| Device | Address | Segment | Notes |
| --- | --- | --- | --- |
| **Volta** — `enp46s0` | `169.254.223.140/16` | Link-local | Onboard NIC, direct to the Ouster |
| **Volta** — `enxc8a362bd9823` | `192.168.200.199/24` | IBEX router | USB-C dock adapter |
| **Volta** — `wlo1` | `192.168.0.107/24` | Lab wireless | |
| **Ouster OS1-64** | `os-122540007570.local` | Link-local | Resolved by mDNS |
| **Kairos P4S4** | `192.168.200.220` | IBEX router | |
| **Router admin** | `192.168.200.1` | IBEX router | Web interface |
| **SICK picoScan 150** | TODO(verify) | IBEX router | Powered and cabled; no driver |
| **OCU (Panasonic CF-53)** | `192.168.200.30/16` | Direct to P4S4 | **/16 mask, unlike everything else** — see below |

> TODO(verify): the SICK's address. SICK scanners ship with a fixed factory address and
> usually need configuring onto the local subnet. See
> [sick-picoscan-150.md](../04-subsystems/perception/hardware/sick-picoscan-150.md).


## Volta's interfaces

Three, and **confusing them is the most common cause of a failed session**.

| Interface | Address | Purpose | Hardware |
| --- | --- | --- | --- |
| `enp46s0` | 169.254.223.140 | **Ouster only** | Motherboard ethernet port |
| `enxc8a362bd9823` | 192.168.200.199 | IBEX router | USB-C dock |
| `wlo1` | 192.168.0.107 | Lab wireless | Internal wifi |

**The lidar cable and the network cable must not be swapped.** Both are ethernet, both
land on Volta, and they do entirely different things.

### Checklist before connecting to Volta

1. Identify both ethernet interfaces: `ip link`
2. Confirm the **lidar** cable is on `enp46s0` and the **network** cable is on the dock
3. In NoMachine, verify the advertised address is the **network** interface's, not the
   lidar's
4. Confirm you can reach that address before doing anything else

> NoMachine binding to the link-local interface is a known failure: it advertises an
> address nothing can route to, and the connection simply fails.

## The link-local segment

The Ouster is cabled **directly to Volta's onboard NIC** with no switch. Volta's address on
this segment is auto-negotiated link-local, and the IPv4 method must be set to
**Link-Local Only** for it to come up.

| | |
| --- | --- |
| Volta — `enp46s0` | `169.254.223.140` |
| **Sensor** | **`169.254.105.158`** — set as a literal in the driver config |
| Sensor hostname | `os-122540007570.local` |
| Lidar data port | **Auto-assigned** — observed 58293 |
| IMU data port | **Auto-assigned** — observed 59631 |
| Configuration | TCP, Ouster's HTTP/TCP interface |

### The sensor's address is a hardcoded literal

`ibex_ouster_sensor_config.yaml` sets `sensor_hostname: '169.254.105.158'`.

**Link-local addresses are auto-negotiated**, so if the sensor ever picks a different one
the driver cannot find it. The sensor also advertises itself over mDNS as
`os-122540007570.local`, which would survive an address change.

> TODO(verify): consider using the mDNS hostname instead of the literal IP. The sensor's
> serial number is stable; its link-local address is not.

`udp_dest` is left **empty** in the config, so the driver determines the destination
itself rather than relying on a stored value — that part is not fragile.

### The data ports are auto-assigned and change between runs

`lidar_port: 0` and `imu_port: 0` mean "first available", so 58293 and 59631 are **what
this run happened to get**, not fixed values.

**Anything written against either those numbers or Ouster's 7502/7503 defaults will
break.** Use `ss -lunp` or the driver's startup log to find the current pair.

### MTU and fragmentation

Volta's MTU is 1500. The sensor has no MTU setting and emits UDP datagrams larger than
that, so **IP fragmentation is normal on this segment** rather than a fault.

## The IBEX router segment

A **TP-Link Archer A7** on Bank A, drawing 18 W — see
[power/](../04-subsystems/power/README.md). It provides both wired and wireless access on
`192.168.200.0/24`.

| | |
| --- | --- |
| Subnet | `192.168.200.0/24` |
| Admin interface | `http://192.168.200.1` |
| Wireless SSID | The "IBEX" network |

**This segment carries the drive-by-wire command path**, so congesting it has safety
implications:

```
Gamepad → shared_link_bridge (Volta) → SharedLink UDP → router → P4S4 (.220) → VIM → actuators
```

> TODO(verify): the SharedLink UDP port. The e-stop beacon uses 7001; the command path's
> port is unrecorded. See
> [shared-link-bridge.md](../04-subsystems/motion/software/shared-link-bridge.md).

**The router and the P4S4 share a power bank.** Cutting the Kairos box takes both down
together, so there is no state where powered actuators are waiting on a dead link — see
[estop-chain.md](../01-safety/estop-chain.md).

### The e-stop beacon broadcasts to the wrong address

`estop_beacon.py` sends 40-byte UDP packets to **`255.255.255.255` port 7001** at 1 Hz,
three copies per cycle.

**`255.255.255.255` is the global broadcast address**, and the kernel sends it out whichever
interface holds the default route. On a dual-homed host that may be `wlo1` — the lab
network — rather than the router segment where the P4S4 lives.

> TODO(verify): confirm which interface actually carries the beacon, and change it to the
> router segment's directed broadcast (`192.168.200.255`) or to the P4S4's address
> directly. **This is a safety path with no acknowledgement**, so a misdirected beacon
> fails silently. Recorded in full on
> [estop-chain.md](../01-safety/estop-chain.md).

## The lab wireless segment

Volta's `wlo1` connects to the lab's own network at `192.168.0.107`.

### Volta is dual-homed

Volta sits on both the IBEX router segment and the lab network simultaneously.

**Two consequences:**

**Reaching Volta works two ways**, which explains a long-standing troubleshooting note. The
recorded fix for NoMachine failures — "cycle through the IP addresses to see which one
allows connection" — is a dual-homing symptom:

| Your laptop is on | Reach Volta at |
| --- | --- |
| IBEX wireless | `192.168.200.199` |
| Lab wireless | `192.168.0.107` |

Both are correct; which one works depends on which network you joined.

**ROS 2 traffic reaches the lab network.** DDS uses unauthenticated multicast discovery and
will use every interface it finds. So IBEX's topics — including the drive-by-wire command
path — are discoverable by anything on `192.168.0.0/24`.

> TODO(verify): decide whether `wlo1` should stay up during operation. Options, in
> increasing effort: disable wireless while driving, restrict DDS to the router interface
> in the FastDDS profile, or accept it as a lab-internal risk and record that decision.
> **Any of the three is better than leaving it undecided.**

## DDS configuration

| | |
| --- | --- |
| Implementation | `rmw_fastrtps_cpp` — FastDDS |
| Profile | `/home/river/fastdds_ibex_config.xml` |

**Do not switch to CycloneDDS.** It breaks the Alvium camera's subscriber discovery on
Ubuntu 22.04 — the camera initializes and then never streams, with no error. VimbaX's own
documentation recommends CycloneDDS, so this is a trap worth knowing about. See
[alvium-rgb-camera.md](../04-subsystems/perception/hardware/alvium-rgb-camera.md).

> TODO(verify): **read the FastDDS profile and record what it configures.** It affects
> every node on the vehicle, it lives in a home directory rather than the repository, and
> it is currently documented nowhere. If it restricts interfaces, that bears directly on
> the dual-homing question above.

## Ports in use

| Port | Protocol | Purpose |
| --- | --- | --- |
| 58293 | UDP | Ouster lidar data → Volta |
| 59631 | UDP | Ouster IMU data → Volta |
| 7001 | UDP | E-stop beacon broadcast |
| 22 | TCP | SSH to Volta |
| 4000 | TCP | NoMachine, default |
| 80 | TCP | Router admin |
| TODO(verify) | UDP | SharedLink command path |
| TODO(verify) | — | SICK picoScan |

## Known issues

### The OCU's address and its odd subnet mask

| | |
| --- | --- |
| Address | `192.168.200.30` |
| Subnet mask | **`255.255.0.0`** — a /16 |
| Default gateway | `192.168.200.1` — the router |

No collision: `.1`, `.30`, `.199`, and `.220` are all distinct.

**The /16 mask is inconsistent with the rest of the vehicle**, where everything uses /24.
It makes the OCU treat all of `192.168.0.0/16` — 65,536 addresses — as directly reachable
on its own link, including the lab network at `192.168.0.0/24`.

**It works for what it is used for.** Calibration is a direct OCU ↔ P4S4 link, both are
inside the /16 and inside the /24, so they reach each other either way.

**Two things to be aware of:**

**The gateway is unreachable during calibration.** `192.168.200.1` is the router, and the
router is out of the path when the cable is moved to the OCU. So the OCU has no route off
the link — harmless, and arguably desirable during a safety-relevant operation.

**If the OCU is ever put on the router network, it will not reach the lab network.** The
/16 makes it ARP directly for `192.168.0.x` addresses instead of sending them to the
gateway, so that traffic black-holes rather than routing.

> TODO(verify): set the mask to `255.255.255.0` to match everything else, unless something
> about Shepherd requires otherwise. It costs nothing and removes a trap.

### The OCU shares the P4S4's cable

**The ethernet cable used to connect the OCU to the P4S4 is the same cable that connects
the P4S4 to the router.** The P4S4 has one ethernet port.

So steering calibration — which runs through Shepherd on the OCU — requires unplugging the
P4S4 from the router.

> **It must be moved back afterwards, or `shared_link_bridge` cannot reach the P4S4 at all.**
> This has caught people. See
> [kairos-p4s4-ocu.md](../04-subsystems/motion/hardware/kairos-p4s4-ocu.md).

### Two lidars, two segments, two power banks

| | Network | Power |
| --- | --- | --- |
| Ouster OS1-64 | Link-local, direct | Bank B, 24 V rail |
| SICK picoScan 150 | Router segment | Bank A, 12 V rail |

Nothing is wrong with this, but it means **no single cut takes both lidars down**, and the
two fail independently. Worth knowing when diagnosing.

### Volta's hostname resolution

`volta` and `volta.local` both work when both machines are on the same segment. `.local`
resolution needs mDNS, which is how the Ouster is found too:

```bash
avahi-browse -lrt _roger._tcp
```

## Verifying the network

```bash
# Volta's interfaces and addresses
ip link
hostname -I

# Is the Ouster visible over mDNS?
avahi-browse -lrt _roger._tcp

# Can Volta reach the P4S4?
ping 192.168.200.220

# Which interface holds the default route?  (bears on the e-stop beacon)
ip route get 255.255.255.255
ip route show default

# Is lidar data actually arriving?
sudo tcpdump -i enp46s0 udp port 58293 -c 5
```

> Record the output of `ip route show default` when verifying — it determines where the
> e-stop beacon goes.

## Open items

| Item | Why it matters |
| --- | --- |
| **E-stop beacon's actual egress interface** | Safety path, no acknowledgement, may be leaving via the wrong NIC |
| **`wlo1` during operation** — keep, restrict, or disable | ROS 2 traffic currently reaches the lab network |
| **FastDDS profile contents** | Affects every node, lives outside the repo, undocumented |
| **SharedLink command port** | The drive-by-wire path is undocumented at the network layer |
| **SICK address** | The device is on the vehicle and unaddressed here |
| **OCU uses a /16 mask** | Inconsistent with the rest; black-holes lab-network traffic if ever put on the router segment |
| **Ouster `udp_dest` hardcoding** | Silent data loss if Volta's link-local address shifts |

## Related

- [ros-graph.md](ros-graph.md) — what rides on these segments
- [estop-chain.md](../01-safety/estop-chain.md) — the beacon, and what each control cuts
- [shared-link-bridge.md](../04-subsystems/motion/software/shared-link-bridge.md) — the
  command path
- [ouster-ros.md](../04-subsystems/perception/software/ouster-ros.md) — the link-local
  configuration
- [kairos-p4s4-ocu.md](../04-subsystems/motion/hardware/kairos-p4s4-ocu.md) — the shared
  cable
- [power/](../04-subsystems/power/README.md) — which bank each network device sits on
- [workstation-setup.md](../00-onboarding/workstation-setup.md) — connecting to Volta
