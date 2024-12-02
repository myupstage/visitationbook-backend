# Generated by Django 5.0.7 on 2024-09-19 15:46

import visitationbookapi.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('visitationbookapi', '0005_alter_user_managers_remove_user_username'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='content_type',
            field=models.CharField(blank=True, help_text='The file extension', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='original_file_name',
            field=models.CharField(blank=True, help_text='Original file name', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='profile_image',
            field=models.ImageField(blank=True, null=True, upload_to=visitationbookapi.models.User._generate_document_path),
        ),
    ]