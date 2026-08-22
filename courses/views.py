from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Count, Q, F, Sum
from django.utils import timezone

import os
import json
import hmac
import hashlib
import logging
import requests as http_requests
from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

logger = logging.getLogger(__name__)
from .models import Formation, Module, Lecon, Examen, Question, OptionReponse, Commentaire, TentativeExamen, VideoLecon, RessourceComplementaire, Inscription, ProgressionLecon
from .forms import CommentaireForm, FormationForm, LeconForm, ExamenForm, VideoLeconForm, RessourceForm
from .services import evaluer_examen, generer_certificat_pdf


def is_formateur(user):
    return user.is_authenticated and (user.is_staff or user.username.lower() == 'admin')


# ═══════════════════════════════════════
#  PAGE D'ACCUEIL
# ═══════════════════════════════════════
def home(request):
    # ── Statistiques réelles de la plateforme ──
    total_formations = Formation.objects.count()
    total_modules = Module.objects.count()
    total_lecons = Lecon.objects.count()
    total_videos = VideoLecon.objects.count()
    total_etudiants = User.objects.filter(is_staff=False).count()
    total_inscriptions = Inscription.objects.count()
    total_tentatives = TentativeExamen.objects.filter(est_termine=True).count()

    # Certifications réussies
    nb_certifies = 0
    for t in TentativeExamen.objects.filter(est_termine=True):
        if t.note >= t.examen.formation.seuil_certification:
            nb_certifies += 1

    # Heures totales de contenu
    total_secondes = VideoLecon.objects.aggregate(total=models.Sum('duree_secondes'))['total'] or 0
    total_heures = round(total_secondes / 3600, 1)

    stats = [
        {
            'valeur': str(total_formations),
            'label': 'Formations certifiantes',
            'color': 'teal',
            'icon_html': '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>'
        },
        {
            'valeur': f'{total_heures}h',
            'label': 'Heures de contenu',
            'color': 'copper',
            'icon_html': '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
        },
        {
            'valeur': str(total_etudiants),
            'label': 'Apprenants inscrits',
            'color': 'slate',
            'icon_html': '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>'
        },
        {
            'valeur': str(nb_certifies),
            'label': 'Certifications délivrées',
            'color': 'emerald',
            'icon_html': '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>'
        },
    ]

    # Formations les plus récentes pour la section "Découvrir"
    formations_recentes = Formation.objects.annotate(
        nb_vid=Count('videos'),
    ).order_by('-date_creation')[:6]

    # Domaines avec compteurs
    domaines = []
    for code, label in Formation.DOMAINE_CHOICES:
        count = Formation.objects.filter(domaine=code).count()
        if count > 0:
            domaines.append({'code': code, 'label': label, 'count': count})

    return render(request, 'courses/home.html', {
        'stats': stats,
        'formations_recentes': formations_recentes,
        'domaines': domaines,
        'total_modules': total_modules,
        'total_lecons': total_lecons,
        'nb_certifies': nb_certifies,
        'total_heures': total_heures,
    })


