from django.urls import path
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'courses'

urlpatterns = [
    # Page d'accueil
    path('', views.home, name='home'),

    # Authentification
    path('connexion/', views.login_view, name='login'),
    path('deconnexion/', views.logout_view, name='logout'),
    path('inscription/', views.register_view, name='register'),
    path('profil/', views.profile_view, name='profile'),

    # Réinitialisation du mot de passe
    path('mot-de-passe-oublie/', auth_views.PasswordResetView.as_view(
        template_name='courses/password_reset_form.html',
        email_template_name='courses/password_reset_email.html',
        success_url=reverse_lazy('courses:password_reset_done'),
    ), name='password_reset'),
    path('mot-de-passe-envoye/', auth_views.PasswordResetDoneView.as_view(
        template_name='courses/password_reset_done.html',
    ), name='password_reset_done'),
    path('reinitialiser/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='courses/password_reset_confirm.html',
        success_url=reverse_lazy('courses:password_reset_complete'),
    ), name='password_reset_confirm'),
    path('mot-de-passe-reinitialise/', auth_views.PasswordResetCompleteView.as_view(
        template_name='courses/password_reset_complete.html',
    ), name='password_reset_complete'),
    path('conditions-utilisation/', views.terms_view, name='terms'),
    path('a-propos/', views.a_propos_view, name='a_propos'),

    # ══ PUBLIC ══
    path('verification/', views.verifier_certificat_view, name='verifier_certificat'),

    # ══ PAIEMENT ══
    path('paiement/', views.page_paiement, name='page_paiement'),
    path('paiement/initier/', views.initier_paiement, name='initier_paiement'),
    path('paiement/callback/', views.callback_maishapay, name='callback_maishapay'),
    path('paiement/verifier/<str:reference>/', views.verifier_statut_transaction, name='verifier_statut_transaction'),

    # ══ APPRENANT ══
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('mes-certifications/', views.mes_certifications_view, name='mes_certifications'),
    path('certificat/<int:tentative_id>/telecharger/', views.telecharger_certificat, name='telecharger_certificat'),
    path('certificat/<int:tentative_id>/visualiser/', views.visualiser_certificat, name='visualiser_certificat'),

    # ══ UPLOAD CLOUDINARY ══
    path('api/cloudinary-params/', views.cloudinary_upload_params, name='cloudinary_upload_params'),

    # ══ FORMATEUR / ADMIN ══
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-formations/', views.admin_formations, name='admin_formations'),
    path('admin-formations/ajouter/', views.admin_formation_form, name='admin_formation_add'),
    path('admin-formations/<int:formation_id>/modifier/', views.admin_formation_form, name='admin_formation_edit'),
    path('admin-formations/<int:formation_id>/supprimer/', views.admin_formation_delete, name='admin_formation_delete'),
    path('admin-formations/<int:formation_id>/module/ajouter/', views.admin_module_add, name='admin_module_add'),
    path('admin-module/<int:module_id>/lecon/ajouter/', views.admin_lecon_add, name='admin_lecon_add'),
    path('admin-formations/<int:formation_id>/examen/ajouter/', views.admin_examen_form, name='admin_examen_add'),
    path('admin-formations/<int:formation_id>/examen/<int:examen_id>/modifier/', views.admin_examen_form, name='admin_examen_edit'),
    path('admin-apprenants/', views.admin_apprenants, name='admin_apprenants'),
    path('admin-apprenants/<int:user_id>/', views.admin_apprenant_detail, name='admin_apprenant_detail'),
    path('admin-apprenants/<int:user_id>/reinitialiser-mot-de-passe/', views.admin_reset_password, name='admin_reset_password'),
    path('admin-apprenants/<int:user_id>/supprimer/', views.admin_supprimer_apprenant, name='admin_supprimer_apprenant'),
    path('admin-apprenants/<int:user_id>/prolonger/', views.prolonger_abonnement, name='prolonger_abonnement'),
    path('admin-certifications/', views.admin_certifications, name='admin_certifications'),
    path('admin-transactions/', views.admin_transactions, name='admin_transactions'),

    # ══ DEMANDES DE FORMATION ══
    path('demander-formation/', views.demander_formation, name='demander_formation'),
    path('mes-demandes/', views.mes_demandes, name='mes_demandes'),
    path('admin-demandes/', views.admin_demandes_formation, name='admin_demandes_formation'),
    path('admin-demandes/<int:demande_id>/repondre/', views.admin_repondre_demande, name='admin_repondre_demande'),

    # ══ CONTENU PUBLIC ══
    path('formations/', views.liste_formations, name='liste_formations'),
    path('formations/<int:formation_id>/', views.formation_detail_view, name='formation_detail'),
    path('formations/<int:formation_id>/inscription/', views.inscription_view, name='inscription'),
    path('formations/<int:formation_id>/cours/', views.video_player_view, name='video_player'),
    path('video/<int:video_id>/vue/', views.marquer_video_vue_view, name='marquer_video_vue'),
    path('lecon/<int:lecon_id>/', views.detail_lecon, name='detail_lecon'),
    path('examen/<int:examen_id>/', views.passer_examen, name='passer_examen'),
]
