ANALYSE COMPLÈTE ITops v1.0 - Chef de Projet Senior
📊 SOMMAIRE EXÉCUTIF
ITops est une plateforme de supervision réseau professionnelle avec moteur no-code intégré, architecturée pour le déploiement en production. Ce document fourni une analyse technique exhaustive pour prendre la suite du projet en tant que Chef de Projet Senior.
🏗️ ARCHITECTURE GLOBALE
Stack Technique
Couche
Technologie
Rôle
Frontend
HTML5/CSS3/JS (Vanilla)
Interface web réactive
Backend API
FastAPI + Uvicorn
API REST + WebSockets
Backend Métier
Python 3.12 (Services)
Logique applicative
Persistance
MariaDB 10.6+
Stockage relationnel
Reverse Proxy
Caddy/Nginx
TLS Termination
Build
PyInstaller/InnoSetup
Package Windows
Déploiement Linux
systemd
Service natif
Authentification
PBKDF2-SHA256 + Sessions
Sécurité
Diagramme d'Architecture
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NAVIGATEUR WEB                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │ portal.html │  │ index.html  │  │ setup.html   │  │ shared_*.js     │    │
│  │ + portal.js │  │ + app.js     │  │ + setup.js   │  │ (Code partagé)  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼ (HTTPS/TLS)
┌─────────────────────────────────────────────────────────────────────────────┐
│                            REVERSE PROXY (Caddy/Nginx)                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼ (HTTP 8080)
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI APPLICATION                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  monitoring/api/app.py                                               │   │
│  │  - Routes REST/GraphQL                                              │   │
│  │  - WebSocket (/monitoring/ws)                                        │   │
│  │  - Middleware Auth (Bearer Token)                                    │   │
│  │  - Validation Pydantic                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION BACKEND                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  monitoring/backend/app_backend.py: ApplicationBackend                 │   │
│  │  - Injecte tous les services                                         │   │
│  │  - Gère le lifecycle                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ DeviceService │  │MonitoringSvc │  │ AuthService   │  │CustomSvcSvc  │    │
│  │ (CRUD)        │  │(Ping/Async)  │  │(Sessions)     │  │(No-Code)     │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        ▼                               ▼                               ▼
┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐
│    MODELS         │       │   REPOSITORIES     │       │    STORAGE        │
│  DevicesModel     │       │  DeviceRepository  │       │  MariaDBFile      │
│  (Thread-Safe)    │       │  DeviceTypeRepo    │       │  Manager          │
│  DeviceInventory  │       │  CustomSvcRepo     │       │  + Bootstrap      │
│  State            │       └───────────────────┘       └───────────────────┘
└───────────────────┘                       │                       │
                                        ▼                       ▼
                                ┌───────────────────────┐   ┌───────────────┐
                                │     MARIADB            │   │  Filesystem   │
                                │  - devices             │   │  - linked_files│
                                │  - device_types        │   │  - configs    │
                                │  - custom_services     │   └───────────────┘
                                │  - auth_*              │
                                │  - sync_*              │
                                └───────────────────────┘
📚 COMPOSANTS CLÉS & RESPONSABILITÉS
🔧 1. CORE MONITORING
Composant
Fichier
Responsabilité
Technologies
MonitoringService
monitoring/services/monitoring_service.py
Moteur de ping, gestion des statuts (online/offline/idle), notifications
aioping, asyncio, ThreadPool
MonitoringRuntimeService
monitoring/services/monitoring_runtime_service.py
Orchestration des threads, start/stop par type, état global
threading, MonitoringRuntimeThreads
MonitoringCycleState
monitoring/services/monitoring_cycle_state.py
État d'un cycle de monitoring
Dataclass
DevicesModel
monitoring/models/devices_model.py
Modèle central thread-safe, observateurs, inventaire
threading.RLock, Observer Pattern
DeviceService
monitoring/services/device_service.py
Logique métier CRUD, validation, sérialisation
Validation, MariaDBFileManager
Fonctionnalités: ✅ Ping asynchrone (aioping sur Linux, subprocess sur Windows) ✅ Délais de détection configurables (offline_delay, online_recovery_delay) ✅ Notifications email (SMTP/TLS) et popups ✅ Gestion des échecs (failures_for_offline: 5, successes_for_online: 3) ✅ Thread-safe avec verrous ✅ WebSockets pour real-time
🎨 2. NO-CODE DYNAMIC SERVICES (✨ INNOVATION MAJEURE)
C'est le cœur différenciant du projet - Permet de créer des services métiers sans écrire de code.
Tables MariaDB:
-- Définition des services
custom_services (code, label, is_active, credentials_enabled, child_enabled, sort_order)

-- Champs personnalisés
custom_service_fields (service_code, field_key, label, field_kind, required, options, sort_order)

-- Données (stockage JSON)
custom_service_records (id, service_code, payload_json, created_at, updated_at)

-- Hiérarchie
custom_service_children (record_id, child_name, child_code, sort_order)

-- Relations entre services
custom_service_relations (id, source_service_code, target_service_code, verb, cardinality, ...)

-- Catégories de documents
custom_service_document_categories (service_code, category_key, label, allowed_extensions, ...)

