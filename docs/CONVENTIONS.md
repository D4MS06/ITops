# Conventions techniques

## Contrats communs

Chercher d'abord dans `monitoring/web/shared_*.js`, `monitoring/services` et `monitoring/storage`. Les consommateurs utilisent des adaptateurs minces. Les contrats d'inventaire, de Treeview, de menu, de modalite, d'import, de telechargement et d'authentification ne sont pas recopies dans un module.

Les composants UI communs utilisent `app.css` et `shared_ui.js`. Les menus passent par `shared_menu.js`; les appels HTTP et echappements par `shared_api.js`; la session par `shared_auth.js`. Les formulaires compacts sont affiches dans une modale enfant ; un inventaire ou editeur riche garde son contexte de travail.

## API, donnees et securite

Une route FastAPI valide, applique les dependances d'acces puis delegue. Une regle metier, une normalisation ou une synchronisation vit dans un service ; la persistence vit dans un repository ou un manager. Les donnees entrantes sont validees aux frontieres. Les secrets restent dans les mecanismes existants et ne sont jamais retournes, copies dans la documentation ou journalises.

Les changements de schema et de persistance doivent respecter les migrations et compatibilites MariaDB existantes. Ne pas utiliser le front comme source de verite pour une regle de securite ou de persistence.

## Etat, erreurs et UX

Un composant est responsable de son etat local ; un etat partage possede un contrat explicite. Une erreur utilisateur est normalisee et affichee dans le contexte de l'action. Ne pas masquer une erreur par un delai, une interception ou une exception specifique a un module. Conserver le contexte appelant pour les actions courtes.

## Tests et documentation

Ajouter ou adapter des tests de comportement lorsque le contrat change. Executer les controles adaptes : tests Python pour services/API et `node --check` pour JavaScript modifie. Documenter les decisions non evidentes, les limites et les migrations dans le document de domaine ou d'architecture unique. Une specification future est explicitement identifiee comme telle.
