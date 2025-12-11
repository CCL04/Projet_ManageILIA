from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from ILIA.models import Personne, Notification, PersonneNotification
from projects.models import Projet, PersonneProjet, Fichier
from .forms import ProjetForm, AjouterPersonneForm, UploadFichierForm
from PIL import Image
import os, io
import base64

@login_required
def mes_projets(request):
    """Vue pour afficher tous les projets de l'utilisateur connecté"""
    
    try:
        utilisateur = request.user.personne
        projets = PersonneProjet.objects.filter(Id_Matricule=utilisateur).select_related('Id_projet')
        projets_list = [pp.Id_projet for pp in projets]
    except Personne.DoesNotExist:
        projets_list = []
    
    return render(request, 'projects/mes_projets.html', {'projets': projets_list})

@login_required
def creer_projet(request):
    """Vue pour créer un nouveau projet"""
    image_cache = request.POST.get('image_cache', '')
    if request.method == 'POST':
        form = ProjetForm(request.POST)
        personne_form = AjouterPersonneForm()

        if 'image_file' in request.FILES:
            image_file = request.FILES['image_file']
            # On lit le fichier et on le convertit en texte base64 pour le stocker dans le HTML
            image_data = image_file.read()
            image_cache = base64.b64encode(image_data).decode('utf-8')
            # Important : on "rembobine" le fichier pour qu'il puisse être relu plus tard si besoin
            image_file.seek(0)

        # Gérer la suppression d'une personne temporaire
        if 'remove_personne' in request.POST:
            personne_id = request.POST.get('remove_personne')
            if 'personnes_temp' in request.session:
                request.session['personnes_temp'] = [
                    p for p in request.session['personnes_temp'] 
                    if str(p['id']) != str(personne_id)
                ]
                request.session.modified = True
            personne_form = AjouterPersonneForm()
        
        # Ajouter une personne
        elif 'ajouter_personne' in request.POST:
            personne_form = AjouterPersonneForm(request.POST)
            if personne_form.is_valid():
                # Ajouter une personne temporairement en session
                if 'personnes_temp' not in request.session:
                    request.session['personnes_temp'] = []
                
                # Vérifier si c'est l'ajout par rôle ou par personne individuelle
                personnes = personne_form.cleaned_data.get('personnes')
                personne = personne_form.cleaned_data.get('personne')
                
                if personnes:
                    # Ajouter toutes les personnes du rôle sélectionné
                    for p in personnes:
                        personne_data = {
                            'id': p.Id_Matricule,
                            'nom': p.Nom,
                            'prenom': p.Prenom
                        }
                        # Éviter les doublons
                        if personne_data not in request.session['personnes_temp']:
                            request.session['personnes_temp'].append(personne_data)
                elif personne:
                    # Ajouter une seule personne
                    personne_data = {
                        'id': personne.Id_Matricule,
                        'nom': personne.Nom,
                        'prenom': personne.Prenom
                    }
                    # Éviter les doublons
                    if personne_data not in request.session['personnes_temp']:
                        request.session['personnes_temp'].append(personne_data)
                
                request.session.modified = True
                personne_form = AjouterPersonneForm()
            else:
                # Afficher les erreurs du formulaire en messages
                for error in personne_form.non_field_errors():
                    messages.error(request, str(error))
                for field, errors in personne_form.errors.items():
                    for error in errors:
                        messages.warning(request, f"Erreur {field}: {error}")
        
        # Créer le projet
        elif 'creer_projet' in request.POST:
            form = ProjetForm(request.POST, request.FILES)
            if form.is_valid():
                # Créer le projet
                projet = form.save(commit=False)

                if 'image_file' in request.FILES:
                    image_file = request.FILES['image_file']
                    try:
                        img = Image.open(image_file)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img.thumbnail((800, 800))
                        buffer = io.BytesIO()
                        img.save(buffer, format="JPEG", quality=80)
                        projet.Image_projet = buffer.getvalue()
                    except Exception as e:
                        print(f"Erreur image: {e}")

                elif image_cache:
                    try:
                        img_data = base64.b64decode(image_cache)
                        img_buffer = io.BytesIO(img_data)

                        img = Image.open(img_buffer)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img.thumbnail((800, 800))

                        buffer = io.BytesIO()
                        img.save(buffer, format="JPEG", quality=80)
                        projet.Image_projet = buffer.getvalue()
                    except Exception as e:
                        print(f"Erreur image cache: {e}")

                try:
                    projet.createur = request.user.personne
                except Exception:
                    projet.createur = None
                projet.save()
                
                # Ajouter le créateur du projet comme participant
                try:
                    utilisateur_courant = request.user.personne
                    PersonneProjet.objects.get_or_create(
                        Id_Matricule=utilisateur_courant,
                        Id_projet=projet
                    )
                except Personne.DoesNotExist:
                    pass
                
                # Récupérer les personnes temporaires en session (si l'utilisateur les a ajoutées)
                personnes_temp = request.session.get('personnes_temp', []) or []


                matricule = request.POST.get('matricule')
                username = request.POST.get('username')
                if matricule:
                    try:
                        p = Personne.objects.get(Id_Matricule=matricule)
                        entry = {'id': p.Id_Matricule, 'nom': p.Nom, 'prenom': p.Prenom}
                        if entry not in personnes_temp:
                            personnes_temp.append(entry)
                    except Personne.DoesNotExist:
                        pass
                elif username:
                    parts = username.strip().split()
                    if len(parts) >= 2:
                        prenom = parts[0]
                        nom = ' '.join(parts[1:])
                        personnes_qs = Personne.objects.filter(Nom__iexact=nom, Prenom__iexact=prenom)
                        if personnes_qs.exists():
                            p = personnes_qs.first()
                            entry = {'id': p.Id_Matricule, 'nom': p.Nom, 'prenom': p.Prenom}
                            if entry not in personnes_temp:
                                personnes_temp.append(entry)
                invites = []
                for p_data in personnes_temp:
                    try:
                        personne = Personne.objects.get(Id_Matricule=p_data['id'])
                        PersonneProjet.objects.get_or_create(
                            Id_Matricule=personne,
                            Id_projet=projet
                        )
                        invites.append(personne)
                    except Personne.DoesNotExist:
                        continue

                # Créer une notification "Vous avez été ajouté dans NOMPROJET"
                if invites:
                    titre = f"Ajout au projet : {projet.Nom_projet}"
                    createur_texte = (
                        f"{utilisateur_courant.Prenom} {utilisateur_courant.Nom}"
                        if utilisateur_courant else "un utilisateur"
                    )
                    contenu = (
                        f"Vous avez été ajouté(e) dans le projet « {getattr(projet, 'Nom', projet.Nom_projet)} ».\n\n"
                        f"Créateur du projet : {createur_texte}\n"
                        f"Description : {getattr(projet, 'Description', '') or 'Non spécifiée'}\n"
                        f"Date de création : {timezone.localtime(timezone.now()).strftime('%d/%m/%Y à %H:%M')}\n"
                    )

                    notif = Notification.objects.create(
                        Titre=titre,
                        Contenu=contenu,
                        Type="PROJET"
                    )

                    # Lier la notification à chaque invité
                    for personne in invites:
                        PersonneNotification.objects.get_or_create(
                            Id_Matricule=personne,
                            Id_notif=notif
                        )

                # Nettoyer la session
                if 'personnes_temp' in request.session:
                    try:
                        del request.session['personnes_temp']
                    except KeyError:
                        pass
                
                return redirect('projects:project_detail', projet_id=projet.Id_projet)
    else:
        form = ProjetForm()
        personne_form = AjouterPersonneForm()
    
    personnes_temp = request.session.get('personnes_temp', [])
    return render(request, 'projects/creer_projet.html', {
        'form': form,
        'personne_form': personne_form,
        'personnes_temp': personnes_temp,
        'image_cache': image_cache
    })

