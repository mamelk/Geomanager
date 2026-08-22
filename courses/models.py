import os
import logging
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class Formation(models.Model):
    DOMAINE_CHOICES = [
        ('geologie', 'Géologie & Sondage'),
        ('securite', 'Sécurité Minière & HSE'),
        ('exploitation', 'Exploitation & Cartographie'),
        ('traitement', 'Traitement du Minerai'),
        ('topographie', 'Topographie & SIG'),
        ('general', 'Général'),
    ]
    titre = models.CharField(max_length=255)
    domaine = models.CharField(max_length=50, choices=DOMAINE_CHOICES, default='general')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='formations/', blank=True, null=True)
    instructeur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='formations')
    seuil_certification = models.DecimalField(max_digits=5, decimal_places=2, default=70.00, help_text="Pourcentage minimum pour obtenir la certification")
    duree_totale_minutes = models.PositiveIntegerField(default=0, help_text="Durée totale calculée automatiquement")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.titre

    @property
    def duree_totale_secondes(self):
        """Durée totale en secondes calculée dynamiquement."""
        return self.videos.aggregate(total=models.Sum('duree_secondes'))['total'] or 0

    @property
    def duree_totale(self):
        """Durée totale en minutes calculée dynamiquement."""
        return self.duree_totale_secondes // 60 if self.duree_totale_secondes else 0

    @property
    def duree_totale_formatee(self):
        """Retourne la durée totale formatée : '2h 15min 30s' ou '45 min'."""
        total_s = self.duree_totale_secondes
        if total_s == 0:
            return "0 min"
        h = total_s // 3600
        m = (total_s % 3600) // 60
        s = total_s % 60
        parts = []
        if h > 0:
            parts.append(f"{h}h")
        if m > 0:
            parts.append(f"{m}min")
        if s > 0 and h == 0:
            parts.append(f"{s}s")
        return ' '.join(parts) if parts else '0 min'

    @property
    def nb_videos(self):
        return self.videos.count()

    @property
    def nb_inscrits(self):
        return self.inscriptions.count()

    def recalculer_duree(self):
        self.duree_totale_minutes = self.duree_totale
        self.save(update_fields=['duree_totale_minutes'])


class Module(models.Model):
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='modules')
    titre = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    ordre = models.PositiveIntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return f"{self.formation.titre} - {self.titre}"


class Lecon(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lecons')
    titre = models.CharField(max_length=255)
    contenu = models.TextField(blank=True)
    video_url = models.URLField(blank=True, null=True, help_text="URL de la vidéo de la leçon")
    fichier_pdf = models.FileField(upload_to='lecons/pdf/', blank=True, null=True)
    lien_externe = models.URLField(blank=True, null=True, help_text="Lien vers une ressource externe")
    duree_minutes = models.PositiveIntegerField(default=0)
    ordre = models.PositiveIntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return self.titre


class VideoLecon(models.Model):
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='videos')
    titre = models.CharField(max_length=255)
    fichier_video = models.FileField(upload_to='formations/videos/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True, help_text="Ou lien vidéo externe (YouTube, etc.)")
    duree_secondes = models.PositiveIntegerField(default=0, help_text="Durée en secondes (calculée automatiquement)")
    duree_minutes = models.PositiveIntegerField(default=0, help_text="Durée en minutes (calculée automatiquement)")
    ordre = models.PositiveIntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return f"{self.formation.titre} - {self.titre}"

    @property
    def duree_formatee(self):
        """Retourne la durée formatée : '04:35' ou '12:00'."""
        total = self.duree_secondes
        if total == 0:
            return f"{self.duree_minutes} min" if self.duree_minutes else "--:--"
        m = total // 60
        s = total % 60
        if m >= 60:
            h = m // 60
            m = m % 60
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def save(self, *args, **kwargs):
        # Détecter si un nouveau fichier vidéo est téléversé
        detecter_duree = False
        if self.pk:
            try:
                ancien = VideoLecon.objects.get(pk=self.pk)
                if self.fichier_video and self.fichier_video != ancien.fichier_video:
                    detecter_duree = True
                elif not self.duree_secondes and self.fichier_video:
                    detecter_duree = True
            except VideoLecon.DoesNotExist:
                if self.fichier_video:
                    detecter_duree = True
        else:
            if self.fichier_video:
                detecter_duree = True

        super().save(*args, **kwargs)

        # Calculer la durée avec moviepy
        if detecter_duree and self.fichier_video:
            self._extraire_duree_video()

    def _extraire_duree_video(self):
        """Extrait la durée du fichier vidéo avec moviepy."""
        try:
            from moviepy import VideoFileClip
            path = self.fichier_video.path
            if os.path.exists(path):
                clip = VideoFileClip(path)
                duree_s = int(clip.duration)
                clip.close()
                self.duree_secondes = duree_s
                self.duree_minutes = max(1, round(duree_s / 60))
                # Sauvegarder sans boucle infinie
                VideoLecon.objects.filter(pk=self.pk).update(
                    duree_secondes=duree_s,
                    duree_minutes=self.duree_minutes
                )
                # Recalculer la durée totale de la formation
                self.formation.recalculer_duree()
                logger.info(f'Durée détectée pour "{self.titre}": {duree_s}s ({self.duree_minutes}min)')
        except Exception as e:
            logger.warning(f'Impossible de détecter la durée de "{self.fichier_video}": {e}')


class RessourceComplementaire(models.Model):
    TYPE_CHOICES = [
        ('fichier', 'Fichier'),
        ('lien', 'Lien web'),
    ]
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='ressources')
    titre = models.CharField(max_length=255)
    type_ressource = models.CharField(max_length=10, choices=TYPE_CHOICES, default='fichier')
    fichier = models.FileField(upload_to='formations/ressources/', blank=True, null=True)
    lien_web = models.URLField(blank=True, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.formation.titre} - {self.titre}"


