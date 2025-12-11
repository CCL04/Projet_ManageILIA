from django.contrib import admin
from .models import Projet, Fichier


# ========== PROJET ==========
@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    list_display = ('Id_projet', 'Nom_projet', 'Type')
    list_filter = ('Type',)
    search_fields = ('Nom_projet',)
    ordering = ('Nom_projet',)


# ========== FICHIER ==========
@admin.register(Fichier)
class FichierAdmin(admin.ModelAdmin):
    list_display = (
        'Id_fichier', 'Nom', 'Description', 'Date_publication',
        'Id_Matricule', 'Id_projet'
    )
    list_filter = ( 'Date_publication', 'Id_projet')
    search_fields = ('Nom', 'Id_Matricule__Nom', 'Id_projet__Nom_projet')
    date_hierarchy = 'Date_publication'
    ordering = ('-Date_publication',)

    fieldsets = (
        ('Informations du fichier', {
            'fields': ('Nom', 'Description', 'Date_publication')
        }),
        ('Associations', {
            'fields': ('Id_Matricule', 'Id_projet')
        }),
    )