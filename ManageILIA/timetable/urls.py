from django.urls import path
from . import views

urlpatterns = [
    path('personal/', views.personal_schedule, name='personal_schedule'),
    path('add-entry/', views.add_schedule_entry, name='add_schedule_entry'),
    path('add-telework/', views.add_recurring_telework, name='add_recurring_telework'),
    path('sync-events/', views.sync_accepted_events, name='sync_events'),
    path('sync-bookings/', views.sync_office_bookings, name='sync_bookings'),
    path('schedule/delete-entry/', views.delete_personal_entry, name='delete_personal_entry'),
    path('schedule/delete-telework/', views.delete_recurring_telework, name='delete_recurring_telework'),
    path('schedule/delete-telework-occurrence/',views.delete_recurring_telework_occurrence,name='delete_recurring_telework_occurrence',),
    path('api/events-reservations/', views.get_events_and_reservations, name='get_events_and_reservations'),
    path('api/delete-event/', views.delete_event, name='delete_event'),
    path('api/delete-reservation/', views.delete_reservation, name='delete_reservation'),
]