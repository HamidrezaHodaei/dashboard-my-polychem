"""
Follow-up reminders for the customer database -- the «روز تماس اقدام بعدی» field
(`customers.next_follow_up_date`).

Like the task deadline warnings and the sample reminders they are generated lazily when the user's
notification list is fetched (the header polls it), so no scheduler is needed.

  next_follow_up_date == today   ->  kind "due"      «امروز موعد پیگیری مشتری است»
  next_follow_up_date <  today   ->  kind "overdue"  «موعد پیگیری مشتری گذشته است»  (once a day, until
                                                                                    the date is changed)
Who is told: the customer's responsible person (`assigned_to_user_id`), else its creator.

Rules that prevent duplicate / irrelevant notices:
* at most ONE notice per (customer, kind, day): dedupe key `cf:<kind>:<customer id>:<date>`;
* a newer daily notice supersedes the older UNREAD ones of that customer;
* the reminder follows the CURRENT data: when the date is moved to the future / cleared, the customer
  is deleted or becomes inactive, or the responsible person changes, the stale unread reminders of
  that customer are marked read on the next poll.
"""
from datetime import date

from sqlalchemy import or_

from app.core.users.models import User
from app.extensions import db
from app.modules.customers.models import Customer, OperationalStatus
from app.modules.notifications import services as notifications
from app.modules.notifications.models import Notification
from app.utils.jalali import format_jalali, tehran_today

TYPES = {"due": "CUSTOMER_FOLLOWUP_DUE", "overdue": "CUSTOMER_FOLLOWUP_OVERDUE"}
PREFIX = "cf:"


def _fa(value) -> str:
    return str(value).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _recipient(customer: Customer) -> int | None:
    return customer.assigned_to_user_id or customer.created_by_user_id


def due_reminder(customer: Customer, today: date) -> tuple[str, str, str] | None:
    """(kind, title, body) that applies to `customer` today -- or None."""
    nxt = customer.next_follow_up_date
    if nxt is None or nxt > today:
        return None
    name = customer.display_name
    action = (customer.next_action or "").strip()
    action_part = f"\nاقدام بعدی: {action}" if action else ""
    if nxt == today:
        return ("due", "امروز موعد پیگیری مشتری است",
                f"امروز روز تماس / اقدام بعدی مشتری «{name}» است.{action_part}")
    return ("overdue", "موعد پیگیری مشتری گذشته است",
            f"موعد تماس / اقدام بعدی مشتری «{name}» ({_fa(format_jalali(nxt))}) گذشته است.{action_part}")


def generate_for(user_id: int) -> int:
    """Create today's follow-up reminders for `user_id`. Idempotent: safe to call on every poll."""
    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        return 0
    today = tehran_today()
    candidates = db.session.query(Customer).filter(
        Customer.deleted_at.is_(None), Customer.is_active.is_(True),
        Customer.operational_status == OperationalStatus.ACTIVE,
        Customer.next_follow_up_date.isnot(None), Customer.next_follow_up_date <= today,
        or_(
            Customer.assigned_to_user_id == user_id,
            (Customer.assigned_to_user_id.is_(None)) & (Customer.created_by_user_id == user_id),
        ),
    ).all()
    created = 0
    current_ids: set[int] = set()
    for customer in candidates:
        found = due_reminder(customer, today)
        if found is None or _recipient(customer) != user_id:
            continue
        kind, title, body = found
        current_ids.add(customer.id)
        key = f"{PREFIX}{kind}:{customer.id}:{today.isoformat()}"
        row = notifications.notify(
            user_id, TYPES[kind], title, body, link=f"/crm/customers?open={customer.id}", dedupe_key=key,
        )
        if row is None:
            continue
        # keep the bell clean: older unread reminders of this customer are superseded
        db.session.query(Notification).filter(
            Notification.user_id == user_id, Notification.read_at.is_(None),
            Notification.dedupe_key.like(f"{PREFIX}%:{customer.id}:%"), Notification.dedupe_key != key,
        ).update({Notification.read_at: notifications._utcnow()}, synchronize_session=False)
        created += 1

    # self-heal: unread reminders of customers that are no longer due (date moved / cleared,
    # customer deleted, deactivated or re-assigned) are marked read
    stale = db.session.query(Notification).filter(
        Notification.user_id == user_id, Notification.read_at.is_(None), Notification.dedupe_key.like(f"{PREFIX}%"),
    ).all()
    now = notifications._utcnow()
    for n in stale:
        try:
            cid = int(n.dedupe_key.split(":")[2])
        except (IndexError, ValueError):
            continue
        if cid not in current_ids:
            n.read_at = now
    if created or stale:
        db.session.commit()
    return created
