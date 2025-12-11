from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin

# ... existing code ...

from timetable.models import PersonalSchedule, RecurringTelework
from ILIA.models import Personne
from django.utils import timezone


class HomeView(LoginRequiredMixin, View):
    login_url = 'login'
    redirect_field_name = 'next'

    def get(self, request):
        # Récupérer la personne actuelle
        personne = Personne.objects.filter(user=request.user).first()

        # Récupérer tous les utilisateurs
        all_users = Personne.objects.all().order_by('Prenom', 'Nom')

        # Déterminer le statut de chaque utilisateur (sur place ou télétravail)
        users_status = []
        today = timezone.now().date()
        today_weekday = today.weekday()  # 0 = lundi, 6 = dimanche

        for user in all_users:
            # Vérifier si l'utilisateur est en télétravail aujourd'hui
            is_teleworking = False

            if user.user:
                # Récupérer le schedule de l'utilisateur
                schedule = PersonalSchedule.objects.filter(user=user.user).first()
                if schedule:
                    # Vérifier s'il y a un télétravail récurrent pour aujourd'hui
                    is_teleworking = RecurringTelework.objects.filter(
                        schedule=schedule,
                        day_of_week=today_weekday,
                        start_date__lte=today,
                        end_date__gte=today
                    ).exists()

            status = 'telework' if is_teleworking else 'present'
            users_status.append({
                'personne': user,
                'user_id': user.user.id if user.user else None,  # Ajouter cette ligne
                'status': status,
                'display_name': f"{user.Prenom} {user.Nom}"
            })

            users_status = sorted(
                users_status,
                key=lambda u: (u['status'], u['personne'].Prenom.lower(), u['personne'].Nom.lower())
            )

        context = {
            'personne': personne,
            'users_status': users_status,
        }
        return render(request, 'home.html', context)