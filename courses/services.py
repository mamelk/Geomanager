import os
import io
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
from .models import Question, OptionReponse, TentativeExamen

FORMATEUR_NOM = "Delphin BAZIBUHE"


def evaluer_examen(etudiant, examen, reponses_soumises):
    """
    Évalue les réponses soumises pour un examen et enregistre la tentative.
    Si la note >= seuil, génère un certificat PDF.

    Returns:
        dict contenant note, pourcentage, est_certifie, tentative, certificat_pdf_bytes
    """
    questions = examen.questions.all()
    total = questions.count()

    if total == 0:
        note = Decimal('0.00')
        pourcentage = Decimal('0.00')
    else:
        bonnes_reponses = 0
        for question in questions:
            # Le formulaire envoie "question_<id>" comme clé
            cle = f'question_{question.id}'
            option_id_selectionnee = reponses_soumises.get(cle)
            if option_id_selectionnee:
                try:
                    option = OptionReponse.objects.get(
                        id=int(option_id_selectionnee),
                        question=question,
                    )
                    if option.est_correcte:
                        bonnes_reponses += 1
                except (OptionReponse.DoesNotExist, ValueError):
                    pass

        pourcentage = Decimal(str(round((bonnes_reponses / total) * 100, 2)))
        note = pourcentage

    est_certifie = pourcentage >= examen.formation.seuil_certification

    tentative = TentativeExamen.objects.create(
        examen=examen,
        etudiant=etudiant,
        note=pourcentage,
        date_soumission=timezone.now(),
        est_termine=True,
    )

    # Générer un numéro de certificat unique si certifié
    if est_certifie:
        tentative.numero_certificat = tentative.generer_numero_certificat()
        tentative.save(update_fields=['numero_certificat'])

    resultats = {
        'note': note,
        'pourcentage': pourcentage,
        'total_questions': total,
        'est_certifie': est_certifie,
        'seuil_certification': examen.formation.seuil_certification,
        'tentative': tentative,
        'certificat_pdf_bytes': None,
    }

    # Générer le certificat PDF si certifié
    if est_certifie:
        pdf_bytes = generer_certificat_pdf(etudiant, examen.formation, tentative)
        resultats['certificat_pdf_bytes'] = pdf_bytes

    return resultats


