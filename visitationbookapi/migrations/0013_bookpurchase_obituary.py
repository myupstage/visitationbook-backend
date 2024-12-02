# Generated by Django 5.0.7 on 2024-09-21 21:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visitationbookapi', '0012_paymenttransaction_stripe_payment_intent_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookpurchase',
            name='obituary',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='book_purchase', to='visitationbookapi.obituary', verbose_name='Obituary'),
        ),
    ]