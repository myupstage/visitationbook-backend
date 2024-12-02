# Generated by Django 5.0.7 on 2024-10-30 15:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visitationbookapi', '0019_alter_bookpurchase_allow_address_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bookpurchase',
            name='custom_field_25',
        ),
        migrations.RemoveField(
            model_name='bookpurchase',
            name='custom_field_50',
        ),
        migrations.RemoveField(
            model_name='guestinfo',
            name='custom_field_video_25',
        ),
        migrations.RemoveField(
            model_name='guestinfo',
            name='custom_field_video_50',
        ),
        migrations.RemoveField(
            model_name='obituary',
            name='date_of_birth',
        ),
        migrations.AddField(
            model_name='book',
            name='text_color',
            field=models.CharField(default='#000000', help_text='Color code in hex format (e.g. #ffffff)', max_length=7),
        ),
        migrations.AddField(
            model_name='bookpurchase',
            name='custom_text_color',
            field=models.CharField(default='#000000', help_text='Color code in hex format (e.g. #ffffff)', max_length=7),
        ),
        migrations.AddField(
            model_name='obituary',
            name='text_color',
            field=models.CharField(default='#000000', help_text='Color code in hex format (e.g. #ffffff)', max_length=7),
        ),
        migrations.AlterField(
            model_name='obituary',
            name='date_of_death',
            field=models.DateField(blank=True, null=True, verbose_name='Date of Death'),
        ),
    ]
