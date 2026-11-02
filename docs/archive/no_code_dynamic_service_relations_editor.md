# Editeur visuel de relations des services dynamiques

Document de reference pour integrer dans le wizard no-code un editeur de relations proche de la maquette `relations_builder.html`.

Statut: specification de developpement pour une evolution ulterieure.

## 1. Objectif

Ajouter dans l'etape `Relations` du wizard de creation/modification d'un service dynamique un editeur canvas fonctionnel permettant de visualiser, creer et configurer les relations entre services.

L'editeur doit rester generique. Il ne doit pas etre specialise pour un metier comme les copieurs, les licences ou le monitoring.

L'objectif fonctionnel est double:

- permettre a l'utilisateur de comprendre visuellement comment les services sont relies;
- produire une configuration relationnelle exploitable ensuite dans les fiches, les tableaux, les imports, les sauvegardes et les restaurations.

## 2. Maquette de reference

Fichier fourni par l'utilisateur:

```text
C:\Users\damien\Downloads\relations_builder.html
```

Fonctionnalites presentes dans la maquette:

- panneau gauche avec la liste des services/tables disponibles;
- glisser-deposer d'un service vers le canvas;
- canvas central quadrille;
- blocs de services deplacables;
- ports gauche/droite sur chaque bloc;
- creation d'une relation par glisser entre deux ports;
- ligne temporaire pendant la creation;
- lien SVG avec fleche directionnelle;
- lien cliquable via une zone invisible plus large que le trait;
- selection visuelle du lien actif;
- panneau droit contextuel;
- choix du verbe de relation via chips;
- saisie d'un verbe personnalise;
- choix de cardinalite simplifie;
- phrase explicative en langage naturel;
- suppression de la relation selectionnee;
- boutons annuler/enregistrer.

La maquette contient aussi une logique de formulation en francais. Cette partie est utile pour l'ergonomie, mais ne doit pas bloquer la premiere integration fonctionnelle.

## 3. Etat actuel dans le code

Fichiers principaux:

- `monitoring/web/portal.js`
- `monitoring/web/app.css`
- `monitoring/storage/mariadb_bootstrap.py`
- `monitoring/storage/mariadb_manager.py`
- `monitoring/api/app.py`
- `monitoring/services/custom_service_schema.py`

Fonctions frontend deja presentes dans `portal.js`:

- `noCodeRelationDrafts(editor)`
- `noCodeRelationAvailableServices(editor)`
- `findNoCodeRelationDraft(editor, serviceCode)`
- `createNoCodeRelationDraft(service, index)`
- `noCodeRelationTypeLabel(type)`
- `buildNoCodeRelationCanvasBlockMarkup(...)`
- `buildNoCodeRelationCanvasMarkup(editor)`
- `buildNoCodeRelationPaletteMarkup(editor)`
- `buildNoCodeRelationPropertiesMarkup(editor)`
- `buildNoCodeServiceRelationsStepMarkup(editor)`
- `beginNoCodeRelationNodeDrag(event)`
- `updateNoCodeRelationNodeDrag(event)`
- `endNoCodeRelationNodeDrag()`

Styles existants dans `app.css`:

- `.no-code-relations-panel`
- `.no-code-relations-builder`
- `.no-code-relations-palette`
- `.no-code-relations-canvas`
- `.no-code-relations-canvas-tools`
- `.no-code-relations-stage`
- `.no-code-relation-lines`
- `.no-code-relation-node`
- `.no-code-relation-port`
- `.no-code-relations-properties`

L'existant couvre deja:

- une palette de services;
- un canvas;
- des noeuds de service;
- le zoom;
- le recentrage;
- le deplacement des noeuds;
- une selection basique de relation;
- des proprietes simples: type, sens, obligatoire.

Ce qui manque par rapport a la cible:

- creation de relation directement par ports;
- lien SVG selectionnable et editable;
- libelle/verbe de relation;
- cardinalite presentee de maniere ergonomique;
- phrase d'explication claire;
- suppression via l'inspecteur avec confirmation Itops;
- persistence robuste des relations;
- exploitation des relations dans les fiches et les listes.

## 4. Principe architectural

L'editeur canvas est uniquement l'interface de configuration.

La relation doit etre stockee comme une donnee metier stable, pas seulement comme une position graphique.

Les positions des noeuds, le zoom et les informations d'affichage sont secondaires. Elles servent a reouvrir le canvas dans le meme etat, mais ne doivent pas conditionner la logique applicative.

La logique relationnelle doit etre partagee par tous les services dynamiques:

- creation de service;
- modification de service;
- consultation d'une fiche;
- import/export;
- sauvegarde/restauration globale;
- futures specialisations metier.

## 5. Modele cible d'une relation

Objet logique recommande:

```json
{
  "id": "rel_...",
  "source_service_code": "copieurs",
  "target_service_code": "sites",
  "verb": "est localise sur",
  "cardinality": "many_to_one",
  "direction": "out",
  "required": false,
  "display_label": "Site",
  "source_x": 80,
  "source_y": 180,
  "target_x": 460,
  "target_y": 180,
  "sort_order": 10,
  "is_active": true
}
```

