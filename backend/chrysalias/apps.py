"""
Chrysalias.com — Custom Admin Site configuration
"""
from django.contrib.admin import AdminSite
from django.apps import AppConfig


class ChrysaliasAdminSite(AdminSite):
    site_header  = 'CHRYSALIAS.COM Administration'
    site_title   = 'Chrysalias Admin Portal'
    index_title  = 'Chrysalias Admin Dashboard'
    site_url     = '/'


chrysalias_admin = ChrysaliasAdminSite(name='chrysalias_admin')


class ChrysaliasAdminConfig(AppConfig):
    name    = 'chrysalias'
    label   = 'chrysalias'
    verbose_name = 'Chrysalias Admin'

    def ready(self):
        pass

    default_auto_field = 'django.db.models.BigAutoField'
