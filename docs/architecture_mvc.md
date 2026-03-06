# Architecture MVC cible

## Objectif
Rendre l'application plus modulaire et maintenable en separant clairement:
- `Model`: etat metier et persistance.
- `View`: UI Tkinter.
- `Controller`: orchestration des actions utilisateur.

## Regles de separation
- Une `View` ne lit/crit plus directement la base de donnees.
- Un `Controller` appelle un `Service` metier.
- Un `Service` encapsule les appels repository/persistance.
- Le theming ne doit jamais modifier la logique (state, donnees, bindings metier).

## Couches actuelles
- `monitoring/models`: modele de donnees runtime.
- `monitoring/services`:
  - `DeviceTypeService`: gestion types/schemas dynamiques.
  - `DeviceFormService`: metadonnees de formulaires devices.
- `monitoring/controllers`:
  - `DeviceTypeController`: facade MVC pour les vues de parametrage.
- `monitoring/ui`: vues/dialogs (consomment controllers/services).
  - Dashboard decoupe en mixins de responsabilite:
    - `DashboardMenuMixin`: menus contextuels/nav personnalisés.
    - `DashboardUpdateMixin`: orchestration MAJ (check/download/install).
    - `DashboardWatermarkMixin`: personnalisation filigrane/fond.

## Conventions d'evolution
- Toute nouvelle fonctionnalite UI:
  1. Ajout logique metier dans `services`.
  2. Exposition via `controllers`.
  3. Wiring minimal dans `ui`.
- Eviter les classes > 500 lignes (split en sous-composants).
- Eviter les effects de bord transverses (pas de mutation d'etat widget dans la couche theme).

## Conventions Theme / Heritage
- `resolve_theme()` doit toujours retourner un set complet de tokens couleurs (fallback automatique).
- Ne jamais rappeler `style.theme_use(...)` en cours de vie de l'application (uniquement au bootstrap).
- Les mixins de theme doivent couvrir explicitement les widgets `tk` ET `ttk` utilises (Button, Entry, Treeview, Scrollbar, Canvas, Menu, Listbox, Combobox).
- Les hooks d'interaction (hover/bind) ne doivent pas etre injectes implicitement dans la passe d'heritage, pour eviter les effets de bord cumulés.