Cardinalites UI recommandees:

```text
one-one     -> one_to_one
one-many    -> one_to_many ou many_to_one selon le sens choisi
many-many   -> many_to_many
reference   -> many_to_one par defaut pour compatibilite simple
```

La maquette parle en langage simple:

- `Unique de chaque cote` -> `one_to_one`
- `Un element contient plusieurs autres` -> `one_to_many`
- `Tout le monde peut se melanger` -> `many_to_many`

Il faut conserver un vocabulaire utilisateur simple dans l'UI, mais stocker des valeurs techniques explicites.

## 6. Stockage recommande

Preferer une table dediee plutot qu'un champ JSON dans `custom_services`.

Table cible possible:

```sql
CREATE TABLE custom_service_relations (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  source_service_code VARCHAR(64) NOT NULL,
  target_service_code VARCHAR(64) NOT NULL,
  verb VARCHAR(191) NOT NULL DEFAULT 'est lie a',
  cardinality VARCHAR(32) NOT NULL DEFAULT 'many_to_one',
  direction VARCHAR(16) NOT NULL DEFAULT 'out',
  display_label VARCHAR(191) NULL,
  required TINYINT(1) NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  source_x INT NULL,
  source_y INT NULL,
  target_x INT NULL,
  target_y INT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_custom_service_relation (
    source_service_code,
    target_service_code,
    cardinality,
    direction
  ),
  KEY idx_custom_service_relations_source (source_service_code),
  KEY idx_custom_service_relations_target (target_service_code)
);
```

Points a confirmer avant implementation:

- ajout de contraintes FK vers `custom_services(code)` si le moteur actuel les supporte bien;
- comportement lors de la suppression d'un service lie;
- conservation ou suppression des relations inactives.

### Maintenance et suppression d'un service

La suppression d'un service doit toujours etre executee dans une transaction. Elle doit supprimer, dans cet ordre:

1. les liens de fiches concernes par les relations entrantes ou sortantes;
2. les relations dont le service est source ou cible;
3. les liens qui referencent directement une fiche de ce service;
4. les fiches du service puis le service lui-meme.

Les cles etrangeres avec `ON DELETE CASCADE` restent la protection principale pour une base neuve. Le gestionnaire applicatif doit cependant refaire ce nettoyage explicitement afin que les installations migrees, restaurations partielles ou anciennes bases sans contrainte ne laissent pas de donnees orphelines.

Une relation inactive ne doit plus etre proposee ni modifiable depuis les fiches. Elle reste consultable dans le wizard afin d'etre reactivee ou supprimee proprement.

## 7. Integration dans le wizard

### Etape Relations

L'etape `Relations` doit devenir une page en trois zones:

```text
[ Services disponibles ] [ Canvas relationnel ] [ Proprietes du lien ]
```

Le wizard doit garder ses boutons de navigation generaux:

- precedent;
- suivant;
- enregistrer;
- quitter avec confirmation.

Le canvas doit prendre le maximum d'espace disponible dans l'etape.

### Panneau gauche

Afficher les services dynamiques disponibles, hors service courant.

Chaque item doit contenir:

- libelle du service;
- code technique discret;
- nombre de champs;
- etat deja ajoute ou non au canvas.

Actions:

- clic: ajoute ou selectionne le service;
- drag/drop: depose le service sur le canvas a la position de la souris.

### Canvas central

Fonctions minimales:

- grille visuelle;
- blocs de service;
- ports de connexion;
- liens SVG;
- selection de lien;
- deplacement des blocs;
- zoom/dezoom;
- recentrage;
- suppression du lien selectionne via inspecteur.

Fonctions a ajouter ensuite:

- deplacement du canvas par pan;
- zoom molette avec limite;
- ajuster a l'ecran;
- mini-map si le canvas devient dense.

### Panneau droit

Etat vide:

- message clair quand aucune relation n'est selectionnee.

Etat relation selectionnee:

- source -> cible;
- verbe de relation;
- verbe personnalise;
- cardinalite;
- obligatoire ou non;
- sens de lecture;
- phrase explicative;
- bouton supprimer.

Le bouton supprimer doit utiliser la fenetre de confirmation Itops mutualisee, pas `confirm()`.

## 8. Creation d'une relation

Flux cible:

1. L'utilisateur ajoute deux services au canvas.
2. Il clique/glisse depuis un port du premier service.
3. Une ligne temporaire suit la souris.
4. Il relache sur le port du second service.
5. Une relation par defaut est creee.
6. Le panneau droit s'ouvre automatiquement sur cette relation.
7. L'utilisateur choisit le verbe et la cardinalite.

Validation a appliquer:

- refuser une relation d'un service vers lui-meme;
- refuser une relation si la source ou cible est vide;
- eviter les doublons exacts;
- alerter si une relation inverse existe deja;
- ne pas supprimer silencieusement une relation deja utilisee par des fiches.

