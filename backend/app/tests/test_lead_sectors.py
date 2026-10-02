from app.api.v1.leads import parse_sectors, serialize_sectors


def test_serialize_sectors_dedupes_and_keeps_order():
    assert (
        serialize_sectors(["interventoria", "obra", "interventoria", "estudios_disenos"])
        == "interventoria,estudios_disenos"
    )


def test_serialize_sectors_rejects_unknown():
    assert serialize_sectors(["consultoria"]) is None


def test_parse_sectors_roundtrip():
    raw = serialize_sectors(["estudios_disenos", "ejecucion_obra"])
    assert parse_sectors(raw) == ["estudios_disenos", "ejecucion_obra"]
