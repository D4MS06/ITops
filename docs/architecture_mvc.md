# Architecture Web ITops

## Objectif
Ce document sert de reference pour les futures modifications du projet. Toute evolution doit respecter une architecture web centralisee, mutualisee et extensible:
- Le portail general est le point d'entree fonctionnel.
- Les modules, dont le module monitoring, heritent des comportements communs du portail et des couches partagees.
- Le code commun doit etre place au plus haut niveau raisonnable avant d'ajouter une logique specifique a un module.
- L'ancien contexte desktop/Tkinter ne doit plus guider les choix d'architecture du runtime actuel.

## Runtime Actuel
L'application est un runtime web unique:
- `FastAPI` expose les endpoints, la configuration UI, l'authentification et les donnees metier.
- `MariaDB` porte la persistance runtime.
- Le front est servi depuis `monitoring/web`.
- Les pages principales sont `portal.html`, `index.html` et `setup.html`.
- Le portail general (`portal.html` + `portal.js`) est la surface centrale.
- Le module monitoring (`index.html` + `app.js`) est un module specialise qui doit reutiliser les comportements partages.

## Couches
- `monitoring/api`: routes HTTP, schemas API, securite, orchestration mince.
- `monitoring/services`: logique metier, normalisation, policies, imports, actions.
- `monitoring/models`: modeles runtime en memoire quand necessaire.
- `monitoring/repositories`: acces donnees oriente domaine.
- `monitoring/storage`: persistance MariaDB, bootstrap schema, managers bas niveau.
- `monitoring/shared`: logique Python transversale, themes, compatibilite d'actions, utilitaires non lies a une page.
- `monitoring/web`: UI web, pages, CSS, JavaScript partage et JavaScript specifique.
- `monitoring/tests`: tests cibles sur logique metier, themes, API, parsing/import et regressions.

## Hierarchie Front
Le front doit etre pense dans cet ordre:
1. `app.css`: design system global, variables CSS, surfaces, boutons, tables, Treeview, menus, formulaires.
2. `shared_*.js`: comportements transverses utilises par plusieurs pages/modules.
3. `portal.js`: logique du portail general et administration des services/modules.
4. `app.js`: logique specifique au module monitoring.
5. `setup.js`: logique specifique installation, en reutilisant les partages disponibles.

Regle importante:
- Si une modification concerne plusieurs pages, le portail et le module monitoring, ou un comportement UI generique, elle doit etre faite dans `app.css`, `shared_ui.js`, `shared_menu.js`, `shared_api.js`, `shared_auth.js`, `shared_admin_*`, `shared_import.js` ou `shared_download.js`.
- `app.js` et `portal.js` ne doivent pas dupliquer un mapping, une politique UI ou une logique deja possible en partage.

## Mutualisation Et Heritage
La priorite architecturale est la mutualisation:
- Centraliser au niveau le plus haut possible.
- Faire heriter les modules via les fichiers `shared_*.js`.
- Garder les modules specialises uniquement pour leurs donnees, workflows et ecrans propres.
- Eviter les corrections locales qui produisent des differences entre portail, monitoring et setup.

Exemple de regle:
- Mauvais: corriger seulement `app.js` pour un probleme de theme du monitoring.
- Correct: corriger `shared_ui.js` ou `app.css`, puis laisser `portal.js`, `app.js` et `setup.js` heriter.

## Themes Et Charte Graphique
Les themes sont geres en deux niveaux:
- Serveur: `monitoring/shared/theme_manager.py` definit les palettes `light` et `dark`, les cles editables, les overrides et les aliases legacy.
- Front: `monitoring/web/shared_ui.js` applique les variables CSS via `applyThemeConfig(config)`.

Le futur editeur de charte graphique doit rester simple:
- Il modifie uniquement des couleurs.
- Il propose une palette pour le theme clair et une palette pour le theme sombre.
- Il ne modifie pas les ombres, rayons, espacements, animations, layout ou design structurel.
- Les couleurs liees restent liees pour limiter le nombre de choix.

