from django import forms
from django.contrib import admin
from django.shortcuts import redirect
from django.utils.html import format_html

from .models import Nastaveni, PushOdber


class NastaveniForm(forms.ModelForm):
    displej = forms.ChoiceField(
        label="Změnit odkaz na displej",
        required=False,
        choices=[
            ("", "ponechat"),
            ("novy", "vytvořit nový odkaz (starý přestane platit)"),
            ("vypnout", "vypnout displej (odkaz přestane platit)"),
        ],
    )

    class Meta:
        model = Nastaveni
        fields = [
            "email_rezim",
            "povolene_adresy",
            "testovaci_provoz",
            "automaticka_uzaverka",
            "hlidat_licence",
        ]


@admin.register(Nastaveni)
class NastaveniAdmin(admin.ModelAdmin):
    form = NastaveniForm
    readonly_fields = ["odkaz"]
    fieldsets = [
        ("E-maily", {"fields": ["email_rezim", "povolene_adresy"]}),
        ("Provoz", {"fields": ["testovaci_provoz"]}),
        ("Uzávěrky", {"fields": ["automaticka_uzaverka"]}),
        ("Licence a rozlétanost", {"fields": ["hlidat_licence"]}),
        ("Velký displej", {"fields": ["odkaz", "displej"]}),
    ]

    @admin.display(description="Odkaz na displej")
    def odkaz(self, obj):
        if not obj.odkaz_displeje:
            return "vypnuto"
        return format_html('<a href="{0}" target="_blank">{0}</a>', obj.odkaz_displeje)

    def save_model(self, request, obj, form, change):
        volba = form.cleaned_data.get("displej")
        if volba == "novy":
            obj.novy_klic_displeje()
        elif volba == "vypnout":
            obj.displej_klic = ""
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Jediný záznam – seznam rovnou přeskočíme na jeho úpravu.
        return redirect("admin:provoz_nastaveni_change", Nastaveni.aktualni().pk)


@admin.register(PushOdber)
class PushOdberAdmin(admin.ModelAdmin):
    list_display = ["osoba", "zarizeni", "vytvoreno"]
    list_select_related = ["osoba"]
    search_fields = ["osoba__prijmeni", "osoba__jmeno"]
    fields = ["osoba", "zarizeni", "vytvoreno"]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False
