# Moteur de services no-code dynamiques

Document de reference pour developper l'editeur de services dynamiques no-code dans NetworkMonitoringProject.

Derniere mise a jour: 23 juin 2026  
Statut: specification de developpement alignee sur le code existant

## 1. Objectif

Le moteur no-code existe deja. Il permet de definir des services dynamiques, leurs champs, puis de stocker des records dans `custom_service_records.payload_json`.

L'objectif de cette evolution est de rendre ce moteur utilisable comme fonctionnalite majeure, sans casser les donnees ni les endpoints existants:

- ameliorer la recherche et le tri sur les records no-code;
- securiser progressivement les credentials;
- ajouter un audit des actions importantes;
- rendre l'editeur frontend plus maintenable;
- garder la compatibilite avec les tables et routes actuelles.

## 2. Etat actuel confirme

### Projet

Racine locale:

```text
C:\Users\damien\PycharmProjects\pythonProject\NetworkMonitoringProject
```

Fichiers principaux:

- `monitoring/api/app.py`: routes FastAPI.
- `monitoring/storage/mariadb_bootstrap.py`: creation et evolution idempotente du schema MariaDB.
- `monitoring/storage/mariadb_manager.py`: operations MariaDB haut niveau.
- `monitoring/services/custom_service_schema.py`: validation des definitions et valeurs no-code.
- `monitoring/services/custom_service_records_tabular.py`: import/export records no-code.
- `monitoring/services/tabular_io.py`: lecture CSV, TSV, TXT, XLSX.
- `monitoring/web/portal.js`: UI principale et logique no-code actuelle.
- `monitoring/web/shared_api.js`: wrapper API avec token Bearer.
- `monitoring/web/shared_ui.js`: `SharedTreeView`.

### Versions locales observees

- Python: `3.12.10`
- MariaDB: `12.2.2-MariaDB`
- FastAPI via `requirements.txt`
- Acces DB via `PyMySQL`

### Authentification

L'application n'utilise pas JWT. Elle utilise des tokens de session opaques envoyes avec:

```http
Authorization: Bearer <token>
```

Les utilisateurs et droits reposent sur:

- `auth_users(subject, label, is_active, password_hash, must_change_password)`
- `auth_roles(code, label, is_system, sort_order)`
- `auth_modules(code, label, route_path, is_active, sort_order)`
- `auth_user_roles(subject, role_code)`
- `auth_role_modules(role_code, module_code)`

Les modules generes pour les services no-code suivent le format:

```text
service_<service_code_sanitized>_<sha1_8>
```

## 3. Tables no-code existantes

### `custom_services`

