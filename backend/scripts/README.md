# scripts/

Reserved for one-off/maintenance scripts.

## `seed_roles_permissions.py` (Phase 1)

Idempotent development seed: creates the 16 initial system roles, the
initial organizational structure (دفتر مرکزی / کارخانه organizations;
فروش, مالی, تدارکات, تولید, انبار, کنترل کیفیت, لجستیک departments;
فروش داخلی team), and a single seed-time `admin @ GLOBAL` grant (see the
script's own docstring for why exactly one grant/permission exists this
early — the real permission registry is Phase 2).

Run after `flask db upgrade`:

```powershell
python scripts/seed_roles_permissions.py
```

Safe to re-run — every row is looked up by its natural key before insert.
