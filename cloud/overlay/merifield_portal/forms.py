from django import forms
from .models import PlanChangeRequest, WorkspaceInvitation


class OrganizationForm(forms.Form):
    username = forms.RegexField(regex=r'^[a-zA-Z][a-zA-Z0-9_-]{2,49}$', max_length=50, label='Identifiant de l’entreprise',
        help_text='3 à 50 caractères : lettres, chiffres, tirets. Exemple : cabinet-meridien.')


class ProjectForm(forms.Form):
    name = forms.RegexField(regex=r'^[a-zA-Z0-9_.-]+$', max_length=255, label='Nom du projet', help_text='Sans espace, par exemple : parcelles-bouake.')
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, max_length=4000, label='Description')


class ChangeForm(forms.ModelForm):
    class Meta:
        model = PlanChangeRequest
        fields = ['offer', 'cycle']
        labels = {'offer': 'Formule souhaitée', 'cycle': 'Périodicité souhaitée'}


class InvitationForm(forms.ModelForm):
    class Meta:
        model = WorkspaceInvitation
        fields = ['email', 'role']
        labels = {'email': 'Adresse e-mail', 'role': 'Rôle dans l’entreprise'}