```sql
CREATE TABLE custom_services (
  code VARCHAR(64) PRIMARY KEY,
  label VARCHAR(191) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  credentials_enabled TINYINT(1) NOT NULL DEFAULT 0,
  child_enabled TINYINT(1) NOT NULL DEFAULT 0,
  child_label VARCHAR(191) NOT NULL DEFAULT 'Elements lies',
  sort_order INT NOT NULL DEFAULT 100
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### `custom_service_fields`

```sql
CREATE TABLE custom_service_fields (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  service_code VARCHAR(64) NOT NULL,
  field_key VARCHAR(191) NOT NULL,
  label VARCHAR(191) NOT NULL,
  field_kind VARCHAR(64) NOT NULL,
  required TINYINT(1) NOT NULL DEFAULT 0,
  options TEXT NOT NULL,
  default_value TEXT NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  list_source_kind VARCHAR(16) NOT NULL DEFAULT 'local',
  shared_list_code VARCHAR(64) NOT NULL DEFAULT '',
  UNIQUE KEY uq_custom_service_field (service_code, field_key),
  CONSTRAINT fk_custom_service_fields_code
    FOREIGN KEY (service_code) REFERENCES custom_services(code) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### `custom_service_records`

Important: `id` est un `VARCHAR(191)`, pas un entier.

```sql
CREATE TABLE custom_service_records (
  id VARCHAR(191) PRIMARY KEY,
  service_code VARCHAR(64) NOT NULL,
  payload_json LONGTEXT NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  KEY idx_custom_service_records_service_updated (service_code, updated_at),
  CONSTRAINT fk_custom_service_records_code
    FOREIGN KEY (service_code) REFERENCES custom_services(code) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### `custom_service_children`

```sql
CREATE TABLE custom_service_children (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  record_id VARCHAR(191) NOT NULL,
  child_name VARCHAR(255) NOT NULL,
  child_code VARCHAR(255) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  CONSTRAINT fk_custom_service_children_record
    FOREIGN KEY (record_id) REFERENCES custom_service_records(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### `shared_lists` et `shared_list_items`

Ces tables existent deja et doivent etre reutilisees pour les champs `list` avec `list_source_kind = 'shared'`.

## 4. Principe d'architecture retenu

Le JSON reste le stockage canonique des records:

```text
custom_service_records.payload_json
```

La v1 n'essaie pas de convertir chaque champ dynamique en vraie colonne SQL. Cela evite:

- une table physique par service;
- un modele EAV complet;
- une migration risquee des donnees existantes.

La v1 ajoute plutot des tables auxiliaires:

- une table d'index pour accelerer recherche et affichage;
- une table d'audit;
- plus tard, une table de credentials chiffres.

## 5. Perimetre recommande

### Phase 1: socle stable et index de recherche

Objectif: ameliorer recherche, tri basique et pagination sans changer le contrat historique.

A faire:

- ajouter des colonnes metadata simples sur `custom_services`;
- ajouter des colonnes d'affichage simples sur `custom_service_fields`;
- ajouter `custom_service_record_index`;
- creer un service Python d'indexation;
- remplir l'index a la creation, modification et suppression d'un record;
- ajouter un backfill idempotent pour les records existants;
- etendre `GET /admin/custom-services/{service_code}/records` avec parametres optionnels.

### Phase 2: audit no-code

Objectif: tracer les actions importantes.

A faire:

- ajouter `custom_service_audit_log`;
- logguer create, update, delete, import, export;
- ne jamais stocker de secret dans l'audit;
- ajouter un endpoint de consultation admin.

### Phase 3: credentials securises

Objectif: sortir `device_login` et `device_password` du JSON.

A faire apres stabilisation des phases 1 et 2:

- ajouter une dependance de chiffrement si necessaire;
- definir le stockage et la sauvegarde de la cle maitre;
- ajouter `custom_service_credentials`;
- ajouter endpoints de reveal avec droit dedie;
- exclure les credentials des exports standards;
- migrer les credentials existants uniquement s'il y en a.

### Phase 4: extraction frontend

Objectif: reduire la taille et la complexite de `portal.js`.

A faire:

- creer `monitoring/web/no_code_engine.js`;
- deplacer progressivement les helpers no-code depuis `portal.js`;
- garder `SharedTreeView` dans `shared_ui.js`;
- eviter une rewrite complete en une fois.

### Hors v1

Reporter:

- relations inter-services;
- references vers devices;
- pieces jointes dediees no-code;
- field choices versionnes dans une table separee;
- workflow public non-admin complet;
- webhooks et notifications.

## 6. Evolutions de schema v1

Toutes les evolutions doivent etre idempotentes dans `monitoring/storage/mariadb_bootstrap.py`, avec le pattern deja utilise:

```python
if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="...", column_name="..."):
    cursor.execute("ALTER TABLE ... ADD COLUMN ...")
```

Ne pas utiliser `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` dans le SQL cible, car le code existant utilise deja une compatibilite par introspection `information_schema`.

### 6.1 Colonnes a ajouter sur `custom_services`

```sql
ALTER TABLE custom_services ADD COLUMN icon VARCHAR(64) NOT NULL DEFAULT '';
ALTER TABLE custom_services ADD COLUMN color VARCHAR(32) NOT NULL DEFAULT '';
ALTER TABLE custom_services ADD COLUMN description TEXT NOT NULL;
ALTER TABLE custom_services ADD COLUMN treeview_config LONGTEXT NOT NULL;
ALTER TABLE custom_services ADD COLUMN allow_export TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE custom_services ADD COLUMN allow_import TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE custom_services ADD COLUMN created_at DATETIME NULL;
ALTER TABLE custom_services ADD COLUMN updated_at DATETIME NULL;
```

Notes:

- utiliser des valeurs `NOT NULL DEFAULT ''` pour rester coherent avec le style existant;
- pour `created_at` et `updated_at`, accepter `NULL` au debut pour eviter les problemes sur anciennes lignes, puis backfill possible.

### 6.2 Colonnes a ajouter sur `custom_service_fields`

```sql
ALTER TABLE custom_service_fields ADD COLUMN show_in_list TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE custom_service_fields ADD COLUMN searchable TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE custom_service_fields ADD COLUMN unique_value TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE custom_service_fields ADD COLUMN placeholder VARCHAR(255) NOT NULL DEFAULT '';
ALTER TABLE custom_service_fields ADD COLUMN help_text TEXT NOT NULL;
ALTER TABLE custom_service_fields ADD COLUMN min_value DOUBLE NULL;
ALTER TABLE custom_service_fields ADD COLUMN max_value DOUBLE NULL;
```

Noms recommandes:

- preferer `show_in_list` a `is_visible_in_list`, plus court et coherent avec `show_in_table` deja present cote `device_type_fields`;
- preferer `unique_value` a `is_unique`, pour eviter les ambiguites avec le mot-cle conceptuel SQL.

### 6.3 Table `custom_service_record_index`

Cette table sert a accelerer la recherche globale et l'affichage liste.

```sql
CREATE TABLE IF NOT EXISTS custom_service_record_index (
  record_id VARCHAR(191) NOT NULL,
  service_code VARCHAR(64) NOT NULL,
  label_value VARCHAR(500) NOT NULL DEFAULT '',
  search_blob TEXT NOT NULL,
  indexed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (record_id),
  KEY idx_csri_service_label (service_code, label_value),
  KEY idx_csri_service_indexed (service_code, indexed_at),
  FULLTEXT KEY ft_csri_search_blob (search_blob),
  CONSTRAINT fk_csri_record
    FOREIGN KEY (record_id) REFERENCES custom_service_records(id) ON DELETE CASCADE,
  CONSTRAINT fk_csri_service
    FOREIGN KEY (service_code) REFERENCES custom_services(code) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

Limite volontaire:

- cette table permet une recherche globale performante;
- elle ne permet pas encore de filtrer efficacement par n'importe quel champ dynamique;
- le filtrage avance par champ sera traite en v2 avec une table par champ indexe si necessaire.

### 6.4 Table optionnelle pour index par champ

Ne pas implementer en phase 1 sauf besoin fort de filtre par colonne.

Modele possible:

```sql
CREATE TABLE IF NOT EXISTS custom_service_record_field_index (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  record_id VARCHAR(191) NOT NULL,
  service_code VARCHAR(64) NOT NULL,
  field_key VARCHAR(191) NOT NULL,
  value_text VARCHAR(1024) NOT NULL DEFAULT '',
  value_number DOUBLE NULL,
  value_date DATE NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_csfi_record_field (record_id, field_key),
  KEY idx_csfi_service_field_text (service_code, field_key, value_text),
  KEY idx_csfi_service_field_number (service_code, field_key, value_number),
  KEY idx_csfi_service_field_date (service_code, field_key, value_date),
  CONSTRAINT fk_csfi_record
    FOREIGN KEY (record_id) REFERENCES custom_service_records(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

Cette table est plus puissante mais plus couteuse. Elle doit etre decidee apres tests reels.

### 6.5 Table `custom_service_audit_log`

```sql
CREATE TABLE IF NOT EXISTS custom_service_audit_log (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  service_code VARCHAR(64) NOT NULL,
  record_id VARCHAR(191) NOT NULL DEFAULT '',
  action VARCHAR(64) NOT NULL,
  subject VARCHAR(255) NOT NULL DEFAULT '',
  detail_json LONGTEXT NOT NULL,
  client_ip VARCHAR(45) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_csal_service_created (service_code, created_at),
  KEY idx_csal_record_created (record_id, created_at),
  KEY idx_csal_subject_created (subject, created_at),
  KEY idx_csal_action_created (action, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

Ne pas utiliser `JSON` comme type obligatoire en v1. Le projet utilise deja souvent `LONGTEXT` pour stocker du JSON, ce qui reste plus compatible et coherent.

Actions v1:

- `service_create`
- `service_update`
- `service_delete`
- `record_create`
- `record_update`
- `record_delete`
- `records_import`
- `records_export`
- `credentials_purge`

Actions phase credentials:

- `credential_view`
- `credential_update`
- `credential_delete`
- `credential_export`

## 7. Credentials securises

### Etat actuel

Si `credentials_enabled = 1`, le frontend et l'API utilisent les cles reservees:

```text
device_login
device_password
```

Ces valeurs sont aujourd'hui stockees dans `payload_json`.

### Regle cible

Apres la phase credentials:

- `payload_json` ne doit plus contenir `device_login`;
- `payload_json` ne doit plus contenir `device_password`;
- les exports standards ne doivent pas inclure les credentials;
- la revelation d'un secret doit passer par un endpoint dedie et un droit dedie;
- l'audit doit logguer la revelation sans stocker la valeur.

### Table cible

```sql
CREATE TABLE IF NOT EXISTS custom_service_credentials (
  record_id VARCHAR(191) NOT NULL,
  service_code VARCHAR(64) NOT NULL,
  login_encrypted TEXT NOT NULL,
  password_encrypted TEXT NOT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (record_id),
  KEY idx_csc_service (service_code),
  CONSTRAINT fk_csc_record
    FOREIGN KEY (record_id) REFERENCES custom_service_records(id) ON DELETE CASCADE,
  CONSTRAINT fk_csc_service
    FOREIGN KEY (service_code) REFERENCES custom_services(code) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Choix chiffrement a decider avant implementation

Avant de coder cette phase, documenter:

- dependance choisie (`cryptography` / Fernet ou autre);
- generation de la cle maitre;
- stockage de la cle maitre;
- backup/recovery;
- rotation de cle;
- comportement si la cle est absente ou invalide.

Sans procedure de recovery, ne pas migrer des credentials reels.

## 8. Services Python a creer

Eviter de mettre la logique metier dans `monitoring/api/helpers.py`.

Preferer:

```text
monitoring/services/custom_service_index.py
monitoring/services/custom_service_audit.py
monitoring/services/custom_service_credentials.py
```

### `custom_service_index.py`

Responsabilites:

- construire `label_value`;
- construire `search_blob`;
- exclure `device_login` et `device_password`;
- upsert dans `custom_service_record_index`;
- supprimer l'index d'un record;
- backfill par batch.

Interface recommandee:

```python
def build_record_index_payload(*, service: dict, record: dict) -> dict:
    ...

def upsert_record_index(*, manager, service: dict, record: dict) -> None:
    ...

def delete_record_index(*, manager, record_id: str) -> None:
    ...

def backfill_record_index(*, manager, batch_size: int = 100) -> int:
    ...
```

### `custom_service_audit.py`

Responsabilites:

- normaliser le sujet utilisateur;
- masquer les champs sensibles;
- limiter la taille de `detail_json`;
- inserer une ligne dans `custom_service_audit_log`.

Interface recommandee:

```python
def log_custom_service_event(
    *,
    manager,
    service_code: str,
    action: str,
    subject: str,
    record_id: str = "",
    detail: dict | None = None,
    client_ip: str = "",
) -> None:
    ...
```

En cas d'erreur d'audit, l'action utilisateur ne doit pas echouer en v1. Logger un warning serveur suffit.

## 9. Evolutions API

Contrainte importante: ne pas casser les routes existantes.

### Route existante a etendre

```http
GET /admin/custom-services/{service_code}/records
```

Parametres optionnels:

```text
search       recherche globale dans search_blob
limit        defaut 500 aujourd'hui possible, cible 50 pour mode pagine
offset       defaut 0
sort         champ de tri: label, updated_at, created_at
direction    asc|desc
```

Deux options possibles:

1. garder la reponse liste actuelle si aucun parametre de pagination n'est fourni;
2. creer une route separee paginee:

```http
GET /admin/custom-services/{service_code}/records/query
```

Recommandation: utiliser une route separee pour eviter de casser `portal.js` et les tests existants.

Reponse paginee recommandee:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

### Audit

```http
GET /admin/custom-services/{service_code}/audit-log?limit=100&offset=0&action=&record_id=
```

Acces admin uniquement en v1.

### Credentials phase 3

Endpoints a ajouter seulement apres choix chiffrement:

```http
POST /admin/custom-services/{service_code}/records/{record_id}/credentials/reveal
PUT  /admin/custom-services/{service_code}/records/{record_id}/credentials
DELETE /admin/custom-services/{service_code}/records/{record_id}/credentials
```

Utiliser `POST` pour reveal afin d'eviter une consultation cachee par un lien GET.

## 10. Frontend

### Etat actuel

Le frontend no-code est principalement dans `portal.js`. Il contient deja:

- gestion des services no-code;
- modal d'edition de service;
- import/export champs;
- import/export records;
- edition records;
- treeview records via `SharedTreeView`;
- preference colonnes via `localStorage`.

### Strategie

Ne pas faire une rewrite complete.

Etape 1:

- garder l'UI existante;
- brancher la route paginee/search sur la treeview records;
- conserver `SharedTreeView`.

Etape 2:

- creer `monitoring/web/no_code_engine.js`;
- deplacer les fonctions pures depuis `portal.js`;
- exposer un namespace `window.NMPNoCodeEngine`.

Etape 3:

- extraire un builder de formulaire uniquement si la duplication devient bloquante.

### Preferences colonnes

Aujourd'hui, elles sont dans `localStorage`.

Ne pas ajouter de preferences serveur en v1 sauf besoin multi-poste immediat. Cela evite une table et des endpoints supplementaires.

## 11. Import/export

### Formats existants

Import:

- `.csv`
- `.txt`
- `.tsv`
- `.xlsx`

Non supporte:

- `.xls`

Export:

- CSV avec BOM UTF-8 pour Excel Windows.

### Regles v1

- garder l'import/export existant;
- limiter les imports a `MAX_TABULAR_ROWS = 5000` comme aujourd'hui;
- exclure `device_password` des exports standards des que la phase credentials commence;
- ajouter un test d'export pour verifier l'absence de secrets.

## 12. Migration: ce que cela veut dire ici

Il ne faut pas migrer tout le moteur no-code.

Trois operations distinctes existent:

### 12.1 Migration de schema

Ajouter les nouvelles colonnes et tables via bootstrap idempotent.

Cette operation est obligatoire.

### 12.2 Backfill de l'index

Si `custom_service_records` contient deja des lignes, construire les entrees manquantes dans `custom_service_record_index`.

Cette operation est sans effet si aucun record n'existe.

En local, au moment de l'analyse, il y avait:

- `0` service no-code;
- `0` champ no-code;
- `0` record no-code.

### 12.3 Migration credentials

Uniquement si des records existants contiennent `device_login` ou `device_password` dans `payload_json`.

Ne pas executer tant que:

- le chiffrement n'est pas valide;
- la cle maitre n'est pas sauvegardee;
- un backup DB n'a pas ete fait;
- un test de restauration n'a pas ete fait.

## 13. Ordre de developpement recommande

### Lot 1: schema + index

1. Ajouter tables/colonnes phase 1 dans `mariadb_bootstrap.py`.
2. Ajouter methodes DB dans `mariadb_manager.py` ou repository dedie.
3. Creer `monitoring/services/custom_service_index.py`.
4. Brancher indexation sur create/update/delete records.
5. Ajouter script `scripts/backfill_custom_service_record_index.py`.
6. Ajouter tests d'idempotence bootstrap et backfill.

Critere d'acceptation:

- le bootstrap peut etre relance deux fois sans erreur;
- creer un record cree son index;
- modifier un record met a jour son index;
- supprimer un record supprime son index par cascade ou appel explicite;
- la recherche globale retourne les records attendus.

### Lot 2: recherche paginee

1. Ajouter une route paginee separee ou etendre prudemment la route existante.
2. Ajouter requete SQL utilisant `custom_service_record_index`.
3. Adapter `portal.js` pour utiliser la recherche paginee dans la vue records.
4. Garder fallback sur l'ancien chargement si la route echoue.

Critere d'acceptation:

- 50 records par page par defaut;
- recherche par texte dans `search_blob`;
- tri par `label_value`, `updated_at`, `created_at`;
- pas de changement cassant pour l'API liste existante.

### Lot 3: audit

1. Ajouter table `custom_service_audit_log`.
2. Ajouter `custom_service_audit.py`.
3. Journaliser actions records et import/export.
4. Ajouter endpoint de consultation.

Critere d'acceptation:

- chaque create/update/delete record produit une ligne d'audit;
- import/export produisent une ligne d'audit;
- les valeurs sensibles sont masquees;
- une panne d'audit ne bloque pas l'action utilisateur.

### Lot 4: credentials

1. Choisir et documenter le chiffrement.
2. Ajouter dependance si necessaire.
3. Ajouter table `custom_service_credentials`.
4. Ajouter service credentials.
5. Ajouter endpoints reveal/update/delete.
6. Ajouter migration optionnelle depuis `payload_json`.
7. Modifier export pour exclure credentials par defaut.

Critere d'acceptation:

- les nouveaux credentials ne sont plus stockes dans `payload_json`;
- reveal requiert un droit admin ou module dedie;
- reveal est audite;
- export standard ne contient pas `device_password`;
- la cle de chiffrement est recuperable apres redemarrage.

### Lot 5: frontend extraction

1. Creer `no_code_engine.js`.
2. Deplacer fonctions pures no-code.
3. Garder `portal.js` comme orchestrateur.
4. Ajouter tests manuels documentes.

Critere d'acceptation:

- creation service;
- creation record;
- recherche;
- edition;
- suppression;
- import;
- export;
- aucune regression visible sur dashboard/admin.

## 14. Tests a ajouter

### Tests Python prioritaires

- bootstrap idempotent;
- index payload simple;
- index exclut credentials;
- backfill idempotent;
- audit masque credentials;
- import/export conserve le comportement existant.

### Tests API prioritaires

- `POST /admin/custom-services/{code}/records` cree un index;
- `PUT /admin/custom-services/{code}/records/{id}` met a jour l'index;
- `DELETE /admin/custom-services/{code}/records/{id}` nettoie l'index;
- route query paginee filtre par recherche;
- action non authentifiee renvoie 401;
- utilisateur sans admin/module renvoie 403 si endpoint admin.

### Tests manuels

- demarrer l'app;
- creer un service no-code;
- ajouter champs `text`, `ip`, `url`, `date`, `list`;
- creer 3 records;
- rechercher une IP;
- exporter;
- importer un CSV;
- verifier que la treeview reste utilisable.

## 15. Points d'attention

### Encodage

Tous les fichiers `.md`, `.py`, `.js` doivent rester en UTF-8.

Eviter les caracteres typographiques si le fichier risque d'etre lu dans une console Windows mal configuree. Preferer ASCII dans le code et les commentaires techniques.

### Donnees sensibles

Ne jamais logguer:

- `device_password`;
- mot de passe revele;
- cle Fernet ou cle maitre;
- token Bearer.

### Transactions

Pour create/update record:

1. sauvegarder le record;
2. sauvegarder children;
3. mettre a jour l'index;
4. logger audit.

Idealement dans une transaction DB unique pour record + children + index. L'audit peut etre best-effort en v1 si cela simplifie.

### Compatibilite

Ne pas renommer:

- `device_login`;
- `device_password`;
- `payload_json`;
- routes existantes;
- champs de reponse existants.

Ajouter plutot des champs optionnels et endpoints nouveaux.

## 16. Definition de done v1

La v1 est consideree terminee quand:

- le schema est cree par bootstrap idempotent;
- les records no-code ont un index maintenu automatiquement;
- une recherche globale paginee fonctionne sur les records;
- l'export/import existant fonctionne toujours;
- les actions create/update/delete/import/export sont auditees;
- les credentials ne sont pas inclus dans `search_blob`;
- aucune route existante critique n'est cassee;
- les tests Python/API prioritaires passent.

## 17. Decision technique finale pour demarrer

Demarrer par le lot 1 uniquement.

Ne pas commencer par:

- chiffrement credentials;
- nouvelle UI complete;
- attachments;
- relations inter-services;
- preferences serveur;
- field choices en table dediee.

Ces sujets sont utiles, mais ils augmentent trop le risque tant que le socle index + audit n'est pas stabilise.
