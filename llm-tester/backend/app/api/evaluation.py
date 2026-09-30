import asyncio
import csv
import io
import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_maker, get_db
from app.models.evaluation_models import (
    EvaluationAsset, EvaluationDataset, EvaluationDatasetItem, EvaluationDatasetVersion,
    EvaluationAttempt, EvaluationModelRoute, EvaluationPipelineVersion, EvaluationPromptVersion, EvaluationResult,
    EvaluationRun, EvaluationRunItem, EvaluationSuiteVersion,
)
from app.models.evaluation_schemas import (
    DatasetCreateRequest, DatasetImportMapping, DatasetItemInput, DatasetVersionCreateRequest, PipelineCreateRequest, PromptCreateRequest,
    RouteCreateRequest, RunCreateRequest, RunEstimateRequest, RunEstimateResponse, SuiteCreateRequest,
)
from app.services.evaluation_runner import EvaluationRunner
from app.models.evaluation_schemas import RunEvaluationRequest
from app.models.evaluation_schemas import PromptPreviewRequest, RunRetryRequest
from app.services.prompt_rendering import render_prompt, TOKEN
from app.services.judge_evaluation import judge_prompt
from app.services.v1_providers import EnvironmentSecretResolver, ProviderExecutionError, list_provider_models

router = APIRouter(prefix="/v1", tags=["evaluation-v1"])


@router.post('/prompts:import')
async def import_prompt(file: UploadFile = File(...)):
    from app.services.prompt_import import import_prompt_yaml
    try:
        return import_prompt_yaml(await file.read(256 * 1024 + 1))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.post('/prompts:preview')
async def preview_prompt(request: PromptPreviewRequest):
    try:
        return {'rendered': render_prompt(request.template, request.input)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


def obj(entity, fields):
    return {field: getattr(entity, field) for field in fields}


async def resolve_run_inputs(request: RunEstimateRequest, db: AsyncSession):
    version = await db.get(EvaluationDatasetVersion, str(request.dataset_version_id))
    if not version or version.status != "published":
        raise HTTPException(422, "Run requires a published DatasetVersion")
    prompts = [await db.get(EvaluationPromptVersion, str(item)) for item in request.prompt_version_ids]
    routes = [await db.get(EvaluationModelRoute, str(item)) for item in request.candidate_route_ids]
    if any(item is None for item in prompts) or any(item is None for item in routes):
        raise HTTPException(422, "PromptVersion or ModelRoute was not found")
    required_modalities = set(version.schema_json.get("modalities", ["text"]))
    for route in routes:
        supported_modalities = set(route.capabilities_json.get("modalities", ["text"]))
        if not required_modalities.issubset(supported_modalities):
            raise HTTPException(422, "Route capability does not satisfy DatasetVersion modalities")
    count = (await db.execute(select(func.count()).select_from(EvaluationDatasetItem).where(EvaluationDatasetItem.dataset_version_id == version.id))).scalar_one()
    if not count:
        raise HTTPException(422, "DatasetVersion has no items")
    source_items = (await db.execute(select(EvaluationDatasetItem).where(EvaluationDatasetItem.dataset_version_id == version.id))).scalars().all()
    try:
        for row_number, item in enumerate(source_items, 1):
            for prompt in prompts:
                render_prompt(prompt.template, item.input_json)
    except ValueError as exc:
        raise HTTPException(422, f'Строка датасета №{row_number}: {exc}') from None
    return version, prompts, routes, count


@router.post("/datasets", status_code=status.HTTP_201_CREATED)
async def create_dataset(request: DatasetCreateRequest, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(EvaluationDataset).where(EvaluationDataset.name == request.name))).scalar_one_or_none()
    if existing: raise HTTPException(409, "Dataset name already exists")
    dataset = EvaluationDataset(name=request.name, description=request.description); db.add(dataset); await db.flush()
    version = EvaluationDatasetVersion(dataset_id=dataset.id, version_number=1, schema_json=request.schema); db.add(version); await db.flush()
    return {"id": dataset.id, "name": dataset.name, "draft_version_id": version.id}


@router.get("/datasets")
async def list_datasets(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(EvaluationDataset).order_by(EvaluationDataset.created_at.desc()))).scalars().all()
    return [obj(row, ["id", "name", "description", "created_at"]) for row in rows]



