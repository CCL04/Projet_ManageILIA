from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime, timedelta, date
from django.utils.dateparse import parse_datetime
from .models import PersonalSchedule, PersonalScheduleEntry, RecurringTelework
from .forms import PersonalScheduleEntryForm, RecurringTeleworkForm
from django.utils import timezone as dj_tz
import json
from ILIA.models import Personne
from reservations.models import Bureau


@login_required
def personal_schedule(request):
    schedule, created = PersonalSchedule.objects.get_or_create(user=request.user)

    has_shareable_bureau = False
    try:
        # Tenter de récupérer l'objet Personne lié à l'utilisateur
        personne = Personne.objects.get(user=request.user)

        # Vérifier si un bureau est attribué ET si son Type est PARTAGEABLE
        # (en supposant que Bureau.TypeBureau est correctement défini)
        if personne.Id_bureau and personne.Id_bureau.Type == Bureau.TypeBureau.PARTAGEABLE:
            has_shareable_bureau = True

    except Personne.DoesNotExist:
        # L'utilisateur n'a pas de profil Personne, has_shareable_bureau reste False
        pass

    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # Calculer les dates du mois
    start_date = date(year, month, 1)
    last_day = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    end_date = last_day

    fc_start = request.GET.get('start')
    fc_end = request.GET.get('end')

    start_range = None
    end_range = None

    if fc_start and fc_end:
        # 1) Essai avec parse_datetime
        start_range = parse_datetime(fc_start)
        end_range = parse_datetime(fc_end)

        # 2) Si échec, essai avec datetime.fromisoformat
        if start_range is None:
            try:
                start_range = datetime.fromisoformat(fc_start)
            except Exception:
                start_range = None

        if end_range is None:
            try:
                end_range = datetime.fromisoformat(fc_end)
            except Exception:
                end_range = None

    # 3) Si on n'a toujours pas de plage valide, revenir à l’ancienne logique
    if start_range is None or end_range is None:
        extended_start = start_date - timedelta(days=7)
        extended_end = end_date + timedelta(days=7)
        start_range = datetime.combine(extended_start, datetime.min.time())
        end_range = datetime.combine(extended_end, datetime.max.time())

    entries = PersonalScheduleEntry.objects.filter(
        schedule=schedule,
        # start_datetime__gte=start_range,
        # start_datetime__lte=end_range
    ).order_by('start_datetime')

    recurring_teleworks = RecurringTelework.objects.filter(schedule=schedule)

    # Si demande au format JSON (depuis AJAX du calendrier)
    if request.GET.get('format') == 'json':
        entries_data = [
            {
                'id':entry.id,
                'title': entry.title,
                'start_datetime': entry.start_datetime.isoformat(),
                'end_datetime': entry.end_datetime.isoformat(),
                'description': entry.description or ''
            }
            for entry in entries
        ]

        recurring_data = [
            {
                'id':telework.id,
                'day_of_week': telework.day_of_week,
                'start_date': telework.start_date.isoformat(),
                'end_date': telework.end_date.isoformat()
            }
            for telework in recurring_teleworks
            if telework.start_date and telework.end_date and telework.day_of_week is not None
        ]

        print(f"DEBUG: Retour {len(entries_data)} entries et {len(recurring_data)} télétravaux")
        return JsonResponse({
            'entries': entries_data,
            'recurring_teleworks': recurring_data,
            'year': year,
            'month': month
        })

    context = {
        "schedule": schedule,
        "entries": entries,
        "recurring_teleworks": recurring_teleworks,
        "current_date": today,
        "year": year,
        "month": month,
        'has_shareable_bureau': has_shareable_bureau,
    }
    return render(request, "timetable/personal_schedule.html", context)



@login_required
def add_schedule_entry(request):
    schedule = get_object_or_404(PersonalSchedule, user=request.user)

    if request.method == "POST":
        form = PersonalScheduleEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.schedule = schedule
            entry.save()
            messages.success(request, f"✅ Événement ajouté avec succès!")
            return redirect('personal_schedule')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erreur dans {field}: {error}")
    else:
        form = PersonalScheduleEntryForm()

    return render(request, "timetable/add_schedule_entry.html", {"form": form})


