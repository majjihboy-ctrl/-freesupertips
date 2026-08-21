from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("predictions", "0010_seed_second_tier_leagues_and_teams"),
    ]

    operations = [
        migrations.RemoveField(model_name="match", name="win_prob_home"),
        migrations.RemoveField(model_name="match", name="win_prob_draw"),
        migrations.RemoveField(model_name="match", name="win_prob_away"),
        migrations.RemoveField(model_name="match", name="pick"),
        migrations.RemoveField(model_name="match", name="proj_home_score"),
        migrations.RemoveField(model_name="match", name="proj_away_score"),
    ]
