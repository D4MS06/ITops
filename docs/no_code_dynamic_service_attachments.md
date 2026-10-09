# Pieces jointes des services dynamiques

## Objectif

Ajouter au moteur no-code des services dynamiques une capacite optionnelle de pieces jointes par fiche, sans specialiser la fonctionnalite pour un metier donne.

Exemples d'usage :

- copieur : facture d'achat, fiche d'intervention, licence, contrat ;
- vehicule : carte grise, controle technique, facture, assurance ;
- contrat : avenants, documents signes, justificatifs.

La fonctionnalite doit rester generique : l'utilisateur choisit d'activer ou non les documents sur un service, puis organise les categories documentaires comme il le souhaite.

## Principe architectural

Ne pas creer un second moteur de stockage.

iTops dispose deja d'un moteur de stockage general. Les services dynamiques doivent s'appuyer dessus pour :

- stocker physiquement les fichiers ;
- telecharger / supprimer / renommer si ces primitives existent deja ;
- conserver les controles de securite, chemins, taille et types de fichiers ;
- eviter la duplication de code et de logique.

La couche service dynamique doit seulement ajouter :

- la configuration documentaire du service ;
- le lien entre une fiche de service et un fichier stocke ;
- l'organisation des fichiers par categories documentaires.

## Concepts

### Activation par service

Ajouter une option de service :

```text
attachments_enabled: bool
```

Si l'option est desactivee :

- aucune section document ne s'affiche dans la fiche ;
- aucune API d'upload propre au service ne doit accepter de document ;
- aucune colonne compteur document n'est affichee.

### Categories documentaires

Chaque service peut definir ses propres categories.

Exemple pour un service `copieurs` :

- Factures d'achat
- Fiches d'intervention
- Licences
- Contrats
- Photos
- Divers

Ces valeurs ne doivent pas etre codees en dur. Elles sont configurees dans le wizard.

Parametres possibles par categorie :

- cle technique stable ;
- libelle ;
- description ;
- extensions autorisees optionnelles ;
- taille max optionnelle ;
- un seul fichier ou plusieurs fichiers ;
- obligatoire ou non ;
- ordre d'affichage.

## Modele de donnees cible

### Configuration des categories

Table proposee :

```sql
custom_service_document_categories
```

Colonnes indicatives :

```text
id BIGINT AUTO_INCREMENT PRIMARY KEY
service_code VARCHAR(64) NOT NULL
category_key VARCHAR(191) NOT NULL
label VARCHAR(191) NOT NULL
description TEXT NOT NULL
allowed_extensions TEXT NOT NULL
max_size_mb INT NULL
multiple_files TINYINT(1) NOT NULL DEFAULT 1
required TINYINT(1) NOT NULL DEFAULT 0
sort_order INT NOT NULL DEFAULT 100
created_at DATETIME NULL
updated_at DATETIME NULL
```

Contraintes :

```text
UNIQUE(service_code, category_key)
FOREIGN KEY(service_code) REFERENCES custom_services(code) ON DELETE CASCADE
```

### Liaison fiche / fichier

Table proposee :

```sql
custom_service_record_attachments
```

Colonnes indicatives :

```text
id BIGINT AUTO_INCREMENT PRIMARY KEY
service_code VARCHAR(64) NOT NULL
record_id VARCHAR(191) NOT NULL
category_key VARCHAR(191) NOT NULL
storage_file_id VARCHAR(191) NOT NULL
display_name VARCHAR(255) NOT NULL
description TEXT NOT NULL
uploaded_at DATETIME NOT NULL
uploaded_by VARCHAR(191) NOT NULL DEFAULT ''
sort_order INT NOT NULL DEFAULT 100
```

`storage_file_id` doit pointer vers l'identifiant ou la reference stable du moteur de stockage general. Si le moteur actuel expose plutot un chemin, preferer ajouter une abstraction cote stockage plutot que stocker des chemins bruts partout.

Contraintes :

```text
FOREIGN KEY(service_code) REFERENCES custom_services(code) ON DELETE CASCADE
FOREIGN KEY(record_id) REFERENCES custom_service_records(id) ON DELETE CASCADE
```

## Wizard service no-code

Ajouter une etape ou section `Documents`.

UI attendue :

