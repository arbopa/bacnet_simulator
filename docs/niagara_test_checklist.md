# Niagara Integration Checklist

Use this checklist when validating the simulator from Niagara Workbench.

## 1) Preflight (Simulator PC)

- [ ] `run.bat` launches app successfully
- [ ] Sample project loaded: `sample_projects/training_lab.yaml`
- [ ] Click `Start` and confirm log shows `BACnet running`
- [ ] Confirm devices are online in log (`JACE-9000-*`)
- [ ] Windows Firewall allows inbound/outbound UDP on ports `47808-47829`

## 2) Network Preconditions

- [ ] Niagara/Workbench/YABE host is separate from simulator host
- [ ] Niagara host can reach simulator host IP
- [ ] Same subnet preferred for first test
- [ ] If routed/VLAN-separated, ensure BACnet broadcast strategy is defined (BBMD/Foreign Device)

## 3) Niagara Discovery

- [ ] Add BACnet Network in Niagara station
- [ ] Configure interface/network settings for simulator subnet
- [ ] Run discovery (Who-Is)
- [ ] Confirm simulator devices appear by instance/name
- [ ] Add discovered devices

## 4) Point Import + Read

- [ ] Import points from all discovered JACE devices
- [ ] Verify MS/TP child proxy points are visible under parent JACE devices
- [ ] Verify changing analog reads (ex: `AHU-1.OutdoorAirTemp`)
- [ ] Verify binary and multistate values read correctly

## 5) Write / Command Test

- [ ] Command writable point (ex: `AHU-1.SupplyFanCmd`)
- [ ] Confirm value changes in Niagara and simulator UI
- [ ] Release command and verify value returns/updates logically

## 6) COV + Activity

- [ ] Subscribe to COV on a changing analog point
- [ ] Confirm updates arrive without polling-only behavior

## 7) Schedule + Trend

- [ ] Read schedule objects (ex: `OccSchedule`)
- [ ] Confirm occupancy-driven points respond
- [ ] Verify trendable points update over time in Niagara history/trend views

## 8) Response Dynamics

- [ ] Verify AHU response dynamics (fan status delay, SAT lag, mixed air blending)
- [ ] Verify VAV response dynamics (damper-to-flow, flow influence on zone temp)
- [ ] Confirm trend lines show inertia (not instant jumps) for response points

## 9) Optional Functional Training

- [ ] Build simple Niagara graphic bound to imported points
- [ ] Add one alarm extension and verify transitions
- [ ] Add one history extension and confirm samples/logging

## 10) Troubleshooting Notes

- If no devices discovered:
  - Verify simulator is still running
  - Verify IP/UDP/firewall settings
  - Try narrowing Who-Is range to known device instances (1900-1902)
- If points import but do not update:
  - Confirm simulator is not paused
  - Confirm values changing in simulator live table
- If cross-subnet discovery fails:
  - Configure BBMD/Foreign Device path in Niagara + network infrastructure
