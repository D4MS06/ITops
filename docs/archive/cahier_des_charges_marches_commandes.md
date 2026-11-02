# Cahier des charges — Marchés et commandes

## 1. Objet et périmètre

Mettre en place des modules personnalisés ITops permettant au service informatique de suivre un achat, depuis la demande de devis jusqu'à sa réception. La conception doit être réutilisable à terme par les autres services de la collectivité.

Le périmètre comprend :

- les marchés publics et accords-cadres, partagés par tous les services ;
- les commandes du service informatique ;
- les fournisseurs, sous la forme initiale d'une liste partagée ;
- les documents liés (devis, bon de commande, bon de livraison, facture) ;
- les liens facultatifs vers les équipements suivis dans ITops.

Les engagements existants restent dédiés aux contrats, abonnements, garanties et renouvellements. Une commande peut y être reliée si nécessaire, sans que ce soit obligatoire.

## 2. Principes de conception

1. **Pas de ressaisie des données durables.** Le titulaire, la référence et les dates d'un marché sont saisis une fois dans le module Marchés.
2. **Une commande conserve son contexte historique.** Elle est liée à un marché ou identifiée explicitement comme hors marché.
3. **Les relations vers les équipements sont facultatives.** Les câbles, consommables et petits matériels ne créent pas d'équipement inventorié ; un serveur, un switch ou un poste peut y être lié si la collectivité choisit de l'inventorier.
4. **Le document est la preuve, pas une donnée à recopier.** Les fichiers sont liés à la fiche ITops ; leur date de liaison alimente les dates de suivi, tout en restant corrigeable manuellement.
5. **La solution est générique.** Les futurs services pourront réutiliser Marchés et Fournisseurs sans modifier le moteur des modules personnalisés.

## 3. Module générique « Marchés / accords-cadres »

### 3.1 Finalité

Centraliser les marchés et accords-cadres de la collectivité, notamment les trois marchés informatiques actuels : vidéoprotection, matériel informatique et téléphonie IP.

Une fiche représente un marché ou, si la gestion des lots doit être précise, un lot de marché. La règle est : une fiche doit correspondre à un titulaire, une référence et une période cohérents.

### 3.2 Champs

| Libellé | Clé technique | Type | Obligatoire | Règle |
|---|---|---:|---:|---|
| Intitulé du marché | `intitule` | Texte | Oui | Libellé lisible dans les relations. |
| Service pilote | `service_pilote` | Liste / relation | Oui | Informatique au démarrage ; extensible aux autres services. |
| Domaine | `domaine` | Liste | Oui | Informatique, vidéoprotection, téléphonie IP, puis autres domaines. |
| Fournisseur titulaire | `fournisseur` | Liste partagée Fournisseurs | Oui | Fournisseur déduit pour les commandes via marché. |
| Référence du marché | `reference_marche` | Texte | Oui | Référence officielle. |
| Lot | `lot` | Texte | Non | À renseigner si le marché est découpé en lots. |
| Date de début | `date_debut` | Date | Oui | Historisée. |
| Date de fin | `date_fin` | Date | Oui | Historisée et exploitable pour les alertes futures. |
| Statut | `statut` | Liste | Oui | Actif, Expiré, Clôturé, Suspendu. |
| Observations | `observations` | Texte long | Non | Informations utiles non structurées. |

### 3.3 Documents et stockage

Documents possibles : acte d'engagement, règlement, bordereau de prix, avenant et document de renouvellement.

Les documents sont stockés via le mécanisme documentaire commun. Le nom du dossier doit être basé sur une référence stable de marché, jamais sur un identifiant technique ITops.

## 4. Liste partagée « Fournisseurs »

Créer une liste partagée, et non un module Fournisseurs dans cette première phase.

Elle sert aux marchés et aux commandes hors marché. Elle évite les variantes de saisie d'un même fournisseur. Un module dédié ne sera créé que lorsque le besoin de gérer contacts, SIRET, coordonnées, conditions de règlement ou évaluations fournisseurs sera confirmé.

## 5. Module « Commandes informatiques »

### 5.1 Finalité

Suivre le processus d'achat d'une commande informatique : demande de devis, devis reçu, validation, bon de commande, commande, réception complète ou partielle, puis clôture.

Une fiche représente un dossier de commande. Elle peut contenir plusieurs articles homogènes ou une commande mixte. Une future extension « lignes de commande » ne sera envisagée que si le suivi article par article devient nécessaire.

### 5.2 Champs

| Libellé | Clé technique | Type | Obligatoire | Règle |
|---|---|---:|---:|---|
| Référence interne | `reference_commande` | Texte | Oui | Unique et utilisée pour le dossier documentaire. |
| Objet | `objet` | Texte | Oui | Description courte de la commande. |
| Catégorie | `categorie` | Liste | Oui | Petit matériel, matériel informatique, réseau, téléphonie IP, vidéoprotection, logiciel, autre. |
| Priorité | `priorite` | Liste | Oui | Normale, Haute, Urgente. |
| Service bénéficiaire | `services_beneficiaires` | Relation | Non | Une ou plusieurs relations. |
| Mode d'achat | `mode_achat` | Liste | Oui | Via un marché ou Hors marché. |
| Fournisseur hors marché | `fournisseur_hors_marche` | Liste partagée Fournisseurs | Conditionnel | Requis seulement si le mode est Hors marché. |
| Motif hors marché | `motif_hors_marche` | Texte long | Conditionnel | Requis seulement si le mode est Hors marché. |
| Statut | `statut` | Liste | Oui | Voir le cycle de vie. |
| Date de réception du devis | `date_reception_devis` | Date | Non | Préremplie lors du lien du premier devis ; modifiable. |
| Date de commande | `date_commande` | Date | Non | Préremplie lors du lien du premier bon de commande ; modifiable. |
| Date de réception finale | `date_reception_finale` | Date | Non | Renseignée lorsque la réception est complète. |
| Éléments manquants | `elements_manquants` | Texte long | Non | Attendu pour une réception partielle. |
| Observations | `observations` | Texte long | Non | Réserves, échanges fournisseur ou informations pratiques. |

