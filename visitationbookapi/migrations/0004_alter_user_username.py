# Generated by Django 5.0.7 on 2024-09-18 19:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visitationbookapi', '0003_book_bookpurchase_guestinfo_obituary_paymentmethod_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(blank=True, max_length=150, null=True, unique=True),
        ),
    ]
