# Projet : Création d'un site web pour le service ILIA #

**Auteurs :** BROUILLARD Charline, CLAUS Christian, DEBILLOEZ Nathan, DEVILLEZ Amory\
**Cours :** Modélisation des données, big data et projet (Professeur Sidi Ahmed MAHMOUDI, Aurélie COOLS, Tojo Valisoa)

ManageILIA est une application web développée avec Django pour la gestion du service Informatique, Logiciel et Intelligence Artificielle (ILIA) de Polytech de Mons.


[Python Version] 3.10+
[Django Version] 5.2.8

### Prérequis
* Python 3.10
* Django 5.2.8
* Git

#### Installation en local :

1. Cloner le dépot : `git clone https://github.com/CCL04/Projet_GestionILIA.git`
2. Créer un environnement virtuel : `venv\Scripts\activate`
3. Installer les dépendances : `pip install -r requirements.txt` 
4. Configurer les variables d'environnement : `Placer le fichier .env dans ./ManageILIA`
5. Lancer les migrations et créer un admin : `python manage.py migrate` & `python manage.py createsuperuser`
6. Récupérer les fichiers statiques : `python manage.py collectstatic`
7. Lancer le serveur : `python manage.py runserver`


### Structure du projet :

```text
Projet_GestionILIA/
├── ManageILIA/          # Racine du projet Django
│   ├── ManageILIA/      # Configuration (settings, urls, wsgi)
│   ├── ILIA/            # Modèles généraux et vue Home
│   ├── accounts/        # Gestion des utilisateurs
│   ├── events/          # Gestion des évènements
│   ├── notifications/   # Système de notifications
│   ├── projects/        # Gestion des projets 
│   ├── reservations/    # Gestion des bureaux 
│   ├── templates/       # Fichiers HTML génériques
│   ├── staticfiles/     # CSS, JS, Images
│   ├── .env             # Variables d'environnement
│   ├── ssl.pem          # clé pour utilisation locale
│   └── manage.py
└── README.md
└── requirements.txt