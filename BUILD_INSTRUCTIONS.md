# Building FACOT for Windows

This guide explains how to build the FACOT application into a standalone Windows executable.

## Prerequisites

- Windows 10 or later
- Python 3.10 or later installed and in PATH
- Git (optional, for cloning the repository)

## Quick Build

1. Open Command Prompt or PowerShell in the FACOT project directory
2. Run the build script:
   ```cmd
   build_facot_exe.bat
   ```
3. Wait for the build to complete (may take 5-10 minutes)
4. Find the executable in `dist\facot.exe`

## What the Build Script Does

The `build_facot_exe.bat` script automatically:

1. **Creates a clean virtual environment** (`.venv_build`)
2. **Installs all dependencies** from `requirements.txt`
3. **Detects PyQt6 location** and includes WebEngine components:
   - QtWebEngineProcess.exe (required for PDF preview)
   - Qt6 resources (required for WebEngine rendering)
   - Qt6 translations (for internationalization)
4. **Packages application data**:
   - `templates/` - Invoice and quotation HTML templates
   - `themes/` - UI theme files
   - `assets/` - Icons, images, and other assets
   - `data/` - Database and configuration files
   - `firebase_credentials.json` (if present)
   - `facot_config.py` and `facot_config.json` (if present)
5. **Builds a single-file executable** using PyInstaller with:
   - Windowed mode (no console window)
   - Application icon (if available in `assets/`)
   - All Python dependencies embedded
   - Hidden imports for Firebase and other modules

## Build Output

```
dist/
  └── facot.exe      # Single-file executable (ready to distribute)

build/              # Temporary build files (can be deleted)
.venv_build/        # Virtual environment (can be deleted)
```

## Troubleshooting

### "Python not found"
- Ensure Python is installed and added to PATH
- Try running `python --version` to verify

### "Failed to install requirements"
- Check your internet connection
- Try manually installing: `pip install -r requirements.txt`
- Ensure you have the latest pip: `python -m pip install --upgrade pip`

### "QtWebEngineProcess.exe not found"
- Ensure PyQt6-WebEngine is installed: `pip install PyQt6-WebEngine`
- The script will warn but continue; PDF preview may not work

### Build succeeds but exe won't run
- Check Windows Defender or antivirus (they may block PyInstaller exes)
- Add an exception for `dist\facot.exe`
- Try running from command prompt to see error messages

### Missing data files at runtime
- Check that all required directories exist before building:
  - `templates/`
  - `themes/`
  - `assets/`
  - `data/`
- Verify the build script output shows "Including [directory]"

## Advanced: Using facot.spec

For more control over the build process, you can edit `facot.spec` and run:

```cmd
pyinstaller facot.spec
```

The spec file is pre-configured with all necessary data files and options.

## Distribution

The built `facot.exe` can be distributed as a single file. Users need:
- Windows 10 or later
- No Python or other dependencies (all included)

**Note:** First run may be slow as files are extracted. Subsequent runs will be faster.

## File Size

The executable will be approximately 150-250 MB due to:
- Embedded Python interpreter
- PyQt6 libraries
- Firebase libraries
- WebEngine components (large but necessary for PDF preview)

To reduce size, consider:
- Using PyInstaller's `--onedir` mode instead of `--onefile`
- Removing unused dependencies from `requirements.txt`
- Using UPX compression (already enabled in the spec file)

## Security Notes

- Windows Defender may flag PyInstaller executables as suspicious
- This is a false positive due to the packing method
- Users may need to add an exception or approve the first run
- Consider code signing the executable for production distribution

## Updating the Build

When the application code changes:
1. Pull latest changes from git
2. Re-run `build_facot_exe.bat`
3. The script will clean previous builds automatically

## Support

If you encounter issues:
1. Check the build script output for error messages
2. Review the PyInstaller build log in `build\facot\`
3. Ensure all dependencies are compatible versions
4. Try building in a fresh virtual environment

## Related Documentation

- [UI_THEME_FIX_SUMMARY.md](UI_THEME_FIX_SUMMARY.md) - UI theme fixes implemented
- [requirements.txt](requirements.txt) - Python dependencies
- [facot.spec](facot.spec) - PyInstaller specification file
