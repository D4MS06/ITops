# Architecture du portail ITops

## Principe directeur

Les modules du portail doivent utiliser les composants, contrats et moteurs
mutualises existants. Une adaptation locale ne doit contenir que les donnees
propres au module (schema, endpoints adaptes ou callback de rafraichissement).

## Avant toute implementation

1. Rechercher le flux equivalent dans un module existant, en particulier
   Mail, Copieurs ou les services no-code.
2. Reutiliser son composant de presentation, son gestionnaire d'action et son
   moteur metier. Ne pas recreer une modale, un bouton ou un parseur similaire.
3. Generaliser le composant commun si un parametre ou un adaptateur manque.
   Ne creer un composant specifique qu'en l'absence reelle d'equivalent.

## Imports et inventaires

- Toute importation tabulaire passe par le moteur commun : selection de
  fichier, feuille, detection d'entete, apercu, mapping et politique de
  doublons.
- Les modules systeme fournissent un schema virtuel et des endpoints adaptes,
  sans dupliquer le parseur ou l'interface d'import.
- Les actions visibles (Importer, Exporter, Ajouter) sont generees avec les
  memes fabriques de boutons et de libelles dynamiques que les autres modules.

## Verification obligatoire

Avant un commit, verifier que la modification n'introduit pas de flux ou de
composant duplique, et que le module preserve le meme cycle de vie portail que
les modules de reference.
