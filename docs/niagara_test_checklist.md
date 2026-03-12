# Niagara Integration Checklist

Use this checklist when validating the simulator from Niagara Workbench.

## 1) Preflight (Simulator PC)

- [ ] `run.bat` launches app successfully
- [ ] Sample project loaded: `sample_projects/training_lab.yaml`
- [ ] Click `Start` and confirm log shows `BACnet running`
- [ ] Confirm devices are online in log (`AHU-1`, `VAV-*`, etc.)
- [ ] Windows Firewall allows inbound/outbound UDP on ports `47808-47829`

## 2) Network Preconditions

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

- [ ] Import points from AHU and at least one VAV
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

## 8) Optional Functional Training

- [ ] Build simple Niagara graphic bound to imported points
- [ ] Add one alarm extension and verify transitions
- [ ] Add one history extension and confirm samples/logging

## 9) Troubleshooting Notes

- If no devices discovered:
  - Verify simulator is still running
  - Verify IP/UDP/firewall settings
  - Try narrowing Who-Is range to known device instances (2000+)
- If points import but do not update:
  - Confirm simulator is not paused
  - Confirm values changing in simulator live table
- If cross-subnet discovery fails:
  - Configure BBMD/Foreign Device path in Niagara + network infrastructure