@router.post("/datasets/{dataset_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_dataset_version(dataset_id: str, request: DatasetVersionCreateRequest, db: AsyncSession = Depends(get_db)):
    dataset = await db.get(EvaluationDataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    existing_draft = (await db.execute(
        select(EvaluationDatasetVersion).where(
            EvaluationDatasetVersion.dataset_id == dataset_id,
            EvaluationDatasetVersion.status == "draft",
        )
    )).scalars().first()
    if existing_draft:
        raise HTTPException(409, "Dataset already has a draft version")

    base_version = None
    if request.base_version_id:
        base_version = await db.get(EvaluationDatasetVersion, str(request.base_version_id))
        if not base_version or base_version.dataset_id != dataset_id:
            raise HTTPException(422, "Base DatasetVersion does not belong to this Dataset")
    else:
        base_version = (await db.execute(
            select(EvaluationDatasetVersion)
            .where(EvaluationDatasetVersion.dataset_id == dataset_id)
            .order_by(EvaluationDatasetVersion.version_number.desc())
        )).scalars().first()

    latest_number = (await db.execute(
        select(func.max(EvaluationDatasetVersion.version_number)).where(EvaluationDatasetVersion.dataset_id == dataset_id)
    )).scalar_one() or 0
    schema_json = request.schema if request.schema is not None else (base_version.schema_json if base_version else {})
    version = EvaluationDatasetVersion(
        dataset_id=dataset_id,
        version_number=latest_number + 1,
        schema_json=schema_json,
        status="draft",
    )
    db.add(version)
    await db.flush()
    return obj(version, ["id", "dataset_id", "version_number", "schema_json", "status", "created_at"])


@router.get("/dataset-versions")
async def list_dataset_versions(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(EvaluationDatasetVersion, EvaluationDataset.name)
        .join(EvaluationDataset, EvaluationDataset.id == EvaluationDatasetVersion.dataset_id)
        .order_by(EvaluationDatasetVersion.created_at.desc())
    )).all()
    return [{**obj(version, ["id", "dataset_id", "version_number", "schema_json", "status", "created_at"]), "dataset_name": name} for version, name in rows]
@router.get("/dataset-versions/{version_id}/items")
async def list_dataset_version_items(
    version_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    if not await db.get(EvaluationDatasetVersion, version_id):
        raise HTTPException(404, "Dataset version not found")
    total = (await db.execute(
        select(func.count()).select_from(EvaluationDatasetItem).where(EvaluationDatasetItem.dataset_version_id == version_id)
    )).scalar_one()
    rows = (await db.execute(
        select(EvaluationDatasetItem)
        .where(EvaluationDatasetItem.dataset_version_id == version_id)
        .order_by(EvaluationDatasetItem.external_id)
        .offset(offset)
        .limit(limit)
    )).scalars().all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [obj(row, ["id", "external_id", "input_json", "reference_json", "metadata_json", "tags_json"]) for row in rows],
    }


def format_item_validation_error(exc: ValidationError, raw: dict) -> str:
    reasons = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error.get("loc", ())) or "строка"
        error_type = error.get("type")
        if error_type == "missing":
            reasons.append(f"обязательное поле «{field}» отсутствует")
        elif error_type == "dict_type":
            reasons.append(f"поле «{field}» должно быть JSON-объектом")
        elif error_type == "list_type":
            reasons.append(f"поле «{field}» должно быть JSON-массивом")
        elif error_type == "string_type":
            reasons.append(f"поле «{field}» должно быть строкой")
        elif error_type == "extra_forbidden":
            reasons.append(f"неизвестное поле «{field}»")
        else:
            reasons.append(f"поле «{field}»: {error.get('msg', 'некорректное значение')}")
    available = ", ".join(str(key) for key in raw.keys()) or "нет"
    return "; ".join(reasons) + f". Получены поля: {available}"


IMPORT_MAX_BYTES = 5 * 1024 * 1024


def build_import_preview(source_format: str, raw_rows: list[tuple[int, object]], source_fields: list[str] | None = None, source_preview: list[dict] | None = None, mapping_applied: bool = False, source_encoding: str | None = None, source_delimiter: str | None = None):
    items, errors, seen = [], [], set()
    for row_number, raw in raw_rows:
        if not isinstance(raw, dict):
            errors.append({"row": row_number, "reason": "row must be a JSON object"})
            continue
        if "__parse_error__" in raw:
            errors.append({"row": row_number, "reason": raw["__parse_error__"]})
            continue
        try:
            item = DatasetItemInput.model_validate(raw)
        except ValidationError as exc:
            errors.append({"row": row_number, "reason": format_item_validation_error(exc, raw)})
            continue
        if item.external_id in seen:
            errors.append({"row": row_number, "reason": "duplicate external_id"})
            continue
        seen.add(item.external_id)
        items.append(item)
    return {
        "source_format": source_format,
        "source_fields": source_fields or [],
        "source_preview": source_preview or [],
        "mapping_applied": mapping_applied,
        "source_encoding": source_encoding,
        "source_delimiter": source_delimiter,
        "total_count": len(raw_rows),
        "valid_count": len(items),
        "invalid_count": len(errors),
        "row_errors": errors,
        "preview": [item.model_dump() for item in items],
    }, items


def parse_csv_row(row: dict[str, str]):
    result = {"external_id": (row.get("external_id") or "").strip()}
    for field, fallback in (("input", {}), ("reference", {}), ("metadata", {}), ("tags", [])):
        value = (row.get(field) or "").strip()
        result[field] = fallback if not value else json.loads(value)
    return result


def parse_import_mapping(mapping_json: str | None) -> DatasetImportMapping | None:
    if not mapping_json:
        return None
    try:
        raw = json.loads(mapping_json)
        return DatasetImportMapping.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(422, f"Некорректное сопоставление полей: {exc}")


