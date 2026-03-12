# Future Releases Backlog

## Architecture / Runtime

- Add explicit protocol lifecycle state in UI (per adapter: starting/running/stopped/unavailable).
- Add protocol adapter health checks and retry policies.
- Add metrics counters for dirty points processed per tick and per adapter.

## Protocol Scope

- Implement real Modbus adapter:
  - Config model for unit IDs / port / register map profile
  - Runtime mapping from `RuntimePoint` to holding/input registers
  - Write path (register writes -> runtime point updates)
- Implement real MQTT adapter:
  - Broker config + authentication model
  - Topic mapping strategy from `RuntimePoint` refs
  - Publish on change and optional retained state
  - Write/control subscription topics
- Keep protocol mappings independent from simulation model classes.

## BACnet Improvements

- Add optional COV-first push path backed by runtime registry changes.
- Add selective pullback optimization for writable points that were written since last tick.
- Expand integration tests for Read/Write/COV behavior with dirty-point consumer flow.

## Networking / Niagara Interop

- Add GUI BACnet network settings panel:
  - Bind IP selection
  - Base UDP port
  - Optional per-device network overrides
- Add explicit "single-host Niagara mode" wizard for local testing setup guidance.
- Explore optional multi-IP alias support (where OS/network adapter supports additional local IP bindings).

## Usability

- Add startup environment diagnostics panel (Python version, BACpypes3 status, port checks).
- Add connection-profile presets (Local Lab, Same Subnet, Routed/BBMD).
