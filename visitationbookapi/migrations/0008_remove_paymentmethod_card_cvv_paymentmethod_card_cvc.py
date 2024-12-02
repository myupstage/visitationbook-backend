# Generated by Django 5.0.7 on 2024-09-20 02:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visitationbookapi', '0007_alter_paymentmethod_card_brand_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentmethod',
            name='card_cvv',
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='card_cvc',
            field=models.CharField(default='501', max_length=3, verbose_name='Card CVC'),
        ),
    ]