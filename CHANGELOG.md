# Changelog

## 1.0.7-pre-release - 2026-03-19

- ajout d'un runtime de monitoring partage entre desktop Tkinter et serveur web embarque
- ajout d'un mode serveur HTTP et d'un serveur web embarque pilotable depuis le desktop
- ajout d'une premiere interface web de supervision avec authentification, dashboard live et commandes monitoring
- alignement progressif de l'UI web sur la philosophie du desktop, y compris le watermark partage
- ajout d'un pilotage distant coherent du monitoring entre desktop et web
- durcissement du moteur avec verrouillage thread-safe de `DevicesModel`
- separation du cycle de vie entre API HTTP et runtime de monitoring partage
- optimisation du flux temps reel avec diffusion d'etat partagee pour les WebSockets
- persistance SQLite des sessions d'authentification admin pour survivre aux redemarrages serveur
- correction de lisibilite et de comportement des controles `Serveur web` dans le dashboard desktop
- refactoring de modularisation approfondi: extraction des repositories SQLite, services transverses et mixins dashboard
- reduction de complexite du dashboard principal via separation structure/menu/topbar/monitoring/web-server/lifecycle
- gel du scope d'optimisation (objectif pre-release), validation runtime (desktop + server) et campagne de tests verte
- regeneration du setup Windows `1.0.7-pre-release` pour aligner l'installateur avec le code pousse

## 1.0.6-pre-release

- extraction de `DeviceService` pour centraliser le CRUD, la validation, la recherche et la serialisation des equipements
- extraction de `MonitoringService` pour isoler le moteur de supervision, les transitions d'etat, les logs et les notifications hors de Tkinter
- ajout de `AuthService` avec hash admin, login/logout et sessions tokenisees
- ajout d'un backend applicatif partage pour aligner desktop Tkinter et API HTTP sur la meme pile de services
- ajout d'un squelette FastAPI avec endpoints auth, devices, device-types, logs, config-files et settings
- correction de la mise a jour des tuiles dashboard et des refresh UI sur transitions `idle -> online/offline`
- correction de la parallelisation du fallback `ping.exe` pour eviter les blocages de supervision sur des lots volumineux
- correction de l'injection de l'icone native Windows dans le build PyInstaller et les raccourcis du setup Inno Setup
- ajout des tests backend, API, auth, device service, monitoring service et dashboard counts
