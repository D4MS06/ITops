# Caddy reverse proxy

Objectif :

- conserver un backend local configurable sur `127.0.0.1:<port>`
- exposer une URL stable `https://monitoring.mvl`
- rester portable entre Windows et Linux

## Architecture cible

- DNS interne : `monitoring.mvl -> IP du serveur`
- backend applicatif : `127.0.0.1:8000` ou autre port configure
- Caddy : ecoute sur `443`
- Caddy reverse proxy vers `127.0.0.1:<port>`

## Windows

Le setup Windows embarque `Caddy`, cree le service `NetworkMonitoringCaddy`
et initialise un proxy HTTPS local vers `127.0.0.1:8000`.

Ensuite, quand le port backend change dans l'application desktop :

- les parametres sont sauvegardes
- le `Caddyfile` est reecrit dans `%PROGRAMDATA%\\NetworkMonitoringProject\\caddy`
- le service Caddy est recharge automatiquement
- l'URL publique reste `https://monitoring.mvl`

Pour un HTTPS reconnu sans alerte navigateur sur les autres postes, il faut :

- soit deployer la CA interne Caddy sur tous les postes clients
- soit remplacer la directive `tls internal` par un certificat issu de votre PKI interne

## Linux

Exemple de `Caddyfile` :

```caddy
monitoring.mvl {
    reverse_proxy 127.0.0.1:8000
}
```

Avec certificat fourni :

```caddy
monitoring.mvl {
    tls /etc/ssl/monitoring/fullchain.pem /etc/ssl/monitoring/privkey.pem
    reverse_proxy 127.0.0.1:8000
}
```

## Bonnes pratiques

- laisser l'application ecouter uniquement sur `127.0.0.1`
- ne pas exposer directement le port backend aux clients
- publier uniquement `443` via le proxy
- afficher l'URL publique `https://monitoring.mvl` dans l'application desktop
