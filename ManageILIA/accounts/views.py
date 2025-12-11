from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .forms import RegistrationForm, ProfilePhotoForm
from ILIA.models import Personne
import io
from PIL import Image
from django.core.files.base import ContentFile
from django.contrib.auth.models import User

class RegistrationView(View):
    def get(self, request):
        form = RegistrationForm()
        return render(request, 'register.html', {'form': form})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Demande d'inscription envoyée à l'administrateur")
            return redirect('login')
        return render(request, 'register.html',{"form":form})


class LoginView(auth_views.LoginView):
    template_name = 'login.html'


@login_required
def profile_view(request):
    # On récupère la personne liée à l'utilisateur connecté
    personne = get_object_or_404(Personne, user=request.user)
    roles = personne.roles.all()

    context = {
        "profile_user": request.user,
        "personne": personne,
        "roles": roles,
        "is_own_profile": True,
        "is_admin": request.user.is_superuser or request.user.is_staff,
    }
    return render(request, "accounts/profile.html", context)


@login_required
def user_profile(request, user_id):
    # L'utilisateur qu'on veut voir
    profile_user = get_object_or_404(User, pk=user_id)

    try:
        personne = profile_user.personne
        roles = personne.roles.all()
    except Personne.DoesNotExist:
        personne = None
        roles = None


    is_own_profile = (request.user == profile_user)
    is_admin = request.user.is_staff or request.user.is_superuser


    context = {
        'profile_user': profile_user,
        'personne': personne,
        'is_own_profile': is_own_profile,
        'roles': roles,
        'is_admin': is_admin,
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def upload_photo_view(request):
    personne = get_object_or_404(Personne, user=request.user)

    if request.method == 'POST':
        # SUPPRESSION
        if 'delete_photo' in request.POST:
            personne.Photo = None
            personne.save()
            messages.success(request, "Photo supprimée.")
            return redirect('accounts:profil')

        # UPLOAD ET COMPRESSION
        form = ProfilePhotoForm(request.POST, request.FILES)
        if form.is_valid() and request.FILES.get('photo_file'):
            uploaded_file = request.FILES['photo_file']

            try:

                image = Image.open(uploaded_file)


                if image.mode != 'RGB':
                    image = image.convert('RGB')


                image.thumbnail((300, 300))


                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=85)  # Qualité 85%


                personne.Photo = buffer.getvalue()
                personne.save()

                messages.success(request, "Photo mise à jour et compressée !")
                return redirect('accounts:profil')

            except Exception as e:
                messages.error(request, f"Erreur lors du traitement de l'image : {e}")
    else:
        form = ProfilePhotoForm()

    return render(request, 'accounts/upload_photo.html', {'form': form})