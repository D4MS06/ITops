# Etat fonctionnel confirme

## Portail et administration

Le portail fournit l'authentification, les droits de module, les preferences UI, les modules administratifs, les listes partagees et les services dynamiques. Les services no-code possedent schemas, records, relations, import/export, recherche et gestion des doublons. Voir [modules/no_code.md](modules/no_code.md).

## Monitoring et equipements reseau

L'inventaire de devices, les types configurables, les outils reseau, la supervision et les journaux sont disponibles. Monitoring et Equipements reseau partagent les menus et actions de fichiers de configuration. La creation de device appartient au contexte Equipements reseau. Voir [modules/monitoring.md](modules/monitoring.md).

Les configurations de device sont conservees localement et peuvent etre sauvegardees vers un stockage distant SMB3 configure. La sauvegarde manuelle et la synchronisation automatique sont accessibles depuis Monitoring ; la planification expose les intervalles un jour, semaine, mois ou an. La planification est executee par un runner API, pas encore par un moteur d'automation generique.

## Documents et stockage

Les fichiers de configuration possedent un stockage specialise. Les pieces jointes generiques de services no-code sont une extension projetee, non une fonctionnalite confirmee. Voir [modules/attachments.md](modules/attachments.md).

## Collecte et integrations

Les synchronisations Active Directory sont presentes dans les settings et services d'annuaire. Le collecteur universel SNMPv3 reste un projet documente, non un composant runtime confirme. Voir [modules/collector_snmp.md](modules/collector_snmp.md).

## Exploitation

Le reverse proxy Caddy est documente pour les deploiements Windows et Linux dans [caddy_reverse_proxy.md](caddy_reverse_proxy.md). Les contraintes d'installation et de lancement sont conservees dans le README.
