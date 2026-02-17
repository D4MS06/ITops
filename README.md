# NetworkMonitoringProject

Ce projet est une petite application Tkinter permettant de monitorer des équipements réseau (switches, serveurs...). Les pings sont effectués de manière asynchrone et une notification peut être envoyée lorsqu'un changement de statut est détecté.

## Installation

1. **Prérequis**
   - Python 3.10 ou plus récent.
   - Tkinter (sur Linux « `sudo apt-get install python3-tk` » si nécessaire).
2. **Dépendances Python**
   ```bash
   pip install -r requirements.txt
   ```
   Ceci installe principalement [aioping](https://pypi.org/project/aioping/) pour le ping asynchrone et [keyring](https://pypi.org/project/keyring/) pour la gestion du mot de passe SMTP.

Pour les tests unitaires, `pytest` est recommandé.

## Utilisation

Lancer directement le fichier principal :

```bash
python main.py
```

L'interface Tkinter s'affiche alors. Depuis le tableau de bord :

- **Vue Séparée** : visualise les switchs et les serveurs indépendamment.
- **Vue Globale** : récapitule tous les appareils avec leurs statuts.
- Bouton « Démarrer Tout » / « Arrêter Tout » pour lancer ou stopper les pings en continu.
- Menu « Paramètres → Notifications... » pour configurer l'envoi d'e-mails d'alerte.

Les paramètres de notification sont sauvegardés dans `~/.network_monitor_settings.json` et, si `keyring` est disponible, le mot de passe est stocké de manière sécurisée.

