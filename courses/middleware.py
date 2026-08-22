"""
Middleware Geomanager — Vérifie l'abonnement actif des apprenants.
Redirige vers la page de paiement si abonnement absent ou expiré.
"""

from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.conf import settings


# URLs publiques exemptées du blocage
URLS_PUBLIQUES = [
    'courses:login',
    'courses:logout',
    'courses:register',
    'courses:home',
    'courses:verifier_certificat',
    'courses:a_propos',
    'courses:terms',
    'courses:liste_formations',
    'courses:formation_detail',
]

# Préfixes d'URL exemptés (assets, media, admin, API)
PREFIXES_EXEMPTES = [
    '/static/',
    '/media/',
    '/admin/',
    '/favicon.ico',
]


class AbonnementMiddleware:
    """
    Intercepte les requêtes des apprenants connectés.
    Si l'abonnement n'est pas actif → redirection vers la page de paiement.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifier si l'utilisateur est connecté
        if request.user.is_authenticated:
            # Exempter les formateurs/staff
            if request.user.is_staff or request.user.is_superuser:
                return self.get_response(request)

            # Exempter les URLs publiques
            try:
                resolved = resolve(request.path_info)
                url_name = resolved.url_name
                namespace = resolved.namespace
                full_name = f'{namespace}:{url_name}' if namespace else url_name
                if full_name in URLS_PUBLIQUES:
                    return self.get_response(request)
            except Exception:
                pass

            # Exempter les préfixes d'assets
            for prefix in PREFIXES_EXEMPTES:
                if request.path_info.startswith(prefix):
                    return self.get_response(request)

            # Vérifier l'abonnement
            abonnement = getattr(request.user, 'abonnement', None)
            if abonnement is None or not abonnement.est_actif:
                # Ne pas rediriger si on est déjà sur la page de paiement
                try:
                    resolved = resolve(request.path_info)
                    if resolved.url_name in ('page_paiement', 'initier_paiement', 'callback_maishapay'):
                        return self.get_response(request)
                except Exception:
                    pass
                return redirect('courses:page_paiement')

        return self.get_response(request)
