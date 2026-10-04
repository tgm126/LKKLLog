import io

import pytest
from django.core import mail
from django.core.management import CommandError, call_command

from osoby.models import Osoba

pytestmark = pytest.mark.django_db


def test_zaloha_odejde_jen_administratorum(monkeypatch):
    Osoba.objects.create_superuser("admin@example.com", "x-Heslo-123", jmeno="A", prijmeni="B")
    Osoba.objects.create_user("pilot@example.com", jmeno="P", prijmeni="Q")
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"PGDMP-data")))
    call_command("odeslat_zalohu", nazev="lkkllog-2026-10-01.dump")
    assert len(mail.outbox) == 1
    zprava = mail.outbox[0]
    assert zprava.to == ["admin@example.com"]
    assert zprava.attachments[0][0] == "lkkllog-2026-10-01.dump"


def test_prazdny_export_neodejde(monkeypatch, db):
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"")))
    with pytest.raises(CommandError):
        call_command("odeslat_zalohu", nazev="x.dump")
