@echo off
setlocal
echo Suche nach dem lokalen KitaFenster-Server auf Port 8088 ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'uvicorn' -and $_.CommandLine -match 'server.app:create_app' -and $_.CommandLine -match '8088' }; if ($p) { foreach ($i in $p) { Stop-Process -Id $i.ProcessId -Force; Write-Host ('Gestoppt: PID ' + $i.ProcessId) } } else { Write-Host 'Kein laufender KitaFenster-Server gefunden.' }"
timeout /t 3 >nul
endlocal
