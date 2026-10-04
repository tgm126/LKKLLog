from django import forms
from django.contrib import admin, messages

from . import uzaverky
from .models import (
    AuditLog,
    Let,
    Letadlo,
    Letiste,
    Osnova,
    Posadka,
    Ucel,
    Uloha,
    Upozorneni,
    Uzaverka,
)


@admin.register(Letadlo)
class LetadloAdmin(admin.ModelAdmin):
    list_display = [
        "imatrikulace",
        "typ",
        "kategorie",
        "pocet_mist",
        "max_doba_min",
        "vlecne",
        "soukrome",
        "aktivni",
        "poradi",
    ]
    list_filter = ["kategorie", "aktivni", "soukrome", "vlecne"]
    list_editable = ["poradi"]
    search_fields = ["imatrikulace", "typ"]


@admin.register(Letiste)
class LetisteAdmin(admin.ModelAdmin):
    list_display = ["icao", "nazev", "domovske", "teren", "aktivni", "poradi"]
    list_filter = ["aktivni", "domovske", "teren"]
    list_editable = ["poradi"]
    search_fields = ["icao", "nazev"]


class UlohaForm(forms.ModelForm):
    # Účely (ArrayField) jako zaškrtávátka místo textu odděleného čárkami.
    ucely = forms.MultipleChoiceField(
        label="Účely", choices=Ucel.choices, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Uloha
        fields = ["osnova", "kod", "nazev", "ucely", "aktivni", "poradi"]


class UlohaInline(admin.TabularInline):
    model = Uloha
    form = UlohaForm
    extra = 0


@admin.register(Osnova)
class OsnovaAdmin(admin.ModelAdmin):
    inlines = [UlohaInline]
    list_display = ["nazev", "kategorie", "aktivni", "poradi"]
    list_filter = ["kategorie", "aktivni"]
    list_editable = ["poradi"]


@admin.register(Uloha)
class UlohaAdmin(admin.ModelAdmin):
    form = UlohaForm
    list_display = ["kod", "nazev", "osnova", "ucely_text", "aktivni", "poradi"]
    list_filter = ["osnova__kategorie", "osnova", "aktivni"]
    list_editable = ["poradi"]
    search_fields = ["kod", "nazev"]

    @admin.display(description="účely")
    def ucely_text(self, obj):
        return ", ".join(Ucel(u).label for u in obj.ucely)


class PosadkaInline(admin.TabularInline):
    model = Posadka
    extra = 0
    autocomplete_fields = ["osoba"]


@admin.register(Let)
class LetAdmin(admin.ModelAdmin):
    """Nouzový přístup k letům. Běžně se lety zakládají a opravují v aplikaci,
    kde se zapisují do auditního logu – změny zde se do něj (zatím) nezapisují."""

    inlines = [PosadkaInline]
    list_display = [
        "id",
        "letadlo",
        "ucel",
        "stav",
        "cas_vzletu",
        "cas_pristani",
        "doba_min",
        "platce",
        "plati_aeroklub",
    ]
    list_filter = ["stav", "ucel", "zpusob_vzletu", "letadlo__kategorie", "soukrome"]
    date_hierarchy = "cas_vzletu"
    readonly_fields = ["doba_min", "zalozeno", "zmeneno", "verze"]
    autocomplete_fields = ["platce", "zalozil", "vlecny_let"]
    search_fields = ["letadlo__imatrikulace", "posadka__osoba__prijmeni"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["kdy", "kdo", "akce", "objekt", "objekt_id", "duvod"]
    list_filter = ["akce", "objekt"]
    search_fields = ["objekt_id"]
    date_hierarchy = "kdy"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Uzaverka)
class UzaverkaAdmin(admin.ModelAdmin):
    list_display = ["typ", "obdobi", "verze", "uzavrel", "kdy", "znovu_otevreno"]
    list_filter = ["typ", ("znovu_otevreno", admin.EmptyFieldListFilter)]
    actions = ["znovu_otevrit"]

    @admin.action(description="Znovu otevřít vybraná období (verze zůstanou v historii)")
    def znovu_otevrit(self, request, queryset):
        obdobi = set(queryset.values_list("typ", "obdobi"))
        pocet = sum(bool(uzaverky.znovu_otevrit(t, o, request.user)) for t, o in obdobi)
        self.message_user(request, f"Znovu otevřeno období: {pocet}.", messages.SUCCESS)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Upozorneni)
class UpozorneniAdmin(admin.ModelAdmin):
    list_display = ["kdy", "let", "druh", "prijemci"]
    list_filter = ["druh"]
    list_select_related = ["let__letadlo"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
