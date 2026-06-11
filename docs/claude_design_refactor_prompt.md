# Instruction d'utilisation

Ce document contient déjà le contexte projet et l'audit UX/UI initial.
Ne refais pas l'audit global sauf demande explicite.
Utilise ce document comme base de travail pour appliquer les phases de refonte.

Pour l'itération actuelle, applique uniquement la phase demandée par l'utilisateur.
Si la phase demandée est la phase 1, ne lis que :
- ce document
- monitoring/web/app.css

Ne lis pas app.js, portal.js, les fichiers backend ou l'ensemble du projet sauf nécessité justifiée.
Avant toute modification, indique précisément les fichiers que tu comptes modifier et attends validation.

Application: ITops, supervision reseau web/API pour switches, serveurs et services IT.

Stack:
- Backend Python 3.12.
- API FastAPI dans `monitoring/api`.
- Services metier dans `monitoring/services`.
- Persistance MariaDB dans `monitoring/storage` et repositories.
- Interface web vanilla HTML/CSS/JavaScript dans `monitoring/web`.
- Runtime web unique: pas de dependance Tkinter dans le runtime.

Architecture obligatoire:
- `monitoring/api`: routes HTTP, validation, securite, appels services.
- `monitoring/services`: logique metier, normalisation, policies.
- `monitoring/models` et `monitoring/storage`: donnees runtime et persistance.
- `monitoring/web`: UI web uniquement.
- `monitoring/shared`: utilitaires transverses non lies a une UI particuliere.

Regles d'architecture:
- Ne pas deplacer la logique metier vers le front.
- Ne pas ajouter de dependance framework front sans justification forte.
- Ne pas dupliquer les composants deja mutualises.
- Toute refonte design doit rester compatible avec les fichiers HTML/JS existants.
- Les changements UI doivent privilegier `app.css` et les helpers mutualises avant de modifier massivement `app.js` ou `portal.js`.

Fichiers UI principaux:
- `monitoring/web/app.css`: theme global, layout, dashboard, tables, modales, portail, setup.
- `monitoring/web/index.html`: page monitoring, auth, dashboard, inventaire, detail, modales, menus.
- `monitoring/web/portal.html`: portail modules IT, auth, cartes modules, menus.
- `monitoring/web/setup.html`: assistant premiere installation.
- `monitoring/web/app.js`: orchestration monitoring, dashboard, inventaire, modales, menus, scan reseau.
- `monitoring/web/portal.js`: portail, admin, services no-code, listes partagees.
- `monitoring/web/shared_ui.js`: composants mutualises treeview, modales, menus, boutons, dashboard editor.
- `monitoring/web/shared_menu.js`: menus communs.
- `monitoring/web/shared_api.js`: requetes API, token bearer, erreurs.
- `monitoring/web/shared_auth.js`: authentification et contexte session.
- `monitoring/web/shared_admin_ui.js`: markup admin mutualise.
- `monitoring/web/shared_admin_store.js`: cache/store admin.
- `monitoring/web/shared_admin_controller.js`: actions admin mutualisees.

Taille approximative du contexte UI:
- Fichiers UI/design utiles: environ 220k tokens.
- Projet source/docs/tests complet filtre: environ 460k tokens.
- Recommandation cout: commencer par les fichiers UI ci-dessus, pas tout le projet.

## Audit synthetique initial

Forces:
- Architecture web claire et documentee.
- Mutualisation deja en place: API, auth, menus, treeview, modales, boutons et admin UI.
- CSS centralise dans un seul fichier, ce qui permet une refonte visuelle sans toucher au backend.
- Parcours fonctionnels couverts: auth, portail, monitoring, inventaire, setup, admin, services no-code.
- Responsive deja prevu avec breakpoints `1200px`, `900px`, `820px`.
- Support `prefers-reduced-motion` present sur l'animation du logo.

