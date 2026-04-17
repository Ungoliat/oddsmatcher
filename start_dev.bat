@echo off
cd /d "%~dp0"

start "Oddsmatcher Backend" cmd /k ""%~dp0start_backend.bat""
start "Oddsmatcher Frontend" cmd /k ""%~dp0start_frontend.bat""

pause