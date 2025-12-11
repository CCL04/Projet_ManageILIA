# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (Role, Personne, Notification, PersonneNotification)


# ========== ROLE ==========
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('Id_role', 'Nom_role')
    search_fields = ('Nom_role',)
    ordering = ('Id_role',)


# ========== PERSONNE (avec validation d'inscription) ==========
@admin.register(Personne)
class PersonneAdmin(admin.ModelAdmin):
    list_display = (
        'Id_Matricule', 'Nom', 'Prenom', 'Email',
        'get_roles', 'Service', 'Departement', 'is_active_status'
    )
    list_filter = ('Service', 'Departement', 'roles', 'user__is_active')
    search_fields = ('Nom', 'Prenom', 'Email', 'Id_Matricule')
    filter_horizontal = ('roles',)
    ordering = ('Nom', 'Prenom')

    fieldsets = (
        ('Informations personnelles', {
            'fields': ('Id_Matricule', 'Nom', 'Prenom', 'Email')
        }),
        ('Informations professionnelles', {
            'fields': ('Service', 'Departement', 'Universite', 'roles', 'Id_bureau', 'Date_fin')
        }),
        ('Compte utilisateur', {
            'fields': ('user',)
        }),
    )

    readonly_fields = ('Mot_de_passe',)

    actions = ['valider_inscription', 'desactiver_compte']

    def get_roles(self, obj):
        return ", ".join([role.Nom_role for role in obj.roles.all()])
    get_roles.short_description = 'ROles'

    def is_active_status(self, obj):
        if obj.user:
            return ' Actif' if obj.user.is_active else ' En attente'
        return ' Pas de compte'
    is_active_status.short_description = 'Statut'

    def valider_inscription(self, request, queryset):
        """Active les comptes utilisateurs s�lectionn�s"""
        count = 0
        for personne in queryset:
            if personne.user and not personne.user.is_active:
                personne.user.is_active = True
                personne.user.save()
                count += 1
        self.message_user(request, f"{count} inscription(s) valid�e(s).")
    valider_inscription.short_description = " Valider l'inscription"

    def desactiver_compte(self, request, queryset):
        """D�sactive les comptes utilisateurs s�lectionn�s"""
        count = 0
        for personne in queryset:
            if personne.user and personne.user.is_active:
                personne.user.is_active = False
                personne.user.save()
                count += 1
        self.message_user(request, f"{count} compte(s) désactivé(s).")
    desactiver_compte.short_description = " Désactiver le compte"



# ========== NOTIFICATION ==========
class PersonneNotificationInline(admin.TabularInline):
    """Inline pour afficher les destinataires dans l'admin des notifications"""
    model = PersonneNotification
    extra = 1
    autocomplete_fields = ['Id_Matricule']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('Id_notif', 'Titre', 'Type', 'Date', 'contenu_preview')
    list_filter = ('Type', 'Date')
    search_fields = ('Titre', 'Contenu')
    date_hierarchy = 'Date'
    ordering = ('-Date',)
    inlines = [PersonneNotificationInline]

    fieldsets = (
        ('Informations générales', {
            'fields': ('Titre', 'Type')
        }),
        ('Contenu', {
            'fields': ('Contenu',)
        }),
    )

    def contenu_preview(self, obj):
        return obj.Contenu[:50] + '...' if len(obj.Contenu) > 50 else obj.Contenu
    contenu_preview.short_description = 'Aperçu du contenu'





# ========== PERSONNALISATION USER (pour g�rer les comptes) ==========
class PersonneInline(admin.StackedInline):
    model = Personne
    can_delete = False
    verbose_name_plural = 'Informations Personne'
    fk_name = 'user'
    fields = ('Id_Matricule', 'Nom', 'Prenom', 'Email', 'Service', 'Departement')
    readonly_fields = ('Id_Matricule', 'Email')


class CustomUserAdmin(BaseUserAdmin):
    inlines = (PersonneInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff', 'is_superuser')


# R�enregistrer User avec la personnalisation
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# ========== PERSONNALISATION DU SITE ADMIN ==========
admin.site.site_header = "Administration ManageILIA"
admin.site.site_title = "ManageILIA Admin"
admin.site.index_title = "Gestion de l'application ILIA"
