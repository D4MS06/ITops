# Spécification technique — Éditeur no-code de services dynamiques

## 1. Contexte du projet

L’application est une application web ITops centralisée.  
Elle repose sur une architecture web unique avec :

- un backend `FastAPI` ;
- une base de données `MariaDB` ;
- un frontend servi depuis `monitoring/web` ;
- un portail général `portal.html` / `portal.js` ;
- un module monitoring spécialisé `index.html` / `app.js` ;
- des fichiers JavaScript partagés `shared_*.js` ;
- des couches Python structurées dans `monitoring/api`, `monitoring/services`, `monitoring/repositories`, `monitoring/storage`, `monitoring/shared`.

La règle directrice du projet est :

> Centraliser au niveau portail/shared, faire hériter les modules, spécialiser uniquement quand le besoin métier l’impose.

L’ancien contexte desktop/Tkinter ne doit plus guider les choix d’architecture.  
Toute nouvelle fonctionnalité doit respecter l’architecture web centralisée, mutualisée et extensible.

---

## 2. Objectif général

Développer un éditeur no-code permettant de créer des services dynamiques sans écrire de code.

Un service dynamique représente un objet métier configurable par l’utilisateur, par exemple :

- Radars pédagogiques ;
- Imprimantes ;
- Caméras ;
- Bornes d’appel d’urgence ;
- Armoires réseau ;
- Switchs ;
- Serveurs ;
- Licences ;
- Contrats ;
- Défibrillateurs.

L’utilisateur doit pouvoir :

- créer un service ;
- définir ses champs ;
- importer des données ;
- créer des relations avec d’autres services ;
- activer des fonctionnalités transversales appelées `capabilities` ;
- afficher les fiches dans le portail ;
- générer automatiquement des vues simples ;
- exploiter les services sans développement spécifique.

---

## 3. Vocabulaire fonctionnel

### 3.1 Service dynamique

Un service dynamique est un module métier configurable.

Exemple :

```text
Service : Radars pédagogiques
Champs : Nom, Adresse, Latitude, Longitude, État, Prestataire, Numéro de série
Fonctionnalités : suivi d’intervention, rapports, affichage sur carte
```

### 3.2 Champ dynamique

Un champ dynamique décrit une information portée par une fiche.

Types de champs à prévoir en priorité :

- texte court ;
- texte long ;
- nombre ;
- date ;
- booléen ;
- liste déroulante ;
- adresse IP ;
- adresse MAC ;
- email ;
- URL ;
- fichier ;
- latitude ;
- longitude ;
- relation vers un autre service.

### 3.3 Fiche dynamique

Une fiche dynamique est une ligne de données appartenant à un service.

Exemple :

```text
Service : Radars pédagogiques
Fiche : Radar RD6007 - Avenue des Rives
```

### 3.4 Relation

Une relation lie deux services dynamiques.

Les trois types de relations à proposer à l’utilisateur sont :

1. **Lien simple**  
   Exemple : une imprimante appartient à un service.

2. **Lien multiple**  
   Exemple : un serveur héberge plusieurs applications.

3. **Lien multiple avec informations complémentaires**  
   Exemple : plusieurs utilisateurs peuvent utiliser plusieurs imprimantes, avec un code personnel différent par imprimante.

### 3.5 Capability

Une capability est une fonctionnalité transversale activable sur un service dynamique.

Exemples de capabilities :

- `history` : historique détaillé ;
- `interventions` : suivi d’intervention ;
- `reports` : génération de rapports ;
- `attachments` : pièces jointes ;
- `map_display` : affichage sur carte ;
- `notifications` : notifications ;
- `exports` : exports.

Nom affiché dans l’interface :

```text
Fonctionnalités du service
```

Nom technique conseillé :

```text
capabilities
```

---

## 4. Principe général de l’éditeur no-code

L’éditeur doit fonctionner sous forme d’assistant clair :

```text
Étape 1 — Créer le service
Étape 2 — Ajouter les champs
Étape 3 — Définir les relations
Étape 4 — Activer les fonctionnalités
Étape 5 — Configurer les vues
Étape 6 — Importer les données
Étape 7 — Prévisualiser
Étape 8 — Publier dans le portail
```

