from unittest.mock import MagicMock, patch

from app.services.specific_experience import (
    _vision_batch,
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


def test_extracts_objeto_on_following_line():
    text = """
    ACTA DE RECIBO FINAL
    OBJETO DEL CONTRATO
    Construcción y mejoramiento de la malla vial urbana en el municipio de Paipa.
    VALOR DEL CONTRATO: $ 1.000
    """
    result = extract_specific_experience_from_text(text)
    assert result is not None
    assert "malla vial" in result.lower()
    assert "valor" not in result.lower()


def test_extracts_tiene_por_objeto():
    text = (
        "El Fondo Financiero de Proyectos de Desarrollo FONADE contrató al "
        "Consorcio Santa Isabel, contrato que tiene por objeto estudios, "
        "diseños y construcción del sistema de acueducto de Santa Isabel. "
        "Valor: $ 500."
    )
    result = extract_specific_experience_from_text(text)
    assert result is not None
    assert "acueducto" in result.lower()
    assert "santa isabel" in result.lower()


def test_extracts_objetivo_field_on_a_certificate():
    text = """
    CERTIFICA
    OBJETIVO: INTERVENTORÍA TÉCNICA, ADMINISTRATIVA Y AMBIENTAL PARA EL MEJORAMIENTO DE LA VÍA LAS MARGARITAS.
    FECHA DE INICIACION: Septiembre 11 de 2006
    """
    result = extract_specific_experience_from_text(text)
    assert result is not None
    assert "margaritas" in result.lower()
    assert "fecha" not in result.lower()


def test_vision_reads_the_scan_at_high_detail():
    client = MagicMock()
    message = MagicMock()
    message.content = (
        '{"objeto": "INTERVENTORIA TECNICA PARA EL MEJORAMIENTO DE LA VIA LAS MARGARITAS CAUYA"}'
    )
    client.chat.completions.create.return_value.choices = [MagicMock(message=message)]
    result = _vision_batch(client, [(1, b"\xff\xd8\xff" + b"x" * 40)])
    content = client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    image = next(part["image_url"] for part in content if part.get("type") == "image_url")
    assert image["detail"] == "high"
    assert "margaritas" in result.lower()


def test_reads_the_object_inside_the_certificate_sentence():
    text = """
    CERTIFICA:
    Que el contratista ejecutó las obras del Contrato de Obra Pública No. 031 de 1990,
    en la adecuación y construcción de canchas, en los barrios Aurora II y San Luis Sur,
    valor de $ 9.970.530.
    Las obras ejecutadas consistieron principalmente en:
    1- Excavación para sub-razante.
    2- Relleno en material proveniente del corte.
    3- Compactación.
    """
    result = extract_specific_experience_from_text(text)
    assert result is not None
    assert "canchas" in result.lower()
    assert "aurora" in result.lower()
    assert "excav" not in result.lower()


def test_rejects_the_executed_works_list_as_objeto():
    text = (
        "Las obras ejecutadas consistieron principalmente en: "
        "1- Excavación para sub-razante. "
        "2- Relleno en material proveniente del corte. "
        "3- Compactación de la base."
    )
    assert extract_specific_experience_from_text(text) is None


def test_returns_none_when_no_objeto():
    text = "Certificado de existencia y representación legal de la sociedad. " * 5
    assert extract_specific_experience_from_text(text) is None


def test_scanned_acta_uses_vision_when_pdf_has_no_text():
    with patch(
        "app.services.specific_experience._page_texts",
        return_value=["044\n045\n046\n047\n048\n049"],
    ), patch(
        "app.services.specific_experience.extract_specific_experience_with_vision",
        return_value="Construcción y mejoramiento de la malla vial urbana en Paipa.",
    ) as vision:
        result = extract_specific_experience_from_pdf_bytes(b"%PDF-scan")
    assert "malla vial" in result
    vision.assert_called_once()


def test_garbled_scan_text_layer_uses_vision():
    garbage = (
        "r`> h} ^) ---.-.:.-,_ § ¡J, ;iii iiiiiiiiiii! Ííi!! ii8 >Ci !ii3iiíi "
        * 40
    )
    with patch(
        "app.services.specific_experience._page_texts",
        return_value=[garbage],
    ), patch(
        "app.services.specific_experience.extract_objeto_from_text_with_llm",
        return_value=None,
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
        "app.services.specific_experience._page_texts",
        return_value=[native],
    ), patch(
        "app.services.specific_experience.extract_specific_experience_with_vision"
    ) as vision:
        result = extract_specific_experience_from_pdf_bytes(b"%PDF-text")
    assert "acueducto" in result.lower()
    vision.assert_not_called()


def test_llm_extracts_objeto_when_regex_misses():
    native = (
        "Certificado de cumplimiento. El contratista ejecutó la pavimentación "
        "de la vía terciaria entre Paipa y Sotaquirá, incluyendo obras de "
        "drenaje y señalización. Constancia de recibo a satisfacción. "
        * 2
    )
    with patch(
        "app.services.specific_experience._page_texts",
        return_value=[native],
    ), patch(
        "app.services.specific_experience.extract_objeto_from_text_with_llm",
        return_value="Pavimentación de la vía terciaria entre Paipa y Sotaquirá.",
    ) as llm, patch(
        "app.services.specific_experience.extract_specific_experience_with_vision"
    ) as vision:
        result = extract_specific_experience_from_pdf_bytes(b"%PDF-llm")
    assert "terciaria" in result.lower()
    llm.assert_called_once()
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
    ), patch(
        "app.services.specific_experience._page_texts",
        return_value=["acta"],
    ), patch("openai.OpenAI", return_value=fake_client):
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
        result = extract_specific_experience_with_vision(b"%PDF")
    assert "Pavimentación" in result


def test_backfill_reads_the_replaced_acta_before_older_pending_files():
    from datetime import datetime
    from types import SimpleNamespace

    from app.services.specific_experience import backfill_objetos_from_stored_actas

    older = SimpleNamespace(
        id="old",
        specific_experience=None,
        specific_evidence_key="old-key",
        specific_evidence_filename="acta-vieja.pdf",
        updated_at=datetime(2020, 1, 1),
        keywords=None,
    )
    newer = SimpleNamespace(
        id="new",
        specific_experience="  ",
        specific_evidence_key="new-key",
        specific_evidence_filename="acta-nueva.pdf",
        updated_at=datetime(2026, 10, 12),
        keywords=None,
    )
    storage = MagicMock()
    storage.iter_file_chunks.return_value = [b"%PDF"]
    objeto = "INTERVENTORIA TECNICA PARA EL MEJORAMIENTO DE LA VIA LAS MARGARITAS CAUYA."
    with patch(
        "app.services.document_storage.get_document_storage",
        return_value=storage,
    ), patch(
        "app.services.specific_experience.extract_specific_experience_from_pdf_bytes",
        return_value=objeto,
    ), patch(
        "app.services.rup_contract_kind.apply_kind_from_specific_experience",
    ), patch(
        "app.services.project_typology.apply_project_typologies",
    ), patch(
        "app.services.experience_matching.extract_keywords",
        return_value=["via"],
    ):
        filled = backfill_objetos_from_stored_actas(MagicMock(), [older, newer], limit=1)

    assert filled == 1
    assert newer.specific_experience == objeto
    assert older.specific_experience is None
    storage.iter_file_chunks.assert_called_once_with("new-key")