@login_required
def detail_projet(request, projet_id):
    """Vue pour afficher les détails d'un projet"""

    projet = get_object_or_404(Projet, Id_projet=projet_id)
    membres = PersonneProjet.objects.filter(Id_projet=projet)
    fichiers = Fichier.objects.filter(Id_projet=projet).order_by('-Date_publication')
    
    # Vérifier si l'utilisateur est participant au projet
    try:
        utilisateur = request.user.personne
        is_participant = PersonneProjet.objects.filter(Id_Matricule=utilisateur, Id_projet=projet).exists()
    except Exception:
        is_participant = False
    
    return render(request, 'projects/details_projet.html', {
        'projet': projet, 
        'membres': membres,
        'fichiers': fichiers,
        'is_participant': is_participant
    })


@login_required
def edit_projet(request, projet_id):
    """Vue pour modifier la description et gérer les participants du projet"""
    projet = get_object_or_404(Projet, Id_projet=projet_id)

    # Vérifier que l'utilisateur connecté est bien le créateur
    try:
        utilisateur = request.user.personne
    except Exception:
        utilisateur = None

    if projet.createur is None or utilisateur is None or projet.createur != utilisateur:
        return render(request, 'projects/details_projet.html', {
            'projet': projet,
            'membres': PersonneProjet.objects.filter(Id_projet=projet),
            'error': "Vous n'êtes pas autorisé(e) à modifier ce projet. Seul le créateur peut apporter des modifications."
        }, status=403)

    if request.method == 'POST':

        if 'delete_image' in request.POST:
            projet.Image_projet = None
            projet.save()
            messages.success(request, "L'image du projet a été supprimée.")
            return redirect('projects:edit_projet', projet_id=projet.Id_projet)
        # Sauvegarder les modifications du projet
        if 'save_projet' in request.POST:
            form = ProjetForm(request.POST, request.FILES, instance=projet)
            if form.is_valid():
                projet_obj = form.save(commit=False)

                if 'image_file' in request.FILES:
                    image_file = request.FILES['image_file']
                    try:
                        img = Image.open(image_file)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')

                        img.thumbnail((800, 800))

                        buffer = io.BytesIO()
                        img.save(buffer, format="JPEG", quality=80)
                        projet_obj.Image_projet = buffer.getvalue()
                    except Exception as e:
                        print(f"Erreur image: {e}")
                projet_obj.save()
                messages.success(request, "Projet modifié avec succès.")
                return redirect('projects:project_detail', projet_id=projet.Id_projet)

        if 'add_person' in request.POST:
            add_form = AjouterPersonneForm(request.POST)
            if add_form.is_valid():
                # Vérifier si c'est l'ajout par rôle ou par personne individuelle
                personnes = add_form.cleaned_data.get('personnes')
                personne = add_form.cleaned_data.get('personne')
                
                count_added = 0
                if personnes:
                    # Ajouter toutes les personnes du rôle sélectionné
                    for p in personnes:
                        created = PersonneProjet.objects.get_or_create(Id_Matricule=p, Id_projet=projet)[1]
                        if created:
                            count_added += 1
                    if count_added > 0:
                        messages.success(request, f"{count_added} personne(s) du rôle ajoutée(s) au projet.")
                elif personne:
                    # Ajouter une seule personne
                    created = PersonneProjet.objects.get_or_create(Id_Matricule=personne, Id_projet=projet)[1]
                    if created:
                        messages.success(request, f"{personne.Prenom} {personne.Nom} a été ajouté(e) au projet.")
                    else:
                        messages.info(request, f"{personne.Prenom} {personne.Nom} est déjà membre du projet.")
                
                return redirect('projects:edit_projet', projet_id=projet.Id_projet)
            else:
                # Afficher les erreurs du formulaire
                for error in add_form.non_field_errors():
                    messages.error(request, str(error))
                for field, errors in add_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                
                # Recharger la page avec les erreurs visibles
                form = ProjetForm(instance=projet)
                membres = PersonneProjet.objects.filter(Id_projet=projet)
                return render(request, 'projects/edit_projet.html', {
                    'projet': projet,
                    'form': form,
                    'add_form': add_form,
                    'membres': membres,
                })

        # Retirer une personne
        if 'remove_person' in request.POST:
            personne_id = request.POST.get('remove_person')
            try:
                perso = Personne.objects.get(Id_Matricule=personne_id)
                PersonneProjet.objects.filter(Id_Matricule=perso, Id_projet=projet).delete()
            except Personne.DoesNotExist:
                pass
            return redirect('projects:edit_projet', projet_id=projet.Id_projet)


    form = ProjetForm(instance=projet)
    add_form = AjouterPersonneForm()
    membres = PersonneProjet.objects.filter(Id_projet=projet)
    return render(request, 'projects/edit_projet.html', {
        'projet': projet,
        'form': form,
        'add_form': add_form,
        'membres': membres,
    })


