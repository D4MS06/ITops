param(
    [string]$PublicHost = "monitoring.mvl",
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$serviceName = "NetworkMonitoringCaddy"
$ruleName = "NetworkMonitoring HTTPS"
$appRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$caddyExe = Join-Path $appRoot "_internal\tools\caddy\windows-amd64\caddy.exe"
$programDataDir = Join-Path $env:ProgramData "NetworkMonitoringProject\caddy"
$configPath = Join-Path $programDataDir "Caddyfile"

if (-not (Test-Path $caddyExe)) {
    throw "Le binaire Caddy est introuvable: $caddyExe"
}

New-Item -ItemType Directory -Force -Path $programDataDir | Out-Null
@(
    "$PublicHost {"
    "    encode gzip zstd"
    "    tls internal"
    "    reverse_proxy $BackendHost`:$BackendPort"
    "}"
) -join [Environment]::NewLine | Set-Content -Path $configPath -Encoding ascii

& $caddyExe validate --config $configPath --adapter caddyfile | Out-Null

$serviceExists = $false
try {
    sc.exe query $serviceName | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $serviceExists = $true
    }
}
catch {
    $serviceExists = $false
}

if (-not $serviceExists) {
    $binPath = "`"$caddyExe`" run --config `"$configPath`" --adapter caddyfile"
    sc.exe create $serviceName "binPath= $binPath" "start= auto" | Out-Null
    sc.exe description $serviceName "Reverse proxy HTTPS NetworkMonitoringProject" | Out-Null
}

netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=443 | Out-Null

& $caddyExe reload --config $configPath --adapter caddyfile 2>$null
if ($LASTEXITCODE -ne 0) {
    sc.exe stop $serviceName | Out-Null
    Start-Sleep -Seconds 1
    sc.exe start $serviceName | Out-Null
}
