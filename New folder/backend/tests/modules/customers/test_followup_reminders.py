"""«روز تماس اقدام بعدی» -> automatic notifications (customers/reminders.py)."""
import datetime as dt

import pytest

from app.extensions import db
from app.modules.customers.models import Customer, CustomerType, OperationalStatus
from app.utils.jalali import tehran_today
from tests.core4.factories import auth_headers, make_user

API = "/api/notifications"


def _customer(owner, when, **over):
    c = Customer(
        customer_type=CustomerType.LEGAL, company_name=over.pop("company_name", "پلیمر آریا"),
        next_follow_up_date=when, next_action=over.pop("next_action", "تماس برای نهایی کردن قرارداد"),
        assigned_to_user_id=owner.id, **over,
    )
    db.session.add(c)
    db.session.commit()
    return c


def _items(client, user):
    return client.get(API, headers=auth_headers(user)).get_json()["data"]["items"]


def _cf(items):
    return [n for n in items if n["type"].startswith("CUSTOMER_FOLLOWUP")]


@pytest.fixture
def rep(app):
    user = make_user()
    db.session.commit()
    return user


def test_notice_on_the_follow_up_day_with_the_planned_action(client, rep):
    c = _customer(rep, tehran_today())
    notes = _cf(_items(client, rep))
    assert len(notes) == 1
    n = notes[0]
    assert n["type"] == "CUSTOMER_FOLLOWUP_DUE"
    assert "پلیمر آریا" in n["body"] and "تماس برای نهایی کردن قرارداد" in n["body"]
    assert n["link"] == f"/crm/customers?open={c.id}"


def test_polling_again_does_not_duplicate(client, rep):
    _customer(rep, tehran_today())
    for _ in range(3):
        _items(client, rep)
    assert len(_cf(_items(client, rep))) == 1


def test_no_notice_before_the_day(client, rep):
    _customer(rep, tehran_today() + dt.timedelta(days=1))
    assert _cf(_items(client, rep)) == []


def test_overdue_follow_up_is_reported_as_overdue(client, rep):
    _customer(rep, tehran_today() - dt.timedelta(days=2))
    notes = _cf(_items(client, rep))
    assert [n["type"] for n in notes] == ["CUSTOMER_FOLLOWUP_OVERDUE"]


def test_only_the_responsible_person_is_notified(client, rep):
    other = make_user()
    db.session.commit()
    _customer(rep, tehran_today())
    assert _cf(_items(client, other)) == []
    assert len(_cf(_items(client, rep))) == 1


def test_creator_is_notified_when_nobody_is_assigned(client, rep):
    c = Customer(customer_type=CustomerType.LEGAL, company_name="بدون مسئول",
                 next_follow_up_date=tehran_today(), created_by_user_id=rep.id)
    db.session.add(c)
    db.session.commit()
    assert len(_cf(_items(client, rep))) == 1


def test_moving_the_date_to_the_future_retires_the_unread_notice(client, rep):
    c = _customer(rep, tehran_today())
    assert len(_cf(_items(client, rep))) == 1
    c.next_follow_up_date = tehran_today() + dt.timedelta(days=7)
    db.session.commit()
    data = client.get(API, headers=auth_headers(rep)).get_json()["data"]
    assert all(n["is_read"] for n in _cf(data["items"]))
    assert data["unread_count"] == 0


def test_inactive_customer_gets_no_notice(client, rep):
    _customer(rep, tehran_today(), operational_status=OperationalStatus.INACTIVE)
    assert _cf(_items(client, rep)) == []
