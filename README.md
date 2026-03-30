# NetworkMonitoringProject v1.0.7-pre-release

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

Mode serveur API seule:

```bash
python main.py --mode server --host 127.0.0.1 --port 8000
```

Interface web incluse:

- ouvrir `http://127.0.0.1:8000/` (portail modules)
- module monitoring web: `http://127.0.0.1:8000/monitoring`
- login admin obligatoire avant acces au portail et aux modules
- dashboard live alimente par `GET /monitoring/snapshot` et `WS /monitoring/ws`
- commandes monitoring disponibles depuis l'UI web (global + par type)
- si le runtime Python n'a pas de backend WebSocket disponible, l'UI bascule automatiquement en polling HTTP

Depuis l'application desktop Tkinter:

- menu `Supervision > Serveur web`
- parametrage `host/port`
- parametrage optionnel d'une URL publique stable (`https://monitoring.mvl`)
- demarrage / arret / redemarrage
- ouverture directe de l'interface web dans le navigateur
- le serveur web demarre dans le meme process que le desktop et partage le meme backend/runtime monitoring
- un reverse proxy (Caddy recommande) peut publier l'application sans exposer le port backend

## API HTTP

Squelette FastAPI disponible pour la preparation web 1.0.7:

```bash
uvicorn monitoring.api.main:app --reload
```

Ou via le point d'entree principal:

```bash
python main.py --mode server --reload
```

Endpoints de base:
- `GET /health`
- `GET /auth/status`
- `POST /auth/bootstrap`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `GET/POST/PUT/DELETE /devices`
- `GET /device-types`
- `GET /device-types/{type_code}/schema`
- `GET /logs`
- `GET /monitoring/summary`
- `GET /monitoring/snapshot`
- `POST /monitoring/start/{type_code}`
- `POST /monitoring/stop/{type_code}`
- `POST /monitoring/start-all`
- `POST /monitoring/stop-all`
- `WS /monitoring/ws?token=...`
- `GET /config-files`
- `GET/PUT /settings`

Les endpoints hors `health` et `auth/status/bootstrap/login` sont proteges par un bearer token.
Le WebSocket monitoring est protege par le token passe en query string et diffuse un snapshot initial puis les changements d'etat.

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
- installe les dependances de build figees via `requirements-build.txt`,
- puis genere l'installateur via Inno Setup si `ISCC.exe` est detecte.

Sorties:
- application portable: `dist\NetworkMonitoringProject\`
- installateur: `installer\output\NetworkMonitoringProject-Setup-<version>.exe`

## Configuration

- Fichier de configuration utilisateur:
  - `%LOCALAPPDATA%\\NetworkMonitoringProject\\config\\settings.json`
- Mot de passe SMTP stocke via `keyring`.
- Inventaire des devices (runtime):
  - `%LOCALAPPDATA%\\NetworkMonitoringProject\\data\\devices.db` (SQLite par defaut)
  - migration automatique depuis `devices.json` au premier lancement
- Backend base de donnees selectable:
  - `NMP_DB_BACKEND=sqlite` (par defaut)
  - `NMP_DB_BACKEND=mariadb`
- Variables MariaDB (si `NMP_DB_BACKEND=mariadb`):
  - `NMP_MARIADB_HOST` (defaut `127.0.0.1`)
  - `NMP_MARIADB_PORT` (defaut `3306`)
  - `NMP_MARIADB_USER` (defaut `root`)
  - `NMP_MARIADB_PASSWORD`
  - `NMP_MARIADB_DATABASE` (defaut `network_monitoring`)

Migration des donnees SQLite vers MariaDB:

```bash
python scripts/migrate_sqlite_to_mariadb.py --sqlite-path "%LOCALAPPDATA%\\NetworkMonitoringProject\\data\\devices.db"
```

En mode `NMP_DB_BACKEND=mariadb`, une migration automatique depuis SQLite est aussi tentee au premier demarrage si la base MariaDB est vide.

## Reverse proxy portable

- URL publique stable recommandee : `https://monitoring.mvl`
- backend applicatif recommande : `127.0.0.1:<port configurable>`
- reverse proxy portable recommande : `Caddy`
- le setup Windows installe et initialise automatiquement le service Caddy local
- si le port backend change dans l'application, la configuration Caddy est reecrite puis rechargee automatiquement
- l'application peut exporter le certificat racine HTTPS a importer sur les postes clients autorises

