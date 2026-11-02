# ITops — Spécifications fonctionnelles : demandes de devis

**Statut :** référence fonctionnelle du P0 en cours de validation
**Périmètre :** service personnalisé No-Code et extensions génériques du moteur existant
**Sources :** décisions fonctionnelles échangées avec le commanditaire ; audits du code et de la configuration MariaDB fournis par Codex (octobre 2026). Les constatations techniques sont à revalider dans la branche et la base ciblées avant modification.

## 1. Objectif

Créer un service personnalisé **Demandes de devis** indépendant, au moyen de l'éditeur No-Code ITops, capable de :

1. préparer un courrier de demande de devis à partir d'un modèle et des données disponibles ;
2. le présenter à un utilisateur pour correction et autorisation explicite avant l'envoi ;
3. conserver les informations réellement envoyées et tracer les étapes ;
4. surveiller les délais, préparer les relances et notifier le responsable, sans jamais envoyer un email métier externe sans validation ;
5. détecter la réception d'un devis par l'association d'un document à une rubrique dédiée et arrêter les relances ;
6. **si le circuit d'achat est activé**, créer automatiquement une fiche **Commandes informatiques** au statut **Brouillon** et une fiche **Engagements** au statut de préparation, sans validation administrative ni engagement financier officiel ;
7. lier les fiches produites et éviter toute création en double.

Le moteur ne doit connaître aucun concept métier « devis », « fournisseur » ou « engagement » en dur : ces notions proviennent de la configuration des services No-Code et de règles déclaratives.

## 2. Modes d'utilisation et portée

Une demande peut être :

- **Libre** : adresse email saisie, sans fiche Fournisseur et sans Marché ;
- **Avec fournisseur référencé** : lien facultatif vers une fiche `fournisseurs`, sans marché obligatoire ;
- **Avec fournisseur et marché** : liens vers `fournisseurs` et éventuellement `marches` ; respecter la cohérence avec le titulaire du marché lorsque cette donnée est disponible.

Les liens Fournisseur et Marché ne sont **jamais des prérequis absolus** à la création ou à l'envoi d'une demande. Il faut en revanche un destinataire effectif, valide et confirmé avant tout envoi.

Un choix **Suite de la demande** distingue :

- `suivi_uniquement` : envoi, relances, réception et traçabilité sans création de Commande/Engagement ;
- `circuit_achat` : création des deux fiches en préparation dès l'association du devis reçu.

Le choix est explicite, éditable dans les limites des opérations déjà effectuées. Ne pas supprimer automatiquement une commande créée lorsqu'on change ensuite de mode.

## 3. Modules existants : constat de l'audit MariaDB

| Service | Code | Enregistrements audit | Éléments utiles / limites |
|---|---|---:|---|
| Fournisseurs | `fournisseurs` | 22 | `raison_sociale` obligatoire, `contact_commercial`, `email`, autres coordonnées ; **0 adresse email renseignée** lors de l'audit |
| Marchés | `marches` | 0 | `intitule`, `reference_marche`, `statut`, dates ; relation obligatoire vers titulaire Fournisseur |
| Commandes informatiques | `commandes_informatiques` | 216 | `objet`, `categorie`, `priorite`, `mode_achat` obligatoires ; `statut=Brouillon` existe ; rubriques Devis et Bon de commande |
| Engagements | `engagements` | 217 | `reference`, `objet`, `date_debut` obligatoires ; `statut=Brouillon` existe, **`En préparation` absent** ; rubriques Devis, Bon de commande, Facture |

Relations existantes identifiées : `marches → fournisseurs` (30), `commandes_informatiques → marches` (31), `commandes_informatiques → fournisseurs` (32), `commandes_informatiques → engagements` (39). Vérifier leur sens et cardinalité, notamment la relation 31 (`one_to_many`).

**Anomalies connues :** `commandes_informatiques.montant_ht` porte le libellé « Montant TTC » ; `engagements.montant_annuel` est un texte et n'est pas équivalent à un prix ponctuel ; certaines valeurs accentuées de conditions/automatisations semblent mal encodées. Ne pas effectuer de mapping financier automatique tant que la sémantique n'a pas été clarifiée.

## 4. Proposition minimale de données du nouveau service

