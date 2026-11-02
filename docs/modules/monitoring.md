# Monitoring et equipements reseau

## Role

Ce domaine gere l'inventaire reseau, les types de devices configurables, la supervision, les outils reseau et les fichiers de configuration. `monitoring/web/app.js` porte le contexte specialise ; `shared_monitoring_module.js` fournit la vue Monitoring native du portail.

## Contrats partages

Les devices et leurs types sont exposes par les routes de `monitoring/api/app.py`. Les menus de configuration sont fabriques par `shared_menu.js`. L'import de configuration est commun via `shared_device_config_files.js`. Le stockage distant et la planification utilisent `shared_config_storage.js`; Monitoring ouvre des modales enfants sans charger le module Equipements reseau.

Le flag de type `config_backups_enabled` conditionne les actions de configuration. Les versions de fichiers sont liees au device et conservees dans le stockage dedie ; l'existence d'une version est exposee au client pour activer les actions pertinentes.

La gestion des identifiants est definie par le schema du type : les champs reserves `device_login` et `device_password` existent ensemble lorsque l'option est active et sont absents sinon. Le couple actuel constitue le profil d'acces par defaut du device et conserve sa cle historique dans le coffre. Une evolution multi-acces devra ajouter des enregistrements enfants rattaches au device ; les secrets supplementaires peuvent utiliser un identifiant de profil dans la cle du coffre sans migrer le profil par defaut ni dupliquer les devices consommes par Monitoring.

## Fonctions confirmees

- inventaire, types, import/export, filtres et actions de device ;
- supervision, snapshot, journaux et demarrage/arret selon les permissions ;
- outils Ping, ports, traceroute, DNS, HTTP(S), SNMP et scan reseau ;
- import, consultation et telechargement des configurations de devices eligibles ;
- stockage local, redondance SMB3, test, sauvegarde manuelle et planification automatique.

## Limites

Le stockage reste specialise aux configurations de devices. La synchronisation automatique est executee par le runner de l'API ; elle n'est pas encore planifiee par un moteur d'automation commun. Une destination SMB sous Linux requiert un chemin deja monte et les dependances systeme adequates.
