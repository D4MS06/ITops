param(
    [string]$DestinationDir = "",
    [string]$MariaDbVersion = "12.2.2"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $DestinationDir) {
    $DestinationDir = Join-Path (Resolve-Path (Join-Path $PSScriptRoot "..")).Path "build_support\mariadb\windows-amd64"
}

New-Item -ItemType Directory -Force -Path $DestinationDir | Out-Null
$msiName = "mariadb-$MariaDbVersion-winx64.msi"
$msiPath = Join-Path $DestinationDir $msiName
$downloadUrl = "https://downloads.mariadb.org/rest-api/mariadb/$MariaDbVersion/$msiName"

if (Test-Path $msiPath) {
    Write-Host "MSI MariaDB deja prepare: $msiPath"
    return
}

Write-Host "Telechargement de MariaDB depuis $downloadUrl"
Invoke-WebRequest -Uri $downloadUrl -OutFile $msiPath

if (-not (Test-Path $msiPath)) {
    throw "Le package MariaDB est introuvable apres telechargement."
}

Write-Host "MSI MariaDB prepare: $msiPath"
