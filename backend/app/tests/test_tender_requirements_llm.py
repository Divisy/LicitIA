"""Tests for LLM enrichment of tender requirements (US 1.5)."""
from unittest.mock import MagicMock, patch

from app.services.tender_requirements.llm_extraction import (
    enrich_requirements_with_llm,
    extract_scoring_fallback_with_llm,
)


def _llm_response(sections: dict) -> MagicMock:
    message = MagicMock()
    message.content = '{"sections": ' + __import__("json").dumps(sections) + "}"
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_skipped_when_disabled(mock_settings):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = False
    existing = {"experiencia_general": [], "experiencia_especifica": []}
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="Experiencia general del 30%",
        existing_sections=existing,
    )
    assert result == existing


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_refines_sections_when_regex_already_filled(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "experiencia_general": [
                {
                    "key": "requirement_description",
                    "label": "Descripción del requisito",
                    "display_value": (
                        "Interventoría de proyectos de construcción, rehabilitación o "
                        "conservación de vías."
                    ),
                    "evidence": "interventoria a proyectos de construccion",
                    "confidence": 0.91,
                }
            ],
            "experiencia_especifica": [
                {
                    "key": "specific_scope",
                    "label": "Alcance exigido",
                    "display_value": (
                        "Al menos un contrato de experiencia general debe equivaler al "
                        "60% del Presupuesto Oficial."
                    ),
                    "evidence": "por lo menos el 60% del valor del presupuesto oficial",
                    "confidence": 0.89,
                }
            ],
        }
    )

    existing = {
        "experiencia_general": [
            {
                "key": "requirement_description",
                "label": "Descripción del requisito",
                "display_value": "interventoria a proyectos de construccion o mejoramiento...",
                "confidence": 0.92,
                "extraction_method": "regex",
            }
        ],
        "experiencia_especifica": [
            {
                "key": "specific_scope",
                "label": "Alcance exigido",
                "display_value": "por lo menos uno (1) de los contratos validos...",
                "confidence": 0.92,
                "extraction_method": "regex",
            }
        ],
    }
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="3.1 EXPERIENCIA GENERAL ... 60% del presupuesto oficial",
        existing_sections=existing,
    )

    assert result["experiencia_general"][0]["extraction_method"] == "llm"
    assert "Interventoría" in result["experiencia_general"][0]["display_value"]
    assert result["experiencia_especifica"][0]["extraction_method"] == "llm"
    mock_client.chat.completions.create.assert_called_once()


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_fills_sparse_experience_sections(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "experiencia_general": [
                {
                    "key": "min_percentage_budget",
                    "label": "Experiencia mínima",
                    "display_value": "30% del PO",
                    "evidence": "treinta por ciento (30%) del presupuesto oficial",
                    "confidence": 0.88,
                }
            ],
            "experiencia_especifica": [
                {
                    "key": "specific_min_percentage",
                    "label": "Experiencia específica",
                    "display_value": "20% del PO",
                    "evidence": "equivalente al 20% del valor del contrato",
                    "confidence": 0.82,
                }
            ],
        }
    )

    existing = {"experiencia_general": [], "experiencia_especifica": []}
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="3.1 EXPERIENCIA GENERAL ... 30% ... 4. EXPERIENCIA ESPECIFICA 20%",
        existing_sections=existing,
    )

    assert len(result["experiencia_general"]) == 1
    assert result["experiencia_general"][0]["extraction_method"] == "llm"
    assert len(result["experiencia_especifica"]) == 1
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["response_format"] == {"type": "json_object"}


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_keeps_regex_when_model_returns_nothing(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {"experiencia_general": [], "experiencia_especifica": []}
    )

    regex_item = {
        "key": "min_percentage_budget",
        "label": "Porcentaje",
        "display_value": "100%",
        "confidence": 0.9,
        "extraction_method": "regex",
    }
    existing = {"experiencia_general": [regex_item], "experiencia_especifica": []}
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="texto",
        existing_sections=existing,
    )

    assert result["experiencia_general"] == [regex_item]


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_rejects_low_confidence_items(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "experiencia_general": [
                {
                    "key": "min_percentage_budget",
                    "label": "Experiencia mínima",
                    "display_value": "30%",
                    "evidence": "fragmento",
                    "confidence": 0.55,
                }
            ]
        }
    )

    existing = {"experiencia_general": [], "experiencia_especifica": []}
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="texto",
        existing_sections=existing,
    )

    assert result["experiencia_general"] == []


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_financial_regex_priority_over_llm_thresholds(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "indicadores_financieros": [
                {
                    "key": "endeudamiento",
                    "label": "Índice de endeudamiento",
                    "display_value": "≥ 2.0",
                    "evidence": "hallucinated",
                    "confidence": 0.95,
                },
                {
                    "key": "financial_summary",
                    "label": "Resumen",
                    "display_value": "Acreditar solvencia según Matriz 2 y numeral 3.7.1.",
                    "evidence": "Matriz 2",
                    "confidence": 0.88,
                },
            ]
        }
    )

    regex_endeudamiento = {
        "key": "endeudamiento",
        "label": "Índice de endeudamiento",
        "display_value": "≤ 1.2",
        "value": {"operator": "<=", "threshold": 1.2},
        "confidence": 0.9,
        "extraction_method": "regex",
    }
    regex_summary = {
        "key": "financial_summary",
        "label": "Resumen",
        "display_value": "texto crudo del pdf...",
        "confidence": 0.88,
        "extraction_method": "regex",
    }
    existing = {
        "experiencia_general": [],
        "experiencia_especifica": [],
        "indicadores_financieros": [regex_endeudamiento, regex_summary],
    }
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría",
        context_excerpt="",
        financial_context_excerpt="3.5 Capacidad financiera ... endeudamiento <= 1.2",
        existing_sections=existing,
    )

    endeudamiento = next(item for item in result["indicadores_financieros"] if item["key"] == "endeudamiento")
    assert endeudamiento["display_value"] == "≤ 1.2"
    assert endeudamiento["extraction_method"] == "regex"

    summary = next(item for item in result["indicadores_financieros"] if item["key"] == "financial_summary")
    assert summary["extraction_method"] == "llm"
    assert "Matriz 2" in summary["display_value"]


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_cannot_inject_financial_metric_keys(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "indicadores_financieros": [
                {
                    "key": "endeudamiento",
                    "label": "Índice de endeudamiento",
                    "display_value": "≥ 1.2",
                    "evidence": "hallucinated",
                    "confidence": 0.95,
                },
                {
                    "key": "financial_summary",
                    "label": "Resumen",
                    "display_value": "Acreditar solvencia según el pliego.",
                    "evidence": "solvencia economica",
                    "confidence": 0.88,
                },
            ]
        }
    )

    regex_endeudamiento = {
        "key": "endeudamiento",
        "label": "Índice de endeudamiento",
        "display_value": "PT / AT ≤ 70%",
        "value": {"operator": "<=", "threshold": 0.7},
        "confidence": 0.9,
        "extraction_method": "regex",
    }
    existing = {
        "experiencia_general": [],
        "experiencia_especifica": [],
        "indicadores_financieros": [regex_endeudamiento],
    }
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría",
        context_excerpt="",
        financial_context_excerpt="endeudamiento menor o igual a 70%",
        existing_sections=existing,
    )

    keys = {item["key"] for item in result["indicadores_financieros"]}
    assert "endeudamiento" in keys
    endeudamiento = next(item for item in result["indicadores_financieros"] if item["key"] == "endeudamiento")
    assert endeudamiento["extraction_method"] == "regex"
    assert endeudamiento["value"]["threshold"] == 0.7


