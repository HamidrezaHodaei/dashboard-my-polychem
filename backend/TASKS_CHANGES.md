# Tasks module — what changed

Run after copying: `python -m flask db upgrade` (revision e5c9a3b7d2f1, after d4b8f2a6c1e9), restart the backend.

| # | Request | Where |
|---|---|---|
| 1,2,10 | Only a **manager** deletes checklist items / messages, renames or deletes a task | `services.Authority.is_manager` |
| 3 | A unit sees only its own projects, tasks, teams and people (**strict**: only `admin` sees all; grants — even GLOBAL — never widen a user's unit; creator/assignee no longer bypasses it) — see AUTHORIZATION.md §12 | `services.Authority.in_units`, `_scope_filtered_task_query`, `_can_view_task`, `task_meta`, `rules._within_units`, `notifications._accessible_task_ids` |
| 4 | Any number of files per task | `files.py`, `/tasks/<id>/files` |
| 5 | Several assignees at once | `PUT /tasks/<id>/assignees` |
| 7 | Referral chain | `POST /tasks/<id>/refer`, `GET /tasks/<id>/assignments` |
| 8 | Recurring tasks (daily / weekly / monthly / yearly / manual span) | `recurrence.py`, `scripts/run_recurring_tasks.py` |
| 9 | @mentions in messages | `@[userId]` tokens, `/tasks/mentions`, `/tasks/<id>/mention-candidates` |
| 11 | Tehran time + Jalali, UTF-8 | `utils/jalali.py`, ISO timestamps with `+00:00`, `due_time`, utf8mb4 |

**Who is a «مدیر» (manager)?** An admin, or anyone holding the permission `tasks.task.delete`
(حذف تسک) at the task's department/team. Give it to department heads in the access matrix
(Tasks row, «حذف» column). The department's `manager_user_id` label is deliberately NOT used
(AUTHORIZATION.md forbids deriving permissions from it).

**Unit isolation.** Unless you are an admin, you see and manage only the tasks of your own
department / the departments of your teams. No grant (GLOBAL included) and no creator/assignee
link widens that.
The "projects" list in the UI (= departments) follows the same rule.

**Referral.** An active assignee refers the task to someone in the task's department/team; the
referrer's assignment closes (`REFERRED`) and the new one points at it. The recipient can refer on.

**Recurrence.** A task with a repeat rule is the series template. Every interval a copy (same
assignees, fresh checklist) is created with the occurrence date as its due date. Months/years are
Jalali (day 31 in a 30-day month is clamped, then returns to 31). Copies are created lazily when
tasks are listed; optionally run `python scripts/run_recurring_tasks.py` nightly from cron.

**Worklist pictures.** Each department (کارتابل واحد) has ONE shared logo and ONE header banner:
`PUT/DELETE /api/tasks/departments/<id>/branding/<logo|header>` (multipart field `file`, **admin only**) and
`GET` the same path (any user who can see that unit's worklist; others get 403). PNG/JPG/WEBP/GIF only, 3 MB max,
content sniffed server-side. `GET /api/tasks/meta` lists `has_logo`, `has_header`, `branding_version` per department.