L’utilisateur ne doit pas voir de vocabulaire technique SQL.

À éviter dans l’interface :

- table pivot ;
- foreign key ;
- cardinalité ;
- relation N-N ;
- schéma EAV ;
- clé étrangère.

À utiliser à la place :

- lien simple ;
- lien multiple ;
- information du lien ;
- fiche liée ;
- service lié ;
- fonctionnalités du service.

---

## 5. Exemple métier 1 — Gestion des imprimantes

### 5.1 Service

```text
Nom du service : Imprimantes
Nom au singulier : Imprimante
Description : Gestion du parc des imprimantes
Icône : imprimante
```

### 5.2 Champs

```text
Nom
Adresse IP
Modèle
Numéro de série
Localisation
État
```

### 5.3 Relations

```text
Imprimante → Service interne
Type : lien simple

Imprimantes ↔ Utilisateurs
Type : lien multiple avec informations complémentaires
```

### 5.4 Informations du lien utilisateur / imprimante

```text
Code personnel
Droit couleur
Droit scanner
Quota
Commentaire
```

### 5.5 Résultat attendu sur une fiche utilisateur

```text
Imprimantes associées

| Imprimante       | Code personnel | Couleur | Scanner |
|------------------|----------------|---------|---------|
| Copieur RH       | 1234           | Oui     | Oui     |
| Copieur Accueil  | 7788           | Non     | Oui     |
```

### 5.6 Résultat attendu sur une fiche imprimante

```text
Utilisateurs autorisés

| Utilisateur   | Code personnel | Couleur | Scanner |
|---------------|----------------|---------|---------|
| Jean Dupont   | 1234           | Oui     | Oui     |
| Marie Martin  | 4567           | Oui     | Non     |
```

Le code personnel appartient au lien entre l’utilisateur et l’imprimante.  
Il ne doit pas être stocké uniquement sur l’utilisateur ni uniquement sur l’imprimante.

---

## 6. Exemple métier 2 — Radars pédagogiques

### 6.1 Service

```text
Nom du service : Radars pédagogiques
Description : Gestion des radars pédagogiques et des interventions prestataires
```

### 6.2 Champs

```text
Nom
Adresse
Sens de circulation
Latitude
Longitude
Adresse IP
Numéro de série
État
Prestataire
Date d’installation
Commentaire
```

### 6.3 Capabilities activées

```text
[x] Historique détaillé
[x] Suivi d’intervention
[x] Génération de rapports
[x] Pièces jointes
[x] Affichage sur carte
```

### 6.4 Onglets générés sur la fiche radar

```text
Informations
Interventions
Documents
Rapports
Carte
Historique
```

### 6.5 Actions disponibles

```text
Ajouter une intervention
Générer un rapport
Ajouter une pièce jointe
Voir sur la carte
Exporter la fiche
```

---

## 7. Différence entre historique détaillé et suivi d’intervention

### 7.1 Historique détaillé

L’historique détaillé est un journal automatique.

Il répond à la question :

```text
Qu’est-ce qui a changé sur cette fiche ?
```

Exemples :

```text
Dams a modifié le champ État.
Ancienne valeur : En panne
Nouvelle valeur : Fonctionnel

Dams a ajouté une pièce jointe.
Fichier : photo_radar.jpg

Dams a créé une intervention.
Objet : remplacement alimentation radar
```

### 7.2 Suivi d’intervention

Le suivi d’intervention est un dossier métier.

Il répond aux questions :

```text
Qui doit intervenir ?
Pourquoi ?
Quand ?
Quel est le statut ?
Quel est le compte rendu ?
Y a-t-il un devis, une photo ou une pièce jointe ?
```

Exemple :

```text
Intervention n°2026-014
Objet : Radar ne remonte plus les données
Prestataire : SNEF
Date de demande : 08/06/2026
Date prévue : 12/06/2026
Statut : En attente prestataire
Compte rendu : En attente
```

### 7.3 Règle

Le suivi d’intervention est une action métier.  
L’historique détaillé trace automatiquement les changements liés à cette action.

