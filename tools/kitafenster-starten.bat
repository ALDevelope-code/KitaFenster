@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"
if errorlevel 1 exit /b 1
set "DATA_DIR=%ROOT%\local-data"
set "NAS_ROOT=%ROOT%\local-nas"
if not defined ADMIN_USERNAME set "ADMIN_USERNAME=admin"
if not defined ADMIN_PASSWORD set "ADMIN_PASSWORD=KitaLokal2026!"

REM Port 8088 schon belegt?
"%ROOT%\.venv\Scripts\python.exe" -c "import socket; s=socket.socket(); s.settimeout(1); raise SystemExit(0 if s.connect_ex(('127.0.0.1', 8088)) == 0 else 1)"
if %errorlevel%==0 (
  echo.
  echo Der Server laeuft schon: http://127.0.0.1:8088
  echo Stoppen geht ueber tools\kitafenster-stoppen.bat
  timeout /t 5 >nul
  exit /b 0
)

if not exist "%DATA_DIR%\kita.sqlite3" (
  echo Erstlauf: lege Admin-Konto und Beispieldaten an ...
  "%ROOT%\.venv\Scripts\python.exe" -m server.manage admin
  if errorlevel 1 exit /b 1
  "%ROOT%\.venv\Scripts\python.exe" -m server.manage demo
  if errorlevel 1 exit /b 1
)

echo.
echo ============================================================
echo  KitaFenster lokal:  http://127.0.0.1:8088
echo  Benutzer: admin     Passwort: KitaLokal2026!
echo  Beenden: Strg+C oder dieses Fenster schliessen
echo ============================================================
echo.
"%ROOT%\.venv\Scripts\python.exe" -m uvicorn server.app:create_app --factory --host 127.0.0.1 --port 8088
endlocal