Documentation :

- `docs/caddy_reverse_proxy.md`
- le setup Windows embarque `Caddy` et initialise automatiquement son service local

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests de validation release apres build:

```bash
pytest monitoring/tests/test_packaged_dist.py -q
```

## Check-list release

La check-list de release est disponible dans `docs/release_checklist.md`.

## Structure du projet

- `main.py` : point d'entree.
- `monitoring/controllers/` : logique monitoring, orchestration UI.
- `monitoring/models/` : modeles de donnees devices.
- `monitoring/ui/` : dashboard, vues, dialogs.
- `monitoring/storage/` : persistance SQLite/MariaDB (migration auto depuis JSON legacy).
- `monitoring/utils/` : logging, notifications, utilitaires reseau.

## Nouveautes 1.0.7 pre-release

- backend partage stable entre desktop Tkinter, API HTTP et serveur web embarque
- premiere interface web exploitable avec authentification admin, dashboard live et commandes monitoring
- serveur web embarque pilotable depuis le desktop (demarrage, arret, redemarrage, port, autostart)
- mode remote cohérent: desktop et web pilotent le meme runtime de monitoring
- watermark et theming partages entre desktop et web
- sessions admin persistees en SQLite pour conserver les connexions web a travers les redemarrages serveur
- verrouillage thread-safe du modele et optimisation du flux WebSocket

## Nouveautes 1.0.6 pre-release

- extraction de la logique device dans `DeviceService`
- extraction du moteur de supervision dans `MonitoringService`
- ajout de `AuthService` pour preparer la protection navigateur
- ajout d'un backend applicatif partage entre desktop Tkinter et API locale
- ajout d'un squelette FastAPI avec routes securisees de base
- correction du calcul des tuiles dashboard et des refresh sur transitions `idle`
- correction de la parallelisation du fallback `ping.exe`
- correction de l'injection de l'icone Windows dans le build/setup

## Nouveautes 1.0.5 pre-release

- Refactor structurel important du dashboard en mixins specialises:
  - `dashboard_cards_mixin.py`
  - `dashboard_detail_mixin.py`
  - `dashboard_theme_mixin.py`
- Reduction forte de la taille de `dashboard.py` pour faciliter la maintenance.
- Rationalisation MVC:
  - ajout d'une API publique `refresh_views()` dans le controller,
  - suppression des appels UI vers la methode privee `_refresh_all_views()`.
- Optimisation persistance SQLite:
  - upsert/delete incremental par equipement,
  - suppression de la reecriture complete de la table `devices` a chaque edition.
- Reorganisation ergonomique des menus principaux:
  - `Supervision`, `Inventaire`, `Affichage`, `Aide`.
- Clarification des actions contextuelles:
  - actions rapides en tete,
  - telechargement de configuration par device,
  - outils reseau avant les actions de gestion.
- Mise a jour documentation/dependances:
  - clarification persistance SQLite,
  - retrait de `pytest` des dependances runtime.

## Nouveautes 1.0.4 pre-release

- Types de devices dynamiques (plus de types figes en dur).
- Editeur de formulaire de type modulaire (champs obligatoires + champs personnalisables).
- Catalogue plugins avec drag-and-drop pour menu contextuel.
- Assignation des plugins par OS via configuration UI.
- Formulaire device dynamique alimente par la definition du type.
- Dashboard dynamique (tuiles, navigation et boutons monitoring par type).
- Edition du dashboard (reordre, masquer/ajouter des tuiles, persistance).
- Tuiles d'etat simplifiees avec clic direct sur les compteurs pour filtrer les devices.
- Correctifs de stabilite graphique des tuiles dashboard.
- Harmonisation theme Dark sur les dialogs (listes, combobox, boutons, treeview).
- Flux de mise a jour ameliore:
  - verification immediate apres validation des parametres MAJ,
  - fenetre de progression pendant le telechargement,
  - lancement installeur apres fermeture du process applicatif.

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

Version actuelle: **1.0.7-pre-release**

## Licence

Projet prive/interne (adapter la licence selon votre besoin).


