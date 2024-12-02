from rest_framework.renderers import BrowsableAPIRenderer

class NoHTMLFormBrowsableAPIRenderer(BrowsableAPIRenderer):

    def get_context(self, *args, **kwargs):
        ctx = super().get_context(*args, **kwargs)
        ctx['display_edit_forms'] = False
        return ctx
    
    def show_form_for_method(self, view, method, request, obj):
        """We never want to do this! So just return False."""
        return False

    def get_rendered_html_form(self, *args, **kwargs):
        """
        We don't want the HTML forms to be rendered because it can be
        really slow with large datasets
        """
        return ""