def apply_import_mapping(raw: dict, mapping: DatasetImportMapping) -> dict:
    def source_value(field: str):
        if field not in raw:
            raise ValueError(f"поле-источник «{field}» отсутствует")
        return raw[field]

    external_value = source_value(mapping.external_id_field)
    if external_value is None or not str(external_value).strip():
        raise ValueError(f"поле-источник «{mapping.external_id_field}» содержит пустой идентификатор")
    text_value = source_value(mapping.input_text_field)
    if not isinstance(text_value, str):
        raise ValueError(f"поле-источник «{mapping.input_text_field}» должно содержать текст")

    reference = {}
    if mapping.reference_field:
        reference_value = source_value(mapping.reference_field)
        if mapping.reference_format == 'text':
            if reference_value is not None and not isinstance(reference_value, str):
                raise ValueError('Текстовый эталон должен содержать строку')
            reference_value = {'text': reference_value} if reference_value else {}
        if reference_value not in (None, ""):
            if isinstance(reference_value, str):
                try:
                    reference_value = json.loads(reference_value)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"поле-источник «{mapping.reference_field}» содержит некорректный JSON: {exc.msg}")
            if not isinstance(reference_value, dict):
                raise ValueError(f"поле-источник «{mapping.reference_field}» должно содержать JSON-объект")
            reference = reference_value

    return {
        "external_id": str(external_value).strip(),
        "input": {"text": text_value},
        "reference": reference,
        "metadata": raw.get("metadata", {}),
        "tags": raw.get("tags", []),
    }


def decode_import_content(content: bytes) -> tuple[str, str]:
    if content.startswith(b"\xef\xbb\xbf"):
        return content.decode("utf-8-sig"), "utf-8-bom"
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        return content.decode("utf-16"), "utf-16-bom"
    try:
        return content.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        try:
            return content.decode("cp1251"), "windows-1251"
        except UnicodeDecodeError:
            raise HTTPException(422, "Import file encoding is unsupported. Use UTF-8, UTF-16 with BOM, or Windows-1251")


def detect_csv_delimiter(text: str) -> str:
    sample = text[:65536]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        first_line = next((line for line in text.splitlines() if line.strip()), "")
        counts = {candidate: first_line.count(candidate) for candidate in (",", ";", "\t", "|")}
        delimiter = max(counts, key=counts.get)
        if counts[delimiter] == 0:
            raise HTTPException(422, "CSV delimiter was not detected. Supported delimiters: comma, semicolon, tab, pipe")
    return delimiter


def make_source_preview(raw_rows: list[tuple[int, object]], source_fields: list[str]) -> list[dict]:
    samples = []
    for line_number, raw in raw_rows:
        if not isinstance(raw, dict) or "__parse_error__" in raw:
            continue
        values = {}
        for field in source_fields:
            value = raw.get(field)
            if isinstance(value, str):
                rendered = value
            else:
                rendered = json.dumps(value, ensure_ascii=False)
            values[field] = rendered if len(rendered) <= 500 else rendered[:500] + "…"
        samples.append({"row": line_number, "values": values})
        if len(samples) == 3:
            break
    return samples


async def parse_import_file(file: UploadFile, mapping: DatasetImportMapping | None = None):
    filename = (file.filename or "").lower()
    if filename.endswith(".csv"):
        source_format = "csv"
    elif filename.endswith(".jsonl"):
        source_format = "jsonl"
    else:
        raise HTTPException(422, "Import file must have .csv or .jsonl extension")
    content = await file.read()
    if not content or len(content) > IMPORT_MAX_BYTES:
        raise HTTPException(422, "Import file size must be between 1 byte and 5 MiB")
    text, source_encoding = decode_import_content(content)
    source_delimiter = None

    raw_rows = []
    source_fields = set()
    if source_format == "jsonl":
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                raw_rows.append((line_number, raw))
                if isinstance(raw, dict):
                    source_fields.update(raw.keys())
            except json.JSONDecodeError as exc:
                raw_rows.append((line_number, {"__parse_error__": f"invalid JSON: {exc.msg}"}))
    else:
        try:
            source_delimiter = detect_csv_delimiter(text)
            reader = csv.DictReader(io.StringIO(text), delimiter=source_delimiter)
            if not reader.fieldnames:
                raise HTTPException(422, "CSV requires a header row")
            source_fields.update(reader.fieldnames)
            canonical_csv = "external_id" in reader.fieldnames
            for line_number, row in enumerate(reader, 2):
                try:
                    raw_rows.append((line_number, row if mapping or not canonical_csv else parse_csv_row(row)))
                except json.JSONDecodeError as exc:
                    raw_rows.append((line_number, {"__parse_error__": f"invalid JSON field: {exc.msg}"}))
        except csv.Error as exc:
            raise HTTPException(422, f"Invalid CSV: {exc}")

    ordered_source_fields = sorted(str(field) for field in source_fields)
    source_preview = make_source_preview(raw_rows, ordered_source_fields)

    if mapping:
        mapped_rows = []
        for line_number, raw in raw_rows:
            if not isinstance(raw, dict) or "__parse_error__" in raw:
                mapped_rows.append((line_number, raw))
                continue
            try:
                mapped_rows.append((line_number, apply_import_mapping(raw, mapping)))
            except ValueError as exc:
                mapped_rows.append((line_number, {"__parse_error__": f"ошибка сопоставления: {exc}"}))
        raw_rows = mapped_rows

    return build_import_preview(source_format, raw_rows, ordered_source_fields, source_preview, bool(mapping), source_encoding, source_delimiter)

