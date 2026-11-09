"""
Create every recurring-task occurrence that is due (Tehran calendar day).

Occurrences are also created lazily whenever tasks are listed, so this script is
optional -- run it from cron/Task Scheduler (e.g. every night at 00:05) if you want
the tasks to exist even when nobody opens the app:

    python scripts/run_recurring_tasks.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.modules.tasks.recurrence import generate_due_recurring_tasks


def main() -> int:
    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        n = generate_due_recurring_tasks()
    print(f"Created {n} recurring task(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
