from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import LoginForm, UsuarioCreateForm, UsuarioUpdateForm
from .models import Usuario
from .permissions import GerenciaUsuariosRequiredMixin


class LoginOTOView(LoginView):
    template_name = "acesso/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


def logout_view(request):
    logout(request)
    messages.info(request, "Sessão encerrada.")
    return redirect("acesso:login")


class UsuarioListView(GerenciaUsuariosRequiredMixin, ListView):
    model = Usuario
    template_name = "acesso/usuario_lista.html"
    context_object_name = "usuarios"


class UsuarioCreateView(GerenciaUsuariosRequiredMixin, CreateView):
    model = Usuario
    form_class = UsuarioCreateForm
    template_name = "acesso/usuario_form.html"
    success_url = reverse_lazy("acesso:usuario_lista")

    def form_valid(self, form):
        messages.success(self.request, "Usuário criado com sucesso.")
        return super().form_valid(form)


class UsuarioUpdateView(GerenciaUsuariosRequiredMixin, UpdateView):
    model = Usuario
    form_class = UsuarioUpdateForm
    template_name = "acesso/usuario_form.html"
    success_url = reverse_lazy("acesso:usuario_lista")

    def form_valid(self, form):
        messages.success(self.request, "Usuário atualizado com sucesso.")
        return super().form_valid(form)
