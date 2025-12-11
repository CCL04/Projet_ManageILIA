from django import forms
from .models import PersonalScheduleEntry, RecurringTelework
from datetime import datetime, timedelta

class PersonalScheduleEntryForm(forms.ModelForm):
    class Meta:
        model = PersonalScheduleEntry
        fields = ['title', 'start_datetime', 'end_datetime', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre de l\'événement'}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Description (optionnelle)', 'rows': 3}),
        }
        labels = {
            'title': 'Titre',
            'start_datetime': 'Date et heure de début',
            'end_datetime': 'Date et heure de fin',
            'description': 'Description',
        }


class RecurringTeleworkForm(forms.ModelForm):
    class Meta:
        model = RecurringTelework
        fields = ['day_of_week', 'start_date', 'end_date']
        widgets = {
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'day_of_week': 'Jour de la semaine',
            'start_date': 'Date de début de la répétition',
            'end_date': 'Date de fin de la répétition',
        }