-- Liaison fiche/fichier
custom_service_record_attachments (service_code, record_id, category_key, storage_file_id, ...)
Fonctionnalités:
Feature
Implémentation
Status
Création de services
custom_service_schema.py
✅
Champs dynamiques
text, ip, url, date, list
✅
Lists partagées
shared_lists, shared_list_items
✅
Import/Export
CSV, TSV, XLSX
✅
Recherche avancée
custom_service_index.py
✅
Indexation
custom_service_records_tabular.py
✅
Éditeur de relations
Canvas drag-and-drop
🟡 (En cours)
Pièces jointes
Intégration storage
🟡 (Spécifié)
Audit
custom_service_history.py
✅
Workflow Utilisateur:
1.
Créer un service (ex: "Copieurs")
2.
Définir les champs (ex: "Modèle", "IP", "N° Série")
3.
Configurer les actions (ex: "Ouvrir Web UI", "SSH")
4.
Importer des données (CSV/XLSX)
5.
Créer des relations avec d'autres services (ex: "Copieur → Site")
6.
Attacher des documents à chaque fiche
7.
Visualiser dans le portail
Exemple de Service:
{
  "code": "copieurs",
  "label": "Parc Copieurs",
  "is_active": true,
  "fields": [
    {"field_key": "modele", "label": "Modèle", "field_kind": "text", "required": true},
    {"field_key": "ip", "label": "Adresse IP", "field_kind": "ip", "required": true},
    {"field_key": "numero_serie", "label": "N° Série", "field_kind": "text"},
    {"field_key": "site", "label": "Site", "field_kind": "list", "options": "Paris,Lyon,Marseille"}
  ],
  "records": [
    {
      "id": "cop-001",
      "values": {"modele": "Xerox WorkCentre", "ip": "192.168.1.100", "numero_serie": "XRX12345"},
      "children": []
    }
  ]
}
🔐 3. AUTHENTIFICATION & SÉCURITÉ
Composant
Fichier
Responsabilité
AuthService
monitoring/services/auth_service.py
Gestion des sessions, hash PBKDF2, vérification
AuthSession
Dataclass
Token, subject, created_at, expires_at
PasswordStore
keyring + fichier
Stockage sécurisé des mots de passe
Middleware API
monitoring/api/app.py
Validation Bearer Token, RBAC
Caractéristiques:
•
Hash: PBKDF2-SHA256 (600,000 itérations)
•
Sessions: Tokens opaques, TTL configurable (default: 3600s)
•
Stockage: keyring (si disponible) ou fichier JSON chiffré
•
RBAC: Rôles (admin, user), permissions par module
•
Révocation: revoke_all_sessions() au démarrage (configurable)
Tables MariaDB:
auth_users (subject, label, is_active, password_hash, must_change_password)
auth_roles (code, label, is_system, sort_order)
auth_modules (code, label, route_path, is_active, sort_order)
auth_user_roles (subject, role_code)
auth_role_modules (role_code, module_code)
auth_sessions (token, subject, created_at, expires_at)
💾 4. STORAGE & PERSISTANCE
Composant
Fichier
Responsabilité
MariaDBFileManager
monitoring/storage/mariadb_manager.py
Point central d'accès à MariaDB, bootstrap, helpers
MariaDBBootstrapper
monitoring/storage/mariadb_bootstrap.py
Création idempotente des tables
Repositories
monitoring/repositories/
Accès données par domaine
StorageTargetService
monitoring/services/storage_target_service.py
Gestion des cibles de stockage (SMB3)
LinkedFileService
monitoring/services/linked_file_service.py
Upload, download, métadonnées
Cibles de Stockage:
•
Local: /var/lib/itops/linked_files
•
SMB3: Montage automatique via itops_storage_helper.py
•
Configurable: Par service custom
Tables MariaDB:
linked_files (id, owner_kind, owner_id, module_code, category, filename, stored_path, mime_type, size_bytes, sha256, ...)
storage_targets (id, label, service_code, kind, remote_path, username, secret_ref, ...)
🌐 5. FRONTEND WEB
Structure:
monitoring/web/
├── app.css          # Design System Global (147KB)
├── app.js           # Logique Monitoring (514KB)
├── portal.html      # Portail principal
├── portal.js        # Logique Portail + No-Code (862KB)
├── setup.html       # Wizard installation
├── setup.js         # Logique Setup
├── shared_*.js      # Code partagé (API, UI, Auth, Menu, etc.)
└── assets/          # Images, icônes, etc.
Design System:
•
Thèmes: Light/Dark (theme_manager.py)
•
Tokens de couleurs: 38 tokens éditables (app_bg, surface_bg, accent_primary, etc.)
•
Composants: TreeView, menus contextuels, formulaires dynamiques
•
Responsive: Adapté desktop
Fonctionnalités Frontend:
Feature
Implémentation
Status
Dashboard
Tuiles dynamiques, filtres
✅
TreeView
Recherche temps réel, tri
✅
Formulaires
Génération dynamique
✅
Menu contextuel
Actions par type
✅
Outils réseau
Ping, Port Check, Traceroute, DNS, HTTP, SNMP
✅
Drag-and-Drop
Relations, réordonnancement
✅
WebSockets
Real-time monitoring
✅
Polling Fallback
Si WebSockets indisponible
✅
Éditeur No-Code
Création de services
✅
Éditeur de Relations
Canvas visuel
🟡 (Partiel)
⚙️ 6. CONFIGURATION
Fichiers de Configuration:
Fichier
Path
Description
settings.json
%LOCALAPPDATA%\NetworkMonitoringProject\config\ (Windows)
Settings utilisateur
hebergement_web.json
/etc/itops/ (Linux)
Configuration serveur
auth.json
/etc/itops/auth.json
Stockage des hashs admin
.env
/etc/default/itops
Variables d'environnement
Variables d'Environnement:
# MariaDB
NMP_MARIADB_HOST=127.0.0.1
NMP_MARIADB_PORT=3306
NMP_MARIADB_USER=itops
NMP_MARIADB_PASSWORD=*****
NMP_MARIADB_DATABASE=itops

# Application
NMP_HEBERGEMENT_CONFIG=/etc/itops/hebergement_web.json
NMP_AUTH_STORE_PATH=/etc/itops/auth.json
NMP_DATA_DIR=/var/lib/itops
NMP_ENABLE_KEYRING=0  # Désactivé par défaut

