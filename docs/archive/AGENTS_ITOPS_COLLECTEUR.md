# Instructions Codex — moteur universel de collecte Itops (phase SNMPv3)

## Contexte et mission
Tu connais déjà Itops, son architecture, ses modèles de données, son module Gestion des équipements, son Monitoring et son coffre-fort. **Ne recommence pas un audit général du dépôt.** Réutilise les conventions, services, modèles et mécanismes existants.

Développer et intégrer dans Itops un **moteur universel de collecte**, composé :
1. d'un orchestrateur transversal (planification, exécution, identification, erreurs et traçabilité) ;
2. de sous-moteurs de communication indépendants et interchangeables ;
3. de plugins de profils d'équipements qui déclarent les données à collecter et interprètent les réponses ;
4. d'une couche de normalisation et de synchronisation vers les fiches Gestion des équipements et le Monitoring.

**Périmètre immédiat : SNMPv3 exclusivement**, avec profils `generic_snmp` et `synology_dsm`. Prévoir des interfaces extensibles pour SSH, WinRM et REST, **sans implémenter** ces protocoles à ce stade.

## Démarrage : v0.1, intégration directe
- Examiner **uniquement les points d'intégration utiles** dans le code actuel (fiches et identifiants des équipements, APIs, tâches/planification, stockage, coffre-fort, autorisations et tests). Il ne s'agit pas d'un nouvel audit du projet.
- Présenter brièvement les composants existants réutilisés, les fichiers à créer ou modifier, les impacts et les risques.
- **Implémenter la v0.1**, incluant le squelette intégré au projet, les contrats/interfaces entre orchestrateur, adaptateurs et plugins, l'enregistrement des composants et des tests unitaires de base ; ne pas ajouter de collecte réelle avant la v0.2.
- Ne pas lancer automatiquement une migration destructive, un changement de configuration d'équipement ou un déploiement en production.
- Fournir les tests et le compte rendu, puis **attendre validation avant v0.2**.

## Architecture et contrats impératifs
- L'orchestrateur est indépendant des modules Gestion des équipements et Monitoring ; ces deux modules utilisent un **référentiel d'équipements unique** (`device_id` existant).
- Les sous-moteurs gèrent seulement le protocole et les opérations réseau. SNMP prend en charge GET, WALK et BULK selon les capacités de l'agent ; **aucun SET**.
- Un plugin déclare ses capacités et ses besoins (OID, opérations, fréquence), identifie son équipement et normalise les réponses. Il ne détient ni mots de passe, ni accès direct en écriture à la base et n'implémente pas la pile réseau.
- La découverte de base identifie d'abord l'équipement (OID standards), puis le plugin peut demander des OID spécifiques au constructeur.
- Les réponses normalisées utilisent des clés fonctionnelles stables, indépendantes des noms de colonnes Itops. Un mapping central relie ces clés aux champs existants.
- Préserver les données administratives/manuelles ; modes de synchronisation par champ : automatique, si vide, manuel uniquement. Prévisualiser les changements avant la première association/synchronisation et enregistrer leur provenance.
- La collecte enrichit les fiches existantes sans en créer de doublons ; en cas de doute sur l'identité, demander confirmation avant rattachement.
- Les mesures dynamiques sont horodatées ; distinguer état actuel, dernier état connu, échec de collecte et données périmées (*stale*).
- Un équipement peut utiliser plusieurs protocoles à terme ; aucune dépendance directe d'un plugin à la structure des tables du module Monitoring.

## Sécurité et exploitation
- SNMPv3 **authPriv**, SHA/AES conformément aux possibilités du Synology de test ; lecture seule, ciblage d'IP explicitement autorisées, limitation du débit et des connexions simultanées.
- Identifiants stockés dans le coffre-fort Itops existant et récupérés uniquement lors de l'exécution ; ne jamais les enregistrer en clair, les exposer dans une réponse API ou les journaliser.
- Ne pas déclencher de scan de sous-réseau non autorisé ; ne jamais utiliser SNMP SET.
- Réutiliser RBAC, journalisation, migrations réversibles et framework de tests déjà présents.
- Prévoir délais d'expiration, réessais limités et différenciation des erreurs (réseau, authentification, OID absent, format inattendu).
- Les exemples de tests/fixtures ne contiennent ni véritables secrets ni numéros de série réels.

## Jalons — une seule version à la fois
| Version | Travail attendu | Validation indispensable |
|---|---|---|
| **v0.1** | Architecture modulaire **intégrée au code existant**, contrats, registre de plugins/adaptateurs, tests de base | Intégration propre, tests réussis, sans régression |
| **v0.2** | Sous-moteur SNMPv3 GET / WALK / BULK, gestion `authPriv`, erreurs et tests | Requêtes en lecture seule réussies sur NAS de test |
| **v0.3** | Plugins `generic_snmp` et `synology_dsm`, sélection du profil, OID et normalisation | Modèle, DSM, disques, volumes et SMART interprétés à partir de fixtures et du NAS |
| **v0.4** | Mapping centralisé et synchronisation des fiches Itops existantes, provenance, prévisualisation, règles de champs | Pas de doublon ni écrasement de champ protégé, synchronisation idempotente |
| **v0.5** | Découverte et assistant de rattachement/création de nouveaux équipements | Identification, rapprochement et validation humaine fonctionnels |
| **v0.6** | Interface Itops de configuration des collectes, profils, tests et états | Parcours utilisateur complet avec RBAC |
| **v0.7** | Planification, historique, métriques et intégration Monitoring | Collectes périodiques, données horodatées, état *stale*, alertes prévues |
| **v1.0** | Stabilisation, tests de recette, documentation et procédure de retour arrière | Recette fonctionnelle/sécurité validée avant production |

## Rapport obligatoire en fin de jalon
Indiquer : fichiers créés/modifiés ; réutilisation des composants Itops ; changements de schéma éventuels ; tests exécutés et résultats ; limites connues ; risques ; procédure de retour arrière ; démonstration du résultat attendu ; points nécessitant une décision. **S'arrêter après chaque version et demander sa validation.**

## Interdictions
Pas de réécriture de l'architecture Itops, pas d'audit général inutile, pas de SNMP SET, pas de modification d'équipement, pas de suppression/réinitialisation de données, pas de secret en clair, pas de déploiement automatique en production et pas de dépendance SaaS obligatoire.
