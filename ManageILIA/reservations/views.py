from calendar import weekday
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Piece, Bureau, Reservation, PersonneReservation, LiberationBureau
import datetime
from ILIA.models import Personne
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from timetable.models import PersonalSchedule, RecurringTelework
from .forms import ReservationBureauRapideForm


BUREAU_COLORS = [
    "#0D47A1", "#2962FF", "#00838F", "#00ACC1",
    "#1B5E20", "#43A047", "#7CB342",
    "#EF6C00", "#F4511E", "#FF7043",
    "#B71C1C", "#E53935", "#FF5252",
    "#4A148C", "#8E24AA", "#BA68C8",
    "#004D40", "#00796B", "#26A69A",
    "#9E9D24", "#FDD835", "#FBC02D",
]

PIECE_COLORS = [
    "#0D47A1", "#1976D2", "#42A5F5", "#90CAF9",
    "#01579B", "#0288D1", "#4FC3F7", "#81D4FA",
    "#283593", "#3F51B5", "#5C6BC0", "#9FA8DA",
    "#6A1B9A", "#8E24AA", "#AB47BC", "#CE93D8",
]


def get_bureau_color(bureau_id):
    """Retourne une couleur unique pour chaque bureau basée sur son ID"""
    return BUREAU_COLORS[bureau_id % len(BUREAU_COLORS)]


def get_piece_color(piece_id):
    """Retourne une couleur unique pour chaque pièce/salle basée sur son ID"""
    return PIECE_COLORS[piece_id % len(PIECE_COLORS)]


def _parse_iso(dt_str):
    """Parse ISO datetime string and make it timezone-aware if needed"""
    if not dt_str:
        return None

    try:

        if ' ' in dt_str and '+' not in dt_str:
            dt_str = dt_str.replace(' ', '+')

        # Essayer d'abord le parser Django
        dt = parse_datetime(dt_str)
        if dt:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
            return dt

        dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        return dt
    except Exception as e:
        print(f"Error parsing datetime {dt_str}: {e}")
        return None


def est_en_presentiel(personne, date_verif):
    """
    Retourne True si personne est au bureau.
    Retourne False si en télétravail.
    """
    if not personne or not hasattr(personne, 'user'):
        return True
    try:
        schedule = PersonalSchedule.objects.get(user=personne.user)
        jour_semaine = date_verif.weekday()

        teletravail = RecurringTelework.objects.filter(
            schedule=schedule,
            day_of_week=jour_semaine,
            start_date__lte=date_verif,
            end_date__gte=date_verif,
        ).exists()

        if teletravail:
            return False
    except PersonalSchedule.DoesNotExist:
        return True

    return True


@login_required
def events_json(request):
    """Retourne les réservations sous forme d'événements JSON pour FullCalendar."""
    start = request.GET.get('start')
    end = request.GET.get('end')

    start_dt = _parse_iso(start) if start else None
    end_dt = _parse_iso(end) if end else None

    qs = Reservation.objects.select_related('Id_bureau', 'Id_piece', 'Id_Matricule')
    if start_dt and end_dt:
        qs = qs.filter(Debut__lt=end_dt, Fin__gt=start_dt)

    events = []
    for r in qs:
        title_loc = ''
        color = None
        if r.Id_bureau:
            title_loc = r.Id_bureau.Nom if r.Id_bureau.Nom else f"Bureau {r.Id_bureau.Id_bureau}"
            color = get_bureau_color(r.Id_bureau.Id_bureau)
        elif r.Id_piece:
            title_loc = r.Id_piece.Nom
            color = '#6366f1'  # Couleur indigo pour les salles

        reservant = str(r.Id_Matricule) if r.Id_Matricule else "Inconnu"
        if r.Id_bureau:
            bureau_display = r.Id_bureau.Nom if r.Id_bureau.Nom else f"B{r.Id_bureau.Id_bureau}"
            title = f"{bureau_display}\n{reservant}"
        elif r.Id_piece:
            title = f"{r.Id_piece.Nom}\n{reservant}"
        else:
            title = reservant

        debut_local = r.Debut
        fin_local = r.Fin
        if timezone.is_aware(debut_local):
            debut_local = timezone.localtime(debut_local)
        if timezone.is_aware(fin_local):
            fin_local = timezone.localtime(fin_local)

        event_data = {
            'id': r.Id_reservation,
            'title': title,
            'start': debut_local.isoformat(),
            'end': fin_local.isoformat(),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'type': r.get_Type_display(),
                'organisateur': str(r.Id_Matricule),
                'email': r.Id_Matricule.Email if r.Id_Matricule else '',
                'bureau_id': r.Id_bureau.Id_bureau if r.Id_bureau else None,
                'piece_id': r.Id_piece.Id_piece if r.Id_piece else None,
                'nom_reservation': r.Nom,
                'location': title_loc,
            }
        }
        events.append(event_data)

    return JsonResponse(events, safe=False)


