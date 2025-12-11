from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView
from django.views import View
import random
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Event, Participant
from .forms import EventCreateForm
from ILIA.models import Personne, Notification, PersonneNotification
from django.contrib import messages
from django.utils import timezone


class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    
    def get_queryset(self):
        now = timezone.localtime(timezone.now())
        deleted_count, _ = Event.objects.filter(end__lt=now).delete()
        if deleted_count > 0:
            messages.info(self.request, f"{deleted_count} événement(s) passé(s) supprimé(s) automatiquement.")
        return Event.objects.all()


class EventDetailView(DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'
    
    def get(self, request, *args, **kwargs):
        # Supprimer automatiquement les événements passés
        now = timezone.localtime(timezone.now())
        Event.objects.filter(end__lt=now).delete()
        
        try:
            event = self.get_object()
        except:
            messages.error(request, "Cet événement n'existe plus (événement passé).")
            return redirect('events:dashboard')
        
        return super().get(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'events/event_dashboard.html'

    def get_personne(self):
        if not self.request.user.is_authenticated:
            return None
        return Personne.objects.filter(user=self.request.user).first()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        personne = self.get_personne()
        now = timezone.localtime(timezone.now())
        
        # Supprimer automatiquement les événements passés
        deleted_count, _ = Event.objects.filter(end__lt=now).delete()
        if deleted_count > 0:
            messages.info(self.request, f"{deleted_count} événement(s) passé(s) supprimé(s) automatiquement.")
        
        if personne:
            # Events created by me
            created = Event.objects.filter(organiser=personne).order_by('-start')
            # Events where I am a participant and accepted, and not created by me
            accepted = Event.objects.filter(participants__person=personne, participants__status=Participant.Status.ACCEPTED).exclude(organiser=personne).distinct()
            # Invitations pending
            pending_parts = Participant.objects.filter(person=personne, status=Participant.Status.INVITED).select_related('event')
            pending = [p.event for p in pending_parts]
        else:
            created = Event.objects.none()
            accepted = Event.objects.none()
            pending = []

        ctx.update({
            'created_events': created,
            'accepted_events': accepted,
            'pending_invitations': pending,
            'personne': personne,
        })
        return ctx


class EventCreateView(LoginRequiredMixin, View):
    def get(self, request):
        # Initialiser la session si elle n'existe pas
        if 'invited_temp' not in request.session:
            request.session['invited_temp'] = []
            request.session.modified = True
        if 'event_data' not in request.session:
            request.session['event_data'] = {}
            request.session.modified = True
        
        form = EventCreateForm()
        # Récupérer les participants temporaires de la session
        invited_temp = request.session.get('invited_temp', [])
        return render(request, 'events/event_form.html', {
            'form': form,
            'invited_temp': invited_temp,
            'personnes_temp': invited_temp,
        })

    def post(self, request):
        # Gérer l'ajout d'invités à la session (avant création)
        if 'add_invited' in request.POST or 'ajouter_personne' in request.POST:
            # Sauvegarder les données du formulaire en session
            request.session['event_data'] = {
                'title': request.POST.get('title', ''),
                'description': request.POST.get('description', ''),
                'start': request.POST.get('start', ''),
                'end': request.POST.get('end', ''),
            }
            request.session.modified = True
            
            if 'invited_temp' not in request.session:
                request.session['invited_temp'] = []
            
            invited_matricules = request.POST.get('invited_matricules', '').strip()
            invited_names = request.POST.get('invited_names', '').strip()
            invited_roles = request.POST.getlist('invited_roles')
            
            invited_people = set()
            has_error = False
            
            # Traiter les matricules
            if invited_matricules:
                for mat_str in invited_matricules.split(','):
                    mat_str = mat_str.strip()
                    try:
                        mat = int(mat_str)
                        p = Personne.objects.filter(Id_Matricule=mat).first()
                        if p:
                            invited_people.add(p.Id_Matricule)
                        else:
                            messages.error(request, f"Personne avec le matricule {mat} non trouvée.")
                            has_error = True
                    except (ValueError, TypeError):
                        messages.error(request, f"Matricule invalide : '{mat_str}'. Veuillez entrer des nombres séparés par des virgules.")
                        has_error = True
            
            # Traiter les noms
            if invited_names:
                for name in invited_names.split(';'):
                    name = name.strip()
                    if not name:
                        continue
                    tokens = name.split()
                    if len(tokens) >= 2:
                        prenom, nom = tokens[0], ' '.join(tokens[1:])
                        p = Personne.objects.filter(Prenom__iexact=prenom, Nom__iexact=nom).first()
                        if p:
                            invited_people.add(p.Id_Matricule)
                        else:
                            messages.error(request, f"Personne '{prenom} {nom}' non trouvée.")
                            has_error = True
                    else:
                        messages.error(request, f"Format de nom invalide : '{name}'. Veuillez entrer : Prénom Nom")
                        has_error = True
            
            # Traiter les rôles
            if invited_roles:
                for role_id in invited_roles:
                    try:
                        personnes_by_role = Personne.objects.filter(roles__Id_role=int(role_id))
                        for p in personnes_by_role:
                            invited_people.add(p.Id_Matricule)
                    except (ValueError, TypeError):
                        pass
            
            # Ajouter à la session sans doublons
            added_count = 0
            for mat_id in invited_people:
                p = Personne.objects.get(Id_Matricule=mat_id)
                entry = {
                    'id': p.Id_Matricule,
                    'nom': p.Nom,
                    'prenom': p.Prenom
                }
                # Vérifier qu'il n'existe pas déjà
                if entry not in request.session['invited_temp']:
                    request.session['invited_temp'].append(entry)
                    added_count += 1
            
            if added_count > 0:
                messages.success(request, f"{added_count} participant(s) ajouté(s) avec succès.")
            
            request.session.modified = True
            # Créer un formulaire avec les données sauvegardées
            form = EventCreateForm(initial=request.session['event_data'])
            invited_temp = request.session.get('invited_temp', [])
            return render(request, 'events/event_form.html', {
                'form': form,
                'invited_temp': invited_temp,
                'personnes_temp': invited_temp,
            })
        
        # Gérer la suppression d'un invité
        if 'remove_invited' in request.POST or 'remove_personne' in request.POST:
            invited_id = request.POST.get('remove_invited') or request.POST.get('remove_personne')
            if 'invited_temp' in request.session:
                request.session['invited_temp'] = [
                    p for p in request.session['invited_temp']
                    if str(p['id']) != str(invited_id)
                ]
                request.session.modified = True
            # Créer un formulaire avec les données sauvegardées
            form = EventCreateForm(initial=request.session.get('event_data', {}))
            invited_temp = request.session.get('invited_temp', [])
            return render(request, 'events/event_form.html', {
                'form': form,
                'invited_temp': invited_temp,
                'personnes_temp': invited_temp,
            })
        
        # Créer l'événement
        form = EventCreateForm(request.POST)
        

        personne = Personne.objects.filter(user=request.user).first()
        if not personne:
            # try matching by email
            email = getattr(request.user, 'email', None)
            if email:
                personne = Personne.objects.filter(Email__iexact=email).first()
                if personne:
                    personne.user = request.user
                    personne.save()
        
        if not personne:
            messages.error(request, "Impossible de créer l'événement : votre profil Personne n'a pas pu être trouvé.")
            invited_temp = request.session.get('invited_temp', [])
            return render(request, 'events/event_form.html', {
                'form': form,
                'invited_temp': invited_temp,
                'personnes_temp': invited_temp,
            })

        if form.is_valid():
            # Vérifier qu'il y a au moins des invités en session
            invited_temp = request.session.get('invited_temp', [])
            if not invited_temp:
                messages.error(request, "Vous devez ajouter au moins un invité avant de créer l'événement.")
                # Restaurer le formulaire avec les données POST
                form = EventCreateForm(initial=request.session.get('event_data', {}))
                return render(request, 'events/event_form.html', {
                    'form': form,
                    'invited_temp': invited_temp,
                    'personnes_temp': invited_temp,
                })
            
            print(f"DEBUG: Création de l'événement avec {len(invited_temp)} invités")
            
            # Créer l'événement avec le formulaire
            ev = form.save(commit=True, creator_personne=personne)

            # S'assurer que l'organisateur est participant et accepté
            try:
                if ev.organiser:
                    Participant.objects.update_or_create(
                        event=ev,
                        person=ev.organiser,
                        defaults={'status': Participant.Status.ACCEPTED}
                    )
            except Exception as e:
                # Ne pas bloquer la création pour une erreur de participant
                print(f"DEBUG: impossible d'ajouter l'organisateur en tant que participant: {e}")
            
            # Ajouter les participants de la session
            invited_people = []
            for invited_data in invited_temp:
                try:
                    p = Personne.objects.get(Id_Matricule=invited_data['id'])
                    Participant.objects.get_or_create(event=ev, person=p)
                    invited_people.append(p)
                except Personne.DoesNotExist:
                    pass
            
            # Créer et envoyer une notification aux participants invités
            if invited_people:
                # Créer la notification
                notification = Notification.objects.create(
                    Titre=f"Invitation à l'événement : {ev.title}",
                    Contenu=f"Vous avez été invité(e) à l'événement '{ev.title}' "
                            f"organisé par {personne.Prenom} {personne.Nom}.\n\n"
                            f"Date de début : {ev.start.strftime('%d/%m/%Y à %H:%M')}\n"
                            f"Date de fin : {ev.end.strftime('%d/%m/%Y à %H:%M')}\n"
                            f"Description : {ev.description or 'Non spécifiée'}\n\n"
                            f"ID de l'événement : {ev.id}",
                    Type="ALERTE"
                )
                
                # Associer la notification à chaque participant invité
                for p in invited_people:
                    PersonneNotification.objects.create(
                        Id_Matricule=p,
                        Id_notif=notification
                    )
            
            # Nettoyer la session
            if 'invited_temp' in request.session:
                del request.session['invited_temp']
            if 'event_data' in request.session:
                del request.session['event_data']
            request.session.modified = True
            
            # Aucun lien vers Reservation/PersonneReservation ou PersonalScheduleEntry
            # : la gestion des réservations/calendriers est volontairement désactivée
            # ici pour éviter la duplication d'événements dans d'autres modules.
            return redirect('events:dashboard')
        else:
            # Afficher les erreurs du formulaire mais garder les invités en session
            invited_temp = request.session.get('invited_temp', [])
            for error in form.non_field_errors():
                messages.error(request, str(error))
            return render(request, 'events/event_form.html', {
                'form': form,
                'invited_temp': invited_temp,
                'personnes_temp': invited_temp,
            })


class EventUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        ev = get_object_or_404(Event, pk=self.kwargs.get('pk'))
        personne = Personne.objects.filter(user=self.request.user).first()
        return ev.organiser == personne

    def get(self, request, pk):
        ev = get_object_or_404(Event, pk=pk)
        form = EventCreateForm(instance=ev)
        return render(request, 'events/event_form.html', {'form': form, 'event': ev})

    def post(self, request, pk):
        ev = get_object_or_404(Event, pk=pk)
        form = EventCreateForm(request.POST, instance=ev)
        if form.is_valid():
            ev = form.save(commit=True, creator_personne=ev.organiser)
            # S'assurer que l'organisateur reste participant accepté après update
            try:
                if ev.organiser:
                    Participant.objects.update_or_create(
                        event=ev,
                        person=ev.organiser,
                        defaults={'status': Participant.Status.ACCEPTED}
                    )
            except Exception as e:
                print(f"DEBUG: impossible d'assurer le participant organisateur après update: {e}")
            # Aucune synchronisation avec Reservation/PersonneReservation ni
            # suppression d'entrées dans PersonalScheduleEntry lors de la mise à
            # jour d'un événement : la logique de réservation/calendrier est
            # volontairement désactivée ici.
            return redirect('events:dashboard')
        return render(request, 'events/event_form.html', {'form': form, 'event': ev})


class EventDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        ev = get_object_or_404(Event, pk=self.kwargs.get('pk'))
        personne = Personne.objects.filter(user=self.request.user).first()
        return ev.organiser == personne

    def post(self, request, pk):
        ev = get_object_or_404(Event, pk=pk)
        ev.delete()
        return redirect('events:dashboard')


class RespondInvitationView(LoginRequiredMixin, View):
    """Handle accept/decline actions for an invitation to an event.

    Expects POST with 'action' in ('accept', 'decline').
    """
    def post(self, request, pk):
        action = request.POST.get('action')
        personne = Personne.objects.filter(user=request.user).first()
        if not personne:
            messages.error(request, "Impossible de trouver votre profil Personne pour répondre à l'invitation.")
            return redirect('events:dashboard')

        event = get_object_or_404(Event, pk=pk)
        participant = Participant.objects.filter(event=event, person=personne).first()
        if not participant:
            messages.error(request, "Vous n'êtes pas invité à cet événement.")
            return redirect('events:dashboard')

        if action == 'accept':
            participant.status = Participant.Status.ACCEPTED
            participant.save()
            messages.success(request, "Invitation acceptée.")
            # Synchronisation avec reservations désactivée :
            # nous n'ajoutons plus d'entrée dans Reservation / PersonneReservation
            # lors de l'acceptation d'une invitation.

        elif action == 'decline':
            participant.status = Participant.Status.DECLINED
            participant.save()
            messages.info(request, "Invitation refusée.")
        else:
            messages.error(request, "Action inconnue.")

        return redirect('events:dashboard')


class RemoveParticipantView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Allow organiser to remove a participant from an event."""
    def test_func(self):
        ev = get_object_or_404(Event, pk=self.kwargs.get('pk'))
        personne = Personne.objects.filter(user=self.request.user).first()
        return ev.organiser == personne

    def post(self, request, pk, participant_pk):
        ev = get_object_or_404(Event, pk=pk)
        participant = get_object_or_404(Participant, pk=participant_pk, event=ev)
        participant.delete()
        messages.success(request, "Invité supprimé.")
        return redirect('events:edit', pk=pk)
