from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list, name='mes_notifications'),
    path('mes-notifications/', views.mes_notifications, name='mes_notifications'),
    path('<int:notif_id>/', views.notification_detail, name='notification_detail'),
    path('creer/', views.notification_create, name='notification_create'),
    path('<int:notif_id>/repondre/', views.respond_event_invitation, name='respond_event_invitation'),
    path('<int:notif_id>/supprimer/', views.notification_delete, name='notification_delete'),
]