## 9. Exploitation dans l'application

L'editeur ne doit pas rester decoratif. Une relation configuree doit produire un comportement exploitable.

### Dans une fiche

Selon la cardinalite:

- `one_to_one`: champ reference unique;
- `many_to_one`: champ reference unique cote record courant;
- `one_to_many`: section "Elements lies" consultable depuis la fiche;
- `many_to_many`: table de liaison et section multi-selection.

La fiche doit permettre:

- consulter les elements lies;
- ajouter ou retirer un lien;
- naviguer vers la fiche liee;
- afficher un etat vide propre.

### Dans les tableaux

Prevoir:

- colonne optionnelle affichant le libelle de l'element lie;
- filtre par relation;
- tri si techniquement raisonnable;
- action contextuelle "Voir les elements lies".

### Dans l'import

Le moteur d'import global doit pouvoir mapper une colonne vers une relation existante.

Exemple:

```text
Copieur.Site -> reference vers service Sites
Copieur.Contrat -> reference vers service Contrats
```

Regles:

- le mapping doit proposer les relations existantes;
- la resolution doit se faire par identifiant stable ou libelle selon configuration;
- les erreurs de resolution doivent suivre le moteur d'import souple deja mis en place.

## 10. Sauvegarde et restauration

La sauvegarde globale doit inclure:

- definitions de services;
- champs;
- records;
- historique;
- relations;
- positions canvas si elles sont conservees;
- eventuelles tables de liaison.

La restauration doit etre idempotente:

- rejouer une restauration ne duplique pas les relations;
- les relations existantes sont mises a jour;
- les relations supprimees dans la sauvegarde doivent etre traitees explicitement selon la politique retenue.

## 11. Plan d'implementation recommande

### Lot 1 - Base relationnelle et backfill

- Ajouter la table `custom_service_relations`.
- Ajouter bootstrap idempotent.
- Ajouter operations manager:
  - lister relations;
  - creer/mettre a jour;
  - supprimer/desactiver;
  - remplacer les relations d'un service.
- Ajouter schemas API.
- Ajouter routes API.
- Ajouter tests d'idempotence et backfill.

### Lot 2 - Wizard UI canvas

- Remplacer l'etape relations actuelle par le layout trois zones.
- Conserver les fonctions de drag de noeuds deja presentes.
- Ajouter creation de liens par ports.
- Ajouter selection de liens SVG.
- Ajouter inspecteur droit complet.
- Ajouter verbe, cardinalite, sens, obligatoire.
- Ajouter suppression avec modal Itops.

### Lot 3 - Persistance wizard

- Charger les relations existantes en mode edition.
- Sauvegarder les relations au moment de la sauvegarde du service.
- Conserver les positions canvas.
- Gerer les erreurs API.
- Tester modification puis reouverture du wizard.

### Lot 4 - Exploitation dans les fiches

- Afficher les relations dans la vue fiche.
- Ajouter consultation des elements lies.
- Ajouter edition des references selon la cardinalite.
- Ajouter confirmations si suppression d'un lien utilise.

### Lot 5 - Import/export et sauvegarde globale

- Integrer les relations au moteur d'import souple.
- Integrer les relations a la sauvegarde/restauration globale.
- Ajouter tests de restauration idempotente.

### Lot 6 - Finitions UX

- Pan canvas.
- Ajuster a l'ecran.
- Zoom molette.
- Libelles naturels plus pousses.
- Accessibilite clavier.
- Etat d'erreur visuel sur les liens invalides.

## 12. Tests a prevoir

Backend:

- bootstrap cree la table une seule fois;
- creation relation simple;
- mise a jour relation;
- suppression/desactivation;
- prevention des doublons;
- restauration idempotente;
- suppression d'un service avec relations existantes.

Frontend:

- `node --check monitoring/web/portal.js`;
- ajout d'un service sur canvas;
- deplacement d'un bloc;
- zoom/dezoom;
- creation d'un lien par ports;
- selection du lien;
- modification verbe/cardinalite;
- suppression avec confirmation Itops;
- sauvegarde puis reouverture du wizard.

Integration:

- creation service A;
- creation service B;
- relation A -> B;
- creation d'une fiche A referencee a B;
- affichage depuis la fiche;
- sauvegarde globale;
- restauration sur une base vide;
- verification absence de doublons.

## 13. Points d'attention

- Ne pas dupliquer un moteur relationnel specifique au monitoring.
- Ne pas melanger configuration visuelle et logique metier.
- Ne pas stocker uniquement dans le frontend.
- Ne pas utiliser de prompt navigateur.
- Ne pas casser les services dynamiques deja crees.
- Ne pas rendre obligatoire la configuration de relations.
- Ne pas specialiser les libelles sur un cas metier.

## 14. Decision recommandee

Commencer par le lot 1 puis le lot 2.

La raison est simple: si le canvas est fait avant le modele de donnees, il risque de produire une configuration fragile ou non restaurable. Le modele relationnel doit donc etre stabilise avant d'investir dans l'interface complete.