---

## 8. Capability — Suivi d’intervention

### 8.1 Objectif

Permettre à n’importe quel service dynamique de suivre des interventions liées à ses fiches.

Exemples de services concernés :

- radars pédagogiques ;
- caméras ;
- imprimantes ;
- bornes d’appel d’urgence ;
- armoires réseau ;
- serveurs ;
- switchs.

### 8.2 Données minimales d’une intervention

```text
Service concerné
Fiche concernée
Objet
Type d’intervention
Statut
Prestataire
Date de demande
Date prévue
Date réalisée
Description
Compte rendu
Pièces jointes
Agent référent
```

### 8.3 Statuts conseillés

```text
Brouillon
Demandée
En attente prestataire
Planifiée
En cours
Terminée
Annulée
À reprogrammer
```

### 8.4 Types d’intervention conseillés

```text
Installation
Maintenance
Dépannage
Contrôle
Remplacement
Mise à jour
Autre
```

### 8.5 Interface utilisateur

Quand la capability `interventions` est activée :

- chaque fiche du service obtient un onglet `Interventions` ;
- un bouton `Ajouter une intervention` est disponible ;
- les interventions peuvent être filtrées par statut, prestataire, date et type.

---

## 9. Capability — Génération de rapports

### 9.1 Objectif

Permettre à plusieurs services dynamiques de générer automatiquement des rapports à partir :

- des champs de la fiche ;
- des relations ;
- des interventions ;
- des pièces jointes ;
- de l’historique ;
- d’un modèle de rapport.

### 9.2 Types de rapports à prévoir

```text
Rapport complet de fiche
Rapport d’intervention
Rapport de synthèse mensuelle
Rapport annuel
Rapport personnalisé par service
```

### 9.3 Exemple de rapport radar

```text
Rapport automatique - Radar pédagogique RD6007

1. Informations générales
- Adresse
- Numéro de série
- État actuel
- Prestataire

2. Interventions
- Date
- Type
- Statut
- Compte rendu

3. Pièces jointes
- Photos
- Devis
- Documents associés

4. Conclusion
- Dernière intervention
- Problèmes ouverts
- Actions à prévoir
```

### 9.4 Interface utilisateur

Quand la capability `reports` est activée :

- chaque fiche obtient un onglet `Rapports` ;
- un bouton `Générer un rapport` est disponible ;
- les modèles disponibles sont configurables dans l’éditeur.

---

## 10. Capability — Affichage sur carte

### 10.1 Objectif

Permettre à certains services dynamiques d’afficher leurs fiches sur une carte à partir de coordonnées GPS.

Exemples :

- radars pédagogiques ;
- caméras extérieures ;
- bornes d’appel d’urgence ;
- armoires réseau ;
- équipements Wi-Fi ;
- défibrillateurs ;
- panneaux lumineux.

### 10.2 Configuration dans l’éditeur no-code

Quand l’utilisateur active `map_display`, afficher une configuration simple :

```text
Champ latitude : [Latitude]
Champ longitude : [Longitude]
Champ utilisé comme titre : [Nom]
Champ utilisé comme description : [Adresse]
Champ utilisé comme état : [État]
Icône : [Radar pédagogique]
Afficher ce service sur la carte globale : Oui / Non
```

### 10.3 Carte dans une fiche

Sur une fiche précise, afficher uniquement la position de l’objet concerné.

```text
Fiche Radar pédagogique
└── Onglet Carte
    └── Position GPS du radar
```

### 10.4 Carte globale multi-services

Créer une page globale :

```text
Carte des équipements
```

Elle doit permettre d’afficher ou masquer les services :

```text
[x] Radars pédagogiques
[x] Caméras
[ ] Bornes d’appel d’urgence
[ ] Armoires réseau
```

Elle doit aussi permettre de filtrer par état :

```text
[x] Fonctionnel
[x] En panne
[x] En maintenance
[ ] Hors service
```

### 10.5 Popup de carte

Au clic sur un point :

```text
Radar RD6007
Avenue des Rives
État : Fonctionnel

[Ouvrir la fiche]
[Voir les interventions]
[Ajouter une intervention]
[Générer un rapport]
```

