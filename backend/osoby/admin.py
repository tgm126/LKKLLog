from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import OsobaChangeForm, OsobaCreationForm
from .models import Opravneni, Osoba


class OpravneniInline(admin.TabularInline):
    model = Opravneni
    extra = 0


@admin.register(Osoba)
class OsobaAdmin(UserAdmin):
    add_form = OsobaCreationForm
    form = OsobaChangeForm
    inlines = [OpravneniInline]
    ordering = ["prijmeni", "jmeno"]
    list_display = [
        "prijmeni",
        "jmeno",
        "email",
        "role_casomeric",
        "role_ucetni",
        "is_staff",
        "externi",
        "is_active",
    ]
    list_filter = ["is_active", "externi", "role_casomeric", "role_ucetni", "is_staff"]
    search_fields = ["prijmeni", "jmeno", "email"]
    fieldsets = [
        (None, {"fields": ["jmeno", "prijmeni", "email", "password"]}),
        ("Role", {"fields": ["role_casomeric", "role_ucetni", "is_staff", "is_superuser"]}),
        ("Stav", {"fields": ["is_active", "externi", "last_login", "vytvoreno"]}),
    ]
    readonly_fields = ["last_login", "vytvoreno"]
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