Problemes design/ergonomie observes:
- Design encore tres "tableur/admin brut": beaucoup de grilles, bordures, controles compacts, peu de hierarchie visuelle.
- Accent violet (`--accent: #7c3aed`) peu coherent avec un outil de supervision reseau/NOC; preferer une direction plus operationnelle.
- Plusieurs zones utilisent des libelles courts ou techniques (`Cfg`, `Pret`, `Types monitorises`, `Vue detaillee`) qui peuvent etre clarifies.
- Les tables affichent des colonnes sensibles ou lourdes (`Mot de passe`, `Login`) dans les vues principales; cela surcharge et pose un risque UX/securite.
- Le topbar et les toolbars accumulent menus, session, actions et navigation dans une zone dense.
- Les cartes dashboard restent peu expressives: statuts online/offline peu mis en scene, priorite visuelle faible pour les alertes.
- Les modales nombreuses risquent une experience incoherente si chaque rendu local ajoute son propre markup.
- `app.js` et `portal.js` sont tres volumineux: risque de refonte par duplication plutot que par composants mutualises.
- `app.css` reference des variables non declarees: `--text-main`, `--line-soft`, `--text-muted`. Il faut soit les declarer dans `:root`, soit remplacer par les variables existantes (`--text`, `--line`, `--muted`).
- Quelques chaines visibles semblent mal encodees dans les fichiers HTML/JS ou dans l'affichage terminal. Verifier l'encodage UTF-8 avant modification.

Priorites de refonte:
- Priorite 1: clarifier la supervision operationnelle: alertes, etats, inventaire, actions critiques.
- Priorite 2: harmoniser le systeme visuel via variables CSS et composants mutualises.
- Priorite 3: reduire la densite des ecrans sans perdre les fonctions admin.
- Priorite 4: ameliorer mobile/tablette, tables larges et modales.
- Priorite 5: corriger les incoherences CSS et libelles visibles.

## Prompt principal a envoyer a Claude

Tu es charge d'un audit UX/UI et d'une refonte ergonomique de l'application ITops.

Contexte:
- ITops est une application web/API de supervision reseau pour switches, serveurs, services IT et inventaire.
- L'application est operationnelle et utilise une architecture mutualisee.
- Le backend Python/FastAPI et les services metier ne doivent pas etre redesignes sauf si necessaire.
- La refonte doit respecter strictement l'architecture existante:
  - `monitoring/api` pour routes HTTP.
  - `monitoring/services` pour logique metier.
  - `monitoring/web` pour UI.
  - `monitoring/web/shared_*.js` pour composants mutualises.

Fichiers a analyser en priorite:
- `docs/architecture_mvc.md`
- `README.md`
- `monitoring/web/app.css`
- `monitoring/web/index.html`
- `monitoring/web/portal.html`
- `monitoring/web/setup.html`
- `monitoring/web/shared_ui.js`
- `monitoring/web/shared_menu.js`
- `monitoring/web/shared_api.js`
- `monitoring/web/shared_auth.js`
- `monitoring/web/shared_admin_ui.js`
- `monitoring/web/app.js`
- `monitoring/web/portal.js`

Objectif de sortie:
1. Produire un audit ergonomique priorise.
2. Identifier les problemes de design, lisibilite, navigation, densite, responsive et accessibilite.
3. Proposer une direction artistique coherente pour un outil de supervision reseau professionnel.
4. Proposer un design system simple base sur les variables CSS existantes.
5. Lister les fichiers a modifier, dans l'ordre.
6. Proposer une strategie de refonte incrementalement testable.
7. Eviter toute duplication de composants deja mutualises.
8. Preserver les identifiants DOM utilises par JavaScript.
9. Preserver les endpoints API et la logique metier.
10. Signaler les risques de regression.

