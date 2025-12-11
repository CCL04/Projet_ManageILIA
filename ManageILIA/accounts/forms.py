from django import forms
from django.contrib.auth.models import User
from ILIA.models import Personne,Role

def get_roles_choices():
    """
    Dynamically retrieves role choices from the database.
    Returns a list of tuples (Id_role, Nom_role) for use in form fields.
    """
    return [(role.Id_role, role.Nom_role) for role in Role.objects.all()]

class RegistrationForm(forms.ModelForm):
    """
    Class used to define a model form for user registration. The form is tied to the
    Personne model and incorporates custom password and role field handling.

    This form is used to collect and validate specific user information for
    registration, including matricule, name, email, and role-based data, while
    enforcing constraints like password validation and unique matricule checking.

    :ivar password1: First password field that accepts user input securely.
    :ivar password2: Second password confirmation field to verify password match.
    :ivar roles: Multiple choice field for role selection, rendered as checkboxes.
    """
    password1 = forms.CharField(label = "Mot de passe" , widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label = "Confirmer mot de passe" , widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    roles = forms.MultipleChoiceField(
        choices=[],  # Will be populated in __init__
        widget=forms.CheckboxSelectMultiple(),
        label="Rôles",
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['roles'].choices = get_roles_choices()

    class Meta:
        model = Personne
        fields = ['Id_Matricule','Nom','Prenom','Email','Service','Departement','Universite','Date_fin']
        widgets = {
            'Id_Matricule' : forms.TextInput(attrs={'class': 'form-control'}),
            "Nom" : forms.TextInput(attrs={'class': 'form-control'}),
            "Prenom" : forms.TextInput(attrs={'class': 'form-control'}),
            "Email" : forms.EmailInput(attrs={'class': 'form-control'}),
            "Service" : forms.TextInput(attrs={'class': 'form-control'}),
            "Departement" : forms.TextInput(attrs={'class': 'form-control'}),
            "Universite" : forms.TextInput(attrs={'class': 'form-control'}),
            "Date_fin" : forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'Id_Matricule': 'Matricule',
            'Nom': 'Nom',
            'Prenom': 'Prénom',
            'Email': 'Email',
            'Service': 'Service',
            'Departement': 'Département',
            'Universite': 'Université',
            'Date_fin': 'Date de fin (optionnelle)',
        }


    def clean_Email(self):
        email = self.cleaned_data.get("Email")
        if User.objects.filter(email=email).exists(): raise forms.ValidationError("Cet Email est deja utilisé")

        return email

    def clean(self,commit=True):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2","Les mots de passes ne correspondent pas ")

        return cleaned

    def clean_Id_Matricule(self):
        matricule = self.cleaned_data['Id_Matricule']

        try :
            value = int(matricule)
        except (TypeError,ValueError):
            raise forms.ValidationError("Le matricule doit être un nombre à 6 chiffres ")
        if value < 100000 or value > 999999:
            raise forms.ValidationError("Le matricule doit être un nombre à 6 chiffres ")

        if Personne.objects.filter(Id_Matricule=matricule).exists():
            raise forms.ValidationError("Ce matricule est déjà utilisé ")

        return value

    def save(self, commit=True):
        cleaned = self.cleaned_data
        #on crée user en attente de validation par admin
        username = f"{cleaned.get('Prenom', '')}{cleaned.get('Nom', '')}"
        user = User.objects.create_user(
            username= username,
            email=cleaned.get("Email"),
            password=cleaned.get("password1"),
        )
        user.first_name = cleaned.get("Prenom", "")
        user.last_name = cleaned.get("Nom", "")
        user.is_active = False
        user.save()

        personne = super().save(commit=False)
        personne.user = user
        personne.Mot_de_passe = cleaned.get("password1", "")
        if commit:
            personne.save()
            # Les rôles sélectionnés sont déjà des Id_role (entiers)
            role_ids = [int(role_id) for role_id in cleaned.get("roles", [])]
            roles = Role.objects.filter(Id_role__in=role_ids)
            personne.roles.set(roles)

        return user

class ProfilePhotoForm(forms.Form):
    photo_file = forms.FileField(
        label="Choisir une photo",
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )

    def clean_photo_file(self):
        file = self.cleaned_data.get('photo_file')
        # Vérification de la taille (5MB)
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Fichier trop volumineux")
        return file