Les boutons doivent être affichés uniquement si les capabilities correspondantes sont activées.

### 10.6 Bibliothèque conseillée

Utiliser `Leaflet` pour la carte.

Attention :

- si l’application doit fonctionner sans Internet, prévoir une stratégie de tuiles locales ;
- sinon, utiliser OpenStreetMap ou une source compatible ;
- ne pas intégrer de dépendance lourde inutilement.

---

## 11. Modèle de données recommandé

### 11.1 Services dynamiques

Table conseillée :

```text
dynamic_services
```

Rôle :

```text
Définir les services créés par l’utilisateur.
```

Champs possibles :

```text
id
slug
label
singular_label
description
icon
is_published
created_at
updated_at
```

### 11.2 Champs dynamiques

Table conseillée :

```text
dynamic_fields
```

Champs possibles :

```text
id
service_id
field_key
label
field_type
is_required
is_unique
is_displayed_in_list
sort_order
options_json
created_at
updated_at
```

### 11.3 Fiches dynamiques

Table conseillée :

```text
dynamic_records
```

Champs possibles :

```text
id
service_id
display_label
status
created_at
updated_at
created_by
updated_by
```

### 11.4 Valeurs des fiches

Table conseillée :

```text
dynamic_record_values
```

Champs possibles :

```text
id
record_id
field_id
value_text
value_number
value_date
value_bool
value_json
created_at
updated_at
```

### 11.5 Relations entre services

Table conseillée :

```text
dynamic_relations
```

Champs possibles :

```text
id
source_service_id
target_service_id
relation_type
label
reverse_label
is_enriched
created_at
updated_at
```

Types possibles :

```text
single_link
multi_link
many_to_many_enriched
```

### 11.6 Champs propres aux relations

Table conseillée :

```text
dynamic_relation_fields
```

Champs possibles :

```text
id
relation_id
field_key
label
field_type
is_required
sort_order
options_json
created_at
updated_at
```

### 11.7 Liens entre fiches

Table conseillée :

```text
dynamic_relation_records
```

Champs possibles :

```text
id
relation_id
source_record_id
target_record_id
created_at
updated_at
created_by
```

### 11.8 Valeurs propres aux liens

Table conseillée :

```text
dynamic_relation_values
```

Champs possibles :

```text
id
relation_record_id
relation_field_id
value_text
value_number
value_date
value_bool
value_json
created_at
updated_at
```

### 11.9 Capabilities activées par service

Table conseillée :

```text
dynamic_service_capabilities
```

Champs possibles :

```text
id
service_id
capability_key
enabled
config_json
created_at
updated_at
```

Exemple :

```json
{
  "service_id": "radars",
  "capability_key": "map_display",
  "enabled": true,
  "config_json": {
    "latitude_field": "latitude",
    "longitude_field": "longitude",
    "title_field": "nom",
    "subtitle_field": "adresse",
    "status_field": "etat",
    "icon": "radar"
  }
}
```

### 11.10 Interventions

Table conseillée :

```text
interventions
```

Champs possibles :

```text
id
target_service_id
target_record_id
title
intervention_type
status
provider
request_date
planned_date
completed_date
description
report_text
created_by
updated_by
created_at
updated_at
```

### 11.11 Rapport généré

Table conseillée :

```text
generated_reports
```

Champs possibles :

```text
id
target_service_id
target_record_id
template_id
title
file_path
file_type
generated_by
generated_at
metadata_json
```

### 11.12 Modèles de rapports

Table conseillée :

```text
report_templates
```

Champs possibles :

```text
id
service_id
label
template_type
config_json
is_default
created_at
updated_at
```

### 11.13 Historique détaillé

Table conseillée :

```text
audit_logs
```

Champs possibles :

```text
id
target_type
target_service_id
target_record_id
action
field_key
old_value
new_value
user_id
created_at
metadata_json
```

---

## 12. API à prévoir

### 12.1 Services dynamiques

```text
GET    /api/dynamic-services
POST   /api/dynamic-services
GET    /api/dynamic-services/{service_id}
PUT    /api/dynamic-services/{service_id}
DELETE /api/dynamic-services/{service_id}
```