def build_item_preview(items: list[dict]):
    preview, _ = build_import_preview("json", list(enumerate(items, 1)))
    return preview


@router.post("/datasets/import:preview")
async def preview_import(file: UploadFile = File(...), mapping_json: str | None = Form(default=None)):
    mapping = parse_import_mapping(mapping_json)
    preview, _ = await parse_import_file(file, mapping)
    return preview

@router.post("/datasets/items:preview")
async def preview_new_dataset_items(items: list[dict]):
    return build_item_preview(items)


@router.post("/datasets/{version_id}/items:preview")
async def preview_items(version_id: str, items: list[dict], db: AsyncSession = Depends(get_db)):
    if not await db.get(EvaluationDatasetVersion, version_id):
        raise HTTPException(404, "Dataset version not found")
    return build_item_preview(items)


@router.post("/datasets/{version_id}/items:import", status_code=status.HTTP_201_CREATED)
async def import_items(version_id: str, file: UploadFile = File(...), mapping_json: str | None = Form(default=None), db: AsyncSession = Depends(get_db)):
    version = await db.get(EvaluationDatasetVersion, version_id)
    if not version: raise HTTPException(404, "Dataset version not found")
    if version.status != "draft": raise HTTPException(409, "Published dataset version cannot be changed")
    mapping = parse_import_mapping(mapping_json)
    preview, items = await parse_import_file(file, mapping)
    if preview["invalid_count"]:
        raise HTTPException(422, "Import contains invalid rows; run preview and correct the file before commit")
    if not items:
        raise HTTPException(422, "Import file contains no rows")
    if mapping:
        mapping_definition = mapping.model_dump(exclude_unset=True)
        stored_mapping = version.schema_json.get("import_mapping")
        if stored_mapping and stored_mapping != mapping_definition:
            raise HTTPException(409, "Import mapping differs from the mapping stored for this DatasetVersion")
        version.schema_json = {**version.schema_json, "import_mapping": mapping_definition}
    version.schema_json = {
        **version.schema_json,
        "import_source": {
            "format": preview["source_format"],
            "encoding": preview["source_encoding"],
            "delimiter": preview["source_delimiter"],
        },
    }
    existing = (await db.execute(select(EvaluationDatasetItem.external_id).where(EvaluationDatasetItem.dataset_version_id == version_id))).scalars().all()
    if set(item.external_id for item in items) & set(existing):
        raise HTTPException(422, "external_id values must be unique within a dataset version")
    db.add_all([EvaluationDatasetItem(dataset_version_id=version_id, external_id=item.external_id, input_json=item.input, reference_json=item.reference, metadata_json=item.metadata, tags_json=item.tags) for item in items])
    await db.flush()
    return {"committed_count": len(items), "dataset_version_id": version_id, "source_format": preview["source_format"]}

@router.post("/datasets/{version_id}/items:commit", status_code=status.HTTP_201_CREATED)
async def commit_items(version_id: str, items: list[DatasetItemInput], db: AsyncSession = Depends(get_db)):
    version = await db.get(EvaluationDatasetVersion, version_id)
    if not version: raise HTTPException(404, "Dataset version not found")
    if version.status != "draft": raise HTTPException(409, "Published dataset version cannot be changed")
    ids = [item.external_id for item in items]
    existing = (await db.execute(select(EvaluationDatasetItem.external_id).where(EvaluationDatasetItem.dataset_version_id == version_id))).scalars().all()
    if len(ids) != len(set(ids)) or set(ids) & set(existing): raise HTTPException(422, "external_id values must be unique within a dataset version")
    db.add_all([EvaluationDatasetItem(dataset_version_id=version_id, external_id=item.external_id, input_json=item.input, reference_json=item.reference, metadata_json=item.metadata, tags_json=item.tags) for item in items])
    await db.flush(); return {"committed_count": len(items), "dataset_version_id": version_id}


@router.post("/datasets/{version_id}:publish")
async def publish_dataset(version_id: str, db: AsyncSession = Depends(get_db)):
    version = await db.get(EvaluationDatasetVersion, version_id)
    if not version: raise HTTPException(404, "Dataset version not found")
    count = (await db.execute(select(func.count()).select_from(EvaluationDatasetItem).where(EvaluationDatasetItem.dataset_version_id == version_id))).scalar_one()
    if not count: raise HTTPException(422, "Cannot publish an empty dataset version")
    version.status = "published"; await db.flush()
    return {"id": version.id, "status": version.status, "item_count": count}


