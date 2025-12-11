from django import forms
from ILIA.models import Notification, Personne, Role


class NotificationForm(forms.ModelForm):
    """Formulaire pour créer et modifier le contenu de la notification"""

    class Meta:
        model = Notification
        fields = ['Titre', 'Type', 'Contenu']  # On enlève les champs de destinataires d'ici
        widgets = {
            'Titre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de la notification'
            }),
            'Contenu': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Contenu de la notification'
            }),
            'Type': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'Titre': 'Titre',
            'Contenu': 'Contenu',
            'Type': 'Type de notification'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['Type'].initial = 'GENERAL'


# 2. Le formulaire pour rechercher/ajouter des gens (IDENTIQUE À PROJET)
class AjouterPersonneForm(forms.Form):
    matricule = forms.IntegerField(
        required=False,
        label="Matricule",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 123456'})
    )
    username = forms.CharField(
        required=False,
        label="Prénom Nom",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Jean Dupont'})
    )
    role = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        required=False,
        label="Ajouter par rôle",
        widget=forms.CheckboxSelectMultiple(),
        help_text="Cochez pour ajouter tous les membres de ce rôle"
    )

    def clean(self):
        cleaned_data = super().clean()
        matricule = cleaned_data.get("matricule")
        username = cleaned_data.get("username")
        role = cleaned_data.get("role")

        # Vérifier qu'au moins un champ est rempli
        if not matricule and not username and not role:
            raise forms.ValidationError(
                "Veuillez entrer un matricule, un nom, ou sélectionner un rôle."
            )

        # 1. Recherche par rôle (retourne une liste)
        if role:
            personnes = Personne.objects.filter(roles__in=role)
            if not personnes.exists():
                raise forms.ValidationError(f"Aucune personne trouvée avec ce(s) rôle(s).")
            cleaned_data["personnes"] = personnes
            cleaned_data["personne"] = None
            return cleaned_data

        # 2. Recherche par matricule (prioritaire sur le nom)
        if matricule:
            try:
                personne = Personne.objects.get(Id_Matricule=matricule)
                cleaned_data["personne"] = personne
                cleaned_data["personnes"] = None
            except Personne.DoesNotExist:
                raise forms.ValidationError("Aucune personne trouvée avec ce matricule.")

        # 3. Recherche par Prénom Nom
        elif username:
            parts = username.strip().split()
            if len(parts) < 2:
                raise forms.ValidationError("Veuillez entrer 'Prénom Nom' complet.")

            prenom = parts[0]
            nom = ' '.join(parts[1:])

            # Recherche insensible à la casse
            personnes = Personne.objects.filter(Nom__iexact=nom, Prenom__iexact=prenom)

            if not personnes.exists():
                # On tente l'inverse (Nom Prénom) au cas où
                personnes = Personne.objects.filter(Nom__iexact=prenom, Prenom__iexact=nom)

            if not personnes.exists():
                raise forms.ValidationError(f"Aucune personne trouvée pour '{username}'.")

            if personnes.count() > 1:
                raise forms.ValidationError(
                    "Plusieurs personnes trouvées avec ce nom. Utilisez le matricule."
                )

            cleaned_data["personne"] = personnes.first()
            cleaned_data["personnes"] = None

        return cleaned_data