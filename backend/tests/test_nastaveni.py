from config.settings import databaze_z_vps_centra


def test_bez_promennych_vps_centra(monkeypatch):
    monkeypatch.delenv("DB_NAME", raising=False)
    assert databaze_z_vps_centra() is None


def test_databaze_pres_socket_z_vps_centra(monkeypatch):
    monkeypatch.setenv("DB_NAME", "lkkl_lety")
    monkeypatch.setenv("DB_USER", "lkkl_lety")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_SOCKET", "/var/run/postgresql/.s.PGSQL.5432")
    db = databaze_z_vps_centra()
    assert db["NAME"] == "lkkl_lety"
    assert db["HOST"] == "/var/run/postgresql"
    assert db["PORT"] == "5432"
    assert db["PASSWORD"] == ""


def test_socket_jako_slozka(monkeypatch):
    monkeypatch.setenv("DB_NAME", "x")
    monkeypatch.setenv("DB_SOCKET", "/run/postgresql")
    assert databaze_z_vps_centra()["HOST"] == "/run/postgresql"