@router.post("/datasets/{version_id}/assets", status_code=status.HTTP_201_CREATED)
async def upload_asset(version_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    version = await db.get(EvaluationDatasetVersion, version_id)
    if not version or version.status != "draft": raise HTTPException(409, "Assets require a draft dataset version")
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}: raise HTTPException(422, "Only JPEG, PNG and WebP assets are supported")
    content = await file.read()
    if not content or len(content) > 10 * 1024 * 1024: raise HTTPException(422, "Asset size must be between 1 byte and 10 MiB")
    asset_id = str(uuid4()); storage = Path("data") / "assets" / asset_id; storage.parent.mkdir(parents=True, exist_ok=True); storage.write_bytes(content)
    asset = EvaluationAsset(id=asset_id, dataset_version_id=version_id, storage_path=str(storage), original_filename=file.filename or "upload", mime_type=file.content_type, byte_size=len(content), sha256=sha256(content).hexdigest())
    db.add(asset); await db.flush(); return obj(asset, ["id", "mime_type", "byte_size", "sha256"])


@router.post("/prompts", status_code=status.HTTP_201_CREATED)
async def create_prompt(request: PromptCreateRequest, db: AsyncSession = Depends(get_db)):
    entity = EvaluationPromptVersion(name=request.name, template=request.template); db.add(entity); await db.flush()
    return obj(entity, ["id", "name", "template", "version_number"])


@router.post("/pipelines", status_code=status.HTTP_201_CREATED)
async def create_pipeline(request: PipelineCreateRequest, db: AsyncSession = Depends(get_db)):
    entity = EvaluationPipelineVersion(name=request.name, definition_json=request.definition); db.add(entity); await db.flush()
    return obj(entity, ["id", "name", "definition_json", "status"])


@router.post("/model-routes", status_code=status.HTTP_201_CREATED)
async def create_model_route(request: RouteCreateRequest, db: AsyncSession = Depends(get_db)):
    entity = EvaluationModelRoute(provider_name=request.provider_name, model_identifier=request.model_identifier, capabilities_json=request.capabilities, credential_ref=request.credential_ref, timeout_seconds=request.timeout_seconds); db.add(entity); await db.flush()
    return obj(entity, ["id", "provider_name", "model_identifier", "capabilities_json", "credential_ref", "timeout_seconds"])


@router.put("/model-routes/{route_id}")
async def update_model_route(route_id: str, request: RouteCreateRequest, db: AsyncSession = Depends(get_db)):
    entity = await db.get(EvaluationModelRoute, route_id)
    if not entity:
        raise HTTPException(404, "ModelRoute not found")
    entity.provider_name = request.provider_name
    entity.model_identifier = request.model_identifier
    entity.capabilities_json = request.capabilities
    entity.credential_ref = request.credential_ref
    entity.timeout_seconds = request.timeout_seconds
    await db.flush()
    available = entity.provider_name.lower() in {"offline", "crt_mko"} or EnvironmentSecretResolver().is_available(entity.credential_ref)
    return {**obj(entity, ["id", "provider_name", "model_identifier", "capabilities_json", "credential_ref", "timeout_seconds"]), "credential_available": available}


@router.delete("/model-routes/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_route(route_id: str, db: AsyncSession = Depends(get_db)):
    entity = await db.get(EvaluationModelRoute, route_id)
    if not entity:
        raise HTTPException(404, "ModelRoute not found")
    await db.delete(entity)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/evaluation-suites", status_code=status.HTTP_201_CREATED)
async def create_suite(request: SuiteCreateRequest, db: AsyncSession = Depends(get_db)):
    rule = {"quality_threshold": request.quality_threshold, "scoring_mode": request.scoring_mode}
    entity = EvaluationSuiteVersion(name=request.name, evaluators_json=[{"id": "judge", "criteria": [item.model_dump() for item in request.criteria]}], decision_rule_json=rule)
    db.add(entity); await db.flush(); return {"id": entity.id, "name": entity.name, "criteria": entity.evaluators_json[0]["criteria"], **rule}



@router.get("/prompts")
async def list_prompts(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(EvaluationPromptVersion).order_by(EvaluationPromptVersion.created_at.desc()))).scalars().all()
    return [obj(row, ["id", "name", "template", "version_number"]) for row in rows]

@router.get("/pipelines")
async def list_pipelines(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(EvaluationPipelineVersion).order_by(EvaluationPipelineVersion.created_at.desc()))).scalars().all()
    return [obj(row, ["id", "name", "definition_json", "status"]) for row in rows]

@router.get("/model-routes")
async def list_model_routes(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(EvaluationModelRoute).order_by(EvaluationModelRoute.created_at.desc()))).scalars().all()
    resolver = EnvironmentSecretResolver()
    return [{**obj(row, ["id", "provider_name", "model_identifier", "capabilities_json", "credential_ref", "timeout_seconds"]), "credential_available": row.provider_name.lower() in {"offline", "crt_mko"} or resolver.is_available(row.credential_ref)} for row in rows]

