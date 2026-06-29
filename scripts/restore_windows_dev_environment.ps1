param(
    [string]$VenvPath = "venv312",
    [string]$PythonExe = "",
    [switch]$InstallDevDependencies,
    [switch]$InstallMariaDb,
    [switch]$CheckOnly,
    [switch]$StartServer,
    [switch]$PersistUserEnvironment = $true,
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 3306,
    [string]$DbName = "network_monitoring",
    [string]$DbUser = "itops",
    [string]$DbPassword = "ChangeMoiFort!",
    [string]$MariaDbRootPassword = "",
    [string]$AppHost = "127.0.0.1",
    [int]$AppPort = 8080
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)
    Write-Host "[info] $Message"
}

function Write-Warn {
    param([string]$Message)
    Write-Warning $Message
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Resolve-ProjectRoot {
    $scriptPath = $PSCommandPath
    if (-not $scriptPath) {
        $scriptPath = $env:RESTORE_NMP_PS1
    }
    if (-not $scriptPath) {
        throw "Impossible de determiner le chemin du script."
    }
    $scriptDir = Split-Path -Parent $scriptPath
    return (Resolve-Path (Join-Path $scriptDir "..")).Path
}

function Resolve-Python312 {
    param([string]$RequestedPythonExe)

    if ($RequestedPythonExe) {
        if (-not (Test-Path $RequestedPythonExe)) {
            throw "Python introuvable: $RequestedPythonExe"
        }
        return (Resolve-Path $RequestedPythonExe).Path
    }

    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        try {
            $resolved = (& py -3.12 -c "import sys; print(sys.executable)").Trim()
            if ($resolved -and (Test-Path $resolved)) {
                return $resolved
            }
        }
        catch {
        }
    }

    foreach ($candidate in @(
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files (x86)\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    )) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $version = (& $pythonCmd.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
        if ($version -eq "3.12") {
            return $pythonCmd.Source
        }
    }

    throw "Python 3.12 est requis. Installe Python 3.12 puis relance ce script."
}

function Assert-PythonVersion {
    param([string]$PythonExe)
    $version = (& $PythonExe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')").Trim()
    if (-not $version.StartsWith("3.12.")) {
        throw "Python 3.12 est requis. Interpreteur detecte: $PythonExe ($version)"
    }
    Write-Info "Python: $PythonExe ($version)"
}

function Find-MariaDbCli {
    $commands = @("mariadb.exe", "mysql.exe")
    foreach ($commandName in $commands) {
        $cmd = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($cmd) {
            return $cmd.Source
        }
    }

    $programFilesCandidates = @()
    foreach ($root in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $root) {
            continue
        }
        $programFilesCandidates += Get-ChildItem $root -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "MariaDB *" -or $_.Name -like "MySQL*" } |
            ForEach-Object {
                @(
                    (Join-Path $_.FullName "bin\mariadb.exe"),
                    (Join-Path $_.FullName "bin\mysql.exe")
                )
            }
    }

    foreach ($candidate in $programFilesCandidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    return ""
}

function Find-MariaDbInstallDb {
    foreach ($root in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $root) {
            continue
        }
        $candidate = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "MariaDB *" } |
            Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName "bin\mariadb-install-db.exe" } |
            Where-Object { Test-Path $_ } |
            Select-Object -First 1
        if ($candidate) {
            return $candidate
        }
    }
    return ""
}

function Find-MariaDbService {
    $names = @("NetworkMonitoringMariaDB", "MariaDB", "MariaDB10", "MariaDB11", "MySQL80", "MySQL")
    foreach ($name in $names) {
        $service = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($service) {
            return $service
        }
    }
    $serviceByDisplayName = Get-Service -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like "*MariaDB*" -or $_.DisplayName -like "*MySQL*" } |
        Select-Object -First 1
    return $serviceByDisplayName
}

