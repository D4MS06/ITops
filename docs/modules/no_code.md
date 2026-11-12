# Services dynamiques no-code

## Role

Les services no-code permettent de definir des services, leurs champs, records, relations et listes partagees sans creer un module applicatif distinct. Le portail porte l'UI ; les routes `admin/custom-services` et les magasins MariaDB fournissent le contrat persistant.

## Architecture actuelle

Les definitions de service, de champ et de relation sont separees des records. Les valeurs variables de records restent gerees par le contrat de valeurs du service. Les relations declarent les liens autorises entre services et sont exploitees dans les fiches, les imports et les vues associees. Les listes partagees fournissent des valeurs reutilisables.

Les composants `shared_admin_*` et les mecanismes communs de Treeview, formulaires, import/export et permissions sont reutilises. Les annuaires Agents et Services consomment ce socle avec leurs adaptateurs de domaine.

L'apercu et l'application de l'import des fiches utilisent le droit effectif `import` du module. Le proprietaire le recoit personnellement sans role d'administration global. L'apercu reste accessible si aucune colonne n'est encore mappee, pour permettre la correction du mappage ; l'application refuse toujours un import sans fiche exploitable. La creation de champs par import exige le droit de configuration du module ; l'import d'identifiants exige le droit de gestion des identifiants.

L'export CSV des annuaires systeme Agents et Services utilise la projection de leurs donnees AD et manuelles, le generateur CSV commun et le droit `export` du module correspondant. L'action n'est affichee qu'avec ce droit. Le fichier inclut toutes les fiches visibles de l'annuaire, independamment des filtres de la vue courante.

L'export des inventaires propose aussi « Vue actuelle » : il reprend les lignes affichees avec leurs filtres, leur tri, les colonnes visibles dans leur ordre et les valeurs des colonnes de relations. Le selecteur « Afficher » offre « Tout » pour charger l'ensemble des lignes filtrees au-dela de 500 ; les modules personnalises sont charges par lots. Le serveur verifie le droit `export` avant que le navigateur construise le CSV. L'option « Export des données du module » conserve l'export historique. Les deux modes proposent un nom modifiable, par defaut `export_<nom du module>.csv`, et un choix du dossier via le selecteur de fichier lorsque le navigateur le prend en charge ; autrement le navigateur utilise son emplacement de telechargement configure.

## Fonctions confirmees

- definition, activation et gestion de dependances des services ;
- champs, relations et impact des relations ;
- records, enfants, recherche, filtres, import/export et doublons ;
- historiques et actions de relation exposees par les routes admin ;
- listes partagees, import/export de valeurs et droits de module.
- creation de definitions delegable via le droit « Gestion des modules personnalisés » ; la definition conserve le compte createur, affiche dans la colonne Auteur. La modification est ouverte au proprietaire et aux roles ayant `configure` sur ce module ; sa suppression reste reservee au proprietaire et aux administrateurs. Les administrateurs et `sa` peuvent gerer toutes les definitions.

Les droits effectifs d'un module actif combinent les droits partages de ses roles avec les droits complets de son proprietaire, accordes au compte et non au role. Le role `admin` donne tous les droits sur tous les modules actifs, meme sans attribution explicite dans chaque role. Un compte ou un module desactive ne donne pas acces aux fiches. Le droit `module_builder.create` sert uniquement a creer un nouveau module : son retrait ne supprime pas la propriete ni la gestion d'un module existant. Un nouveau module n'ajoute aucun droit au role du createur. Les anciens droits deja enregistres sur les roles sont conserves car leur origine automatique ou manuelle ne peut pas etre determinee sans ambiguite ; ils doivent etre revus dans l'administration des roles si un acces trop large est constate.

Les operations globales de gestion des roles, de sauvegarde et d'administration du socle exigent le role `admin` (`sa` reste le compte technique privilegie). Le module « Admin » ne confere pas ce role. Un gestionnaire d'utilisateurs delegue ne peut ni attribuer `admin`, ni modifier ou supprimer un compte qui le possede. Le marqueur historique de permissions `{}` garde l'acces complet des anciens liens de role ; une liste explicite `[]` ne confere aucun droit.

La desactivation d'un module peut desactiver tout son groupe de relations. Elle exige donc le droit de modifier la definition de chacun des modules touches avant d'enregistrer le changement ; le proprietaire d'un seul module ne peut pas agir sur les autres par effet de bord.

Une migration ponctuelle attribue `sa` aux modules personnalises dont le proprietaire est vide, sans remplacer un compte deja enregistre ; les modules systeme sont exclus. La creation refuse avec un conflit HTTP 409 un code de module deja utilise, meme en cas de creation concurrente.

## Evolutions proposees

Un index de recherche dedie, un audit no-code plus complet et une separation renforcee des credentials sont des pistes de roadmap, pas des garanties actuelles. Un editeur graphique de relations est egalement une specification archivee : les relations actuelles restent configurees par les contrats existants.
