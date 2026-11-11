@echo off
setlocal
cd /d "%~dp0.."
echo === Optilens setup ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python est introuvable. Installez Python depuis python.org en cochant "Add python.exe to PATH".
    goto :fail
)
python --version

if not exist ".venv\Scripts\python.exe" (
    echo Creation de l'environnement Python...
    python -m venv .venv || goto :fail
)

echo Installation des composants...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt || goto :fail

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Fichier .env cree.
)

echo Mise a jour de la base de donnees...
".venv\Scripts\python.exe" -W ignore manage.py migrate || goto :fail

echo.
echo === Termine ===
echo - Pour reprendre les donnees d'un autre PC : copiez optilens.sqlite3 dans le dossier data\
echo - Pour une base vide, creez un utilisateur : .venv\Scripts\python manage.py createsuperuser
echo - Pour demarrer : double-cliquez sur scripts\Run Optilens.bat
echo.
pause
exit /b 0

:fail
echo.
echo *** Echec de l'installation. Lisez le message ci-dessus. ***
pause
exit /b 1
