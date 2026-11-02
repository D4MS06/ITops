# ITops — Plan incrémental : workflow demandes de devis

**État général :** P0 en cours de validation ; formulaire et paramètres No-Code dynamiques présents sur la branche dédiée
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

**État :** ◐ En cours de validation

- Vérifier les schémas MariaDB et propriétés des quatre services en lecture seule, puis valider la structure minimale de `Demandes de devis`.
- Préparer les champs, statut, option `suite_demande`, rubrique Devis reçu et relations facultatives vers Fournisseurs/Marchés, futures relations Commande/Engagement.
- Utiliser les sélecteurs relationnels existants ; ne pas développer de listes dynamiques supplémentaires pour ce lot.
- Identifier les règles existantes activables (notamment `document_linked` → date).
- Ne créer/configurer le service qu'après accord ; sauvegarder la configuration préalable ; ne modifier aucun code générique sans besoin démontré.

**Acceptation :** fiche indépendante enregistrable en mode libre ou référencé ; aucun marché requis ; rubrique de Devis reçu exploitable ; aucune régression.

### Lot 1 — Contexte générique des enregistrements et relations

**État :** ☐ À faire

- Étendre le résolveur des templates pour exposer les champs de la fiche source et d'une relation au maximum dans un premier temps.
- Résoudre la destination email à partir d'un champ lié (ou adresse libre validée) ; gérer relation manquante, multiple, donnée vide et permissions.
- Utiliser des identifiants stables et un sélecteur de variables lisible dans l'éditeur de templates ; préserver `{var}` et `{{var}}` existants.
- Séparer la résolution métier de l'envoi SMTP pour réemploi dans les futurs mappings interservices.

**Acceptation :** aperçu de variables correct, données relationnelles non dupliquées, erreurs explicites, tests de non-régression des templates/Monitoring.

### Lot 2 — Brouillon d'email et validation humaine

**État :** ☐ À faire

- Réutiliser templates, transport SMTP et tâches existantes ; persister snapshot rendu du destinataire, sujet, corps et décision d'approbation.
- Introduire un état ou indicateur `awaiting_approval` distinct des tâches expédiables ; prévisualiser, éditer, accepter, annuler.
- Prévoir l'extension de pièces jointes ou documenter son report après décision fonctionnelle.
- Empêcher toute exécution automatique d'un email externe non approuvé ; gérer envoi en doublon et état SMTP ambigu, erreurs persistantes et traçabilité.
- Envoi initial confirmé → événement exploitable et date d'envoi.

**Acceptation :** demande libre et référencée envoyables après approbation ; impossible d'envoyer sans approbation ; contenu envoyé auditable ; notifications internes existantes inchangées.

### Lot 3 — Échéances, notifications et relances conditionnelles

**État :** ☐ À faire

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

### Lot 5 — Action générique `create_record` et relations interservices

**État :** ☐ À faire

- Ajouter une action universelle de création de fiche cible avec mapping typé depuis fiche source, événement et relations.
- Vérifier côté serveur les droits et champs obligatoires du service cible.
- Introduire idempotence par identité d'origine et reprise sûre après échec partiel ; relation vers la nouvelle fiche dans le même traitement logique.
- Réutiliser relation Commande → Engagement (39) et lier Demande aux deux fiches.
- En `circuit_achat` et sur devis reçu : Commande `Brouillon` + Engagement en préparation ; aucune validation financière ou envoi BC automatique.
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
