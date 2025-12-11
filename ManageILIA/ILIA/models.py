from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator



class Role(models.Model):
    Id_role = models.AutoField(primary_key=True)
    Nom_role = models.CharField(max_length=100)

    def __str__(self):
        return self.Nom_role



class Personne (models.Model):
    #créer un lien 1-1 entre classe personne et classe user fournis par django
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    Id_Matricule = models.IntegerField(primary_key=True, validators=[MinValueValidator(100000), MaxValueValidator(999999)],verbose_name="Matricule")
    Nom = models.CharField(max_length=100)
    Prenom = models.CharField(max_length=100)
    Mot_de_passe = models.CharField(max_length=128)
    Email = models.EmailField(unique=True)
    Service = models.CharField(max_length=100, blank=True, null=True)
    Departement = models.CharField(max_length=100, blank=True, null=True)
    Universite = models.CharField(max_length=100, blank=True, null=True)
    Date_fin = models.DateField(blank=True, null=True)
    Photo = models.BinaryField(null=True, blank=True, editable=True)
    Id_bureau = models.ForeignKey('reservations.Bureau', on_delete=models.SET_NULL, null=True, blank=True)
    Id_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    roles = models.ManyToManyField(Role, related_name='personnes', blank=True)

    def __str__(self):
        return f"{self.Prenom} {self.Nom}"


class Notification(models.Model):
    Id_notif = models.AutoField(primary_key=True)
    Titre = models.CharField(max_length=200)
    Contenu = models.TextField()
    Type = models.CharField(max_length=50)
    Date = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.Titre} - {self.Type}"

class PersonneNotification(models.Model):
    Id_Matricule = models.ForeignKey(Personne, on_delete=models.CASCADE)
    Id_notif = models.ForeignKey(Notification, on_delete=models.CASCADE)
    Date_notif = models.DateTimeField(auto_now_add=True)
    Lu = models.BooleanField(default=False)

    class Meta:
        unique_together = ('Id_Matricule', 'Id_notif')
    
    def __str__(self):
        return f"{self.Id_Matricule} - {self.Id_notif.Titre}"
