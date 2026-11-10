from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Usuario


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "campo", "autofocus": True, "placeholder": "Usuário"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "campo", "placeholder": "Senha"}
        )


class UsuarioCreateForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ["username", "first_name", "last_name", "email", "perfil", "ativo"]


class UsuarioUpdateForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ["username", "first_name", "last_name", "email", "perfil", "ativo"]
