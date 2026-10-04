from django.contrib import admin
from django.shortcuts import redirect

from .models import Nastaveni


@admin.register(Nastaveni)
class NastaveniAdmin(admin.ModelAdmin):
    fieldsets = [
        ("E-maily", {"fields": ["email_rezim", "povolene_adresy"]}),
        ("Provoz", {"fields": ["testovaci_provoz"]}),
        ("Uzávěrky", {"fields": ["automaticka_uzaverka", "uzaverka_po_soumraku_min"]}),
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Jediný záznam – seznam rovnou přeskočíme na jeho úpravu.
        return redirect("admin:provoz_nastaveni_change", Nastaveni.aktualni().pk)
