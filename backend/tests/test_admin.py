import pytest

from osoby.models import Osoba

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(client):
    admin = Osoba.objects.create_superuser(
        "admin@example.com", "tajne-heslo-123", jmeno="Ad", prijmeni="Min"
    )
    client.force_login(admin)
    return client


def test_admin_zalozi_osobu_bez_prihlaseni(admin_client):
    odpoved = admin_client.post(
        "/admin/osoby/osoba/add/",
        {
            "jmeno": "Eva",
            "prijmeni": "Malá",
            "email": "",
            "usable_password": "false",
            # prázdný formulář oprávnění (inline)
            "opravneni-TOTAL_FORMS": "0",
            "opravneni-INITIAL_FORMS": "0",
            "licence-TOTAL_FORMS": "0",
            "licence-INITIAL_FORMS": "0",
            "medicaly-TOTAL_FORMS": "0",
            "medicaly-INITIAL_FORMS": "0",
        },
    )
    assert odpoved.status_code == 302, odpoved.content.decode()[:2000]
    eva = Osoba.objects.get(prijmeni="Malá")
    assert eva.email is None
    assert not eva.has_usable_password()


@pytest.mark.parametrize(
    "url",
    [
        "/admin/",
        "/admin/osoby/osoba/",
        "/admin/osoby/osoba/add/",
        "/admin/lety/letadlo/add/",
        "/admin/lety/uloha/add/",
        "/admin/lety/osnova/add/",
        "/admin/lety/let/",
        "/admin/lety/let/add/",
        "/admin/lety/auditlog/",
    ],
)
def test_stranky_administrace_se_zobrazi(admin_client, url):
    assert admin_client.get(url).status_code == 200
