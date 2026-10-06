from unittest.mock import MagicMock, patch

from app.services.specific_experience import (
    extract_specific_experience_from_pdf_bytes,
    extract_specific_experience_from_text,
    extract_specific_experience_with_vision,
)


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


def test_scanned_acta_uses_vision_when_pdf_has_no_text():
    with patch(
        "app.services.rup_parser.extract_text_from_pdf_bytes",
        return_value="044\n045\n046\n047\n048\n049",
    ), patch(
        "app.services.specific_experience.extract_specific_experience_with_vision",
        return_value="Construcción y mejoramiento de la malla vial urbana en Paipa.",
    ) as vision:
        result = extract_specific_experience_from_pdf_bytes(b"%PDF-scan")
    assert "malla vial" in result
    vision.assert_called_once_with(b"%PDF-scan")


def test_garbled_scan_text_layer_uses_vision():
    garbage = (
        "r`> h} ^) ---.-.:.-,_ § ¡J, ;iii iiiiiiiiiii! Ííi!! ii8 >Ci !ii3iiíi "
        * 40
    )
    with patch(
        "app.services.rup_parser.extract_text_from_pdf_bytes",
        return_value=garbage,
    ), patch(
        "app.services.specific_experience.extract_specific_experience_with_vision",
        return_value="Mejoramiento de la vía Santa Isabel en el municipio.",
    ) as vision:
        result = extract_specific_experience_from_pdf_bytes(b"%PDF-garbled")
    assert "Santa Isabel" in result
    vision.assert_called_once()


def test_native_text_skips_vision():
    native = (
        "Acta de recibo. Objeto del contrato: Construcción del acueducto veredal "
        "en el municipio de Paipa, Boyacá. Valor: 100."
    )
    with patch(
        "app.services.rup_parser.extract_text_from_pdf_bytes",
        return_value=native,
    ), patch(
        "app.services.specific_experience.extract_specific_experience_with_vision"
    ) as vision:
        result = extract_specific_experience_from_pdf_bytes(b"%PDF-text")
    assert "acueducto" in result.lower()
    vision.assert_not_called()


def test_vision_reads_objeto_json():
    fake_response = MagicMock()
    fake_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"objeto": "Pavimentación de la vía urbana en el centro de Paipa."}'
            )
        )
    ]
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response
    with patch("app.services.specific_experience.settings") as mock_settings, patch(
        "app.services.specific_experience.render_acta_page_jpegs",
        return_value=[(1, b"jpeg-bytes")],
    ), patch("openai.OpenAI", return_value=fake_client):
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
        result = extract_specific_experience_with_vision(b"%PDF")
    assert "Pavimentación" in result

