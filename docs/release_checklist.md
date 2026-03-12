# Check-list release

## Avant build

- verifier que la branche de release est figee
- verifier `git status` propre
- verifier la version dans `__init__.py` et `monitoring/__init__.py`
- relire `CHANGELOG.md` et les notes de release GitHub
- verifier que les dependances de build sont installees via `requirements-build.txt`

## Validation locale

- lancer `pytest`
- lancer `pytest monitoring/tests/test_packaged_dist.py -q` apres generation du `dist`
- verifier le lancement desktop en local
- verifier le demarrage, l'arret et le redemarrage du serveur web
- verifier l'interface web sur `http://127.0.0.1:8000/`

## Build Windows

- executer `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Clean`
- verifier la presence de `dist\NetworkMonitoringProject\_internal\monitoring\web\index.html`
- verifier la presence de `dist\NetworkMonitoringProject\NetworkMonitoringProject.exe`
- verifier la presence de `installer\output\NetworkMonitoringProject-Setup-<version>.exe`

## Validation post-build

- installer le setup sur un poste vierge ou de test
- verifier le lancement desktop apres installation
- verifier le demarrage du serveur web sur le poste installe
- verifier l'authentification web et l'affichage du dashboard
- verifier une mise a jour depuis la version precedente si applicable
- verifier la desinstallation puis reinstallation

## Publication GitHub

- pousser la branche cible
- aligner le tag de release sur le commit valide
- remplacer l'asset `.exe` de la release GitHub
- verifier l'URL de release et la taille de l'asset
- tester le setup telecharge depuis GitHub