### 12.2 Champs

```text
GET    /api/dynamic-services/{service_id}/fields
POST   /api/dynamic-services/{service_id}/fields
PUT    /api/dynamic-services/{service_id}/fields/{field_id}
DELETE /api/dynamic-services/{service_id}/fields/{field_id}
```

### 12.3 Fiches

```text
GET    /api/dynamic-services/{service_id}/records
POST   /api/dynamic-services/{service_id}/records
GET    /api/dynamic-services/{service_id}/records/{record_id}
PUT    /api/dynamic-services/{service_id}/records/{record_id}
DELETE /api/dynamic-services/{service_id}/records/{record_id}
```

### 12.4 Relations

```text
GET    /api/dynamic-services/{service_id}/relations
POST   /api/dynamic-services/{service_id}/relations
PUT    /api/dynamic-relations/{relation_id}
DELETE /api/dynamic-relations/{relation_id}
```

### 12.5 Capabilities

```text
GET /api/dynamic-services/{service_id}/capabilities
PUT /api/dynamic-services/{service_id}/capabilities
```

### 12.6 Interventions

```text
GET  /api/interventions?service_id={service_id}&record_id={record_id}
POST /api/interventions
GET  /api/interventions/{intervention_id}
PUT  /api/interventions/{intervention_id}
```

### 12.7 Rapports

```text
GET  /api/reports/templates?service_id={service_id}
POST /api/reports/generate
GET  /api/reports/generated?service_id={service_id}&record_id={record_id}
```

### 12.8 Carte

```text
GET /api/map/layers
GET /api/map/items?services=radars,cameras
```

Exemple de retour pour `/api/map/layers` :

```json
[
  {
    "service_id": "radars",
    "label": "Radars pédagogiques",
    "enabled": true,
    "icon": "radar"
  },
  {
    "service_id": "cameras",
    "label": "Caméras",
    "enabled": true,
    "icon": "camera"
  }
]
```

Exemple de retour pour `/api/map/items` :

```json
[
  {
    "service_id": "radars",
    "record_id": 15,
    "title": "Radar RD6007",
    "subtitle": "Avenue des Rives",
    "latitude": 43.657210,
    "longitude": 7.126840,
    "status": "Fonctionnel",
    "icon": "radar",
    "capabilities": ["interventions", "reports", "map_display"]
  }
]
```

---

## 13. Architecture de fichiers recommandée

Respecter la logique existante du projet.

```text
monitoring/
├── api/
│   ├── dynamic_services_api.py
│   ├── dynamic_relations_api.py
│   ├── dynamic_capabilities_api.py
│   ├── interventions_api.py
│   ├── reports_api.py
│   └── dynamic_map_api.py
│
├── services/
│   ├── dynamic_service_manager.py
│   ├── dynamic_schema_service.py
│   ├── dynamic_record_service.py
│   ├── dynamic_relation_service.py
│   ├── dynamic_capability_service.py
│   ├── dynamic_import_service.py
│   ├── intervention_service.py
│   ├── report_service.py
│   ├── document_generation_service.py
│   ├── dynamic_map_service.py
│   └── audit_log_service.py
│
├── repositories/
│   ├── dynamic_service_repository.py
│   ├── dynamic_field_repository.py
│   ├── dynamic_record_repository.py
│   ├── dynamic_relation_repository.py
│   ├── dynamic_capability_repository.py
│   ├── intervention_repository.py
│   ├── report_template_repository.py
│   ├── generated_report_repository.py
│   ├── dynamic_map_repository.py
│   └── audit_log_repository.py
│
├── storage/
│   ├── dynamic_schema_bootstrap.py
│   └── dynamic_schema_migrations.py
│
├── shared/
│   ├── dynamic_types.py
│   ├── dynamic_permissions.py
│   └── dynamic_validation.py
│
├── web/
│   ├── dynamic_service_editor.html
│   ├── dynamic_service_editor.js
│   ├── dynamic_runtime.html
│   ├── dynamic_runtime.js
│   ├── dynamic_map.html
│   ├── dynamic_map.js
│   ├── shared_dynamic_forms.js
│   ├── shared_dynamic_tables.js
│   ├── shared_dynamic_relations.js
│   ├── shared_dynamic_capabilities.js
│   ├── shared_interventions.js
│   ├── shared_reports.js
│   └── shared_map.js
│
└── tests/
    ├── test_dynamic_schema_service.py
    ├── test_dynamic_record_service.py
    ├── test_dynamic_relations.py
    ├── test_dynamic_capabilities.py
    ├── test_dynamic_import.py
    ├── test_intervention_service.py
    ├── test_report_service.py
    ├── test_dynamic_map_service.py
    └── test_audit_log_service.py
```