@login_required
def locations_json(request):
    """Retourne les locations disponibles (bureaux et salles)."""
    bureaux = Bureau.objects.filter(Type__in=[Bureau.TypeBureau.LIBRE, Bureau.TypeBureau.PARTAGEABLE]).select_related(
        'Id_piece')
    pieces = Piece.objects.filter(Type=Piece.TypePiece.SALLE_REUNION)

    data = {
        'pieces': [
            {
                'id': p.Id_piece,
                'label': f"{p.Nom} — Étage {p.Etage} (cap: {p.Capacite if p.Capacite else 'N/A'})",
            }
            for p in pieces
        ],
        'bureaux': [
            {
                'id': b.Id_bureau,
                'label': f"{b.Nom if b.Nom else f'Bureau {b.Id_bureau}'} — {b.Id_piece.Nom if b.Id_piece else ''}",
                'type': b.get_Type_display(),
            }
            for b in bureaux
        ]
    }
    return JsonResponse(data)


@login_required
@require_http_methods(['POST'])
def create_reservation_api(request):
    """Créer une réservation via POST."""
    user = request.user
    try:
        personne = user.personne
    except Exception:
        return JsonResponse({'error': 'Compte Personne introuvable pour cet utilisateur.'}, status=400)

    # Lire les données
    if request.content_type == 'application/json':
        import json
        data = json.loads(request.body)
        typ = data.get('type')
        nom = data.get('nom') or data.get('title')
        debut = data.get('debut')
        fin = data.get('fin')
        bureau_id = data.get('bureau_id') or data.get('bureau')
        piece_id = data.get('piece_id') or data.get('piece')
        recurrence = data.get('recurrence')
        frequence = data.get('frequence')
        repetitions = data.get('repetitions')
    else:
        typ = request.POST.get('type')
        nom = request.POST.get('nom') or request.POST.get('title')
        debut = request.POST.get('debut')
        fin = request.POST.get('fin')
        bureau_id = request.POST.get('bureau')
        piece_id = request.POST.get('piece')
        recurrence = request.POST.get('recurrence')
        frequence = request.POST.get('frequence')
        repetitions = request.POST.get('repetitions')

    print(f"DEBUG create_reservation: typ={typ}, nom={nom}, debut={debut}, fin={fin}, bureau_id={bureau_id}")

    if not (nom and debut and fin and typ is not None):
        return JsonResponse({'error': f'Champs manquants: nom={nom}, debut={debut}, fin={fin}, type={typ}'}, status=400)

    debut_dt = _parse_iso(debut)
    fin_dt = _parse_iso(fin)
    if not debut_dt or not fin_dt or debut_dt >= fin_dt:
        return JsonResponse({'error': 'Dates invalides'}, status=400)

    duree = fin_dt - debut_dt

    # Vérifier conflit
    loc_bureau = None
    loc_piece = None

    if str(typ) == '1':
        if not bureau_id:
            return JsonResponse({'error': 'Bureau requis pour ce type'}, status=400)
        try:
            loc_bureau = Bureau.objects.prefetch_related('personne_set').get(pk=int(bureau_id))
            print(f"DEBUG: Bureau trouvé: {loc_bureau.Id_bureau}")
        except Bureau.DoesNotExist:
            return JsonResponse({'error': 'Bureau introuvable'}, status=400)

        proprietaires = loc_bureau.personne_set.all()

        for proprietaire in proprietaires:
            if proprietaire.Id_Matricule == personne.Id_Matricule:
                continue

            current_check = debut_dt.date()
            end_check = fin_dt.date()

            while current_check <= end_check:
                if is_presentiel:
                    has_liberation = LiberationBureau.objects.filter(
                        Id_Matricule=proprietaire,
                        Id_bureau=loc_bureau,
                        Date=current_check
                    ).exists()

                    # Si le propriétaire est présent ET n'a PAS libéré le bureau
                    if not has_liberation:
                        return JsonResponse({
                            'error': f"Ce bureau est assigné à {proprietaire} qui est présent(e) le {current_check.strftime('%d/%m')} et n'a pas libéré son bureau."
                        }, status=400)
                current_check += datetime.timedelta(days=1)

        if loc_bureau.Type == Bureau.TypeBureau.OCCUPE:
            return JsonResponse({'error': 'Ce bureau est marqué comme occupé et ne peut pas être réservé.'}, status=400)
    else:
        if not piece_id:
            return JsonResponse({'error': 'Salle requise pour ce type'}, status=400)
        try:
            loc_piece = Piece.objects.get(pk=int(piece_id))
        except Piece.DoesNotExist:
            return JsonResponse({'error': 'Salle introuvable'}, status=400)

    # Gérer la récurrence
    if recurrence and recurrence in ['true', 'True', True]:
        from datetime import timedelta
        frequence_map = {
            'daily': timedelta(days=1),
            'weekly': timedelta(weeks=1),
            'biweekly': timedelta(weeks=2),
            'monthly': timedelta(days=30),
        }
        increment = frequence_map.get(frequence, timedelta(weeks=1))
        try:
            nb_repetitions = int(repetitions) if repetitions else 1
            nb_repetitions = min(nb_repetitions, 52)
        except:
            nb_repetitions = 1

        created_count = 0
        conflict_dates = []

        for i in range(nb_repetitions):
            current_debut = debut_dt + (increment * i)
            current_fin = current_debut + duree

            if str(typ) == '1':
                conflicts = Reservation.objects.filter(Id_bureau=loc_bureau, Debut__lt=current_fin,
                                                       Fin__gt=current_debut)
            else:
                conflicts = Reservation.objects.filter(Id_piece=loc_piece, Debut__lt=current_fin, Fin__gt=current_debut)

            if not conflicts.exists():
                r = Reservation(
                    Nom=nom,
                    Type=int(typ),
                    Debut=current_debut,
                    Fin=current_fin,
                    Id_Matricule=personne,
                    Id_bureau=loc_bureau if str(typ) == '1' else None,
                    Id_piece=loc_bureau.Id_piece if (str(typ) == '1' and loc_bureau) else (
                        loc_piece if str(typ) != '1' else None),
                )
                r.save()
                PersonneReservation.objects.get_or_create(
                    Id_Matricule=personne,
                    Id_reservation=r,
                    defaults={'Valide': True}
                )
                created_count += 1
            else:
                conflict_dates.append(current_debut.strftime('%Y-%m-%d %H:%M'))

        message = f'{created_count} réservation(s) créée(s)'
        if conflict_dates:
            message += f'. {len(conflict_dates)} créneau(x) ignoré(s) en raison de conflits.'

        return JsonResponse({'message': message, 'created': created_count, 'conflicts': len(conflict_dates)})

    else:
        # Réservation simple
        if str(typ) == '1':
            conflicts = Reservation.objects.filter(Id_bureau=loc_bureau, Debut__lt=fin_dt, Fin__gt=debut_dt)
            if conflicts.exists():
                return JsonResponse({'error': 'Plage horaire occupée pour ce bureau.'}, status=400)
        else:
            conflicts = Reservation.objects.filter(Id_piece=loc_piece, Debut__lt=fin_dt, Fin__gt=debut_dt)
            if conflicts.exists():
                return JsonResponse({'error': 'Plage horaire occupée pour cette salle.'}, status=400)

        r = Reservation(
            Nom=nom,
            Type=int(typ),
            Debut=debut_dt,
            Fin=fin_dt,
            Id_Matricule=personne,
            Id_bureau=loc_bureau if str(typ) == '1' else None,
            Id_piece=loc_bureau.Id_piece if (str(typ) == '1' and loc_bureau) else (
                loc_piece if str(typ) != '1' else None),
        )
        r.save()
        PersonneReservation.objects.get_or_create(
            Id_Matricule=personne,
            Id_reservation=r,
            defaults={'Valide': True}
        )
        return JsonResponse({'id': r.Id_reservation, 'message': 'Réservation créée'})


