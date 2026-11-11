# Optilens — patient web system

Standalone Django application for optometry patient records (migration from FileMaker Pro 5).  
**Not connected** to Librairie Joukhadar — separate database, login, and port.

## Install

```powershell
cd C:\Optilens
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
```

## Run

```powershell
python manage.py runserver 127.0.0.1:8002
```

Or double-click `scripts\Run Optilens.bat`.

Open **http://127.0.0.1:8002/** and sign in.

## Import FileMaker data

### Direct import from `.fp5` (recommended)

From the Desktop copy of the database:

```powershell
cd C:\Optilens
python manage.py import_optilens_fp5 --commit
```

Default file: `C:\Users\RMJ\Desktop\FileMaker Pro 5\System\PATIEN~1 Copy.FP5`  
Séances: `SEANCE~1.FP5` in the same `System` folder (link **Nb** → patient).

```powershell
python manage.py import_optilens_visits --commit --seance-only
```

Uses [fp5dump](https://github.com/qwesda/fp5dump) (in `tools\fp5dump`). One patient row per name (latest FileMaker revision).

### CSV export (alternative)

1. Export CSV from FileMaker 5 (field names as headers).
2. **Import CSV** in the web UI, or:

```powershell
python manage.py import_optilens_patients "C:\path\patients.csv"
python manage.py import_optilens_patients "C:\path\patients.csv" --commit
```

## Data storage

Default: SQLite file `data\optilens.sqlite3`.  
For PostgreSQL, set `OPTILENS_DB_ENGINE=postgresql` and related variables in `.env` (see `.env.example`).

## Network access (LAN)

Add your PC name or IP to `OPTILENS_ALLOWED_HOSTS` in `.env`, then:

```powershell
python manage.py runserver 0.0.0.0:8002
```
