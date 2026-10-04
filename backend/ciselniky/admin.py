from django.contrib import admin

from .models import DruhPrukazu, DruhTerminu, KvalifikacePrukazu, ProvozniOpravneni, TypLetadla

# Běžně se číselníky spravují v aplikaci (menu Číselníky); tady jen pro nouzi.
for model in (TypLetadla, DruhPrukazu, KvalifikacePrukazu, ProvozniOpravneni, DruhTerminu):
    admin.site.register(model)
