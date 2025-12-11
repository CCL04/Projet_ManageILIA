from django import forms
from .models import Reservation


class ReservationBureauRapideForm(forms.Form):
    """Formulaire simple pour libérer un bureau pour certaines dates"""
    Date_debut = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='Date de début'
    )
    Date_fin = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label='Date de fin'
    )

    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('Date_debut')
        date_fin = cleaned_data.get('Date_fin')

        if date_debut and date_fin:
            if date_fin < date_debut:
                raise forms.ValidationError("La date de fin doit être après la date de début.")

        return cleaned_data