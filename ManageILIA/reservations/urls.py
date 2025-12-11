from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    path('api/events/', views.events_json, name='events_json'),
    path('api/locations/', views.locations_json, name='locations_json'),
    path('api/reservations/create/', views.create_reservation_api, name='create_reservation_api'),
    path('api/reservations/<int:pk>/', views.reservation_detail_api, name='reservation_detail_api'),
    
    # Occupation des locaux
    path('horaire/', views.horaire_reservation, name='horaire_reservation'),
    path('occupation/', views.occupation_locaux, name='occupation_locaux'),
    path('bureau/<int:bureau_id>/', views.bureau_occupation, name='bureau_occupation'),
    path('api/bureau/<int:bureau_id>/events/', views.bureau_events_json, name='bureau_events_json'),
    path('piece/<int:piece_id>/', views.piece_occupation, name='piece_occupation'),
    path('api/piece/<int:piece_id>/events/', views.piece_events_json, name='piece_events_json'),
    path('liberer-bureau/', views.liberer_bureau, name='liberer_bureau'),
]