@login_required
@require_http_methods(['GET', 'POST', 'PUT', 'DELETE'])
def reservation_detail_api(request, pk):
    r = get_object_or_404(Reservation.objects.select_related('Id_Matricule', 'Id_bureau', 'Id_piece'), pk=pk)

    if request.method == 'GET':
        debut_local = r.Debut
        fin_local = r.Fin
        if timezone.is_aware(debut_local):
            debut_local = timezone.localtime(debut_local)
        if timezone.is_aware(fin_local):
            fin_local = timezone.localtime(fin_local)

        data = {
            'id': r.Id_reservation,
            'nom': r.Nom,
            'type': r.Type,
            'debut': debut_local.isoformat(),
            'fin': fin_local.isoformat(),
            'organisateur': str(r.Id_Matricule),
            'email': r.Id_Matricule.Email if r.Id_Matricule else '',
            'bureau_id': r.Id_bureau.Id_bureau if r.Id_bureau else None,
            'piece_id': r.Id_piece.Id_piece if r.Id_piece else None,
            'bureau_nom': (r.Id_bureau.Nom if r.Id_bureau.Nom else f"Bureau {r.Id_bureau.Id_bureau}") if r.Id_bureau else None,
            'piece_nom': r.Id_piece.Nom if r.Id_piece else None,
            'can_edit': hasattr(request.user, 'personne') and getattr(request.user.personne, 'Id_Matricule',
                                                                      None) == getattr(r.Id_Matricule, 'Id_Matricule',
                                                                                       None)
        }
        return JsonResponse(data)

    if request.method == 'DELETE':
        if not (hasattr(request.user,
                        'personne') and request.user.personne.Id_Matricule == r.Id_Matricule.Id_Matricule):
            return JsonResponse({'error': 'Vous ne pouvez pas supprimer une réservation d\'un autre utilisateur'},
                                status=403)
        r.delete()
        return JsonResponse({'message': 'Réservation supprimée'})

    # POST or PUT
    if request.content_type == 'application/json':
        import json
        data = json.loads(request.body)
        action = data.get('action')
        nom = data.get('nom')
        typ = data.get('type')
        debut = data.get('debut')
        fin = data.get('fin')
        bureau_id = data.get('bureau_id') or data.get('bureau')
        piece_id = data.get('piece_id') or data.get('piece')
    else:
        action = request.POST.get('action')
        nom = request.POST.get('nom')
        typ = request.POST.get('type')
        debut = request.POST.get('debut')
        fin = request.POST.get('fin')
        bureau_id = request.POST.get('bureau')
        piece_id = request.POST.get('piece')

    if action == 'delete':
        if not (hasattr(request.user,
                        'personne') and request.user.personne.Id_Matricule == r.Id_Matricule.Id_Matricule):
            return JsonResponse({'error': 'Pas autorisé'}, status=403)
        r.delete()
        return JsonResponse({'message': 'Supprimée'})

    if not (hasattr(request.user, 'personne') and request.user.personne.Id_Matricule == r.Id_Matricule.Id_Matricule):
        return JsonResponse({'error': 'Vous ne pouvez pas modifier une réservation d\'un autre utilisateur'},
                            status=403)

    if nom:
        r.Nom = nom
    if typ is not None:
        try:
            r.Type = int(typ)
        except Exception:
            pass

    new_debut = r.Debut
    new_fin = r.Fin
    if debut:
        debut_dt = _parse_iso(debut)
        if debut_dt:
            new_debut = debut_dt
            r.Debut = debut_dt
    if fin:
        fin_dt = _parse_iso(fin)
        if fin_dt:
            new_fin = fin_dt
            r.Fin = fin_dt

    if bureau_id or piece_id:
        if bureau_id:
            try:
                b = Bureau.objects.get(pk=int(bureau_id))
            except Bureau.DoesNotExist:
                return JsonResponse({'error': 'Bureau introuvable'}, status=400)
            if b.Type == Bureau.TypeBureau.OCCUPE:
                return JsonResponse({'error': 'Ce bureau est marqué comme occupé.'}, status=400)

            conflicts = Reservation.objects.filter(Id_bureau=b, Debut__lt=new_fin, Fin__gt=new_debut).exclude(pk=r.pk)
            if conflicts.exists():
                return JsonResponse({'error': 'Plage horaire occupée pour ce bureau.'}, status=400)
            r.Id_bureau = b
            r.Id_piece = None
        elif piece_id:
            try:
                p = Piece.objects.get(pk=int(piece_id))
            except Piece.DoesNotExist:
                return JsonResponse({'error': 'Salle introuvable'}, status=400)

            conflicts = Reservation.objects.filter(Id_piece=p, Debut__lt=new_fin, Fin__gt=new_debut).exclude(pk=r.pk)
            if conflicts.exists():
                return JsonResponse({'error': 'Plage horaire occupée pour cette salle.'}, status=400)
            r.Id_piece = p
            r.Id_bureau = None
    else:
        if r.Id_bureau:
            conflicts = Reservation.objects.filter(Id_bureau=r.Id_bureau, Debut__lt=new_fin, Fin__gt=new_debut).exclude(
                pk=r.pk)
            if conflicts.exists():
                return JsonResponse({'error': 'Plage horaire occupée.'}, status=400)
        elif r.Id_piece:
            conflicts = Reservation.objects.filter(Id_piece=r.Id_piece, Debut__lt=new_fin, Fin__gt=new_debut).exclude(
                pk=r.pk)
            if conflicts.exists():
                return JsonResponse({'error': 'Plage horaire occupée.'}, status=400)
        else:
            return JsonResponse({'error': 'Aucun local sélectionné'}, status=400)

    if r.Debut >= r.Fin:
        return JsonResponse({'error': 'Dates invalides'}, status=400)

    r.save()
    return JsonResponse({'message': 'Réservation mise à jour', 'id': r.Id_reservation})