Les dates, le statut et les champs de suivi doivent être historisés par le mécanisme commun des modules personnalisés.

### 5.3 Relations

| Relation | Cardinalité | Obligation fonctionnelle | Comportement |
|---|---:|---:|---|
| Marché / accord-cadre | 0..1 | Requise si `mode_achat = Via un marché` | Le fournisseur est déduit et affiché depuis le marché. |
| Services bénéficiaires | 0..n | Facultative | Une commande peut servir plusieurs services. |
| Engagement | 0..1 ou 0..n | Facultative | Uniquement lorsqu'un contrat, abonnement ou garantie est concerné. |
| Équipements inventoriés | 0..n | Facultative | Lien seulement vers les actifs que la collectivité choisit d'inventorier. |

Le lien Marché ne doit pas être utilisé pour une commande hors marché. La saisie fournisseur hors marché reste alors disponible.

### 5.4 Cycle de vie

Valeurs proposées pour `statut` :

1. Brouillon
2. Devis demandé
3. Devis reçu
4. À valider
5. Validée
6. Bon de commande envoyé
7. Commandée
8. Réception partielle
9. Réceptionnée
10. Annulée
11. Litige fournisseur

Règles principales :

- le statut **Réception partielle** impose une saisie dans `elements_manquants` ;
- le statut **Réceptionnée** renseigne ou demande la date de réception finale ;
- le statut **Hors marché** ne rend pas la commande invalide : il impose le fournisseur et le motif hors marché ;
- le statut **Commandée** exige qu'un bon de commande soit lié ou que la date de commande soit renseignée manuellement.

## 6. Gestion documentaire

### 6.1 Catégories

Chaque commande expose quatre catégories documentaires :

- Devis ;
- Bon de commande ;
- Bon de livraison ;
- Facture.

Le stockage doit utiliser `reference_commande` comme source de nom de dossier afin d'obtenir un chemin stable et unique, par exemple :

`\\serveur\partage\COMMANDES\CMD-2026-0042`

### 6.2 Comportements attendus

- L'ajout du premier devis renseigne `date_reception_devis` avec la date de liaison du fichier si le champ est vide.
- L'ajout du premier bon de commande renseigne `date_commande` si le champ est vide.
- L'utilisateur peut toujours modifier ces deux dates : l'automatisation ne doit jamais écraser une valeur saisie manuellement.
- Dans les inventaires et modales, un seul document lié est ouvert depuis le texte du champ configuré ; plusieurs documents ouvrent la modale de consultation.
- Un PDF est ouvert dans un nouvel onglet avec le lecteur du navigateur ; les autres formats restent téléchargeables.

L'alimentation automatique des dates est une évolution générique du moteur documentaire, à concevoir pour être utilisable par tout module personnalisé et non seulement par les commandes.

## 7. Droits et traçabilité

- Les rôles habilités peuvent créer et modifier les commandes selon les droits du module.
- Les dates, statuts et relations doivent conserver leur historique.
- Les suppressions de documents ne suppriment que le lien ITops ; la suppression physique doit rester une action explicitement confirmée dans le stockage.
- Les commandes clôturées et les marchés expirés restent consultables.

## 8. Critères de recette

1. Une commande via marché ne demande pas de ressaisir le fournisseur ; le marché lié affiche le titulaire.
2. Une commande hors marché peut être créée sans relation Marché, avec fournisseur et motif obligatoires.
3. Une commande ne comportant aucun équipement inventorié est valide.
4. Une réception partielle affiche et conserve les éléments manquants.
5. Le dépôt d'un devis puis d'un bon de commande préremplit les dates correspondantes sans écraser une date manuelle.
6. Une fiche Marché modifiée n'altère pas les informations propres déjà saisies sur une commande.
7. Les documents, relations et changements de statut sont visibles selon les droits du module.
8. Le même module Marchés peut être utilisé par un futur module de commandes d'un autre service.

## 9. Phasage recommandé

### Phase 1 — Socle

- Liste partagée Fournisseurs ;
- Module Marchés / accords-cadres ;
- Module Commandes informatiques ;
- Relations, statuts, historique et documents ;
- Création des trois marchés informatiques existants.

### Phase 2 — Automatisation documentaire

- Règle générique de préremplissage d'un champ date à partir du premier document lié d'une catégorie ;
- Validation conditionnelle du mode d'achat ;
- Alertes éventuelles sur fin de marché.

### Phase 3 — Selon les usages

- Module Fournisseurs détaillé ;
- Lignes de commande et réception article par article ;
- Réemploi du module Marchés par les autres services.
