"""Tests for tender requirements extraction (US 1.5)."""
from uuid import uuid4

from app.models.tender import Tender, TenderSource
from app.services.tender_requirements.regex_extraction import (
    extract_experiencia_especifica,
    extract_experiencia_general,
    extract_indicadores_financieros,
    extract_otros_requisitos,
    extract_requisitos_legales,
    merge_financial_requirement_items,
    normalize_text,
)
from app.services.tender_requirements.service import build_tender_requirements


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


def test_extract_requisitos_legales_rup():
    items = extract_requisitos_legales(PLIEGO_SAMPLE, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "rup_vigente" in keys
    assert "legal_capacity" in keys


def test_extract_requisitos_legales_license():
    items = extract_requisitos_legales(PLIEGO_SAMPLE, "pliego_condiciones", None)
    assert any(item["key"] == "specific_license" for item in items)


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


def test_extract_otros_requisitos_pyme():
    text = "El Proponente podra acreditar la calidad de Mipyme y de emprendimiento y empresa de mujeres."
    items = extract_otros_requisitos(text, "pliego_condiciones", None)
    keys = {item["key"] for item in items}
    assert "pyme" in keys
    assert "mujer" in keys
    assert "mocho" not in keys


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
        if section["key"] != "otros"
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
        "otros",
    ]