@login_required
def occupation_locaux(request):
    """Vue d'occupation des locaux avec tri unifié (Salles + Bureaux mélangés)"""

    # 1. Gestion Date
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()

    # 2. Paramètres
    search_query = request.GET.get('q', '')
    sort_option = request.GET.get('tri', 'type')  # 'type' par défaut

    start_of_day = datetime.datetime.combine(selected_date, datetime.time(7, 0))
    end_of_day = datetime.datetime.combine(selected_date, datetime.time(18, 0))

    bureaux = Bureau.objects.select_related('Id_piece')
    pieces = Piece.objects.filter(Type=1)

    if search_query:
        bureaux = bureaux.filter(
            Q(Id_bureau__icontains=search_query) |
            Q(Nom__icontains=search_query) |
            Q(Id_piece__Nom__icontains=search_query) |
            Q(personne__Nom__icontains=search_query) |
            Q(personne__Prenom__icontains=search_query)
        ).distinct()

        pieces = pieces.filter(Nom__icontains=search_query)

    liste_bureaux = []
    liste_salles = []

    for bureau in bureaux:
        creneaux = []
        est_bloque = False
        texte_blocage = ""

        if bureau.Type == Bureau.TypeBureau.OCCUPE:
            est_bloque = True
            texte_blocage = "Bureau Occupé"
        else:
            proprietaires = bureau.personne_set.all()
            for prop in proprietaires:
                if est_en_presentiel(prop, selected_date):
                    has_liberation = LiberationBureau.objects.filter(
                        Id_Matricule=prop,
                        Id_bureau=bureau,
                        Date=selected_date
                    ).exists()

                    if not has_liberation:
                        est_bloque = True
                        texte_blocage = f"{prop.Prenom} {prop.Nom}"
                        break

        if est_bloque:
            creneaux.append({
                'is_blocked': True,
                'owner_name': texte_blocage,
                'left': 0, 'width': 100, 'debut_str': '07:00', 'fin_str': '18:00',
                'color': '#95a5a6',
            })
        else:
            reservations = Reservation.objects.filter(
                Id_bureau=bureau, Debut__lt=end_of_day, Fin__gt=start_of_day
            ).select_related('Id_Matricule').order_by('Debut')

            for res in reservations:
                res_debut_local = timezone.localtime(res.Debut) if timezone.is_aware(res.Debut) else res.Debut
                res_fin_local = timezone.localtime(res.Fin) if timezone.is_aware(res.Fin) else res.Fin
                if timezone.is_aware(res_debut_local): res_debut_local = res_debut_local.replace(tzinfo=None)
                if timezone.is_aware(res_fin_local): res_fin_local = res_fin_local.replace(tzinfo=None)

                debut_hour = max(res_debut_local, start_of_day)
                fin_hour = min(res_fin_local, end_of_day)
                start_minutes = (debut_hour.hour - 7) * 60 + debut_hour.minute
                end_minutes = (fin_hour.hour - 7) * 60 + fin_hour.minute

                left_percent = (start_minutes / 660) * 100
                width_percent = ((end_minutes - start_minutes) / 660) * 100

                creneaux.append({
                    'reservation': res, 'is_blocked': False,
                    'left': left_percent, 'width': width_percent,
                    'debut_str': debut_hour.strftime('%H:%M'), 'fin_str': fin_hour.strftime('%H:%M'),
                    'color': get_bureau_color(bureau.Id_bureau),
                })

        liste_bureaux.append({
            'type': 'bureau',
            'sort_type_val': bureau.Type,  # 0, 1, 2
            'local': bureau,
            'nom': bureau.Nom if bureau.Nom else f'Bureau {bureau.Id_bureau}',
            'id': bureau.Id_bureau,
            'piece': bureau.Id_piece,
            'creneaux': creneaux,
        })

    # --- 2. TRAITEMENT DES SALLES ---
    for piece in pieces:
        reservations = Reservation.objects.filter(
            Id_piece=piece, Debut__lt=end_of_day, Fin__gt=start_of_day
        ).select_related('Id_Matricule').order_by('Debut')

        creneaux = []
        for res in reservations:
            res_debut_local = timezone.localtime(res.Debut) if timezone.is_aware(res.Debut) else res.Debut
            res_fin_local = timezone.localtime(res.Fin) if timezone.is_aware(res.Fin) else res.Fin
            if timezone.is_aware(res_debut_local): res_debut_local = res_debut_local.replace(tzinfo=None)
            if timezone.is_aware(res_fin_local): res_fin_local = res_fin_local.replace(tzinfo=None)

            debut_hour = max(res_debut_local, start_of_day)
            fin_hour = min(res_fin_local, end_of_day)
            start_minutes = (debut_hour.hour - 7) * 60 + debut_hour.minute
            end_minutes = (fin_hour.hour - 7) * 60 + fin_hour.minute

            left_percent = (start_minutes / 660) * 100
            width_percent = ((end_minutes - start_minutes) / 660) * 100

            creneaux.append({
                'reservation': res, 'is_blocked': False,
                'left': left_percent, 'width': width_percent,
                'debut_str': debut_hour.strftime('%H:%M'), 'fin_str': fin_hour.strftime('%H:%M'),
                'color': '#6366f1',
            })

        liste_salles.append({
            'type': 'salle',
            'sort_type_val': -1,
            'local': piece,
            'nom': piece.Nom,
            'id': piece.Id_piece,
            'piece': piece,
            'creneaux': creneaux,
        })

    # --- 3. FUSION ET TRI FINAL ---
    locaux_data = liste_bureaux + liste_salles

    if sort_option == 'type':
        locaux_data.sort(key=lambda x: (x['sort_type_val'], x['piece'].Etage, x['nom']))

    elif sort_option == 'etage':
        # Tri par Étage (mélange salles et bureaux) puis par Nom
        locaux_data.sort(key=lambda x: (x['piece'].Etage, x['nom']))

    elif sort_option == 'nom':
        # Tri alphabétique pur sur le nom affiché
        locaux_data.sort(key=lambda x: x['nom'])

    context = {
        'locaux_data': locaux_data,
        'selected_date': selected_date,
        'title': 'Occupation des locaux',
        'search_query': search_query,
        'sort_option': sort_option,
    }
    return render(request, 'reservations/occupation_locaux.html', context)


