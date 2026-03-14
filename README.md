# BACnet BAS Simulator (PySide6 + BACpypes3)

Desktop building automation simulator for Niagara 4 training and testing.

## Python Version

- Target runtime: Python 3.11+
- Recommended: Python 3.11 or 3.12 (BACpypes3 compatibility is best on these versions)

## Features

- Multi-device project model with per-device BACnet identity
- Device transport modes:
  - BACnet/IP devices with IP + UDP port
  - BACnet MS/TP devices with parent IP device + MAC address
- BACnet object editing for:
  - Device
  - Analog Input / Output / Value
  - Binary Input / Output / Value
  - Multi-state Value
  - Schedule
  - TrendLog (with internal trend buffer)
- Built-in device templates:
  - AHU
  - VAV
  - Boiler
  - Chiller
  - Pump
  - Generic controller
- Simulation engine with behavior modes:
  - Constant
  - Manual
  - Random/noisy
  - Sine/drift
  - Linked
  - Logic-driven
  - Schedule-driven
- Internal logic rules (safe declarative rules, no arbitrary eval)
- Live value table and trend chart in GUI
- Runtime point registry with dirty-point tracking
- Protocol manager + protocol adapter layer
- BACnet protocol adapter (active)
- Modbus protocol adapter stub (registered, unavailable)
- MQTT protocol adapter stub (registered, unavailable)
- Portable project persistence (`.yaml`)

## Install

1. Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install requirements:

```powershell
pip install -r requirements.txt
```

## Launch

From the `bacnet_simulator` directory:

```powershell
python main.py
```

Or use one-click startup on Windows:

```powershell
.\run.bat
```

## Open Sample Project

- Sample project path: `sample_projects/training_lab.yaml`
- On startup, the app auto-loads this sample if present.

The sample includes:

- 3 BACnet/IP gateway devices (`JACE-9000-A/B/C`)
- MS/TP field devices grouped under those gateways:
  - AHU + 15 VAVs under `JACE-9000-A`
  - Boiler + Chiller + Pump panel under `JACE-9000-B`
  - 3 Generic field controllers under `JACE-9000-C`
- On BACnet/IP, each JACE publishes proxy points for its modeled MS/TP children.

## Running the Simulator

1. Click `Start` in the toolbar.
2. Simulation values begin updating at 1 second intervals.
3. Protocol manager starts available adapters:
   - BACnet adapter starts if BACpypes3 is available.
   - Modbus/MQTT stubs currently report unavailable.
4. Use `Pause`, `Resume`, `Stop`, and `Reset` as needed.

## Device Transport Fields

Per device:

- `transport`:
  - `ip` for BACnet/IP devices
  - `mstp` for BACnet MS/TP modeled devices
- `bacnet_ip` and `bacnet_port` are used for `ip` devices
- `mstp_parent` and `mstp_mac` are used for `mstp` devices

Current behavior:

- Any `ip` device can act as an MS/TP parent/gateway placeholder.
- `mstp` devices are currently modeled in project/runtime data and validation.
- Direct BACnet/IP bind is skipped for `mstp` devices in the BACnet server.
- Parent IP devices expose BACnet proxy points for child MS/TP devices.

## Niagara 4 Connection Guide

1. In Niagara Workbench, add a BACnet Network under your station.
2. Ensure Niagara and simulator machine can exchange UDP traffic.
3. Run Niagara/Workbench/YABE on a different host than the simulator for reliable discovery/import behavior.
4. In Niagara BACnet network, run `Discover` (Who-Is).
5. Add discovered devices.
6. Import points from each device.
7. Validate workflows:
   - discovery and object browsing
   - ReadProperty / ReadPropertyMultiple
   - WriteProperty on writable points
   - COV subscriptions on active points
   - schedules and occupancy-driven setpoints
   - histories and graphics against changing values

Use the test checklist:

- `docs/niagara_test_checklist.md`

## Same Machine vs Different Machine