# Dev Mode (Windows/PyCharm)
NMP_DEV_SKIP_SETUP_WIZARD=1
NMP_SETUP_SKIP_MARIADB_PROVISION=1
NMP_SETUP_SKIP_REVERSE_PROXY_SETUP=1
NotificationSettings (Dataclass):
@dataclass
class NotificationSettings:
    # Logging
    log_level: str = "INFO"
    monitoring_log_level: str = "INFO"
    ui_log_level: str = "ERROR"

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_auth_enabled: bool = False
    user: str = ""  # SMTP user
    password: str = ""  # SMTP password (via keyring)
    use_tls: bool = True
    recipients: str = ""  # Email recipients

    # Monitoring
    offline_delay_seconds: int = 20
    online_recovery_delay_seconds: int = 10
    notification_cooldown_seconds: int = 120
    monitoring_notify_on_outage: bool = True
    monitoring_notify_on_recovery: bool = True

    # Monitoring Parameters
    failures_for_offline: int = 5
    successes_for_online: int = 3
    ping_timeout_ms: int = 2500
    probe_interval_ms: int = 2000
    log_diagnostic_events: bool = False

    # Web
    web_session_ttl_seconds: int = 3600
    web_revoke_sessions_on_startup: bool = True
📋 MÉTHODOLOGIE DE DÉVELOPPEMENT
🔨 Patterns de Code
1. Backend (Python)
# ✅ Bon
class DeviceService:
    def __init__(self, manager: MariaDBFileManager) -> None:
        self._mgr = manager

    def list_devices(self) -> list[Device]:
        with self._mgr._lock:  # Thread-safe
            return self._mgr.read_devices()

# ❌ À éviter
class DeviceService:
    def list_devices(self):
        # Pas de lock, pas de typage
        return db.query("SELECT * FROM devices")
2. Frontend (JavaScript)
// ✅ Bon
function getDevices() {
    return sharedApi.get('/devices')
        .then(response => response.json())
        .catch(error => sharedUi.showError(error));
}

// ❌ À éviter
function getDevices() {
    // Duplication de code, pas de gestion d'erreur
    fetch('/devices', {headers: {...}})
        .then(r => r.json());
}
3. Architecture MVC
# Controller
class DeviceTypeController:
    def __init__(self, service: DeviceTypeService) -> None:
        self._service = service

    def list_types(self) -> list[dict]:
        return self._service.list_types()

# Service
class DeviceTypeService:
    def list_types(self) -> list[dict]:
        return self._mgr.list_device_types()

# Repository
class DeviceTypeRepository(MariaDBRepository):
    def list_device_types(self) -> list[dict]:
        # Accès MariaDB
        pass
