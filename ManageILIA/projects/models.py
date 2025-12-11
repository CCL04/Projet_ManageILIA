from django.db import models


class Projet(models.Model):
    class TypeProjet(models.IntegerChoices):
        ENSEIGNEMENT = 0, "Enseignement"
        RECHERCHE = 1, "Recherche"
        SERVICESOCIETE = 2, "Service à la societé"

    Id_projet = models.AutoField(primary_key=True)
    Nom_projet = models.CharField(max_length=200)
    Description = models.TextField(blank=True, null=True)
    Type = models.IntegerField(choices=TypeProjet.choices, default= TypeProjet.ENSEIGNEMENT)
    Image_projet = models.BinaryField(null=True, blank=True)
    createur = models.ForeignKey('ILIA.Personne', on_delete=models.SET_NULL, null=True, blank=True, related_name='projets_crees')

    @property
    def couleur_defaut(self):
        """Retourne la classe CSS de la couleur par défaut basée sur l'ID"""
        index = self.Id_projet % 4
        return f"bg-defaut-{index}"

class PersonneProjet(models.Model):
    Id_Matricule = models.ForeignKey('ILIA.Personne', on_delete=models.CASCADE)
    Id_projet = models.ForeignKey(Projet, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('Id_Matricule', 'Id_projet')


class Fichier(models.Model):
    Id_fichier = models.AutoField(primary_key=True)
    Nom = models.CharField(max_length=255)
    Description = models.CharField(max_length=500, blank=True)
    Date_publication = models.DateTimeField(auto_now_add=True)
    fichier_contenu = models.BinaryField(null=True, blank=True)  # Stockage BLOB en base de données
    fichier_type = models.CharField(max_length=100, default='application/octet-stream')  # MIME type
    Id_Matricule = models.ForeignKey('ILIA.Personne', on_delete=models.CASCADE)
    Id_projet = models.ForeignKey('projects.Projet', on_delete=models.CASCADE)

class PersonneFichier(models.Model):
    Id_Matricule = models.ForeignKey('ILIA.Personne', on_delete=models.CASCADE)
    Id_fichier = models.ForeignKey(Fichier, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('Id_Matricule', 'Id_fichier')