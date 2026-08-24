# 🏔️ Géomanager — Plateforme de formation minière

Application web Django pour la gestion de formations en ligne avec système de paiement MaishaPay.

## ✨ Fonctionnalités

- **Formations vidéo** avec progression par leçon
- **Examens automatisés** avec correction instantanée
- **Certificats PDF** générés automatiquement
- **Paiement MaishaPay** (Mobile Money : Airtel, Orange, M-Pesa)
- **Dashboard admin** pour gérer formations, apprenants et transactions
- **Middleware d'abonnement** — bloque l'accès si non abonné

## 🚀 Déploiement sur PythonAnywhere (gratuit)

### 1. Créer un compte
- Allez sur [pythonanywhere.com](https://www.pythonanywhere.com)
- Créez un compte gratuit

### 2. Upload du code
- Dans le dashboard, allez dans **Files** → **Upload a file**
- Uploadez votre fichier `.zip` du projet (créez-le avec : `git archive -o geomanager.zip HEAD`)

Ou clonez depuis GitHub :
```bash
cd ~
git clone https://github.com/VOTRE_USERNAME/geomanager.git
```

### 3. Configurer l'environnement
Dans la console Bash PythonAnywhere :
```bash
cd ~/geomanager
pip3 install --user -r requirements.txt
```

### 4. Configurer les variables d'environnement
Créez le fichier `~/.env` :
```bash
nano ~/.env
```
Contenu :
```
DJANGO_SECRET_KEY=votre_cle_secrete_ici
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=VOTRE_USERNAME.pythonanywhere.com
MAISHAPAY_API_URL=https://marchand.maishapay.online/api/payment/rest/vers1.0/merchant
MAISHAPAY_API_KEY=MP-SBPK-EZD/tGzNI90s$26WQXIypk...
MAISHAPAY_SECRET_KEY=MP-SBSK-asnJY16TEDw0dfQfWoWp...
MAISHAPAY_MERCHANT_ID=003243
MAISHAPAY_CALLBACK_URL=https://VOTRE_USERNAME.pythonanywhere.com/paiement/callback/
```

### 5. Configurer la base de données
Dans la console Bash :
```bash
cd ~/geomanager
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py collectstatic --noinput
```

### 6. Configurer le Web App
- Allez dans **Web** → **Add a new web app**
- Choisissez **Manual configuration** → **Python 3.10**
- **Source code** : `/home/VOTRE_USERNAME/geomanager`

**Configuration WSGI** — éditez le fichier WSGI :
```python
import os
import sys

# Ajouter le projet au path
project_home = '/home/VOTRE_USERNAME/geomanager'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Charger le fichier .env
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geomanager.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Configuration Static files** :
| URL | Directory |
|-----|-----------|
| `/static/` | `/home/VOTRE_USERNAME/geomanager/staticfiles` |
| `/media/` | `/home/VOTRE_USERNAME/geomanager/media` |

### 7. Lancer !
Cliquez **Reload** et votre site est en ligne sur :
`https://VOTRE_USERNAME.pythonanywhere.com`

## 🛠️ Développement local

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## 📁 Structure du projet

```
geomanager/
├── courses/          # Application principale
│   ├── models.py     # Modèles Django
│   ├── views.py      # Vues (1400+ lignes)
│   ├── urls.py       # URLs
│   ├── middleware.py  # Middleware d'abonnement
│   ├── admin.py      # Admin Django
│   └── templates/    # Templates HTML
├── geomanager/       # Configuration Django
│   ├── settings.py   # Paramètres
│   └── urls.py       # URLs racine
├── static/           # Fichiers statiques
├── media/            # Fichiers uploadés
├── .env              # Variables d'environnement (NE PAS commit)
├── requirements.txt  # Dépendances Python
├── Procfile          # Pour Railway/Render
└── render.yaml       # Config Render
```

## 🔑 Variables d'environnement

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Clé secrète Django |
| `DJANGO_DEBUG` | Mode debug (True/False) |
| `DJANGO_ALLOWED_HOSTS` | Hôtes autorisés |
| `MAISHAPAY_API_URL` | URL API MaishaPay |
| `MAISHAPAY_API_KEY` | Clé publique MaishaPay |
| `MAISHAPAY_SECRET_KEY` | Clé secrète MaishaPay |
| `MAISHAPAY_MERCHANT_ID` | ID marchand MaishaPay |
| `MAISHAPAY_CALLBACK_URL` | URL de callback paiement |

## 📄 Licence

Projet privé — Tous droits réservés.
