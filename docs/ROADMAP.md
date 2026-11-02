# Roadmap verifiee

Cette feuille ne reprend que les travaux non confirmes par le code ou explicitement proposes.

## Moteur no-code

**Etat : partiel.** Les services, schemas, relations, records, import/export et doublons existent. Restent des ameliorations proposees : index de recherche dedie, audit metier complet, extraction des credentials hors des valeurs JSON et decoupage additionnel du frontend. Voir [modules/no_code.md](modules/no_code.md).

## Pieces jointes no-code

**Etat : projete.** Le stockage de configurations de devices existe mais ne constitue pas encore un contrat de documents generiques par service. La conception a valider couvre categories, liens record/fichier, permissions et import/export. Voir [modules/attachments.md](modules/attachments.md).

## Collecteur universel

**Etat : projete.** Le prochain jalon envisage un moteur extensible avec SNMPv3 et profils generique/Synology. SSH, WinRM et REST ne sont pas inclus dans ce jalon. Voir [modules/collector_snmp.md](modules/collector_snmp.md).

## Automatisation des sauvegardes de configuration

**Etat : partiel.** Le runner de synchronisation automatique est operationnel avec des frequences persistantes. Le rapprochement avec un moteur d'automation generique reste une evolution a cadrer sans changer le contrat actuel.

## Marches et commandes

**Etat : specification.** Le besoin est archive comme cahier des charges et n'est pas presente comme module livre.
