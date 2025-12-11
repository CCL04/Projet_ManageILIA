from django.contrib import admin
from .models import Piece, Bureau, Reservation, PersonneReservation, LiberationBureau


@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display = ('Id_piece', 'Nom', 'Etage', 'Type', 'Capacite', 'nb_bureaux')
    list_filter = ('Etage', 'Type')
    search_fields = ('Nom',)
    ordering = ('Etage', 'Nom')

    def nb_bureaux(self, obj):
        return obj.bureaux.count()
    nb_bureaux.short_description = 'Nb bureaux'


@admin.register(Bureau)
class BureauAdmin(admin.ModelAdmin):
    list_display = ('Id_bureau', 'Nom', 'Type', 'Id_piece', 'get_etage')
    list_filter = ('Type', 'Id_piece__Etage')
    search_fields = ('Nom','Id_bureau', 'Id_piece__Nom')
    ordering = ('Id_piece__Etage', 'Id_bureau')

    def get_etage(self, obj):
        return obj.Id_piece.Etage if obj.Id_piece else '-'
    get_etage.short_description = 'Etage'


class PersonneReservationInline(admin.TabularInline):
    model = PersonneReservation
    extra = 1
    raw_id_fields = ('Id_Matricule',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('Id_reservation', 'Nom', 'Type', 'Debut', 'Fin', 'Id_Matricule', 'get_lieu')
    list_filter = ('Type', 'Debut')
    search_fields = ('Nom', 'Id_Matricule__Nom', 'Id_Matricule__Prenom')
    date_hierarchy = 'Debut'
    ordering = ('-Debut',)
    inlines = [PersonneReservationInline]

    def get_lieu(self, obj):
        if obj.Id_bureau:
            return f"Bureau {obj.Id_bureau.Id_bureau}"
        elif obj.Id_piece:
            return f"{obj.Id_piece.Nom}"
        return '-'
    get_lieu.short_description = 'Lieu'


@admin.register(PersonneReservation)
class PersonneReservationAdmin(admin.ModelAdmin):
    list_display = ('Id_Matricule', 'Id_reservation', 'Valide')
    list_filter = ('Valide',)
    search_fields = ('Id_Matricule__Nom', 'Id_Matricule__Prenom')


@admin.register(LiberationBureau)
class LiberationBureauAdmin(admin.ModelAdmin):
    list_display = ('Id_Matricule', 'Id_bureau', 'Date', 'Date_creation')
    list_filter = ('Date', 'Date_creation')
    search_fields = ('Id_Matricule__Nom', 'Id_Matricule__Prenom', 'Id_bureau__Nom')
    date_hierarchy = 'Date'
    ordering = ('-Date_creation',)