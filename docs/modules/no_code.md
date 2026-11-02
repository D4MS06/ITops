# Services dynamiques no-code

## Role

Les services no-code permettent de definir des services, leurs champs, records, relations et listes partagees sans creer un module applicatif distinct. Le portail porte l'UI ; les routes `admin/custom-services` et les magasins MariaDB fournissent le contrat persistant.

## Architecture actuelle

Les definitions de service, de champ et de relation sont separees des records. Les valeurs variables de records restent gerees par le contrat de valeurs du service. Les relations declarent les liens autorises entre services et sont exploitees dans les fiches, les imports et les vues associees. Les listes partagees fournissent des valeurs reutilisables.

Les composants `shared_admin_*` et les mecanismes communs de Treeview, formulaires, import/export et permissions sont reutilises. Les annuaires Agents et Services consomment ce socle avec leurs adaptateurs de domaine.

## Fonctions confirmees

- definition, activation et gestion de dependances des services ;
- champs, relations et impact des relations ;
- records, enfants, recherche, filtres, import/export et doublons ;
- historiques et actions de relation exposees par les routes admin ;
- listes partagees, import/export de valeurs et droits de module.

## Evolutions proposees

Un index de recherche dedie, un audit no-code plus complet et une separation renforcee des credentials sont des pistes de roadmap, pas des garanties actuelles. Un editeur graphique de relations est egalement une specification archivee : les relations actuelles restent configurees par les contrats existants.
