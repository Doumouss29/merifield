from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='index'),
    path('entreprises/nouvelle/', views.new_organization, name='portal_new_organization'),
    path('espaces/<str:workspace>/projets/nouveau/', views.new_project, name='portal_new_project'),
    path('projets/<uuid:project_id>/fichiers/<path:filename>/', views.download_file, name='portal_download'),
    path('projets/<uuid:project_id>/', views.project_detail, name='portal_project'),
    path('espaces/<str:workspace>/membres/', views.members, name='portal_members'),
    path('espaces/<str:workspace>/abonnement/', views.offers, name='portal_offers'),
    path('rejoindre/<str:token>/', views.accept_invite, name='portal_accept_invite'),
    path('gestion/', views.administration, name='portal_administration'),
    path('gestion/demandes/<int:request_id>/activer/', views.approve, name='portal_approve'),
    path('gestion/demandes/<int:request_id>/refuser/', views.reject, name='portal_reject'),
    path('mentions/', views.legal, name='portal_legal'),
    path('healthz/', views.health, name='portal_health'),
]