@login_required
def bureau_occupation(request, bureau_id):
    """Planning détaillé d'un bureau spécifique"""
    bureau = get_object_or_404(Bureau.objects.select_related('Id_piece'), pk=bureau_id)

    bureau_display = bureau.Nom if bureau.Nom else f'Bureau {bureau.Id_bureau}'
    context = {
        'bureau': bureau,
        'title': f'Planning {bureau_display}'
    }
    return render(request, 'reservations/bureau_occupation.html', context)


@login_required
def bureau_events_json(request, bureau_id):
    """API pour récupérer les événements d'un bureau spécifique avec Debug"""
    # 1. On charge le bureau
    bureau = get_object_or_404(Bureau, pk=bureau_id)

    start = request.GET.get('start')
    end = request.GET.get('end')

    # 2. Parsing sécurisé des dates (avec valeurs par défaut en cas d'échec)
    parsed_start = _parse_iso(start) if start else None
    start_dt = parsed_start if parsed_start else timezone.now()

    parsed_end = _parse_iso(end) if end else None
    end_dt = parsed_end if parsed_end else timezone.now() + datetime.timedelta(days=7)

    events = []

    print(f"--- DEBUG CALENDRIER BUREAU {bureau_id} ---")
    print(f"Période: {start_dt} à {end_dt}")

    # 3. Récupérer les réservations (classiques)
    qs = Reservation.objects.filter(Id_bureau=bureau).select_related('Id_Matricule')
    if start_dt and end_dt:
        qs = qs.filter(Debut__lt=end_dt, Fin__gt=start_dt)

    color = get_bureau_color(bureau_id)
    for r in qs:
        title = f"{r.Nom}\n{r.Id_Matricule}"
        debut_local = r.Debut
        fin_local = r.Fin
        if timezone.is_aware(debut_local): debut_local = timezone.localtime(debut_local)
        if timezone.is_aware(fin_local): fin_local = timezone.localtime(fin_local)

        events.append({
            'id': r.Id_reservation,
            'title': title,
            'start': debut_local.isoformat(),
            'end': fin_local.isoformat(),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'organisateur': str(r.Id_Matricule),
                'email': r.Id_Matricule.Email if r.Id_Matricule else '',
                'type': 'reservation'
            }
        })

    # 4. Générer les blocages (Grisé)
    current_date = start_dt.date()
    end_date = end_dt.date()

    proprietaires = []
    try:
        if hasattr(bureau, 'personne_set'):
            proprietaires = list(bureau.personne_set.all())
        elif hasattr(bureau, 'personnes'):
            proprietaires = list(bureau.personnes.all())
        else:
            # Fallback: requête manuelle si on ne trouve pas l'attribut
            from ILIA.models import Personne  # Import local pour éviter boucle
            proprietaires = list(Personne.objects.filter(Id_bureau=bureau))

        print(f"Propriétaires trouvés : {len(proprietaires)}")
    except Exception as e:
        print(f"Erreur récupération propriétaires: {e}")

    is_admin_occupied = (bureau.Type == Bureau.TypeBureau.OCCUPE)

    while current_date <= end_date:
        is_blocked = False
        block_title = ""

        # A. Bureau marqué OCCUPÉ (Type 2)
        if is_admin_occupied:
            is_blocked = True
            block_title = "Bureau Occupé"

        # B. Propriétaire présent
        elif proprietaires:
            for prop in proprietaires:
                if est_en_presentiel(prop, current_date):
                    has_liberation = LiberationBureau.objects.filter(
                        Id_Matricule=prop,
                        Id_bureau=bureau,
                        Date=current_date
                    ).exists()

                    if not has_liberation:
                        is_blocked = True
                        block_title = f"Assigné: {prop}"
                        break

        if is_blocked:
            start_block = datetime.datetime.combine(current_date, datetime.time(7, 0))
            end_block = datetime.datetime.combine(current_date, datetime.time(19, 0))

            events.append({
                'id': f'blocked_{current_date}_{bureau_id}',
                'title': block_title,
                'start': start_block.isoformat(),
                'end': end_block.isoformat(),
                'display': 'background',
                'backgroundColor': '#95a5a6',
                'extendedProps': {
                    'type': 'blocage',
                    'motif': block_title
                }
            })

        current_date += datetime.timedelta(days=1)

    return JsonResponse(events, safe=False)


