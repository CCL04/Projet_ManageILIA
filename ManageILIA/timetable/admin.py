from django.contrib import admin
from .models import PersonalSchedule, PersonalScheduleEntry, RecurringTelework


@admin.register(PersonalSchedule)
class PersonalScheduleAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PersonalScheduleEntry)
class PersonalScheduleEntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'schedule', 'start_datetime', 'end_datetime', 'created_at')
    list_filter = ('start_datetime', 'created_at')
    search_fields = ('title', 'description', 'schedule__user__username')
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Informations générales', {
            'fields': ('schedule', 'title', 'description')
        }),
        ('Dates et Heures', {
            'fields': ('start_datetime', 'end_datetime')
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(RecurringTelework)
class RecurringTeleworkAdmin(admin.ModelAdmin):
    list_display = ('schedule', 'get_day_name', 'start_date', 'end_date')
    list_filter = ('day_of_week', 'start_date', 'end_date')
    search_fields = ('schedule__user__username',)

    fieldsets = (
        ('Utilisateur', {
            'fields': ('schedule',)
        }),
        ('Configuration du télétravail', {
            'fields': ('day_of_week', 'start_date', 'end_date')
        }),
    )

    def get_day_name(self, obj):
        days = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
        return days.get(obj.day_of_week, 'Inconnu')

    get_day_name.short_description = 'Jour'