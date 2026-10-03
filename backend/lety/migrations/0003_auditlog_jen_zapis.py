from django.db import migrations

# Auditní log je jen pro zápis: databáze odmítne každou úpravu i smazání,
# ať by přišly z aplikace, z administrace, nebo ručním SQL.
SQL = """
CREATE FUNCTION lety_auditlog_jen_zapis() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Auditní log nelze měnit ani mazat.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER lety_auditlog_jen_zapis
    BEFORE UPDATE OR DELETE ON lety_auditlog
    FOR EACH ROW EXECUTE FUNCTION lety_auditlog_jen_zapis();
"""

REVERSE_SQL = """
DROP TRIGGER IF EXISTS lety_auditlog_jen_zapis ON lety_auditlog;
DROP FUNCTION IF EXISTS lety_auditlog_jen_zapis();
"""


class Migration(migrations.Migration):
    dependencies = [("lety", "0002_initial")]

    operations = [migrations.RunSQL(SQL, REVERSE_SQL)]
