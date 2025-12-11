from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from ILIA.models import Notification, PersonneNotification, Personne
from .forms import NotificationForm, AjouterPersonneForm
from events.models import Event, Participant
import re


@login_required
def notification_list(request):
    """Affiche la liste de toutes les notifications"""
    notifications = Notification.objects.all().order_by('-Date')
    context = {
        'notifications': notifications
    }
    return render(request, 'notifications/mes_notifications.html', context)


@login_required
def mes_notifications(request):
    """Affiche les notifications de l'utilisateur connecté"""
    try:
        personne = Personne.objects.get(user=request.user)
        
        # Gestion de la suppression multiple
        if request.method == 'POST':
            notif_ids = request.POST.getlist('notif_ids')
            if notif_ids:
                PersonneNotification.objects.filter(
                    Id_Matricule=personne,
                    Id_notif__Id_notif__in=notif_ids
                ).delete()
                for n_id in notif_ids:
                    # On vérifie s'il reste des liens pour cette ID de notif
                    if not PersonneNotification.objects.filter(Id_notif_id=n_id).exists():
                        # Si vide, on essaie de supprimer la notification parente
                        try:
                            Notification.objects.filter(Id_notif=n_id).delete()
                        except Notification.DoesNotExist:
                            pass  # Déjà supprimée
                return redirect('mes_notifications')
        
        notifications_personne = PersonneNotification.objects.filter(
            Id_Matricule=personne
        ).select_related('Id_notif').order_by('-Date_notif')
        
        # Pour chaque notification, vérifier si c'est un événement et récupérer le participant
        notifications_with_events = []
        for notif_pers in notifications_personne:
            event = None
            participant = None
            
            if "Invitation à l'événement" in notif_pers.Id_notif.Titre:
                event_title = notif_pers.Id_notif.Titre.replace("Invitation à l'événement : ", "")
                event = Event.objects.filter(title=event_title).first()
                if event:
                    participant = Participant.objects.filter(event=event, person=personne).first()
            
            notifications_with_events.append({
                'notif_personne': notif_pers,
                'event': event,
                'participant': participant
            })
        
        context = {
            'notifications_with_events': notifications_with_events
        }
        return render(request, 'notifications/mes_notifications.html', context)
    except Personne.DoesNotExist:
        messages.error(request, "Profil utilisateur non trouvé.")
        return redirect('home')


@login_required
def notification_detail(request, notif_id):
    """Affiche les détails d'une notification"""
    notification = get_object_or_404(Notification, Id_notif=notif_id)
    try:
        personne = Personne.objects.get(user=request.user)

        # On récupère le lien spécifique entre cette personne et cette notif
        notif_personne = PersonneNotification.objects.filter(
            Id_notif=notification,
            Id_Matricule=personne
        ).first()

        # Si le lien existe et n'est pas encore lu, on le marque comme lu
        if notif_personne and not notif_personne.Lu:
            notif_personne.Lu = True
            notif_personne.save()

    except Personne.DoesNotExist:
        pass
    # Récupérer tous les destinataires de cette notification
    destinataires = PersonneNotification.objects.filter(
        Id_notif=notification
    ).select_related('Id_Matricule')
    
    # Vérifier si c'est une notification d'événement et extraire l'ID de l'événement
    event = None
    participant = None
    
    try:
        personne = Personne.objects.get(user=request.user)
        
        import re
        match = re.search(r"ID de l'événement\s*:\s*(\d+)", notification.Contenu)
        if match:
            event_id = int(match.group(1))
            event = Event.objects.filter(id=event_id).first()
            if event:
                participant = Participant.objects.filter(event=event, person=personne).first()
                print(f"DEBUG notification_detail: Event trouvé {event.title}, Participant status: {participant.status if participant else 'None'}")
    except Personne.DoesNotExist:
        pass
    except Exception as e:
        print(f"DEBUG notification_detail: Erreur {e}")
    
    context = {
        'notification': notification,
        'destinataires': destinataires,
        'event': event,
        'participant': participant
    }
    return render(request, 'notifications/notification_detail.html', context)


# DANS views.py

