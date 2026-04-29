# Changelog

## 1.0.9-pre-release - 2026-04-29

- gel fonctionnel full-web pour la branche `pre-release/1.0.9`
- mode de lancement aligne serveur uniquement (API + UI web)
- checklist release mise a jour avec gates full-web et primo-install
- parcours d'import inventaire renforce:
  - previsualisation fichier source
  - mapping manuel colonnes -> champs applicatifs
  - recalcul d'aperçu avant application
  - meilleure tolerance preview quand l'auto-detection initiale ne trouve aucune ligne exploitable
- couverture de tests API et import ajustee pour les nouveaux flux de mapping

## 1.0.8 - 2026-03-26

- gel de version et alignement metadata applicative sur `1.0.8`
- evolution du pilotage des types: avertissements explicites avant purge a la desactivation (monitoring/config)
- purge automatique des logs de statut lors de la desactivation du monitoring d'un type
- purge automatique des fichiers de configuration et metadonnees associees lors de la desactivation config
- harmonisation desktop/web des menus et des indicateurs de presence de configuration (`Cfg`)
- ajustement des sous-menus journaux pour n'afficher que les types monitorables
- correctifs UX desktop/web autour de la gestion des fichiers de configuration et des confirmations de suppression
- regeneration du setup Windows `1.0.8`

## 1.0.7-pre-release - 2026-03-24

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
- ajout d'une gestion d'equipements dediee desktop/web (liste par type, ajout, edition, suppression)
- harmonisation des formulaires d'edition avec la logique plugins/actions selon OS definie par les schemas
- ajout de la mutualisation Treeview (tri + recherche conditionnelle) sur les dialogues desktop cibles
- refactor de l'ergonomie web: table inventaire allegee et actions par icones (modifier/supprimer)
- correctifs de navigation web (retour supervision depuis gestion des equipements) et coherence de section active
- ajout des outils reseau web en flux quasi temps reel (ping continu, traceroute streaming)
- securisation/fiabilisation du flux certificat HTTPS et ajustements de comportement runtime associes
- optimisation des handlers web par delegation d'evenements pour reduire la duplication et le cout de rendu
- integration de Ruff dans l'outillage dev et nettoyage lint (imports/variables mortes + correctifs de portee)
- amelioration de lisibilite de la fenetre des journaux de statut (nom + IP, transitions explicites, marquage des equipements supprimes)

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