def generer_certificat_pdf(etudiant, formation, tentative):
    """
    Génère un certificat PDF haute définition (A4 paysage) via ReportLab.
    Chart Graphique GeoManager : teal #1a3a4a / #2a5e78 + copper #c88e6e / #9e5e3e
    Inclut : logo GM, nom étudiant, formation, durée, date, signature, mention ESTECH.
    """
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import cm, mm
        from reportlab.lib.colors import HexColor, white
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    except ImportError:
        return None

    try:
        from io import BytesIO

        # ── Palette GeoManager ──
        TEAL       = HexColor('#1a3a4a')
        TEAL_LIGHT = HexColor('#2a5e78')
        COPPER     = HexColor('#c88e6e')
        COPPER_DK  = HexColor('#9e5e3e')
        SLATE_700  = HexColor('#334155')
        SLATE_500  = HexColor('#64748B')
        SLATE_300  = HexColor('#CBD5E1')
        WHITE      = HexColor('#FFFFFF')

        # ── Sécuriser les valeurs ──
        nom_complet = str(etudiant.get_full_name() or etudiant.username or 'Apprenant').upper().strip()
        titre_formation = str(getattr(formation, 'titre', 'Formation') or 'Formation')
        note_val = float(getattr(tentative, 'note', 0) or 0)
        date_str = tentative.date_soumission.strftime('%d/%m/%Y') if tentative.date_soumission else timezone.now().strftime('%d/%m/%Y')
        mention = "Excellent" if note_val >= 90 else "Bien" if note_val >= 70 else "Satisfaisant"
        duree_str = formation.duree_totale_formatee if hasattr(formation, 'duree_totale_formatee') else ''
        numero_cert = tentative.numero_certificat or f"GM-{tentative.id:04d}"

        filename = f"certificat_{etudiant.username}_{formation.id}_{tentative.id}.pdf"

        # ── Dimensions A4 Paysage ──
        w, h = landscape(A4)
        # Utiliser BytesIO pour compatibilité serverless (Vercel)
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(A4))
        c.setTitle(f"Certificat Géomanager — {titre_formation}")

        # ══════════════════════════════════════════════════════════
        # FOND & CADRE
        # ══════════════════════════════════════════════════════════
        c.setFillColor(WHITE)
        c.rect(0, 0, w, h, fill=True, stroke=False)

        # Bande latérale gauche teal
        c.setFillColor(TEAL)
        c.rect(0, 0, 12, h, fill=True, stroke=False)

        # Cadre extérieur teal
        c.setStrokeColor(TEAL)
        c.setLineWidth(2.5)
        c.rect(18, 18, w - 36, h - 36, fill=False, stroke=True)

        # Cadre intérieur copper
        c.setStrokeColor(COPPER)
        c.setLineWidth(1)
        c.rect(24, 24, w - 48, h - 48, fill=False, stroke=True)

        # Coins décoratifs copper
        c.setFillColor(COPPER)
        for cx, cy in [(24, h - 34), (w - 34, h - 34), (24, 24), (w - 34, 24)]:
            c.rect(cx, cy, 10, 10, fill=True, stroke=False)

        # ══════════════════════════════════════════════════════════
        # EN-TÊTE : LOGO GM + TEXTE
        # ══════════════════════════════════════════════════════════
        logo_x, logo_y = 60, h - 90

        # Cercle logo GM
        c.setFillColor(TEAL)
        c.circle(logo_x, logo_y + 15, 28, fill=True, stroke=False)
        c.setFillColor(COPPER)
        c.circle(logo_x, logo_y + 15, 24, fill=True, stroke=False)
        c.setFillColor(TEAL)
        c.circle(logo_x, logo_y + 15, 20, fill=True, stroke=False)

        # Texte GM dans le logo
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(logo_x - 1, logo_y + 9, "GM")

        # Texte GEOMANAGER à côté du logo
        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(logo_x + 38, logo_y + 18, "Geo")
        c.setFillColor(COPPER)
        c.drawString(logo_x + 75, logo_y + 18, "Manager")

        # Sous-titre
        c.setFillColor(SLATE_500)
        c.setFont("Helvetica", 9)
        c.drawString(logo_x + 38, logo_y + 3, "MINING ENGINEERING E-LEARNING PLATFORM")

        # Numéro de certificat (droite)
        c.setFillColor(SLATE_500)
        c.setFont("Helvetica", 8)
        c.drawRightString(w - 50, h - 60, f"N° {numero_cert}")
        c.drawRightString(w - 50, h - 72, f"Délivré le {date_str}")

        # Ligne séparatrice
        c.setStrokeColor(COPPER)
        c.setLineWidth(1.5)
        c.line(50, h - 100, w - 50, h - 100)
        c.setStrokeColor(TEAL_LIGHT)
        c.setLineWidth(0.5)
        c.line(50, h - 103, w - 50, h - 103)

        # ══════════════════════════════════════════════════════════
        # TITRE DU CERTIFICAT
        # ══════════════════════════════════════════════════════════
        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(w / 2, h - 145, "CERTIFICAT DE REUSSITE")

        c.setFillColor(SLATE_500)
        c.setFont("Helvetica", 11)
        c.drawCentredString(w / 2, h - 170, "Le présent certificat est officiellement décerné à :")

        # ══════════════════════════════════════════════════════════
        # NOM DE L'APPRENANT
        # ══════════════════════════════════════════════════════════
        font_size_nom = 24
        if len(nom_complet) > 35:
            font_size_nom = 16
        elif len(nom_complet) > 25:
            font_size_nom = 20

        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", font_size_nom)
        c.drawCentredString(w / 2, h - 210, nom_complet)

        # Ligne sous le nom
        c.setStrokeColor(COPPER)
        c.setLineWidth(2)
        c.line(w / 2 - 180, h - 222, w / 2 + 180, h - 222)

        # ══════════════════════════════════════════════════════════
        # FORMATION
        # ══════════════════════════════════════════════════════════
        c.setFillColor(SLATE_500)
        c.setFont("Helvetica", 11)
        c.drawCentredString(w / 2, h - 250, "Pour avoir accompli avec succès la formation spécialisée :")

        # Titre formation avec Paragraph pour retour auto
        styles = getSampleStyleSheet()
        fs_titre = 16 if len(titre_formation) < 50 else 13
        style_titre = ParagraphStyle(
            'TitreF', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=fs_titre, leading=fs_titre + 4,
            textColor=TEAL, alignment=TA_CENTER,
        )
        p_titre = Paragraph(f"&laquo; {titre_formation} &raquo;", style_titre)
        w_p, h_p = p_titre.wrap(620, 60)
        p_titre.drawOn(c, (w - w_p) / 2, h - 290 - (h_p / 2))

        # Score adaptatif
        score_y = h - 290 - h_p - 25

        # ══════════════════════════════════════════════════════════
        # SCORE, DURÉE & MENTION
        # ══════════════════════════════════════════════════════════
        # Badge score
        badge_y = score_y - 5
        c.setFillColor(HexColor('#ECFDF5'))  # emerald-50
        badge_text = f"  Score : {note_val:.1f}%  |  Mention : {mention}  "
        tw = c.stringWidth(badge_text, 'Helvetica-Bold', 11)
        badge_x = (w - tw - 20) / 2
        c.roundRect(badge_x, badge_y - 5, tw + 20, 22, 6, fill=True, stroke=False)
        c.setFillColor(HexColor('#047857'))
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(w / 2, badge_y, badge_text)

        # Durée
        if duree_str:
            c.setFillColor(SLATE_500)
            c.setFont("Helvetica", 9)
            c.drawCentredString(w / 2, badge_y - 22, f"Durée totale de la formation : {duree_str}")

        # ══════════════════════════════════════════════════════════
        # PIED DE PAGE : SIGNATURES & ESTECH
        # ══════════════════════════════════════════════════════════
        footer_y = 80

        # --- Date (gauche) ---
        c.setFillColor(SLATE_700)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(60, footer_y + 30, "Délivré le")
        c.setFont("Helvetica", 10)
        c.drawString(60, footer_y + 14, date_str)
        c.setStrokeColor(SLATE_300)
        c.setLineWidth(0.8)
        c.line(60, footer_y + 8, 180, footer_y + 8)

        # --- Cachet plateforme (centre) ---
        c.setFillColor(TEAL)
        c.circle(w / 2, footer_y + 18, 20, fill=True, stroke=False)
        c.setFillColor(COPPER)
        c.circle(w / 2, footer_y + 18, 16, fill=True, stroke=False)
        c.setFillColor(TEAL)
        c.circle(w / 2, footer_y + 18, 12, fill=True, stroke=False)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(w / 2, footer_y + 14, "GM")
        c.setFillColor(SLATE_500)
        c.setFont("Helvetica", 7)
        c.drawCentredString(w / 2, footer_y - 5, "Géomanager")
        c.setFont("Helvetica-Oblique", 6)
        c.drawCentredString(w / 2, footer_y - 14, "Certifié authentique")

        # --- Signature formateur (droite) ---
        c.setStrokeColor(SLATE_300)
        c.setLineWidth(0.8)
        c.line(w - 260, footer_y + 38, w - 60, footer_y + 38)
        c.setFillColor(SLATE_700)
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(w - 60, footer_y + 22, "Le Formateur Principal")
        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(w - 60, footer_y + 6, FORMATEUR_NOM)
        c.setFillColor(SLATE_500)
        c.setFont("Helvetica-Oblique", 8)
        c.drawRightString(w - 60, footer_y - 8, "Expert en Ingénierie Minière")

        # ══════════════════════════════════════════════════════════
        # BANDEAU INFÉRIEUR : DÉVELOPPÉ PAR ESTECH
        # ══════════════════════════════════════════════════════════
        c.setFillColor(TEAL)
        c.rect(0, 0, w, 30, fill=True, stroke=False)
        c.setFillColor(WHITE)
        c.setFont("Helvetica", 7)
        c.drawCentredString(w / 2, 11, "Développé par ESTECH  •  www.estech.cd  •  Plateforme Géomanager")

        # ══════════════════════════════════════════════════════════
        # FINALISER
        # ══════════════════════════════════════════════════════════
        c.showPage()
        c.save()
        buffer.seek(0)
        pdf_bytes = buffer.read()
        buffer.close()

        # Tenter de sauvegarder sur disque (optionnel, échoue gracieusement en serverless)
        try:
            cert_dir = os.path.join(settings.MEDIA_ROOT, 'certificats')
            os.makedirs(cert_dir, exist_ok=True)
            filepath = os.path.join(cert_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(pdf_bytes)
        except OSError:
            pass  # Serverless : pas d'écriture disque possible

        # Retourner les bytes du PDF pour compatibilité serverless
        return pdf_bytes

    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f'Erreur generation certificat PDF: {e}')
        logger.error(traceback.format_exc())
        return None
