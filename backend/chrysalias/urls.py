"""
Chrysalias.com — Root URL Configuration
"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

# Custom Admin Site Branding
admin.site.site_header = 'CHRYSALIAS.COM Administration'
admin.site.site_title = 'Chrysalias Admin Portal'
admin.site.index_title = 'Chrysalias Admin Dashboard'

urlpatterns = [
    # ── Admin Panel ──────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── REST API ─────────────────────────────────────────────
    path('api/auth/', include('accounts.urls')),
    path('api/', include('transactions.urls')),
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
