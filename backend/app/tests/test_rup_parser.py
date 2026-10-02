"""US 1.11 — parse RUP text and reject empty/scanned PDFs."""
from app.services.rup_parser import extract_text_from_pdf_bytes, parse_rup_text, resolve_contractor_name

SAMPLE_RUP = """
CAMARA DE COMERCIO DE BOGOTA
CERTIFICADO DEL REGISTRO UNICO DE PROPONENTES
Razón social: CONSTRUCTORA VALLE SAS
NIT: 900123456-1
Fecha de expedición: 01/03/2026
Vigente hasta: 31/12/2026
Año corte: 2025
SMMLV 1.423.500

CAPACIDAD FINANCIERA
Índice de liquidez: 1,45
Índice de endeudamiento: 0,52
Cobertura de intereses: 3,10
Rentabilidad del patrimonio: 0,12
Rentabilidad del activo: 0,08
Capital de trabajo: 850000000

CAPACIDAD ORGANIZACIONAL
Personal: 42

EXPERIENCIA HABILITANTE

CONTRATO LP-014-2019
Objeto: Construcción y mejoramiento de la malla vial urbana en Cali
Entidad contratante: Instituto de Infraestructura de Cali
Valor: 120 SMMLV
Fecha de terminación: 15/11/2021
Categoría: Obras civiles viales
Departamento: Valle del Cauca
Municipio: Cali

CONTRATO CMA-008-2022
Objeto: Interventoría técnica de obras de pavimentación
Entidad contratante: INVÍAS
Valor contrato: 450000000
Fecha de finalización: 20/06/2023
Categoría: Interventoría
Departamento: Cundinamarca
"""


def _pdf_with_lines(lines: list[str]) -> bytes:
    ops = ["BT", "/F1 11 Tf", "50 750 Td"]
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        ops.append(f"({safe}) Tj")
        ops.append("0 -14 Td")
    ops.append("ET")
    stream = "\n".join(ops)
    stream_bytes = stream.encode("latin-1", errors="replace")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        ),
        (
            f"4 0 obj << /Length {len(stream_bytes)} >> stream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream endobj\n"
        ),
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]
    header = b"%PDF-1.4\n"
    body = b"".join(objects)
    xref_offset = len(header) + len(body)
    offsets = [0]
    cursor = 0
    for obj in objects:
        offsets.append(cursor)
        cursor += len(obj)
    xref = [b"xref\n0 6\n", b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset + len(header):010d} 00000 n \n".encode("ascii"))
    trailer = (
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode("ascii")
        + b"\n%%EOF\n"
    )
    return header + body + b"".join(xref) + trailer


def test_parse_sample_rup_extracts_contracts_and_capacity():
    result = parse_rup_text(SAMPLE_RUP, use_llm=False)

    assert result.text_insufficient is False
    assert result.looks_like_rup is True
    assert result.nit == "900123456-1"
    assert result.razon_social and "CONSTRUCTORA VALLE" in result.razon_social
    assert result.liquidity == 1.45
    assert result.indebtedness == 0.52
    assert result.organizational.get("staff_count") == 42
    assert len(result.contracts) == 2
    assert "malla vial" in result.contracts[0].object.lower()
    assert result.contracts[0].amount_smmlv == 120
    assert result.contracts[0].amount_cop == 120 * 1_423_500
    assert result.contracts[1].entity and "INV" in result.contracts[1].entity.upper()
    assert result.contracts[0].contract_kind == "ejecucion_obra"
    assert result.contracts[1].contract_kind == "interventoria"


def test_resolve_contractor_name_from_ccb_description():
    name = resolve_contractor_name(
        description="Contrato ejecutado para IDU (CONSORCIO SANTA MARIA 2014). Participación 42%."
    )
    assert name == "CONSORCIO SANTA MARIA 2014"


def test_resolve_contractor_name_does_not_use_login_name():
    assert (
        resolve_contractor_name(
            stored="RAFA",
            account_name="RAFA",
            razon_social="GV GARCIA VILLA S.A.S.",
        )
        == "GV GARCIA VILLA S.A.S."
    )


def test_insufficient_text_does_not_invent_contracts():
    result = parse_rup_text("RUP", use_llm=False)

    assert result.text_insufficient is True
    assert result.contracts == []
    assert any("escaneado" in warning.lower() for warning in result.warnings)


def test_non_rup_pdf_text_has_no_contracts():
    text = (
        "Este es un pliego de condiciones de una licitación pública. " * 8
        + "Objeto: suministro de papelería para la alcaldía."
    )
    result = parse_rup_text(text, use_llm=False)
    assert result.contracts == []
    assert result.looks_like_rup is False