@router.get("/provider-models")
async def provider_models(provider_name: str, credential_ref: str | None = None):
    try:
        return await list_provider_models(provider_name, credential_ref)
    except ProviderExecutionError as exc:
        status_code = 422 if exc.code in {"unsupported_provider", "credential_unavailable"} else 504 if exc.code == "timeout" else 502
        raise HTTPException(status_code, {"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


@router.get("/evaluation-suites")
async def list_suites(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(EvaluationSuiteVersion).order_by(EvaluationSuiteVersion.created_at.desc()))).scalars().all()
    return [obj(row, ["id", "name", "evaluators_json", "decision_rule_json"]) for row in rows]
@router.post("/runs:estimate", response_model=RunEstimateResponse)
async def estimate_run(request: RunEstimateRequest, db: AsyncSession = Depends(get_db)):
    _, _, _, count = await resolve_run_inputs(request, db); candidate = count * len(request.prompt_version_ids) * len(request.candidate_route_ids)
    return RunEstimateResponse(dataset_item_count=count, candidate_calls=candidate, judge_calls=0, total_calls=candidate, policy=request.policy)


async def execute_background(run_id: str, item_ids: set[str] | None = None):
    async with async_session_maker() as db:
        await EvaluationRunner(db).execute(run_id, item_ids=item_ids)


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def create_run(request: RunCreateRequest, db: AsyncSession = Depends(get_db)):
    version, prompts, routes, count = await resolve_run_inputs(request, db)
    pipeline, suite = await db.get(EvaluationPipelineVersion, str(request.pipeline_version_id)), await db.get(EvaluationSuiteVersion, str(request.suite_version_id))
    if not pipeline or (request.suite_version_id and not suite): raise HTTPException(422, "PipelineVersion or EvaluationSuite was not found")
    definition = pipeline.definition_json
    nodes = definition.get('nodes', [])
    if len(nodes) != 1 or nodes[0].get('kind') != 'generate' or definition.get('edges'):
        raise HTTPException(422, 'This executor supports one generate node without edges')
    criteria = suite.evaluators_json[0].get("criteria", []) if suite and suite.evaluators_json else []
    snapshot = {"dataset_version": {"id": version.id, "schema": version.schema_json}, "pipeline": {"id": pipeline.id, "definition": pipeline.definition_json}, "prompts": [obj(p, ["id", "name", "template", "version_number"]) for p in prompts], "routes": [obj(r, ["id", "provider_name", "model_identifier", "capabilities_json", "credential_ref", "timeout_seconds"]) for r in routes], "suite": {"id": suite.id if suite else None, "criteria": criteria, "quality_threshold": suite.decision_rule_json.get("quality_threshold", 0) if suite else None}, "policy": request.policy.model_dump(mode="json")}
    snapshot['kind'] = 'generation'
    run = EvaluationRun(snapshot_json=snapshot, progress_json={"completed": 0, "total": count * len(prompts) * len(routes), "failed": 0}); db.add(run); await db.flush()
    source_items = (await db.execute(select(EvaluationDatasetItem).where(EvaluationDatasetItem.dataset_version_id == version.id))).scalars().all()
    db.add_all([EvaluationRunItem(run_id=run.id, dataset_item_id=item.id, prompt_version_id=prompt.id, route_id=route.id) for item in source_items for prompt in prompts for route in routes]); await db.flush()
    await db.commit()
    asyncio.create_task(execute_background(run.id))
    return {"id": run.id, "status": run.status, "progress": run.progress_json, "snapshot": snapshot}


@router.get("/runs")
async def list_runs(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()))).scalars().all()
    return [{**obj(row, ["id", "status", "progress_json", "created_at", "started_at", "completed_at"]), 'kind': row.snapshot_json.get('kind', 'legacy'), 'source_run_id': row.snapshot_json.get('source_run_id')} for row in rows]


@router.get('/runs/{source_id}/evaluations')
async def list_evaluations(source_id: str, db: AsyncSession = Depends(get_db)):
    if not await db.get(EvaluationRun, source_id):
        raise HTTPException(404, 'Run not found')
    rows = (await db.execute(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()))).scalars().all()
    return [obj(row, ['id', 'status', 'progress_json', 'created_at']) for row in rows if row.snapshot_json.get('kind') == 'evaluation' and row.snapshot_json.get('source_run_id') == source_id]