Contraintes fortes:
- Ne pas introduire React/Vue/Svelte/Tailwind.
- Ne pas renommer les IDs HTML sans verifier tous les usages JS.
- Ne pas casser `NMPSharedUi`, `NMPSharedApi`, `NMPSharedMenu`, `NMPSharedAuth`.
- Ne pas creer de nouveaux helpers locaux si un helper mutualise peut etre etendu.
- Ne pas mettre de logique metier dans `app.css`, HTML ou JS de rendu.
- Eviter les animations inutiles; elles doivent servir la comprehension.
- Respecter `prefers-reduced-motion`.
- Garder une interface utilisable en desktop et mobile.
- Garder les performances: pas de rendu DOM massif inutile.

Direction design souhaitee:
- Style: console d'exploitation IT/NOC moderne, claire, dense mais lisible.
- Ambiance: professionnelle, operationnelle, fiable.
- Eviter le design generique violet/blanc.
- Mettre en avant les statuts critiques:
  - offline/danger visible immediatement.
  - online/success lisible mais moins dominant.
  - idle/warning distinct.
- Dashboard: plus de hierarchie, cartes de synthese plus exploitables, alertes priorisees.
- Tables: lisibilite, colonnes utiles, actions secondaires moins bruyantes.
- Modales: structure homogene, actions primaires/secondaires claires.
- Setup: plus guide, moins formulaire brut.
- Portail: cartes modules plus lisibles avec statut/acces/action principale.

Demandes precises:
- Commence par un plan, pas par du code.
- Propose d'abord une refonte CSS/HTML minimale avant de toucher lourdement au JS.
- Indique quelles declarations CSS mutualisees ajouter/modifier dans `:root`.
- Indique quelles classes existantes peuvent etre reutilisees.
- Indique les classes nouvelles proposees et pourquoi.
- Signale les variables CSS manquantes (`--text-main`, `--line-soft`, `--text-muted`) et propose une correction.
- Verifie les textes mal encodes ou mojibake avant de modifier.
- Pour chaque changement propose, donne:
  - fichier concerne,
  - risque,
  - benefice UX,
  - niveau d'effort.

Format de reponse attendu:
1. Resume executif en 8 lignes maximum.
2. Audit priorise sous forme de tableau.
3. Direction design proposee.
4. Design system CSS propose.
5. Plan de refonte en 3 phases.
6. Liste precise des fichiers a modifier.
7. Prompts courts de suivi pour implementation phase 1, phase 2, phase 3.

## Prompt court pour implementation phase 1

Applique uniquement la phase 1 de la refonte UI ITops.

Contraintes:
- Modifier principalement `monitoring/web/app.css`.
- Ne pas toucher au backend.
- Ne pas renommer les IDs HTML.
- Ne pas dupliquer les helpers `shared_*.js`.
- Corriger les variables CSS manquantes.
- Harmoniser boutons, panels, cartes, badges, tables et modales.
- Garder le rendu responsive existant.
- Corriger uniquement les textes mojibake certains si tu les rencontres dans les fichiers modifies.

Avant modification:
- Liste les fichiers modifies prevus.
- Signale les risques.

Apres modification:
- Donne un diff summary.
- Donne les tests/verifications manuelles a faire.

## Prompt court pour implementation phase 2

Applique la phase 2: amelioration structurelle legere des pages monitoring/portail/setup.

Contraintes:
- Preserver tous les IDs DOM utilises par JS.
- Ne pas modifier les endpoints.
- Favoriser les classes CSS existantes ou mutualisees.
- Ne modifier `app.js` ou `portal.js` que si necessaire pour clarifier un rendu ou reutiliser un helper mutualise.
- Ne pas introduire de framework.

Objectifs:
- Clarifier topbar/navigation/actions.
- Rendre les cartes dashboard et portail plus exploitables.
- Ameliorer la hierarchie de l'inventaire et des statuts.
- Garder les modales coherentes.

## Prompt court pour implementation phase 3

Applique la phase 3: durcissement UX, accessibilite et reduction de dette.

Objectifs:
- Revoir focus visible, labels, aria, reduced motion.
- Verifier responsive mobile/tablette.
- Identifier les helpers a extraire vers `shared_ui.js`.
- Nettoyer les duplications entre `app.js` et `portal.js` uniquement si faible risque.
- Ajouter ou ajuster des tests si des comportements JS/API changent.

