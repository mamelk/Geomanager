from django.contrib import admin
from .models import (
    Formation, Module, Lecon, Examen, Question, OptionReponse,
    TentativeExamen, Inscription, ProgressionLecon,
    VideoLecon, RessourceComplementaire, Commentaire,
    Abonnement, TransactionPaiement, ProlongationAbonnement,
    ParametrePlateforme,
)


@admin.register(Formation)
class FormationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'domaine', 'instructeur', 'date_creation')
    list_filter = ('domaine',)
    search_fields = ('titre',)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('titre', 'formation', 'ordre')
    list_filter = ('formation',)


@admin.register(Lecon)
class LeconAdmin(admin.ModelAdmin):
    list_display = ('titre', 'module', 'duree_minutes', 'ordre')


@admin.register(VideoLecon)
class VideoLeconAdmin(admin.ModelAdmin):
    list_display = ('titre', 'formation', 'duree_minutes', 'ordre')


@admin.register(RessourceComplementaire)
class RessourceAdmin(admin.ModelAdmin):
    list_display = ('titre', 'formation', 'type_ressource')


@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = ('titre', 'formation', 'duree_minutes', 'note_minimale')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('texte', 'examen', 'ordre')


@admin.register(OptionReponse)
class OptionReponseAdmin(admin.ModelAdmin):
    list_display = ('texte', 'question', 'est_correcte')


@admin.register(TentativeExamen)
class TentativeExamenAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'examen', 'note', 'est_termine', 'date_soumission', 'numero_certificat')
    list_filter = ('est_termine',)
    search_fields = ('etudiant__username', 'numero_certificat')


@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'formation', 'date_inscription', 'terminee')


@admin.register(ProgressionLecon)
class ProgressionLeconAdmin(admin.ModelAdmin):
    list_display = ('etudiant', 'video', 'vue', 'date_visionnage')


@admin.register(Commentaire)
class CommentaireAdmin(admin.ModelAdmin):
    list_display = ('auteur', 'lecon', 'date_creation')
    search_fields = ('auteur__username', 'texte')


# ═══════════════════════════════════════
#  ABONNEMENTS & PAIEMENTS
# ═══════════════════════════════════════

@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'statut', 'reseau', 'telephone', 'date_expiration', 'montant')
    list_filter = ('statut', 'reseau')
    search_fields = ('utilisateur__username', 'telephone')
    readonly_fields = ('date_creation', 'date_modification')


@admin.register(TransactionPaiement)
class TransactionPaiementAdmin(admin.ModelAdmin):
    list_display = ('reference_externe', 'abonnement', 'montant', 'devise', 'telephone', 'reseau', 'statut', 'date_creation')
    list_filter = ('statut', 'reseau', 'devise')
    search_fields = ('reference_externe', 'telephone', 'abonnement__utilisateur__username')
    readonly_fields = ('date_creation', 'date_mise_a_jour', 'metadata_reponse')
    list_per_page = 50


@admin.register(ProlongationAbonnement)
class ProlongationAbonnementAdmin(admin.ModelAdmin):
    list_display = ('abonnement', 'jours_ajoutes', 'motif', 'effectue_par', 'date_prolongation')
    list_filter = ('jours_ajoutes',)
    search_fields = ('abonnement__utilisateur__username', 'motif')
    readonly_fields = ('date_prolongation',)


@admin.register(ParametrePlateforme)
class ParametrePlateformeAdmin(admin.ModelAdmin):
    list_display = ('monnaie', 'montant_abonnement', 'duree_abonnement_jours')
    readonly_fields = ('date_modification',)

    def has_add_permission(self, request):
        # Singleton : empêcher la création multiples
        return not ParametrePlateforme.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
