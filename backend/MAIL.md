# Correspondence (مکاتبات سازمانی) — internal mail

Module `app/modules/mail/`, API prefix `/api/mail`, frontend page `/mail` (`front/app/pages/mail`).

## Access
* Permission matrix row **«مکاتبات»**: `correspondence.mail.read | create | update | delete`
  (read = open the mailbox, create = compose/reply/forward/upload, update = star/label/read/archive/spam/mute, delete = trash / permanent delete).
* **Organizational units**: `PUT /api/mail/access/units {"department_ids":[…]}` (needs `core.permission.update`). Members of an enabled department, or of a team of it, get the four actions on their own mailbox.
* A per-user DENY of a mail permission beats a unit grant. Enforced in `services.py` via `access.require`, never only in the UI.
* Navigation key `correspondence` (`/api/me/navigation`) drives the sidebar button «مکاتبات» and the `/mail` route guard.

## Data
`mail_messages` · `mail_participants` (one row per sender/recipient with that user's private folder, read, star, mute, labels) · `mail_attachments` · `mail_unit_access`.
People, e-mail and profile photo are read from `users` (`avatar_data`); responses carry a `people` map so each photo is sent once.

## Endpoints (all authenticated)
`GET meta · counters · recipients?q= · threads?folder|label|starred|q|unread|sort|page` ·
`GET messages/<id>/thread` · `POST messages` (send) · `POST messages/<id>/reply` ·
`POST|PUT|DELETE drafts[/<id>]`, `POST drafts/<id>/send` · `POST messages/<id>/move` · `PATCH messages/<id>/flags` · `PUT messages/<id>/labels` · `DELETE messages/<id>` (permanent, own copy, only from trash/spam) ·
`POST attachments` (multipart `file`) · `GET|DELETE attachments/<id>` · `GET|PUT access/units`.

## Rules
* To and Cc are unlimited. Recipients must be active users who themselves have mail access; you cannot mail yourself.
* Folders are per user; a conversation is the root message plus replies. Non-participants get 404.
* Attachments: allow-listed extensions, content must match the extension, max `MAIL_MAX_ATTACHMENT_MB` (default `MAX_UPLOAD_MB`) per file, 10 files and 25 MB per message; stored in `UPLOAD_DIR/mail/`, served as attachment + `nosniff`, only to participants.
* Message bodies are plain text (rendered escaped).

## Migration
`flask db upgrade` → `a3e7c1f5b9d2` creates the tables and grants the four permissions to `admin`.
Tests: `pytest tests/modules/mail`.
