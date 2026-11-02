# ITops

ITops est un portail web d'administration IT : inventaire et supervision reseau, services dynamiques no-code, annuaires et outils d'exploitation.

## Demarrage local

Prerequis : Python 3.12, MariaDB configure et les dependances de `requirements.txt`.

```powershell
.\venv312\Scripts\python.exe -m pip install -r requirements.txt
.\venv312\Scripts\python.exe main.py --port 8080
```

Ouvrir ensuite `http://localhost:8080`. Le launcher accepte `--host`, `--port` et `--reload` ; consulter `main.py` pour le contrat exact. Les valeurs d'hebergement sont chargees depuis la configuration applicative.

## Verification

```powershell
.\venv312\Scripts\python.exe -m pytest -q
node --check monitoring\web\portal.js
```

Adapter le controle JavaScript aux fichiers modifies. Les tests et les contrats a privilegier sont decrits dans `AGENTS.md` et `docs/CONVENTIONS.md`.

## Documentation

Commencer par [docs/INDEX.md](docs/INDEX.md). Il oriente vers l'architecture, les conventions, l'etat confirme, la roadmap et les documents de domaine. La configuration du reverse proxy est dans [docs/caddy_reverse_proxy.md](docs/caddy_reverse_proxy.md).

## Distribution

Les scripts d'installation et de mise a jour sont sous `scripts/`. Les builds et procedures de release doivent etre verifies contre leur code et leurs scripts avant utilisation ; le changelog conserve l'historique des versions.