@router.post('/runs/{source_id}/evaluations', status_code=status.HTTP_202_ACCEPTED)
async def create_evaluation(source_id: str, request: RunEvaluationRequest, db: AsyncSession = Depends(get_db)):
    source = await db.get(EvaluationRun, source_id)
    if not source:
        raise HTTPException(404, 'Source Run not found')
    if source.snapshot_json.get('kind') == 'evaluation' or source.status not in {'completed', 'completed_with_errors', 'cancelled', 'failed'}:
        raise HTTPException(409, 'Evaluation requires a finished generation Run')
    route = await db.get(EvaluationModelRoute, str(request.judge_route_id))
    prompt = await db.get(EvaluationPromptVersion, str(request.judge_prompt_id))
    suite = await db.get(EvaluationSuiteVersion, str(request.suite_version_id))
    if not route or not prompt or not suite:
        raise HTTPException(422, 'Judge route, prompt or evaluation suite not found')
    if 'text' not in route.capabilities_json.get('modalities', ['text']):
        raise HTTPException(422, 'Judge route must support text')
    if route.provider_name.lower() not in {'offline', 'crt_mko'} and not EnvironmentSecretResolver().is_available(route.credential_ref):
        raise HTTPException(422, 'Judge credential is unavailable')
    if 'output' not in TOKEN.findall(prompt.template):
        raise HTTPException(422, 'Judge prompt must include {{output}}')
    criteria = suite.evaluators_json[0].get('criteria', []) if suite.evaluators_json else []
    if not criteria:
        raise HTTPException(422, 'Evaluation suite requires criteria')
    source_items = (await db.execute(select(EvaluationRunItem).where(EvaluationRunItem.run_id == source_id))).scalars().all()
    inputs, items = {}, []
    assessment_id = str(uuid4())
    for item in source_items:
        if item.status != 'completed' or not isinstance((item.output_json or {}).get('text'), str) or not item.output_json['text'].strip():
            continue
        dataset_item = await db.get(EvaluationDatasetItem, item.dataset_item_id)
        if not dataset_item:
            raise HTTPException(422, 'Source DatasetItem is unavailable')
        new_id = str(uuid4())
        captured = {'source_item_id': item.id, 'input': dataset_item.input_json, 'reference': dataset_item.reference_json, 'output': item.output_json['text']}
        try:
            judge_prompt(prompt.template, captured, criteria)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        inputs[new_id] = captured
        items.append(EvaluationRunItem(id=new_id, run_id=assessment_id, dataset_item_id=item.dataset_item_id, prompt_version_id=item.prompt_version_id, route_id=item.route_id))
    if not items:
        raise HTTPException(422, 'Source Run has no completed text answers to evaluate')
    snapshot = {
        'kind': 'evaluation', 'source_run_id': source_id,
        'dataset_version': source.snapshot_json.get('dataset_version'),
        'routes': source.snapshot_json.get('routes', []), 'prompts': source.snapshot_json.get('prompts', []),
        'judge': {'route': obj(route, ['id', 'provider_name', 'model_identifier', 'credential_ref', 'timeout_seconds', 'capabilities_json']), 'prompt': obj(prompt, ['id', 'name', 'template', 'version_number'])},
        'suite': {'id': suite.id, 'criteria': criteria, 'quality_threshold': suite.decision_rule_json.get('quality_threshold', 0), 'scoring_mode': suite.decision_rule_json.get('scoring_mode', 'weighted')},
        'evaluation_inputs': inputs,
        'policy': {'max_output_tokens': request.max_output_tokens},
    }
    run = EvaluationRun(id=assessment_id, snapshot_json=snapshot, progress_json={'completed': 0, 'total': len(items), 'failed': 0})
    db.add(run)
    await db.flush()
    db.add_all(items)
    await db.commit()
    asyncio.create_task(execute_background(run.id))
    return {'id': run.id, 'status': run.status, 'source_run_id': source_id, 'judge_calls': len(items)}


