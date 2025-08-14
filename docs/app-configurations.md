# App configurations for the web-app
The codebase is setup to be reusable in different scenarios across devices/platforms/frameworks. It's difficult to reason about those scenarios though, so here's some notes on them.

## In-browser web app for the desktop
The main considerations are
- Service worker API availability - for managing storage efficiently and having client-side media storage via cache API fetch intercepts
- IndexedDB - for domain data offline storage
- BroadcastChannel - for communication of storage updates between tabs and/or the storage service

### Offline-capable web app

### Thin client


### Thin client in private mode
No storage between sessions. Only cloud storage persistence/sync is possible.

## Desktop app