function Install-MariaDbFromBundledMsi {
    param(
        [string]$ProjectRoot,
        [string]$RootPassword
    )

    if (-not (Test-IsAdmin)) {
        throw "Installation MariaDB requiert PowerShell en administrateur."
    }
    if (-not $RootPassword) {
        throw "Renseigne -MariaDbRootPassword pour initialiser MariaDB."
    }

    $mariadbMsi = Get-ChildItem (Join-Path $ProjectRoot "build_support\mariadb\windows-amd64") -Filter "mariadb-*-winx64.msi" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        Select-Object -First 1
    if (-not $mariadbMsi) {
        throw "Aucun MSI MariaDB trouve dans build_support\mariadb\windows-amd64."
    }

    Write-Info "Installation silencieuse MariaDB depuis $($mariadbMsi.FullName)"
    if ($CheckOnly) {
        return
    }

    Start-Process msiexec.exe -Wait -NoNewWindow -ArgumentList @(
        "/i",
        "`"$($mariadbMsi.FullName)`"",
        "/qn",
        "/norestart"
    )

    $installDb = Find-MariaDbInstallDb
    if (-not $installDb) {
        Write-Warn "MariaDB installe, mais mariadb-install-db.exe n'a pas ete trouve. La base sera configuree si le service existe deja."
        return
    }

    $installDir = Split-Path -Parent (Split-Path -Parent $installDb)
    $binDir = Join-Path $installDir "bin"
    $mariadbdExe = Join-Path $binDir "mariadbd.exe"
    $programDataDir = Join-Path $env:ProgramData "NetworkMonitoringProject\mariadb"
    $dataDir = Join-Path $programDataDir "data"
    $myIni = Join-Path $dataDir "my.ini"
    New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

    if (-not (Test-Path (Join-Path $dataDir "mysql"))) {
        & $installDb --datadir="$dataDir" --port="$DbPort" --password="$RootPassword"
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

    if (-not (Get-Service -Name "NetworkMonitoringMariaDB" -ErrorAction SilentlyContinue)) {
        & $mariadbdExe --install "NetworkMonitoringMariaDB" --defaults-file="$myIni"
        sc.exe description "NetworkMonitoringMariaDB" "MariaDB local pour NetworkMonitoringProject" | Out-Null
    }
}

function Ensure-MariaDbRunning {
    $service = Find-MariaDbService
    if (-not $service) {
        return
    }
    if ($service.Status -ne "Running") {
        Write-Info "Demarrage du service MariaDB: $($service.Name)"
        if (-not $CheckOnly) {
            Start-Service -Name $service.Name
            $service.WaitForStatus("Running", [TimeSpan]::FromSeconds(30))
        }
    }
    else {
        Write-Info "Service MariaDB actif: $($service.Name)"
    }
}

function Quote-SqlString {
    param([string]$Value)
    return "'" + ($Value -replace "'", "''") + "'"
}

function Quote-SqlIdentifier {
    param([string]$Value)
    return '`' + ($Value -replace '`', '``') + '`'
}

function Invoke-MariaDbSql {
    param(
        [string]$CliPath,
        [string]$Sql,
        [string]$User,
        [string]$Password,
        [string]$Database = ""
    )

    $args = @("-h", $DbHost, "-P", "$DbPort", "-u", $User)
    if ($Password) {
        $args += "-p$Password"
    }
    if ($Database) {
        $args += $Database
    }
    $args += @("-e", $Sql)

    & $CliPath @args
    return $LASTEXITCODE
}

function Test-MariaDbLogin {
    param(
        [string]$CliPath,
        [string]$User,
        [string]$Password,
        [string]$Database = ""
    )
    try {
        Invoke-MariaDbSql -CliPath $CliPath -User $User -Password $Password -Database $Database -Sql "SELECT 1;" | Out-Null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Ensure-Database {
    param([string]$CliPath)

    $dbIdent = Quote-SqlIdentifier $DbName
    $dbUserSql = Quote-SqlString $DbUser
    $dbPasswordSql = Quote-SqlString $DbPassword
    $sql = @"
CREATE DATABASE IF NOT EXISTS $dbIdent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS $dbUserSql@'127.0.0.1' IDENTIFIED BY $dbPasswordSql;
ALTER USER $dbUserSql@'127.0.0.1' IDENTIFIED BY $dbPasswordSql;
CREATE USER IF NOT EXISTS $dbUserSql@'localhost' IDENTIFIED BY $dbPasswordSql;
ALTER USER $dbUserSql@'localhost' IDENTIFIED BY $dbPasswordSql;
GRANT ALL PRIVILEGES ON $dbIdent.* TO $dbUserSql@'127.0.0.1';
GRANT ALL PRIVILEGES ON $dbIdent.* TO $dbUserSql@'localhost';
FLUSH PRIVILEGES;
"@

    if ($CheckOnly) {
        Write-Info "CheckOnly: creation base/utilisateur non executee."
        return
    }

    if (Test-MariaDbLogin -CliPath $CliPath -User "root" -Password $MariaDbRootPassword) {
        Invoke-MariaDbSql -CliPath $CliPath -User "root" -Password $MariaDbRootPassword -Sql $sql | Out-Null
    }
    elseif (Test-MariaDbLogin -CliPath $CliPath -User $DbUser -Password $DbPassword -Database $DbName) {
        Write-Info "Connexion applicative deja valide. Creation SQL root ignoree."
    }
    else {
        throw "Impossible de se connecter a MariaDB. Relance avec -MariaDbRootPassword ou verifie le service MariaDB."
    }

    if (-not (Test-MariaDbLogin -CliPath $CliPath -User $DbUser -Password $DbPassword -Database $DbName)) {
        throw "La connexion applicative MariaDB a echoue apres configuration."
    }
}

function Set-NmpEnvironment {
    param(
        [string]$ProjectRoot,
        [string]$MariaDbCli
    )

    $hebergementPath = Join-Path $ProjectRoot "monitoring\config\hebergement_web.local.json"
    $setupStatePath = Join-Path $ProjectRoot "monitoring\config\setup_installation.local.json"
    $setupTokenPath = Join-Path $ProjectRoot "monitoring\config\setup.local.token"
    $authPath = Join-Path $ProjectRoot ".tmp_localappdata_primo\auth.json"

    $envMap = [ordered]@{
        NMP_MARIADB_HOST = $DbHost
        NMP_MARIADB_PORT = "$DbPort"
        NMP_MARIADB_USER = $DbUser
        NMP_MARIADB_PASSWORD = $DbPassword
        NMP_MARIADB_DATABASE = $DbName
        NMP_HEBERGEMENT_CONFIG = $hebergementPath
        NMP_SETUP_CONFIG = $setupStatePath
        NMP_SETUP_TOKEN_FILE = $setupTokenPath
        NMP_AUTH_STORE_PATH = $authPath
        NMP_DEV_SKIP_SETUP_WIZARD = "1"
        NMP_SETUP_SKIP_MARIADB_PROVISION = "1"
        NMP_SETUP_SKIP_REVERSE_PROXY_SETUP = "1"
    }

    if ($MariaDbCli) {
        $envMap["NMP_MARIADB_BIN_DIR"] = Split-Path -Parent $MariaDbCli
    }

    foreach ($key in $envMap.Keys) {
        Set-Item -Path "Env:$key" -Value $envMap[$key]
        if ($PersistUserEnvironment -and -not $CheckOnly) {
            [Environment]::SetEnvironmentVariable($key, $envMap[$key], "User")
        }
    }

    $localEnvPath = Join-Path $ProjectRoot "scripts\local_dev_env.ps1"
    $localEnvCmdPath = Join-Path $ProjectRoot "scripts\local_dev_env.cmd"
    $localEnvLines = @(
        "# Generated by scripts/restore_windows_dev_environment.ps1",
        "# Dot-source this file to load the project runtime variables in the current shell."
    )
    $localEnvCmdLines = @(
        "@echo off",
        "rem Generated by scripts/restore_windows_dev_environment.ps1"
    )
    foreach ($key in $envMap.Keys) {
        $escaped = $envMap[$key] -replace "'", "''"
        $localEnvLines += "`$env:$key = '$escaped'"
        $cmdEscaped = $envMap[$key] -replace "\^", "^^" -replace "&", "^&" -replace "\|", "^|" -replace "<", "^<" -replace ">", "^>"
        $localEnvCmdLines += "set `"$key=$cmdEscaped`""
    }

    if (-not $CheckOnly) {
        $localEnvLines -join [Environment]::NewLine | Set-Content -Path $localEnvPath -Encoding ascii
        $localEnvCmdLines -join [Environment]::NewLine | Set-Content -Path $localEnvCmdPath -Encoding ascii

        $hebergementPayload = [ordered]@{
            hote_ecoute = $AppHost
            port_ecoute = $AppPort
            demarrage_auto_service = $false
            utiliser_url_publique_reverse_proxy = $false
            url_publique = "http://${AppHost}:$AppPort"
            reverse_proxy_actif = $false
            reverse_proxy_type = "aucun"
        }
        $hebergementPayload | ConvertTo-Json -Depth 4 | Set-Content -Path $hebergementPath -Encoding utf8

        $setupPayload = [ordered]@{
            completed = $false
            completed_at = ""
            completed_by = ""
            reverse_proxy_type = ""
            public_url = ""
        }
        $setupPayload | ConvertTo-Json -Depth 4 | Set-Content -Path $setupStatePath -Encoding utf8
    }

    Write-Info "Variables NMP chargees pour ce shell."
    if ($PersistUserEnvironment) {
        Write-Info "Variables NMP persistees pour l'utilisateur Windows. Redemarre l'IDE pour qu'il les voie."
    }
    Write-Info "Fichier shell local: $localEnvPath"
    Write-Info "Fichier cmd local: $localEnvCmdPath"
}

function Ensure-Venv {
    param(
        [string]$ProjectRoot,
        [string]$BasePython,
        [string]$RelativeVenvPath
    )

    $venvFullPath = Join-Path $ProjectRoot $RelativeVenvPath
    $venvPython = Join-Path $venvFullPath "Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Info "Creation du venv: $venvFullPath"
        if (-not $CheckOnly) {
            & $BasePython -m venv $venvFullPath
        }
    }
    else {
        Write-Info "Venv deja present: $venvFullPath"
    }

    if ($CheckOnly) {
        return $venvPython
    }

    & $venvPython -m pip install --upgrade pip 2>&1 | ForEach-Object { Write-Host $_ }
    & $venvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt") 2>&1 | ForEach-Object { Write-Host $_ }
    if ($InstallDevDependencies) {
        & $venvPython -m pip install -r (Join-Path $ProjectRoot "requirements-dev.txt") 2>&1 | ForEach-Object { Write-Host $_ }
    }
    return $venvPython
}

$projectRoot = Resolve-ProjectRoot
Set-Location $projectRoot

Write-Step "Audit environnement projet"
Write-Info "Projet: $projectRoot"
if ($CheckOnly) {
    Write-Info "Mode CheckOnly actif: aucun changement volontaire ne sera applique."
}

Write-Step "Python et dependances"
$basePython = Resolve-Python312 -RequestedPythonExe $PythonExe
Assert-PythonVersion -PythonExe $basePython
$venvPython = Ensure-Venv -ProjectRoot $projectRoot -BasePython $basePython -RelativeVenvPath $VenvPath
Write-Info "Interpreteur PyCharm conseille: $venvPython"

Write-Step "MariaDB"
$mariaDbCli = Find-MariaDbCli
if (-not $mariaDbCli -and $InstallMariaDb) {
    Install-MariaDbFromBundledMsi -ProjectRoot $projectRoot -RootPassword $MariaDbRootPassword
    $mariaDbCli = Find-MariaDbCli
}
if (-not $mariaDbCli) {
    throw "Client MariaDB introuvable. Installe MariaDB, ou relance en PowerShell administrateur avec -InstallMariaDb -MariaDbRootPassword '<mot_de_passe_root>'."
}
Write-Info "Client MariaDB: $mariaDbCli"
Ensure-MariaDbRunning
Ensure-Database -CliPath $mariaDbCli

Write-Step "Configuration runtime locale"
Set-NmpEnvironment -ProjectRoot $projectRoot -MariaDbCli $mariaDbCli

Write-Step "Verification import applicatif"
if (-not $CheckOnly) {
    & $venvPython -c "from monitoring.backend import build_application_backend; build_application_backend(); print('backend ok')"
}
else {
    Write-Info "CheckOnly: verification Python applicative non executee."
}

Write-Step "Termine"
Write-Host "Commande de lancement:" -ForegroundColor Green
Write-Host "  scripts\local_dev_env.cmd"
Write-Host "  .\$VenvPath\Scripts\python.exe main.py --mode server --host $AppHost --port $AppPort --reload"
Write-Host "URL locale: http://${AppHost}:$AppPort/"

if ($StartServer -and -not $CheckOnly) {
    Write-Step "Demarrage serveur"
    & $venvPython "main.py" "--mode" "server" "--host" $AppHost "--port" "$AppPort" "--reload"
}
