from datetime import datetime, timedelta

from app.services.login_code import generate_code, hash_code, verify_code
from app.models.login_code import LoginCode


def test_generate_code_is_six_digits():
    code = generate_code()
    assert len(code) == 6
    assert code.isdigit()


def test_hash_code_is_stable(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "AUTH_OTP_SECRET", "test-secret")
    assert hash_code("A@B.com", "123456") == hash_code("a@b.com", "123456")
    assert hash_code("a@b.com", "123456") != hash_code("a@b.com", "000000")


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class _FakeDb:
    def __init__(self, row=None):
        self.row = row
        self.committed = False

    def query(self, model):
        return _FakeQuery([self.row] if self.row else [])

    def commit(self):
        self.committed = True


def test_verify_rejects_bad_format():
    db = _FakeDb()
    assert verify_code(db, "a@b.com", "12").ok is False
    assert verify_code(db, "a@b.com", "abcdef").ok is False


def test_verify_accepts_matching_code(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "AUTH_OTP_SECRET", "test-secret")
    monkeypatch.setattr(settings, "AUTH_OTP_MAX_ATTEMPTS", 5)
    row = LoginCode(
        email="a@b.com",
        code_hash=hash_code("a@b.com", "654321"),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        attempt_count=0,
    )
    db = _FakeDb(row)
    result = verify_code(db, "a@b.com", "654321")
    assert result.ok is True
    assert row.consumed_at is not None


def test_ensure_auth_tables_adds_phone_column():
    import inspect
    from app.services import login_code as login_code_mod

    source = inspect.getsource(login_code_mod.ensure_auth_tables)
    assert "phone VARCHAR(50)" in source
    assert "login_codes" in source


def test_verify_rejects_wrong_code(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "AUTH_OTP_SECRET", "test-secret")
    monkeypatch.setattr(settings, "AUTH_OTP_MAX_ATTEMPTS", 5)
    row = LoginCode(
        email="a@b.com",
        code_hash=hash_code("a@b.com", "654321"),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        attempt_count=0,
    )
    db = _FakeDb(row)
    result = verify_code(db, "a@b.com", "000000")
    assert result.ok is False
    assert result.reason == "invalid"
    assert row.attempt_count == 1
