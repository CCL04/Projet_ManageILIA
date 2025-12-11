from django import forms
from django.utils import timezone
from .models import Event
from ILIA.models import Personne, Notification, PersonneNotification, Role
from .models import Participant


class EventCreateForm(forms.ModelForm):
    start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],
        label="Date de début",
    )
    end = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],
        label="Date de fin",
    )
    invited_matricules = forms.IntegerField(
        required=False,
        label="Ou par matricule",
    )
    invited_names = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ex: Jean Dupont'}),
        label="Ou rechercher par prénom nom",
    )

    co_organisers = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Personne.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '6'}),
        label="Co-organisateurs",
        help_text="Sélectionnez une ou plusieurs personnes parmi la liste pour les rendre co-organisateurs.",
    )

    invited_roles = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        label="Ajouter par rôle",
        help_text="Sélectionnez un rôle pour ajouter toutes les personnes avec ce rôle",
    )

    class Meta:
        model = Event
        fields = ['title', 'description', 'start', 'end', 'co_organisers']
        labels = {
            'title': 'Titre',
            'description': 'Description',
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start')
        end = cleaned.get('end')
        if start and end:
            if end <= start:
                raise forms.ValidationError("La date de fin doit être après la date de début.")
            if start < timezone.now():
                pass
        return cleaned

    def save(self, commit=True, creator_personne=None):
        """
        Save the event WITHOUT creating participants.
        Participants are now managed separately via the session in the view.
        """

        event = super().save(commit=False)
        if creator_personne:
            event.organiser = creator_personne
        if commit:
            event.save()

            # set co-organisers (ModelMultipleChoice)
            co_orgs = self.cleaned_data.get('co_organisers')
            if co_orgs is not None:
                event.co_organisers.set(co_orgs)

        return event
