@echo off
cd /d "%~dp0.."
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
set OPTILENS_PORT=8002
if exist .env for /f "usebackq tokens=1,* delims==" %%a in (`findstr /b OPTILENS_PORT= .env`) do set %%a=%%b
python manage.py runserver 127.0.0.1:%OPTILENS_PORT%