# ═══════════════════════════════════════
#  AUTHENTIFICATION
# ═══════════════════════════════════════
def login_view(request):
    if request.user.is_authenticated:
        if is_formateur(request.user):
            return redirect('courses:admin_dashboard')
        return redirect('courses:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if is_formateur(user):
                next_url = request.GET.get('next', 'courses:admin_dashboard')
            else:
                next_url = request.GET.get('next', 'courses:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')

    return render(request, 'courses/login.html', {'next': request.GET.get('next', '')})


def logout_view(request):
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('courses:home')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('courses:home')

    avantages = [
        'Accès à toutes les formations certifiantes',
        'Suivi personnalisé de votre progression',
        'Communauté d\'experts miniers',
        'Certificats reconnus par le secteur',
    ]

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        # Validations
        errors = []
        if not full_name or not email or not username or not password1 or not password2:
            errors.append('Tous les champs sont obligatoires.')
        if password1 != password2:
            errors.append('Les mots de passe ne correspondent pas.')
        if len(password1) < 8:
            errors.append('Le mot de passe doit contenir au moins 8 caractères.')
        if User.objects.filter(username=username).exists():
            errors.append('Ce nom d\'utilisateur est déjà pris.')
        if User.objects.filter(email=email).exists():
            errors.append('Cet email est déjà utilisé.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=full_name,
            )
            login(request, user)
            messages.success(request, f'Bienvenue {full_name} ! Votre compte a été créé.')
            return redirect('courses:dashboard')

    return render(request, 'courses/register.html', {'avantages': avantages})


# ═══════════════════════════════════════
#  TABLEAU DE BORD
# ═══════════════════════════════════════
@login_required
def dashboard_view(request):
    user = request.user
    inscriptions = Inscription.objects.filter(etudiant=user).select_related('formation')
    formations_inscrites = [i.formation for i in inscriptions]

    tentatives = TentativeExamen.objects.filter(etudiant=user)
    tentatives_terminees = tentatives.filter(est_termine=True).select_related('examen__formation')

    # Structurer les certifications pour le template
    certifications = []
    for t in tentatives_terminees:
        seuil = t.examen.formation.seuil_certification
        est_certifie = t.note >= seuil
        certifications.append({
            'tentative': t,
            'seuil': seuil,
            'est_certifie': est_certifie,
        })

    # Progression par formation (basée sur les vidéos vues)
    progression_data = []
    actions_contextuelles = []
    for inscription in inscriptions:
        f = inscription.formation
        total_videos = f.videos.count()
        videos_vues = ProgressionLecon.objects.filter(
            etudiant=user, video__formation=f, vue=True
        ).count()
        pourcentage = round((videos_vues / total_videos) * 100) if total_videos > 0 else 0
        est_complete = pourcentage >= 100
        progression_data.append({
            'formation': f,
            'total': total_videos,
            'vues': videos_vues,
            'pourcentage': pourcentage,
            'est_complete': est_complete,
        })

        # ── Carte d'action contextuelle par formation ──
        examen = f.examens.first()
        # Dernière vidéo non vue
        video_suivante = None
        if not est_complete:
            vues_ids = ProgressionLecon.objects.filter(
                etudiant=user, video__formation=f, vue=True
            ).values_list('video_id', flat=True)
            video_suivante = f.videos.exclude(id__in=vues_ids).order_by('ordre').first()

        # Vérifier certificat
        est_certifie = False
        a_echoue = False
        derniere_tentative = None
        certificat_url = None
        if examen:
            derniere_tentative = TentativeExamen.objects.filter(
                etudiant=user, examen=examen, est_termine=True
            ).order_by('-date_soumission').first()
            if derniere_tentative:
                est_certifie = derniere_tentative.note >= f.seuil_certification
                a_echoue = not est_certifie
                if est_certifie:
                    certificat_url = f"{settings.MEDIA_URL}certificats/certificat_{user.username}_{f.id}_{derniere_tentative.id}.pdf"

        action = {
            'formation': f,
            'pourcentage': pourcentage,
            'est_complete': est_complete,
            'est_certifie': est_certifie,
            'a_echoue': a_echoue,
            'video_suivante': video_suivante,
            'examen': examen,
            'certificat_url': certificat_url,
            'derniere_tentative': derniere_tentative,
            'duree_examen_auto': examen.questions.count() * 2 if examen else 0,
        }
        actions_contextuelles.append(action)

    # Stats pour formateur
    stats_formateur = {}
    if user.is_staff:
        stats_formateur = {
            'total_formations': Formation.objects.count(),
            'total_lecons': Lecon.objects.count(),
            'total_examens': Examen.objects.count(),
            'total_etudiants': User.objects.filter(is_staff=False).count(),
            'total_tentatives': TentativeExamen.objects.count(),
        }

    return render(request, 'courses/dashboard.html', {
        'progression_data': progression_data,
        'actions_contextuelles': actions_contextuelles,
        'certifications': certifications,
        'stats_formateur': stats_formateur,
    })


# ═══════════════════════════════════════
#  PROFIL UTILISATEUR
# ═══════════════════════════════════════
@login_required
def profile_view(request):
    user = request.user
    tentatives = TentativeExamen.objects.filter(etudiant=user).order_by('-date_soumission')[:5]

    if request.method == 'POST':
        form_type = request.POST.get('form_type', '')

        if form_type == 'profile':
            # Modifier les infos profil
            full_name = request.POST.get('full_name', '').strip()
            email = request.POST.get('email', '').strip()
            if full_name:
                parts = full_name.split(' ', 1)
                user.first_name = parts[0]
                user.last_name = parts[1] if len(parts) > 1 else ''
            if email:
                user.email = email
            user.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('courses:profile')

        elif form_type == 'password':
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                login(request, user)
                messages.success(request, 'Votre mot de passe a été modifié avec succès.')
                return redirect('courses:profile')
            else:
                messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        password_form = PasswordChangeForm(user)

    return render(request, 'courses/profile.html', {
        'password_form': password_form,
        'tentatives': tentatives,
    })


def terms_view(request):
    return render(request, 'courses/terms.html')


def a_propos_view(request):
    return render(request, 'courses/a_propos.html')


def verifier_certificat_view(request):
    """Vérification publique d'un certificat par son numéro unique."""
    numero = request.GET.get('numero', '').strip().upper()
    resultat = None
    erreur = None

    if numero:
        tentative = TentativeExamen.objects.filter(
            numero_certificat=numero,
            est_termine=True,
        ).select_related('etudiant', 'examen__formation').first()

        if tentative:
            seuil = tentative.examen.formation.seuil_certification
            if tentative.note >= seuil:
                resultat = {
                    'numero': tentative.numero_certificat,
                    'apprenant': tentative.etudiant.get_full_name() or tentative.etudiant.username,
                    'formation': tentative.examen.formation.titre,
                    'score': f"{tentative.note:.1f}%",
                    'date': tentative.date_soumission.strftime('%d/%m/%Y') if tentative.date_soumission else 'N/A',
                    'formateur': 'Delphin BAZIBUHE',
                    'statut': 'Certificat Authentique',
                }
            else:
                erreur = 'Ce certificat n\'est pas valide (note insuffisante).'
        else:
            erreur = 'Aucun certificat trouvé avec ce numéro.'

    return render(request, 'courses/verifier_certificat.html', {
        'numero': numero,
        'resultat': resultat,
        'erreur': erreur,
    })


# ═══════════════════════════════════════
#  PAIEMENT & ABONNEMENTS
# ═══════════════════════════════════════
import uuid
from .models import Abonnement, TransactionPaiement, ProlongationAbonnement


def _verifier_signature_maishapay(payload_bytes, signature_header):
    """
    Vérifie la signature HMAC envoyée par MaishaPay dans le header X-MaishaPay-Signature.
    Retourne True si la signature est valide, False sinon.
    Si pas de SECRET_KEY configuré, on accepte (mode dev).
    """
    secret = getattr(settings, 'MAISHAPAY_SECRET_KEY', '')
    if not secret:
        # Pas de clé secrète configurée → mode développement
        logger.warning('MAISHAPAY_SECRET_KEY non configurée — signature non vérifiée (mode dev)')
        return True
    if not signature_header:
        logger.warning('Callback MaishaPay sans header de signature')
        return False
    expected = hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@login_required
def page_paiement(request):
    """Page de paiement — informe l'apprenant que son abonnement est requis."""
    abonnement = getattr(request.user, 'abonnement', None)
    statut_abonnement = None
    if abonnement:
        statut_abonnement = {
            'actif': abonnement.est_actif,
            'date_expiration': abonnement.date_expiration,
            'reseau': abonnement.get_reseau_display() if abonnement.reseau else '',
        }

    reseaux = Abonnement.RESEAU_CHOICES
    montant = getattr(settings, 'MAISHAPAY_MONTANT_ABONNEMENT', 10000)

    # Récupérer la dernière référence de transaction (pour le polling JS)
    derniere_reference = request.session.pop('gm_derniere_reference', None)

    return render(request, 'courses/page_paiement.html', {
        'abonnement': abonnement,
        'statut_abonnement': statut_abonnement,
        'reseaux': reseaux,
        'montant': montant,
        'derniere_reference': derniere_reference,
    })


@login_required
def initier_paiement(request):
    """Initialise le paiement via l'API MaishaPay."""
    if request.method != 'POST':
        return redirect('courses:page_paiement')

    reseau = request.POST.get('reseau', 'airtel')
    telephone = request.POST.get('telephone', '').strip()

    if not telephone:
        messages.error(request, 'Veuillez saisir votre numéro de téléphone.')
        return redirect('courses:page_paiement')

    # Nettoyer le numéro (enlever espaces et tirets, garder le +)
    telephone = telephone.replace(' ', '').replace('-', '')
    if not telephone.startswith('+'):
        telephone = '+' + telephone

    # Récupérer ou créer l'abonnement
    abonnement, _ = Abonnement.objects.get_or_create(
        utilisateur=request.user,
        defaults={'reseau': reseau, 'telephone': telephone},
    )
    if abonnement.reseau != reseau:
        abonnement.reseau = reseau
    if abonnement.telephone != telephone:
        abonnement.telephone = telephone
    abonnement.save(update_fields=['reseau', 'telephone', 'date_modification'])

    # Créer la transaction
    reference = f"GM-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    montant = getattr(settings, 'MAISHAPAY_MONTANT_ABONNEMENT', 10000)

    transaction = TransactionPaiement.objects.create(
        abonnement=abonnement,
        reference_externe=reference,
        montant=montant,
        devise='CDF',
        telephone=telephone,
        reseau=reseau,
    )

    logger.info(f"Transaction {reference} créée pour {telephone} ({reseau}) — {montant} CDF")

    # ── Appel à l'API MaishaPay Sandbox ──
    api_url = getattr(settings, 'MAISHAPAY_API_URL', '')
    public_key = getattr(settings, 'MAISHAPAY_API_KEY', '')
    secret_key = getattr(settings, 'MAISHAPAY_SECRET_KEY', '')
    merchant_id = getattr(settings, 'MAISHAPAY_MERCHANT_ID', '')

    # Mapper le reseau en majuscules pour l'API
    provider_map = {'airtel': 'AIRTEL', 'vodacom': 'MPESA', 'orange': 'ORANGE', 'africell': 'AFRICELL'}
    provider_api = provider_map.get(reseau, reseau.upper())

    # ── Mode démo : bypass API si MAISHAPAY_DEMO_MODE=True ──
    if getattr(settings, 'MAISHAPAY_DEMO_MODE', False):
        logger.info(f"Transaction {reference}: MODE DÉMO actif — activation immédiate")
        transaction.marquer_reussi({
            'mode': 'demo',
            'message': 'Mode démo activé — activation sans appel API MaishaPay',
        })
        abonnement.activer(jours=getattr(settings, 'MAISHAPAY_DUREE_ABONNEMENT_JOURS', 30))
        messages.success(
            request,
            f'✅ Paiement de {montant} CDF confirmé (mode démo). '
            f'Votre abonnement est actif pour 30 jours.'
        )
        request.session['gm_derniere_reference'] = reference
        return redirect('courses:dashboard')

    if api_url and public_key and secret_key:
        try:
            payload = {
                'publicApiKey': public_key,
                'secretApiKey': secret_key,
                'merchantId': merchant_id,
                'gatewayMode': 0,
                'transactionReference': reference,
                'amount': float(montant),
                'currency': 'CDF',
                'chanel': 'MOBILEMONEY',
                'provider': provider_api,
                'walletID': telephone,
                'callbackUrl': getattr(settings, 'MAISHAPAY_CALLBACK_URL', ''),
            }
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            logger.info(f"Appel API MaishaPay: POST {api_url}")
            logger.info(f"Payload: {{'transactionReference': '{reference}', 'amount': {montant}, 'provider': '{provider_api}', 'walletID': '{telephone}'}}")
            resp = http_requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=15,
            )
            logger.info(f"Reponse MaishaPay {reference}: HTTP {resp.status_code}")
            if resp.status_code in (200, 201):
                try:
                    data = resp.json()
                except Exception:
                    data = {'raw': resp.text[:500]}
                transaction.metadata_reponse = data
                transaction.save(update_fields=['metadata_reponse'])
                logger.info(f"Transaction {reference} initiée: {data}")
                messages.success(
                    request,
                    f'Paiement initié. Vérifiez votre téléphone ({telephone}) '
                    f'pour confirmer le transfert de {montant} CDF.'
                )
            else:
                logger.error(f"Erreur API MaishaPay {reference}: HTTP {resp.status_code} — {resp.text[:300]}")
                transaction.marquer_echoue({'status_code': resp.status_code, 'body': resp.text[:500]})
                messages.error(request, f'Erreur API MaishaPay (HTTP {resp.status_code}). Réessayez.')
        except http_requests.exceptions.ConnectionError:
            logger.error(f"Erreur connexion MaishaPay pour {reference}")
            transaction.marquer_echoue({'error': 'Impossible de joindre le serveur MaishaPay'})
            messages.error(request, 'Service de paiement momentanément indisponible. Réessayez dans quelques instants.')
        except http_requests.exceptions.Timeout:
            logger.error(f"Timeout MaishaPay pour {reference}")
            transaction.marquer_echoue({'error': 'Timeout de connexion'})
            messages.error(request, 'Le service de paiement met trop de temps à répondre. Réessayez.')
        except Exception as e:
            logger.exception(f"Erreur inattendue MaishaPay pour {reference}")
            transaction.marquer_echoue({'error': str(e)})
            messages.error(request, f'Erreur de connexion au service de paiement : {str(e)}')
    else:
        # ── Mode démo : activation immédiate si pas de clé API ──
        logger.info(f"Transaction {reference}: mode démo (pas de clé API)")
        transaction.marquer_reussi({'mode': 'demo', 'message': 'Clé API non configurée — activation démo'})
        messages.success(
            request,
            f'✅ Paiement de {montant} CDF confirmé (mode démo). '
            f'Votre abonnement est actif pour 30 jours.'
        )

    # Stocker la référence dans la session pour le polling côté client
    request.session['gm_derniere_reference'] = reference
    return redirect('courses:page_paiement')


