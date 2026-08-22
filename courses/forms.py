from django import forms
from .models import Formation, Lecon, Commentaire, Examen, VideoLecon, RessourceComplementaire


class FormationForm(forms.ModelForm):
    class Meta:
        model = Formation
        fields = ['titre', 'domaine', 'description', 'image', 'seuil_certification']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre de la formation'}),
            'domaine': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Description'}),
            'seuil_certification': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
        }


class VideoLeconForm(forms.ModelForm):
    class Meta:
        model = VideoLecon
        fields = ['titre', 'fichier_video', 'video_url']


class RessourceForm(forms.ModelForm):
    class Meta:
        model = RessourceComplementaire
        fields = ['titre', 'type_ressource', 'fichier', 'lien_web']


class LeconForm(forms.ModelForm):
    class Meta:
        model = Lecon
        fields = ['module', 'titre', 'contenu', 'video_url', 'fichier_pdf', 'lien_externe', 'duree_minutes', 'ordre']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre de la leçon'}),
            'contenu': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Contenu de la leçon'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'lien_externe': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'duree_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'ordre': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class CommentaireForm(forms.ModelForm):
    class Meta:
        model = Commentaire
        fields = ['texte']
        widgets = {
            'texte': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Votre commentaire...'}),
        }


class ExamenForm(forms.ModelForm):
    class Meta:
        model = Examen
        fields = ['formation', 'titre', 'description', 'duree_minutes', 'note_minimale']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Titre de l'examen"}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Description'}),
            'duree_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'note_minimale': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
        }
