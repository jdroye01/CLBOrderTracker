@echo off
echo Building OrderTracker.exe...

REM Set path to PyInstaller
set PYI=%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts\pyinstaller.exe

REM Run PyInstaller with the correct options
"%PYI%" --onefile --windowed --icon=CLB_Logo.ico --add-data "CLB_Logo.ico;." --add-data "company_data.db;." OrderTracker.py

echo.
echo Build complete. EXE is in the /dist folder.
pause
