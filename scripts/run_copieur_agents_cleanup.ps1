[CmdletBinding()]
param(
    [string]$EnvironmentFile = $env:NMP_INSTALL_ENV_PATH,
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$migrationPath = Join-Path $projectRoot 'deployment\sql\20260930_supprimer_relations_agents_copieurs.sql'

if (-not $EnvironmentFile) {
    $EnvironmentFile = Join-Path $PSScriptRoot 'local_dev_env.ps1'
}
if (-not (Test-Path -LiteralPath $EnvironmentFile -PathType Leaf)) {
    throw "Fichier d'environnement introuvable : $EnvironmentFile"
}
if (-not (Test-Path -LiteralPath $migrationPath -PathType Leaf)) {
    throw "Migration introuvable : $migrationPath"
}

if ([IO.Path]::GetExtension($EnvironmentFile).ToLowerInvariant() -eq '.ps1') {
    . $EnvironmentFile
} else {
    foreach ($line in Get-Content -LiteralPath $EnvironmentFile) {
        if ($line -match '^\s*(?:export\s+)?(NMP_MARIADB_[A-Z_]+)\s*=\s*["'']?(.*?)["'']?\s*$') {
            Set-Item -Path "Env:$($Matches[1])" -Value $Matches[2]
        }
    }
}

$requiredVariables = 'NMP_MARIADB_HOST', 'NMP_MARIADB_PORT', 'NMP_MARIADB_USER', 'NMP_MARIADB_PASSWORD', 'NMP_MARIADB_DATABASE'
$missing = $requiredVariables | Where-Object { -not (Get-Item -Path "Env:$_" -ErrorAction SilentlyContinue).Value }
if ($missing) {
    throw "Variables MariaDB absentes du fichier d'environnement : $($missing -join ', ')"
}

$clientCandidates = @(
    (Join-Path $env:NMP_MARIADB_BIN_DIR 'mariadb.exe'),
    (Join-Path $env:NMP_MARIADB_BIN_DIR 'mysql.exe'),
    'mariadb.exe',
    'mysql.exe'
)
$client = $clientCandidates | Where-Object {
    if ($_ -match '[\\/]') { Test-Path -LiteralPath $_ -PathType Leaf } else { Get-Command $_ -ErrorAction SilentlyContinue }
} | Select-Object -First 1
if (-not $client) {
    throw 'Client MariaDB introuvable. Definissez NMP_MARIADB_BIN_DIR dans le fichier d''environnement.'
}

$clientArgs = @(
    "--host=$env:NMP_MARIADB_HOST",
    "--port=$env:NMP_MARIADB_PORT",
    "--user=$env:NMP_MARIADB_USER",
    "--database=$env:NMP_MARIADB_DATABASE",
    '--default-character-set=utf8mb4',
    '--batch',
    '--raw'
)

# MYSQL_PWD evite de placer le mot de passe dans la ligne de commande ou dans
# l'historique PowerShell. Il est limite au processus enfant lance ci-dessous.
$previousMysqlPassword = $env:MYSQL_PWD
$env:MYSQL_PWD = $env:NMP_MARIADB_PASSWORD
try {
    $preflightSql = @'
SELECT r.id, r.source_service_code, r.target_service_code, r.display_label, r.is_active,
       COUNT(l.id) AS link_count
FROM custom_service_relations r
LEFT JOIN custom_service_relation_links l ON l.relation_id = r.id
WHERE r.target_service_code = 'utilisateurs'
  AND r.source_service_code IN ('copieur', 'code_copieur')
  AND r.display_label = 'Agents'
GROUP BY r.id, r.source_service_code, r.target_service_code, r.display_label, r.is_active
ORDER BY r.id;
'@
    Write-Host "Cible MariaDB : $env:NMP_MARIADB_HOST`:$env:NMP_MARIADB_PORT / $env:NMP_MARIADB_DATABASE"
    Write-Host 'Relations historiques detectees :'
    $preflightSql | & $client @clientArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Precontrole MariaDB echoue (code $LASTEXITCODE)."
    }

    if (-not $Apply) {
        Write-Host ''
        Write-Host 'Aucune modification appliquee. Apres avoir telecharge une sauvegarde complete ITops, relancez avec -Apply.'
        exit 0
    }

    Write-Host 'Execution de la migration...'
    Get-Content -LiteralPath $migrationPath -Raw | & $client @clientArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Migration MariaDB echouee (code $LASTEXITCODE). La transaction a ete annulee."
    }
    Write-Host 'Migration terminee. Les compteurs ci-dessus doivent indiquer zero relation Agents restante.'
} finally {
    $env:MYSQL_PWD = $previousMysqlPassword
}