@patch("app.services.tender_requirements.llm_extraction._openai_client", None)
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_skipped_without_openai_client(mock_settings):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    existing = {"experiencia_general": [], "experiencia_especifica": []}
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Interventoría vial",
        context_excerpt="texto",
        existing_sections=existing,
    )
    assert result == existing


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_merges_scoring_with_regex_points_priority(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "sistema_puntos": [
                {
                    "key": "oferta_economica",
                    "label": "Oferta económica",
                    "max_points": 50.0,
                    "criterion_type": "evaluacion",
                    "display_value": "50 puntos",
                    "evidence": "Oferta económica 48,5",
                    "confidence": 0.92,
                },
                {
                    "key": "factor_calidad",
                    "label": "Factor de calidad",
                    "max_points": 30.0,
                    "criterion_type": "evaluacion",
                    "display_value": "30 puntos",
                    "evidence": "Factor de calidad 30",
                    "confidence": 0.9,
                },
                {
                    "key": "total_points",
                    "label": "Total",
                    "max_points": 100.0,
                    "criterion_type": "evaluacion",
                    "display_value": "100 puntos",
                    "evidence": "Total 100",
                    "confidence": 0.95,
                },
            ]
        }
    )

    regex_oferta = {
        "key": "oferta_economica",
        "label": "Oferta económica",
        "value": {
            "max_points": 48.5,
            "assignment_rule": "",
            "criterion_type": "evaluacion",
        },
        "display_value": "48.5 puntos",
        "confidence": 0.88,
        "extraction_method": "regex",
    }
    regex_total = {
        "key": "total_points",
        "label": "Total",
        "value": {"max_points": 100.0, "assignment_rule": "", "criterion_type": "evaluacion"},
        "display_value": "100 puntos",
        "confidence": 0.9,
        "extraction_method": "regex",
    }
    existing = {
        "experiencia_general": [],
        "experiencia_especifica": [],
        "sistema_puntos": [regex_oferta, regex_total],
    }
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.LP",
        object_text="Infraestructura vial",
        context_excerpt="",
        scoring_context_excerpt="Capítulo IV. Concepto Puntaje máximo Oferta económica 48,5",
        existing_sections=existing,
    )

    oferta = next(item for item in result["sistema_puntos"] if item["key"] == "oferta_economica")
    assert oferta["value"]["max_points"] == 48.5
    assert oferta["extraction_method"] == "hybrid"
    assert oferta["label"] == "Oferta económica"

    calidad = next(item for item in result["sistema_puntos"] if item["key"] == "factor_calidad")
    assert calidad["extraction_method"] == "llm"
    assert calidad["value"]["max_points"] == 30.0

    total = next(item for item in result["sistema_puntos"] if item["key"] == "total_points")
    assert total["value"]["max_points"] == 100.0


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_scoring_falls_back_to_regex_when_llm_empty(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response({"sistema_puntos": []})

    regex_item = {
        "key": "experiencia",
        "label": "Experiencia",
        "value": {"max_points": 25.0, "assignment_rule": "", "criterion_type": "evaluacion"},
        "display_value": "25 puntos",
        "confidence": 0.85,
        "extraction_method": "regex",
    }
    existing = {
        "experiencia_general": [],
        "experiencia_especifica": [],
        "sistema_puntos": [regex_item],
    }
    result = enrich_requirements_with_llm(
        tender_external_id="CO1.REQ.1",
        object_text="Obra",
        context_excerpt="",
        scoring_context_excerpt="Capítulo IV criterios de evaluación",
        existing_sections=existing,
    )

    assert result["sistema_puntos"] == [regex_item]


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_llm_scoring_keeps_regex_criteria_missing_from_llm(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_LLM_MAX_CHARS = 8000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "sistema_puntos": [
                {
                    "key": "oferta_economica",
                    "label": "Oferta económica",
                    "max_points": 48.5,
                    "criterion_type": "evaluacion",
                    "display_value": "48.5 puntos",
                    "evidence": "Oferta económica 48,5",
                    "confidence": 0.92,
                },
                {
                    "key": "factor_calidad",
                    "label": "Factor de calidad",
                    "max_points": 30.0,
                    "criterion_type": "evaluacion",
                    "display_value": "30 puntos",
                    "evidence": "Factor de calidad 30",
                    "confidence": 0.9,
                },
                {
                    "key": "industria_nacional",
                    "label": "Apoyo a la industria nacional",
                    "max_points": 20.0,
                    "criterion_type": "evaluacion",
                    "display_value": "20 puntos",
                    "evidence": "Industria nacional 20",
                    "confidence": 0.88,
                },
                {
                    "key": "discapacidad",
                    "label": "Vinculación personas con discapacidad",
                    "max_points": 1.0,
                    "criterion_type": "evaluacion",
                    "display_value": "1 puntos",
                    "evidence": "Discapacidad 1",
                    "confidence": 0.87,
                },
                {
                    "key": "empresas_mujeres",
                    "label": "Empresas de mujeres",
                    "max_points": 0.25,
                    "criterion_type": "evaluacion",
                    "display_value": "0.25 puntos",
                    "evidence": "Empresas de mujeres 0,25",
                    "confidence": 0.86,
                },
                {
                    "key": "total_points",
                    "label": "Total",
                    "max_points": 100.0,
                    "criterion_type": "evaluacion",
                    "display_value": "100 puntos",
                    "evidence": "Total 100",
                    "confidence": 0.95,
                },
            ]
        }
    )

    regex_mipyme = {
        "key": "mipyme",
        "label": "MiPyme",
        "value": {
            "max_points": 0.25,
            "assignment_rule": "",
            "criterion_type": "evaluacion",
            "sort_order": 6,
        },
        "display_value": "0.25 puntos",
        "confidence": 0.88,
        "extraction_method": "regex",
    }
    regex_total = {
        "key": "total_points",
        "label": "Total evaluación habilitante",
        "value": {"max_points": 100.0, "assignment_rule": "", "criterion_type": "evaluacion"},
        "display_value": "100 puntos",
        "confidence": 0.9,
        "extraction_method": "regex",
    }
    existing = {
        "experiencia_general": [],
        "experiencia_especifica": [],
        "sistema_puntos": [regex_mipyme, regex_total],
    }
    result = enrich_requirements_with_llm(
        tender_external_id="IDRD-SG-LP-020-2026",
        object_text="Infraestructura",
        context_excerpt="",
        scoring_context_excerpt="Concepto Puntaje maximo Oferta economica 48,5 Mipyme 0,25 Total 100",
        existing_sections=existing,
    )

    eval_items = [
        item
        for item in result["sistema_puntos"]
        if item["key"] != "total_points" and item["value"]["criterion_type"] == "evaluacion"
    ]
    keys = {item["key"] for item in eval_items}
    assert "mipyme" in keys
    assert sum(float(item["value"]["max_points"]) for item in eval_items) == 100.0