@login_required
def verifier_statut_transaction(request, reference):
    """
    Endpoint de polling — l'apprenant peut vérifier si sa transaction a été confirmée.
    Utilisé par le JavaScript côté client pour mettre à jour l'UI automatiquement.
    """
    try:
        transaction = TransactionPaiement.objects.get(
            reference_externe=reference,
            abonnement__utilisateur=request.user,
        )
    except TransactionPaiement.DoesNotExist:
        return JsonResponse({'statut': 'inconnu', 'message': 'Transaction introuvable'}, status=404)

    response_data = {
        'statut': transaction.statut,
        'reference': transaction.reference_externe,
        'montant': float(transaction.montant),
        'devise': transaction.devise,
        'reseau': transaction.reseau,
        'date_creation': transaction.date_creation.isoformat() if transaction.date_creation else None,
    }

    if transaction.statut == 'reussi':
        abonnement = transaction.abonnement
        response_data['message'] = 'Paiement confirmé !'
        response_data['abonnement_actif'] = abonnement.est_actif
        response_data['date_expiration'] = abonnement.date_expiration.isoformat() if abonnement.date_expiration else None
    elif transaction.statut == 'echoue':
        response_data['message'] = 'Le paiement a échoué.'
    elif transaction.statut == 'en_attente':
        response_data['message'] = 'En attente de confirmation...'

    return JsonResponse(response_data)


