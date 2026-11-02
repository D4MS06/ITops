# Instructions Codex - ITops

## Principes

ITops repose sur des contrats, services et composants partages. Reutiliser l'existant est la regle : une implementation locale ne porte que ses donnees propres et un adaptateur mince. Avant de creer quoi que ce soit : reutiliser, etendre ou parametrer, extraire un composant commun si plusieurs usages sont etablis ; ne specialiser qu'en dernier recours et documenter la raison.

Les modules consomment l'architecture commune. Une interface, une action, une validation, une route, un acces aux donnees ou un flux equivalent ne doit pas etre duplique. Les inventaires reutilisent le contrat commun quand il est pertinent : recherche, filtres, ajout, import, export, doublons et remise a zero. Un statut systeme retire seulement les actions interdites.

## Documentation et analyse

Au debut d'une tache, lire `docs/INDEX.md` si une orientation est necessaire, puis seulement les documents utiles. Verifier ensuite le code concerne : la documentation decrit l'intention, le code confirme l'etat reel. Lire `docs/ARCHITECTURE.md` avant un changement transversal, les conventions avant de creer un contrat, et le document du domaine avant une evolution fonctionnelle. Ne pas recharger inutilement un document deja consulte dans la meme tache.

Diagnostiquer la cause racine avant toute correction : responsabilites, etat, cycle de vie, contrats, circulation des donnees, persistance, autorisations et erreurs. Les contournements locaux, temporisations arbitraires, surcharges CSS isolees et duplications ne sont pas des corrections. Une exception temporaire exige une justification, une limite et un retrait planifie.

## Implementation

Limiter le changement au besoin autorise. Preserver les interfaces publiques, la securite, les permissions, les secrets et les donnees. Les routes restent minces ; la logique metier appartient aux services ou aux composants partages. Valider les entrees aux frontieres et ne pas journaliser de secret.

Pour l'interface, utiliser `app.css` et les fabriques de `shared_*.js`. Une action courte et autonome s'ouvre dans une modale enfant partagee qui conserve le contexte appelant. Une vue longue, un inventaire, un arbre ou un editeur complet utilise son espace de travail. Une action compacte ne charge jamais un autre module ou une iframe uniquement pour afficher un formulaire.

## Donnees et securite

Conserver les autorisations, validations et conventions de transaction existantes. Ne jamais exposer de secret ni utiliser le front comme source de verite pour une regle de securite ou de persistance. Les imports, exports et synchronisations reutilisent leurs services et validations. Ne pas supprimer, purger, deplacer ou ecraser des donnees en dehors du besoin explicite.

## Verification et documentation

Apres chaque modification, executer les verifications pertinentes, y compris les consommateurs d'un contrat partage. Les tests doivent couvrir un comportement utile, nominal et d'erreur lorsque necessaire ; ne jamais annoncer un test non execute. Mettre a jour uniquement le document impacte, sans recreer un suivi equivalent ni presenter un projet comme implemente.

Avant un commit, verifier : absence de duplication, respect des contrats et du perimetre, securite, tests adaptes, documentation coherente et absence de fichiers temporaires ou secrets. Ne pas committer automatiquement sans demande explicite.

## Communication

Signaler de facon concise les fichiers modifies, les mecanismes reutilises, les verifications executees et les limites restantes. Distinguer les faits verifies des hypotheses et du travail futur.
