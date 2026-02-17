param(
    [string]$PythonExe = "python",
    [string]$AppVersion = "",
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $projectRoot
try {
    if (-not $AppVersion) {
        $rootInit = Join-Path $projectRoot "__init__.py"
        if (-not (Test-Path $rootInit)) {
            throw "Impossible de trouver __init__.py pour lire la version."
        }
        $content = Get-Content $rootInit -Raw
        $match = [regex]::Match($content, '__version__\s*=\s*"([^"]+)"')
        if (-not $match.Success) {
            throw "Impossible de lire __version__ depuis __init__.py."
        }
        $AppVersion = $match.Groups[1].Value
    }

    if ($Clean) {
        Write-Host "Nettoyage des dossiers build/dist/output..."
        Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force "installer\output" -ErrorAction SilentlyContinue
    }

    Write-Host "Installation de PyInstaller..."
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install pyinstaller

    Write-Host "Build de l'application (PyInstaller)..."
    $pyiArgs = @(
        "--noconfirm"
        "--windowed"
        "--onedir"
        "--name", "NetworkMonitoringProject"
        "--add-data", "monitoring/ui/assets;monitoring/ui/assets"
        "main.py"
    )
    if ($Clean) {
        $pyiArgs = @("--clean") + $pyiArgs
    }
    & $PythonExe -m PyInstaller @pyiArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Echec du build PyInstaller."
    }

    $distPath = Join-Path $projectRoot "dist\NetworkMonitoringProject"
    if (-not (Test-Path $distPath)) {
        throw "Le dossier de build '$distPath' est introuvable."
    }

    Write-Host "Recherche de Inno Setup (ISCC.exe)..."
    $isccCandidates = @()
    if ($env:ISCC_EXE) {
        $isccCandidates += $env:ISCC_EXE
    }
    $isccCandidates += @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    $iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $iscc) {
        Write-Warning "Inno Setup non trouve. Le build applicatif est pret dans: $distPath"
        Write-Warning "Installe Inno Setup 6 puis relance ce script pour generer le Setup.exe."
        return
    }

    Write-Host "Generation du Setup Windows (Inno Setup)..."
    & $iscc "/DMyAppVersion=$AppVersion" "installer\NetworkMonitoringProject.iss"
    if ($LASTEXITCODE -ne 0) {
        throw "Echec de generation du Setup Inno."
    }

    Write-Host "Succes."
    Write-Host "Application: $distPath"
    Write-Host "Installateur: $projectRoot\installer\output"
}
finally {
    Pop-Location
}