@csrf_exempt
def callback_maishapay(request):
    """
    Webhook/callback MaishaPay — reçoit la confirmation de paiement.
    Vérifie la signature HMAC pour sécuriser l'endpoint.
    """
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    # ── Lecture du body brut (pour vérification signature) ──
    raw_body = request.body
    signature_header = request.headers.get('X-MaishaPay-Signature', '') or \
                       request.headers.get('x-maishapay-signature', '')

    # ── Vérification HMAC ──
    if not _verifier_signature_maishapay(raw_body, signature_header):
        logger.warning('Callback MaishaPay: signature invalide rejeté')
        return HttpResponse('Invalid signature', status=403)

    # ── Parsing JSON ──
    try:
        data = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError):
        logger.error('Callback MaishaPay: JSON invalide')
        return HttpResponse('Invalid JSON', status=400)

    reference = data.get('reference', data.get('external_reference', ''))
    status = data.get('status', '')

    if not reference:
        logger.warning('Callback MaishaPay: référence manquante dans le payload')
        return HttpResponse('Missing reference', status=400)

    logger.info(f"Callback MaishaPay reçu: reference={reference}, status={status}")

    try:
        transaction = TransactionPaiement.objects.get(reference_externe=reference)
    except TransactionPaiement.DoesNotExist:
        logger.warning(f"Callback MaishaPay: transaction {reference} introuvable")
        return HttpResponse('Transaction not found', status=404)

    # ── Mise à jour du statut ──
    if status in ('successful', 'completed', 'success'):
        logger.info(f"Transaction {reference} marquée comme RÉUSSIE")
        transaction.marquer_reussi(data)
    elif status in ('failed', 'error', 'cancelled'):
        logger.warning(f"Transaction {reference} marquée comme ÉCHOUÉE")
        transaction.marquer_echoue(data)
    else:
        logger.info(f"Transaction {reference}: statut inconnu '{status}' — stocké en metadata")
        transaction.metadata_reponse = data
        transaction.save(update_fields=['metadata_reponse'])

    return JsonResponse({'status': 'ok', 'reference': reference})


@login_required
def mes_certifications_view(request):
    user = request.user

    # ── 1. Formations terminées à 100% dont l'examen n'a pas encore été réussi ──
    formations_terminees = []
    inscriptions = Inscription.objects.filter(etudiant=user).select_related('formation')
    for inscription in inscriptions:
        f = inscription.formation
        total_videos = f.videos.count()
        if total_videos == 0:
            continue
        videos_vues = ProgressionLecon.objects.filter(
            etudiant=user, video__formation=f, vue=True
        ).count()
        pourcentage = round((videos_vues / total_videos) * 100)
        if pourcentage < 100:
            continue

        examen = f.examens.first()

        # Vérifier si déjà certifié (si examen existe)
        est_deja_certifie = False
        if examen:
            est_deja_certifie = TentativeExamen.objects.filter(
                etudiant=user, examen=examen, est_termine=True,
                note__gte=f.seuil_certification
            ).exists()
        if est_deja_certifie:
            continue

        duree_auto = examen.questions.count() * 2 if examen else 0
        formations_terminees.append({
            'formation': f,
            'examen': examen,
            'duree_examen_auto': duree_auto,
            'pas_examen': examen is None,
        })

    # ── 2. Tentatives d'examens passées (réussies + échouées) ──
    tentatives = TentativeExamen.objects.filter(
        etudiant=user, est_termine=True
    ).select_related('examen__formation').order_by('-date_soumission')

    certifications = []
    for t in tentatives:
        seuil = t.examen.formation.seuil_certification
        est_certifie = t.note >= seuil
        certifications.append({
            'tentative': t,
            'seuil': seuil,
            'est_certifie': est_certifie,
        })

    # ── 3. Vérifier s'il y a au moins une formation ou un examen ──
    nb_inscriptions = inscriptions.count()
    formations_en_cours = 0
    for inscription in inscriptions:
        f = inscription.formation
        total_videos = f.videos.count()
        if total_videos == 0:
            continue
        videos_vues = ProgressionLecon.objects.filter(
            etudiant=user, video__formation=f, vue=True
        ).count()
        if round((videos_vues / total_videos) * 100) < 100:
            formations_en_cours += 1

    return render(request, 'courses/mes_certifications.html', {
        'formations_terminees': formations_terminees,
        'certifications': certifications,
        'nb_inscriptions': nb_inscriptions,
        'formations_en_cours': formations_en_cours,
    })


