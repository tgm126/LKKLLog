from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect

from . import ucty
from .forms import OsobaChangeForm, OsobaCreationForm
from .models import KvalifikaceOsoby, Osoba, PrukazOsoby

# Doklady, přeškolení a výcvik se zadávají na kartě osoby v aplikaci (Osoby);
# tady jsou průkazy jen pro nouzi.


class KvalifikaceOsobyInline(admin.TabularInline):
    model = KvalifikaceOsoby
    extra = 0


@admin.register(PrukazOsoby)
class PrukazOsobyAdmin(admin.ModelAdmin):
    list_display = ["osoba", "druh", "cislo", "zmeneno"]
    list_filter = ["druh"]
    search_fields = ["osoba__prijmeni", "osoba__jmeno", "cislo"]
    autocomplete_fields = ["osoba"]
    inlines = [KvalifikaceOsobyInline]


@admin.register(Osoba)
class OsobaAdmin(UserAdmin):
    add_form = OsobaCreationForm
    form = OsobaChangeForm
    ordering = ["prijmeni", "jmeno"]
    list_display = [
        "prijmeni",
        "jmeno",
        "email",
        "role_casomeric",
        "role_ucetni",
        "is_staff",
        "externi",
        "testovaci",
        "is_active",
        "pozvanka_odeslana",
    ]
    list_filter = [
        "is_active",
        "testovaci",
        "externi",
        "role_casomeric",
        "role_ucetni",
        "is_staff",
    ]
    search_fields = ["prijmeni", "jmeno", "email", "telefon"]
    fieldsets = [
        (None, {"fields": ["jmeno", "prijmeni", "email", "telefon", "password"]}),
        (
            "Role",
            {
                "fields": [
                    "role_casomeric",
                    "role_ucetni",
                    "role_spravce",
                    "is_staff",
                    "is_superuser",
                ]
            },
        ),
        (
            "Stav",
            {
                "fields": [
                    "is_active",
                    "testovaci",
                    "externi",
                    "last_login",
                    "pozvanka_odeslana",
                    "vytvoreno",
                ]
            },
        ),
    ]
    readonly_fields = ["last_login", "pozvanka_odeslana", "vytvoreno"]
    actions = ["poslat_pozvanky", "prihlasit_jako"]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": [
                    "jmeno",
                    "prijmeni",
                    "email",
                    "usable_password",
                    "password1",
                    "password2",
                ],
            },
        ),
    ]
    filter_horizontal = []

    @admin.action(description="Poslat pozvánku vybraným osobám")
    def poslat_pozvanky(self, request, queryset):
        odeslano = sum(ucty.poslat_pozvanku(osoba, kdo=request.user) for osoba in queryset)
        preskoceno = queryset.count() - odeslano
        self.message_user(request, f"Pozvánky odeslány: {odeslano}.", messages.SUCCESS)
        if preskoceno:
            self.message_user(
                request,
                f"Neodesláno: {preskoceno} (bez e-mailu, externí, neaktivní, "
                "nebo to nedovolí režim odesílání v Nastavení provozu).",
                messages.WARNING,
            )

    @admin.action(description="Přihlásit se jako vybraná osoba")
    def prihlasit_jako(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Vyberte právě jednu osobu.", messages.ERROR)
            return None
        cil = queryset.get()
        if not cil.is_active:
            self.message_user(request, "Neaktivní osoba se nemůže přihlásit.", messages.ERROR)
            return None
        ucty.prihlasit_jako(request, cil)
        return redirect("/")