@patch("app.services.tender_requirements.llm_extraction._openai_client", None)
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_scoring_fallback_skipped_without_openai(mock_settings):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.TENDER_REQUIREMENTS_SCORING_LLM_FALLBACK = True
    result = extract_scoring_fallback_with_llm(
        tender_external_id="CO1.TEST",
        object_text="Obra",
        scoring_excerpt="Concepto Puntaje maximo Total 100",
    )
    assert result == []


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_scoring_fallback_accepts_valid_llm_table(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.TENDER_REQUIREMENTS_SCORING_LLM_FALLBACK = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_SCORING_LLM_FALLBACK_MAX_CHARS = 6000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "sistema_puntos": [
                {
                    "key": "experiencia",
                    "label": "Experiencia del proponente",
                    "max_points": 40,
                    "criterion_type": "evaluacion",
                    "display_value": "40 puntos",
                    "evidence": "experiencia especifica 40 puntos",
                    "confidence": 0.93,
                },
                {
                    "key": "equipo_trabajo",
                    "label": "Equipo de trabajo",
                    "max_points": 45,
                    "criterion_type": "evaluacion",
                    "display_value": "45 puntos",
                    "evidence": "personal de equipo 45 puntos",
                    "confidence": 0.93,
                },
                {
                    "key": "industria_nacional",
                    "label": "Industria nacional",
                    "max_points": 15,
                    "criterion_type": "evaluacion",
                    "display_value": "15 puntos",
                    "evidence": "industria nacional 15 puntos",
                    "confidence": 0.9,
                },
                {
                    "key": "total_points",
                    "label": "Total",
                    "max_points": 100,
                    "criterion_type": "evaluacion",
                    "display_value": "100 puntos",
                    "evidence": "puntaje total 100 puntos",
                    "confidence": 0.95,
                },
            ]
        }
    )

    result = extract_scoring_fallback_with_llm(
        tender_external_id="CO1.TEST",
        object_text="Concurso de méritos",
        scoring_excerpt="experiencia 40 puntos equipo 45 puntos industria 15 puntos total 100 puntos",
    )

    assert result
    assert all(item.get("extraction_method") == "llm_fallback" for item in result if item["key"] != "total_points")
    eval_sum = sum(
        float(item["value"]["max_points"])
        for item in result
        if item["key"] != "total_points" and item["value"]["criterion_type"] == "evaluacion"
    )
    assert eval_sum == 100.0
    mock_client.chat.completions.create.assert_called_once()