---

## 14. Règles de développement à respecter

### 14.1 Backend Python

- Python 3.11 ou supérieur.
- Respect PEP 8.
- Docstrings style Google.
- Journalisation avec `logging`.
- Exceptions contrôlées avec `try/except`.
- Ne jamais exposer de secrets.
- Utiliser `os.getenv()` pour toute configuration sensible.
- Les routes API doivent rester minces.
- La logique métier doit être dans `monitoring/services`.
- L’accès aux données doit être dans `monitoring/repositories`.
- La persistance bas niveau et le bootstrap SQL doivent être dans `monitoring/storage`.

### 14.2 Frontend

- Ne pas dupliquer la logique entre `portal.js`, `app.js` et `setup.js`.
- Toute logique commune doit aller dans `shared_*.js`.
- Le CSS global doit rester dans `app.css`.
- Les composants réutilisables doivent être centralisés.
- Les appels API communs doivent passer par `shared_api.js`.
- Les imports doivent réutiliser `shared_import.js`.
- Les téléchargements doivent réutiliser `shared_download.js`.
- Les comportements UI génériques doivent être dans `shared_ui.js`.
- Les menus doivent réutiliser `shared_menu.js`.

### 14.3 UI

- L’interface doit être compréhensible par un utilisateur non développeur.
- Éviter le vocabulaire SQL.
- Toujours afficher un résumé lisible avant validation.
- Prévoir une prévisualisation avant publication.
- Éviter les écrans trop chargés.
- Préférer des assistants étape par étape.

### 14.4 Tests

Prévoir au minimum :

- tests de création de service dynamique ;
- tests de création de champs ;
- tests de validation de données ;
- tests de relations simples ;
- tests de relations enrichies ;
- tests d’activation de capabilities ;
- tests de création d’intervention ;
- tests de génération de rapport ;
- tests de récupération des points cartographiques ;
- tests d’historique détaillé.

---

## 15. Feuille de route de développement

### Phase 1 — Socle des services dynamiques

Objectif : créer le moteur minimal.

À développer :

- tables `dynamic_services`, `dynamic_fields`, `dynamic_records`, `dynamic_record_values` ;
- repositories associés ;
- services Python associés ;
- API de création/modification/suppression ;
- écran simple de création d’un service ;
- écran de création des champs ;
- affichage automatique liste + fiche ;
- tests unitaires de base.

Critère de validation :

```text
On peut créer un service "Radars pédagogiques", ajouter des champs, créer une fiche et l’afficher.
```

---

### Phase 2 — Import CSV / Excel

Objectif : permettre d’alimenter un service dynamique depuis un fichier.

À développer :

- import CSV ;
- import Excel ;
- écran de correspondance colonnes/fichiers ;
- validation des champs obligatoires ;
- rapport d’import ;
- gestion des erreurs de lignes ;
- tests d’import.

Critère de validation :

```text
On peut importer une liste de radars ou d’imprimantes et vérifier les fiches créées.
```

---

### Phase 3 — Relations entre services

Objectif : permettre de relier les services dynamiques.

À développer :

- tables `dynamic_relations`, `dynamic_relation_fields`, `dynamic_relation_records`, `dynamic_relation_values` ;
- relation simple ;
- relation multiple ;
- relation multiple enrichie ;
- interface no-code de création de relation ;
- affichage des fiches liées ;
- affichage inverse automatique ;
- tests de relations.

Critère de validation :