@login_required
def piece_occupation(request, piece_id):
    """Planning détaillé d'une salle de réunion spécifique"""
    piece = get_object_or_404(Piece, pk=piece_id)

    context = {
        'piece': piece,
        'title': f'Planning {piece.Nom}'
    }
    return render(request, 'reservations/piece_occupation.html', context)


@login_required
def piece_events_json(request, piece_id):
    """API pour récupérer les événements d'une salle de réunion spécifique"""
    piece = get_object_or_404(Piece, pk=piece_id)
    start = request.GET.get('start')
    end = request.GET.get('end')

    start_dt = _parse_iso(start) if start else None
    end_dt = _parse_iso(end) if end else None

    qs = Reservation.objects.filter(Id_piece=piece).select_related('Id_Matricule')
    if start_dt and end_dt:
        qs = qs.filter(Debut__lt=end_dt, Fin__gt=start_dt)

    events = []
    color = get_piece_color(piece_id)
    for r in qs:
        title = f"{r.Nom}\n{r.Id_Matricule}"

        debut_local = r.Debut
        fin_local = r.Fin
        if timezone.is_aware(debut_local):
            debut_local = timezone.localtime(debut_local)
        if timezone.is_aware(fin_local):
            fin_local = timezone.localtime(fin_local)

        events.append({
            'id': r.Id_reservation,
            'title': title,
            'start': debut_local.isoformat(),
            'end': fin_local.isoformat(),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'organisateur': str(r.Id_Matricule),
                'email': r.Id_Matricule.Email if r.Id_Matricule else '',
            }
        })

    return JsonResponse(events, safe=False)