Tokens couleur a privilegier:
- `interaction_hover_*`: hover boutons, hover menus contextuels, hover navigation, hover Treeview.
- `interaction_selected_*`: selection Treeview, selection de lignes et etats actifs proches.
- `accent_primary`: couleur d'accent principale.
- `app_bg`, `surface_bg`, `panel_bg`, `panel_hover_bg`: surfaces.
- `text_primary`, `text_secondary`, `text_muted`: textes.
- `control_*`: champs et controles.
- `tree_*`: tables et Treeview.
- `menu_*`: surfaces de menus.

Regles theme:
- Ne pas coder une couleur hover directement dans `app.js`, `portal.js` ou `setup.js`.
- Ne pas dupliquer le mapping CSS dans chaque page.
- Ajouter une nouvelle couleur seulement si elle a un sens semantique reutilisable.
- Si un hover bouton et un hover menu doivent avoir la meme couleur, les raccorder au meme token.
- Garder les anciens aliases seulement pour compatibilite, mais les deriver depuis les tokens centraux.

## API Et Services
Les routes API doivent rester minces:
- Validation des entrees.
- Controle d'acces.
- Appel aux services.
- Construction de reponses.

La logique metier doit rester dans `monitoring/services` ou dans un composant partage dedie:
- Import/export.
- Normalisation de schemas.
- Actions distantes.
- Policies d'autorisation.
- Transformation de donnees.

Eviter:
- Logique metier longue dans `monitoring/api/app.py`.
- Decisions de persistence dans le front.
- Couplage direct entre une route et une structure DOM.

## Synchronisation de sources externes

Les connecteurs de donnees externes sont transverses. Active Directory/LDAP est implemente comme un moteur de synchronisation partage : il valide la connexion et retourne des entrees normalisees, sans connaitre le module consommateur. Les modules (Utilisateurs, RH, Finance, parc) definissent ensuite leur mapping, leur identifiant externe stable et leur politique de creation/mise a jour/desactivation.

Les secrets de connexion restent dans le magasin de secrets et ne doivent jamais etre renvoyes par l'API ou inclus dans les journaux.

## UI Web
Regles UI:
- Le CSS global vit dans `app.css`.
- Les composants repetes doivent etre generes par les helpers partages.
- Les Treeview doivent passer par `window.NMPSharedUi.treeView.SharedTreeView` quand c'est applicable.
- Les menus doivent passer par `shared_menu.js` et les helpers shell de `shared_ui.js`.
- Les appels API communs doivent passer par `shared_api.js`.
- L'authentification/session doit passer par `shared_auth.js`.
- Les imports et downloads doivent passer par `shared_import.js` et `shared_download.js`.

Quand une UI differe entre portail et monitoring:
- Verifier d'abord si la difference est justifiee par le metier.
- Si ce n'est pas justifie, remonter la logique dans un fichier partage.
- Si c'est justifie, documenter la raison dans le code ou dans le nom de la fonction.

## Setup
`setup.html` et `setup.js` sont specifiques a l'installation, mais doivent heriter des elements globaux quand c'est possible:
- CSS global.
- Theme via `shared_ui.js`.
- Helpers API si necessaire.

La page setup ne doit pas devenir une deuxieme architecture UI.

## Tests
Toute evolution structurante doit etre accompagnee de tests cibles quand c'est possible:
- Tests Python pour themes, services, parsing, policies et API.
- Checks JS avec `node --check` pour fichiers modifies.
- Tests d'integration legers pour endpoints critiques.

Pour le theme:
- Tester les palettes `light` et `dark`.
- Tester les overrides par theme.
- Tester que les aliases heritent bien des tokens centraux.

## Regles Pour Agents Et Futures Modifications
Avant de modifier du code, appliquer cette sequence:
1. Identifier si le besoin concerne le portail general, un module specifique, ou un comportement transversal.
2. Si le besoin est transversal, modifier d'abord le niveau partage.
3. Si le module monitoring doit avoir le meme comportement que le portail, ne pas coder dans `app.js` en premier.
4. Verifier les fichiers `shared_*.js`, `app.css` et `theme_manager.py` avant d'ajouter une logique locale.
5. Conserver les modules locaux pour la logique propre au module uniquement.
6. Eviter la duplication entre `portal.js`, `app.js` et `setup.js`.
7. Mettre a jour ce document si une nouvelle regle architecturale durable est introduite.

Phrase directrice:
Centraliser au niveau portail/shared, faire heriter les modules, specialiser uniquement quand le besoin metier l'impose.
