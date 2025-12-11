from django import forms
from ILIA.models import  Personne, Role
from projects.models import Projet, Fichier

class ProjetForm(forms.ModelForm):
    image_file = forms.FileField(
        label = "Image de couverture",
        required = False,
        widget=forms.FileInput(attrs={'accept': 'image/*', 'class': 'form-control'})
    )
    class Meta:
        model = Projet
        fields = ['Nom_projet', 'Description', 'Type']


class UploadFichierForm(forms.Form):
    Nom = forms.CharField(
        max_length=255,
        label="Nom du fichier",
        widget=forms.TextInput(attrs={'placeholder': 'Nom du fichier', 'required': True})
    )
    Description = forms.CharField(
        max_length=500,
        required=False,
        label="Description(optionnel)",
        widget=forms.TextInput(attrs={'placeholder': 'Description du fichier'})
    )
    fichier = forms.FileField(
        label="Fichier",
        widget=forms.FileInput(attrs={'accept': '*/*', 'required': True})
    )


class AjouterPersonneForm(forms.Form):
    matricule = forms.IntegerField(required=False, label="Matricule")
    username = forms.CharField(required=False, label="Prénom Nom", widget=forms.TextInput(attrs={'placeholder': 'Ex: Jean Dupont'}))
    role = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        required=False,
        label="Ajouter par rôle",
        widget=forms.CheckboxSelectMultiple(),
        help_text="Sélectionnez un rôle pour ajouter toutes les personnes avec ce rôle"
    )

    def clean(self):
        cleaned_data = super().clean()
        matricule = cleaned_data.get("matricule")
        username = cleaned_data.get("username")
        role = cleaned_data.get("role")

        # Vérifier qu'au moins un mode d'identification est rempli
        if not matricule and not username and not role:
            raise forms.ValidationError(
                "Veuillez entrer soit un matricule, soit un prénom et un nom, soit sélectionner un rôle."
            )

        # Recherche par rôle (retourne une liste de personnes)
        if role:
            personnes = Personne.objects.filter(roles__in=role)
            if not personnes.exists():
                raise forms.ValidationError(f"Aucune personne trouvée avec le rôle '{role.Nom_role}'.")
            cleaned_data["personnes"] = personnes
            cleaned_data["personne"] = None
            return cleaned_data

        # Recherche par matricule
        if matricule:
            try:
                personne = Personne.objects.get(Id_Matricule=matricule)
                cleaned_data["personne"] = personne
                cleaned_data["personnes"] = None
            except Personne.DoesNotExist:
                raise forms.ValidationError("Aucune personne trouvée avec ce matricule.")

        # Recherche par prénom + nom
        elif username:
            # Séparer le prénom et le nom
            parts = username.strip().split()
            if len(parts) < 2:
                raise forms.ValidationError("Veuillez entrer au minimum un prénom et un nom.")
            
            prenom = parts[0]
            nom = ' '.join(parts[1:])
            
            personnes = Personne.objects.filter(Nom__iexact=nom, Prenom__iexact=prenom)
            if not personnes.exists():
                raise forms.ValidationError(f"Aucune personne trouvée avec le nom '{nom}' et le prénom '{prenom}'.")
            if personnes.count() > 1:
                raise forms.ValidationError(
                    "Plusieurs personnes trouvées : veuillez utiliser le matricule."
                )

            cleaned_data["personne"] = personnes.first()
            cleaned_data["personnes"] = None

        return cleaned_data
