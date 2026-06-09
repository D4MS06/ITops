param(
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 3306,
    [string]$DbName = "IT_DB",
    [string]$DbUser = "IT_DB_MVL",
    [string]$DbPassword = "Villeneuve@06!",
    [string]$RootPassword = "",
    [string]$ServiceName = "NetworkMonitoringMariaDB"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $RootPassword) {
    $RootPassword = $DbPassword
}

$appRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$mariadbMsi = Get-ChildItem (Join-Path $appRoot "_internal\tools\mariadb\windows-amd64") -Filter "mariadb-*-winx64.msi" -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending |
    Select-Object -First 1
if (-not $mariadbMsi) {
    throw "Le package MSI MariaDB est introuvable dans le setup."
}

function Get-MariaDbInstallDir {
    $dirs = Get-ChildItem "C:\Program Files" -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "MariaDB *" } |
        Sort-Object Name -Descending
    foreach ($dir in $dirs) {
        $candidate = Join-Path $dir.FullName "bin\mariadbd.exe"
        if (Test-Path $candidate) {
            return $dir.FullName
        }
    }
    return ""
}

$installDir = Get-MariaDbInstallDir
if (-not $installDir) {
    Start-Process msiexec.exe -Wait -NoNewWindow -ArgumentList @(
        "/i",
        "`"$($mariadbMsi.FullName)`"",
        "/qn",
        "/norestart"
    )
    $installDir = Get-MariaDbInstallDir
}
if (-not $installDir) {
    throw "Installation MariaDB impossible (dossier binaire introuvable)."
}

$binDir = Join-Path $installDir "bin"
$mariadbdExe = Join-Path $binDir "mariadbd.exe"
$mariadbInstallDbExe = Join-Path $binDir "mariadb-install-db.exe"
$mariadbCliExe = Join-Path $binDir "mariadb.exe"
if (-not (Test-Path $mariadbdExe)) {
    throw "mariadbd.exe introuvable: $mariadbdExe"
}

$programDataDir = Join-Path $env:ProgramData "NetworkMonitoringProject\mariadb"
$dataDir = Join-Path $programDataDir "data"
$myIni = Join-Path $dataDir "my.ini"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

if (-not (Test-Path (Join-Path $dataDir "mysql"))) {
    & $mariadbInstallDbExe --datadir="$dataDir" --port="$DbPort" --password="$RootPassword"
}

@(
    "[mysqld]"
    "datadir=$($dataDir -replace '\\','/')"
    "port=$DbPort"
    "bind-address=127.0.0.1"
    "character-set-server=utf8mb4"
    "collation-server=utf8mb4_unicode_ci"
    ""
    "[client]"
    "port=$DbPort"
    "plugin-dir=$($installDir -replace '\\','/')/lib/plugin"
) -join [Environment]::NewLine | Set-Content -Path $myIni -Encoding ascii

$serviceExists = $false
try {
    sc.exe query $ServiceName | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $serviceExists = $true
    }
}
catch {
    $serviceExists = $false
}

if (-not $serviceExists) {
    & $mariadbdExe --install $ServiceName --defaults-file="$myIni"
    sc.exe description $ServiceName "MariaDB local pour NetworkMonitoringProject" | Out-Null
}

sc.exe start $ServiceName | Out-Null

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        & $mariadbCliExe -h $DbHost -P $DbPort -u root -p"$RootPassword" -e "SELECT 1;" | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
    }
    catch {
    }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    throw "MariaDB n'est pas pret apres demarrage du service."
}

$sql = @"
CREATE DATABASE IF NOT EXISTS `$DbName` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DbUser'@'127.0.0.1' IDENTIFIED BY '$DbPassword';
CREATE USER IF NOT EXISTS '$DbUser'@'localhost' IDENTIFIED BY '$DbPassword';
GRANT ALL PRIVILEGES ON `$DbName`.* TO '$DbUser'@'127.0.0.1';
GRANT ALL PRIVILEGES ON `$DbName`.* TO '$DbUser'@'localhost';
FLUSH PRIVILEGES;
"@
& $mariadbCliExe -h $DbHost -P $DbPort -u root -p"$RootPassword" -e $sql

[Environment]::SetEnvironmentVariable("NMP_MARIADB_HOST", $DbHost, "Machine")
[Environment]::SetEnvironmentVariable("NMP_MARIADB_PORT", "$DbPort", "Machine")
[Environment]::SetEnvironmentVariable("NMP_MARIADB_USER", $DbUser, "Machine")
[Environment]::SetEnvironmentVariable("NMP_MARIADB_PASSWORD", $DbPassword, "Machine")
[Environment]::SetEnvironmentVariable("NMP_MARIADB_DATABASE", $DbName, "Machine")
[Environment]::SetEnvironmentVariable("NMP_MARIADB_BIN_DIR", $binDir, "Machine")
