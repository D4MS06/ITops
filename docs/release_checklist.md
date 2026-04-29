# Check-list release

## Objectif release 1.0.9 (full-web, primo-install)

- supprimer le mode desktop du scope produit (mode web/API uniquement)
- abandonner la migration SQLite -> MariaDB pour cette release
- garantir la reprise de donnees via imports fichiers (sans ressaisie manuelle)
- n'accepter que:
  - bug bloquant auth/web/import/supervision
  - regression testable
  - fix packaging/release

## Scope freeze 1.0.9

- mode supporte: `python main.py --mode server`
- mode desktop retire du scope de validation release
- backend runtime: MariaDB uniquement
- la reprise de donnees se fait par imports admin/web:
  - devices (preview/apply/export)
  - services no-code (import fields/export)
  - shared lists (import/export)
  - records services no-code (preview/apply/export)

## Avant build

- verifier que la branche de release est figee
- verifier `git status` propre (hors fichiers explicitement attendus)
- aligner version (`CHANGELOG.md`, metadata applicative, setup)
- verifier dependances:
  - `pip install -r requirements.txt`
  - `pip install -r requirements-dev.txt`

## Validation locale (gates obligatoires)

### 1) Smoke de base

- login web valide sur `http://127.0.0.1:8000/`
- endpoints `GET /health` et `GET /auth/status` OK
- monitoring snapshot lisible (`GET /monitoring/snapshot` avec token)

### 2) Tests unitaires/cibles obligatoires

- `pytest -q monitoring/tests/test_main_entrypoint.py`
- `pytest -q monitoring/tests/test_db_backend.py monitoring/tests/test_auth_service.py`

### 3) Tests API imports obligatoires (no ressaisie)

- `pytest -q monitoring/tests/test_api.py -k "devices_import_preview_apply_and_export"`
- `pytest -q monitoring/tests/test_api.py -k "custom_service_field_import_infers_column_types"`
- `pytest -q monitoring/tests/test_api.py -k "shared_list_items_import_infers_codes_and_labels"`
- `pytest -q monitoring/tests/test_api.py -k "custom_service_records_import_preview_apply_and_export"`
- `pytest -q monitoring/tests/test_api.py -k "admin_shared_list_and_service_fields_export"`

### 4) Tests API auth/roles obligatoires

- `pytest -q monitoring/tests/test_api.py -k "auth_bootstrap_login_and_protected_endpoints or first_login_sa_requires_password_change or settings_require_admin_module"`

### 5) Test E2E manuel primo-install (base vide)

- demarrer sur base MariaDB vide
- bootstrap admin
- importer dans cet ordre:
  - shared lists
  - custom service fields
  - devices
  - custom service records
- verifier:
  - compteurs inventaire cohérents
  - details equipements visibles
  - absence de doublons inattendus apres re-import
  - export CSV re-telechargeable pour chaque bloc

## Build Windows

- executer `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Clean`
- verifier la presence de `dist\NetworkMonitoringProject\_internal\monitoring\web\index.html`
- verifier la presence de `dist\NetworkMonitoringProject\NetworkMonitoringProject.exe`
- verifier la presence de `installer\output\NetworkMonitoringProject-Setup-<version>.exe`

## Validation post-build (poste vierge)

- installer le setup
- demarrer le serveur web
- verifier login + dashboard
- executer le scenario primo-install par imports (ordre ci-dessus)
- verifier supervision type par type (start/stop + status)
- verifier desinstallation puis reinstallation

## Go / No-Go 1.0.9

- Go si:
  - tous les tests obligatoires ci-dessus sont verts
  - primo-install complet reussi sans ressaisie manuelle
  - aucun bug bloquant web/auth/import/monitoring
- No-Go si:
  - un import critique echoue (preview ou apply)
  - perte de donnees ou duplication non maitrisee
  - regression d'authentification/permissions

## Publication GitHub

- pousser la branche cible
- aligner le tag de release sur le commit valide
- remplacer l'asset `.exe` de la release GitHub
- verifier l'URL de release et la taille de l'asset
- tester le setup telecharge depuis GitHub
