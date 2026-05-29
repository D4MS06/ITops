# Architecture Web (runtime unique)

## Objectif
Maintenir une architecture strictement orientee service web:
- `API`: endpoints FastAPI, validation et orchestration HTTP.
- `Services`: regles metier, normalisation, policies d'action/import.
- `Model/Storage`: acces donnees runtime (MariaDB).
- `Web UI`: front JavaScript/CSS servi par l'API.

## Couches
- `monitoring/api`: routes HTTP + schemas API.
- `monitoring/services`: logique metier et transformation des donnees.
- `monitoring/models`: modeles runtime en memoire.
- `monitoring/storage`: persistance MariaDB + bootstrap schema.
- `monitoring/web`: interface utilisateur web.
- `monitoring/shared`: utilitaires transverses non lies a une UI particuliere.

## Regles
- Pas de dependance UI desktop/Tkinter dans le runtime.
- Toute logique metier doit vivre en `services`.
- Les routes API restent minces: validation, securite, appels services.
- Les utilitaires partages (theme, compat actions, etc.) restent dans `shared`.

## Evolution
- Nouvelle fonctionnalite: `services` -> `api` -> `web`.
- Eviter les couplages transverses entre API et front.
- Conserver des tests cibles sur endpoints, policies metier et parsing/import.