@login_required
def notification_create(request):
    """Crée une nouvelle notification"""
    if 'recipients_temp' not in request.session:
        request.session['recipients_temp'] = []

    # On initialise les formulaires
    form = NotificationForm()
    personne_form = AjouterPersonneForm()

    if request.method == 'POST':
        form = NotificationForm(request.POST)

        # 1. Gérer la suppression d'un destinataire
        if 'remove_personne' in request.POST:
            recipient_id = request.POST.get('remove_personne')
            if 'recipients_temp' in request.session:
                request.session['recipients_temp'] = [
                    r for r in request.session['recipients_temp']
                    if str(r['id']) != str(recipient_id)
                ]
                request.session.modified = True


            personne_form = AjouterPersonneForm()

        # 2. Gérer l'ajout de personnes (Logique identique à creer_projet)
        elif 'ajouter_personne' in request.POST:
            personne_form = AjouterPersonneForm(request.POST)
            if personne_form.is_valid():
                # Récupération des données nettoyées par le clean() de AjouterPersonneForm
                personnes_role = personne_form.cleaned_data.get('personnes')
                personne_unique = personne_form.cleaned_data.get('personne')

                new_recipients = []

                # Cas 1 : Ajout par rôle (plusieurs personnes)
                if personnes_role:
                    for p in personnes_role:
                        new_recipients.append({
                            'id': p.Id_Matricule,
                            'nom': p.Nom,
                            'prenom': p.Prenom,
                            'email': p.Email
                        })

                # Cas 2 : Ajout individuel
                elif personne_unique:
                    new_recipients.append({
                        'id': personne_unique.Id_Matricule,
                        'nom': personne_unique.Nom,
                        'prenom': personne_unique.Prenom,
                        'email': personne_unique.Email
                    })

                # Ajout à la session sans doublons
                if 'recipients_temp' not in request.session:
                    request.session['recipients_temp'] = []

                count_added = 0
                current_ids = [r['id'] for r in request.session['recipients_temp']]

                for recipient in new_recipients:
                    if recipient['id'] not in current_ids:
                        request.session['recipients_temp'].append(recipient)
                        current_ids.append(
                            recipient['id'])  # Mettre à jour la liste locale pour éviter doublons internes
                        count_added += 1

                request.session.modified = True

                if count_added > 0:
                    messages.success(request, f"{count_added} destinataire(s) ajouté(s).")
                else:
                    messages.info(request, "Ces destinataires sont déjà dans la liste.")

                # Réinitialiser le formulaire d'ajout après succès
                personne_form = AjouterPersonneForm()
            else:
                messages.error(request, "Erreur lors de l'ajout du participant.")

        # 3. Envoi final du message
        elif 'envoyer_message' in request.POST:
            if form.is_valid():
                recipients_temp = request.session.get('recipients_temp', [])

                if not recipients_temp:
                    messages.error(request, "Vous devez ajouter au moins un destinataire.")
                else:
                    notification = form.save()

                    # Création des liens PersonneNotification
                    count_total = 0
                    for recipient_data in recipients_temp:
                        try:
                            p = Personne.objects.get(Id_Matricule=recipient_data['id'])
                            PersonneNotification.objects.create(
                                Id_Matricule=p,
                                Id_notif=notification
                            )
                            count_total += 1
                        except Personne.DoesNotExist:
                            pass

                    messages.success(request, f"Notification envoyée à {count_total} personne(s).")

                    # Nettoyage de la session
                    if 'recipients_temp' in request.session:
                        del request.session['recipients_temp']

                    return redirect('notification_detail', notif_id=notification.Id_notif)
            else:
                messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")


    recipients_temp = request.session.get('recipients_temp', [])

    context = {
        'form': form,
        'personne_form': personne_form,
        'recipients_temp': recipients_temp,
        'edit_mode': False
    }
    return render(request, 'notifications/notification_form.html', context)


@login_required
def respond_event_invitation(request, notif_id):
    """Permet de répondre à une invitation d'événement depuis une notification"""
    if request.method != 'POST':
        return redirect('notification_detail', notif_id=notif_id)
    
    notification = get_object_or_404(Notification, Id_notif=notif_id)
    action = request.POST.get('action')
    
    try:
        personne = Personne.objects.get(user=request.user)
        
        # Chercher l'ID de l'événement dans le contenu
        match = re.search(r"ID de l'événement\s*:\s*(\d+)", notification.Contenu)
        if not match:
            messages.error(request, "ID de l'événement introuvable dans la notification.")
            return redirect('mes_notifications')
        
        event_id = int(match.group(1))
        event = Event.objects.filter(id=event_id).first()
        
        if not event:
            messages.error(request, "Événement introuvable.")
            return redirect('mes_notifications')
        
        participant = Participant.objects.filter(event=event, person=personne).first()
        
        if not participant:
            messages.error(request, "Vous n'êtes pas invité à cet événement.")
            return redirect('mes_notifications')
        
        print(f"DEBUG respond: Event {event.title}, Participant status avant: {participant.status}, Action: {action}")
        
        if action == 'accept':
            participant.status = Participant.Status.ACCEPTED
            participant.save(update_fields=['status'])
            participant.refresh_from_db()
            print(f"DEBUG respond: Participant status après save et refresh: {participant.status}")



            # Suppression de la notification pour cet utilisateur
            PersonneNotification.objects.filter(Id_notif=notification, Id_Matricule=personne).delete()
            
        elif action == 'decline':
            participant.status = Participant.Status.DECLINED
            participant.save(update_fields=['status'])
            participant.refresh_from_db()
            
            # Supprimer également la notification après refus
            PersonneNotification.objects.filter(Id_notif=notification, Id_Matricule=personne).delete()
        
    except Personne.DoesNotExist:
        messages.error(request, "Profil utilisateur non trouvé.")
    
    return redirect('mes_notifications')




@login_required
def notification_delete(request, notif_id):
    """
    Gère la suppression via POST uniquement (car confirmation via Pop-up).
    Si on accède via GET, on renvoie simplement vers le détail.
    """
    notification = get_object_or_404(Notification, Id_notif=notif_id)

    # 1. Gestion de la suppression (Méthode POST venant du Pop-up)
    if request.method == 'POST':
        try:
            personne = Personne.objects.get(user=request.user)

            # Supprimer le lien pour cet utilisateur
            deleted_count, _ = PersonneNotification.objects.filter(
                Id_notif=notification,
                Id_Matricule=personne
            ).delete()

            if deleted_count > 0:


                # Nettoyage des orphelins (si plus personne n'a la notif)
                if not PersonneNotification.objects.filter(Id_notif=notification).exists():
                    notification.delete()
            else:
                messages.warning(request, "Cette notification n'était déjà plus dans votre liste.")

            return redirect('mes_notifications')

        except Personne.DoesNotExist:
            messages.error(request, "Profil introuvable.")
            return redirect('home')


    messages.warning(request, "Action invalide. Veuillez utiliser le bouton de suppression.")
    return redirect('notification_detail', notif_id=notif_id)