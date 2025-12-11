from django.utils import timezone
from datetime import timedelta
from ILIA.models import Personne, Role, Notification, PersonneNotification

def check_contract_expiration():
    """Vérifie les contrats expirant et envoie des notifications"""
    aujourd_hui = timezone.now().date()
    date_limite = aujourd_hui + timedelta(days=30)

    personnes_a_notifier = Personne.objects.filter(
        Date_fin__lte=date_limite,
        Date_fin__gte=aujourd_hui
    ).exclude(Date_fin__isnull=True)

    try:
        role_admin = Role.objects.get(nom="Administrateur")
        administrateurs = Personne.objects.filter(Id_role=role_admin)
    except Role.DoesNotExist:
        administrateurs = Personne.objects.filter(user__is_staff=True)

    for personne in personnes_a_notifier:
        notification_existante = Notification.objects.filter(
            Titre__contains=f"Fin de contrat : {personne.Prenom} {personne.Nom}",
            Type="CONTRAT_EXPIRE"
        ).exists()

        if not notification_existante:
            titre = f"Fin de contrat : {personne.Prenom} {personne.Nom}"
            jours_restants = (personne.Date_fin - aujourd_hui).days

            contenu = (
                f"⚠️ La personne {personne.Prenom} {personne.Nom} "
                f"(Matricule: {personne.Id_Matricule}) arrive à la fin de son contrat.\n\n"
                f"Date de fin : {personne.Date_fin.strftime('%d/%m/%Y')}\n"
                f"Jours restants : {jours_restants}\n"
            )

            notification = Notification.objects.create(
                Titre=titre,
                Contenu=contenu,
                Type="CONTRAT_EXPIRE"
            )

            for admin in administrateurs:
                PersonneNotification.objects.get_or_create(
                    Id_Matricule=admin,
                    Id_notif=notification
                )