- Use a separate machine for simulator and Niagara/Workbench/YABE.
- Single-machine runs are not considered supported for reliable BACnet discovery/import in this project.
- If on different subnets/VLANs, BACnet discovery may require BBMD/Foreign Device configuration.
## Architecture

```text
GUI (PySide6)
  -> ProjectModel / DeviceModel / ObjectModel
  -> SimulationEngine
     -> PointRegistry (runtime ownership lives here)
  -> ProtocolManager
     -> BacnetProtocolAdapter
     -> ModbusProtocolAdapter (stub)
     -> MqttProtocolAdapter (stub)
  -> Protocol runtimes (BACnet active)
```

Repository layout:

```text
bacnet_simulator/
  main.py
  requirements.txt
  README.md
  run.bat
  docs/
    niagara_test_checklist.md
    future_releases.md
    template_yaml_authoring.md
  app/
    gui/
    models/
    runtime/
    sim/
    protocol/
    bacnet/
    storage/
    utils/
  sample_projects/
    training_lab.yaml
```

- Default sample regeneration script: `scripts/generate_training_lab.py`
- New template/YAML guide: [docs/template_yaml_authoring.md](docs/template_yaml_authoring.md)

## Authoring
## Runtime Registry + Dirty Flow

- Registry ownership is in `SimulationEngine`.
- Protocol adapters receive the registry via `ProtocolManager`.
- Simulation writes changed point values into registry.
- Registry tracks dirty points and per-consumer pending state.
- Each adapter claims dirty refs for its own consumer name, syncs them, then marks consumed.
- Dirty flags clear only after all active consumers consume a point.

## Notes on BACnet/IP Emulation

- BACpypes3 is used for BACnet/IP device/object hosting.
- Each simulated BACnet/IP device has its own BACnet device instance.
- The simulator can bind each IP device to its own local IP address, or fall back to a shared bind IP.
- For larger proxy object lists, segmented responses are enabled to improve client browsing.
- BACnet manager runs in a dedicated worker thread with an asyncio event loop.
- Simulation-to-BACnet synchronization is driven by simulation tick notifications through the protocol manager.
## Network Setup (Alias Safety)

- Network settings let you select the host adapter and enable auto IP alias management.
- Alias management is add-only:
  - Does not change DHCP mode
  - Does not change DNS settings
  - Only attempts New-NetIPAddress for configured BACnet/IP device addresses
- Optional cleanup mode removes only aliases created by this app session on exit.
- On save, the app applies aliases immediately and logs:
  - requested / created / existing / errors
- If the selected adapter has no non-manual IPv4, the app warns before applying aliases.
## Response Behavior

- RESPONSE mode adds system-dynamics behavior (lag/inertia) without emulating controller firmware.
- `Out Of Service` in Object Editor freezes simulator writes (logic/schedule/response/scenario) for that point so manual testing commands do not get overwritten.
- Stability controls include:
  - Clamp by min/max
  - Optional max rate per second
  - Missing input policies: hold / skip / fallback
- Object Editor includes response presets and an Auto-Map button that fills refs using the selected device context.

## Troubleshooting

- If BACnet status says BACpypes3 unavailable, verify your venv and install with:

```powershell
pip install bacpypes3
```

- If Niagara does not discover devices:
  - check Windows firewall UDP rules
  - confirm subnet/broadcast settings
  - if using single-port discovery, verify each IP device alias exists on the simulator host and uses UDP `47808`







## Licensing & Commercial Use

This project uses a dual-use model:

- Free Community Edition for individual and non-commercial learning use.
- Paid Commercial License for business/consulting/internal training use.

Commercial use examples that require a paid license:

- internal corporate training labs
- consultant/client project usage
- paid training delivery
- operational use inside a business environment

Starter annual pricing:

- Solo consultant (1 user): USD 149
- Small company (2-20 users): USD 999
- Mid-size company (21-100 users): USD 2,999
- Enterprise (100+ users): custom quote

See [TERMS.md](TERMS.md) and [LICENSE-COMMERCIAL.md](LICENSE-COMMERCIAL.md).
Commercial licensing contact: `contact@cameratricain.com`
