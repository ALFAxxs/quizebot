from django.db import migrations


CATEGORIES = ["math", "english", "iq"]


def backfill(apps, schema_editor):
    TestSession = apps.get_model("quiz", "TestSession")
    Part = apps.get_model("quiz", "Part")
    PartResult = apps.get_model("quiz", "PartResult")

    for session in TestSession.objects.all():
        parts_by_category = {
            p.category: p for p in Part.objects.filter(package_id=session.package_id)
        }
        rows = []
        for cat in CATEGORIES:
            total = getattr(session, f"{cat}_total")
            if not total:
                continue
            part = parts_by_category.get(cat)
            if not part:
                continue
            rows.append(PartResult(
                session=session, part=part,
                correct=getattr(session, f"{cat}_correct"), total=total,
            ))
        if rows:
            PartResult.objects.bulk_create(rows)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0002_partresult"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
