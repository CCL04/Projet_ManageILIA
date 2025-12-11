from ILIA.models import PersonneNotification, Personne
from django.core.exceptions import ObjectDoesNotExist


def unread_notifications_count(request):
    """
    Context processor pour ajouter le nombre de notifications non lues
    """
    count = 0

    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            personne = Personne.objects.get(user=request.user)

            count = PersonneNotification.objects.filter(
                Id_Matricule=personne,
                Lu=False
            ).count()

        except ObjectDoesNotExist:
            count = 0


    return {'unread_notifications_count': count}