- case `Activer les pieces jointes pour ce service` ;
- liste des categories documentaires ;
- bouton `Ajouter une categorie` ;
- edition inline ou panneau lateral pour chaque categorie ;
- reordonnancement simple ;
- suppression avec confirmation si deja utilisee.

Champs de categorie :

- libelle ;
- cle technique auto-generee depuis le libelle, modifiable si creation ;
- description ;
- extensions autorisees ;
- taille max ;
- plusieurs fichiers autorises ;
- categorie obligatoire ;
- ordre.

L'UI doit rester generique et ne pas afficher de libelles metier predefinis comme "facture" ou "licence", sauf eventuellement sous forme d'exemples non persistants.

## Consultation et edition d'une fiche

Dans la fenetre fiche ouverte au double-clic, ajouter un onglet ou une section `Documents`.

Organisation recommandee :

```text
Documents

Factures d'achat
- facture_achat_2024.pdf
- extension_garantie.pdf

Fiches d'intervention
- intervention_2026-06-12.pdf
- intervention_2026-06-24.pdf

Licences
- licence_scan.pdf
```

Actions par fichier :

- ouvrir / telecharger ;
- renommer l'affichage ;
- changer de categorie ;
- modifier une description ;
- supprimer avec confirmation.

Actions par categorie :

- ajouter un fichier ;
- afficher le nombre de fichiers ;
- signaler les categories obligatoires vides si la regle est activee.

Dans le treeview principal du service, ajouter si utile une colonne automatique `Documents` avec compteur, par exemple `3`.

## API a prevoir

Configuration service :

```text
GET    /admin/custom-services/{service_code}/document-categories
POST   /admin/custom-services/{service_code}/document-categories
PUT    /admin/custom-services/{service_code}/document-categories/{category_key}
DELETE /admin/custom-services/{service_code}/document-categories/{category_key}
```

Pieces jointes de fiche :

```text
GET    /admin/custom-services/{service_code}/records/{record_id}/attachments
POST   /admin/custom-services/{service_code}/records/{record_id}/attachments
PUT    /admin/custom-services/{service_code}/records/{record_id}/attachments/{attachment_id}
DELETE /admin/custom-services/{service_code}/records/{record_id}/attachments/{attachment_id}
```

Telechargement :

```text
GET /admin/custom-services/{service_code}/records/{record_id}/attachments/{attachment_id}/download
```

L'upload doit deleguer au moteur de stockage general et ne conserver dans la table de liaison que la reference stable du fichier.

## Regles de securite

- verifier que le service existe ;
- verifier que la fiche appartient bien au service ;
- verifier que la categorie appartient bien au service ;
- verifier les droits utilisateur existants sur les services dynamiques ;
- ne jamais accepter un chemin de fichier arbitraire depuis le client ;
- appliquer les limites taille / extension si configurees ;
- confirmer toute suppression.

## Import/export

Ne pas melanger cette fonctionnalite avec l'import CSV initial.

Un CSV ne transporte pas les fichiers. Pour un futur besoin avance, prevoir un import ZIP contenant :

- un fichier tabulaire ;
- un dossier de documents ;
- une colonne de mapping vers les fichiers.

Ce point doit etre traite comme une evolution separee.

## Plan de developpement recommande

1. Ajouter le schema base et les migrations idempotentes.
2. Ajouter les services backend de categories et liaisons.
3. Brancher le stockage general pour upload/download/delete.
4. Exposer les endpoints API.
5. Ajouter la section `Documents` dans le wizard.
6. Ajouter l'onglet ou section `Documents` dans la fiche.
7. Ajouter le compteur documents dans le treeview.
8. Ajouter les tests :
   - migration idempotente ;
   - creation/modification/suppression categorie ;
   - upload document ;
   - isolation service/fiche ;
   - suppression fiche supprime les liens ;
   - suppression document demande confirmation cote UI.

## Points d'attention

- Ne pas stocker le binaire en base si le moteur de stockage general gere deja les fichiers.
- Ne pas creer de categories metier codees en dur.
- Ne pas dupliquer l'UI d'upload si un composant existe deja.
- Ne pas casser les services existants : l'activation doit etre opt-in.
- Prevoir la restauration/sauvegarde globale : les fichiers lies doivent suivre la strategie existante du stockage general.