class Commentaire(models.Model):
    lecon = models.ForeignKey(Lecon, on_delete=models.CASCADE, related_name='commentaires')
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commentaires')
    texte = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_creation']

    def __str__(self):
        return f"Commentaire de {self.auteur.username} sur {self.lecon.titre}"


class Examen(models.Model):
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='examens')
    titre = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duree_minutes = models.PositiveIntegerField(default=60, help_text="Durée de l'examen en minutes")
    note_minimale = models.DecimalField(max_digits=5, decimal_places=2, default=50.00)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre


class Question(models.Model):
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE, related_name='questions')
    texte = models.TextField()
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return self.texte[:80]


class OptionReponse(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    texte = models.CharField(max_length=500)
    est_correcte = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.texte} ({'✓' if self.est_correcte else '✗'})"


class TentativeExamen(models.Model):
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE, related_name='tentatives')
    etudiant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tentatives_examen')
    note = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    date_debut = models.DateTimeField(auto_now_add=True)
    date_soumission = models.DateTimeField(blank=True, null=True)
    est_termine = models.BooleanField(default=False)
    numero_certificat = models.CharField(max_length=50, unique=True, null=True, blank=True)

    def generer_numero_certificat(self):
        """Génère un numéro unique de type GEO-AAAA-XXXX."""
        import uuid
        from django.utils import timezone
        annee = timezone.now().strftime('%Y')
        suffixe = uuid.uuid4().hex[:4].upper()
        return f"GEO-{annee}-{suffixe}"

    def __str__(self):
        return f"{self.etudiant.username} - {self.examen.titre} ({self.note}/100)"


class Inscription(models.Model):
    etudiant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inscriptions')
    formation = models.ForeignKey(Formation, on_delete=models.CASCADE, related_name='inscriptions')
    date_inscription = models.DateTimeField(auto_now_add=True)
    terminee = models.BooleanField(default=False)

    class Meta:
        unique_together = ('etudiant', 'formation')

    def __str__(self):
        return f"{self.etudiant.username} inscrit à {self.formation.titre}"


class ProgressionLecon(models.Model):
    etudiant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progressions')
    video = models.ForeignKey(VideoLecon, on_delete=models.CASCADE, related_name='progressions')
    vue = models.BooleanField(default=False)
    date_visionnage = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('etudiant', 'video')

    def __str__(self):
        return f"{self.etudiant.username} - {self.video.titre} ({'✓' if self.vue else '✗'})"


# ═══════════════════════════════════════
#  ABONNEMENTS & PAIEMENTS
# ═══════════════════════════════════════

