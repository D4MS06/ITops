# Architecture actuelle

## Runtime

ITops est une application web Python. `main.py` demarre FastAPI ; `monitoring/api/app.py` compose les routes, les dependances d'autorisation et les services. MariaDB est la persistance runtime. Le front statique est servi depuis `monitoring/web` : `portal.html` est la surface d'entree, `index.html` porte Monitoring et Equipements reseau, `setup.html` est reserve a l'installation.

## Couches

- `monitoring/api` : schemas HTTP, dependances de session et routes minces.
- `monitoring/services` : regles metier, synchronisations, stockage de configurations et policies.
- `monitoring/repositories` et `monitoring/storage` : acces MariaDB, migrations et magasins specialises.
- `monitoring/models` : modeles de domaine et etat runtime lorsque necessaire.
- `monitoring/shared` : services Python transversaux, notamment themes et compatibilite d'actions.
- `monitoring/web` : design system (`app.css`), bibliotheques `shared_*.js`, puis adaptateurs `portal.js`, `app.js` et `setup.js`.
- `monitoring/tests` : regressions de services, routes, stockage, import et contrats metier.

## Frontieres fonctionnelles

Le portail gere l'acces aux modules, l'administration et les services dynamiques. Monitoring consomme les donnees de supervision et l'inventaire reseau ; Equipements reseau reutilise le meme runtime avec son contexte d'inventaire. Les deux contextes partagent les contrats de device, de menus et de fichiers de configuration plutot que de se charger mutuellement.

Les modules no-code sont definis par leurs schemas et records persistants ; le portail les rend via les composants partages. Les annuaires et synchronisations Active Directory restent des services transversaux, pas une implementation locale par module.

## Flux importants

Les appels web passent par les helpers partages, puis les routes FastAPI appliquees aux permissions de session et de module. Les routes deleguent aux services et magasins. Les mutations de configuration sont persistees par les settings et reconsommees par les services runtime.

Les fichiers de configuration de devices sont geres par les routes `config-files` et le stockage dedie. `shared_device_config_files.js` unifie l'import ; `shared_config_storage.js` unifie le stockage distant et la planification. La synchronisation automatique est executee par le runner API selon les settings persistants.

Les sessions web utilisent une expiration glissante cote serveur. `shared_auth.js` suit l'activite utilisateur du portail et de Monitoring, renouvelle la session au plus une fois par minute pendant cette activite, puis verifie l'expiration aupres du serveur avant de deconnecter. La duree d'inactivite configuree reste appliquee meme si des requetes de fond ont prolonge la session serveur. Une erreur reseau transitoire ne supprime pas le jeton ; seul un refus de la session ITops l'invalide, pas un refus d'authentification d'une autre ressource.

## Extensions

Un besoin commun doit etre introduit dans `shared_*.js`, `app.css`, un service ou une policy partagee selon sa couche. Un module fournit seulement son contexte, ses donnees et ses callbacks. Les actions courtes utilisent la modale enfant de `shared_ui.js`; les vues longues restent dans leur espace de travail.

Les points d'entree a verifier avant une evolution sont `monitoring/api/app.py`, le service ou magasin correspondant, `monitoring/web/shared_*.js` et les tests du domaine.
