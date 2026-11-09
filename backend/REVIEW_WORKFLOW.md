# Request review workflow · accounts · notifications

`python -m flask db upgrade` (revision f6d1b8c4e2a7, after e5c9a3b7d2f1) and restart.

## Review workflow (logistics, suppliers, customers)
Statuses: در انتظار بررسی `PENDING` · تأیید `APPROVED` · رد درخواست `REJECTED` ·
نیازمند ویرایش یا تکمیل اطلاعات `NEEDS_EDIT` (the manager's explanation is mandatory). Logistics keeps
its extra `SUSPENDED` for approved parties.

* The **creator** (person who created the record) edits it WITHOUT any `update` permission, but only
  while it is a draft (saved, not yet "ثبت نهایی") or `NEEDS_EDIT`.
* After "ثبت نهایی" it is read-only for them. They can press **درخواست تغییر اطلاعات** and write a
  reason; the manager sees it (badge + banner) and decides.
* A manager (`<module>.review`) approves / rejects / sends back (`REQUEST_EDIT`, note required) /
  reopens. The creator gets an in-app notification for each decision.
* After the creator edits a returned record and presses **ثبت مجدد**, it returns to `PENDING`.
* `review` is a new column in the role / per-user permission matrix for Customers, Suppliers,
  Transport Companies and Drivers (non-delegable). Seeded for `admin`.
* Records created through the PUBLIC forms have no creator account, so only managers edit them.

Endpoints (same for the three modules): `POST /<id>/finalize`, `POST /<id>/request-change {reason}`,
`POST /<id>/review {action, note}`; every record carries `my_actions {can_edit, can_finalize,
can_request_change, can_review}` for the signed-in user.

## Accounts
* `POST /api/auth/change-password {current_password, new_password}` – every user, own password.
* `POST /api/core/users/<id>/password {new_password}` – admin only. **A current password can never be
  shown: it is stored as an Argon2 hash.** The admin sets a new one.
* `GET /api/me` returns name / e-mail / username / roles from the database (read-only for the user);
  `PUT/DELETE /api/me/avatar` – the user's own photo (data URL ≤ 300 KB, validated).

## Notifications
`GET /api/notifications`, `POST /api/notifications/read`. Created when a task is assigned / referred /
the user is @mentioned / a review decision is made, and (lazily, when the bell polls) for tasks due
within 24 h or overdue – once per task and due date. All texts are Persian.