```text
On peut lier des utilisateurs à plusieurs imprimantes avec un code personnel différent par imprimante.
```

---

### Phase 4 — Capabilities

Objectif : activer des fonctionnalités transversales par service.

À développer :

- table `dynamic_service_capabilities` ;
- service `dynamic_capability_service.py` ;
- API capabilities ;
- interface `Fonctionnalités du service` ;
- activation/désactivation de capability ;
- configuration JSON par capability ;
- affichage conditionnel des onglets et boutons.

Critère de validation :

```text
On peut activer ou désactiver les capabilities d’un service depuis l’éditeur.
```

---

### Phase 5 — Historique détaillé

Objectif : tracer automatiquement les changements.

À développer :

- table `audit_logs` ;
- service `audit_log_service.py` ;
- repository associé ;
- journalisation création/modification/suppression ;
- affichage onglet Historique ;
- tests.

Critère de validation :

```text
Quand une fiche est modifiée, l’ancienne et la nouvelle valeur sont visibles dans l’historique.
```

---

### Phase 6 — Suivi d’intervention

Objectif : ajouter une gestion d’intervention réutilisable.

À développer :

- table `interventions` ;
- repository intervention ;
- service intervention ;
- API intervention ;
- composant frontend `shared_interventions.js` ;
- onglet Interventions ;
- formulaire d’ajout/modification ;
- filtres statut/type/prestataire ;
- lien avec l’historique ;
- tests.

Critère de validation :

```text
Un service "Radars pédagogiques" peut avoir des interventions rattachées à chaque radar.
```

---

### Phase 7 — Pièces jointes

Objectif : rattacher des fichiers à une fiche ou à une intervention.

À développer :

- capability `attachments` ;
- stockage fichier sécurisé ;
- métadonnées des fichiers ;
- upload ;
- téléchargement ;
- suppression contrôlée ;
- affichage dans fiche et intervention ;
- tests.

Critère de validation :

```text
On peut joindre un devis ou une photo à une intervention radar.
```

---

### Phase 8 — Génération de rapports

Objectif : générer des rapports automatiquement.

À développer :

- tables `report_templates` et `generated_reports` ;
- service `report_service.py` ;
- service `document_generation_service.py` ;
- modèles standards ;
- modèle rapport complet de fiche ;
- modèle rapport d’intervention ;
- génération HTML dans un premier temps ;
- export PDF dans un second temps ;
- historique des rapports générés ;
- tests.

Critère de validation :

```text
On peut générer un rapport complet pour un radar avec ses informations et ses interventions.
```

---

### Phase 9 — Affichage sur carte

Objectif : afficher des fiches dynamiques localisées sur une carte.

À développer :

- capability `map_display` ;
- configuration latitude/longitude/titre/description/état/icône ;
- service `dynamic_map_service.py` ;
- API `/api/map/layers` ;
- API `/api/map/items` ;
- page `dynamic_map.html` ;
- composant `shared_map.js` ;
- filtres par service ;
- filtres par état ;
- popup avec actions conditionnelles ;
- tests.

Critère de validation :

```text
On peut afficher les radars et caméras sur une carte globale, puis masquer ou afficher chaque service.
```

---

### Phase 10 — Publication dans le portail

Objectif : rendre les services dynamiques accessibles depuis le portail général.

À développer :

- affichage des services publiés dans `portal.html` / `portal.js` ;
- droits d’accès ;
- ordre d’affichage ;
- icônes ;
- ouverture du runtime dynamique ;
- masquage des services non publiés.

Critère de validation :

```text
Un service dynamique publié apparaît dans le portail et peut être utilisé comme un module classique.
```

---

### Phase 11 — Permissions et sécurité

Objectif : contrôler qui peut créer, modifier, importer, supprimer et consulter.

À développer :

- permissions par service ;
- permissions par capability ;
- contrôle côté API ;
- contrôle côté UI ;
- interdiction de suppression destructive sans confirmation ;
- audit des actions sensibles ;
- tests de permissions.

Critère de validation :

```text
Un utilisateur sans droit d’administration ne peut pas modifier la structure d’un service dynamique.
```

---

