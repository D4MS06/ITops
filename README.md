# NetworkMonitoringProject v1.0.0

Application desktop (Tkinter) de supervision reseau pour switches et serveurs.

## Capacites principales

- Dashboard central avec tuiles de synthese (totaux, en ligne, hors ligne, etat monitoring).
- Vues dediees `Switch`, `Serveur` et `Globale`.
- Monitoring en continu par ping asynchrone.
- Delai de declaration `hors ligne` configurable (par defaut 5 secondes).
- Notifications sur changement de statut:
  - email (SMTP/TLS),
  - popup locale activable/desactivable.
- Notification activable par equipement (menu contextuel).
- Recherche temps reel dans chaque Treeview (nom, IP, description, statut, type, id).
- Filtrage visuel des statuts depuis les tuiles du dashboard.
- Outils reseau dans le menu contextuel (place en premier):
  - Ping continu,
  - Port check,
  - Traceroute,
  - DNS lookup,
  - HTTP(S) check,
  - SNMP check.
- Actions rapides par double-clic et menu contextuel (RDP, SSH, Web, TeamViewer selon type serveur).

## Prerequis

- Python 3.12 recommande
- Windows (fonctions RDP/PowerShell/`mstsc`/`wt` optimisees pour Windows)

## Installation

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## Lancement

```bash
python main.py
```

## Setup Windows (.exe)

### Prerequis

- Windows 10/11
- Python 3.12+
- Inno Setup 6 (pour generer l'installateur final)

### Build de l'application + setup

Depuis PowerShell, a la racine du projet:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Clean
```

Le script:
- compile l'application avec PyInstaller (mode `onedir`),
- inclut les assets UI (`monitoring/ui/assets`),
- puis genere l'installateur via Inno Setup si `ISCC.exe` est detecte.

Sorties:
- application portable: `dist\NetworkMonitoringProject\`
- installateur: `installer\output\NetworkMonitoringProject-Setup-<version>.exe`

## Configuration

- Fichier de configuration utilisateur:
  - `~/.network_monitor_settings.json`
- Mot de passe SMTP stocke via `keyring`.
- Inventaire des devices:
  - `monitoring/storage/devices.json`

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Structure du projet

- `main.py` : point d'entree.
- `monitoring/controllers/` : logique monitoring, orchestration UI.
- `monitoring/models/` : modeles de donnees devices.
- `monitoring/ui/` : dashboard, vues, dialogs.
- `monitoring/storage/` : persistance JSON.
- `monitoring/utils/` : logging, notifications, utilitaires reseau.

## Version

Version stable actuelle: **1.0.0**

## Licence

Projet prive/interne (adapter la licence selon votre besoin).
