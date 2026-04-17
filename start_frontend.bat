@echo off
cd /d "%~dp0frontend"

echo ==========================
echo   FRONTEND ODDSMATCHER
echo ==========================
echo.

if not exist node_modules (
    echo [1/2] Instalando dependencias npm...
    npm install
)

echo [2/2] Arrancando Vite...
npm run dev

pause