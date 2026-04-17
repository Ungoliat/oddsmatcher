@echo off
cd /d "%~dp0backend"

echo ==========================
echo   BACKEND ODDSMATCHER
echo ==========================
echo.

if not exist venv\Scripts\python.exe (
    echo [1/4] Creando entorno virtual...
    python -m venv venv
)

echo [2/4] Activando entorno...
call venv\Scripts\activate

if exist requirements.txt (
    echo [3/4] Instalando dependencias...
    python -m pip install -r requirements.txt
) else (
    echo [3/4] No existe requirements.txt en backend
)

echo [4/4] Arrancando FastAPI...
python -m uvicorn app.main:app --reload

pause