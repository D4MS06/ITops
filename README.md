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

## Travail courant et mise a jour du serveur Linux

`main` est la branche de reference pour le code pret a etre installe sur le serveur. La definir aussi comme branche par defaut du depot GitHub. Une petite correction peut y etre faite directement. Pour un chantier plus long, creer une branche `feature/<sujet>` depuis `main`, puis l'integrer a `main` apres verification locale. Garder les chantiers en cours sur leur branche ; ne pas les inclure dans une mise a jour du serveur par accident.

Avant une mise a jour, verifier les changements, executer les tests pertinents, puis enregistrer et pousser `main` sur `origin`. Le script `scripts/linux/upgrade_itops.sh` suit `origin/main` par defaut, refuse les modifications locales des fichiers suivis sur le serveur et exige une avance rapide de la branche. Il redemarre le service `itops` et controle `http://127.0.0.1:8080/health` ; `BRANCH`, `APP_DIR`, `SERVICE_NAME` et `HEALTH_URL` restent configurables.

Pour une installation Linux existante, controler d'abord la branche et les modifications locales dans `/opt/itops`, ainsi que le port du service. Si `main` contient deja le meme code applicatif que la branche en service, on peut aligner seulement la branche Git, sans redemarrer l'application. Verifier cette equivalence avant de lancer la bascule ; conserver les anciennes branches tant que le nouvel etat n'est pas confirme.

Depuis une session root ouverte avec `su -`, la bascule Git seule se fait ainsi quand `HEAD` est un ancetre de `origin/main` :

```bash
git -C /opt/itops fetch origin --prune &&
git -C /opt/itops merge-base --is-ancestor HEAD origin/main &&
git -C /opt/itops branch -f main origin/main &&
git -C /opt/itops switch main
```

Pour une vraie mise a jour du code applicatif, utiliser le script. Il redemarre le service ; le demarrage d'ITops peut verifier ou modifier le schema MariaDB et revoquer les sessions. Sauvegarder la base avant une evolution qui la concerne. Les mises a jour suivantes utilisent les valeurs par defaut :

```bash
bash /opt/itops/scripts/linux/upgrade_itops.sh
```

Apres la mise a jour, verifier les fonctions touchees dans le navigateur. Conserver l'identifiant du commit precedent pour un retour arriere du code ; Git ne restaure ni la base ni les fichiers de donnees. La procedure Windows depend du mode d'installation utilise et n'est pas couverte par le script Linux.

## Documentation

Commencer par [docs/INDEX.md](docs/INDEX.md). Il oriente vers l'architecture, les conventions, l'etat confirme, la roadmap et les documents de domaine. La configuration du reverse proxy est dans [docs/caddy_reverse_proxy.md](docs/caddy_reverse_proxy.md).

## Distribution

Les scripts d'installation et de mise a jour sont sous `scripts/`. Les builds et procedures de release doivent etre verifies contre leur code et leurs scripts avant utilisation ; le changelog conserve l'historique des versions.
