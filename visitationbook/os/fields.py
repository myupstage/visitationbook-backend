from django_userforeignkey.models.fields import UserForeignKey as UserForeignKey_Base

class UserForeignKey(UserForeignKey_Base):

    def contribute_to_class(self, cls, name, **kwargs):
        super(UserForeignKey, self).contribute_to_class(cls, name)