### Phase 12 — Stabilisation et ergonomie

Objectif : rendre l’outil fiable pour un utilisateur non développeur.

À développer :

- prévisualisation avant publication ;
- messages d’erreur lisibles ;
- assistants étape par étape ;
- modèles de services prêts à l’emploi ;
- duplication d’un service existant ;
- export/import de modèle de service ;
- documentation utilisateur.

Critère de validation :

```text
Un utilisateur peut créer un service simple sans connaître la base de données ni le code.
```

---

## 16. Priorité de développement recommandée

Ordre strict conseillé :

```text
1. Socle dynamique : services, champs, fiches
2. Import CSV / Excel
3. Relations simples et enrichies
4. Capabilities
5. Historique détaillé
6. Suivi d’intervention
7. Pièces jointes
8. Génération de rapports
9. Affichage sur carte
10. Publication portail
11. Permissions
12. Stabilisation ergonomique
```

Ne pas commencer par la carte ou les rapports avant d’avoir un socle dynamique stable.

---

## 17. Règles importantes pour l’agent Codex

Avant toute modification :

1. Identifier si le besoin est transversal ou spécifique.
2. Si le besoin est transversal, modifier d’abord les couches partagées.
3. Ne pas coder une fonctionnalité uniquement dans `app.js` si elle peut servir au portail ou à plusieurs services.
4. Ne pas dupliquer une logique déjà présente dans `shared_*.js`.
5. Garder les API minces.
6. Placer la logique métier dans `monitoring/services`.
7. Placer l’accès données dans `monitoring/repositories`.
8. Ajouter ou adapter les tests.
9. Respecter l’architecture web actuelle.
10. Ne pas réintroduire de logique desktop/Tkinter.

---

## 18. Livrables attendus par phase

Chaque phase doit idéalement produire :

- fichiers Python complets ;
- fichiers JS complets ;
- migrations ou bootstrap SQL ;
- tests unitaires ;
- documentation courte ;
- validation manuelle possible dans PyCharm ;
- absence de duplication inutile ;
- logs exploitables ;
- erreurs compréhensibles côté utilisateur.

---

## 19. Notes d’implémentation

### 19.1 Configuration JSON des capabilities

Chaque capability peut stocker sa configuration dans `config_json`.

Exemple pour la carte :

```json
{
  "latitude_field": "latitude",
  "longitude_field": "longitude",
  "title_field": "nom",
  "subtitle_field": "adresse",
  "status_field": "etat",
  "icon": "radar",
  "show_on_global_map": true
}
```

Exemple pour les rapports :

```json
{
  "enabled_templates": [
    "full_record_report",
    "intervention_report"
  ],
  "include_interventions": true,
  "include_attachments": true,
  "include_history": false
}
```

Exemple pour les interventions :

```json
{
  "allowed_types": [
    "Installation",
    "Maintenance",
    "Dépannage",
    "Contrôle",
    "Remplacement",
    "Autre"
  ],
  "required_fields": [
    "title",
    "status",
    "provider",
    "request_date"
  ]
}
```

### 19.2 Actions conditionnelles

Les actions affichées dans l’interface doivent dépendre des capabilities activées.

Exemple :

```text
Si interventions activé :
- afficher "Ajouter une intervention"

Si reports activé :
- afficher "Générer un rapport"

Si map_display activé :
- afficher "Voir sur la carte"

Si attachments activé :
- afficher "Ajouter une pièce jointe"
```

---

## 20. Résumé opérationnel

L’éditeur no-code doit permettre de créer des services dynamiques réutilisables, reliés entre eux, enrichis par des capabilities transversales.

Le cœur du système est :

```text
Service dynamique
├── Champs
├── Fiches
├── Relations
└── Capabilities
    ├── Historique détaillé
    ├── Suivi d’intervention
    ├── Génération de rapports
    ├── Pièces jointes
    └── Affichage sur carte
```

La priorité est de construire un socle simple, stable et extensible, puis d’ajouter progressivement les moteurs transversaux.

La règle d’or reste :

> Centraliser au niveau portail/shared, faire hériter les modules, spécialiser uniquement quand le besoin métier l’impose.
