from django.db import models
from django.core.exceptions import ValidationError


class Piece(models.Model):
    """Modèle pour les pièces (bureaux, salles de réunion, etc.)"""
    class TypePiece(models.IntegerChoices):
        BUREAU = 0, "Bureau"
        SALLE_REUNION = 1, "Salle de réunion"
        AUTRE = 2, "Autre"

    Id_piece = models.AutoField(primary_key=True)
    Nom = models.CharField(max_length=100)
    Etage = models.IntegerField()
    Capacite = models.IntegerField(blank=True, null=True)
    Type = models.IntegerField(choices=TypePiece.choices, default=TypePiece.BUREAU)

    def __str__(self):
        return f"{self.Nom} - Etage {self.Etage}"

    class Meta:
        verbose_name = "Pièce"
        verbose_name_plural = "Pièces"
        ordering = ['Etage', 'Nom']


class Bureau(models.Model):
    """Modèle pour les bureaux"""
    class TypeBureau(models.IntegerChoices):
        LIBRE = 0, "Libre"
        PARTAGEABLE = 1, "Partageable"
        OCCUPE = 2, "Occupé"

    Id_bureau = models.AutoField(primary_key=True)
    Nom = models.CharField(max_length=100, blank=True, null=True)
    Type = models.IntegerField(choices=TypeBureau.choices, default=TypeBureau.LIBRE)
    Id_piece = models.ForeignKey(Piece, on_delete=models.CASCADE, related_name='bureaux')

    def clean(self):
        """Valider que le nombre de bureaux ne dépasse pas la capacité de la pièce"""
        if self.Id_piece and self.Id_piece.Capacite is not None:
            # Compter les bureaux existants dans cette pièce (en excluant le bureau actuel si on modifie)
            existing_bureaux = Bureau.objects.filter(Id_piece=self.Id_piece)
            if self.pk:  # Si on modifie un bureau existant
                existing_bureaux = existing_bureaux.exclude(pk=self.pk)
            
            count = existing_bureaux.count()
            
            if count >= self.Id_piece.Capacite:
                raise ValidationError(
                    f"La pièce '{self.Id_piece.Nom}' a atteint sa capacité maximale de {self.Id_piece.Capacite} bureau(x). "
                    f"Il y a déjà {count} bureau(x) dans cette pièce."
                )
    
    def save(self, *args, **kwargs):
        """Appeler clean() avant de sauvegarder"""
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Bureau {self.Id_bureau} - {self.get_Type_display()}"

    class Meta:
        verbose_name = "Bureau"
        verbose_name_plural = "Bureaux"
        ordering = ['Id_piece', 'Id_bureau']


class Reservation(models.Model):
    """Modèle pour les réservations"""
    class TypeReservation(models.IntegerChoices):
        REUNION = 0, "Réunion"
        BUREAU = 1, "Réservation de bureau"

    Id_reservation = models.AutoField(primary_key=True)
    Type = models.IntegerField(choices=TypeReservation.choices, default=TypeReservation.BUREAU)
    Nom = models.CharField(max_length=100)
    Debut = models.DateTimeField()
    Fin = models.DateTimeField()
    Id_Matricule = models.ForeignKey('ILIA.Personne', on_delete=models.CASCADE, related_name='reservations')
    Id_bureau = models.ForeignKey(Bureau, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations')
    Id_piece = models.ForeignKey(Piece, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations')

    def __str__(self):
        return f"{self.Nom} - {self.get_Type_display()} ({self.Debut.strftime('%d/%m/%Y %H:%M')})"

    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
        ordering = ['-Debut']

class LiberationBureau(models.Model):
    """Modèle pour tracker les jours où un propriétaire libère son bureau"""
    Id_liberation = models.AutoField(primary_key=True)
    Id_Matricule = models.ForeignKey('ILIA.Personne', on_delete=models.CASCADE, related_name='liberations_bureau')
    Id_bureau = models.ForeignKey(Bureau, on_delete=models.CASCADE, related_name='liberations')
    Date = models.DateField()  # Une ligne par jour libéré
    Date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('Id_Matricule', 'Id_bureau', 'Date')
        verbose_name = "Libération de bureau"
        verbose_name_plural = "Libérations de bureau"
        ordering = ['-Date_creation']

    def __str__(self):
        return f"{self.Id_Matricule} - {self.Id_bureau} ({self.Date})"

class PersonneReservation(models.Model):
    """Table de liaison pour les participants d'une réservation"""
    Id_Matricule = models.ForeignKey('ILIA.Personne', on_delete=models.CASCADE, related_name='participations_reservations')
    Id_reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='participants')
    Valide = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.Id_Matricule} - {self.Id_reservation}"

    class Meta:
        unique_together = ('Id_Matricule', 'Id_reservation')
        verbose_name = "Participant à une réservation"
        verbose_name_plural = "Participants aux réservations"
