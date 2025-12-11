from django.contrib import admin
from .models import Event
from .models import Participant


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start', 'end', 'organiser', 'co_organisers_list')
    list_filter = ('start', 'end')
    search_fields = ('title', 'description')

    def co_organisers_list(self, obj):
        return ", ".join([f"{p.Prenom} {p.Nom}" for p in obj.co_organisers.all()])
    co_organisers_list.short_description = 'Co-organisateurs'


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('person_display', 'event', 'status')
    list_filter = ('status', 'event')
    search_fields = ('person__Nom', 'person__Prenom', 'event__title')

    def person_display(self, obj):
        """Affiche le nom complet de la personne"""
        return f"{obj.person.Prenom} {obj.person.Nom}"

    person_display.short_description = 'Personne'

    def has_add_permission(self, request):
        return True
