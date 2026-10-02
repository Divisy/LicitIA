"""Hybrid regex + LLM extraction of contractor RUP certificates."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from io import BytesIO
from typing import Any, Optional

from app.config import settings
from app.core.logging import get_logger
from app.services.rup_contract_kind import classify_rup_experience_kind, extract_unspsc_codes

logger = get_logger(__name__)

MIN_TEXT_CHARS = 200
MAX_PDF_PAGES = 80
DEFAULT_SMMLV_COP = 1_423_500.0

_SMMLV_BY_YEAR = {
    2023: 1_160_000.0,
    2024: 1_300_000.0,
    2025: 1_423_500.0,
    2026: 1_423_500.0,
}

_SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_RUP_MARKERS = (
    "registro único de proponentes",
    "registro unico de proponentes",
    "registro unico de",
    " certificado rup",
    "capacidad financiera",
    "capacidad organizacional",
    "experiencia habilitante",
    "experiencia específica",
    "experiencia especifica",
    "numero consecutivo del reporte del contrato ejecutado",
    "cámara de comercio",
    "camara de comercio",
)

_CCB_STOP_LABELS = (
    r"NUMERO CONSECUTIVO DEL REPORTE",
    r"CONTRATO CELEBRADO POR",
    r"NOMBRE DEL CONTRATISTA",
    r"NOMBRE DEL CONTRATANTE",
    r"VALOR DEL CONTRATO",
    r"PORCENTAJE",
    r"CONTRATO EJECUTADO IDENTIFICADO",
    r"CERTIFICA:",
    r"CONTRATOS ADJUDICADOS",
    r"CONTRATOS EJECUTADOS",
    r"ENTIDAD CONTRATANTE",
    r"MUNICIPIO:",
    r"NUMERO DEL CONTRATO",
    r"FECHA ",
    r"CLASIFICACION CONTRATO",
    r"CLASIFICACION INDUSTRIAL",
)

_DATE_RE = re.compile(
    r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})|(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})"
)


@dataclass
class RupContract:
    contract_number: Optional[str] = None
    object: str = ""
    entity: Optional[str] = None
    contractor: Optional[str] = None
    amount_cop: Optional[float] = None
    amount_smmlv: Optional[float] = None
    participation_pct: Optional[float] = None
    completion_date: Optional[date] = None
    category: Optional[str] = None
    contract_kind: Optional[str] = None
    unspsc_codes: list[str] = field(default_factory=list)
    department: Optional[str] = None
    municipality: Optional[str] = None


@dataclass
class RupParseResult:
    nit: Optional[str] = None
    razon_social: Optional[str] = None
    camara: Optional[str] = None
    issued_at: Optional[date] = None
    valid_until: Optional[date] = None
    smmlv: Optional[float] = None
    liquidity: Optional[float] = None
    indebtedness: Optional[float] = None
    interest_coverage: Optional[float] = None
    return_on_equity: Optional[float] = None
    return_on_assets: Optional[float] = None
    working_capital: Optional[float] = None
    cut_year: Optional[int] = None
    organizational: dict[str, Any] = field(default_factory=dict)
    contracts: list[RupContract] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extracted_text_chars: int = 0
    looks_like_rup: bool = False
    text_insufficient: bool = False


def extract_text_from_pdf_bytes(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(content))
    chunks: list[str] = []
    for page in reader.pages[:MAX_PDF_PAGES]:
        text = page.extract_text() or ""
        if text.strip():
            chunks.append(text)
    return "\n".join(chunks)


def parse_rup_text(text: str, *, use_llm: bool = True) -> RupParseResult:
    cleaned = _normalize_rup_layout(text or "")
    result = RupParseResult(extracted_text_chars=len((text or "").strip()))
    if len((text or "").strip()) < MIN_TEXT_CHARS:
        result.text_insufficient = True
        result.warnings.append(
            "Este PDF parece escaneado; usa el certificado descargado de la cámara (texto seleccionable)."
        )
        return result

    lowered = cleaned.lower()
    result.looks_like_rup = any(marker in lowered for marker in _RUP_MARKERS)

    _apply_regex(cleaned, result)

    regex_complete = bool(result.contracts) and result.liquidity is not None
    if use_llm and settings.OPENAI_API_KEY and not regex_complete:
        try:
            llm_payload = _extract_with_llm(cleaned, result)
            if llm_payload:
                _merge_llm(result, llm_payload)
        except Exception as exc:
            logger.warning("RUP LLM extraction failed: %s", exc)
            result.warnings.append("No se pudo enriquecer el RUP con IA; se usó solo el texto estructurado.")

    smmlv = result.smmlv or _SMMLV_BY_YEAR.get(result.cut_year or 0, DEFAULT_SMMLV_COP)
    for contract in result.contracts:
        claimed = contract.amount_smmlv
        if claimed is not None and contract.participation_pct is not None:
            claimed = round(claimed * (contract.participation_pct / 100.0), 4)
            contract.amount_smmlv = claimed
        if contract.amount_cop is None and claimed is not None:
            contract.amount_cop = round(claimed * smmlv, 2)
        if not contract.contract_kind:
            contract.contract_kind = classify_rup_experience_kind(
                object_text=contract.object or "",
                category=contract.category or "",
                contract_number=contract.contract_number or "",
                unspsc_codes=contract.unspsc_codes,
            ).value
        if not (contract.object or "").strip():
            continue
        if not (contract.contractor or "").strip():
            contract.contractor = result.razon_social
    result.contracts = [c for c in result.contracts if (c.object or "").strip()]

    if not result.looks_like_rup and not result.contracts:
        result.warnings.append(
            "Este archivo no parece un certificado RUP. Sube el PDF que expide la cámara de comercio."
        )
    elif not result.contracts:
        result.warnings.append(
            "No se encontraron contratos inscritos en el RUP. Revisa que el PDF sea el certificado completo."
        )

    return result


def _parse_number(raw: str) -> Optional[float]:
    if not raw:
        return None
    value = raw.strip()
    if re.search(r"\d+\.\d{3}", value) and "," in value:
        value = value.replace(".", "").replace(",", ".")
    elif value.count(",") == 1 and value.count(".") == 0:
        value = value.replace(",", ".")
    elif value.count(".") > 1:
        value = value.replace(".", "")
    value = re.sub(r"[^\d.\-]", "", value)
    if value in {"", ".", "-"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_date(raw: str) -> Optional[date]:
    text = raw or ""
    match = _DATE_RE.search(text)
    if match:
        try:
            if match.group(1):
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            else:
                year, month, day = int(match.group(4)), int(match.group(5)), int(match.group(6))
            return date(year, month, day)
        except ValueError:
            pass
    spanish = re.search(
        r"(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚÑ]+)\s+DE\s+(\d{4})",
        text,
        re.IGNORECASE,
    )
    if spanish:
        month = _SPANISH_MONTHS.get(spanish.group(2).lower())
        if month:
            try:
                return date(int(spanish.group(3)), month, int(spanish.group(1)))
            except ValueError:
                return None
    return None


def _normalize_rup_layout(text: str) -> str:
    """Insert breaks before CCB labels; pypdf often glues 'S.A.S.NIT:' on one line."""
    cleaned = re.sub(r"[ \t]+", " ", text or "")
    labels = (
        "IDENTIFICACION",
        "QUE:",
        "NIT:",
        "CERTIFICA:",
        "NUMERO CONSECUTIVO DEL REPORTE DEL CONTRATO EJECUTADO:",
        "CONTRATO CELEBRADO POR:",
        "NOMBRE DEL CONTRATISTA:",
        "NOMBRE DEL CONTRATANTE:",
        "VALOR DEL CONTRATO EJECUTADO EXPRESADO EN SMMLV:",
        "PORCENTAJE DE PARTICIPACION",
        "CONTRATO EJECUTADO IDENTIFICADO",
        "CONTRATOS ADJUDICADOS",
        "CONTRATOS EJECUTADOS",
        "ENTIDAD CONTRATANTE:",
        "MUNICIPIO:",
        "NUMERO DEL CONTRATO:",
        "FECHA DE ADJUDICACION:",
        "FECHA INICIO:",
        "FECHA TERMINACION:",
        "VALOR INICIAL DEL CONTRATO EN PESOS:",
        "VALOR FINAL DEL CONTRATO PAGADO",
        "VALOR DEL CONTRATO (EN PESOS):",
        "CLASIFICACION CONTRATO",
        "FECHA DE INSCRIPCION:",
        "CAPACIDAD FINANCIERA",
        "CAPACIDAD ORGANIZACIONAL",
        "INFORMACION FINANCIERA",
        "INDICE DE LIQUIDEZ:",
        "INDICE DE ENDEUDAMIENTO:",
        "RAZON DE CORBERTURA DE INTERESES:",
        "RAZON DE COBERTURA DE INTERESES:",
        "RENTABILIDAD DEL PATRIMONIO:",
        "RENTABILIDAD DEL ACTIVO:",
        "ACTIVO CORRIENTE:",
        "PASIVO CORRIENTE:",
        "FECHA DE CORTE",
    )
    for label in labels:
        cleaned = re.sub(rf"(?<!\n)({re.escape(label)})", r"\n\1", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _collapse(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip(" :-")
    return cleaned or None


def _field(label: str, text: str) -> Optional[str]:
    stop = "|".join(_CCB_STOP_LABELS)
    match = re.search(
        rf"{label}\s*[:\s]+(.+?)(?=(?:{stop})|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    return _collapse(match.group(1) if match else None)


def _unspsc_codes(text: str) -> list[str]:
    return extract_unspsc_codes(text)


def _apply_regex(text: str, result: RupParseResult) -> None:
    ident = re.search(
        r"IDENTIFICACION\s*QUE:\s*(.+?)\s*NIT:\s*(\d{5,12})\s*[-]?\s*(\d)?",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if ident:
        result.razon_social = _collapse(ident.group(1))
        check = ident.group(3)
        result.nit = f"{ident.group(2)}-{check}" if check else ident.group(2)
    else:
        nit = _first_match(r"NIT[:\s]+(\d{5,12}(?:\s*-?\s*\d)?)", text)
        if nit:
            result.nit = re.sub(r"\s+", "", nit).replace("--", "-")
            if re.fullmatch(r"\d{6,12}\d", result.nit) and len(result.nit) >= 8:
                result.nit = f"{result.nit[:-1]}-{result.nit[-1]}"
        razon = _first_match(
            r"(?:raz[oó]n social|nombre o raz[oó]n social)[:\s]+([^\n]{3,180})",
            text,
        )
        if razon:
            result.razon_social = _collapse(razon)

    camara = _first_match(r"c[aá]mara de comercio de\s+([A-ZÁÉÍÓÚÑa-záéíóúñ. ]{3,60})", text)
    if camara:
        result.camara = camara.strip(" .")

    issued = _first_match(
        r"(?:fecha de (?:expedici[oó]n|generaci[oó]n)|expedido el)[:\s]+([^\n]{8,40})",
        text,
    )
    result.issued_at = _parse_date(issued or "")
    if result.issued_at is None:
        header_date = re.search(
            r"(\d{1,2}\s+DE\s+[A-ZÁÉÍÓÚÑ]+\s+DE\s+20\d{2})",
            text,
            re.IGNORECASE,
        )
        if header_date:
            result.issued_at = _parse_date(header_date.group(1))

    valid = _first_match(
        r"(?:vigente hasta|fecha de vencimiento|validez hasta)[:\s]+([^\n]{8,40})",
        text,
    )
    if valid:
        result.valid_until = _parse_date(valid)

    smmlv = _first_match(
        r"(?:SMMLV|salario m[ií]nimo)[^\d]{0,80}(\d{1,3}(?:[.\s]\d{3})+|\d{6,8})",
        text,
    )
    parsed_smmlv = _parse_number(smmlv or "")
    if parsed_smmlv and parsed_smmlv > 100_000:
        result.smmlv = parsed_smmlv

    result.liquidity = _parse_number(
        _first_match(r"(?:[ií]ndice de )?liquidez[:\s]+([\d.,]+)", text) or ""
    )
    result.indebtedness = _parse_number(
        _first_match(r"(?:[ií]ndice de )?endeudamiento[:\s]+([\d.,]+)", text) or ""
    )
    result.interest_coverage = _parse_number(
        _first_match(
            r"(?:raz[oó]n de )?(?:cobertura|corbertura)(?:\s+de)?\s+intereses[:\s]+([\d.,]+)",
            text,
        )
        or ""
    )
    result.return_on_equity = _parse_number(
        _first_match(r"rentabilidad del patrimonio[:\s]+([\d.,]+)", text) or ""
    )
    result.return_on_assets = _parse_number(
        _first_match(r"rentabilidad del activo[:\s]+([\d.,]+)", text) or ""
    )

    current_assets = _parse_number(
        _first_match(r"activo corriente[:\s]+\$?\s*([\d.,]+)", text) or ""
    )
    current_liabilities = _parse_number(
        _first_match(r"pasivo corriente[:\s]+\$?\s*([\d.,]+)", text) or ""
    )
    working = _parse_number(_first_match(r"capital de trabajo[:\s]+\$?\s*([\d.,]+)", text) or "")
    if working is None and current_assets is not None and current_liabilities is not None:
        working = current_assets - current_liabilities
    result.working_capital = working

    staff = _first_match(
        r"(?:personal|planta de personal|n[uú]mero de empleados)[:\s]+(\d{1,6})",
        text,
    )
    if staff:
        result.organizational["staff_count"] = int(staff)
    size = _first_match(
        r"clasific[oó]\s+como:\s*(microempresa|pequeña empresa|mediana empresa|gran empresa)",
        text,
    )
    if size:
        result.organizational["company_size"] = size.lower()

    cut = _first_match(
        r"(?:fecha de corte[^\n]{0,40}|corte a|corte de la informaci[oó]n financiera)[:\s]+(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4})",
        text,
    )
    if cut:
        cut_date = _parse_date(cut)
        if cut_date:
            result.cut_year = cut_date.year
    if result.cut_year is None:
        cut_year = _first_match(r"(?:a[nñ]o|corte|vigencia)\s*(?:fiscal)?[:\s]+(20\d{2})", text)
        if cut_year:
            result.cut_year = int(cut_year)

    result.contracts = _extract_ccb_experience(text)
    if not result.contracts:
        result.contracts = _extract_contracts_regex(text)
    entity_reported = _extract_entity_reported_contracts(text)
    existing_numbers = {
        (c.contract_number or "").upper() for c in result.contracts if c.contract_number
    }
    for extra in entity_reported:
        key = (extra.contract_number or "").upper()
        if key and key in existing_numbers:
            continue
        result.contracts.append(extra)
        if key:
            existing_numbers.add(key)


def _build_ccb_description(
    *,
    entity: Optional[str],
    contractor: Optional[str],
    participation: Optional[float],
    codes: list[str],
) -> str:
    if entity and contractor and contractor.upper() != entity.upper():
        description = f"Contrato ejecutado para {entity} ({contractor})"
    elif entity:
        description = f"Contrato ejecutado para {entity}"
    elif contractor:
        description = f"Contrato ejecutado por {contractor}"
    else:
        description = "Contrato ejecutado reportado en el RUP"
    if participation is not None:
        description += f". Participación {participation:g}%"
    return description


def resolve_contractor_name(
    *,
    stored: Optional[str] = None,
    description: Optional[str] = None,
    razon_social: Optional[str] = None,
    account_name: Optional[str] = None,
) -> Optional[str]:
    """Return the RUP contractor (consorcio/UT/empresa), never the login name."""

    def usable(value: Optional[str]) -> Optional[str]:
        cleaned = re.sub(r"\s+", " ", value or "").strip(" :-")
        if not cleaned:
            return None
        lowered = cleaned.lower()
        if account_name and lowered == account_name.strip().lower():
            return None
        if lowered in {"proponente", "mi empresa"}:
            return None
        if lowered.startswith("consorcio, union temporal") or lowered.startswith(
            "consorcio, unión temporal"
        ):
            return None
        return cleaned

    from_stored = usable(stored)
    if from_stored:
        return from_stored
    text = description or ""
    parenthetical = re.search(
        r"contrato ejecutado para .+?\((.+?)\)",
        text,
        re.IGNORECASE,
    )
    if parenthetical:
        from_desc = usable(parenthetical.group(1))
        if from_desc:
            return from_desc
    by_contractor = re.search(
        r"contrato ejecutado por ([^.]+)",
        text,
        re.IGNORECASE,
    )
    if by_contractor:
        from_desc = usable(by_contractor.group(1))
        if from_desc:
            return from_desc
    return usable(razon_social)


def _extract_ccb_experience(text: str) -> list[RupContract]:
    contracts: list[RupContract] = []
    starts = list(
        re.finditer(
            r"NUMERO CONSECUTIVO DEL REPORTE DEL CONTRATO EJECUTADO:\s*(\d+)",
            text,
            re.IGNORECASE,
        )
    )
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.start() : end]
        if re.search(r"CONTRATOS ADJUDICADOS|ENTIDAD CONTRATANTE:", block, re.IGNORECASE):
            cutoff = re.search(r"CERTIFICA:|CONTRATOS ADJUDICADOS|ENTIDAD CONTRATANTE:", block, re.IGNORECASE)
            if cutoff:
                block = block[: cutoff.start()]
        contractor = _field("NOMBRE DEL CONTRATISTA", block)
        entity = _field("NOMBRE DEL CONTRATANTE", block)
        amount_smmlv = _parse_number(
            _first_match(
                r"VALOR DEL CONTRATO EJECUTADO EXPRESADO EN SMMLV:\s*([\d.,]+)",
                block,
            )
            or ""
        )
        participation = _parse_number(
            _first_match(
                r"PORCENTAJE\s+DE PARTICIPACION[\s\S]{0,200}?:\s*([\d.,]+)\s*%",
                block,
            )
            or ""
        )
        codes = _unspsc_codes(block)
        description = _build_ccb_description(
            entity=entity,
            contractor=contractor,
            participation=participation,
            codes=codes,
        )
        contracts.append(
            RupContract(
                contract_number=f"RUP-{match.group(1)}",
                object=description,
                entity=entity,
                contractor=contractor,
                amount_smmlv=amount_smmlv,
                participation_pct=participation,
                category=None,
                unspsc_codes=codes,
                contract_kind=classify_rup_experience_kind(
                    object_text=description,
                    category=", ".join(codes),
                    extra_text=block,
                    unspsc_codes=codes,
                ).value,
            )
        )
    return contracts


def _extract_entity_reported_contracts(text: str) -> list[RupContract]:
    marker = re.search(r"CONTRATOS ADJUDICADOS", text, re.IGNORECASE)
    body = text[marker.start() :] if marker else text
    chunks = re.split(r"(?=ENTIDAD CONTRATANTE:)", body)
    contracts: list[RupContract] = []
    for chunk in chunks:
        if not re.search(r"FECHA TERMINACION:", chunk, re.IGNORECASE):
            continue
        entity = _field("ENTIDAD CONTRATANTE", chunk)
        number = _field("NUMERO DEL CONTRATO", chunk)
        if not entity and not number:
            continue
        municipality = _field("MUNICIPIO", chunk)
        completion = _parse_date(_field("FECHA TERMINACION", chunk) or "")
        amount = _parse_number(
            _first_match(
                r"VALOR FINAL DEL CONTRATO PAGADO \(EN PESOS\):\s*\$?\s*([\d.,]+)",
                chunk,
            )
            or ""
        )
        if amount is None:
            amount = _parse_number(
                _first_match(
                    r"VALOR INICIAL DEL CONTRATO EN PESOS:\s*\$?\s*([\d.,]+)",
                    chunk,
                )
                or ""
            )
        classification = _field("CLASIFICACION CONTRATO", chunk)
        if classification:
            classification = re.sub(
                r"FECHA DE INSCRIPCION:.+",
                "",
                classification,
                flags=re.IGNORECASE | re.DOTALL,
            )
            classification = re.sub(
                r"CONTRATO RELACIONADO CON LA CONSTRUCCI[OÓ]N[\s\S]*",
                "",
                classification,
                flags=re.IGNORECASE,
            )
            classification = _collapse(classification)
        codes = _unspsc_codes(chunk)
        contractor = _field("NOMBRE DEL CONTRATISTA", chunk)
        description = classification or _build_ccb_description(
            entity=entity,
            contractor=contractor,
            participation=None,
            codes=codes,
        )
        contracts.append(
            RupContract(
                contract_number=number,
                object=description,
                entity=entity,
                contractor=contractor,
                amount_cop=amount,
                completion_date=completion,
                category=classification,
                unspsc_codes=codes,
                contract_kind=classify_rup_experience_kind(
                    object_text=description,
                    category=classification or "",
                    contract_number=number or "",
                    extra_text=chunk,
                    unspsc_codes=codes,
                ).value,
                municipality=municipality,
            )
        )
    return contracts


def _first_match(pattern: str, text: str, flags: int = re.IGNORECASE) -> Optional[str]:
    match = re.search(pattern, text, flags)
    if not match:
        return None
    return match.group(1).strip()


def _extract_contracts_regex(text: str) -> list[RupContract]:
    contracts: list[RupContract] = []
    blocks = re.split(r"\n(?=(?:CONTRATO|Contrato|Experiencia\s+\d))", text)
    for block in blocks:
        if not re.search(r"(?:contrato(?:\s+n[oº°.]*)?|n[uú]mero de contrato)", block, re.IGNORECASE):
            continue
        number = _first_match(
            r"(?:contrato(?:\s+n[oº°.]*)?|n[uú]mero)[:\s]+([A-Z0-9][A-Z0-9\-\/]{2,40})",
            block,
        )
        obj = _first_match(r"objeto[:\s]+([^\n]{8,500})", block)
        entity = _first_match(r"entidad(?:\s+contratante)?[:\s]+([^\n]{3,200})", block)
        if not obj:
            continue
        amount_smmlv = _parse_number(
            _first_match(r"valor[^\n]{0,40}?([\d.,]+)\s*SMMLV", block) or ""
        )
        amount_cop = _parse_number(
            _first_match(r"valor(?:\s+contrato|\s+actual)?[:\s]+\$?\s*([\d.,]+)", block) or ""
        )
        if amount_smmlv is not None and amount_cop is not None and amount_cop < 10_000:
            amount_cop = None
        completion = _parse_date(
            _first_match(
                r"(?:fecha (?:de )?(?:terminaci[oó]n|finalizaci[oó]n|ejecuci[oó]n))[:\s]+([^\n]{8,40})",
                block,
            )
            or ""
        )
        category = _first_match(r"(?:categor[ií]a|clasificador|c[oó]digo)[:\s]+([^\n]{2,120})", block)
        codes = _unspsc_codes(block)
        department = _first_match(r"departamento[:\s]+([^\n]{3,80})", block)
        municipality = _first_match(r"municipio[:\s]+([^\n]{3,80})", block)
        object_text = re.sub(r"\s+", " ", obj).strip()
        contracts.append(
            RupContract(
                contract_number=number,
                object=object_text,
                entity=entity,
                amount_cop=amount_cop,
                amount_smmlv=amount_smmlv,
                completion_date=completion,
                category=", ".join(codes) if codes else category,
                unspsc_codes=codes,
                contract_kind=classify_rup_experience_kind(
                    object_text=object_text,
                    category=category or "",
                    contract_number=number or "",
                    extra_text=block,
                    unspsc_codes=codes,
                ).value,
                department=department,
                municipality=municipality,
            )
        )
    return contracts


def _extract_with_llm(text: str, regex_result: RupParseResult) -> Optional[dict[str, Any]]:
    from openai import OpenAI

    excerpt = text[:40_000]
    hint = {
        "nit": regex_result.nit,
        "razon_social": regex_result.razon_social,
        "contracts_found": len(regex_result.contracts),
        "liquidity": regex_result.liquidity,
        "indebtedness": regex_result.indebtedness,
    }
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = (
        "Extrae datos de un certificado RUP colombiano (Registro Único de Proponentes). "
        "No inventes valores que no estén en el texto. Responde solo JSON con esta forma:\n"
        "{"
        '"nit": string|null, "razon_social": string|null, "camara": string|null, '
        '"issued_at": "YYYY-MM-DD"|null, "valid_until": "YYYY-MM-DD"|null, '
        '"smmlv": number|null, "cut_year": number|null, '
        '"financial": {"liquidity": number|null, "indebtedness": number|null, '
        '"interest_coverage": number|null, "return_on_equity": number|null, '
        '"return_on_assets": number|null, "working_capital": number|null}, '
        '"organizational": {"staff_count": number|null}, '
        '"contracts": [{"contract_number": string|null, "object": string, '
        '"entity": string|null, "amount_cop": number|null, "amount_smmlv": number|null, '
        '"completion_date": "YYYY-MM-DD"|null, "category": string|null, '
        '"department": string|null, "municipality": string|null}]'
        "}\n"
        "Borrador regex: "
        f"{json.dumps(hint, ensure_ascii=False)}\n\n"
        "TEXTO:\n"
        f"{excerpt}"
    )
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL_NAME or "gpt-4o-mini",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "Eres un extractor de certificados RUP. Nunca inventas contratos ni cifras.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        return None
    return json.loads(content)


def _merge_llm(result: RupParseResult, payload: dict[str, Any]) -> None:
    result.nit = result.nit or _as_str(payload.get("nit"))
    result.razon_social = result.razon_social or _as_str(payload.get("razon_social"))
    result.camara = result.camara or _as_str(payload.get("camara"))
    result.issued_at = result.issued_at or _parse_iso_date(payload.get("issued_at"))
    result.valid_until = result.valid_until or _parse_iso_date(payload.get("valid_until"))
    if result.smmlv is None:
        result.smmlv = _as_float(payload.get("smmlv"))
    if result.cut_year is None:
        result.cut_year = _as_int(payload.get("cut_year"))

    financial = payload.get("financial") if isinstance(payload.get("financial"), dict) else {}
    result.liquidity = result.liquidity if result.liquidity is not None else _as_float(financial.get("liquidity"))
    result.indebtedness = (
        result.indebtedness if result.indebtedness is not None else _as_float(financial.get("indebtedness"))
    )
    result.interest_coverage = (
        result.interest_coverage
        if result.interest_coverage is not None
        else _as_float(financial.get("interest_coverage"))
    )
    result.return_on_equity = (
        result.return_on_equity
        if result.return_on_equity is not None
        else _as_float(financial.get("return_on_equity"))
    )
    result.return_on_assets = (
        result.return_on_assets
        if result.return_on_assets is not None
        else _as_float(financial.get("return_on_assets"))
    )
    result.working_capital = (
        result.working_capital if result.working_capital is not None else _as_float(financial.get("working_capital"))
    )

    organizational = payload.get("organizational") if isinstance(payload.get("organizational"), dict) else {}
    for key, value in organizational.items():
        if key not in result.organizational or result.organizational.get(key) in (None, ""):
            result.organizational[key] = value

    llm_contracts = payload.get("contracts")
    parsed: list[RupContract] = []
    if isinstance(llm_contracts, list):
        for item in llm_contracts:
            if not isinstance(item, dict):
                continue
            obj = _as_str(item.get("object"))
            if not obj:
                continue
            parsed.append(
                RupContract(
                    contract_number=_as_str(item.get("contract_number")),
                    object=obj,
                    entity=_as_str(item.get("entity")),
                    contractor=_as_str(item.get("contractor")),
                    amount_cop=_as_float(item.get("amount_cop")),
                    amount_smmlv=_as_float(item.get("amount_smmlv")),
                    completion_date=_parse_iso_date(item.get("completion_date")),
                    category=_as_str(item.get("category")),
                    unspsc_codes=_codes_from_llm(item.get("unspsc_codes")),
                    contract_kind=_as_str(item.get("contract_kind")),
                    department=_as_str(item.get("department")),
                    municipality=_as_str(item.get("municipality")),
                )
            )
    if len(parsed) > len(result.contracts):
        result.contracts = parsed


def _codes_from_llm(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    codes: list[str] = []
    seen: set[str] = set()
    for item in value:
        digits = re.sub(r"\D", "", str(item))
        if len(digits) == 8 and digits not in seen:
            seen.add(digits)
            codes.append(digits)
    return codes


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return _parse_number(str(value))


def _as_int(value: Any) -> Optional[int]:
    number = _as_float(value)
    if number is None:
        return None
    return int(number)


def _parse_iso_date(value: Any) -> Optional[date]:
    text = _as_str(value)
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            year, month, day = text.split("-")
            return date(int(year), int(month), int(day))
        except ValueError:
            return None
    return _parse_date(text)
