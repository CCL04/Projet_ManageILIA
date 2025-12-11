from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.mes_projets, name='mes_projets'),
    path('create/', views.creer_projet, name='create_project'),
    path('<int:projet_id>/', views.detail_projet, name='project_detail'),
    path('<int:projet_id>/edit/', views.edit_projet, name='edit_projet'),
    path('<int:projet_id>/delete/', views.supprimer_projet, name='delete_projet'),
    path('<int:projet_id>/upload-file/', views.upload_fichier_projet, name='upload_file'),
    path('file/<int:fichier_id>/download/', views.telecharger_fichier, name='download_file'),
    path('file/<int:fichier_id>/delete/', views.supprimer_fichier, name='delete_file'),
]
