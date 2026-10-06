from app.services.company_email import is_company_email, is_personal_email


def test_rejects_gmail_and_hotmail():
    assert is_personal_email("juan@gmail.com")
    assert is_personal_email("  Ana@Hotmail.ES ")
    assert not is_company_email("ana@outlook.com")


def test_accepts_company_domain():
    assert is_company_email("licitaciones@constructorabec.com")
    assert is_company_email("otto@exury.io")
    assert not is_personal_email("compras@municipio.gov.co")
