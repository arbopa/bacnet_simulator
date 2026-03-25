# Windows Executable Build

This project can be packaged into a distributable Windows executable using PyInstaller.

## Quick Build

From repo root:

```powershell
.\build_exe.bat
```

Output:

- Executable: `dist/BACsim/BACsim.exe`
- Distributable folder: `dist/BACsim/`

## What Gets Bundled

- app code (`main.py`, `app/` modules)
- `sample_projects/`
- `docs/`
- `README.md`
- `TERMS.md`
- `LICENSE-COMMERCIAL.md`

The default sample project is loaded from bundled resources when present.

## Build Notes

- Recommended Python for runtime compatibility: 3.11 or 3.12.
- The build script uses a dedicated `.venv-build` environment.
- If your users need BACnet network alias management, they may still need admin privileges when using those functions.

## Release Checklist

1. Build: `build_exe.bat`
2. Smoke test:
   - app launches
   - sample project auto-loads
   - Start/Stop simulation works
   - BACnet adapter starts (if BACpypes3 dependencies are available)
3. Zip `dist/BACsim/` and share.
4. Include docs and licensing terms with release.