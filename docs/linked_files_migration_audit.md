# Audit migration fichiers lies

## Objectif

Preparer l'extraction d'un moteur generique de fichiers lies, tout en conservant
l'experience actuelle de sauvegarde des configurations reseau dans le module
monitoring.

L'objectif metier prioritaire reste la constitution d'une banque locale de
fichiers de configuration des equipements reseau, principalement les switches,
avec redondance vers un dossier distant lorsque le stockage SMB3 ou un dossier
de sauvegarde est configure.

## Etat actuel

La gestion des fichiers de configuration est aujourd'hui exposee comme une
fonctionnalite du module monitoring/inventaire.

Points principaux:

- `ConfigStorageService` centralise les chemins locaux, le dossier de sauvegarde
  actif, la connexion SMB3, l'import de versions et la synchronisation.
- `monitoring/utils/config_files.py` contient la logique bas niveau de recherche,
  nommage, copie, import, liste, suppression et renommage de versions locales.
- Les routes API actuelles sont rattachees au module monitoring:
  - `GET /config-storage/state`
  - `POST /config-storage/open-local-folder`
  - `POST /config-storage/open-backup-folder`
  - `POST /config-storage/sync-now`
  - `GET /config-files`
  - `GET /config-files/latest-download`
  - `POST /config-files/import`
- Les types d'equipements portent le flag `config_backups_enabled`.
- L'UI web active les actions de configuration seulement si le type du device a
  `config_backups_enabled = true`.
- Le modele enrichit les devices avec `has_saved_config` lorsqu'une version
  locale existe.
- Les metadonnees de versions importees sont stockees dans
  `config_file_versions`.

## Comportements a conserver

La migration ne doit pas degrader les usages techniciens existants.

Comportements a maintenir:

- Activer ou desactiver la gestion des configurations par type d'equipement.
- Afficher les actions de configuration uniquement pour les types eligibles.
- Importer un fichier de configuration pour un device.
- Lier les versions importees au type et au nom du device.
- Lister les versions disponibles depuis la fiche ou le menu du device.
- Telecharger la derniere sauvegarde connue d'un device.
- Detecter l'existence d'au moins une config sauvegardee via `has_saved_config`.
- Conserver une copie locale sur le serveur.
- Permettre une redondance vers un dossier de sauvegarde local ou SMB3.
- Purger les fichiers de configuration lorsqu'un type perd la gestion des
  configurations, si ce comportement est confirme comme souhaitable.

## Limites identifiees

La gestion actuelle fonctionne pour le cas monitoring, mais elle est trop
specialisee pour devenir directement un service commun.

Limites:

- Les concepts sont lies aux devices: `device_type`, `device_name`, `device_ip`.
- Le stockage est pense pour les configurations reseau, pas pour des pieces
  jointes generiques.
- Les routes exigent l'acces au module monitoring.
- Les services dynamiques ne consomment pas ce mecanisme.
- Les parametres `config_auto_sync_enabled` et
  `config_auto_sync_interval_seconds` sont stockes et exposes dans l'UI, mais
  aucun scheduler d'execution automatique n'a ete identifie.
- La fonction `sync_latest_config_versions_for_type` existe mais n'est pas
  appelee dans le flux actuel.
- Des primitives de suppression/renommage existent dans les utilitaires, mais
  elles ne sont pas exposees clairement dans les routes actuelles auditees.

## Cible proposee

Ne pas transformer `ConfigStorageService` en service generique directement.
Introduire plutot un moteur generique en dessous, puis garder une facade metier
specialisee pour le monitoring.

### Moteur generique

Nom possible: `LinkedFileService` ou `AttachmentService`.

Responsabilites:

- Stocker un fichier lie a un objet applicatif.
- Lister les fichiers d'un objet.
- Telecharger un fichier.
- Supprimer ou renommer un fichier.
- Gerer le versioning si la categorie le demande.
- Calculer taille, hash et type MIME.
- Gerer le statut de synchronisation vers un stockage distant.
- Fournir une base reutilisable pour les services dynamiques.

Champs communs envisages:

- `id`
- `owner_kind`, par exemple `device` ou `custom_service_record`
- `owner_id`
- `module_code`
- `category`, par exemple `config` ou `attachment`
- `filename`
- `stored_path`
- `mime_type`
- `size_bytes`
- `sha256`
- `version_label`
- `detail`
- `metadata_json`
- `sync_status`
- `sync_error`
- `created_by`
- `created_at`
- `updated_at`

`metadata_json` doit rester un champ secondaire pour les details variables. Les
champs servant aux recherches, droits, rattachements et synchronisations doivent
rester en colonnes.

### Facade monitoring

Nom possible: `DeviceConfigFileService`.

Responsabilites:

- Garder le vocabulaire metier: configuration de device, versions de switch,
  derniere sauvegarde.
- Verifier `config_backups_enabled`.
- Traduire un device vers `owner_kind = device`, `owner_id = <device_id>`,
  `category = config`.
- Conserver la recherche historique par nom/IP pour les fichiers deja presents
  dans les dossiers de sauvegarde.
- Presenter des messages adaptes aux techniciens reseau.

## Premiere sequence de migration

1. Ajouter le modele et le repository generique de fichiers lies.
2. Ajouter `LinkedFileService` sans modifier les routes existantes.
3. Ajouter `DeviceConfigFileService` comme facade monitoring.
4. Faire appeler les routes `/config-files/*` par la facade monitoring.
5. Migrer progressivement les metadonnees de `config_file_versions` vers le
   nouveau modele, ou maintenir une compatibilite temporaire.
6. Ajouter ensuite les actions manquantes si souhaitees: suppression,
   renommage, telechargement d'une version precise.
7. Ajouter le drag and drop dans l'UI monitoring.
8. Ajouter un etat de redondance par fichier: local seulement, synchronise,
   erreur.
9. Mettre en place la synchronisation automatique seulement apres stabilisation
   du modele et de la synchronisation manuelle.
10. Brancher les services dynamiques sur le moteur generique avec une UI
    "pieces jointes", separee de l'UI "configurations de device".

## Points de vigilance

- Ne pas casser les URLs et comportements existants de l'UI monitoring pendant
  la migration.
- Eviter que les services dynamiques dependent de notions monitoring.
- Eviter de stocker dans `metadata_json` des informations qui devront etre
  filtrees, indexees ou securisees.
- Definir clairement si la suppression d'un type ou la desactivation de
  `config_backups_enabled` doit supprimer les fichiers physiques, les masquer,
  ou seulement bloquer les nouveaux imports.
- Prevoir une migration reversible ou au minimum idempotente pour les
  metadonnees existantes.