📝 Bonnes Pratiques
Pratique
Description
Exemple
Centralisation
Code partagé au niveau le plus haut
shared_ui.js, theme_manager.py
Héritage
Modules héritent du portail
portal.js → app.js
Validation
Toujours valider en entrée
Pydantic, validate_device_fields()
Thread-Safety
Locks sur données partagées
with self._lock:
Logging
Logs systématiques
log_with_timestamp()
Error Handling
Exceptions spécifiques
DeviceReadingError, PasswordChangeRequiredError
Typing
Annotations systématiques
def func(arg: str) -> int:
Tests
Tests ciblés
test_custom_service_records_tabular.py
❌ Anti-Patterns (À Éviter)
Anti-Pattern
Pourquoi
Solution
Logique métier dans l'API
Difficile à tester/maintenir
Déplacer dans services/
Duplication portal.js ↔ app.js
Incohérence, maintenance lourde
Centraliser dans shared_*.js
Couleurs en dur dans JS
Thème non maintenable
Utiliser tokens CSS
Couplage route ↔ DOM
Fragile
Utiliser shared_api.js
Décisions de persistance dans frontend
Sécurité, cohérence
Tout dans services/ + API
Modification directe de DevicesModel
Thread-safety
Toujours via DeviceService
🎯 Règles d'Architecture (docs/architecture_mvc.md)
1.
Centraliser au niveau portail/shared
◦
Si plusieurs pages utilisent la même logique → shared_*.js
◦
Si plusieurs modules utilisent la même couleur → theme_manager.py
2.
Faire hériter les modules
◦
app.js doit hériter de shared_ui.js
◦
portal.js doit utiliser shared_api.js
3.
Spécialiser uniquement quand nécessaire
◦
Ne pas dupliquer du code pour une légère variation
◦
Utiliser des paramètres pour généraliser
4.
Éviter la duplication
◦
DRY (Don't Repeat Yourself) partout
◦
Si du code est copié → factoriser
5.
Mettre à jour la documentation
◦
Toute nouvelle règle architecturale → documenter
◦
Toute modification majeure → mettre à jour architecture_mvc.md
Phrase directrice: "Centraliser au niveau portail/shared, faire hériter les modules, spécialiser uniquement quand le besoin métier l'impose."
🧪 Tests
Framework:
•
pytest: Tests unitaires Python
•
Node --check: Validation syntaxe JS
Stratégie:
# Installation
pip install -r requirements-dev.txt

# Exécution
pytest                          # Tous les tests
pytest -q                       # Mode silencieux
pytest monitoring/tests/        # Tests spécifiques
pytest -k "custom_service"      # Filtre par nom

# Validation JS
node --check monitoring/web/app.js
Exemple de Test:
# test_custom_service_records_tabular.py
from monitoring.services.custom_service_records_tabular import (
    infer_custom_service_records_from_rows,
    resolve_effective_record_column_mapping,
)

def test_record_import_falls_back_to_positional_mapping() -> None:
    rows, detected_rows, detected_columns, issues = infer_custom_service_records_from_rows(
        headers=["Colonne A", "Colonne B"],
        rows=[["Portail", "192.0.2.10"]],
        fields=[
            {"field_key": "name", "label": "Nom"},
            {"field_key": "ip", "label": "IP"},
        ],
    )

    assert detected_rows == 1
    assert issues == ["Aucune correspondance exacte d'entete: colonnes mappees par position."]
    assert rows[0]["values"] == {"name": "Portail", "ip": "192.0.2.10"}
Couvertures de Test:
Module
Tests
Couverture
Custom Service Records
5 tests
✅ Bonne
Custom Service Index
1 test
🟡 À améliorer
Device Inventory
2 tests
🟡 À améliorer
Theme Manager
0 test
❌ Manquant
API Routes
0 test
❌ Manquant
🚀 DÉPLOIEMENT
🪟 Windows
1. Build de l'Application
# Depuis PowerShell (racine du projet)
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Clean
Ce que fait le script:
1.
Vérifie Python 3.12
2.
Installe les dépendances de build (requirements-build.txt)
3.
Prépare Caddy (reverse proxy)
4.
Prépare MariaDB (package Windows)
5.
Build avec PyInstaller:
◦
Mode onedir (dossier portable)
◦
Icône personnalisée
◦
Hidden imports (aioping, click, keyring)
◦
Inclusion des assets (web, assets, scripts runtime)
6.
Génère l'installateur avec Inno Setup (si ISCC.exe disponible)
Sorties:
•
Application portable: dist\NetworkMonitoringProject\
•
Installateur: installer\output\NetworkMonitoringProject-Setup-<version>.exe
2. Contenu du Build
dist\NetworkMonitoringProject\
├── NetworkMonitoringProject.exe  # Point d'entrée
├── _internal\                     # Fichiers internes PyInstaller
│   ├── monitoring\
│   │   ├── web\                  # Frontend
│   │   ├── assets\               # Images, icônes
│   │   └── ...                  # Code Python
│   ├── tools\
│   │   ├── caddy\                # Binaire Caddy
│   │   └── mariadb\              # Installateur MariaDB
│   └── scripts\runtime\          # Scripts d'installation
└── ...                          # Autres dépendances
3. Installation Windows
1.
Lancer NetworkMonitoringProject-Setup-<version>.exe
2.
Suivre le wizard:
◦
Choix du dossier d'installation
◦
Création de raccourcis
◦
Installation du service Windows
◦
Initialisation de Caddy (reverse proxy local)
3.
Premier lancement:
◦
Le service démarre automatiquement
◦
Accès via http://127.0.0.1:8080/
◦
Setup web si premier lancement
4. Service Windows
•
Nom: NetworkMonitoringProject
•
Type: Service Windows natif
•
Démarrage: Automatique
•
Port: 8080 (configurable)
🐧 Linux (Debian/Ubuntu)
1. Bootstrap (Primo-Installation)
# En root
curl -fsSL https://raw.githubusercontent.com/D4MS06/ITops/pre-release/1.0/scripts/linux/bootstrap_debian.sh -o /tmp/bootstrap_itops.sh
bash /tmp/bootstrap_itops.sh
Ce que fait le script (bootstrap_debian.sh):
1.
Vérifications: Root, installation existante
2.
Installation des dépendances:
apt-get install -y git python3 python3-venv python3-pip mariadb-server mariadb-client curl caddy nginx openssl cifs-utils
3.
Configuration MariaDB:
◦
Active le service
◦
Crée la base de données
◦
Crée l'utilisateur itops
◦
Configure les permissions
4.
Préparation des dossiers:
◦
/etc/itops/ (config)
◦
/var/log/itops/ (logs)
◦
/var/lib/itops/ (data)
5.
Récupération du code:
◦
Clone le repo dans /opt/itops
◦
Checkout sur pre-release/1.0
6.
Installation Python:
◦
Crée un virtualenv (/opt/itops/.venv)
◦
Installe les dépendances (requirements.txt)
7.
Configuration:
◦
Génère un token de setup (/etc/itops/setup.token)
◦
Crée hebergement_web.json
◦
Crée /etc/default/itops (env vars)
8.
Service systemd:
◦
Crée /etc/systemd/system/itops.service
◦
Active et démarre le service
9.
Marqueur d'installation: /etc/itops/.installed
2. Configuration Générée
/etc/itops/hebergement_web.json:
{
  "hote_ecoute": "0.0.0.0",
  "port_ecoute": 8080,
  "demarrage_auto_service": true,
  "utiliser_url_publique_reverse_proxy": false,
  "url_publique": "",
  "reverse_proxy_actif": false,
  "reverse_proxy_type": "aucun"
}
/etc/default/itops:
NMP_MARIADB_HOST='127.0.0.1'
NMP_MARIADB_PORT='3306'
NMP_MARIADB_USER='itops'
NMP_MARIADB_PASSWORD='ChangeMoiFort!'
NMP_MARIADB_DATABASE='itops'
NMP_MARIADB_ROOT_PASSWORD='MDPFort1234!'
NMP_MARIADB_BIN_DIR='/usr/bin'
NMP_HEBERGEMENT_CONFIG='/etc/itops/hebergement_web.json'
NMP_SETUP_CONFIG='/etc/itops/setup_installation.json'
NMP_SETUP_TOKEN_FILE='/etc/itops/setup.token'
NMP_INSTALL_ENV_PATH='/etc/default/itops'
NMP_AUTH_STORE_PATH='/etc/itops/auth.json'
NMP_DATA_DIR='/var/lib/itops'
NMP_APP_USER='root'
NMP_STORAGE_HELPER='/usr/local/sbin/itops-storage-helper'
3. Service systemd
/etc/systemd/system/itops.service:
[Unit]
Description=ITops Web Service
After=network-online.target mariadb.service
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/itops
EnvironmentFile=/etc/default/itops
ExecStartPre=/usr/local/lib/itops/itops-prestart.sh
ExecStart=/opt/itops/.venv/bin/python main.py --mode server --host 0.0.0.0 --port 8080
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
/usr/local/lib/itops/itops-prestart.sh:
•
Vérifie que MariaDB est disponible avant de démarrer l'app
4. Finalisation via Wizard Web
1.
Accéder à http://<ip_serveur>:8080/setup
2.
Saisir le token affiché par le script bootstrap
3.
Définir:
◦
Mot de passe admin
◦
Paramètres MariaDB (si différents)
◦
Configuration Reverse Proxy (Caddy/Nginx)
4.
Le wizard:
◦
Configure le reverse proxy automatiquement
◦
Redirige vers l'URL publique
5. Reverse Proxy (Caddy)
Si reverse_proxy_type = "caddy":
•
Caddy est installé mais désactivé par défaut
•
Le wizard active et configure Caddy automatiquement
•
Configuration générée dans /etc/caddy/Caddyfile
Exemple de configuration Caddy:
monitoring.mvl {
    reverse_proxy 127.0.0.1:8080
}
🔄 Mise à Jour (Upgrade)
Windows:
# Arrêter le service
Stop-Service NetworkMonitoringProject

# Sauvegarder les données (optionnel)
Copy-Item -Path "$env:LOCALAPPDATA\NetworkMonitoringProject" -Destination "C:\backup\itops" -Recurse

# Lancer le nouvel installateur
.\installer\output\NetworkMonitoringProject-Setup-<new-version>.exe

# Redémarrer le service
Start-Service NetworkMonitoringProject
Linux:
# Arrêter le service
sudo systemctl stop itops

# Sauvegarder les données
sudo cp -r /etc/itops /etc/itops.backup
sudo cp -r /var/lib/itops /var/lib/itops.backup

# Mettre à jour le code
cd /opt/itops
git fetch --all --prune
git checkout pre-release/1.0
git pull --ff-only origin pre-release/1.0

# Mettre à jour les dépendances
/opt/itops/.venv/bin/pip install -r requirements.txt

# Redémarrer le service
sudo systemctl restart itops
Script dédié:
# Sur la VM Debian
bash /opt/itops/scripts/linux/upgrade_itops.sh
📈 ROADMAP & ÉVOLUTIONS
🎉 Historique des Versions
Version
Date
Principales évolutions
1.0-pre-release
2026-07
Actuelle - Backend partagé, interface web exploitable, auth, dashboard live
1.0.7
-
Backend partagé desktop/web, première interface web exploitable, serveur web embarqué, mode remote cohérent, watermark/thème partagés, sessions admin persistantes, thread-safety
1.0.6
-
Extraction DeviceService/MonitoringService, AuthService, backend applicatif partagé, squelette FastAPI
1.0.5
-
Refactor MVC, dashboard en mixins, optimisation persistance DB, réorganisation menus, clarification actions contextuelles
1.0.4
-
Types de devices dynamiques, éditeur de formulaire modulaire, catalogue plugins drag-and-drop, dashboard dynamique, edition dashboard
1.0.3
-
Thème global Light/Dark, personnalisation (watermark, indicateurs de statut), distinction état Idle, correctifs de robustesse
🚀 Feuille de Route (d'après docs/)
1. Priorités Courantes (1.0 Finalisation)
Tâche
Description
Complexité
Impact
✅ Finaliser le wizard web
Setup complet (BDD, reverse proxy, auth)
Moyenne
⭐⭐⭐⭐⭐
✅ Stabiliser le monitoring
Thread-safety, performances
Élevée
⭐⭐⭐⭐⭐
✅ Interface web exploitable
Dashboard, TreeView, actions
Élevée
⭐⭐⭐⭐⭐
🟡 Éditeur de relations
Canvas drag-and-drop
Élevée
⭐⭐⭐⭐
🟡 Pièces jointes no-code
Intégration storage
Moyenne
⭐⭐⭐
🟡 Audit complet
Logging des actions
Moyenne
⭐⭐⭐
2. Prochaines Versions (Post-1.0)
Feature
Description
Priorité
Éditeur graphique de thèmes
Personnalisation UI avancée
Moyenne
API GraphQL
Alternative à REST
Basse
Plugins Python
Extensibilité code
Moyenne
Synchronisation temps réel
WebSockets bidirectionnels
Élevée
Mobile App
Application compagnon
Basse
Multi-tenancy
Support multi-clients
Moyenne
Clustering
Scalabilité horizontale
Basse
📋 Backlog Technique (Issues Identifiés)
ID
Titre
Description
Priorité
T-001
Tests manquantes
Peu de tests API et frontend
⭐⭐⭐⭐
T-002
Documentation utilisateur
Manuel d'utilisation manquant
⭐⭐⭐
T-003
Performance DB
Optimisation des requêtes
⭐⭐⭐
T-004
Internationalisation
Support multi-langues
⭐⭐
T-005
Éditeur de relations
Finaliser le canvas
⭐⭐⭐⭐
T-006
Pièces jointes
Implémenter le storage
⭐⭐⭐
T-007
Audit
Historique des actions
⭐⭐⭐
T-008
Monitoring du monitoring
Métriques app
⭐⭐
T-009
Upgrade automatisé
Migration DB automatique
⭐⭐⭐
T-010
Backup/Restore
Sauvegarde complète
⭐⭐⭐
🎯 RECOMMANDATIONS STRATÉGIQUES
🏆 Priorités Immédiates (0-3 mois)
1. Finaliser la Version 1.0
•
Objectif: Version stable, déployable en production
•
Actions:
◦
[ ] Corriger les bugs critiques (thread-safety, mémoire)
◦
[ ] Finaliser le wizard de setup
◦
[ ] Stabiliser le monitoring (tests de charge)
◦
[ ] Documenter l'installation et l'utilisation
◦
[ ] Créer des tests d'intégration
2. Améliorer la Qualité de Code
•
Objectif: Code plus maintenable et robuste
•
Actions:
◦
[ ] Augmenter la couverture de tests (>80%)
◦
[ ] Documenter les API internes
◦
[ ] Refactorer les parties critiques (app.py trop gros)
◦
[ ] Ajouter des linting (ruff, mypy)
3. Optimiser les Performances
•
Objectif: Scalabilité à 1000+ devices
•
Actions:
◦
[ ] Pool de connexions MariaDB
◦
[ ] Cache des requêtes fréquentes
◦
[ ] Pagination des résultats API
◦
[ ] Optimisation des WebSockets
🚀 Priorités Moyennes (3-6 mois)
1. Finaliser le Moteur No-Code
•
Objectif: Rendre le no-code production-ready
•
Actions:
◦
[ ] Finaliser l'éditeur de relations (canvas)
◦
[ ] Implémenter les pièces jointes
◦
[ ] Ajouter l'audit complet
◦
[ ] Optimiser les imports/exports
◦
[ ] Documenter le moteur no-code
2. Améliorer l'Expérience Utilisateur
•
Objectif: Interface plus intuitive
•
Actions:
◦
[ ] Ajouter des tutoriels interactifs
◦
[ ] Améliorer les messages d'erreur
◦
[ ] Optimiser les performances frontend
◦
[ ] Ajouter des raccourcis clavier
◦
[ ] Implémenter un éditeur de thèmes
3. Étendre les Fonctionnalités
•
Objectif: Répondre aux besoins métiers
•
Actions:
◦
[ ] Ajouter le support SNMP avancé
◦
[ ] Intégrer Grafana/Prometheus
◦
[ ] Ajouter des dashboards personnalisables
◦
[ ] Implémenter des alertes avancées
◦
[ ] Ajouter le support IPAM
🌌 Priorités Long Terme (6-12 mois)
1. Scalabilité et Haute Disponibilité
•
Objectif: Déploiement en cluster
•
Actions:
◦
[ ] Support multi-instances
◦
[ ] Load balancing
◦
[ ] Base de données répartie
◦
[ ] Cache distribué (Redis)
◦
[ ] File d'attente (RabbitMQ/Kafka)
2. Extensibilité
•
Objectif: Écosystème de plugins
•
Actions:
◦
[ ] API de plugins Python
◦
[ ] Marketplace de plugins
◦
[ ] Documentation pour développeurs
◦
[ ] Exemples de plugins
3. Internationalisation
•
Objectif: Support multi-langues
•
Actions:
◦
[ ] Extraction des strings
◦
[ ] Système de traduction
◦
[ ] Traduction en anglais
◦
[ ] Support RTL
4. Mobilité
•
Objectif: Accès depuis mobile
•
Actions:
◦
[ ] Application mobile (React Native/Flutter)
◦
[ ] PWA (Progressive Web App)
◦
[ ] Notifications push
💼 PLAN D'ACTION POUR LA PRISE DE SUITE
📅 Semaine 1: Immersion et Audit
Jour
Tâche
Livrable
1
Lecture complète du code
Compréhension globale ✅
1
Setup environnement dev
Environnement fonctionnel
2
Analyse des bugs ouverts
Liste des issues critiques
2
Test de l'application
Rapport de test
3
Rencontre avec l'équipe
Compréhension des besoins
3
Audit sécurité
Rapport de sécurité
4
Audit performances
Benchmark actuel
5
Synthèse
Rapport d'audit complet
Actions concrètes:
# Cloner le repo (déjà fait)
git clone https://github.com/D4MS06/ITops.git
cd ITops
git checkout pre-release/1.0

# Setup dev environment
python -m venv .venv
source .venv/bin/activate  # Linux
.venv\Scripts\activate     # Windows
pip install -r requirements.txt -r requirements-dev.txt

# Lancer en mode dev
export NMP_DEV_SKIP_SETUP_WIZARD=1
python main.py --mode server --reload
📅 Semaine 2: Stabilisation et Tests
Jour
Tâche
Livrable
1
Correction des bugs critiques
Patchs appliqués
2
Écrire des tests unitaires
Couverture > 50%
3
Optimisation DB
Index manquants ajoutés
4
Test de charge
Rapport de performance
5
Documentation technique
Mise à jour des docs
Actions concrètes:
# Lancer les tests existants
pytest -v

# Analyser la couverture
pytest --cov=monitoring --cov-report=html
open htmlcov/index.html

# Tester le monitoring
curl http://localhost:8080/health
curl -H "Authorization: Bearer <token>" http://localhost:8080/monitoring/snapshot
📅 Semaine 3: Déploiement et Formation
Jour
Tâche
Livrable
1
Déploiement en staging
Environnement de test
2
Formation équipe
Session de formation
3
Documentation utilisateur
Manuel d'utilisation
4
Feedback utilisateurs
Liste d'améliorations
5
Plan de release 1.0
Roadmap finalisée
Actions concrètes:
# Build pour staging
./scripts/build_windows.ps1 -Clean

# Déploiement Linux (staging)
bash scripts/linux/bootstrap_debian.sh

# Vérification
systemctl status itops
journalctl -u itops -f
📅 Semaine 4: Roadmap et Priorisation
Jour
Tâche
Livrable
1
Analyse des besoins
Backlog priorisé
2
Estimation des tâches
Planning détaillé
3
Réunion de priorisation
Backlog validé
4
Création des tickets
Jira/GitHub Issues
5
Kickoff 1.0 Final
Équipe alignée
📊 INDICATEURS CLÉS (KPI)
📈 Métriques Techniques
Métrique
Valeur Actuelle
Cible
Statut
Couverture de tests
~10%
>80%
❌ Critique
Temps de réponse API
<200ms
<100ms
✅ Bon
Mémoire utilisée
~500MB
<1GB
✅ Bon
Devices supportés
1000+
10000+
🟡 À améliorer
Uptime
99.5%
>99.9%
🟡 À améliorer
Temps de déploiement
10min
<5min
🟡 À améliorer
💰 Métriques Business
Métrique
Valeur
Cible
Statut
Nombre d'utilisateurs
1 (dev)
100+
🟡 En croissance
Nombre de services no-code
0
50+
🟡 À développer
Temps d'onboarding
1h
<30min
🟡 À améliorer
Satisfaction utilisateur
N/A
>4.5/5
🟡 À mesurer
🔧 OUTILS & RESSOURCES
🛠️ Outils de Développement
Outil
Utilisation
Commande
PyCharm
IDE principal
-
VS Code
Alternative
-
Git
Versioning
git status, git commit
pytest
Tests unitaires
pytest -v
ruff
Linting Python
ruff check monitoring/
mypy
Type checking
mypy monitoring/
MariaDB Client
Requêtes DB
mysql -u itops -p
Postman
Tests API
-
Chrome DevTools
Debug frontend
F12
📚 Ressources Techniques
Ressource
Lien/Path
Description
Documentation
docs/
Architecture, no-code, Caddy
Changelog
CHANGELOG.md
Historique des versions
Release Checklist
docs/release_checklist.md
Checklist de release
API Reference
/docs (auto)
Documentation OpenAPI
Issues GitHub
https://github.com/D4MS06/ITops/issues
Bugs et features
Wiki
À créer
Documentation utilisateur
👥 Équipe et Contacts
Rôle
Nom
Email
Responsabilités
Architecte
Damien
-
Conception, développement
Chef de Projet
VOUS
-
Prise de suite complète
Dev Frontend
À désigner
-
JS, CSS, UI/UX
Dev Backend
À désigner
-
Python, MariaDB
DevOps
À désigner
-
Déploiement, CI/CD
⚠️ RISQUES & DÉFIS
🚨 Risques Techniques
Risque
Impact
Probabilité
Mitigation
Thread-safety
Corruption de données
Moyenne
Tests de stress, revues de code
Performance DB
Lenteur
Élevée
Optimisation, cache, index
Mémoire
OOM Killer
Moyenne
Monitoring, optimisation
Compatibilité
Bugs plateforme
Moyenne
Tests multi-OS
Sécurité
Vulnérabilités
Élevée
Audit, mises à jour
📉 Défis Organisationnels
Défi
Description
Solution
Équipe réduite
Peu de développeurs
Priorisation, automatisation
Documentation
Manque de docs utilisateur
Création de guides
Tests
Couverture faible
campagne de tests
Adoption
Résistance au changement
Formation, accompagnement
Maintenance
Code legacy
Refactoring progressif
🔒 Risques Sécurité
Risque
Description
Mitigation
Injection SQL
Requêtes non sécurisées
Utilisation de PyMySQL (paramétrized queries)
XSS
Contenu utilisateur non échappé
Échappement systématique
CSRF
Attaques cross-site
SameSite cookies, CSRF tokens
Authentification
Failles de session
Tokens opaques, TTL court
Secrets
Expositions de mots de passe
Keyring, masquage dans logs
✅ Bonnes pratiques déjà en place:
•
Hash PBKDF2-SHA256 pour les mots de passe
•
Tokens de session opaques
•
Requêtes SQL paramétrées (PyMySQL)
•
Pas de secrets dans le code ou les logs
•
Validation systématique des entrées
🎓 FORMATION & COMPÉTENCES REQUISES
📚 Compétences Techniques Nécessaires
Compétence
Niveau
Ressources
Python 3.12
Avancé
Documentation officielle
FastAPI
Avancé
fastapi.tiangolo.com
MariaDB/MySQL
Intermédiaire
mariadb.org
JavaScript (Vanilla)
Intermédiaire
MDN Web Docs
CSS3
Intermédiaire
MDN CSS
Linux (Debian)
Intermédiaire
Man pages
systemd
Intermédiaire
man systemd
Docker
Optionnel
docs.docker.com
Git
Avancé
git-scm.com
🎓 Plan de Formation (Pour l'Équipe)
Semaine 1: Fondamentaux
Jour
Sujet
Format
1
Architecture globale
Présentation + Q&A
1
Setup environnement dev
Atelier pratique
2
Backend Python
Code review + exercices
2
Frontend JS/CSS
Code review + exercices
3
Base de données
Atelier SQL
3
API FastAPI
Atelier pratique
4
Déploiement
Déploiement en local
5
No-Code Engine
Présentation + démo
Semaine 2: Approfondissement
Jour
Sujet
Format
1
Monitoring Service
Deep dive
2
Custom Services
Atelier création
3
Authentification
Sécurité
4
Storage & Files
Atelier
5
Tests & Debug
Bonnes pratiques
Semaine 3: Projet Pratique
Jour
Tâche
Livrable
1-3
Développement d'une feature
PR sur GitHub
4
Code review
Feedback
5
Déploiement en staging
Environnement fonctionnel
📞 SUPPORT & MAINTENANCE
🆘 Procédures de Support
1. Reporting de Bugs
1.
Reproduire le bug avec des étapes claires
2.
Vérifier les logs:
# Linux
journalctl -u itops -n 100 --no-pager
tail -n 100 /var/log/itops/monitoring.log

# Windows
# Voir les logs dans l'Event Viewer
3.
Collecter les informations:
◦
Version de l'application (__version__ dans __init__.py)
◦
OS et version (Windows 10/11, Debian X.Y)
◦
Version Python (python --version)
◦
Version MariaDB (mysql --version)
◦
Étapes pour reproduire
◦
Screenshot (si UI)
4.
Créer un ticket:
◦
Titre clair et descriptif
◦
Label: bug, enhancement, question
◦
Priorité: critical, high, medium, low
2. Escalade
Niveau
Critère
Responsable
Délai
1
Question simple
Équipe
<4h
2
Bug mineur
Dev assigné
<24h
3
Bug majeur
Chef de Projet
<8h
4
Incident critique
Équipe complète
Immédiat
🔧 Maintenance Préventive
Tâche
Fréquence
Responsable
Sauvegarde DB
Quotidienne
DevOps
Mise à jour dépendances
Mensuelle
Dev Backend
Test de restauration
Trimestrielle
DevOps
Audit sécurité
Trimestrielle
Chef de Projet
Revue de code
Par PR
Équipe
Nettoyage logs
Hebdomadaire
Script automatique
Script de sauvegarde:
#!/bin/bash
# Sauvegarde MariaDB
mysqldump -u itops -p"password" itops > /backup/itops-$(date +%Y%m%d).sql
gzip /backup/itops-$(date +%Y%m%d).sql

# Sauvegarde fichiers
tar -czvf /backup/itops-data-$(date +%Y%m%d).tar.gz /var/lib/itops /etc/itops

# Nettoyage ancien (>30 jours)
find /backup -name "itops-*.sql.gz" -mtime +30 -delete
find /backup -name "itops-data-*.tar.gz" -mtime +30 -delete
📊 Monitoring de l'Application
1. Métriques à Surveiller
Métrique
Outil
Seuil
CPU Usage
htop, top
<80%
Memory Usage
htop, free -h
<1GB
Disk Usage
df -h
<90%
DB Connections
SHOW STATUS LIKE 'Threads_connected'
<50
API Response Time
Prometheus/Grafana
<200ms
Error Rate
Logs
<1%
Uptime
systemd
>99.9%
2. Alertes
Condition
Action
Responsable
CPU > 90% pendant 5min
Investiger
DevOps
Memory > 1.5GB
Redémarrer service
DevOps
Disk > 95%
Nettoyer + étendre
DevOps
DB Connections > 80
Optimiser
Dev Backend
API Errors > 5%
Debugger
Équipe
Service down
Redémarrer
DevOps
Script de monitoring simple:
#!/bin/bash
# Vérifier le service
if ! systemctl is-active --quiet itops; then
    echo "Service ITops est DOWN!" | mail -s "ALERT: ITops Down" admin@example.com
    systemctl restart itops
fi

# Vérifier l'espace disque
if [ $(df / --output=pcent | tail -1 | tr -d '%') -gt 90 ]; then
    echo "Espace disque critique!" | mail -s "ALERT: Disk Full" admin@example.com
fi
🏁 CONCLUSION & PROCHAINES ÉTAPES
🎯 Résumé Exécutif
ITops est un projet mature, bien architecturé et innovant avec:
•
✅ Une architecture moderne (FastAPI, MariaDB, WebSockets)
•
✅ Un moteur no-code puissant pour services dynamiques
•
✅ Une méthodologie de développement rigoureuse
•
✅ Des scripts de déploiement complets (Windows/Linux)
•
✅ Une base solide pour la version 1.0
Points forts:
•
Code bien structuré et maintenable
•
Patterns éprouvés (MVC, Repository, Observer)
•
Extensibilité via le no-code
•
Déploiement professionnel
•
Sécurité robuste
Axes d'amélioration:
•
Couverture de tests faible
•
Documentation utilisateur manquante
•
Optimisation des performances
•
Finalisation du no-code (relations, pièces jointes)
🚀 Prochaines Étapes Immédiates
Priorité
Tâche
Responsable
Échéance
🔴 Critique
Corrections bugs bloquants
Chef de Projet
Semaine 1
🔴 Critique
Tests unitaires (couverture >50%)
Équipe Dev
Semaine 2
🟡 Haute
Finaliser le wizard setup
Dev Frontend
Semaine 2
🟡 Haute
Documentation utilisateur
Chef de Projet
Semaine 3
🟡 Haute
Déploiement en staging
DevOps
Semaine 3
🟢 Moyenne
Optimisation DB
Dev Backend
Semaine 4
🟢 Moyenne
Éditeur de relations
Dev Frontend
Semaine 5
📈 Vision Long Terme
"Devenir la plateforme de supervision réseau et de gestion de services métiers la plus flexible et intuitive du marché."
Objectifs stratégiques:
1.
Stabiliser la version 1.0 (Q3 2026)
2.
Finaliser le moteur no-code (Q4 2026)
3.
Atteindre 100 utilisateurs (2027)
4.
Développer l'écosystème (plugins, marketplace) (2027-2028)
5.
Scalabilité enterprise (2028+)
💬 Message Final
Félicitations ! Vous avez maintenant une compréhension complète du projet ITops. En tant que Chef de Projet Senior, vous avez toutes les clés pour:
•
✅ Comprendre l'architecture et le code existant
•
✅ Maintenir l'application en production
•
✅ Étendre les fonctionnalités
•
✅ Manager l'équipe de développement
•
✅ Décider des orientations stratégiques
Le projet est sur la bonne voie pour devenir un succès. Avec une bonne priorisation, une équipe motivée, et une méthodologie rigoureuse, ITops peut devenir une référence dans le domaine de la supervision réseau et des applications métiers no-code.