"""Tests for tender requirements extraction (US 1.5)."""
from uuid import uuid4

from app.models.tender import Tender, TenderSource
from app.models.tender_document import TenderDocument
from app.services.tender_requirements.regex_extraction import (
    extract_experiencia_especifica,
    extract_experiencia_general,
    extract_indicadores_financieros,
    extract_requisitos_legales,
    merge_financial_requirement_items,
    normalize_text,
)
from app.services.tender_requirements.residual_capacity_extraction import extract_capacidad_residual
from app.services.tender_requirements.scoring_extraction import (
    extract_sistema_puntos,
    merge_scoring_fallback_items,
    reconcile_sistema_puntos_items,
    sistema_puntos_sum_mismatch,
)
from app.services.tender_requirements.text_selection import (
    select_scoring_fallback_text_for_llm,
    select_scoring_text_for_llm,
)
from app.services.tender_requirements.service import build_tender_requirements, requirements_cache_is_stale


PLIEGO_SAMPLE = """
CAPITULO III REQUISITOS DE PARTICIPACION
3.1 EXPERIENCIA GENERAL
El proponente deberá acreditar experiencia general equivalente al treinta por ciento (30%)
del presupuesto oficial de la presente licitación, ejecutada en los últimos 5 años.
La experiencia se acreditará mediante Matriz 1 y certificados de experiencia.

3.2 SOLVENCIA ECONOMICA Y FINANCIERA
El índice de liquidez corriente deberá ser mayor o igual a 1.0.
La calificación por solvencia tendrá un puntaje de 20 puntos.

3.3 REQUISITOS LEGALES
El proponente deberá estar inscrito en el Registro Único de Proponentes (RUP) con capacidad jurídica.
Deberá contar con licencia de construcción vigente cuando aplique.
"""

ANEXO_SAMPLE = """
ANEXO TECNICO
4. EXPERIENCIA ESPECIFICA
El proponente deberá demostrar experiencia específica en interventoría de obras viales,
equivalente al 20% del valor del contrato.
Códigos de actividad UNSPSC: 72141100, 72141200
"""


CCE_PLIEGO_EXPERIENCE = """
3.5.9 RELACION DE LOS CONTRATOS FRENTE AL PRESUPUESTO OFICIAL
Numero de contratos con los cuales el Proponente cumple la experiencia acreditada
Valor minimo a certificar (como % del Presupuesto Oficial de obra expresado en SMMLV)
De 1 hasta 2 75 %
De 3 hasta 4 120 %
Hasta 5 150 %
"""


def test_extract_cce_experience_value_tiers_and_contracts():
    general = extract_experiencia_general(CCE_PLIEGO_EXPERIENCE, "pliego_condiciones", None)
    specific = extract_experiencia_especifica(CCE_PLIEGO_EXPERIENCE, "pliego_condiciones", None)
    general_keys = {item["key"] for item in general}
    specific_keys = {item["key"] for item in specific}

    assert "experience_value_tiers" in general_keys
    assert "min_amount_smmlv" in general_keys
    assert "experience_value_tiers" not in specific_keys

    tiers = next(item for item in general if item["key"] == "experience_value_tiers")
    assert tiers["value"] == [
        {"contract_range": "1-2", "percentage": 75.0},
        {"contract_range": "3-4", "percentage": 120.0},
        {"contract_range": "1-5", "percentage": 150.0},
    ]


def test_extract_cce_tier_table_with_spaced_percent_sign():
    text = """
    3.5.9 RELACION DE LOS CONTRATOS FRENTE AL PRESUPUESTO OFICIAL
    Numero de contratos con los cuales el Proponente cumple la experiencia acreditada
    De 1 hasta 2 75 %
    De 3 hasta 4 120 %
    Hasta 5 150 %
    """
    from app.services.tender_requirements.regex_extraction import extract_experience_value_tiers, normalize_text

    tiers = extract_experience_value_tiers(normalize_text(text))
    assert tiers[-1] == {"contract_range": "1-5", "percentage": 150.0}


def test_interventoria_experience_does_not_use_contract_tier_table():
    text = """
    3.8.1 EXIGENCIA MINIMA DE LA EXPERIENCIA DEL PROPONENTE
    contratos aportados como experiencia es mayor o igual al cien por ciento (100 %)
    respecto del valor total del Presupuesto Oficial expresado en SMMLV.
    EXPERIENCIA GENERAL: INTERVENTORIA DE OBRAS VIALES.
    EXPERIENCIA ESPECIFICA: al menos el 60% del Presupuesto Oficial del presente proceso.
    """
    general = extract_experiencia_general(text, "pliego_condiciones", None)
    specific = extract_experiencia_especifica(text, "pliego_condiciones", None)
    assert "experience_value_tiers" not in {item["key"] for item in general}
    assert "experience_value_tiers" not in {item["key"] for item in specific}
    assert "min_percentage_budget" in {item["key"] for item in general}
    assert "specific_min_percentage" in {item["key"] for item in specific}


VILLA_MARIA_SPECIFIC_AREA = """
FASE I - ESTUDIO, DISEÑOS, OBTENCIÓN DE PERMISOS DEL PROYECTO
ESPECIFICA
Con la sumatoria de uno o hasta maximo dos (2) de los contratos validos aportados como
experiencia general deben contemplar consultoria a un proyecto con un area que sea igual o superior al (60%)
del total de metros cuadrados del proceso de seleccion, el cual corresponde a 2396 m2
FASE II – MANTENIMIENTO, MEJORAMIENTO Y ADECUACION PARQUE Y ESPACIO PUBLICO
ESPECIFICA
Con la sumatoria de uno o hasta maximo dos (2) de los contratos validos aportados como experiencia general
deben contemplar un area sea igual o superior al (70%) del total de metros cuadrados del proceso de seleccion,
el cual corresponde a 2396 m2.
"""


def test_extract_villa_maria_specific_area_phases():
    specific = extract_experiencia_especifica(VILLA_MARIA_SPECIFIC_AREA, "pliego_condiciones", None)
    keys = {item["key"] for item in specific}
    assert "specific_area_phases" in keys
    assert "contracts_minimum" in keys
    assert "specific_min_percentage" not in keys
    assert "activity_codes" not in keys
    assert "experience_value_tiers" not in keys

    phases = next(item for item in specific if item["key"] == "specific_area_phases")["value"]
    assert len(phases) == 2
    assert phases[0]["area_percentage"] == 60.0
    assert phases[1]["area_percentage"] == 70.0
    assert phases[0]["minimum_m2"] == 1437.6
    assert phases[1]["minimum_m2"] == 1677.2


