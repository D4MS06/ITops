# ITops — Plan incrémental : workflow demandes de devis

**État général :** P0, P1 et premier lot texte de P2 validés en recette locale.
**Référence fonctionnelle :** `DEMANDES_DEVIS_SPEC.md`
**Principe :** un lot à la fois ; audit ciblé → proposition → accord → code et tests → validation → mise à jour du présent plan.

## 1. État initial confirmé par les audits Codex

- Services No-Code réels actifs : `fournisseurs` (22 fiches ; aucune adresse email remplie), `marches` (0), `commandes_informatiques` (216), `engagements` (217).
- Relations et sélection de fiches liées déjà disponibles : pas besoin d'attendre un nouveau type de liste dynamique pour le premier workflow.
- Templates limités aux variables simples (`task.*`, `module.code`, `record.id`, etc.) ; relations non injectées ; destinataires dynamiques partiellement disponibles.
- Notifications `pending` envoyées automatiquement à échéance ; ni brouillon rendu persistant, ni validation humaine structurée, ni pièces jointes sortantes.
- Planificateur existant (cycle d'une minute) ; risques de réactivation et d'envoi de relances après réception faute de garde finale.
- Déclencheur `document_linked` utilisable et champ date préremplissable ; absence de `document_unlinked`, droits documentaires insuffisants sur certaines routes, chemin de stockage globalement unique.
- Moteur d'automatisation : `set_field`, ajout/retrait de relations, tâches ; **pas** de `create_record`, mapping ni chaîne automatisée interservices sûre.
- Commande `Brouillon` disponible ; Engagements `En préparation` absent, `reference` et `date_debut` obligatoires.
- Ne pas conclure que les scripts du dépôt reflètent la base en cours : s'appuyer sur le relevé MariaDB récent et recontrôler avant migration.

## 2. Prérequis bloquants et ordre d'exécution

| Prérequis | Conséquence | Responsable / moment |
|---|---|---|
| Définir une adresse email pour les fournisseurs ciblés ou permettre la saisie libre vérifiée | Bloque l'envoi effectif sinon | Avant tests d'envoi réel |
| Clarifier `engagements.reference` et `date_debut` | Bloque la création automatique valide | Avant Lot 5 |
| Décider du statut d'engagement en préparation | `En préparation` n'existe pas | Avant Lot 5 |
| Évaluer `montant_ht` / « Montant TTC » et `montant_annuel` | Évite des engagements erronés | Avant mapping des montants |
| Confirmer la cardinalité de la relation 31 | Évite associations indésirables | Avant Lot 5 |
| Vérifier les valeurs accentuées et les règles existantes | Risque de transitions/notifications défaillantes | Lors des tests ciblés |
| Règles de jours ouvrés, après-première-relance, responsable | Pour calcul/suivi précis | Avant Lot 4 |

## 3. Lots de développement

### Lot 0 — Configuration No-Code et contrats de données

**État :** validé en recette locale le 23 novembre 2026.

- Vérifier les schémas MariaDB et propriétés des quatre services en lecture seule, puis valider la structure minimale de `Demandes de devis`.
- Préparer les champs, statut, option `suite_demande`, rubrique Devis reçu et relations facultatives vers Fournisseurs/Marchés, futures relations Commande/Engagement.
- Utiliser les sélecteurs relationnels existants ; ne pas développer de listes dynamiques supplémentaires pour ce lot.
- Identifier les règles existantes activables (notamment `document_linked` → date).
- Ne créer/configurer le service qu'après accord ; sauvegarder la configuration préalable ; ne modifier aucun code générique sans besoin démontré.

**Acceptation :** fiche indépendante enregistrable en mode libre ou référencé ; aucun marché requis ; rubrique de Devis reçu exploitable ; aucune régression.

### Lot 1 — Contexte générique des enregistrements et relations

**État :** validé en recette locale le 24 novembre 2026. Dans Edge, le portail a été testé avec des réponses API simulées : insertion dans le sujet, aperçus libre et lié, masquage après modification et affichage d’une erreur de relation. L’API a été vérifiée séparément.

Dans « Modèles de messages », choisir le module et l’usage « Courrier préparé depuis une fiche ». Le sélecteur propose les champs déclarés de la fiche et des modules No-Code directement liés et lisibles. Pour vérifier le sujet, le corps et le destinataire, indiquer l’identifiant d’une fiche puis sélectionner un champ d’adresse ou saisir une adresse libre. La sélection du destinataire sert à cet aperçu. L’aperçu ne crée aucune tâche.

Le contrôle API couvre les deux syntaxes de variables, les droits aux deux extrémités du lien, les relations absentes ou multiples et les adresses vides ou invalides. Les champs réservés aux identifiants sont exclus du catalogue et du rendu. Une demande libre se prévisualise sans consulter les relations. Les automatisations excluent les modèles réservés à l’aperçu. Suite complète du 24 novembre 2026 avec le test MariaDB activé : 411 tests réussis.

- Étendre le résolveur des templates pour exposer les champs de la fiche source et d'une relation au maximum dans un premier temps.
- Résoudre la destination email à partir d'un champ lié (ou adresse libre validée) ; gérer relation manquante, multiple, donnée vide et permissions.
- Utiliser des identifiants stables et un sélecteur de variables lisible dans l'éditeur de templates ; préserver `{var}` et `{{var}}` existants.
- Séparer la résolution métier de l'envoi SMTP pour réemploi dans les futurs mappings interservices.

**Acceptation :** aperçu de variables correct, données relationnelles non dupliquées, erreurs explicites, tests de non-régression des templates/Monitoring.

### Lot 2 — Brouillon d'email et validation humaine

**État :** lot texte validé en recette locale le 24 novembre 2026. Les pièces jointes sont reportées conformément à la décision fonctionnelle.

Depuis une fiche enregistrée, « Prévisualiser un courrier » ouvre le composeur. L’utilisateur sélectionne un modèle actif du module, charge son texte, ajuste le destinataire, le sujet et le message, puis enregistre le brouillon ou choisit « Valider et envoyer ». Le modèle initial « Demande de devis » utilise l’objet et la description du besoin. Sa configuration reproductible se trouve dans `scripts/configure_demande_devis_mail.sql`.

Le brouillon réutilise la persistance et le journal des demandes de suivi. Seule l’approbation réserve l’envoi sous verrou MariaDB, après vérification des droits et de la révision. Le contenu approuvé, son auteur, la date de remise confirmée (`sent_at`) et les événements restent consultables. Après une remise incertaine, une vérification en messagerie permet de confirmer le résultat. Le planificateur des notifications ne consomme pas ces brouillons.

La sauvegarde accepte un brouillon dont le destinataire reste à compléter. La validation exige une adresse valide. Lorsque le courrier contient des données issues d’un module lié, le composeur et le suivi contrôlent le droit de lecture de ce module. MariaDB renvoie la révision enregistrée dans la transaction de la demande.

Recette locale : choix du modèle et ajustements dans Edge avec API simulée. Tests API sur tables temporaires MariaDB avec transport SMTP simulé : annulation, réouverture, sauvegarde sans destinataire, refus d’une révision périmée, retrait des droits, validation répétée et remise incertaine. Une panne d’enregistrement après remise SMTP a également été simulée : la confirmation manuelle après vérification ne réexpédie pas le courrier. Suite complète : 414 tests réussis.

- Réutiliser templates, transport SMTP et tâches existantes ; persister snapshot rendu du destinataire, sujet, corps et décision d'approbation.
- Introduire un état ou indicateur `awaiting_approval` distinct des tâches expédiables ; prévisualiser, éditer, accepter, annuler.
- Prévoir l'extension de pièces jointes ou documenter son report après décision fonctionnelle.
- Empêcher toute exécution automatique d'un email externe non approuvé ; gérer envoi en doublon et état SMTP ambigu, erreurs persistantes et traçabilité.
- Envoi initial confirmé → événement exploitable et date d'envoi.

**Acceptation :** demande libre et référencée envoyables après approbation ; impossible d'envoyer sans approbation ; contenu envoyé auditable ; notifications internes existantes inchangées.

### Lot 3 — Échéances, notifications et relances conditionnelles

**État :** ☐ À faire

Socle de routage ajoute le 27 novembre 2026 : abonnement explicite par role et module, profil Complet et cases detaillees, resolution des Agents actifs a l'execution et blocage visible sans repli SMTP global. Voir `docs/modules/no_code.md`. Ce socle ne calcule pas encore J+7 ouvres et n'ajoute pas le parcours partage de validation/report/ignorance des relances.

- Calculer la première échéance J+7 ouvrés depuis l'envoi confirmé, avec calendrier validé.
- Étendre `notification_tasks` : garde au dernier instant, tâche à approuver, report/ignorance, annulation par automatisation, suivi du résultat, protection contre la réactivation par upsert.
- Afficher la relance dans une vue/tâche existante et produire une notification interne, sans email externe automatique.
- Contrôle des droits avant validation, unicité par demande/échéance et exclusion des demandes terminées/annulées.
- Stratégie des relances suivantes configurable ou action explicite, pas de répétition infinie par défaut.

**Acceptation :** une seule proposition à J+7 ouvrés ; destinataire informé via ITops ; envoi uniquement après accord ; report/ignorance historisés ; aucune relance après devis reçu.

### Lot 4 — Réception documentaire et arrêt du suivi

**État :** ☐ À faire

- Exploiter `document_linked` sur rubrique Devis reçu : date, statut, annulation des relances en attente.
- Corriger l'accès et les permissions sur l'association documentaire ; traiter retrait/remplacement sans rollback automatique dangereux.
- Permettre, avec une extension générique, la référence à un même fichier physique depuis plusieurs fiches si indispensable au Lot 5.
- Prévoir une séparation claire référence texte/document lié et une traçabilité de l'événement.

**Acceptation :** une liaison de devis déclenche une seule réception ; relances bloquées/annulées, y compris celles préparées ; accès document sécurisé.

### Lot 5 — Création de fiche liée et relations interservices

**État :** création et mise à jour de la commande configurées en local le 25 novembre 2026. L’engagement et le partage documentaire restent à développer.

Dans le module source, étape Automatisations, choisir **Créer ou mettre à jour une fiche liée**. Sélectionner une relation sortante à cible unique (un à un ou plusieurs à un), le comportement si la cible manque, puis les champs source ou valeurs fixes à reprendre. Chaque champ cible peut être conservé, complété si vide ou modifié. Une condition sur la fiche existante limite les transitions autorisées.

Pour **Commande → Engagement**, plusieurs commandes peuvent partager le même engagement. Une modification porte sur cette fiche commune. Si la commande n’a aucun lien et que la création est activée, la règle crée un nouvel engagement pour cette commande. Le rattachement à un engagement existant se fait par la relation.

Le brouillon préparé fait passer la demande de Brouillon à À valider. La confirmation du courrier conserve la première date d’envoi et passe la demande en attente du devis. Une commande liée encore en Brouillon passe à Demande de devis. La réception documentaire sur une demande non annulée conserve la première date de réception. En circuit d’achat, elle crée une commande au statut Devis reçu ou actualise une commande encore en Brouillon ou Demande de devis. Les autres statuts de commande sont conservés. En suivi uniquement, la réception intervient sur la demande seule.

Les règles utilisent le compte qui effectue l’action et les droits de lecture, création ou modification du module cible. Lors d’une réception, la liaison au document, les changements de fiches, le lien entre modules et le journal partagent la transaction MariaDB. Un champ requis manquant est signalé à l’utilisateur qui peut compléter la demande puis relier le document. Installation locale reproductible via `python -m scripts.configure_devis_automations`.
- Vérifier côté serveur les droits et champs obligatoires du service cible.
- Introduire idempotence par identité d'origine et reprise sûre après échec partiel ; relation vers la nouvelle fiche dans le même traitement logique.
- Réutiliser relation Commande → Engagement (39) et lier Demande aux deux fiches.
- En circuit d’achat, le statut initial de la commande à réception est **Devis reçu**. La préparation de l’engagement relève d’une étape ultérieure.
- Gérer la règle de référence/date de début de l'engagement validée avant activation. Ne pas mapper automatiquement HT/TTC ou montant annuel incertain.
- Document lié référencé dans les fiches cibles sans duplication binaire, après correction générique nécessaire.

**Acceptation :** deux fiches liées créées une fois ; événement répété sans doublon ; reprise d'échec partiel ; suivi uniquement sans créations ; champs financiers cohérents.

### Lot 6 — Parcours complet et stabilisation

**État :** ☐ À faire

- Scénarios de bout en bout : libre sans fournisseur/marché ; avec fournisseur ; avec marché ; suivi uniquement ; circuit d'achat ; annulation ; réception pendant validation d'une relance ; document retiré ; erreurs SMTP ; reprise après panne.
- Vérifier régressions sur 216 Commandes et 217 Engagements existants et sur les automatisations des échéances.
- Compléter uniquement les documents d'architecture pertinents ; bilan des tests et limites ; aucune réécriture des historiques.

**Acceptation :** critères de `DEMANDES_DEVIS_SPEC.md` satisfaits et démontrés en environnement de test.

## 4. Règles de travail Codex

1. Lire `AGENTS.md` et uniquement la documentation pertinente au lot en cours.
2. Pour chaque lot : inventaire ciblé des fonctionnalités existantes → proposition courte et fichiers impactés → attente d'accord → implémentation limitée → tests → bilan.
3. Ne pas modifier le lot suivant par anticipation ni reconstruire le moteur No-Code.
4. Ne pas créer de règles codées pour les achats ; toute nouvelle capacité est générique et configurable.
5. En cas de doute sur un choix métier, inscrire le blocage ici et demander validation au lieu d'inventer un comportement.
6. Après validation d'un lot, mettre à jour seulement son état, les tests, les décisions et le prochain lot, sans longues narrations ni duplication de la SPEC.
7. Adapter l'ordre uniquement avec justification technique explicite, sans perdre les critères d'acceptation.

## 5. Journal de suivi (à tenir brièvement)

| Date | Lot | Statut | Tests / décision / blocage |
|---|---|---|---|
| 2026-10-16 | Cadrage | Spécifié | Attente validation des deux fichiers et décisions de la SPEC §10 |
| 2026-11-23 | Lot 0 | Validé en recette locale | Configuration et parcours vérifiés ci-dessous. |
| 2026-11-24 | Lot 1 | Validé en recette locale | API et régressions vérifiées, parcours de l’éditeur contrôlé dans Edge. |

### Recette du lot 0 sur main, 23 novembre 2026

Le module actif `demandes_de_devis` possède 18 champs. La suite proposée à la création est « Suivi uniquement ». « Circuit d'achat » est sélectionnable. Catégorie, priorité et mode d'achat reprennent les listes de Commandes et restent facultatifs à ce stade. Les relations vers Commande et Engagement sont facultatives et de cardinalité un à un.

La rubrique « Devis reçu » est ancrée sur `reference_devis` et utilise le stockage « Devis Informatique » avec un dossier par fiche. Une liaison explicite renseigne `date_reception_devis` si elle est vide. Les nouveaux dépôts des utilisateurs de modules utilisent un dossier isolé par module, fiche et rubrique. Rejouer la liaison conserve son identifiant. Un fichier déjà associé à une autre fiche ou rubrique reste sur sa fiche d’origine. La consultation des fichiers déjà liés dans les anciens dossiers reste soumise au droit de lecture du module.

La liaison et son automatisation s’enregistrent dans une même transaction MariaDB, après verrouillage de la fiche. La recette sur tables temporaires vérifie l’annulation après un échec d’écriture de la fiche ou du journal, puis la reprise et la répétition sans doublon. Le fichier déposé reste disponible pour la reprise.

Les trois créations via l’API (libre, fournisseur sans marché, fournisseur avec marché) ont été relues dans MariaDB. Le dépôt, la liaison, la date et le téléchargement ont été vérifiés sur un répertoire temporaire. La transaction de recette a été annulée et les trois demandes initiales comparées. Le chemin SMB configuré était accessible en lecture. La recette ne couvre pas un dépôt sur le SMB avec le compte du service déployé.

Sauvegarde locale préalable : `exports/devis_config_avant_phase0_20261123_132146.json` (définition et relations). Les règles externes d’envoi, de relance et de création de fiches relèvent des lots suivants.
