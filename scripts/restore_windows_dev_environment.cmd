@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%restore_windows_dev_environment.ps1"
set "RESTORE_NMP_PS1=%PS_SCRIPT%"

if not exist "%PS_SCRIPT%" (
  echo Script PowerShell introuvable: "%PS_SCRIPT%"
  exit /b 1
)

powershell.exe -NoProfile -Command "$scriptPath = $env:RESTORE_NMP_PS1; $code = Get-Content -LiteralPath $scriptPath -Raw; & ([scriptblock]::Create($code)) @args" %*
exit /b %ERRORLEVEL%
