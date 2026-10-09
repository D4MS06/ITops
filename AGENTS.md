# Philosophie de conception ITops

## Mutualisation par defaut

L'application est concue autour de composants, contrats et services partages.
Toute fonctionnalite doit reutiliser les mecanismes existants des lors que son
besoin est equivalent ou voisin. Cela s'applique a toute couche : interface,
etat client, actions, validation, API, metier, persistance, securite,
import/export, synchronisation, journalisation et tests.

La duplication de code, de presentation ou de comportement est interdite par
defaut. Une implementation locale ne peut contenir que les donnees propres a
son contexte et un adaptateur mince vers le mecanisme commun.

## Regle de decision

Avant de creer du code, rechercher l'abstraction, le flux ou le contrat deja
present dans le projet.

1. Reutiliser directement l'existant lorsqu'il couvre le besoin.
2. Etendre ou parametrer l'existant lorsqu'il ne manque qu'une variation.
3. Extraire un composant commun lorsqu'au moins deux usages sont comparables.
4. Creer une implementation specifique uniquement lorsqu'aucune generalisation
   raisonnable n'est possible ; documenter alors clairement cette contrainte.

Ne jamais recreer localement un bouton, une modale, un formulaire, un parseur,
un endpoint, une regle de validation ou une requete deja disponibles sous une
forme reutilisable.

## Architecture et evolution

- Les modules sont des consommateurs de l'architecture commune, pas des
  applications paralleles.
- Les ecarts entre modules doivent etre exprimes par configuration, schema,
  adaptateur ou callback, jamais par une copie du cycle de vie complet.
- Une correction doit reduire la dette de duplication et rapprocher les
  comportements equivalents, sans introduire une nouvelle exception locale.
- Les interfaces equivalentes utilisent les memes fabriques de composants,
  les memes conventions visuelles et les memes gestionnaires d'action.
- Lorsqu'un module expose un inventaire, il doit satisfaire le contrat
  d'inventaire commun (recherche, filtres, ajout, import, export, analyse des
  doublons et remise a zero des filtres lorsque ces actions sont pertinentes).
  Un module systeme retire seulement les actions interdites par son statut ; il
  ne remplace pas le composant d'inventaire par une interface parallele.

## Verification avant commit

Verifier explicitement que la modification :

1. ne duplique pas un composant ou une logique deja presente ;
2. reutilise ou generalise l'abstraction appropriee ;
3. preserve les contrats et le cycle de vie communs ;
4. ajoute des tests ou met a jour ceux qui couvrent le comportement partage.