@login_required
def supprimer_projet(request, projet_id):
    """Permet au créateur du projet de le supprimer uniquement."""
    projet = get_object_or_404(Projet, Id_projet=projet_id)

    # Vérifier que l'utilisateur connecté est bien le créateur
    try:
        utilisateur = request.user.personne
    except Exception:
        utilisateur = None

    if projet.createur is None or utilisateur is None or projet.createur != utilisateur:
        # Interdire la suppression si l'utilisateur n'est pas le créateur
        return render(request, 'projects/details_projet.html', {
            'projet': projet,
            'membres': PersonneProjet.objects.filter(Id_projet=projet),
            'error': "Vous n'êtes pas autorisé(e) à supprimer ce projet."
        }, status=403)

    if request.method == 'POST':
        projet.delete()
        return redirect('projects:mes_projets')

    return render(request, 'projects/confirm_delete.html', {'projet': projet})




@login_required
def upload_fichier_projet(request, projet_id):
    """Vue pour permettre aux participants d'uploader des fichiers dans le projet"""
    projet = get_object_or_404(Projet, Id_projet=projet_id)
    
    # Vérifier que l'utilisateur est un participant du projet
    try:
        utilisateur = request.user.personne
    except Exception:
        utilisateur = None
    
    if utilisateur is None or not PersonneProjet.objects.filter(Id_Matricule=utilisateur, Id_projet=projet).exists():
        return render(request, 'projects/details_projet.html', {
            'projet': projet,
            'membres': PersonneProjet.objects.filter(Id_projet=projet),
            'error': "Vous n'êtes pas participant à ce projet et ne pouvez donc pas ajouter de fichiers."
        }, status=403)
    
    if request.method == 'POST':
        form = UploadFichierForm(request.POST, request.FILES)
        if form.is_valid():
            fichier_uploaded = request.FILES.get('fichier')
            if fichier_uploaded:
                fichier_contenu = fichier_uploaded.read()
                fichier_type = fichier_uploaded.content_type or 'application/octet-stream'
                
                # Créer l'enregistrement Fichier
                fichier = Fichier(
                    Nom=form.cleaned_data['Nom'] + os.path.splitext(fichier_uploaded.name)[1],
                    Description=form.cleaned_data.get('Description', ''),
                    Date_publication=timezone.now().date(),
                    fichier_contenu=fichier_contenu,
                    fichier_type=fichier_type,
                    Id_Matricule=utilisateur,
                    Id_projet=projet
                )
                fichier.save()

                participants_qs = PersonneProjet.objects.filter(Id_projet=projet)
                destinataires = [
                    pp.Id_Matricule for pp in participants_qs
                    if pp.Id_Matricule != utilisateur
                ]

                if destinataires:
                    titre = f"Nouveau fichier dans le projet : {projet.Nom_projet}"
                    contenu = (
                        f"Un nouveau fichier a été ajouté dans le projet « {getattr(projet, 'Nom', projet.Nom_projet)} ».\n\n"
                        f"Nom du fichier : {fichier.Nom}\n"
                        f"Description : {fichier.Description or 'Non spécifiée'}\n"
                        f"Auteur : {utilisateur.Prenom} {utilisateur.Nom}\n"
                        f"Date d'ajout : {timezone.localtime(timezone.now()).strftime('%d/%m/%Y à %H:%M')}\n"
                    )

                    notif = Notification.objects.create(
                        Titre=titre,
                        Contenu=contenu,
                        Type="PROJET_FICHIER"
                    )

                    for personne in destinataires:
                        PersonneNotification.objects.get_or_create(
                            Id_Matricule=personne,
                            Id_notif=notif
                        )

                return redirect('projects:project_detail', projet_id=projet.Id_projet)
    else:
        form = UploadFichierForm()
    
    return render(request, 'projects/upload_fichier.html', {
        'form': form,
        'projet': projet
    })


