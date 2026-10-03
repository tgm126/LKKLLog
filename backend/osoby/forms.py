from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import Osoba


class OsobaCreationForm(AdminUserCreationForm):
    """Založení osoby v administraci. Heslo lze vypnout (osoba bez přihlášení)."""

    class Meta:
        model = Osoba
        fields = ("jmeno", "prijmeni", "email")

    def clean_email(self):
        # Prázdný e-mail ukládáme jako NULL, aby nekolidoval s unikátností.
        return self.cleaned_data.get("email") or None


class OsobaChangeForm(UserChangeForm):
    class Meta:
        model = Osoba
        fields = ("jmeno", "prijmeni", "email")

    def clean_email(self):
        return self.cleaned_data.get("email") or None
