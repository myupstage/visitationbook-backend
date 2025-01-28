# Generated by Django 5.0.7 on 2025-01-11 00:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visitationbookapi', '0025_funeralhomesubscription_bookpurchase_subscription_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='funeralhomesubscription',
            name='payment_transaction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subscriptions', to='visitationbookapi.paymenttransaction'),
        ),
    ]
