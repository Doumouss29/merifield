from django.contrib import admin
from merifield_portal.urls import urlpatterns as portal_urls
from qfieldcloud.urls import urlpatterns as engine_urls
from qfieldcloud.core.admin import qfc_admin_site

for site in (admin.site, qfc_admin_site):
    site.site_header = 'Mérifield Cloud'
    site.site_title = 'Mérifield Cloud'
    site.index_title = 'Administration de la plateforme'

# Keep /api/v1 and account routes unchanged for mobile and QGIS clients.
urlpatterns = portal_urls + [url for url in engine_urls if getattr(url, 'name', None) != 'index']
