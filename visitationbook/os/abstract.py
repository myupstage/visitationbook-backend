from django.db import models
from visitationbook.os.fields import UserForeignKey

class CoreModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Registration date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modification date")
    created_by = UserForeignKey(auto_user_add=True, verbose_name="Added by", on_delete=models.PROTECT,
                                null=True, blank=True, related_name="created_%(app_label)s_%(class)s_set")
    updated_by = UserForeignKey(auto_user=True, verbose_name="Modified by", on_delete=models.PROTECT,
                                null=True, blank=True, related_name="modified_%(app_label)s_%(class)s_set")

    def save(self, *args, **kwargs):
        if self.pk:
            kwargs['force_update'] = True
            kwargs['force_insert'] = False
        else:
            kwargs['force_insert'] = True
            kwargs['force_update'] = False    

        super(CoreModel, self).save(*args, **kwargs)

    class Meta:
        abstract = True