@login_required
def telecharger_certificat(request, tentative_id):
    """Télécharge le certificat PDF d'une tentative certifiée."""
    tentative = get_object_or_404(
        TentativeExamen, id=tentative_id, etudiant=request.user, est_termine=True
    )
    formation = tentative.examen.formation
    est_certifie = tentative.note >= formation.seuil_certification
    if not est_certifie:
        messages.error(request, 'Vous n\'êtes pas certifié pour cette tentative.')
        return redirect('courses:mes_certifications')

    filename = f"certificat_{request.user.username}_{formation.id}_{tentative.id}.pdf"
    pdf_bytes = None

    # 1) Tenter de lire depuis le cache disque (utile en local)
    try:
        filepath = os.path.join(settings.MEDIA_ROOT, 'certificats', filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                pdf_bytes = f.read()
    except OSError:
        pass

    # 2) Générer en mémoire si pas en cache (compatible serverless)
    if not pdf_bytes:
        try:
            pdf_bytes = generer_certificat_pdf(request.user, formation, tentative)
            if not pdf_bytes:
                messages.error(request, 'Erreur lors de la génération du certificat.')
                return redirect('courses:mes_certifications')
        except Exception as e:
            messages.error(request, f"Erreur lors de la génération du certificat : {str(e)}")
            return redirect('courses:mes_certifications')

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def visualiser_certificat(request, tentative_id):
    """Prévisualise le certificat PDF en ligne (inline) sans le télécharger."""
    tentative = get_object_or_404(
        TentativeExamen, id=tentative_id, etudiant=request.user, est_termine=True
    )
    formation = tentative.examen.formation
    est_certifie = tentative.note >= formation.seuil_certification
    if not est_certifie:
        messages.error(request, 'Vous n\'êtes pas certifié pour cette tentative.')
        return redirect('courses:mes_certifications')

    filename = f"certificat_{request.user.username}_{formation.id}_{tentative.id}.pdf"
    pdf_bytes = None

    # 1) Tenter de lire depuis le cache disque (utile en local)
    try:
        filepath = os.path.join(settings.MEDIA_ROOT, 'certificats', filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                pdf_bytes = f.read()
    except OSError:
        pass

    # 2) Générer en mémoire si pas en cache (compatible serverless)
    if not pdf_bytes:
        try:
            pdf_bytes = generer_certificat_pdf(request.user, formation, tentative)
            if not pdf_bytes:
                messages.error(request, 'Erreur lors de la génération du certificat.')
                return redirect('courses:mes_certifications')
        except Exception as e:
            messages.error(request, f"Erreur certificat : {str(e)}")
            return redirect('courses:mes_certifications')

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="Certificat.pdf"'
    return response


@user_passes_test(is_formateur, login_url='courses:login')
def admin_dashboard_view(request):
    from django.db.models import Avg
    formations = Formation.objects.annotate(
        nb_modules=Count('modules', distinct=True),
        nb_lecons=Count('modules__lecons', distinct=True),
    )
    apprenants = User.objects.filter(is_staff=False)
    tentatives = TentativeExamen.objects.filter(est_termine=True)
    nb_certifies = 0
    for t in tentatives:
        if t.note >= t.examen.formation.seuil_certification:
            nb_certifies += 1
    stats = {
        'total_formations': Formation.objects.count(),
        'total_apprenants': apprenants.count(),
        'total_examens_passes': tentatives.count(),
        'total_certifies': nb_certifies,
        'total_lecons': Lecon.objects.count(),
        'taux_reussite': round((nb_certifies / tentatives.count() * 100), 1) if tentatives.count() > 0 else 0,
    }
    return render(request, 'courses/admin_dashboard.html', {'stats': stats, 'formations': formations})


# ═══════════════════════════════════════
#  ESPACE FORMATEUR / ADMIN
# ═══════════════════════════════════════
@user_passes_test(is_formateur, login_url='courses:login')
def admin_formations(request):
    formations = Formation.objects.annotate(
        nb_modules=Count('modules', distinct=True),
        nb_lecons=Count('modules__lecons', distinct=True),
        nb_examens=Count('examens', distinct=True),
    ).order_by('-date_creation')
    return render(request, 'courses/admin_formations.html', {'formations': formations})


@user_passes_test(is_formateur, login_url='courses:login')
def admin_formation_form(request, formation_id=None):
    if formation_id:
        formation = get_object_or_404(Formation, id=formation_id)
        titre_page = 'Modifier la formation'
    else:
        formation = None
        titre_page = 'Nouvelle formation'

    if request.method == 'POST':
        form = FormationForm(request.POST, request.FILES, instance=formation)
        if form.is_valid():
            f = form.save(commit=False)
            if not f.instructeur:
                f.instructeur = request.user
            f.save()

            # ── Vidéos ──
            vid_titres = request.POST.getlist('video_titre')
            vid_fichiers = request.FILES.getlist('video_fichier')
            vid_urls = request.POST.getlist('video_url')
            # Supprimer les anciennes vidéos si édition
            if formation:
                f.videos.all().delete()
            for i, titre in enumerate(vid_titres):
                if not titre.strip():
                	continue
                fichier = vid_fichiers[i] if i < len(vid_fichiers) and vid_fichiers[i] else None
                url = vid_urls[i] if i < len(vid_urls) and vid_urls[i].strip() else None
                VideoLecon.objects.create(
                    formation=f, titre=titre.strip(),
                    fichier_video=fichier, video_url=url,
                    ordre=i
                )
            # Recalculer la durée totale (auto-détectée par moviepy dans save())
            f.recalculer_duree()

            # ── Ressources complémentaires ──
            res_titres = request.POST.getlist('ressource_titre')
            res_types = request.POST.getlist('ressource_type')
            res_fichiers = request.FILES.getlist('ressource_fichier')
            res_liens = request.POST.getlist('ressource_lien')
            if formation:
                f.ressources.all().delete()
            for i, (titre, rtype) in enumerate(zip(res_titres, res_types)):
                if not titre.strip():
                	continue
                fichier = res_fichiers[i] if i < len(res_fichiers) and res_fichiers[i] else None
                lien = res_liens[i] if i < len(res_liens) and res_liens[i].strip() else None
                RessourceComplementaire.objects.create(
                    formation=f, titre=titre.strip(),
                    type_ressource=rtype, fichier=fichier, lien_web=lien
                )

            # ── Examen QCM ──
            exam_titre = request.POST.get('exam_titre', '').strip()
            exam_desc = request.POST.get('exam_description', '').strip()
            exam_duree = request.POST.get('exam_duree', 60)
            exam_note = request.POST.get('exam_note_minimale', 50)

            # ── Validation des questions ──
            q_textes = [t.strip() for t in request.POST.getlist('question_texte') if t.strip()]
            exam_errors = []
            if not exam_titre:
                exam_errors.append('Le titre de l\'examen est requis.')
            if not q_textes:
                exam_errors.append('Au moins une question est requise pour l\'examen.')

            for qi, q_text in enumerate(q_textes):
                opt_textes = []
                for oi in range(20):
                    ot = request.POST.get(f'option_texte_{qi}_{oi}', '').strip()
                    if ot:
                        opt_textes.append(ot)
                if len(opt_textes) < 2:
                    exam_errors.append(f'Question #{qi+1} "{q_text[:50]}" : au moins 2 options de réponse requises.')
                has_correct = any(
                    request.POST.get(f'option_correcte_{qi}_{oi}')
                    for oi in range(len(opt_textes))
                )
                if len(opt_textes) >= 2 and not has_correct:
                    exam_errors.append(f'Question #{qi+1} "{q_text[:50]}" : cochez au moins une réponse correcte.')

            if exam_errors:
                for err in exam_errors:
                    messages.error(request, err)
                videos = formation.videos.all() if formation else []
                ressources = formation.ressources.all() if formation else []
                examen = formation.examens.first() if formation else None
                questions = examen.questions.prefetch_related('options').all() if examen else []
                return render(request, 'courses/admin_formation_form.html', {
                    'form': form,
                    'formation': formation,
                    'titre_page': titre_page,
                    'videos': videos,
                    'ressources': ressources,
                    'examen': examen,
                    'questions': questions,
                })

            if exam_titre:
                examen, _ = Examen.objects.update_or_create(
                    formation=f, defaults={
                        'titre': exam_titre, 'description': exam_desc,
                        'duree_minutes': int(exam_duree) if exam_duree else 60,
                        'note_minimale': float(exam_note) if exam_note else 50,
                    }
                )
                # Supprimer anciennes questions
                examen.questions.all().delete()
                for qi, q_text in enumerate(q_textes):
                    q = Question.objects.create(examen=examen, texte=q_text, ordre=qi)
                    for oi in range(20):
                        ot = request.POST.get(f'option_texte_{qi}_{oi}', '').strip()
                        if not ot:
                            continue
                        is_correcte = bool(request.POST.get(f'option_correcte_{qi}_{oi}'))
                        OptionReponse.objects.create(
                            question=q, texte=ot,
                            est_correcte=is_correcte
                        )

            messages.success(request, f'Formation "{f.titre}" enregistrée avec succès.')
            return redirect('courses:admin_formations')
    else:
        form = FormationForm(instance=formation)

    # Sous-éléments si édition
    videos = formation.videos.all() if formation else []
    ressources = formation.ressources.all() if formation else []
    examen = formation.examens.first() if formation else None
    questions = examen.questions.prefetch_related('options').all() if examen else []

    return render(request, 'courses/admin_formation_form.html', {
        'form': form,
        'formation': formation,
        'titre_page': titre_page,
        'videos': videos,
        'ressources': ressources,
        'examen': examen,
        'questions': questions,
    })


@user_passes_test(is_formateur, login_url='courses:login')
def admin_formation_delete(request, formation_id):
    formation = get_object_or_404(Formation, id=formation_id)
    if request.method == 'POST':
        titre = formation.titre
        formation.delete()
        messages.success(request, f'Formation "{titre}" supprimée.')
    return redirect('courses:admin_formations')


@user_passes_test(is_formateur, login_url='courses:login')
def admin_module_add(request, formation_id):
    formation = get_object_or_404(Formation, id=formation_id)
    if request.method == 'POST':
        Module.objects.create(
            formation=formation,
            titre=request.POST.get('titre', '').strip(),
            description=request.POST.get('description', '').strip(),
            ordre=request.POST.get('ordre', 0),
        )
        messages.success(request, 'Module ajouté.')
    return redirect('courses:admin_formation_form', formation_id=formation.id)


@user_passes_test(is_formateur, login_url='courses:login')
def admin_lecon_add(request, module_id):
    module = get_object_or_404(Module, id=module_id)
    if request.method == 'POST':
        Lecon.objects.create(
            module=module,
            titre=request.POST.get('titre', '').strip(),
            contenu=request.POST.get('contenu', '').strip(),
            video_url=request.POST.get('video_url', '').strip() or None,
            lien_externe=request.POST.get('lien_externe', '').strip() or None,
            duree_minutes=request.POST.get('duree_minutes', 0),
            ordre=request.POST.get('ordre', 0),
        )
        messages.success(request, 'Leçon ajoutée.')
    return redirect('courses:admin_formation_form', formation_id=module.formation.id)


@user_passes_test(is_formateur, login_url='courses:login')
def admin_examen_form(request, formation_id, examen_id=None):
    formation = get_object_or_404(Formation, id=formation_id)
    if examen_id:
        examen = get_object_or_404(Examen, id=examen_id, formation=formation)
    else:
        examen = None

    if request.method == 'POST':
        form = ExamenForm(request.POST, instance=examen)
        if form.is_valid():
            e = form.save(commit=False)
            e.formation = formation
            e.save()

            # Gestion des questions
            question_ids = request.POST.getlist('question_id')
            question_textes = request.POST.getlist('question_texte')
            for i, (q_id, q_text) in enumerate(zip(question_ids, question_textes)):
                if not q_text.strip():
                    continue
                if q_id:
                    q = Question.objects.get(id=q_id)
                    q.texte = q_text.strip()
                    q.ordre = i
                    q.save()
                else:
                    q = Question.objects.create(examen=e, texte=q_text.strip(), ordre=i)

                # Options pour chaque question
                option_ids = request.POST.getlist(f'option_id_{q.id}')
                option_textes = request.POST.getlist(f'option_texte_{q.id}')
                option_correctes = request.POST.getlist(f'option_correcte_{q.id}')
                for o_id, o_text, o_corr in zip(option_ids, option_textes, option_correctes):
                    if not o_text.strip():
                        continue
                    if o_id:
                        opt = OptionReponse.objects.get(id=o_id)
                        opt.texte = o_text.strip()
                        opt.est_correcte = o_corr == 'on'
                        opt.save()
                    else:
                        OptionReponse.objects.create(
                            question=q, texte=o_text.strip(), est_correcte=(o_corr == 'on')
                        )

            messages.success(request, f'Examen "{e.titre}" enregistré avec succès.')
            return redirect('courses:admin_formation_form', formation_id=formation.id)
    else:
        form = ExamenForm(instance=examen)

    questions = examen.questions.prefetch_related('options').all() if examen else []
    return render(request, 'courses/admin_examen_form.html', {
        'form': form,
        'formation': formation,
        'examen': examen,
        'questions': questions,
    })


@user_passes_test(is_formateur, login_url='courses:login')
def admin_apprenants(request):
    apprenants = User.objects.filter(is_staff=False).annotate(
        nb_examens=Count('tentatives_examen', distinct=True),
        nb_formations=Count('commentaires__lecon__module__formation', distinct=True),
    ).order_by('username')
    return render(request, 'courses/admin_apprenants.html', {'apprenants': apprenants})


@user_passes_test(is_formateur, login_url='courses:login')
def admin_apprenant_detail(request, user_id):
    apprenant = get_object_or_404(User, id=user_id, is_staff=False)
    tentatives = TentativeExamen.objects.filter(etudiant=apprenant).select_related(
        'examen__formation'
    ).order_by('-date_soumission')
    commentaires = Commentaire.objects.filter(auteur=apprenant).select_related(
        'lecon__module__formation'
    ).order_by('-date_creation')[:10]
    return render(request, 'courses/admin_apprenant_detail.html', {
        'apprenant': apprenant,
        'tentatives': tentatives,
        'commentaires': commentaires,
    })


@user_passes_test(is_formateur, login_url='courses:login')
def prolonger_abonnement(request, user_id):
    """Prolonge l'abonnement d'un apprenant (formateur/admin)."""
    if request.method != 'POST':
        return redirect('courses:admin_apprenant_detail', user_id=user_id)

    apprenant = get_object_or_404(User, id=user_id, is_staff=False)
    jours = int(request.POST.get('jours', 30))
    motif = request.POST.get('motif', '').strip()

    # Récupérer ou créer l'abonnement
    abonnement, _ = Abonnement.objects.get_or_create(
        utilisateur=apprenant,
        defaults={'reseau': 'airtel', 'telephone': ''},
    )

    ancienne_date = abonnement.date_expiration
    abonnement.activer(jours=jours)

    # Enregistrer l'historique
    ProlongationAbonnement.objects.create(
        abonnement=abonnement,
        jours_ajoutes=jours,
        motif=motif,
        ancienne_date_expiration=ancienne_date,
        nouvelle_date_expiration=abonnement.date_expiration,
        effectue_par=request.user,
    )

    messages.success(
        request,
        f'Abonnement de {apprenant.username} prolongé de {jours} jours. '
        f'Expire le {abonnement.date_expiration.strftime("%d/%m/%Y")}.'
    )
    return redirect('courses:admin_apprenant_detail', user_id=user_id)


@user_passes_test(is_formateur, login_url='courses:login')
def admin_certifications(request):
    filtre = request.GET.get('filtre', 'all')
    tentatives = TentativeExamen.objects.select_related(
        'etudiant', 'examen__formation'
    ).order_by('-date_soumission')

    if filtre == 'certifie':
        tentatives = tentatives.filter(est_termine=True, note__gte=F('examen__formation__seuil_certification'))
    elif filtre == 'echec':
        tentatives = tentatives.filter(est_termine=True, note__lt=F('examen__formation__seuil_certification'))

    # Calcul statuts
    tentatives_list = []
    for t in tentatives:
        seuil = t.examen.formation.seuil_certification
        est_certifie = t.est_termine and t.note >= seuil
        tentatives_list.append({
            'tentative': t,
            'seuil': seuil,
            'est_certifie': est_certifie,
        })

    return render(request, 'courses/admin_certifications.html', {
        'tentatives_list': tentatives_list,
        'filtre': filtre,
    })



# ═══════════════════════════════════════
#  ADMIN TRANSACTIONS PAIEMENT
# ═══════════════════════════════════════
@user_passes_test(is_formateur, login_url='courses:login')
@login_required
def admin_transactions(request):
    """Liste de toutes les transactions de paiement pour l'admin/formateur."""
    filtre = request.GET.get('filtre', 'all')
    transactions = TransactionPaiement.objects.select_related(
        'abonnement', 'abonnement__utilisateur'
    ).order_by('-date_creation')

    if filtre == 'succes':
        transactions = transactions.filter(statut='reussi')
    elif filtre == 'en_attente':
        transactions = transactions.filter(statut='en_attente')
    elif filtre == 'echec':
        transactions = transactions.filter(statut='echoue')

    total = TransactionPaiement.objects.count()
    total_succes = TransactionPaiement.objects.filter(statut='reussi').count()
    total_montant = sum(
        t.montant for t in TransactionPaiement.objects.filter(statut='reussi')
    )
    abonnements_actifs = Abonnement.objects.filter(statut='actif').count()

    return render(request, 'courses/admin_transactions.html', {
        'transactions': transactions,
        'filtre': filtre,
        'total': total,
        'total_succes': total_succes,
        'total_montant': total_montant,
        'abonnements_actifs': abonnements_actifs,
    })



# ═══════════════════════════════════════
#  FORMATIONS & CONTENU
# ═══════════════════════════════════════
def liste_formations(request):
    formations = Formation.objects.all()
    user_inscriptions = []
    if request.user.is_authenticated:
        user_inscriptions = Inscription.objects.filter(etudiant=request.user).values_list('formation_id', flat=True)
    return render(request, 'courses/formation_list.html', {
        'formations': formations,
        'user_inscriptions': user_inscriptions,
    })


@login_required
def inscription_view(request, formation_id):
    formation = get_object_or_404(Formation, id=formation_id)
    inscription, created = Inscription.objects.get_or_create(
        etudiant=request.user, formation=formation
    )
    if created:
        messages.success(request, f'Vous êtes inscrit à la formation "{formation.titre}".')
    else:
        messages.info(request, f'Vous êtes déjà inscrit à "{formation.titre}".')
    return redirect('courses:video_player', formation_id=formation.id)


def formation_detail_view(request, formation_id):
    formation = get_object_or_404(Formation, id=formation_id)
    est_inscrit = False
    progression = 0
    examen_debloque = False
    est_certifie = False
    duree_examen_auto = 0

    if request.user.is_authenticated:
        est_inscrit = Inscription.objects.filter(etudiant=request.user, formation=formation).exists()
        if est_inscrit:
            total = formation.videos.count()
            vues = ProgressionLecon.objects.filter(
                etudiant=request.user, video__formation=formation, vue=True
            ).count()
            progression = round((vues / total) * 100) if total > 0 else 0

    videos = formation.videos.all()
    ressources = formation.ressources.all()
    examen = formation.examens.first()

    if examen:
        duree_examen_auto = examen.questions.count() * 2
        if request.user.is_authenticated:
            examen_debloque = progression >= 100
            est_certifie = TentativeExamen.objects.filter(
                etudiant=request.user, examen=examen, est_termine=True,
                note__gte=formation.seuil_certification
            ).exists()

    return render(request, 'courses/formation_detail.html', {
        'formation': formation,
        'est_inscrit': est_inscrit,
        'progression': progression,
        'examen_debloque': examen_debloque,
        'est_certifie': est_certifie,
        'duree_examen_auto': duree_examen_auto,
        'videos': videos,
        'ressources': ressources,
        'examen': examen,
    })


@login_required
def video_player_view(request, formation_id):
    formation = get_object_or_404(Formation, id=formation_id)
    # Vérifier inscription
    if not Inscription.objects.filter(etudiant=request.user, formation=formation).exists():
        messages.warning(request, 'Vous devez être inscrit pour accéder aux vidéos.')
        return redirect('courses:formation_detail', formation_id=formation.id)

    videos = formation.videos.all()
    video_id = request.GET.get('video')
    if video_id:
        video = get_object_or_404(VideoLecon, id=video_id, formation=formation)
    else:
        video = videos.first()

    # Calcul progression
    total = videos.count()
    vues = ProgressionLecon.objects.filter(
        etudiant=request.user, video__formation=formation, vue=True
    ).count()
    progression = round((vues / total) * 100) if total > 0 else 0

    # Vidéo suivante
    video_suivante = None
    if video:
        video_suivante = videos.filter(ordre__gt=video.ordre).first()

    # Vérifier si peut passer l'examen
    peut_passer_examen = progression >= 100
    examen = formation.examens.first()

    # Vérifier si l'apprenant a déjà réussi la certification
    est_certifie = False
    if examen and request.user.is_authenticated:
        est_certifie = TentativeExamen.objects.filter(
            etudiant=request.user, examen=examen, est_termine=True,
            note__gte=formation.seuil_certification
        ).exists()

    # Calcul durée examen dynamique (nb_questions × 2 min)
    duree_examen_auto = examen.questions.count() * 2 if examen else 0

    return render(request, 'courses/video_player.html', {
        'formation': formation,
        'video': video,
        'videos': videos,
        'progression': progression,
        'video_suivante': video_suivante,
        'peut_passer_examen': peut_passer_examen,
        'examen': examen,
        'est_certifie': est_certifie,
        'duree_examen_auto': duree_examen_auto,
    })


@login_required
def marquer_video_vue_view(request, video_id):
    video = get_object_or_404(VideoLecon, id=video_id)
    progression, created = ProgressionLecon.objects.get_or_create(
        etudiant=request.user, video=video,
        defaults={'vue': True, 'date_visionnage': timezone.now()}
    )
    if not progression.vue:
        progression.vue = True
        progression.date_visionnage = timezone.now()
        progression.save()

    # Rediriger vers la vidéo suivante ou le lecteur
    video_suivante = video.formation.videos.filter(ordre__gt=video.ordre).first()
    if video_suivante:
        url = reverse('courses:video_player', kwargs={'formation_id': video.formation.id}) + f'?video={video_suivante.id}'
        return redirect(url)
    return redirect('courses:video_player', formation_id=video.formation.id)


def detail_lecon(request, lecon_id):
    lecon = get_object_or_404(Lecon, id=lecon_id)
    commentaires = lecon.commentaires.all()

    if request.method == 'POST':
        form = CommentaireForm(request.POST)
        if form.is_valid():
            commentaire = form.save(commit=False)
            commentaire.lecon = lecon
            commentaire.auteur = request.user
            commentaire.save()
            messages.success(request, 'Votre commentaire a été ajouté.')
            return redirect('courses:detail_lecon', lecon_id=lecon.id)
    else:
        form = CommentaireForm()

    return render(request, 'courses/detail_lecon.html', {
        'lecon': lecon,
        'commentaires': commentaires,
        'form': form,
    })


@login_required
def passer_examen(request, examen_id):
    examen = get_object_or_404(Examen, id=examen_id)
    formation = examen.formation
    questions = examen.questions.prefetch_related('options').all()

    # ── Durée dynamique : nb_questions × 2 minutes ──
    nb_questions = questions.count()
    duree_auto_minutes = nb_questions * 2

    # Vérifier progression 100%
    total = formation.videos.count()
    vues = ProgressionLecon.objects.filter(
        etudiant=request.user, video__formation=formation, vue=True
    ).count()
    progression = round((vues / total) * 100) if total > 0 else 0

    if progression < 100 and total > 0:
        messages.warning(request, f'Vous devez terminer la formation ({progression}%) avant de passer l\'examen.')
        return redirect('courses:video_player', formation_id=formation.id)

    if request.method == 'POST':
        resultats = evaluer_examen(request.user, examen, request.POST)
        if resultats['est_certifie']:
            msg = (
                f"🎉 Note : {resultats['pourcentage']}% — Félicitations, vous êtes certifié !\n"
                f"Votre certificat est disponible dans vos certifications."
            )
        else:
            msg = (
                f"Note : {resultats['pourcentage']}% — Non certifié. "
                f"(Seuil : {formation.seuil_certification}%) — Vous pouvez repasser l'examen."
            )
        messages.success(request, msg)
        return redirect('courses:mes_certifications')

    return render(request, 'courses/examen_detail.html', {
        'examen': examen,
        'questions': questions,
        'progression': progression,
        'duree_auto_minutes': duree_auto_minutes,
        'nb_questions': nb_questions,
    })
