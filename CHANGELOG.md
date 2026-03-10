# Changelog

## 1.0.7-prep

- extraction de `DeviceService` pour centraliser le CRUD, la validation, la recherche et la serialisation des equipements
- extraction de `MonitoringService` pour isoler le moteur de supervision, les transitions d'etat, les logs et les notifications hors de Tkinter
- ajout de `AuthService` avec hash admin, login/logout et sessions tokenisees
- ajout d'un backend applicatif partage pour aligner desktop Tkinter et API HTTP sur la meme pile de services
- ajout d'un squelette FastAPI avec endpoints auth, devices, device-types, logs, config-files et settings
- correction de la mise a jour des tuiles dashboard et des refresh UI sur transitions `idle -> online/offline`
- correction de la parallelisation du fallback `ping.exe` pour eviter les blocages de supervision sur des lots volumineux
- ajout des tests backend, API, auth, device service, monitoring service et dashboard counts