def test_extract_tier_table_without_section_number():
    text = """
    Valor minimo a certificar (como % del Presupuesto Oficial de obra expresado en SMMLV)
    De 1 hasta 2 75 %
    De 3 hasta 4 120 %
    Hasta 5 150 %
    Minimo uno (1) y maximo cinco (5) contratos
    """
    general = extract_experiencia_general(text, "pliego_condiciones", None)
    keys = {item["key"] for item in general}
    assert "experience_value_tiers" in keys
    assert "contracts_minimum" in keys


def test_sanitize_especifica_removes_po_tier_fields():
    from app.services.tender_requirements.llm_extraction import sanitize_experiencia_especifica_items

    items = [
        {"key": "specific_area_phases", "display_value": "Fase I", "value": []},
        {
            "key": "specific_min_percentage",
            "display_value": "120% del Presupuesto Oficial para contratos de experiencia especifica.",
            "value": 120,
        },
        {
            "key": "contracts_minimum",
            "display_value": "Minimo 1 y maximo 5 contratos para la experiencia general.",
            "value": None,
        },
        {
            "key": "activity_codes",
            "display_value": "Segmentos [72] y [81]",
            "value": ["72", "81"],
        },
    ]
    sanitized = sanitize_experiencia_especifica_items(items)
    keys = {item["key"] for item in sanitized}
    assert keys == {"specific_area_phases"}


def test_normalize_text_strips_accents():
    assert normalize_text("Últimos 5 años") == "ultimos 5 anos"


