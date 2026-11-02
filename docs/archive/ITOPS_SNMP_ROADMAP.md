# Roadmap versionnée — Moteur universel de collecte Itops (phase SNMPv3)

**Prérequis :** l'agent Codex connaît déjà l'architecture d'Itops. Il ne doit pas recommencer un audit général. Chaque version commence seulement par une vérification ciblée des points d'intégration concernés.

**Périmètre initial :** moteur universel extensible + sous-moteur SNMPv3 + plugins SNMP générique et Synology. SSH, WinRM et REST sont uniquement anticipés par les interfaces, sans implémentation.

| Version | Objectif et livrable démontrable | Condition de validation |
|---|---|---|
| **v0.1** | Intégrer au dépôt la structure modulaire du moteur universel : orchestrateur, contrats d'adaptateurs, registre de plugins et tests de base | Réutilisation de l'architecture Itops ; tests réussis ; aucune régression |
| **v0.2** | Sous-moteur SNMPv3 : GET, WALK, BULK, authentification `authPriv` SHA/AES, erreurs et timeouts | Requêtes en lecture seule réussies sur le DS214+ ; aucun SET |
| **v0.3** | Plugins `generic_snmp` et `synology_dsm`, reconnaissance d'équipement, OID, interprétation et normalisation | Identification modèle/version DSM et parsing disques, volumes, SMART |
| **v0.4** | Mapping automatique des champs normalisés vers les fiches existantes ; politiques de synchronisation, prévisualisation, provenance | Fiche enrichie sans doublon ni écrasement des champs manuels |
| **v0.5** | Découverte et rattachement simplifiés d'un nouvel équipement (avec validation humaine) | Assistant d'intégration testé sur équipement existant et nouveau |
| **v0.6** | Interface/API de configuration SNMP, test de connexion, choix des profils et suivi des collectes | Parcours complet ; contrôle des droits ; secrets non exposés |
| **v0.7** | Planification, historique de collecte et alimentation du module Monitoring | Mesures horodatées ; gestion des erreurs et de l'état *stale* |
| **v1.0** | Stabilisation, tests de non-régression, sécurité, documentation et retour arrière | Recette validée et déploiement production explicitement autorisé |

## Règles de pilotage Codex
1. Ne travailler **que sur la version demandée** ; arrêter après rapport et validation.
2. Vérifier uniquement le code existant nécessaire au jalon, puis **implémenter** : pas d'audit général préalable.
3. Conserver un `device_id` unique et l'intégrité des données existantes.
4. Réutiliser coffre-fort, modèles, API, RBAC, tâches et tests existants autant que possible.
5. Ne jamais déployer automatiquement en production, ni modifier la configuration des équipements ; SNMP en lecture seule.
6. En fin de jalon : résumé des modifications, fichiers touchés, résultats de tests, risques, réversibilité, éléments à valider.

**Extensions post-v1.0 :** profils Aruba/HPE et autres équipements SNMP, puis connecteurs SSH / WinRM / REST selon les besoins, sans refonte de l'orchestrateur.
