# Monitoring et equipements reseau

## Role

Ce domaine gere l'inventaire reseau, les types de devices configurables, la supervision, les outils reseau et les fichiers de configuration. `monitoring/web/app.js` porte le contexte specialise ; `shared_monitoring_module.js` fournit la vue Monitoring native du portail.

## Contrats partages

Les devices et leurs types sont exposes par les routes de `monitoring/api/app.py`. Les menus de configuration sont fabriques par `shared_menu.js`. L'import de configuration est commun via `shared_device_config_files.js`. Le stockage distant et la planification utilisent `shared_config_storage.js`; Monitoring ouvre des modales enfants sans charger le module Equipements reseau.

Le flag de type `config_backups_enabled` conditionne les actions de configuration. Les versions de fichiers sont liees au device et conservees dans le stockage dedie ; l'existence d'une version est exposee au client pour activer les actions pertinentes.

La gestion des identifiants est definie par le schema du type : les champs reserves `device_login` et `device_password` existent ensemble lorsque l'option est active et sont absents sinon. Le couple actuel constitue le profil d'acces par defaut du device et conserve sa cle historique dans le coffre. Une evolution multi-acces devra ajouter des enregistrements enfants rattaches au device ; les secrets supplementaires peuvent utiliser un identifiant de profil dans la cle du coffre sans migrer le profil par defaut ni dupliquer les devices consommes par Monitoring.

Dans les fiches d'equipement, les champs TeamViewer, URL web et utilisateur SSH dependent des actions de prise en main a distance actives pour le systeme choisi, y compris apres un changement de systeme dans le formulaire. Le plugin Remote Desktop utilise l'adresse IP du champ commun et ne requiert pas de champ supplementaire. Les valeurs masquees restent conservees ; l'option distincte de gestion des identifiants pilote les champs login et mot de passe.

La fiche affiche les plugins de prise en main actifs pour l'OS du device sous forme de cartouches. Un clic reutilise l'action distante configuree : TeamViewer et Web ouvrent leur URL, Remote Desktop ouvre le choix de lancement du raccourci RDP, et SSH propose le client local via `ssh://` avec la commande en secours. Un cartouche dont les donnees de connexion manquent est desactive.

Dans la fiche, l'icone œil du champ mot de passe ouvre la revelation protegee par le mot de passe de session lorsque l'equipement possede un mot de passe stocke. La liste des equipements propose une icone de prise en main pour l'action distante par defaut du device ou de son OS, seulement si ce plugin dispose des donnees necessaires. Cette icone lance l'action configuree sans basculer vers un autre plugin.

## Fonctions confirmees

- inventaire, types, import/export, filtres et actions de device ;
- l'export de l'inventaire peut porter sur le fichier standard ou sur la vue du Treeview, avec ses colonnes visibles dans leur ordre ; le filtre d'affichage « Tout » permet d'inclure toutes les lignes ; le nom du fichier est modifiable et le dossier est choisi via le navigateur lorsqu'il le permet ;
- supervision, snapshot, journaux et demarrage/arret selon les permissions ;
- outils Ping, ports, traceroute, DNS, HTTP(S), SNMP et scan reseau ;
- le scan identifie l'adresse IPv4 du proxy ITops a partir de l'URL publique configuree (Caddy ou Nginx), l'affiche comme « Proxy ITops » et n'offre pas d'ajout de device pour cette ligne ;
- import, consultation et telechargement des configurations de devices eligibles ;
- stockage local, redondance SMB3, test, sauvegarde manuelle et planification automatique.

## Limites

Le stockage reste specialise aux configurations de devices. La synchronisation automatique est executee par le runner de l'API ; elle n'est pas encore planifiee par un moteur d'automation commun. Une destination SMB sous Linux requiert un chemin deja monte et les dependances systeme adequates.

L'identification du proxy dans un scan requiert une URL publique configuree et resolvable en IPv4 depuis le serveur ITops. Les autres hotes ne sont pas classes comme proxy sur la seule base d'une reponse HTTP Caddy.
