"""Tests de non-régression sécurité : paiement, privilèges, uploads, redirections."""
import hashlib
import hmac
import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from . import views
from .models import Abonnement, Formation, Media, ProgressionLecon, TransactionPaiement, VideoLecon


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class SecuritePaiementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('apprenant', password='motdepasse123')
        self.formation = Formation.objects.create(titre='Géologie minière')
        self.video = VideoLecon.objects.create(formation=self.formation, titre='Leçon 1', ordre=1)
        self.abonnement = Abonnement.objects.create(utilisateur=self.user)
        self.abonnement.activer(jours=30)

    # ── 1. Mode démo ──
    def test_demo_refuse_en_production(self):
        with override_settings(DEBUG=False, MAISHAPAY_DEMO_MODE=True):
            self.assertFalse(views._paiement_demo_autorise())

    def test_demo_accepte_en_developpement(self):
        with override_settings(DEBUG=True, MAISHAPAY_DEMO_MODE=True):
            self.assertTrue(views._paiement_demo_autorise())

    @override_settings(
        DEBUG=False, MAISHAPAY_DEMO_MODE=True,
        MAISHAPAY_API_URL='', MAISHAPAY_API_KEY='', MAISHAPAY_SECRET_KEY='',
    )
    def test_paiement_sans_passerelle_n_active_rien(self):
        self.abonnement.statut = 'inactif'
        self.abonnement.date_expiration = None
        self.abonnement.save()
        self.client.force_login(self.user)
        self.client.post(reverse('courses:initier_paiement'), {'reseau': 'airtel', 'telephone': '+243900000000'})
        self.abonnement.refresh_from_db()
        self.assertFalse(self.abonnement.est_actif)
        self.assertEqual(TransactionPaiement.objects.first().statut, 'echoue')

    # ── 2. Escalade de privilèges par nom d'utilisateur ──
    def test_compte_nomme_admin_sans_droits(self):
        imposteur = User.objects.create_user('Admin', password='motdepasse123')
        self.assertFalse(views.is_formateur(imposteur))
        self.assertFalse(User.objects.filter(username__iexact='admin', is_staff=True).exists())
        staff = User.objects.create_user('formateur', password='motdepasse123', is_staff=True)
        self.assertTrue(views.is_formateur(staff))

    # ── 3. Idempotence du crédit d'abonnement ──
    def test_callback_rejoue_ne_prolonge_pas_deux_fois(self):
        tx = TransactionPaiement.objects.create(
            abonnement=self.abonnement, reference_externe='GM-TEST-1',
            montant=Decimal('10000'), devise='CDF', telephone='+243900000000',
        )
        tx.marquer_reussi({'etape': 1})
        self.abonnement.refresh_from_db()
        premiere_expiration = self.abonnement.date_expiration
        tx.marquer_reussi({'etape': 2})
        self.abonnement.refresh_from_db()
        self.assertEqual(self.abonnement.date_expiration, premiere_expiration)

    # ── 4. Callback : signature, montant, devise ──
    def _callback(self, tx, amount, devise='CDF', secret='secret-test', status='successful'):
        payload = json.dumps({
            'reference': tx.reference_externe, 'status': status,
            'amount': amount, 'currency': devise,
        }).encode()
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return self.client.post(
            reverse('courses:callback_maishapay'), data=payload,
            content_type='application/json', HTTP_X_MAISHAPAY_SIGNATURE=signature,
        )

    @override_settings(MAISHAPAY_SECRET_KEY='secret-test')
    def test_callback_montant_inferieur_rejete(self):
        tx = TransactionPaiement.objects.create(
            abonnement=self.abonnement, reference_externe='GM-TEST-2',
            montant=Decimal('10000'), devise='CDF', telephone='+243900000000',
        )
        resp = self._callback(tx, amount=1)
        tx.refresh_from_db()
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(tx.statut, 'en_attente')

    @override_settings(MAISHAPAY_SECRET_KEY='secret-test')
    def test_callback_devise_differente_rejetee(self):
        tx = TransactionPaiement.objects.create(
            abonnement=self.abonnement, reference_externe='GM-TEST-3',
            montant=Decimal('10000'), devise='CDF', telephone='+243900000000',
        )
        resp = self._callback(tx, amount=10000, devise='USD')
        tx.refresh_from_db()
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(tx.statut, 'en_attente')

    @override_settings(MAISHAPAY_SECRET_KEY='secret-test')
    def test_callback_signature_invalide_rejetee(self):
        tx = TransactionPaiement.objects.create(
            abonnement=self.abonnement, reference_externe='GM-TEST-4',
            montant=Decimal('10000'), devise='CDF', telephone='+243900000000',
        )
        resp = self._callback(tx, amount=10000, secret='mauvaise-cle')
        self.assertEqual(resp.status_code, 403)

    @override_settings(MAISHAPAY_SECRET_KEY='secret-test')
    def test_callback_valide_active_abonnement(self):
        tx = TransactionPaiement.objects.create(
            abonnement=self.abonnement, reference_externe='GM-TEST-5',
            montant=Decimal('10000'), devise='CDF', telephone='+243900000000',
        )
        resp = self._callback(tx, amount=10000)
        tx.refresh_from_db()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(tx.statut, 'reussi')

    # ── 5. Open redirect après connexion ──
    def test_next_externe_ignore(self):
        resp = self.client.post(reverse('courses:login'), {
            'username': 'apprenant', 'password': 'motdepasse123',
            'next': 'https://evil.example/vol',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('evil.example', resp['Location'])

    # ── 6. Progression sans inscription ──
    def test_progression_refusee_sans_inscription(self):
        self.client.force_login(self.user)
        self.client.get(reverse('courses:marquer_video_vue', args=[self.video.id]))
        self.assertFalse(ProgressionLecon.objects.exists())

    # ── 7. Upload : contenu non-image déguisé ──
    def test_svg_degulse_en_png_refuse(self):
        self.client.force_login(self.user)
        contenu = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        fichier = SimpleUploadedFile('photo.png', contenu, content_type='image/png')
        self.client.post(reverse('courses:media_photo_upload'), {'photo': fichier})
        self.assertFalse(Media.objects.exists())
