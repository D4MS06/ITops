param(
    [string]$DestinationDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $DestinationDir) {
    $DestinationDir = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path "build_support\caddy\windows-amd64"
}

New-Item -ItemType Directory -Force -Path $DestinationDir | Out-Null
$zipPath = Join-Path $env:TEMP "caddy-windows-amd64.zip"
$exePath = Join-Path $DestinationDir "caddy.exe"

if (Test-Path $exePath) {
    Write-Host "Caddy deja prepare: $exePath"
    return
}

$release = Invoke-RestMethod -Uri "https://api.github.com/repos/caddyserver/caddy/releases/latest"
$asset = $release.assets | Where-Object { $_.name -match "windows_amd64\.zip$" } | Select-Object -First 1
if (-not $asset) {
    throw "Impossible de trouver l'asset Caddy Windows amd64."
}

Write-Host "Telechargement de Caddy depuis $($asset.browser_download_url)"
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath

Expand-Archive -Path $zipPath -DestinationPath $DestinationDir -Force
if (-not (Test-Path $exePath)) {
    throw "Le binaire caddy.exe est introuvable apres extraction."
}

Write-Host "Caddy prepare: $exePath"
