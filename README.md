# NetworkMonitoringProject v1.0.3

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
- Inventaire des devices (runtime):
  - `%LOCALAPPDATA%\\NetworkMonitoringProject\\data\\devices.db` (SQLite)
  - migration automatique depuis `devices.json` au premier lancement

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

## Nouveautes 1.0.3

- Theming global `Light` / `Dark` avec harmonisation des composants UI.
- Menu `Personnalisation` enrichi:
  - image de fond (watermark) importable,
  - apercu + reglage d'opacite,
  - reset.
- Indicateurs de statut configurables (independants du theme):
  - `Badge coche / croix`,
  - `Pastille moderne`.
- Application des indicateurs aux vues `Switch`, `Serveur` et `Globale`.
- Distinction visuelle explicite de l'etat `Idle` (icone + libelle).
- Clic sur les tuiles `Total Switchs`, `Total Serveurs` et `Equipements`:
  - affiche l'inventaire meme monitoring arrete.
- Fenetre `Journaux` themable (light/dark) avec style homogene.
- Logique notification/log status renforcee:
  - notifications et logs `status_change` uniquement sur `online <-> offline`,
  - aucune notif/log sur transitions impliquant `idle`.
- Correctifs de robustesse et optimisations de base pour evolutions futures
  (types de devices plus dynamiques, exposition web distante).

## Vision modulaire (UX-first)

Objectif: rendre l'ajout de types de devices tres simple, sans exposer
des parametres techniques complexes a tous les utilisateurs.

### Principes

- Interface orientee "blocs preconfigures" plutot que configuration brute.
- Toolbox visuelle avec icones metier (SSH, TeamViewer, RDP, Web, Terminal...).
- Ajout par glisser-deposer des blocs dans le formulaire d'un type de device.
- Les champs necessaires sont ajoutes automatiquement par le bloc
  (ex: `ID TeamViewer`, `login SSH`).
- Personnalisation legere seulement:
  - libelle,
  - ordre,
  - obligatoire / optionnel.
- Mode avance optionnel (masque par defaut), reserve aux profils admin.

### Cible ergonomique

- En 1 coup d'oeil, l'utilisateur comprend:
  - quels champs sont indispensables,
  - quels blocs fonctionnels sont actifs,
  - quelles actions de prise en main a distance sont disponibles.
- L'utilisateur standard construit un type en quelques clics,
  sans ecrire de commande.

### Strategy technique retenue

- Priorite a un catalogue de blocs preconfigures (packages internes).
- Import/export de presets de type (JSON) pour partage rapide.
- Eviter les plugins "code" dans un premier temps:
  - plus simple a maintenir,
  - plus sur,
  - meilleur compromis modularite/UX.

## Version

Version stable actuelle: **1.0.3**

## Licence

Projet prive/interne (adapter la licence selon votre besoin).


