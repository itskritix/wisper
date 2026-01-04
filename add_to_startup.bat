@echo off
echo Creating startup shortcut for Wisper...

set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\Wisper.lnk
set TARGET_PATH=%~dp0run_hidden.vbs

:: Create VBS script to run without console window
echo Set WshShell = CreateObject("WScript.Shell") > "%~dp0run_hidden.vbs"
echo WshShell.Run """%~dp0venv\Scripts\pythonw.exe"" ""%~dp0main.py""", 0, False >> "%~dp0run_hidden.vbs"

:: Create shortcut using PowerShell
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%TARGET_PATH%'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Wisper Speech to Text'; $s.Save()"

echo.
echo Done! Wisper will now start automatically when Windows boots.
echo.
pause
