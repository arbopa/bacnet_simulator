# Template and YAML Authoring Guide

This guide explains how to add new realistic equipment points and how to build/edit project YAML safely.

## 1. Where to Add New Points

Main files:

- `app/models/template_defs.py`
- `app/sim/response_engine.py`
- `app/utils/validators.py` (only if you add new validation rules)

Flow:

1. Add points in the template function (`ahu_template`, `boiler_template`, etc.).
2. Wire behavior:
   - simple tracking: `BehaviorMode.LINKED`
   - command points: `BehaviorMode.MANUAL` or `LOGIC`
   - physical dynamics: `BehaviorMode.RESPONSE`
3. For new RESPONSE kinds, add a pure math function in `response_engine.py` and register it in `_RESPONSE_FUNCTIONS`.

## 2. Point Naming Convention

Use stable, operator-friendly names:

- Commands: `*Cmd`
- Feedback/status: `*Status`, `*Pos`
- Sensors: engineering name + unit context (`SupplyAirTemp`, `DuctStaticPressure`)
- Trends: `*Trend`

Examples:

- `SupplyFanCmd` / `SupplyFanStatus`
- `CondenserWaterValveCmd` / `CondenserWaterValvePos`
- `FreezeStat`

## 3. RESPONSE Model Pattern

Each model should:

1. Read numeric inputs defensively.
2. Compute a target value from inputs/params.
3. Apply first-order lag (`tau`) if appropriate.
4. Let `SimulationEngine` apply global clamp/rate limits from behavior config.

Keep functions pure: no direct project/model references inside response functions.

## 4. Building the Default Training Project

Use:

```powershell
$env:PYTHONPATH='.'
python scripts/generate_training_lab.py
```

What it does:

- rebuilds `sample_projects/training_lab.yaml` from current templates
- preserves intended topology (JACE gateways + MS/TP children)
- runs validation before save

## 5. Manual YAML Editing Tips

`training_lab.yaml` is loaded through `project_io` and supports YAML (preferred). JSON format also works because JSON is valid YAML.

High-level structure:

- `bacnet` settings
- `devices` list
- `logic_rules`
- `scenario`

Per device key fields:

- `transport`: `ip` or `mstp`
- `bacnet_ip`, `bacnet_port` for IP devices
- `mstp_parent`, `mstp_mac` for MS/TP devices

Per point key fields:

- `object_type`
- `present_value`, `initial_value`
- `writable`, `out_of_service`
- `behavior` (including `response_kind`, `response_inputs`, `response_params`)

## 6. Quick Validation Check

Use:

```powershell
$env:PYTHONPATH='.'
python -c "from app.storage.project_io import load_project; from app.utils.validators import validate_project; p=load_project('sample_projects/training_lab.yaml'); e=validate_project(p); print(f'errors={len(e)}'); print('\\n'.join(e[:20]))"
```

## 7. Recommended Workflow for New Equipment Realism

1. Add/adjust template points.
2. Add/adjust RESPONSE math if needed.
3. Regenerate training sample YAML.
4. Validate project.
5. Launch simulator and verify in BACnet client (YABE/Niagara).