@login_required
def add_recurring_telework(request):
    schedule = get_object_or_404(PersonalSchedule, user=request.user)

    if request.method == "POST":
        form = RecurringTeleworkForm(request.POST)
        if form.is_valid():
            telework = form.save(commit=False)
            telework.schedule = schedule
            telework.save()
            days = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}
            messages.success(
                request,
                f"✅ Télétravail le {days[telework.day_of_week]} configuré du {telework.start_date.strftime('%d/%m/%Y')} au {telework.end_date.strftime('%d/%m/%Y')}!"
            )
            return redirect('personal_schedule')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erreur dans {field}: {error}")
    else:
        form = RecurringTeleworkForm()

    return render(request, "timetable/add_recurring_telework.html", {"form": form})

@login_required
def delete_personal_entry(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        entry_id = data.get('id')
        entry = PersonalScheduleEntry.objects.get(id=entry_id, schedule__user=request.user)
        entry.delete()
        return JsonResponse({'status': 'ok'})
    except PersonalScheduleEntry.DoesNotExist:
        return JsonResponse({'status': 'error', 'error': 'Événement introuvable'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@login_required
def delete_recurring_telework(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        telework_id = data.get('id')
        telework = RecurringTelework.objects.get(id=telework_id, schedule__user=request.user)
        telework.delete()
        return JsonResponse({'status': 'ok'})
    except RecurringTelework.DoesNotExist:
        return JsonResponse({'status': 'error', 'error': 'Télétravail introuvable'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@login_required
def delete_recurring_telework_occurrence(request):
    """
    Supprime une seule occurrence d'une règle de télétravail récurrent
    en ajustant / découpant la règle existante (pas de nouveau modèle).
    """
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'error': 'Méthode non autorisée'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        telework_id = data.get('id')
        date_str = data.get('date')

        if not telework_id or not date_str:
            return JsonResponse({'status': 'error', 'error': 'Paramètres manquants'}, status=400)

        telework = RecurringTelework.objects.get(id=telework_id, schedule__user=request.user)

        try:
            target_date = datetime.fromisoformat(date_str).date()
        except Exception:
            return JsonResponse({'status': 'error', 'error': 'Date invalide'}, status=400)

        # Vérifier que la date est dans la plage de la règle
        if target_date < telework.start_date or target_date > telework.end_date:
            return JsonResponse({'status': 'ok'})  # rien à faire

        # Vérifier que c'est bien le bon jour de semaine
        # (0 = lundi dans day_of_week, 0 = lundi dans isoweekday()-1)
        if (target_date.weekday() != telework.day_of_week):
            # Ce n'est pas un jour où cette règle s'applique
            return JsonResponse({'status': 'ok'})

        # Cas 1 : un seul jour dans la règle -> on supprime toute la règle
        if telework.start_date == telework.end_date == target_date:
            telework.delete()
            return JsonResponse({'status': 'ok'})

        # Cas 2 : occurrence au tout début de la plage
        if target_date == telework.start_date:
            telework.start_date = telework.start_date + timedelta(days=7)
            telework.save()
            return JsonResponse({'status': 'ok'})

        # Cas 3 : occurrence à la fin de la plage
        if target_date == telework.end_date:
            telework.end_date = telework.end_date - timedelta(days=7)
            telework.save()
            return JsonResponse({'status': 'ok'})

        # Cas 4 : occurrence au milieu -> découper en deux règles
        old_end = telework.end_date

        # La règle actuelle devient la partie "avant"
        telework.end_date = target_date - timedelta(days=7)
        telework.save()

        # Créer la partie "après"
        RecurringTelework.objects.create(
            schedule=telework.schedule,
            day_of_week=telework.day_of_week,
            start_date=target_date + timedelta(days=7),
            end_date=old_end,
        )

        return JsonResponse({'status': 'ok'})

    except RecurringTelework.DoesNotExist:
        return JsonResponse({'status': 'error', 'error': 'Télétravail introuvable'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@login_required
def sync_accepted_events(request):
    schedule = get_object_or_404(PersonalSchedule, user=request.user)

    try:
        from events.models import Event
        accepted_events = Event.objects.filter(attendees=request.user, status='accepted')

        count = 0
        for event in accepted_events:
            if not PersonalScheduleEntry.objects.filter(
                    schedule=schedule,
                    title=event.title,
                    start_datetime=event.start_datetime
            ).exists():
                PersonalScheduleEntry.objects.create(
                    schedule=schedule,
                    title=event.title,
                    description=event.description if hasattr(event, 'description') else "",
                    start_datetime=event.start_datetime,
                    end_datetime=event.end_datetime,
                )
                count += 1

        return JsonResponse({'status': 'synced', 'count': count})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@login_required
def sync_office_bookings(request):
    schedule = get_object_or_404(PersonalSchedule, user=request.user)

    try:
        return JsonResponse({'status': 'synced', 'count': 0})
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@login_required
def get_events_and_reservations(request):
    """
    API JSON pour récupérer les événements et réservations de l'utilisateur
    pour l'affichage dans le calendrier.
    
    Retourne:
    - events: événements auquel l'utilisateur participe (ACCEPTED)
    - reservations: réservations de l'utilisateur
    """
    try:
        from ILIA.models import Personne
        from events.models import Event, Participant
        from reservations.models import Reservation, PersonneReservation
        
        # Récupérer la personne associée à l'utilisateur
        personne = Personne.objects.filter(user=request.user).first()
        
        fc_start = request.GET.get('start')
        fc_end = request.GET.get('end')
        
        start_range = None
        end_range = None
        
        if fc_start and fc_end:
            try:
                start_range = parse_datetime(fc_start)
            except Exception:
                try:
                    start_range = datetime.fromisoformat(fc_start)
                except Exception:
                    pass
            
            try:
                end_range = parse_datetime(fc_end)
            except Exception:
                try:
                    end_range = datetime.fromisoformat(fc_end)
                except Exception:
                    pass
        
        # Fallback si les dates ne sont pas valides
        if start_range is None or end_range is None:
            today = date.today()
            start_range = dj_tz.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_range = start_range + timedelta(days=30)
        else:
            # Assurer que les dates sont awareness-aware (avec timezone)
            if dj_tz.is_naive(start_range):
                start_range = dj_tz.make_aware(start_range, dj_tz.get_current_timezone())
            if dj_tz.is_naive(end_range):
                end_range = dj_tz.make_aware(end_range, dj_tz.get_current_timezone())
        
        events_data = []
        reservations_data = []
        
        # ===== ÉVÉNEMENTS =====
        if personne:
            # Événements où l'utilisateur est:
            # 1. Participant avec status ACCEPTED
            # 2. OU organisateur (créateur de l'événement)
            accepted_events = Event.objects.filter(
                Q(participants__person=personne, participants__status=Participant.Status.ACCEPTED) |
                Q(organiser=personne)
            ).distinct()
            
            for event in accepted_events:
                # Vérifier si l'événement est dans la plage
                if event.start <= end_range and event.end >= start_range:
                    is_organiser = event.organiser == personne
                    events_data.append({
                        'id': f'event_{event.id}',
                        'title': event.title,
                        'start': event.start.isoformat(),
                        'end': event.end.isoformat(),
                        'description': event.description or '',
                        'type': 'event',
                        'is_organiser': is_organiser,
                        'can_edit': is_organiser,
                        'can_delete': is_organiser,
                        'organiser_name': f"{event.organiser.Prenom} {event.organiser.Nom}" if event.organiser else 'N/A',
                        'event_id': event.id,
                    })
        
        # ===== RÉSERVATIONS =====
        if personne:
            # Réservations validées de l'utilisateur
            # IMPORTANT: Ajouter select_related pour charger Id_bureau et Id_piece
            user_reservations = PersonneReservation.objects.filter(
                Id_Matricule=personne,
                Valide=True,
                Id_reservation__Debut__lte=end_range,
                Id_reservation__Fin__gte=start_range
            ).select_related(
                'Id_reservation',
                'Id_reservation__Id_bureau',
                'Id_reservation__Id_bureau__Id_piece',
                'Id_reservation__Id_piece'
            )

            for pr in user_reservations:
                r = pr.Id_reservation
                start_dt = r.Debut
                end_dt = r.Fin

                if dj_tz.is_naive(start_dt):
                    start_dt = dj_tz.make_aware(start_dt, dj_tz.get_current_timezone())
                if dj_tz.is_naive(end_dt):
                    end_dt = dj_tz.make_aware(end_dt, dj_tz.get_current_timezone())

                is_creator = r.Id_Matricule == personne

                # Construire la description avec les infos du bureau/pièce
                bureau_name = None
                piece_name = None
                description = f"Type: {r.get_Type_display()}"

                if r.Id_bureau:
                    bureau_name = r.Id_bureau.Nom if r.Id_bureau.Nom else f"Bureau {r.Id_bureau.Id_bureau}"
                    piece_name = r.Id_bureau.Id_piece.Nom if r.Id_bureau.Id_piece else None
                    description = f"Bureau: {bureau_name}"
                    if piece_name:
                        description += f" - Pièce: {piece_name}"
                elif r.Id_piece:
                    piece_name = r.Id_piece.Nom
                    description = f"Pièce: {piece_name}"

                reservations_data.append({
                    'id': f'reservation_{r.Id_reservation}',
                    'title': r.Nom,
                    'start': start_dt.isoformat(),
                    'end': end_dt.isoformat(),
                    'description': description,
                    'type': 'reservation',
                    'is_creator': is_creator,
                    'can_edit': is_creator,
                    'can_delete': is_creator,
                    'creator_name': f"{r.Id_Matricule.Prenom} {r.Id_Matricule.Nom}",
                    'reservation_id': r.Id_reservation,
                    'bureau_name': bureau_name,
                    'bureau_id': r.Id_bureau.Id_bureau if r.Id_bureau else None,
                    'piece_name': piece_name,
                })
        
        return JsonResponse({
            'events': events_data,
            'reservations': reservations_data,
        })
    
    except Exception as e:
        print(f"DEBUG get_events_and_reservations: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'events': [],
            'reservations': [],
            'error': str(e)
        }, status=400)


@login_required
def delete_event(request):
    """
    Supprime un événement si l'utilisateur est l'organisateur.
    """
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'error': 'Méthode non autorisée'}, status=405)
    
    try:
        from events.models import Event
        from ILIA.models import Personne
        
        data = json.loads(request.body.decode('utf-8'))
        event_id = data.get('event_id')
        
        personne = Personne.objects.filter(user=request.user).first()
        if not personne:
            return JsonResponse({'status': 'error', 'error': 'Profil utilisateur introuvable'}, status=403)
        
        event = Event.objects.get(id=event_id)
        
        # Vérifier que l'utilisateur est l'organisateur
        if event.organiser != personne:
            return JsonResponse({'status': 'error', 'error': 'Seul l\'organisateur peut supprimer'}, status=403)
        
        event.delete()
        return JsonResponse({'status': 'ok'})
    
    except Event.DoesNotExist:
        return JsonResponse({'status': 'error', 'error': 'Événement introuvable'}, status=404)
    except Exception as e:
        print(f"DEBUG delete_event: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@login_required
def delete_reservation(request):
    """
    Supprime une réservation si l'utilisateur en est le créateur.
    """
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'error': 'Méthode non autorisée'}, status=405)
    
    try:
        from reservations.models import Reservation
        from ILIA.models import Personne
        
        data = json.loads(request.body.decode('utf-8'))
        reservation_id = data.get('reservation_id')
        
        personne = Personne.objects.filter(user=request.user).first()
        if not personne:
            return JsonResponse({'status': 'error', 'error': 'Profil utilisateur introuvable'}, status=403)
        
        reservation = Reservation.objects.get(Id_reservation=reservation_id)
        
        # Vérifier que l'utilisateur est le créateur
        if reservation.Id_Matricule != personne:
            return JsonResponse({'status': 'error', 'error': 'Seul le créateur peut supprimer'}, status=403)
        
        reservation.delete()
        return JsonResponse({'status': 'ok'})
    
    except Reservation.DoesNotExist:
        return JsonResponse({'status': 'error', 'error': 'Réservation introuvable'}, status=404)
    except Exception as e:
        print(f"DEBUG delete_reservation: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)
