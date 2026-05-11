@echo off

cd /d "%~dp0python_survey" || exit /b 1


if not exist "venv" (
    python -m venv venv
)

call venv\Scripts\activate.bat
echo Installing dependencies...
pip install -q -r requirements.txt 2>nul || (
    pip install -r requirements.txt
)

python main.py

deactivate
pause