@login_required
def horaire_reservation(request):
    return render(request, 'reservations/horaire_reservation.html')


@login_required
@require_POST
def liberer_bureau(request):
    """Vue pour libérer un bureau pour certaines dates (sans créer de réservation)"""
    try:
        personne = Personne.objects.get(user=request.user)
    except Personne.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Personne non trouvée'}, status=400)

    # Vérifier que la personne a un bureau attribué
    if not personne.Id_bureau:
        return JsonResponse({'success': False, 'message': 'Aucun bureau attribué'}, status=400)

    # Vérifier que le bureau est de type PARTAGEABLE
    if personne.Id_bureau.Type != Bureau.TypeBureau.PARTAGEABLE:
        return JsonResponse({'success': False, 'message': 'Le bureau doit être de type partageable'}, status=400)

    form = ReservationBureauRapideForm(request.POST)
    if form.is_valid():
        date_debut = form.cleaned_data['Date_debut']
        date_fin = form.cleaned_data['Date_fin']

        # Créer une ligne LiberationBureau pour chaque jour
        liberations_creees = 0
        date_courante = date_debut

        while date_courante <= date_fin:
            # Créer ou mettre à jour la libération pour ce jour
            liberation, created = LiberationBureau.objects.get_or_create(
                Id_Matricule=personne,
                Id_bureau=personne.Id_bureau,
                Date=date_courante
            )
            if created:
                liberations_creees += 1

            date_courante += datetime.timedelta(days=1)

        if liberations_creees > 0:
            return JsonResponse({
                'success': True,
                'message': f'Bureau libéré pour {liberations_creees} jour(s)'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Ce bureau est déjà libéré pour cette période'
            }, status=400)
    else:
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