Contraintes:
- Pas de refonte metier.
- Pas de changement de schema ou endpoint.
- Pas de changement de stockage.

## Strategie de reduction de cout OpenRouter

Utilisation recommandee:
- Audit initial avec `anthropic/claude-opus-4.8` et contexte UI prioritaire uniquement.
- Implementation avec `anthropic/claude-sonnet-4.6`.
- Helpers/resumes avec Haiku.

Ne pas envoyer:
- `venv`, `venv312`, `.git`, `.idea`, `build`, `dist`, caches, logs.
- Tous les tests sauf si Claude modifie un comportement teste.
- Tout le backend si la demande porte seulement sur UI/design.

Envoyer a chaque iteration:
- Ce document.
- Les fichiers modifies dans l'iteration.
- Le diff courant.
- Les erreurs console/navigateur si disponibles.

Ne pas renvoyer a chaque iteration:
- L'ensemble de `app.js` et `portal.js` si la modification ne concerne que CSS/HTML.
- Le README complet, sauf pour rappeler le contexte produit.

Audit Réalisé :
Je vais lire les fichiers prioritaires indiqués dans le prompt pour produire un audit fondé sur le code réel, pas générique. Commençons par explorer la structure UI et lire les fichiers clés.Je vais lire les fichiers UI prioritaires pour réaliser l'audit. Commençons par le CSS (le plus important) et les pages HTML.Let me read the rest of the CSS and the key HTML files.Let me read the rest of the CSS and look at the key HTML/JS files.Let me check the total size of app.css and look at the modal/portal sections, plus inspect the HTML files for structure and IDs.Now let me look at the HTML files and a few shared JS files to understand the structure and DOM IDs.Now let me look at the portal and setup HTML, and check for mojibake/encoding issues.Now let me look at setup.html and check the middle section of the CSS for any other relevant patterns, plus check file sizes and mojibake.Now let me look at the shared UI components and the JS structure to understand mutualization and the dashboard/portal card rendering.Let me look at the global API namespaces exposed by the shared modules and check the README for product context.Maintenant je dispose d'assez de contexte (CSS complet, les 3 pages HTML, les helpers mutualisés `NMPShared*`, l'architecture MVC et le README). Voici le livrable demandé : audit, direction design et plan de refonte. **Aucun code n'est modifié.**
# Audit UX/UI & refonte ergonomique — ITops
## 1. Résumé exécutif (≤ 8 lignes)
ITops dispose d'une base saine : architecture web mutualisée claire (`NMPShared*`), CSS centralisé et responsive (breakpoints 1200/900/820). Le frein principal est visuel : look « tableur/admin brut », accent violet peu adapté à un outil NOC, statuts critiques pas assez prioritaires, et écrans denses (topbar/toolbars surchargées, tables exposant `Login`/`Mot de passe`). Trois bugs CSS certains : variables , , utilisées mais **non déclarées** dans (14 usages). La refonte recommandée est incrémentale et majoritairement CSS d'abord, puis HTML léger, sans toucher au backend ni aux IDs DOM. Risque global faible si l'on préserve IDs, classes structurantes et endpoints. Objectif : console d'exploitation IT moderne, lisible, opérationnelle. `--text-main``--text-muted``--line-soft``:root`
## 2. Audit priorisé

| # | Pri. | Problème | Fichier(s) | Risque actuel | Bénéfice UX | Effort |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | P1 | Variables CSS manquantes , , (14 usages) → couleurs `inherit`/transparentes imprévisibles `--text-main``--text-muted``--line-soft` | (l.578, 642, 1293, 1296, 1311-12, 1696, 1791, 1797, 1800, 1896, 2011, 2089, 2110) `app.css` | Rendu incohérent (texte/bordures), bug visuel certain | Cohérence immédiate | Faible |
| 2 | P1 | Statuts critiques peu hiérarchisés : badges discrets, offline/danger pas dominant sur cartes & tables | (, `.status-*`, `.stat-*`) `app.css``.dash-card` | Alertes manquées en supervision | Lecture NOC en 1 coup d'œil | Moyen |
| 3 | P1 | Colonnes sensibles `Login` / `Mot de passe` dans les vues principales (supervision + inventaire) | (`#devices-head`, `#inventory-head`), rendu dans `index.html``app.js` | UX surchargée + risque sécurité/affichage secrets | Tables épurées, secrets masqués | Moyen |
| 4 | P2 | Accent violet non opérationnel pour un outil réseau `#7c3aed` | () `app.css``--accent` | Image produit « générique » | Identité NOC pro | Faible |
| 5 | P2 | Topbar dense (titre + nav + session + actions + edit) empilés | / , `index.html``portal.html``.topbar``app.css` | Charge cognitive | Navigation claire | Moyen |
| 6 | P2 | Cartes dashboard peu expressives (peu de hiérarchie valeur/sous-titre/stats) | (`.dash-card*`) `app.css` | Synthèse faible | Cartes exploitables | Moyen |
| 7 | P3 | Libellés techniques/courts : `Cfg`, `Pret`, `Types monitorisés`, `Vue detaillee` | , `index.html``app.js` | Ambiguïté | Clarté | Faible |
| 8 | P3 | Modales : structure correcte mais actions primaire/secondaire pas hiérarchisées (`Fermer` = ) `toolbar-btn` | (`.app-modal-*`, ), `app.css``.modal-actions``shared_ui.js` | Incohérence d'action | Décision plus rapide | Faible |
| 9 | P3 | Accessibilité : pas de `:focus-visible` global, contrastes muted limites, hover `transform` sur tous boutons | `app.css` | Navigation clavier faible | A11y / clavier | Moyen |
| 10 | P3 | Mojibake possible : `Types monitorés` (l.111 index.html) vs `Types monitorisés` ailleurs — encodage à vérifier avant édition | , JS `index.html` | Affichage texte | Propreté | Faible |
| 11 | P4 | Setup = long formulaire vertical brut (≈ 16 champs sans regroupement) | , (`.setup-*`) `setup.html``app.css` | Onboarding pénible | Wizard guidé | Moyen |
| 12 | P4 | Portail : carte unique « Chargement » + cartes modules sans statut/action explicite | , , `portal.html``portal.js``app.css` | Module peu lisible | Cartes module claires | Moyen |
| 13 | P5 | / volumineux : risque de refonte par duplication de markup au lieu d'helpers `app.js``portal.js``shared_ui.js` | , `app.js``portal.js` | Dette technique | Maintenabilité | Élevé |
**Note encodage (contrainte du prompt) :** avant toute édition d'un fichier, vérifier l'UTF-8. Seul `Types monitorés` (`#runtime-types`, label) diverge de `Types monitorisés` employé ailleurs — à confirmer, ne pas « corriger » à l'aveugle.
## 3. Direction design proposée
**Concept : « ITops NOC Console »** — sobre, dense mais lisible, orientée exploitation.
- **Palette opérationnelle** (remplace le violet) :
    - Accent principal : bleu acier/cyan d'infrastructure (ex. `#0ea5e9` ou `#2563eb`) → neutre, professionnel, non alarmant.
    - Sémantique d'état renforcée et **toujours prioritaire visuellement** :
        - `danger`/offline : rouge dominant + fond teinté + pastille pleine (le plus visible).
        - `warning`/idle : ambre, distinct du rouge et du vert.
        - `success`/online : vert lisible mais **moins dominant** (texte/pastille fine).

- **Hiérarchie** : titres en , valeurs de cartes fortes, métadonnées en . Réduction du « bruit » : bordures plus douces, hover sans translation systématique. `--font-display``--muted`
- **Densité maîtrisée** : conserver la compacité (outil pro) mais aérer verticalement les zones critiques (cartes d'alerte, en-têtes de table).
- **Statuts mis en scène** : une carte « Alertes/Hors-ligne » prioritaire en tête de dashboard ; bandeau de couleur sur cartes en alerte.
- **Animations** : conserver , supprimer les micro-animations purement décoratives sur les boutons utilitaires. `prefers-reduced-motion`
- **Mode sombre** : déjà supporté côté thème (variables surchargeables) — la refonte doit passer **exclusivement par variables CSS** pour rester compatible.

## 4. Design system CSS proposé
Basé sur les variables existantes, **sans renommer** ce qui est utilisé par le JS de thème.
**4.1 Corriger les variables manquantes (P1) — 2 options, recommander l'alias :**``` css
:root {
    /* Alias des variables référencées mais non déclarées */
    --text-main: var(--text);
    --text-muted: var(--muted);
    --line-soft: color-mix(in srgb, var(--line) 60%, transparent);
}
```

Recommandation : créer les alias plutôt que remplacer les 14 usages — moins risqué, réversible, et compatible avec un éventuel override de thème ciblant ces noms.
4.2 Tokens d'échelle à introduire (nouveaux, additifs, non destructifs) :``` css
:root {
    /* Espacement */
    --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
    /* Rayons (uniformiser : actuellement mix 0 / 6 / 8 / 10 / 999px) */
    --radius-sm: 6px; --radius-md: 10px; --radius-pill: 999px;
    /* Élévation */
    --shadow-sm: 0 2px 8px rgba(15,23,42,.10);
    /* Accent opérationnel */
    --accent: #2563eb;                 /* remplace #7c3aed */
    --accent-strong: color-mix(in srgb, var(--accent) 70%, black 30%);
    /* Surfaces d'état (fonds de badges/cartes) */
    --state-danger-bg: color-mix(in srgb, var(--danger) 12%, var(--panel));
    --state-warning-bg: color-mix(in srgb, var(--warning) 14%, var(--panel));
    --state-success-bg: color-mix(in srgb, var(--success) 12%, var(--panel));
    --focus-ring: 0 0 0 2px color-mix(in srgb, var(--accent) 55%, transparent);
}
```

4.3 Classes existantes à réutiliser (ne pas dupliquer) : .panel, .panel-lite, .primary-btn, .toolbar-btn, .status-online/offline/idle, .state-badge, .dash-card, .meta-badge, .app-modal-*, .field, .cards-grid, .table-wrap/.device-table.
4.4 Classes nouvelles proposées (minimales, justifiées) :
Classe
Rôle
Pourquoi pas l'existant
.btn-ghost / .btn-secondary
hiérarchiser actions modales/toolbars
toolbar-btn sert à tout aujourd'hui
.dash-card--alert
bandeau/teinte sur carte en alerte
.dash-card neutre uniquement
.status-dot
pastille pleine compacte dans tables
badges actuels trop « pleins » en table
.is-sensitive
masquer/révéler colonnes secrets
aucune gestion actuelle
.topbar-cluster
regrouper session/actions à droite
structure topbar trop plate
4.5 Accessibilité (additif global) :``` css
:focus-visible { outline: none; box-shadow: var(--focus-ring); }
@media (prefers-reduced-motion: reduce) {
    .primary-btn, .toolbar-btn, .monitor-btn, .menu-btn, .nav-btn { transition: none; transform: none; }
}
```
 
5. Plan de refonte en 3 phases (incrémentalement testable)
Phase 1 — Fondations CSS (zéro risque DOM)
Déclarer --text-main/--text-muted/--line-soft (alias) + tokens espacement/rayon/focus.
Remplacer l'accent violet → bleu opérationnel.
Harmoniser boutons (primaire/secondaire/ghost), panels, cartes, badges, tables, modales.
Ajouter :focus-visible, neutraliser animations superflues sous reduced-motion.
Aucun changement HTML/JS. Testable visuellement sur les 3 pages.
Phase 2 — Structure légère HTML/CSS
Topbar : regrouper session + actions (.topbar-cluster), sans renommer d'IDs.
Dashboard : carte d'alerte prioritaire (.dash-card--alert), hiérarchie valeur/sous-titre.
Tables : masquer Login/Mot de passe des vues principales (option révélation), pastilles .status-dot.
Portail : cartes module avec statut/accès/action principale.
Setup : regrouper en sections (Admin / Réseau / Base de données / Proxy).
Toucher app.js/portal.js uniquement si un rendu doit produire ces classes — en réutilisant shared_ui.js.
Phase 3 — Durcissement UX / a11y / dette
Audit aria-*, labels, ordre tab, contraste --muted.
Vérification responsive mobile/tablette des nouveaux blocs.
Extraire vers shared_ui.js les helpers de rendu de cartes/badges dupliqués entre app.js et portal.js (faible risque uniquement).
Ajuster/ajouter tests si un comportement JS/API change.
 
6. Liste précise des fichiers à modifier (dans l'ordre)
monitoring/web/app.css — Phase 1 (variables manquantes, tokens, accent, boutons, cartes, badges, tables, modales, focus). Cœur de la refonte.
monitoring/web/index.html — Phase 2 (topbar regroupée, classes d'état/sensibles ; conserver tous les id).
monitoring/web/portal.html — Phase 2 (cartes module, topbar).
monitoring/web/setup.html — Phase 2 (sections guidées).
monitoring/web/app.js — Phase 2/3, si nécessaire (produire les nouvelles classes via rendu, masquage secrets).
monitoring/web/portal.js — Phase 2/3, si nécessaire (cartes module).
monitoring/web/shared_ui.js — Phase 3 (extraction helpers carte/badge/bouton).
Invariants à préserver : IDs (#auth-form, #cards-grid, #devices-head, #inventory-head, #app-modal*, #detail-panel, data-col=*, data-screen…), globales NMPSharedUi/Api/Menu/Auth/Import/Download/AdminUi/Store/Controller, endpoints API, logique métier. Aucun framework front.
Risques de régression principaux :
Changer --accent impacte aussi .primary-btn, .monitor-btn.global-active, .panel-kicker, badges plugins → vérifier visuellement.
Masquer des colonnes : vérifier que app.js n'indexe pas les cellules par position.
Modifier la topbar : ne pas casser les sélecteurs #nav-toolbar, #session-profile-label, #dashboard-edit-button.
 
7. Prompts courts de suivi (implémentation)
Phase 1 :
Applique la phase 1 ITops : modifie uniquement monitoring/web/app.css. Déclare les alias --text-main, --text-muted, --line-soft dans :root, ajoute les tokens espacement/rayon/focus, remplace --accent violet par bleu opérationnel, harmonise boutons/panels/cartes/badges/tables/modales, ajoute :focus-visible et respect de prefers-reduced-motion. Ne touche ni au HTML ni au JS, ne renomme aucun ID. Liste d'abord les blocs CSS modifiés et les risques, puis donne un diff summary et les vérifications manuelles (index/portal/setup, light/dark).
Phase 2 :
Applique la phase 2 ITops : structure légère HTML/CSS. Regroupe la topbar, ajoute la carte d'alerte dashboard, masque Login/Mot de passe des tables principales, enrichis les cartes portail, sectionne le setup. Préserve tous les IDs DOM et les data-col, réutilise les classes Phase 1 et shared_ui.js. Ne modifie app.js/portal.js que si un rendu doit émettre ces classes. Liste fichiers + risques avant, diff + tests après.
Phase 3 :
Applique la phase 3 ITops : a11y (focus, aria, labels, contraste), responsive mobile/tablette des nouveaux blocs, extraction des helpers de rendu carte/badge dupliqués vers shared_ui.js (faible risque uniquement), ajustement des tests si un comportement JS/API change. Aucune refonte métier, aucun changement d'endpoint ni de stockage