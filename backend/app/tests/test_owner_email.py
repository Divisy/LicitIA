import inspect

from app.services import rup_import


def test_ensure_owner_email_columns_sql():
    source = inspect.getsource(rup_import.ensure_owner_email_columns)
    assert "owner_email" in source
    assert "company_experiences" in source
    assert "company_capacity" in source


def test_replace_experiences_scopes_by_owner_email():
    source = inspect.getsource(rup_import.replace_experiences_from_rup)
    assert "owner_email" in source