def test_extract_experiencia_general_percentage_and_years():
    items = extract_experiencia_general(PLIEGO_SAMPLE, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "min_percentage_budget" in keys
    assert "time_window_years" in keys
    pct = next(item for item in items if item["key"] == "min_percentage_budget")
    assert pct["value"] == 30


def test_extract_experiencia_general_accreditation():
    items = extract_experiencia_general(PLIEGO_SAMPLE, "pliego_condiciones", None)
    assert any(item["key"] == "accreditation_method" for item in items)


def test_extract_experiencia_especifica_scope_and_codes():
    items = extract_experiencia_especifica(ANEXO_SAMPLE, "anexo_tecnico", None)
    keys = {item["key"] for item in items}
    assert "specific_scope" in keys
    assert "activity_codes" in keys
    codes = next(item for item in items if item["key"] == "activity_codes")
    assert "72141100" in codes["value"]


def test_extract_indicadores_financieros_liquidez():
    items = extract_indicadores_financieros(PLIEGO_SAMPLE, "pliego_condiciones", None)
    liquidez = next((item for item in items if item["key"] == "liquidez_corriente"), None)
    assert liquidez is not None
    assert liquidez["value"]["threshold"] == 1.0


def test_extract_indicadores_financieros_puntaje():
    items = extract_indicadores_financieros(PLIEGO_SAMPLE, "pliego_condiciones", None)
    assert any(item["key"] == "qualification_score" for item in items)


CCE_INTERVENTORIA_FINANCIAL = """
3.5 CAPACIDAD FINANCIERA
Los Proponentes deberan acreditar los siguientes indicadores en los terminos senalados en la
Matriz 2 - Indicadores financieros y organizacionales y bajo las condiciones del numeral 3.7.1.

El Proponente que no tiene pasivos corrientes esta habilitado respecto del indice de liquidez.
El Proponente que no tiene gastos de intereses esta habilitado respecto de la razon de cobertura
de intereses, siempre y cuando la Utilidad Operacional sea igual o mayor a cero (0).

3.6 CAPITAL DE TRABAJO
Para el Proceso de Contratacion los Proponentes deberan acreditar:
CT = AC - PC >= CTd
CTd = (POE - Anticipo o Pago anticipado) x 25%
Para procesos cuyo plazo estimado de ejecucion del contrato sea menor a doce (12) meses.

3.7 CAPACIDAD ORGANIZACIONAL
Los Proponentes deberan acreditar los indicadores en la Matriz 2 - Indicadores financieros
y organizacionales.

3.7.1 ACREDITACION DE LA CAPACIDAD FINANCIERA Y ORGANIZACIONAL
La evaluacion financiera se efectuara a partir de la informacion contenida en el Registro Unico
de Proponentes vigente y en firme al momento de su presentacion.
"""


TRADITIONAL_PLIEGO_FINANCIAL = """
3.3 SOLVENCIA ECONOMICA Y FINANCIERA
El indice de liquidez corriente (activo corriente / pasivo corriente) debera ser mayor o igual a 1.2.
El endeudamiento (pasivo total / activo total) debera ser menor o igual a 70%.
La cobertura de intereses (utilidad operacional / gastos por intereses) mayor o igual a 1.5.
El capital de trabajo (activo corriente - pasivo corriente) mayor o igual a $ 116.000.000.
El patrimonio (activo total - pasivo total) debera ser mayor o igual a $ 250.000.000.
El proponente que no tiene pasivos corrientes esta habilitado respecto del indice de liquidez.
El proponente que no tiene gastos de intereses esta habilitado respecto de la cobertura de intereses.
Acreditacion mediante Registro Unico de Proponentes (RUP) vigente.
"""


def test_extract_traditional_pliego_financial_without_liquidez_label():
    """OCR pliegos often omit the 'liquidez corriente' label and only show AC/PC."""
    text = """
    3.3 SOLVENCIA ECONOMICA Y FINANCIERA
    activo corriente / pasivo corriente mayor o igual a 1.2 endeudamiento pasivo total / activo total
    menor o igual a 70% cobertura de intereses utilidad operacional / gastos por intereses mayor o igual a 1.5
    capital de trabajo activo corriente - pasivo corriente mayor o igual a $ 116.000.000
    patrimonio activo total - pasivo mayor o igual a $ 250.000.000
    """
    items = extract_indicadores_financieros(text, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "liquidez_corriente" in keys
    assert "endeudamiento" in keys
    assert "capital_trabajo" in keys
    assert "patrimonio_minimo" in keys

    liquidez = next(item for item in items if item["key"] == "liquidez_corriente")
    assert liquidez["value"]["threshold"] == 1.2

    endeudamiento = next(item for item in items if item["key"] == "endeudamiento")
    assert endeudamiento["value"]["threshold"] == 0.7

    capital = next(item for item in items if item["key"] == "capital_trabajo")
    assert capital["value"]["min_amount_cop"] == 116_000_000

    patrimonio = next(item for item in items if item["key"] == "patrimonio_minimo")
    assert patrimonio["value"]["min_amount_cop"] == 250_000_000


def test_extract_traditional_pliego_financial_indicators():
    items = extract_indicadores_financieros(TRADITIONAL_PLIEGO_FINANCIAL, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "liquidez_corriente" in keys
    assert "endeudamiento" in keys
    assert "cobertura_intereses" in keys
    assert "capital_trabajo" in keys
    assert "patrimonio_minimo" in keys
    assert "financial_exemptions" in keys

    liquidez = next(item for item in items if item["key"] == "liquidez_corriente")
    assert liquidez["value"]["threshold"] == 1.2

    endeudamiento = next(item for item in items if item["key"] == "endeudamiento")
    assert endeudamiento["value"]["operator"] == "<="
    assert endeudamiento["value"]["threshold"] == 0.7

    cobertura = next(item for item in items if item["key"] == "cobertura_intereses")
    assert cobertura["value"]["threshold"] == 1.5

    capital = next(item for item in items if item["key"] == "capital_trabajo")
    assert capital["value"]["min_amount_cop"] == 116_000_000

    patrimonio = next(item for item in items if item["key"] == "patrimonio_minimo")
    assert patrimonio["value"]["min_amount_cop"] == 250_000_000


def test_extract_cce_interventoria_financial_indicators():
    items = extract_indicadores_financieros(CCE_INTERVENTORIA_FINANCIAL, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "financial_summary" in keys
    assert "liquidez_corriente" in keys
    assert "endeudamiento" in keys
    assert "cobertura_intereses" in keys
    assert "capital_trabajo" in keys
    assert "accreditation_method" in keys
    assert "financial_exemptions" in keys
    assert "matriz_2_reference" in keys
    assert "rentabilidad_patrimonio" in keys
    assert "rentabilidad_activo" in keys

    capital = next(item for item in items if item["key"] == "capital_trabajo")
    assert capital["value"]["ctd_percentage"] == 25.0
    assert "CTd" in capital["display_value"]


OBRA_DOCUMENTO_BASE_FINANCIAL = """
CAPITULO III. REQUISITOS HABILITANTES Y SU VERIFICACION
3.6. CAPACIDAD FINANCIERA
Los Proponentes deberan acreditar los siguientes indicadores en los terminos senalados en la Matriz
2 – Indicadores financieros y organizacionales:
Indicador Formula
Liquidez Activo Corriente / Pasivo Corriente
Nivel de Endeudamiento Pasivo Total / Activo Total
Razon de Cobertura de Intereses Utilidad Operacional / Gastos Interes
3.7. CAPITAL DE TRABAJO
CT = AC - PC >= CTd
CTd = (POE - Anticipo o Pago anticipado) x 33%
3.8. PATRIMONIO
no se solicitara el Patrimonio como un indicador de capacidad financiera adicional.
3.9. CAPACIDAD ORGANIZACIONAL
Los Proponentes deben acreditar los siguientes indicadores en los terminos senalados en la Matriz 2:
Indicador Formula
Rentabilidad sobre Patrimonio (Roe) Utilidad Operacional / Patrimonio
Rentabilidad del Activo (Roa) Utilidad Operacional / Activo Total
3.10. ACREDITACION DE LA CAPACIDAD FINANCIERA Y ORGANIZACIONAL
La evaluacion financiera y organizacional se efectuara a partir de la informacion contenida en el RUP.
CAPITULO IV. CRITERIOS DE EVALUACION
"""


def test_extract_obra_documento_base_includes_organizational_indicators():
    items = extract_indicadores_financieros(OBRA_DOCUMENTO_BASE_FINANCIAL, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "liquidez_corriente" in keys
    assert "endeudamiento" in keys
    assert "cobertura_intereses" in keys
    assert "capital_trabajo" in keys
    assert "rentabilidad_patrimonio" in keys
    assert "rentabilidad_activo" in keys
    assert "patrimonio_minimo" not in keys

    roe = next(item for item in items if item["key"] == "rentabilidad_patrimonio")
    assert roe["value"]["threshold_note"] == "Umbrales según Matriz 2 (ver anexo del proceso)"


OBRA_DOCUMENTO_BASE_RESIDUAL = """
3.11 CAPACIDAD RESIDUAL
El Proponente sera habil si su capacidad residual es mayor o igual a la capacidad residual de Proceso
de Contratacion (CRPC). Asi: CRP >= CRPC
3.11.1 CALCULO DE LA CAPACIDAD RESIDUAL DEL PROCESO DE CONTRATACION (CRPC)
Si el plazo estimado del contrato es menor o igual a 12 meses, el calculo de la CRPC debera tener
en cuenta el siguiente proceso: CRPC=POE-Anticipo o pago anticipado
Si el plazo estimado del contrato es mayor a 12 meses el calculo de la CRPC debera tener en cuenta
el siguiente proceso: CRPC=POE-Anticipo o pago anticipado / Plazo estimado (meses) * 12
3.11.2 CALCULO DE LA CAPACIDAD RESIDUAL DEL PROPONENTE (CRP)
La capacidad residual del Proponente se calculara de la siguiente manera:
CRP=CO*[(E+CT+CF)/100]-SCE
La CRP del Proponente plural es la suma de la capacidad residual de cada uno de sus miembros
A cada uno de los factores se le asigna maximo el siguiente puntaje:
Factor Puntaje maximo
Experiencia (E) 120
Capacidad financiera (CF) 40
Capacidad tecnica (CT) 40
La Capacidad de Organizacion (CO) no tiene asignacion de puntaje en la formula porque constituye
un factor multiplicador de los demas factores.
E. Saldos Contratos en Ejecucion (SCE):
El Proponente debe presentar el Formato 5 - Capacidad residual suscrito por su representante legal
Para acreditar el factor (E), el proponente debe diligenciar el Formato 5 - Capacidad residual
4. CAPITULO IV. CRITERIOS DE EVALUACION
"""


def test_extract_capacidad_residual_obra_documento_base():
    items = extract_capacidad_residual(OBRA_DOCUMENTO_BASE_RESIDUAL, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "residual_summary" in keys
    assert "habilitante_rule" in keys
    assert "crpc_formula" in keys
    assert "crp_formula" in keys
    assert "factor_experiencia" in keys
    assert "factor_capacidad_financiera" in keys
    assert "factor_capacidad_tecnica" in keys
    assert "factor_organizacion" in keys
    assert "sce" in keys
    assert "proponente_plural" in keys
    assert "accreditation_formato_5" in keys

    experiencia = next(item for item in items if item["key"] == "factor_experiencia")
    assert experiencia["value"]["max_score"] == 120
    cf = next(item for item in items if item["key"] == "factor_capacidad_financiera")
    assert cf["value"]["max_score"] == 40
    ct = next(item for item in items if item["key"] == "factor_capacidad_tecnica")
    assert ct["value"]["max_score"] == 40

    crpc = next(item for item in items if item["key"] == "crpc_formula")
    assert crpc["value"]["formula_type"] == "both"


def test_extract_capacidad_residual_empty_without_section():
    items = extract_capacidad_residual(OBRA_DOCUMENTO_BASE_FINANCIAL, "pliego_condiciones", None)
    assert items == []


def test_build_tender_requirements_includes_residual_for_obra():
    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.OBRA",
        portfolio_id="portfolio-1",
        source=TenderSource.SECOP_II,
        entity_name="Entity",
        object_text="Construccion de infraestructura vial",
        contract_modality="Licitación pública Obra Pública",
        state="Publicado",
        process_url="https://example.com",
    )
    tender.documents = []
    payload = build_tender_requirements(tender)
    section_keys = [section["key"] for section in payload["sections"]]
    assert "capacidad_residual" in section_keys


def test_build_tender_requirements_excludes_residual_for_interventoria():
    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.INT",
        portfolio_id="portfolio-1",
        source=TenderSource.SECOP_II,
        entity_name="Entity",
        object_text="Interventoria tecnica de obra",
        contract_modality="Licitación pública Obra Pública",
        state="Publicado",
        process_url="https://example.com",
    )
    tender.documents = []
    payload = build_tender_requirements(tender)
    section_keys = [section["key"] for section in payload["sections"]]
    assert "capacidad_residual" not in section_keys


MATRIZ_2_INTERVENTORIA_SAMPLE = """
MATRIZ 2 – INDICADORES FINANCIEROS Y ORGANIZACIONALES
Índices de Capacidad Financiera y Organizacionales para Mipyme.
Indicador Valor concertado Rango 1 Valor concertado Rango 2
Índice de liquidez ≥1,1 ≥1,2
Índice de endeudamiento ≤ 0,65 ≤ 0,70
Razón de cobertura de intereses ≥1,5 ≥ 1
Capital de trabajo Definido en el documento base Definido en el documento base
Rentabilidad del patrimonio ≥ 0,02 ≥ 0,03
Rentabilidad del activo ≥ 0,01 ≥ 0,02
Índices de Capacidad Financiera y Organizacionales para los demás Proponentes.
Los Proponentes que NO demuestren la condición de Mipyme acreditarán los siguientes indicadores:
Indicador Valor concertado Rango 1 Valor concertado Rango 2
Índice de liquidez ≥1,2 ≥1,3
Índice de endeudamiento ≤ 0,65 ≤ 0,70
Razón de cobertura de intereses ≥1,5 ≥ 1
Capital de trabajo Definido en los Pliegos Tipo Definido en los Pliegos Tipo
Rentabilidad del patrimonio ≥ 0,03 ≥ 0,04
Rentabilidad del activo ≥ 0,02 ≥ 0,03
"""


def test_extract_matriz_2_indicadores_document_thresholds():
    items = extract_indicadores_financieros(
        MATRIZ_2_INTERVENTORIA_SAMPLE,
        "indicadores_financieros",
        None,
    )
    keys = {item["key"] for item in items}
    assert "liquidez_corriente" in keys
    assert "endeudamiento" in keys
    assert "rentabilidad_patrimonio" in keys
    assert "matriz_2_reference" not in keys

    liquidez = next(item for item in items if item["key"] == "liquidez_corriente")
    assert liquidez["value"]["threshold"] == 1.2
    assert liquidez["value"]["threshold_by_range"]["rango_2"]["threshold"] == 1.3
    assert "(R1)" in liquidez["display_value"]
    assert "(R2)" in liquidez["display_value"]
    assert liquidez["source_document"] == "indicadores_financieros"

    endeudamiento = next(item for item in items if item["key"] == "endeudamiento")
    assert endeudamiento["value"]["threshold"] == 0.65


def test_merge_matriz_with_pliego_financial_items():
    matriz_items = extract_indicadores_financieros(
        MATRIZ_2_INTERVENTORIA_SAMPLE,
        "indicadores_financieros",
        None,
    )
    pliego_items = extract_indicadores_financieros(
        CCE_INTERVENTORIA_FINANCIAL,
        "pliego_condiciones",
        None,
    )
    merged = merge_financial_requirement_items(
        matriz_items,
        pliego_items,
        has_matriz_document=True,
    )
    keys = {item["key"] for item in merged}
    assert "matriz_2_reference" not in keys
    assert "capital_trabajo" in keys

    liquidez = next(item for item in merged if item["key"] == "liquidez_corriente")
    assert liquidez["value"]["threshold"] == 1.2
    assert "Umbrales según Matriz 2" not in liquidez["display_value"]

    capital = next(item for item in merged if item["key"] == "capital_trabajo")
    assert capital["value"]["ctd_percentage"] == 25.0


IDRD_MATRIZ_PROSE_SAMPLE = """
indice de liquidez mayor o igual a 1,1 indice de endeudamiento menor o igual a 70%
razon cobertura de intereses mayor o igual a 1,0 capital de trabajo mayor o igual a $ 990.000.000
rentabilidad del patrimonio mayor o igual a 2% rentabilidad del activo mayor o igual a 1%
indice de liquidez mayor o igual a 1,2 indice de endeudamiento menor o igual a 70%
razon cobertura de intereses mayor o igual a 1,0 capital de trabajo grupo mayor o igual a $ 990.000.000
rentabilidad del patrimonio mayor o igual a 4% rentabilidad del activo mayor o igual a 2%
"""


def test_extract_matriz_prose_indicadores_idrd_style():
    items = extract_indicadores_financieros(
        IDRD_MATRIZ_PROSE_SAMPLE,
        "indicadores_financieros",
        None,
    )
    liquidez = next(item for item in items if item["key"] == "liquidez_corriente")
    assert liquidez["value"]["threshold"] == 1.1
    assert liquidez["value"]["threshold_by_range"]["rango_2"]["threshold"] == 1.2
    assert liquidez["source_document"] == "indicadores_financieros"

    endeudamiento = next(item for item in items if item["key"] == "endeudamiento")
    assert endeudamiento["value"]["threshold"] == 0.7

    capital = next(item for item in items if item["key"] == "capital_trabajo")
    assert capital["value"]["min_amount_cop"] == 990_000_000

    roe = next(item for item in items if item["key"] == "rentabilidad_patrimonio")
    assert roe["value"]["threshold_by_range"]["rango_2"]["threshold"] == 0.04


def test_requirements_cache_is_stale_when_matriz_exists_but_placeholders_remain():
    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.TEST",
        reference="IDRD-SG-LP-020-2026",
        source="secop_ii",
        entity_name="Entity",
        object_text="Test",
        state="Publicado",
        process_url="https://example.com",
    )
    tender.documents = [
        TenderDocument(
            id=uuid4(),
            tender_id=tender.id,
            external_document_id="matriz-1",
            document_type="indicadores_financieros",
            file_name="Matriz 2 - Indicadores Financieros y Organizacionales.docx",
            file_path="path/matriz.docx",
            extension="docx",
            download_url="https://example.com",
        )
    ]
    cached_payload = {
        "sections": [
            {
                "key": "indicadores_financieros",
                "items": [
                    {
                        "key": "liquidez_corriente",
                        "source_document": "pliego_condiciones",
                        "display_value": "AC / PC — Umbrales según Matriz 2 (ver anexo del proceso)",
                        "value": {"threshold_note": "Umbrales según Matriz 2 (ver anexo del proceso)"},
                    }
                ],
            }
        ]
    }
    assert requirements_cache_is_stale(tender, cached_payload) is True


CCE_LEGAL_PLIEGO_SAMPLE = """
CAPITULO III REQUISITOS DE PARTICIPACION
3.2 CAPACIDAD JURIDICA
Los interesados podran participar como proponentes bajo alguna de las siguientes modalidades.
El Proponente debera acreditar capacidad juridica y no estar en inhabilidad, incompatibilidad
ni conflicto de interes. No debera figurar en el boletin de responsables fiscales de la Contraloria.
Debera presentar certificado REDAM de no estar inhabilitado por deudas alimentarias.
Las personas juridicas deberan informar sociedades controlantes y contraladas (Decreto 1600 de 2024).
La Entidad consultara antecedentes judiciales, fiscales, disciplinarios y RNMC.

3.3 EXISTENCIA Y REPRESENTACION LEGAL
Persona natural: cedula de ciudadania, cedula de extranjeria o pasaporte.
Persona juridica: certificado de existencia y representacion legal expedido por Camaras de Comercio
con vigencia no mayor a treinta (30) dias calendario anteriores a la fecha de cierre.
El objeto social debera ser compatible con el objeto del contrato.
Proponente Plural: diligenciara Formato 2 y registrara la UT o consorcio en SECOP II.

3.4 SEGURIDAD SOCIAL Y APORTES LEGALES
Persona juridica: Formato 5 - Declaracion de pagos al Sistema de Seguridad Social.
Persona natural: afiliacion a los sistemas de seguridad social en salud y pensiones.

2.1 CARTA DE PRESENTACION DE LA OFERTA
Formato 1 - Carta de presentacion de la oferta firmada por el representante legal.
Matricula profesional vigente expedida por el COPNIA segun Ley 842 de 2003.
Los proponentes podran actuar mediante apoderado con poder otorgado en legal forma.

El certificado del Registro Unico de Proponentes (RUP) debera tener fecha de expedición
no mayor a treinta (30) dias calendario anteriores a la fecha de cierre.
Garantia de seriedad de la oferta junto con la propuesta.
Proponentes extranjeros sin domicilio ni sucursal: Formato 4.
"""


def test_extract_requisitos_legales_rup():
    items = extract_requisitos_legales(PLIEGO_SAMPLE, "pliego_condiciones", None)
    combined = " ".join(item["display_value"] for item in items).lower()
    assert "rup" in combined
    assert "capacidad juridica" in combined or "capacidad_juridica" in combined


def test_extract_requisitos_legales_license():
    items = extract_requisitos_legales(PLIEGO_SAMPLE, "pliego_condiciones", None)
    combined = " ".join(item["display_value"] for item in items).lower()
    assert "licencia" in combined or "construccion" in combined


def test_extract_cce_legal_habilitantes():
    items = extract_requisitos_legales(CCE_LEGAL_PLIEGO_SAMPLE, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert any(key.startswith("capacidad_juridica_check_") for key in keys)
    assert any(key.startswith("existencia_representacion_check_") for key in keys)
    assert any(key.startswith("seguridad_social_check_") for key in keys)
    assert "rup_certificate_validity" in keys
    assert len(items) <= 14
    capacidad_items = [item for item in items if item["key"].startswith("capacidad_juridica_check_")]
    combined = " ".join(item["display_value"] for item in capacidad_items).lower()
    assert "redam" in combined


INVIAS_PLIEGO_SAMPLE = """
3.8.1 EXIGENCIA MINIMA DE LA EXPERIENCIA DEL PROPONENTE
contratos aportados como experiencia es mayor o igual al cien por ciento (100 %) respecto del valor
total del Presupuesto Oficial establecido para el Proceso de Contratacion expresado en SMMLV.
Formato 3 - Experiencia y Matriz 1 - Experiencia.

De conformidad con lo anterior, los requisitos de experiencia son:
• EXPERIENCIA GENERAL : INTERVENTORIA A LA CONSTRUCCION O RECONSTRUCCION
O MEJORAMIENTO EN PAVIMENTO ASFALTICO O CONCRETO HIDRAULICO DE VIAS PRIMARIAS
• EXPERIENCIA ESPECIFICA: Por lo menos uno (1) de los contratos validos aportados como
experiencia general sea de un valor correspondiente a por lo menos el 70% del valor de
PRESUPUESTO OFICIAL (PO) del presente proceso de contratacion.
"""


def test_invias_pliego_extracts_general_and_specific_experience():
    general = extract_experiencia_general(INVIAS_PLIEGO_SAMPLE, "pliego_condiciones", None)
    specific = extract_experiencia_especifica(INVIAS_PLIEGO_SAMPLE, "pliego_condiciones", None)

    general_keys = {item["key"] for item in general}
    assert "requirement_description" in general_keys
    assert "min_percentage_budget" in general_keys
    assert any(item["value"] == 100 for item in general if item["key"] == "min_percentage_budget")

    specific_keys = {item["key"] for item in specific}
    assert "specific_scope" in specific_keys
    assert "specific_min_percentage" in specific_keys
    assert any(item["value"] == 70 for item in specific if item["key"] == "specific_min_percentage")


def test_build_tender_requirements_without_documents():
    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.TEST",
        portfolio_id="portfolio-1",
        source=TenderSource.SECOP_II,
        entity_name="Entity",
        object_text="Obra vial",
        state="Publicado",
        process_url="https://example.com",
    )
    tender.documents = []
    payload = build_tender_requirements(tender)
    assert payload["sections"]
    assert all(
        section["status"] == "documento_no_disponible"
        for section in payload["sections"]
    )


def test_build_tender_requirements_section_keys():
    tender = Tender(
        id=uuid4(),
        external_id="CO1.REQ.TEST2",
        portfolio_id="portfolio-1",
        source=TenderSource.SECOP_II,
        entity_name="Entity",
        object_text="Obra vial",
        state="Publicado",
        process_url="https://example.com",
    )
    tender.documents = []
    payload = build_tender_requirements(tender)
    section_keys = [section["key"] for section in payload["sections"]]
    assert section_keys == [
        "experiencia_general",
        "experiencia_especifica",
        "indicadores_financieros",
        "requisitos_legales",
        "sistema_puntos",
    ]


LP_INFRA_SCORING_TABLE_SAMPLE = """
CAPITULO IV. CRITERIOS DE EVALUACION, ASIGNACION DE PUNTAJE Y CRITERIOS DE DESEMPATE
La Entidad calificara las ofertas con los siguientes puntajes:
Concepto
Oferta economica
Puntaje maximo
48,5
Factor de calidad
30
Apoyo a la industria nacional
20
Vinculacion de personas con discapacidad
1
Emprendimientos y empresas de mujeres
0,25
Mipyme
0,25
Total
100
Las Entidades deberan reducir durante la evaluacion de las ofertas dos (2) puntos a los
Proponentes que se les haya impuesto una o mas multas.
4.1 OFERTA ECONOMICA
Para calificar este factor se tendra en cuenta el valor total indicado en la propuesta economica.
4.2 FACTOR DE CALIDAD
La Entidad asignara el puntaje de factor de calidad como sigue.
CRITERIOS DE DESEMPATE
En caso de empate en el puntaje total deberan aplicarse las siguientes reglas:
a. Preferir la propuesta con mayor puntaje en factor de calidad.
CAPITULO V. GARANTIAS
"""


def test_extract_sistema_puntos_ignores_footer_noise_after_total():
    text = """
CAPITULO IV. CRITERIOS DE EVALUACION Y ASIGNACION DE PUNTAJE
Concepto Puntaje maximo Oferta economica 48,5 Factor de calidad 30
Apoyo a la industria nacional 20 Vinculacion de personas con discapacidad 1
Emprendimientos y empresas de mujeres 0,25 Mipyme 0,25 Total 100
documento base licitacion de obra publica de infraestructura social 68 version 2 del 21
de conformidad con el articulo 67 factor de calidad 30 apoyo a la industria nacional 20
tarjeta de circulacion y residencia occre 5
4.1 OFERTA ECONOMICA
4.2 FACTOR DE CALIDAD
"""
    items = extract_sistema_puntos(text, "pliego_condiciones", None)
    eval_keys = [
        item["key"]
        for item in items
        if item["value"].get("criterion_type") == "evaluacion" and item["key"] != "total_points"
    ]
    assert eval_keys == [
        "oferta_economica",
        "factor_calidad",
        "industria_nacional",
        "discapacidad",
        "empresas_mujeres",
        "mipyme",
    ]
    assert sum(
        float(item["value"]["max_points"])
        for item in items
        if item["key"] != "total_points" and item["value"].get("criterion_type") == "evaluacion"
    ) == 100


def test_extract_sistema_puntos_keeps_mipyme_when_section_41_splits_table():
    text = """
CAPITULO IV. CRITERIOS DE EVALUACION
Concepto
Puntaje maximo
Oferta economica
48,5
Factor de calidad
30
Apoyo a la industria nacional
20
Vinculacion de personas con discapacidad
1
Emprendimientos y empresas de mujeres
0,25
4.1 OFERTA ECONOMICA
Para calificar este factor...
Mipyme domiciliada en Colombia
0,25
Total
100
"""
    items = extract_sistema_puntos(text, "pliego_condiciones", None)
    keys = [item["key"] for item in items if item["value"].get("criterion_type") == "evaluacion"]
    assert "mipyme" in keys
    assert sum(
        float(item["value"]["max_points"])
        for item in items
        if item["key"] != "total_points" and item["value"].get("criterion_type") == "evaluacion"
    ) == 100


def test_extract_sistema_puntos_accepts_unknown_table_criteria():
    text = """
CAPITULO IV. CRITERIOS DE EVALUACION Y ASIGNACION DE PUNTAJE
Concepto Puntaje maximo
Criterio especial Alpha 15
Otro factor Beta 5
Total 20
"""
    items = extract_sistema_puntos(text, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "criterio_especial_alpha" in keys
    assert "otro_factor_beta" in keys
    total = next(item for item in items if item["key"] == "total_points")
    assert total["value"]["max_points"] == 20


def test_extract_sistema_puntos_lp_infra_summary_table():
    items = extract_sistema_puntos(LP_INFRA_SCORING_TABLE_SAMPLE, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "oferta_economica" in keys
    assert "factor_calidad" in keys
    assert "industria_nacional" in keys
    assert "total_points" in keys
    assert "48_5_factor_de_calidad" not in keys

    oferta = next(item for item in items if item["key"] == "oferta_economica")
    assert oferta["value"]["max_points"] == 48.5

    eval_points = sum(
        float(item["value"]["max_points"])
        for item in items
        if item["value"].get("criterion_type") == "evaluacion"
        and item["key"] != "total_points"
    )
    assert eval_points == 100


CMA_SCORING_TABLE_SAMPLE = """
CAPITULO IV. CRITERIOS DE EVALUACION, ASIGNACION DE PUNTAJE Y CRITERIOS DE DESEMPATE
La Entidad calificara las ofertas que hayan cumplido los requisitos habilitantes con los siguientes
criterios de evaluacion y puntaje:
Concepto
Puntaje maximo
Experiencia del Proponente
67,50
Equipo de trabajo (Personal Clave Evaluable)
10
Factor de sostenibilidad
1
Apoyo a la industria nacional
20
Vinculacion de personas con discapacidad
1
Emprendimientos y empresas de mujeres
0,25
Mipyme
0,25
Total
100
Las Entidades deben consultar y analizar las anotaciones vigentes en el Registro Nacional de Obras
Civiles Inconclusas. En el evento que cuenten con alguna anotacion vigente se descontara un (1) punto.
Asimismo, las Entidades deberan reducir durante la evaluacion de las ofertas dos (2) puntos a los
Proponentes que se les haya impuesto una o mas multas.
4.1 FORMA DE VERIFICACION Y ASIGNACION DE PUNTAJE POR LA EXPERIENCIA DEL PROPONENTE
Para la asignacion de puntaje, se tomara el promedio de los contratos validos aportados.
4.2 EQUIPO DE TRABAJO (Personal Clave Evaluable)
La asignacion de puntaje relacionada con el Equipo de trabajo se realizara de la siguiente manera.
4.3 FACTOR DE SOSTENIBILIDAD
La Entidad asignara un (1) punto al Proponente que se comprometa con el Formato 12.
CRITERIOS DE DESEMPATE
En caso de empate en el puntaje total de dos o mas ofertas deberan aplicarse las siguientes reglas:
a. Preferir la propuesta presentada por el oferente que acredite la vinculacion en mayor numero de
personas en condicion de discapacidad.
b. Preferir la propuesta de la empresa de mujeres o emprendimiento.
CAPITULO V. PRESENTACION DE LAS OFERTAS
"""


def test_extract_sistema_puntos_cma_summary_table():
    items = extract_sistema_puntos(CMA_SCORING_TABLE_SAMPLE, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "experiencia" in keys
    assert "equipo_trabajo" in keys
    assert "industria_nacional" in keys
    assert "total_points" in keys
    assert "ajuste_obras_inconclusas" in keys
    assert "ajuste_multas" in keys
    assert any(item["key"].startswith("desempate") for item in items)

    experiencia = next(item for item in items if item["key"] == "experiencia")
    assert experiencia["value"]["max_points"] == 67.5
    assert experiencia["value"]["criterion_type"] == "evaluacion"

    total = next(item for item in items if item["key"] == "total_points")
    assert total["value"]["max_points"] == 100


CMA_CONCURSO_MERITOS_TABLE_SAMPLE = """
CAPITULO IV. CRITERIOS DE EVALUACION Y ASIGNACION DE PUNTAJE
criterio de evaluacion puntaje maximo
evaluacion y ponderacion de la experiencia especifica del proponente 40 puntos
evaluacion y ponderacion del personal de equipo de trabajo 45 puntos
generacion de empleo territorial 2.5 puntos
incentivo a la industria nacional 10 puntos
puntaje adicional para empleadores de personas con discapacidad 2 puntos
emprendimiento y empresas de mujeres 0.25 puntos
mipymes 0.25 puntos
puntaje total 100 puntos
CAPITULO V. PRESENTACION DE LAS OFERTAS
"""


def test_extract_sistema_puntos_cma_concurso_meritos_puntos_suffix():
    items = extract_sistema_puntos(CMA_CONCURSO_MERITOS_TABLE_SAMPLE, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert keys == {
        "experiencia",
        "equipo_trabajo",
        "empleo_territorial",
        "industria_nacional",
        "discapacidad",
        "empresas_mujeres",
        "mipyme",
        "total_points",
    }
    eval_sum = sum(
        float(item["value"]["max_points"])
        for item in items
        if item["key"] != "total_points" and item["value"].get("criterion_type") == "evaluacion"
    )
    assert eval_sum == 100


CCE_SCORING_PLIEGO_SAMPLE = """
CAPITULO IV. CRITERIOS DE EVALUACION Y ASIGNACION DE PUNTAJE

4.1 FORMA DE VERIFICACION Y ASIGNACION DE PUNTAJE POR LA EXPERIENCIA
El puntaje maximo asignado a la experiencia del proponente sera de cuarenta (40) puntos.
La experiencia se evaluara conforme a la Matriz 1 - Experiencia del proponente.

4.2 CAPACIDAD FINANCIERA
El puntaje maximo por capacidad financiera sera de veinticinco (25) puntos.
Los indicadores se evaluaran segun la Matriz 2 - Indicadores financieros y organizacionales.

4.3 CAPACIDAD ORGANIZACIONAL
El puntaje maximo por capacidad organizacional sera de quince (15) puntos.

El puntaje total de la evaluacion habilitante sera de cien (100) puntos.

CAPITULO V. PRESENTACION DE LAS OFERTAS
"""


def test_extract_sistema_puntos_cce_chapter_iv():
    items = extract_sistema_puntos(CCE_SCORING_PLIEGO_SAMPLE, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "experiencia" in keys
    assert "capacidad_financiera" in keys
    assert "capacidad_organizacional" in keys
    assert "total_points" in keys

    experiencia = next(item for item in items if item["key"] == "experiencia")
    assert experiencia["value"]["max_points"] == 40
    assert experiencia["display_value"] == "40 puntos"

    total = next(item for item in items if item["key"] == "total_points")
    assert total["value"]["max_points"] == 100


def test_extract_sistema_puntos_ignores_desempate_noise():
    text = CCE_SCORING_PLIEGO_SAMPLE + """
4.4 FACTORES DE DESEMPATE
Empresas de mujeres 0,25 MiPyme 0,25 total 100 puntos de desempate.
"""
    items = extract_sistema_puntos(text, "pliego_condiciones", None)
    assert not any(item["key"] == "otros_criterios" for item in items)
    assert any(item["key"] == "total_points" for item in items)


def test_extract_sistema_puntos_empty_without_chapter_iv():
    items = extract_sistema_puntos(PLIEGO_SAMPLE, "pliego_condiciones", None)
    assert any(item["key"] == "solvencia_economica" for item in items)
    solvencia = next(item for item in items if item["key"] == "solvencia_economica")
    assert solvencia["value"]["max_points"] == 20


def test_extract_sistema_puntos_chapter_iii_solvencia_only():
    text = """
3.3 SOLVENCIA ECONOMICA Y FINANCIERA
El indice de liquidez corriente debera ser mayor o igual a 1.2.
La calificacion por solvencia tendra un puntaje de veinte (20) puntos.
"""
    items = extract_sistema_puntos(text, "pliego_condiciones", None)
    assert len(items) == 1
    assert items[0]["key"] == "solvencia_economica"
    assert items[0]["value"]["max_points"] == 20


def test_extract_sistema_puntos_no_signals_returns_empty():
    text = "3.2 CAPACIDAD JURIDICA. El proponente debera acreditar capacidad juridica."
    assert extract_sistema_puntos(text, "pliego_condiciones", None) == []


def test_select_scoring_text_for_llm_finds_chapter_iii_solvencia():
    text = """
CAPITULO III. REQUISITOS DE PARTICIPACION
3.3 SOLVENCIA ECONOMICA Y FINANCIERA
El indice de liquidez corriente debera ser mayor o igual a 1.2.
La calificacion por solvencia tendra un puntaje de veinte (20) puntos.
CAPITULO IV. PRESENTACION DE LAS OFERTAS
"""
    excerpt = select_scoring_text_for_llm(None, text, 4000)
    assert "solvencia" in excerpt.lower()
    assert "puntaje" in excerpt.lower()
    assert "presentacion de las ofertas" not in excerpt.lower()


def test_select_scoring_text_for_llm_empty_without_scoring_signals():
    text = "3.2 CAPACIDAD JURIDICA. El proponente debera acreditar capacidad juridica."
    assert select_scoring_text_for_llm(None, text, 4000) == ""


def _eval_points_sum(items: list[dict]) -> float:
    total = 0.0
    for item in items:
        if item["key"] == "total_points":
            continue
        value = item.get("value") or {}
        if value.get("criterion_type") != "evaluacion":
            continue
        total += float(value["max_points"])
    return total


def test_reconcile_sistema_puntos_restores_missing_criteria_from_regex():
    regex_items = extract_sistema_puntos(LP_INFRA_SCORING_TABLE_SAMPLE, "pliego_condiciones", None)
    llm_items = [item for item in regex_items if item["key"] != "mipyme"]

    reconciled = reconcile_sistema_puntos_items(llm_items, regex_items=regex_items)
    assert _eval_points_sum(reconciled) == 100
    assert any(item["key"] == "mipyme" for item in reconciled)


def test_reconcile_sistema_puntos_drops_spurious_rows_over_total():
    regex_items = extract_sistema_puntos(LP_INFRA_SCORING_TABLE_SAMPLE, "pliego_condiciones", None)
    llm_items = list(regex_items)
    llm_items.insert(
        -1,
        {
            "key": "factor_calidad_extra",
            "label": "Factor de calidad duplicado",
            "value": {
                "max_points": 5.0,
                "assignment_rule": "",
                "criterion_type": "evaluacion",
            },
            "display_value": "5 puntos",
            "confidence": 0.6,
            "extraction_method": "llm",
        },
    )

    reconciled = reconcile_sistema_puntos_items(llm_items, regex_items=regex_items)
    assert _eval_points_sum(reconciled) == 100
    assert not any(item["key"] == "factor_calidad_extra" for item in reconciled)


def test_sistema_puntos_sum_mismatch_detects_bad_totals():
    items = [
        {
            "key": "experiencia",
            "value": {"max_points": 40.0, "criterion_type": "evaluacion"},
        },
        {
            "key": "total_points",
            "value": {"max_points": 100.0, "criterion_type": "evaluacion"},
        },
    ]
    assert sistema_puntos_sum_mismatch(items) is True


def test_select_scoring_fallback_text_finds_concurso_meritos_table():
    text = CMA_CONCURSO_MERITOS_TABLE_SAMPLE
    excerpt = select_scoring_fallback_text_for_llm(text, 4000)
    assert "experiencia especifica" in excerpt.lower()
    assert "puntaje total" in excerpt.lower()


def test_merge_scoring_fallback_items_keeps_desempate_from_failed_pass():
    failed = [
        {
            "key": "garbage",
            "label": "del decreto 1082 de 2015)",
            "value": {"max_points": 2.0, "criterion_type": "evaluacion"},
        },
        {
            "key": "total_points",
            "value": {"max_points": 100.0, "criterion_type": "evaluacion"},
        },
        {
            "key": "desempate_discapacidad",
            "label": "Desempate discapacidad",
            "value": {"max_points": None, "criterion_type": "desempate"},
        },
    ]
    fallback = extract_sistema_puntos(CMA_CONCURSO_MERITOS_TABLE_SAMPLE, "pliego_condiciones", None)
    merged = merge_scoring_fallback_items(failed, fallback)
    assert not sistema_puntos_sum_mismatch(merged)
    assert any(item["key"] == "experiencia" for item in merged)
    assert any(item["key"] == "desempate_discapacidad" for item in merged)
