from django.contrib import admin
from ILIA.models import PersonneNotification




@admin.register(PersonneNotification)
class PersonneNotificationAdmin(admin.ModelAdmin):
    """Administration de la table associative Personne-Notification"""
    list_display = ['Id_Matricule', 'Id_notif', 'Date_notif']
    list_filter = ['Date_notif']
    search_fields = ['Id_Matricule__Nom', 'Id_Matricule__Prenom', 'Id_notif__Titre']
    date_hierarchy = 'Date_notif'
    ordering = ['-Date_notif']
    autocomplete_fields = ['Id_Matricule', 'Id_notif']