@patch("app.services.tender_requirements.llm_extraction._openai_client")
@patch("app.services.tender_requirements.llm_extraction.settings")
def test_scoring_fallback_discards_mismatched_llm_table(mock_settings, mock_client):
    mock_settings.TENDER_REQUIREMENTS_USE_LLM = True
    mock_settings.TENDER_REQUIREMENTS_SCORING_LLM_FALLBACK = True
    mock_settings.OPENAI_MODEL_NAME = "gpt-4o-mini"
    mock_settings.TENDER_REQUIREMENTS_LLM_MIN_CONFIDENCE = 0.70
    mock_settings.TENDER_REQUIREMENTS_SCORING_LLM_FALLBACK_MAX_CHARS = 6000
    mock_client.chat.completions.create.return_value = _llm_response(
        {
            "sistema_puntos": [
                {
                    "key": "experiencia",
                    "label": "Experiencia",
                    "max_points": 40,
                    "criterion_type": "evaluacion",
                    "confidence": 0.9,
                },
                {
                    "key": "total_points",
                    "label": "Total",
                    "max_points": 100,
                    "criterion_type": "evaluacion",
                    "confidence": 0.9,
                },
            ]
        }
    )

    result = extract_scoring_fallback_with_llm(
        tender_external_id="CO1.TEST",
        object_text="Obra",
        scoring_excerpt="experiencia 40 puntos total 100 puntos",
    )
    assert result == []
