"""Flask CLI commands for Web Push (run with `flask --app wsgi <command>`)."""
import click
from flask.cli import with_appcontext

from app.modules.notifications import push


@click.command("push-generate-keys")
def generate_keys():
    """Print a fresh VAPID key pair for the environment variables (do this once, then keep it)."""
    public, private = push.generate_vapid_keys()
    click.echo(f"VAPID_PUBLIC_KEY={public}")
    click.echo(f"VAPID_PRIVATE_KEY={private}")
    click.echo("VAPID_SUBJECT=mailto:admin@your-domain.example")


@click.command("push-tick")
@with_appcontext
def tick():
    """Cron entry point: create due reminders, send pending/retry pushes, prune old rows."""
    if not push.is_configured():
        click.echo("push is not configured (VAPID_* variables missing) - nothing to do")
        return
    click.echo(push.tick())


@click.command("push-dispatch")
@with_appcontext
def dispatch():
    """Send / retry due deliveries only (no reminder generation)."""
    if not push.is_configured():
        click.echo("push is not configured (VAPID_* variables missing) - nothing to do")
        return
    click.echo(push.process_due())


def register(app) -> None:
    for cmd in (generate_keys, tick, dispatch):
        app.cli.add_command(cmd)
