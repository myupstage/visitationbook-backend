# Generated by Django 5.0.7 on 2024-10-03 07:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visitationbookapi', '0014_guestinfo_guest_picture'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookpurchase',
            name='is_both',
            field=models.BooleanField(default=False, verbose_name='Is both checking'),
        ),
    ]
