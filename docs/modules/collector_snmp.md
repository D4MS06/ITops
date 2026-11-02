# Collecteur universel et SNMP

## Etat

Le moteur universel de collecte et les profils SNMPv3 generique/Synology sont des travaux projetes. Aucun composant runtime ne les declare ici comme livres.

## Direction retenue

Le premier jalon envisage un orchestrateur extensible, un sous-moteur SNMPv3, des profils `generic_snmp` et `synology_dsm`, ainsi que des contrats anticipant SSH, WinRM et REST sans les implementer. Les secrets, la validation de profils, la journalisation et les droits doivent reutiliser les mecanismes existants.

La roadmap et les instructions de jalon precedentes sont archivees afin de conserver les choix de perimetre sans guider automatiquement une intervention courante.
