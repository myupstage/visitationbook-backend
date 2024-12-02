from django.apps import AppConfig

class VisitationBookApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'visitationbookapi'
    verbose_name = 'Visitation Book API'

    def ready(self):
        import visitationbookapi.signals  # noqa

