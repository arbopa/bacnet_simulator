# BACnet BAS Simulator (PySide6 + BACpypes3)

Desktop building automation simulator for Niagara 4 training and testing.

## Python Version

- Target runtime: Python 3.11+
- Recommended: Python 3.11 or 3.12 (BACpypes3 compatibility is best on these versions)

## Features

- Multi-device project model with per-device BACnet identity
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

- 1 AHU
- 15 VAVs
- 1 Boiler
- 1 Chiller
- 1 Pump panel
- 3 Generic controllers
- Total BACnet objects: 195

## Running the Simulator

1. Click `Start` in the toolbar.
2. Simulation values begin updating at 1 second intervals.
3. Protocol manager starts available adapters:
   - BACnet adapter starts if BACpypes3 is available.
   - Modbus/MQTT stubs currently report unavailable.
4. Use `Pause`, `Resume`, `Stop`, and `Reset` as needed.

## Niagara 4 Connection Guide

1. In Niagara Workbench, add a BACnet Network under your station.
2. Ensure Niagara and simulator machine can exchange UDP traffic.
3. In the simulator project, verify each device UDP port (default base 47808 and incremented per device).
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

- The simulator does **not** have to run on a different machine than Niagara.
- You can run both on one machine for quick testing.
- Running on a separate machine is also fine and often closer to field architecture.
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

## Runtime Registry + Dirty Flow

- Registry ownership is in `SimulationEngine`.
- Protocol adapters receive the registry via `ProtocolManager`.
- Simulation writes changed point values into registry.
- Registry tracks dirty points and per-consumer pending state.
- Each adapter claims dirty refs for its own consumer name, syncs them, then marks consumed.
- Dirty flags clear only after all active consumers consume a point.

## Notes on BACnet/IP Emulation

- BACpypes3 is used for BACnet/IP device/object hosting.
- Each simulated device has its own device instance and UDP port.
- BACnet manager runs in a dedicated worker thread with an asyncio event loop.
- Simulation-to-BACnet synchronization is driven by simulation tick notifications through the protocol manager.

## Troubleshooting

- If BACnet status says BACpypes3 unavailable, verify your venv and install with:

```powershell
pip install bacpypes3
```

- If Niagara does not discover devices:
  - check Windows firewall UDP rules
  - confirm subnet/broadcast settings
  - verify device UDP ports are reachable