@router.post("/runs/{run_id}:retry", status_code=202)
async def retry_run(run_id: str, request: RunRetryRequest, db: AsyncSession = Depends(get_db)):
    run = await db.get(EvaluationRun, run_id)
    if not run: raise HTTPException(404, 'Run not found')
    if run.snapshot_json.get('kind') not in {'generation', 'evaluation'}:
        raise HTTPException(409, 'Повтор старого запуска без полного снимка настроек не поддерживается.')
    terminal = {'completed', 'completed_with_errors', 'failed', 'cancelled'}
    if run.status not in terminal:
        raise HTTPException(409, 'Дождитесь завершения запуска перед повтором.')
    rows = (await db.execute(select(EvaluationRunItem).where(EvaluationRunItem.run_id == run_id))).scalars().all()
    ids = {str(value) for value in request.item_ids}
    if ids - {row.id for row in rows}:
        raise HTTPException(422, 'Выбраны записи другого запуска или отсутствующие записи.')
    claimed = await db.execute(update(EvaluationRun).where(EvaluationRun.id == run_id, EvaluationRun.status.in_(terminal)).values(status='queued', completed_at=None).execution_options(synchronize_session=False))
    if claimed.rowcount != 1:
        raise HTTPException(409, 'Повтор уже запущен.')
    for row in rows:
        if row.id in ids:
            row.status, row.output_json, row.error_json = 'queued', None, None
    await db.flush()
    await db.refresh(run)
    run.progress_json = {'completed': sum(r.status in {'completed', 'failed'} for r in rows), 'total': len(rows), 'failed': sum(r.status == 'failed' for r in rows)}
    await db.commit()
    asyncio.create_task(execute_background(run_id, item_ids=ids))
    return {'id': run_id, 'status': 'queued', 'retry_calls': len(ids)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await db.get(EvaluationRun, run_id)
    if not run: raise HTTPException(404, "Run not found")
    return obj(run, ["id", "status", "progress_json", "snapshot_json", "created_at", "started_at", "completed_at"])



async def build_run_details(run_id: str, db: AsyncSession):
    run = await db.get(EvaluationRun, run_id)
    captured = run.snapshot_json.get('evaluation_inputs', {}) if run else {}
    items = (await db.execute(select(EvaluationRunItem).where(EvaluationRunItem.run_id == run_id))).scalars().all()
    payload = []
    for item in items:
        source = await db.get(EvaluationDatasetItem, item.dataset_item_id)
        attempts = (await db.execute(select(EvaluationAttempt).where(EvaluationAttempt.run_item_id == item.id))).scalars().all()
        results = (await db.execute(select(EvaluationResult).where(EvaluationResult.run_item_id == item.id))).scalars().all()
        attempts.sort(key=lambda a: a.route_snapshot_json.get('sequence', 0))
        results.sort(key=lambda r: (r.value_json or {}).get('_attempt', 0), reverse=True)
        latest_sequence = max((a.route_snapshot_json.get('sequence', 0) for a in attempts), default=0)
        current_results = [r for r in results if (r.value_json or {}).get('_attempt', 0) == latest_sequence] if item.status in {'completed', 'failed'} else []
        payload.append({
            **obj(item, ["id", "dataset_item_id", "prompt_version_id", "route_id", "status", "output_json", "error_json"]),
            "dataset_item": obj(source, ["external_id", "input_json", "reference_json", "metadata_json", "tags_json"]) if source else None,
            'evaluation_source': captured.get(item.id),
            "attempts": [obj(attempt, ["id", "node_id", "kind", "latency_ms", "output_json", "error_json"]) for attempt in attempts],
            "results": [obj(result, ["id", "evaluator_id", "status", "value_json", "numeric_score"]) for result in current_results],
            "result_history": [obj(result, ["id", "evaluator_id", "status", "value_json", "numeric_score"]) for result in results],
        })
    return payload


@router.get("/runs/{run_id}/details")
async def get_run_details(run_id: str, db: AsyncSession = Depends(get_db)):
    if not await db.get(EvaluationRun, run_id):
        raise HTTPException(404, "Run not found")
    return await build_run_details(run_id, db)


@router.get("/runs/{run_id}/export")
async def export_run(run_id: str, format: str = "json", db: AsyncSession = Depends(get_db)):
    run = await db.get(EvaluationRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    if format not in {"json", "csv"}:
        raise HTTPException(422, "Export format must be json or csv")
    details = await build_run_details(run_id, db)
    disposition = {"Content-Disposition": f'attachment; filename="run-{run_id}.{format}"'}
    if format == "json":
        bundle = {
            "run": obj(run, ["id", "status", "progress_json", "snapshot_json", "created_at", "started_at", "completed_at"]),
            "items": details,
        }
        return Response(json.dumps(bundle, ensure_ascii=False, indent=2, default=str), media_type="application/json", headers=disposition)
    output = io.StringIO(newline="")
    fields = ["run_id", "run_item_id", "external_id", "prompt_version_id", "route_id", "status", "output", "error", "score", "latency_ms", "criteria_scores", "criteria_scales"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for item in details:
        writer.writerow({
            "run_id": run.id,
            "run_item_id": item["id"],
            "external_id": (item["dataset_item"] or {}).get("external_id", ""),
            "prompt_version_id": item["prompt_version_id"],
            "route_id": item["route_id"],
            "status": item["status"],
            "output": json.dumps(item["output_json"], ensure_ascii=False) if item["output_json"] is not None else "",
            "error": json.dumps(item["error_json"], ensure_ascii=False) if item["error_json"] is not None else "",
            "score": next((result["numeric_score"] for result in item["results"] if result["numeric_score"] is not None), ""),
            "latency_ms": sum(attempt["latency_ms"] or 0 for attempt in item["attempts"]),
            "criteria_scores": json.dumps((item["results"][0]["value_json"] or {}).get("scores", {}), ensure_ascii=False) if item["results"] else "",
            "criteria_scales": json.dumps({c["key"]: [c.get("min_score", 0), c.get("max_score", 1)] for c in run.snapshot_json.get("suite", {}).get("criteria", [])}, ensure_ascii=False),
        })
    return Response(output.getvalue(), media_type="text/csv; charset=utf-8", headers=disposition)


@router.get("/runs/{run_id}/items")
async def get_run_items(run_id: str, db: AsyncSession = Depends(get_db)):
    if not await db.get(EvaluationRun, run_id): raise HTTPException(404, "Run not found")
    rows = (await db.execute(select(EvaluationRunItem).where(EvaluationRunItem.run_id == run_id))).scalars().all()
    return [obj(row, ["id", "dataset_item_id", "prompt_version_id", "route_id", "status", "output_json", "error_json"]) for row in rows]


@router.post("/runs/{run_id}:cancel")
async def cancel_run(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await db.get(EvaluationRun, run_id)
    if not run: raise HTTPException(404, "Run not found")
    if run.status in {'cancelled', 'cancelling'}:
        return {'id': run.id, 'status': run.status}
    queued = await db.execute(update(EvaluationRun).where(EvaluationRun.id == run_id, EvaluationRun.status == 'queued').values(status='cancelled', completed_at=datetime.utcnow()).execution_options(synchronize_session=False))
    if queued.rowcount:
        await db.execute(update(EvaluationRunItem).where(EvaluationRunItem.run_id == run_id, EvaluationRunItem.status == 'queued').values(status='cancelled'))
    else:
        running = await db.execute(update(EvaluationRun).where(EvaluationRun.id == run_id, EvaluationRun.status == 'running').values(status='cancelling').execution_options(synchronize_session=False))
        if not running.rowcount: raise HTTPException(409, 'Запуск уже завершён.')
    await db.commit()
    await db.refresh(run)
    return {'id': run.id, 'status': run.status}
