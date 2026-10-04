from .models import AuditLog


def zapsat(kdo, akce: str, objekt: str, objekt_id: int, zmeny=None, duvod: str = "", poznamka=""):
    """Zapíše záznam do auditního logu (kdo, kdy, co a proč)."""
    return AuditLog.objects.create(
        kdo=kdo if kdo and kdo.is_authenticated else None,
        akce=akce,
        objekt=objekt,
        objekt_id=objekt_id,
        zmeny=zmeny or {},
        duvod=duvod,
        poznamka=poznamka[:300],
    )