class Abonnement(models.Model):
    STATUT_CHOICES = [        ('actif', 'Actif'),
        ('expire', 'Expiré'),
        ('inactif', 'Inactif'),
    ]
    RESEAU_CHOICES = [
        ('airtel', 'Airtel Money'),
        ('vodacom', 'Vodacom M-Pesa'),
        ('orange', 'Orange Money'),
        ('africell', 'Africell Money'),
    ]

    utilisateur = models.OneToOneField(User, on_delete=models.CASCADE, related_name='abonnement')
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='inactif')
    date_debut = models.DateTimeField(null=True, blank=True)
    date_expiration = models.DateTimeField(null=True, blank=True)
    reseau = models.CharField(max_length=20, choices=RESEAU_CHOICES, default='airtel')
    telephone = models.CharField(max_length=20, blank=True, default='')
    montant = models.DecimalField(max_digits=10, decimal_places=2, default=10000)
    devise = models.CharField(max_length=10, default='CDF')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Abonnement'
        verbose_name_plural = 'Abonnements'

    def __str__(self):
        return f"{self.utilisateur.username} — {self.statut} (expire: {self.date_expiration})"

    @property
    def est_actif(self):
        """Vérifie si l'abonnement est actif et non expiré."""
        if self.statut != 'actif':
            return False
        if self.date_expiration is None:
            return False
        return timezone.now() <= self.date_expiration

    def activer(self, jours=30):
        """Active l'abonnement pour N jours à partir de maintenant."""
        now = timezone.now()
        if self.date_expiration and self.date_expiration > now:
            # Prolonger depuis la date d'expiration existante
            from datetime import timedelta
            self.date_expiration += timedelta(days=jours)
        else:
            from datetime import timedelta
            self.date_expiration = now + timedelta(days=jours)
        self.date_debut = self.date_debut or now
        self.statut = 'actif'
        self.save(update_fields=['statut', 'date_debut', 'date_expiration', 'date_modification'])

    def desactiver(self):
        self.statut = 'inactif'
        self.save(update_fields=['statut', 'date_modification'])


class TransactionPaiement(models.Model):
    STATUT_TX_CHOICES = [
        ('en_attente', 'En attente'),
        ('reussi', 'Réussi'),
        ('echoue', 'Échoué'),
        ('annule', 'Annulé'),
    ]

    abonnement = models.ForeignKey(Abonnement, on_delete=models.CASCADE, related_name='transactions')
    reference_externe = models.CharField(max_length=100, unique=True, help_text='ID transaction MaishaPay')
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    devise = models.CharField(max_length=10, default='CDF')
    telephone = models.CharField(max_length=20, help_text='Numéro Mobile Money du payeur')
    reseau = models.CharField(max_length=20, default='airtel')
    statut = models.CharField(max_length=15, choices=STATUT_TX_CHOICES, default='en_attente')
    metadata_reponse = models.JSONField(default=dict, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Transaction de paiement'
        verbose_name_plural = 'Transactions de paiement'
        ordering = ['-date_creation']

    def __str__(self):
        return f"TX#{self.id} — {self.reference_externe} — {self.statut} — {self.montant} {self.devise}"

    def marquer_reussi(self, reponse=None):
        self.statut = 'reussi'
        if reponse:
            self.metadata_reponse = reponse
        self.save(update_fields=['statut', 'metadata_reponse', 'date_mise_a_jour'])
        # Activer l'abonnement
        self.abonnement.activer(jours=30)

    def marquer_echoue(self, reponse=None):
        self.statut = 'echoue'
        if reponse:
            self.metadata_reponse = reponse
        self.save(update_fields=['statut', 'metadata_reponse', 'date_mise_a_jour'])


class ProlongationAbonnement(models.Model):
    """Historique des prolongations d'abonnement par un formateur/admin."""
    abonnement = models.ForeignKey(Abonnement, on_delete=models.CASCADE, related_name='prolongations')
    jours_ajoutes = models.PositiveIntegerField(default=30)
    motif = models.CharField(max_length=255, blank=True, default='')
    ancienne_date_expiration = models.DateTimeField(null=True, blank=True)
    nouvelle_date_expiration = models.DateTimeField(null=True, blank=True)
    effectue_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='prolongations_effectuees')
    date_prolongation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Prolongation d\'abonnement'
        verbose_name_plural = 'Prolongations d\'abonnement'
        ordering = ['-date_prolongation']

    def __str__(self):
        return f"Prolongation +{self.jours_ajoutes}j pour {self.abonnement.utilisateur.username} par {self.effectue_par}"


class ParametrePlateforme(models.Model):
    """Paramètres configurables de la plateforme (singleton)."""
    monnaie = models.CharField(
        max_length=3,
        choices=[('CDF', 'Franc congolais (CDF)'), ('USD', 'Dollar américain (USD)')],
        default='CDF',
    )
    montant_abonnement = models.DecimalField(
        max_digits=10, decimal_places=2, default=10000,
        help_text='Montant de l\'abonnement mensuel',
    )
    duree_abonnement_jours = models.PositiveIntegerField(default=30)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Paramètre de la plateforme'
        verbose_name_plural = 'Paramètres de la plateforme'

    def __str__(self):
        return f"{self.montant_abonnement} {self.monnaie} / {self.duree_abonnement_jours}j"

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

