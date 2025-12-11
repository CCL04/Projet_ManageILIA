from django.db import models
from django.contrib.auth.models import User

#correspond a la table associative entre reccuring telework et personne.
class PersonalSchedule(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Horaire personnel de {self.user.username}"

class PersonalScheduleEntry(models.Model):
    schedule = models.ForeignKey(PersonalSchedule, on_delete=models.CASCADE, related_name="entries")
    title = models.CharField(max_length=200, help_text="Titre de l'événement", default="")
    description = models.TextField(help_text="Description de l'événement", blank=True, default="")
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_datetime"]

    def __str__(self):
        return f"{self.title} - {self.start_datetime}"

class RecurringTelework(models.Model):
    schedule = models.ForeignKey(PersonalSchedule, on_delete=models.CASCADE, related_name="recurring_teleworks")
    day_of_week = models.IntegerField(choices=[
        (0, 'Lundi'),
        (1, 'Mardi'),
        (2, 'Mercredi'),
        (3, 'Jeudi'),
        (4, 'Vendredi'),
        (5, 'Samedi'),
        (6, 'Dimanche'),
    ], help_text="Jour de la semaine", null=True, blank=True)
    start_date = models.DateField(help_text="Date de début de la répétition", null=True, blank=True)
    end_date = models.DateField(help_text="Date de fin de la répétition", null=True, blank=True)

    class Meta:
        ordering = ["start_date", "day_of_week"]

    def __str__(self):
        if self.day_of_week is not None and self.start_date and self.end_date:
            days = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
            return f"{days[self.day_of_week]} - du {self.start_date} au {self.end_date}"
        return "Télétravail non configuré"