@login_required
def telecharger_fichier(request, fichier_id):
    """Vue sécurisée pour télécharger un fichier du projet depuis la base de données"""
    from django.http import HttpResponse, HttpResponseForbidden

    fichier = get_object_or_404(Fichier, Id_fichier=fichier_id)
    projet = fichier.Id_projet
    
    # Vérifier que l'utilisateur est participant du projet
    try:
        utilisateur = request.user.personne
    except Exception:
        utilisateur = None
    
    if utilisateur is None or not PersonneProjet.objects.filter(Id_Matricule=utilisateur, Id_projet=projet).exists():
        return HttpResponseForbidden("Vous n'avez pas accès à ce fichier. Vous devez être participant du projet.")
    
    if not fichier.fichier_contenu:
        return HttpResponseForbidden("Le fichier n'existe pas ou a été supprimé.")
    
    try:
        # Retourner le contenu du BLOB depuis la base de données
        response = HttpResponse(fichier.fichier_contenu, content_type=fichier.fichier_type)
        response['Content-Disposition'] = f'attachment; filename="{fichier.Nom}"'
        return response
    except Exception as e:
        return HttpResponseForbidden(f"Erreur lors du téléchargement : {str(e)}")


@login_required
def supprimer_fichier(request, fichier_id):
    """Vue pour supprimer un fichier du projet (seul propriétaire)"""
    fichier = get_object_or_404(Fichier, Id_fichier=fichier_id)
    projet = fichier.Id_projet
    
    # Vérifier que l'utilisateur est le propriétaire du fichier
    try:
        utilisateur = request.user.personne
    except Exception:
        utilisateur = None
    
    if utilisateur is None or fichier.Id_Matricule != utilisateur:
        return render(request, 'projects/details_projet.html', {
            'projet': projet,
            'membres': PersonneProjet.objects.filter(Id_projet=projet),
            'fichiers': Fichier.objects.filter(Id_projet=projet).order_by('-Date_publication'),
            'is_participant': PersonneProjet.objects.filter(Id_Matricule=utilisateur, Id_projet=projet).exists() if utilisateur else False,
            'error': "Vous n'êtes pas autorisé(e) à supprimer ce fichier. Seul le propriétaire peut le faire."
        }, status=403)
    
    if request.method == 'POST':
        fichier.delete()
        return redirect('projects:project_detail', projet_id=projet.Id_projet)
    
    return render(request, 'projects/confirm_delete_file.html', {
        'fichier': fichier,
        'projet': projet
    })
