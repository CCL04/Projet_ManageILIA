from django.urls import path
from .views import (
    EventListView,
    EventDetailView,
    DashboardView,
    EventCreateView,
    EventUpdateView,
    EventDeleteView,
    RespondInvitationView,
    RemoveParticipantView,
)

app_name = 'events'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('create/', EventCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', EventUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', EventDeleteView.as_view(), name='delete'),
    path('<int:pk>/participant/<int:participant_pk>/remove/', RemoveParticipantView.as_view(), name='participant_remove'),
    path('<int:pk>/respond/', RespondInvitationView.as_view(), name='respond'),
    path('list/', EventListView.as_view(), name='list'),
    path('detail/<int:pk>/', EventDetailView.as_view(), name='detail'),
]