Ce tableau est une **proposition à confronter aux types et mécanismes réellement présents** dans l'éditeur. Les métadonnées internes d'exécution (IDs de tâches, snapshots d'emails, compteurs) doivent de préférence rester dans les composants techniques existants, et non être exposées comme champs métier.

| Champ suggéré | Type | Remarque |
|---|---|---|
| `objet` | Texte | Obligatoire ; repris dans le courrier et les fiches cibles |
| `description_besoin` | Texte long | Obligatoire ; texte de base du courrier |
| `categorie` | Liste partagée ou alignée | Pour satisfaire `commandes_informatiques.categorie` si `circuit_achat` ; exigence conditionnelle ou valeur à compléter |
| `priorite` | Liste partagée ou alignée | Idem ; défaut possible `Normale` |
| `mode_achat` | Liste | Conforme aux valeurs du service Commandes ; ne pas imposer le marché |
| `statut` | Liste | `Brouillon`, `À valider`, `En attente du devis`, `Devis reçu`, `Annulée`, états complémentaires si nécessaires |
| `suite_demande` | Liste | `Suivi uniquement`, `Circuit d'achat` |
| `destinataire_libre` | Email/texte validé | Utilisé si aucune adresse liée ou en mode libre ; adresse finale vérifiable dans le composeur |
| `nom_destinataire_libre` | Texte | Facultatif |
| `reference_devis` | Texte | Facultatif, renseigné à réception si connu |
| `date_envoi` | Date/heure | Calculée à partir de l'envoi réellement confirmé ; peut être une donnée système |
| `date_reception_devis` | Date/heure | Automatiquement renseignée au lien du devis ; pas de saisie obligatoire initiale |

Créer une rubrique documentaire dédiée **Devis reçu**. Les relations **Demande → Fournisseur** et **Demande → Marché** sont facultatives. Prévoir des relations vers **Commande** et **Engagement** pour le circuit d'achat. La sélection de fiches liées existante peut être réutilisée sans attendre une refonte globale des listes dynamiques.

## 5. Courriels : préparation, validation et envoi

- Un modèle existant du moteur de templates fournit sujet et corps ; les variables proviennent de la demande et, sur demande, des fiches liées accessibles.
- Le même moteur de résolution sert à l'aperçu et à l'envoi ; variables manquantes clairement signalées, pas de placeholders irrésolus dans un email externe validé.
- Le composeur affiche et permet de modifier **destinataire, sujet, corps et pièces jointes** (celles-ci nécessitent une extension : le transport actuel ne les prend pas en charge).
- Le courriel métier externe, initial ou de relance, **ne peut être envoyé sans une action de validation humaine explicite**.
- Conserver un snapshot du destinataire, du sujet, du contenu et des pièces jointes approuvés, ainsi que date/heure, auteur, résultat d'envoi et erreurs. Les modifications ultérieures des fiches sources ne réécrivent pas l'historique.
- Les notifications **internes** peuvent rester automatiques.
- Vérifier les permissions au moment de l'approbation et de l'envoi. Les tâches en attente d'approbation ne sont jamais éligibles à l'envoi automatique.
- Gérer les incertitudes SMTP : ne pas relancer aveuglément un envoi dont la remise au serveur SMTP a peut-être réussi sans persistance locale de la confirmation.

## 6. Suivi et relances

- **Départ** : date/heure de confirmation de l'envoi initial, pas la création de la demande ni la simple approbation.
- **Première relance** : échéance à **J+7 jours ouvrés**. Convention par défaut à confirmer : lundi–vendredi hors jours fériés français ; le fuseau horaire utilisé doit être explicite (France métropolitaine).
- À échéance, si la demande est toujours en attente et qu'aucun devis n'a été lié, créer **une seule** action/tâche « relance à valider » et notifier en interne l'utilisateur responsable.
- Vue « Mes actions »/tableau de bord existant à réutiliser si possible : demandes échues, en attente d'approbation, devis reçus à examiner.
- L'utilisateur peut **envoyer après prévisualisation**, **reporter** ou **ignorer** l'échéance ; conserver décision, auteur et date.
- Avant l'envoi effectif, recontrôler l'état de la demande et la présence du document attendu. Bloquer une relance devenue injustifiée.
- À réception du devis ou à annulation de la demande : annuler/suspendre les relances programmées et celles en attente d'approbation.
- Après une relance envoyée, ne pas supposer de cadence infinie : politique des relances suivantes **à définir**, sans envoi implicite. Par défaut MVP : proposer une nouvelle échéance à l'utilisateur, sans nouvelle relance automatique tant que sa politique n'est pas confirmée.
- Les tâches internes et courriers de relance doivent être idempotents, non réactivés à chaque balayage du planificateur.

## 7. Réception documentaire et suite du processus

- La réception est matérialisée par un lien vers un fichier dans la rubrique documentaire dédiée ; **l'arrivée d'un email chez ITops n'est pas actuellement détectée automatiquement**.
- L'événement documentaire inscrit la date si nécessaire, passe à `Devis reçu`, arrête les relances et conserve l'historique.
- En `suivi_uniquement`, aucune Commande ou Engagement n'est créé.
- En `circuit_achat`, **à réception du devis** (sans attendre son acceptation), créer ou retrouver :
  - une `commandes_informatiques` avec `statut=Brouillon` ;
  - une `engagements` au statut de préparation (valeur `En préparation` à ajouter si validée, sinon `Brouillon` comme repli temporaire documenté).
- Préparer les champs obligatoires : objet, catégorie/priorité/mode d'achat pour Commande ; référence unique et date de début pour Engagement. **La règle métier de génération de référence et de date de début doit être décidée avant activation**. Ne pas inventer des dates d'engagement officiel.
- Créer les relations Demande ↔ Commande, Demande ↔ Engagement et Commande ↔ Engagement, selon cardinalités réelles et sans duplication.
- Les données financièrement ambiguës restent à compléter manuellement : pas de transfert automatique d'un TTC vers un HT ni d'un devis ponctuel vers un montant annuel.
- Le même devis doit pouvoir être référencé par les fiches liées **sans dupliquer physiquement le binaire**, après correction de la contrainte d'unicité documentaire observée.
- Les actions de création doivent être **idempotentes** et robustes aux échecs partiels (commande créée, engagement échoué) : pouvoir reprendre sans créer de doublon.
- La préparation n'est ni une approbation de devis, ni l'émission d'un bon de commande, ni un engagement budgétaire/comptable officiel.

## 8. Principes transversaux

- Fonctions ajoutées **génériques** pour tout service No-Code : contexte de relations, templates, approbation d'emails, garde d'exécution, annulation de tâches, création de fiches interservices et mapping, lien documentaire multiple.
- Reprendre la sécurité existante, contrôler les droits de service et des documents côté serveur, traiter les relations absentes/multiples explicitement.
- Conserver les modules existants, leurs données, leurs règles et notifications opérationnelles ; migrations limitées et réversibles avec sauvegarde préalable.
- Ne pas faire de propagation automatique de règles en chaîne sans politique de prévention des boucles.
- La documentation du workflow doit être indépendante des IDs instables, sauf pour les IDs relationnels effectivement audités.

## 9. Critères d'acceptation de bout en bout

1. Une demande libre est créée sans relation Fournisseur ni Marché ; son email peut être préparé puis validé.
2. Une demande avec Fournisseur utilise ses coordonnées si renseignées ; sinon l'utilisateur peut renseigner et valider l'adresse avant envoi.
3. Une demande avec Marché facultatif affiche les valeurs autorisées des fiches liées ; aucun marché existant n'est requis pour le mode libre.
4. Aucun courriel externe n'est envoyé avant validation explicite, y compris après échéance de relance.
5. Le courriel approuvé envoyé est historisé avec son contenu réel, son destinataire et son résultat.
6. La première relance est proposée à J+7 ouvrés, sans doublons ; l'utilisateur reçoit une notification interne et peut valider, reporter ou ignorer.
7. L'association d'un Devis reçu annule les relances non envoyées, y compris celles en attente d'approbation.
8. En suivi uniquement, aucune Commande ni Engagement n'est créé.
9. En circuit d'achat, la réception crée une Commande Brouillon et un Engagement en préparation, liés ; rejouer l'événement ne crée aucun doublon.
10. Un échec partiel se corrige sans dupliquer la fiche déjà produite.
11. Les fiches existantes et les notifications classiques continuent de fonctionner.
12. Les accès non autorisés aux données liées, documents, approbations et emails sont refusés côté serveur.

## 10. Décisions restant à valider

- Sens exact de `En préparation` pour Engagements : nouvelle valeur ou maintien `Brouillon` ; règles de validations associées.
- Génération de `engagements.reference` et source légitime de `date_debut`.
- Valeurs obligatoires Catégorie/Priorité/Mode d'achat de la Commande lorsque la demande est sommaire.
- Définition des jours ouvrés : jours fériés, calendrier et traitement des échéances tombant pendant fermeture.
- Responsable des relances et stratégie après la première relance (délai, maximum, escalade).
- Pièces jointes aux courriels : indispensables dès V1 d'envoi ou à introduire avec une étape dédiée.
- Procédure après retrait/remplacement d'un devis déjà lié, surtout si des fiches ont été générées.
- Traitement des emails transmis depuis un fournisseur sans coordonnées initialement enregistrées.
- Correction des montants, des chaînes mal encodées et de la cardinalité Commande → Marché avant toute automatisation dépendante.
