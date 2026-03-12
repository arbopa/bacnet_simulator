# Future Releases Backlog

## Networking / Niagara Interop

- Add GUI BACnet network settings panel:
  - Bind IP selection
  - Base UDP port
  - Optional per-device network overrides
- Add explicit "single-host Niagara mode" wizard for local testing setup guidance.
- Explore optional multi-IP alias support (where OS/network adapter supports additional local IP bindings).

## Protocol Scope

- Evaluate BACnet MS/TP simulation strategy:
  - Native MS/TP emulation, or
  - BACnet/IP-to-MS/TP gateway simulation mode for Niagara training workflows.

## Usability

- Add startup environment diagnostics panel (Python version, BACpypes3 status, port checks).
- Add connection-profile presets (Local Lab, Same Subnet, Routed/BBMD).
