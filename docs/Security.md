Notes:
* Cloud user settings should have a separate scope, since if they get synced with the desktop app - cloud breaches may insert local folders as projects and hijack local data.
* User ids and device ids are currently assumed to be URI-safe when used in routed URLs and derived local branch names. The current local defaults satisfy that (`local`, `device-<uuid>`). If external/cloud-provided ids are introduced later, their accepted character set should be validated explicitly before using them in those contexts.
