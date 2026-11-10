# Services dynamiques no-code

## Role

Les services no-code permettent de definir des services, leurs champs, records, relations et listes partagees sans creer un module applicatif distinct. Le portail porte l'UI ; les routes `admin/custom-services` et les magasins MariaDB fournissent le contrat persistant.

## Architecture actuelle

Les definitions de service, de champ et de relation sont separees des records. Les valeurs variables de records restent gerees par le contrat de valeurs du service. Les relations declarent les liens autorises entre services et sont exploitees dans les fiches, les imports et les vues associees. Les listes partagees fournissent des valeurs reutilisables.

Les composants `shared_admin_*` et les mecanismes communs de Treeview, formulaires, import/export et permissions sont reutilises. Les annuaires Agents et Services consomment ce socle avec leurs adaptateurs de domaine.

L'export CSV des annuaires systeme Agents et Services utilise la projection de leurs donnees AD et manuelles, le generateur CSV commun et le droit `export` du module correspondant. L'action n'est affichee qu'avec ce droit. Le fichier inclut toutes les fiches visibles de l'annuaire, independamment des filtres de la vue courante.

L'export des inventaires propose aussi « Vue actuelle » : il reprend les lignes affichees avec leurs filtres, leur tri, les colonnes visibles dans leur ordre et les valeurs des colonnes de relations. Le selecteur « Afficher » offre « Tout » pour charger l'ensemble des lignes filtrees au-dela de 500 ; les modules personnalises sont charges par lots. Le serveur verifie le droit `export` avant que le navigateur construise le CSV. L'option « Export des données du module » conserve l'export historique. Les deux modes proposent un nom modifiable, par defaut `export_<nom du module>.csv`, et un choix du dossier via le selecteur de fichier lorsque le navigateur le prend en charge ; autrement le navigateur utilise son emplacement de telechargement configure.

## Fonctions confirmees

- definition, activation et gestion de dependances des services ;
- champs, relations et impact des relations ;
- records, enfants, recherche, filtres, import/export et doublons ;
- historiques et actions de relation exposees par les routes admin ;
- listes partagees, import/export de valeurs et droits de module.
- creation, modification et suppression des definitions delegables via le droit « Gestion des modules personnalisés » ; la definition conserve le compte createur, affiche dans la colonne Auteur de la gestion des modules. Ce compte doit posseder le droit de creation pour gerer ses modules, en plus du droit de modification ou suppression correspondant. Les administrateurs et `sa` peuvent gerer toutes les definitions.

Une migration ponctuelle attribue `sa` aux modules personnalises dont le proprietaire est vide, sans remplacer un compte deja enregistre ; les modules systeme sont exclus. La creation refuse avec un conflit HTTP 409 un code de module deja utilise, meme en cas de creation concurrente.

## Evolutions proposees

Un index de recherche dedie, un audit no-code plus complet et une separation renforcee des credentials sont des pistes de roadmap, pas des garanties actuelles. Un editeur graphique de relations est egalement une specification archivee : les relations actuelles restent configurees par les contrats existants.
