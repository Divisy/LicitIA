from app.services.specific_experience import extract_specific_experience_from_text


def test_extracts_objeto_del_contrato():
    text = """
    ACTA DE RECIBO Y FINALIZACION
    Contrato No. IDU-1257-2017
    Objeto del contrato: Construcción y mejoramiento de la malla vial local
    en la localidad de Kennedy, incluyendo andenes y cicloinfraestructura.
    Valor: $ 6.626.742.978
    Fecha de terminación: 08/03/2019
    """
    result = extract_specific_experience_from_text(text)
    assert result is not None
    assert "malla vial" in result.lower()
    assert "valor" not in result.lower()


def test_returns_none_when_no_objeto():
    text = "Certificado de existencia y representación legal de la sociedad. " * 5
    assert extract_specific_experience_from_text(text) is None
