from django.conf import settings
from django.db import migrations


def grant_superuser(apps, schema_editor):
    """One-off fix: the account matching ADMIN_ALLOWED_EMAIL needs
    is_staff/is_superuser so it can actually pass the email-restricted
    admin gate added in predictions/admin.py. If the account doesn't
    exist yet (e.g. fresh DB), there's nothing to do here -- it must
    register normally first, then this can be re-run.
    """
    User = apps.get_model(settings.AUTH_USER_MODEL)
    email = getattr(settings, "ADMIN_ALLOWED_EMAIL", "majjihboy@gmail.com")
    User.objects.filter(email__iexact=email).update(
        is_staff=True, is_superuser=True
    )


def noop_reverse(apps, schema_editor):
    # Deliberately not reversing the grant -- reversing a migration
    # shouldn't silently strip admin rights from a live account.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("predictions", "0007_vipcode_delete_stripeevent_and_more"),
    ]

    operations = [
        migrations.RunPython(grant_superuser, noop_reverse),
    ]