CCB_RUP = """
CAMARA DE COMERCIO DE BOGOTA
31 DE MARZO DE 2025
CERTIFICADO DE INSCRIPCION Y CLASIFICACION REGISTRO UNICO DE PROPONENTES
IDENTIFICACION
QUE: CONSTRUCTORA ANDINA S.A.S.
NIT: 830118698 1
CERTIFICA:
INFORMACION FINANCIERA
FECHA DE CORTE DE LA INFORMACIÓN FINANCIERA: 31/12/2023
ACTIVO CORRIENTE: $4.501.799.399,00
PASIVO CORRIENTE: $2.769.645.477,00
CERTIFICA:
CAPACIDAD FINANCIERA
INDICE DE LIQUIDEZ: 1,62
INDICE DE ENDEUDAMIENTO: 0,57
RAZON DE CORBERTURA DE INTERESES: 6,50
CERTIFICA:
CAPACIDAD ORGANIZACIONAL
RENTABILIDAD DEL PATRIMONIO: 0,05
RENTABILIDAD DEL ACTIVO: 0,02
QUE EL INSCRITO SE CLASIFICO COMO:
MICROEMPRESA
CERTIFICA:
EXPERIENCIA
NUMERO CONSECUTIVO DEL REPORTE DEL CONTRATO EJECUTADO: 1
CONTRATO CELEBRADO POR:
CONSORCIO, UNION TEMPORAL O SOCIEDAD EN LAS CUALES EL PROPONENTE TENGA
O HAYA TENIDO PARTICIPACION
NOMBRE DEL CONTRATISTA: CONSORCIO VIAS URBANAS 2007
NOMBRE DEL CONTRATANTE: INSTITUTO DE DESARROLLO URBANO IDU
VALOR DEL CONTRATO EJECUTADO EXPRESADO EN SMMLV: 12.290,89
PORCENTAJE DE PARTICIPACION EN EL VALOR EJECUTADO EN CASO DE
CONSORCIOS Y UNIONES TEMPORALES: 25,00%
CONTRATO EJECUTADO IDENTIFICADO CON EL CLASIFICADOR DE BIENES Y
SERVICIOS EN EL TERCER NIVEL:
|SEGM|FAMI|CLAS|PROD|
| 72 | 10 | 33 | 00 |
| 81 | 10 | 15 | 00 |
NUMERO CONSECUTIVO DEL REPORTE DEL CONTRATO EJECUTADO: 2
CONTRATO CELEBRADO POR:
PROPONENTE
NOMBRE DEL CONTRATISTA: CONSTRUCTORA ANDINA S.A.S.
NOMBRE DEL CONTRATANTE: SECRETARIA DE EDUCACION DISTRITAL
VALOR DEL CONTRATO EJECUTADO EXPRESADO EN SMMLV: 836,56
CONTRATO EJECUTADO IDENTIFICADO CON EL CLASIFICADOR DE BIENES Y
SERVICIOS EN EL TERCER NIVEL:
|SEGM|FAMI|CLAS|PROD|
| 72 | 15 | 15 | 00 |
CONTRATOS EJECUTADOS
ENTIDAD CONTRATANTE: SECRETARIA DE EDUCACION DISTRITAL
MUNICIPIO: BOGOTÁ D.C.
NUMERO DEL CONTRATO: CTO-DE-OBRA-1129-2008
FECHA TERMINACION: 2009/10/26
VALOR INICIAL DEL CONTRATO EN PESOS: 152.842.156,00
VALOR FINAL DEL CONTRATO PAGADO (EN PESOS): 207.840.415,00
CLASIFICACION CONTRATO
10403 REMODELACIONES, CONSERVACION Y MANTENIMIENTO
FECHA DE INSCRIPCION: 2011/01/14
LA INFORMACIÓN REMITIDA POR LAS ENTIDADES ESTATALES
"""


def test_parse_ccb_rup_experience_and_capacity():
    result = parse_rup_text(CCB_RUP, use_llm=False)

    assert result.nit == "830118698-1"
    assert result.razon_social and "CONSTRUCTORA ANDINA" in result.razon_social
    assert result.issued_at and result.issued_at.year == 2025
    assert result.cut_year == 2023
    assert result.liquidity == 1.62
    assert result.indebtedness == 0.57
    assert result.interest_coverage == 6.5
    assert result.return_on_equity == 0.05
    assert result.working_capital == 4_501_799_399 - 2_769_645_477
    assert result.organizational.get("company_size") == "microempresa"

    consecutives = [c for c in result.contracts if (c.contract_number or "").startswith("RUP-")]
    assert len(consecutives) == 2
    first = consecutives[0]
    assert first.entity and "IDU" in first.entity
    assert first.participation_pct == 25
    assert first.amount_smmlv == 12290.89
    assert "VIAS URBANAS" in first.object
    assert first.contractor and "VIAS URBANAS" in first.contractor
    assert first.unspsc_codes == ["72103300", "81101500"]
    assert first.category is None
    assert first.contract_kind == "estudios_disenos_y_obra"

    reported = [c for c in result.contracts if c.contract_number == "CTO-DE-OBRA-1129-2008"]
    assert reported
    assert reported[0].completion_date.year == 2009
    assert reported[0].amount_cop == 207_840_415
    assert reported[0].contract_kind == "ejecucion_obra"
    assert reported[0].contractor and "CONSTRUCTORA ANDINA" in reported[0].contractor
    assert reported[0].unspsc_codes == []


def test_extract_text_from_generated_pdf():
    lines = [line.strip() for line in SAMPLE_RUP.splitlines() if line.strip()]
    content = _pdf_with_lines(lines)
    extracted = extract_text_from_pdf_bytes(content)
    assert "REGISTRO UNICO DE PROPONENTES" in extracted.upper().replace("Ú", "U")
    parsed = parse_rup_text(extracted, use_llm=False)
    assert parsed.nit == "900123456-1"
    assert len(parsed.contracts) >= 1
