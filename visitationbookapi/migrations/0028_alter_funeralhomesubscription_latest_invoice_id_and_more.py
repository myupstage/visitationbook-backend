# Generated by Django 5.0.7 on 2025-01-17 01:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visitationbookapi', '0027_subscriptionplan_stripe_price_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='funeralhomesubscription',
            name='latest_invoice_id',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='funeralhomesubscription',
            name='stripe_subscription_id',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='paymenttransaction',
            name='stripe_payment_intent_id',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
    ]
