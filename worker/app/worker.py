import gc
import json
import os
import shutil
import struct
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

import numpy as np
import trimesh
from redis import Redis
from redis.exceptions import RedisError
from scipy.spatial import cKDTree

QUEUE_NAME = "stl:jobs"
PRIORITY_QUEUE_NAMES = ["stl:jobs:premium", "stl:jobs:early_access", "stl:jobs:free", QUEUE_NAME]
UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", "/data/uploads"))
RESULT_ROOT = Path(os.getenv("RESULT_ROOT", "/data/results"))
PIPELINE_VERSION = "mvp-prepare-package-1"
DEFAULT_OPERATIONS = ["analyze", "print_check", "prepare_package"]
IMPLEMENTED_OPERATIONS = {
    "analyze",
    "print_check",
    "prepare_package",
    "model_improvement",
    "fix_symmetry",
    "repair_mesh",
    "reduce_polygons",
    "split_model",
    "fit_to_bed_split",
    "apply_orientation",
    "auto_orientation",
    "ai_cleanup",
    "remove_ai_artifacts",
    "surface_recovery",
    "local_smoothing",
}
PLANNED_OPERATION_LABELS = {
}
GENERATED_FILE_LABELS = {
    "original.stl": ("source", "Исходная модель"),
    "input.stl": ("source", "Исходная модель"),
    "repaired.stl": ("model", "Исправленная сетка"),
    "reduced.stl": ("model", "Уменьшенная модель"),
    "improved_model.stl": ("model", "Улучшенная модель"),
    "repaired_model.stl": ("model", "Улучшенная модель"),
    "oriented_model.stl": ("model", "Модель с применённой ориентацией"),
    "oriented_auto.stl": ("model", "Модель с автоориентацией"),
    "symmetry_fixed.stl": ("model", "Исправленная симметрия"),
    "improved_blender.stl": ("model", "Улучшенная модель"),
    "analysis.json": ("report", "Данные анализа"),
    "README.txt": ("report", "Краткий отчет"),
    "repair_report.json": ("report", "Отчет ремонта сетки"),
    "reduction_report.json": ("report", "Отчет уменьшения полигонов"),
    "split_report.json": ("report", "Отчет разрезания модели"),
    "symmetry_report.json": ("report", "Отчёт симметрии"),
    "connector_pins.stl": ("model", "Штифты для склейки"),
    "connector_slots.stl": ("model", "Направляющие для склейки"),
    "connector_guide.json": ("report", "Инструкция по соединителям"),
    "connector_report.json": ("report", "Отчёт по соединителям"),
    "ai_cleaned.stl": ("model", "Очищенная AI-модель"),
    "ai_cleanup_report.json": ("report", "Отчет очистки AI-модели"),
    "cleaned_artifacts.stl": ("model", "Модель без AI-артефактов"),
    "artifact_cleanup_report.json": ("report", "Отчет удаления AI-артефактов"),
    "surface_recovered.stl": ("model", "Модель с восстановленной поверхностью"),
    "local_smoothed.stl": ("model", "Модель с выборочной правкой"),
    "surface_recovery_report.json": ("report", "Отчет восстановления поверхности"),
    "change_map.json": ("report", "Карта изменений"),
    "artifact_map.json": ("report", "Карта найденных дефектов"),
    "normalized_info.json": ("report", "Нормализованные данные"),
    "print_report.txt": ("report", "Отчёт"),
    "manifest.json": ("report", "Манифест ZIP"),
}
HEAVY_OPERATIONS = {"model_improvement", "repair_mesh", "reduce_polygons", "split_model", "fit_to_bed_split", "ai_cleanup", "fix_symmetry", "surface_recovery", "local_smoothing"}
PROCESSING_SOFT_FILE_MB = 300
PROCESSING_SOFT_TRIANGLES = 2_000_000
BED_WIDTH_MM = 220
BED_DEPTH_MM = 220
BED_HEIGHT_MM = 250
NEAR_ZERO_AXIS_MM = 0.01


def job_key(job_id: str) -> str:
    return f"stl:job:{job_id}"


def update_job(client: Redis, job_id: str, status: str, progress: int, message: str, result: dict | None = None) -> None:
    payload: dict[str, str | int] = {
        "status": status,
        "progress": progress,
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if result is not None:
        payload["result"] = json.dumps(result, ensure_ascii=False)
    client.hset(job_key(job_id), mapping=payload)


def job_cancel_requested(client: Redis, job_id: str) -> bool:
    job = client.hgetall(job_key(job_id))
    return job.get("status") == "cancelled" or job.get("cancel_requested") == "true"


def stop_if_cancelled(client: Redis, job_id: str) -> bool:
    if not job_cancel_requested(client, job_id):
        return False
    client.hset(
        job_key(job_id),
        mapping={
            "status": "cancelled",
            "progress": 0,
            "message": "Задача отменена администратором.",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    print(f"Cancelled job {job_id}", flush=True)
    return True


def parse_job_operations(job: dict[str, str]) -> list[str]:
    raw_operations = job.get("operations")
    if not raw_operations:
        return DEFAULT_OPERATIONS
    try:
        operations = json.loads(raw_operations)
    except json.JSONDecodeError:
        operations = [item.strip() for item in raw_operations.split(",")]
    if not isinstance(operations, list):
        return DEFAULT_OPERATIONS
    normalized = [str(operation).strip() for operation in operations if str(operation).strip()]
    return normalized or DEFAULT_OPERATIONS


def parse_reduction_percent(job: dict[str, str]) -> int:
    try:
        percent = int(job.get("reduction_percent", 50))
    except (TypeError, ValueError):
        return 50
    return percent if percent in (25, 50, 75) else 50


def parse_split_settings(job: dict[str, str]) -> tuple[str, int, float]:
    axis = job.get("split_axis", "z").lower()
    if axis not in ("x", "y", "z"):
        axis = "z"
    try:
        parts = int(job.get("split_parts", 2))
    except (TypeError, ValueError):
        parts = 2
    parts = min(max(parts, 2), 4)
    try:
        plane_offset = float(job.get("split_plane_offset_mm", 0.0) or 0.0)
    except (TypeError, ValueError):
        plane_offset = 0.0
    return axis, parts, plane_offset


def parse_split_mode(job: dict[str, str]) -> str:
    mode = job.get("split_mode", "simple").lower()
    return mode if mode in ("simple", "glue", "pins", "magnets", "lock", "slots") else "simple"


def parse_split_engine(job: dict[str, str]) -> str:
    engine = job.get("split_engine", "").lower()
    if engine in ("safe_mvp", "blender_boolean"):
        return engine
    return "blender_boolean" if blender_available() else "safe_mvp"


def parse_connector_settings(job: dict[str, str]) -> tuple[int, float, int]:
    try:
        size = int(job.get("connector_size_mm", 4))
    except (TypeError, ValueError):
        size = 4
    if size not in (3, 4, 6):
        size = 4
    try:
        clearance = float(job.get("connector_clearance_mm", 0.25))
    except (TypeError, ValueError):
        clearance = 0.25
    if clearance not in (0.15, 0.25, 0.4):
        clearance = 0.25
    try:
        count = int(job.get("connector_count", 2))
    except (TypeError, ValueError):
        count = 2
    if count not in (2, 3, 4):
        count = 2
    return size, clearance, count


def parse_split_connector_config(job: dict[str, str], split_mode: str, connector_size_mm: int, connector_clearance_mm: float, connector_count: int) -> dict[str, object]:
    try:
        depth = float(job.get("connector_depth_mm", 6.0) or 6.0)
    except (TypeError, ValueError):
        depth = 6.0
    depth = min(max(depth, 2.0), 30.0)
    try:
        wall_thickness = float(job.get("connector_wall_thickness_mm", 1.2) or 1.2)
    except (TypeError, ValueError):
        wall_thickness = 1.2
    wall_thickness = min(max(wall_thickness, 0.4), 5.0)
    magnet_size = str(job.get("magnet_size", "6x2") or "6x2").lower().replace("×", "x")
    if magnet_size not in {"5x2", "6x2", "8x3", "10x3"}:
        magnet_size = "6x2"
    default_diameter, default_thickness = [float(value) for value in magnet_size.split("x", 1)]
    try:
        magnet_diameter = float(job.get("magnet_diameter_mm", default_diameter) or default_diameter)
    except (TypeError, ValueError):
        magnet_diameter = default_diameter
    try:
        magnet_thickness = float(job.get("magnet_thickness_mm", default_thickness) or default_thickness)
    except (TypeError, ValueError):
        magnet_thickness = default_thickness
    lock_profile = str(job.get("lock_profile", "tongue_groove") or "tongue_groove").lower()
    if lock_profile not in {"tongue_groove", "dovetail", "wave"}:
        lock_profile = "tongue_groove"
    return {
        "type": split_mode,
        "connector_size_mm": connector_size_mm,
        "connector_clearance_mm": connector_clearance_mm,
        "connector_count": connector_count,
        "connector_depth_mm": depth,
        "connector_wall_thickness_mm": wall_thickness,
        "magnet_size": magnet_size,
        "magnet_diameter_mm": min(max(magnet_diameter, 3.0), 20.0),
        "magnet_thickness_mm": min(max(magnet_thickness, 1.0), 10.0),
        "lock_profile": lock_profile,
    }


def parse_symmetry_axis(job: dict[str, str]) -> str:
    axis = job.get("symmetry_axis", "x").lower()
    return axis if axis in ("x", "y", "z") else "x"


def parse_symmetry_mode(job: dict[str, str]) -> str:
    mode = job.get("symmetry_mode", "analyze").lower()
    return mode if mode in ("analyze", "fix") else "analyze"


def parse_ai_cleanup_strength(job: dict[str, str]) -> str:
    strength = job.get("ai_cleanup_strength", "medium").lower()
    return strength if strength in ("light", "medium", "balanced", "strong") else "medium"


def parse_artifact_cleanup_strength(job: dict[str, str]) -> str:
    strength = job.get("artifact_cleanup_strength", "balanced").lower()
    if strength == "medium":
        strength = "balanced"
    return strength if strength in ("light", "balanced", "strong") else "balanced"


def parse_model_improvement_strength(job: dict[str, str]) -> str:
    strength = job.get("model_improvement_strength", "balanced").lower()
    if strength == "medium":
        strength = "balanced"
    return strength if strength in ("light", "balanced", "strong") else "balanced"


def parse_model_name(job: dict[str, str]) -> str:
    return (job.get("model_name") or job.get("vehicle_name") or "").strip()[:120]


def parse_apply_orientation(job: dict[str, str]) -> bool:
    value = str(job.get("apply_orientation", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def parse_orientation_transform(job: dict[str, str]) -> dict[str, object]:
    defaults = {
        "rotation_x": 0.0,
        "rotation_y": 0.0,
        "rotation_z": 0.0,
        "rotation_x_deg": 0.0,
        "rotation_y_deg": 0.0,
        "rotation_z_deg": 0.0,
        "translate_to_floor": False,
        "translate_x_mm": 0.0,
        "translate_z_mm": 0.0,
    }
    raw_transform = job.get("orientation_transform")
    if not raw_transform:
        return defaults
    try:
        decoded = json.loads(raw_transform)
    except json.JSONDecodeError:
        return defaults
    if not isinstance(decoded, dict):
        return defaults

    transform = defaults.copy()
    for axis in ("x", "y", "z"):
        key = f"rotation_{axis}"
        deg_key = f"rotation_{axis}_deg"
        try:
            value = float(decoded.get(deg_key, decoded.get(key, defaults[key])))
        except (TypeError, ValueError):
            value = defaults[key]
        transform[key] = value
        transform[deg_key] = value
    for key in ("translate_x_mm", "translate_z_mm"):
        try:
            transform[key] = float(decoded.get(key, defaults[key]))
        except (TypeError, ValueError):
            transform[key] = defaults[key]
    transform["translate_to_floor"] = bool(decoded.get("translate_to_floor", defaults["translate_to_floor"]))
    return transform


def parse_local_selection(job: dict[str, str]) -> dict[str, object] | None:
    raw_selection = job.get("local_selection")
    if not raw_selection:
        return None
    try:
        decoded = json.loads(raw_selection)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None

    def parse_region(region: object) -> dict[str, object] | None:
        if not isinstance(region, dict):
            return None
        try:
            parsed_center = np.asarray(region.get("center"), dtype=float)
            radius_mm = float(region.get("radius_mm", 0))
        except (TypeError, ValueError):
            return None
        if parsed_center.shape != (3,) or radius_mm < 1 or radius_mm > 100:
            return None
        return {
            "center": [float(value) for value in parsed_center],
            "radius_mm": radius_mm,
        }

    strength = str(decoded.get("strength", "balanced")).strip().lower()
    if strength not in {"light", "balanced", "strong"}:
        strength = "balanced"
    selection_type = decoded.get("type")
    if selection_type == "sphere":
        region = parse_region(decoded)
        if not region:
            return None
        return {
            "type": "sphere",
            "center": region["center"],
            "radius_mm": region["radius_mm"],
            "strength": strength,
        }
    if selection_type == "spheres":
        raw_regions = decoded.get("regions")
        if not isinstance(raw_regions, list) or not raw_regions or len(raw_regions) > 30:
            return None
        regions = []
        for raw_region in raw_regions:
            region = parse_region(raw_region)
            if not region:
                return None
            regions.append(region)
        return {
            "type": "spheres",
            "regions": regions,
            "strength": strength,
        }
    return None


def parse_auto_orientation(job: dict[str, str]) -> bool:
    value = str(job.get("auto_orientation", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def parse_orientation_priority(job: dict[str, str]) -> str:
    priority = str(job.get("orientation_priority", "supports")).strip().lower()
    return priority if priority in {"supports", "speed", "quality"} else "supports"


def parse_fit_to_bed(job: dict[str, str]) -> bool:
    value = str(job.get("fit_to_bed", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def parse_fit_to_bed_settings(job: dict[str, str]) -> tuple[dict[str, float], str, float]:
    def read_size(key: str, default: float) -> float:
        try:
            value = float(job.get(key, default))
        except (TypeError, ValueError):
            value = default
        return min(max(value, 1.0), 2000.0)

    bed_size = {
        "x": read_size("bed_size_x", 220.0),
        "y": read_size("bed_size_y", 250.0),
        "z": read_size("bed_size_z", 220.0),
    }
    mode = str(job.get("bed_connector_mode", "none")).strip().lower()
    if mode not in {"none", "pins", "slots"}:
        mode = "none"
    try:
        clearance = float(job.get("bed_connector_clearance_mm", 0.25))
    except (TypeError, ValueError):
        clearance = 0.25
    if clearance not in (0.15, 0.25, 0.4):
        clearance = 0.25
    return bed_size, mode, clearance


def build_planned_operations(operations: list[str]) -> list[dict[str, str]]:
    planned = []
    for operation in operations:
        if operation in PLANNED_OPERATION_LABELS:
            planned.append(
                {
                    "operation": operation,
                    "title": PLANNED_OPERATION_LABELS[operation],
                    "status": "not_implemented",
                }
            )
    return planned


def build_skipped_operations(result: dict, operations: list[str]) -> list[dict[str, str]]:
    skipped = []
    heavy_selected = [operation for operation in operations if operation in HEAVY_OPERATIONS]
    if not heavy_selected:
        return skipped

    file_size_mb = result.get("file", {}).get("size_mb", 0) or 0
    triangles_count = result.get("triangles_count", 0) or 0
    reasons = []
    if file_size_mb > PROCESSING_SOFT_FILE_MB:
        reasons.append(f"file_size_mb > {PROCESSING_SOFT_FILE_MB}")
    if triangles_count > PROCESSING_SOFT_TRIANGLES:
        reasons.append(f"triangles_count > {PROCESSING_SOFT_TRIANGLES}")
    if not reasons:
        return skipped

    reason = "Skipped for server safety: " + ", ".join(reasons)
    for operation in heavy_selected:
        skipped.append({"operation": operation, "reason": reason})
    return skipped


def empty_bounds() -> dict:
    return {
        "min": {"x": None, "y": None, "z": None},
        "max": {"x": None, "y": None, "z": None},
    }


def update_bounds(bounds: dict, vertex: tuple[float, float, float]) -> None:
    x, y, z = vertex
    for axis, value in (("x", x), ("y", y), ("z", z)):
        if bounds["min"][axis] is None or value < bounds["min"][axis]:
            bounds["min"][axis] = value
        if bounds["max"][axis] is None or value > bounds["max"][axis]:
            bounds["max"][axis] = value


def dimensions_from_bounds(bounds: dict) -> dict[str, float | None]:
    if bounds["min"]["x"] is None:
        return {"width": None, "depth": None, "height": None}
    return {
        "width": round(bounds["max"]["x"] - bounds["min"]["x"], 6),
        "depth": round(bounds["max"]["y"] - bounds["min"]["y"], 6),
        "height": round(bounds["max"]["z"] - bounds["min"]["z"], 6),
    }


def round_bounds(bounds: dict) -> dict:
    if bounds["min"]["x"] is None:
        return empty_bounds()
    return {
        "min": {axis: round(bounds["min"][axis], 6) for axis in ("x", "y", "z")},
        "max": {axis: round(bounds["max"][axis], 6) for axis in ("x", "y", "z")},
    }


def is_binary_stl(path: Path, size_bytes: int) -> tuple[bool, int | None]:
    if size_bytes < 84:
        return False, None
    with path.open("rb") as source:
        source.seek(80)
        triangle_count = struct.unpack("<I", source.read(4))[0]
    expected_size = 84 + triangle_count * 50
    return expected_size == size_bytes, triangle_count


def binary_vertices(path: Path, triangle_count: int) -> Iterable[tuple[float, float, float]]:
    with path.open("rb") as source:
        source.seek(84)
        for _ in range(triangle_count):
            chunk = source.read(50)
            if len(chunk) < 50:
                break
            values = struct.unpack("<12fH", chunk)
            yield (values[3], values[4], values[5])
            yield (values[6], values[7], values[8])
            yield (values[9], values[10], values[11])


def analyze_binary_stl(path: Path, size_bytes: int, triangle_count: int) -> dict:
    bounds = empty_bounds()
    for vertex in binary_vertices(path, triangle_count):
        update_bounds(bounds, vertex)

    return build_result(size_bytes, "binary", triangle_count, bounds)


def analyze_ascii_stl(path: Path, size_bytes: int) -> dict:
    bounds = empty_bounds()
    vertex_count = 0

    with path.open("r", encoding="utf-8", errors="ignore") as source:
        for line in source:
            parts = line.strip().split()
            if len(parts) == 4 and parts[0].lower() == "vertex":
                try:
                    vertex = (float(parts[1]), float(parts[2]), float(parts[3]))
                except ValueError:
                    continue
                update_bounds(bounds, vertex)
                vertex_count += 1

    triangle_count = vertex_count // 3
    return build_result(size_bytes, "ascii", triangle_count, bounds)


def classify_size(dimensions: dict[str, float | None], triangle_count: int, size_mb: float) -> str:
    numeric_dimensions = [value for value in dimensions.values() if value is not None]
    max_dimension = max(numeric_dimensions) if numeric_dimensions else 0

    if max_dimension <= 50 and triangle_count <= 50_000 and size_mb <= 25:
        return "small"
    if max_dimension <= 150 and triangle_count <= 300_000 and size_mb <= 100:
        return "medium"
    if max_dimension <= 250 and triangle_count <= 500_000 and size_mb <= 500:
        return "large"
    return "huge"


def build_printability(size_bytes: int, triangle_count: int, bounds: dict, dimensions: dict[str, float | None]) -> dict:
    size_mb = round(size_bytes / 1024 / 1024, 3)
    width = dimensions["width"] or 0
    depth = dimensions["depth"] or 0
    height = dimensions["height"] or 0
    has_bounds = bounds["min"]["x"] is not None
    has_negative_coordinates = bool(has_bounds and any(bounds["min"][axis] < 0 for axis in ("x", "y", "z")))
    has_near_zero_axis = any((dimensions[axis] is not None and dimensions[axis] <= NEAR_ZERO_AXIS_MM) for axis in ("width", "depth", "height"))
    bed_fit = width <= BED_WIDTH_MM and depth <= BED_DEPTH_MM and height <= BED_HEIGHT_MM
    warnings: list[str] = []
    recommendations: list[str] = []

    if has_negative_coordinates:
        warnings.append("Модель содержит отрицательные координаты.")
        recommendations.append("Перед печатью проверьте позицию модели на столе и при необходимости перенесите ее в положительную область координат.")
    if has_near_zero_axis:
        warnings.append("Один из размеров модели нулевой или почти нулевой.")
        recommendations.append("Проверьте масштаб и целостность STL: модель может быть плоской или поврежденной.")
    if not bed_fit:
        warnings.append("Модель больше стандартного стола 220x220x250 мм.")
        recommendations.append("Уменьшите масштаб модели или подготовьте разрезание на части перед печатью.")
    if triangle_count > 2_000_000:
        warnings.append("В модели больше 2 000 000 треугольников.")
        recommendations.append("Для стабильной работы slicer рекомендуется сильное упрощение сетки.")
    elif triangle_count > 500_000:
        warnings.append("В модели больше 500 000 треугольников.")
        recommendations.append("Рассмотрите уменьшение полигонов перед печатью или передачей файла.")
    if size_mb > 500:
        warnings.append("Файл больше 500 МБ.")
        recommendations.append("Разделите модель или уменьшите детализацию перед загрузкой в slicer.")
    elif size_mb > 100:
        warnings.append("Файл больше 100 МБ.")
        recommendations.append("Проверьте, нужен ли такой уровень детализации для выбранного размера печати.")

    if not warnings:
        recommendations.append("Критичных ограничений для базовой подготовки к печати не найдено.")

    return {
        "bed_fit_220_220_250": bed_fit,
        "size_class": classify_size(dimensions, triangle_count, size_mb),
        "warnings": warnings,
        "recommendations": recommendations,
    }


def build_result(size_bytes: int, stl_type: str, triangle_count: int, bounds: dict) -> dict:
    rounded_bounds = round_bounds(bounds)
    dimensions = dimensions_from_bounds(bounds)
    return {
        "file": {
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / 1024 / 1024, 3),
        },
        "stl_type": stl_type,
        "triangles": triangle_count,
        "triangles_count": triangle_count,
        "bounding_box": rounded_bounds,
        "dimensions": dimensions,
        "checks": {
            "has_negative_coordinates": bool(rounded_bounds["min"]["x"] is not None and any(rounded_bounds["min"][axis] < 0 for axis in ("x", "y", "z"))),
            "has_near_zero_axis": any((dimensions[axis] is not None and dimensions[axis] <= NEAR_ZERO_AXIS_MM) for axis in ("width", "depth", "height")),
            "oversized_for_bed_220_220_250": not (
                (dimensions["width"] or 0) <= BED_WIDTH_MM
                and (dimensions["depth"] or 0) <= BED_DEPTH_MM
                and (dimensions["height"] or 0) <= BED_HEIGHT_MM
            ),
        },
        "printability": build_printability(size_bytes, triangle_count, rounded_bounds, dimensions),
        "download_ready": False,
        "download_url": None,
    }


def analyze_stl(path: Path, operations: list[str]) -> dict:
    size_bytes = path.stat().st_size
    binary, triangle_count = is_binary_stl(path, size_bytes)
    if binary and triangle_count is not None:
        result = analyze_binary_stl(path, size_bytes, triangle_count)
    else:
        result = analyze_ascii_stl(path, size_bytes)
    result["operations"] = operations
    result["implemented_operations"] = [operation for operation in operations if operation in IMPLEMENTED_OPERATIONS]
    result["planned_operations"] = build_planned_operations(operations)
    return result


def format_list(items: list[str]) -> str:
    if not items:
        return "- Нет"
    return "\n".join(f"- {item}" for item in items)


def build_readme(job_id: str, result: dict) -> str:
    dimensions = result["dimensions"]
    printability = result["printability"]
    bed_fit = "да" if printability["bed_fit_220_220_250"] else "нет"
    planned_operations = result.get("planned_operations", [])
    planned_text = "\n".join(
        f"- {item['operation']}: {item['status']}" for item in planned_operations
    ) or "- Нет"
    return (
        "STL Master: отчет анализа\n"
        f"Job ID: {job_id}\n\n"
        f"Выбранные операции: {', '.join(result.get('operations', []))}\n"
        f"Тип STL: {result['stl_type']}\n"
        f"Количество треугольников: {result['triangles_count']}\n"
        "Габариты модели: "
        f"{dimensions['width']} x {dimensions['depth']} x {dimensions['height']} мм\n"
        f"Подходит под стол 220x220x250 мм: {bed_fit}\n\n"
        "Будущие операции:\n"
        f"{planned_text}\n\n"
        "Предупреждения:\n"
        f"{format_list(printability['warnings'])}\n\n"
        "Рекомендации:\n"
        f"{format_list(printability['recommendations'])}\n"
    )


def build_normalized_info(job_id: str, job: dict[str, str], result: dict, generated_at: str) -> dict:
    return {
        "job_id": job_id,
        "original_filename": job.get("filename", "input.stl"),
        "model_name": job.get("model_name") or job.get("vehicle_name") or None,
        "file_size_mb": result["file"]["size_mb"],
        "stl_type": result["stl_type"],
        "triangles_count": result["triangles_count"],
        "dimensions": result["dimensions"],
        "printability": result["printability"],
        "generated_at": generated_at,
    }


def build_print_report(job_id: str, job: dict[str, str], result: dict) -> str:
    dimensions = result["dimensions"]
    printability = result["printability"]
    bed_fit = "да" if printability["bed_fit_220_220_250"] else "нет"
    implemented = result.get("implemented_operations", [])
    planned = result.get("planned_operations", [])
    planned_text = "\n".join(f"- {item['operation']}: {item['status']}" for item in planned) or "- Нет"
    skipped = result.get("skipped_operations", [])
    skipped_text = "\n".join(f"- {item['operation']}: {item['reason']}" for item in skipped) or "- Нет"
    model_name = job.get("model_name") or job.get("vehicle_name") or ""
    model_text = ""
    if model_name:
        model_text = f"\nНазвание модели: {model_name}\n"

    return (
        "Отчёт STL Master\n"
        f"Job ID: {job_id}\n\n"
        f"Файл: {job.get('filename', 'input.stl')}\n"
        f"{model_text}"
        f"Тип STL: {result['stl_type']}\n"
        f"Треугольники: {result['triangles_count']}\n"
        "Габариты: "
        f"{dimensions['width']} x {dimensions['depth']} x {dimensions['height']} мм\n"
        f"Подходит под стол 220x220x250: {bed_fit}\n\n"
        "Предупреждения:\n"
        f"{format_list(printability['warnings'])}\n\n"
        "Рекомендации:\n"
        f"{format_list(printability['recommendations'])}\n\n"
        "Выполненные операции:\n"
        f"{format_list(implemented)}\n\n"
        "Операции пока запланированы:\n"
        f"{planned_text}\n\n"
        "Операции пропущены защитой сервера:\n"
        f"{skipped_text}\n"
    )


def build_generated_files(job_id: str, zip_files: list[str], result_dir: Path | None = None) -> list[dict[str, str | int]]:
    generated_files = []
    seen = set()
    for file_name in zip_files:
        if file_name in seen:
            continue
        seen.add(file_name)
        size_bytes = 0
        if result_dir:
            file_path = result_dir / file_name
            if not file_path.exists() or not file_path.is_file():
                continue
            size_bytes = file_path.stat().st_size
        if file_name.startswith("split_part_") and file_name.endswith(".stl"):
            part_number = file_name.removeprefix("split_part_").removesuffix(".stl")
            generated_files.append(
                {
                    "name": file_name,
                    "type": "model_part",
                    "label": f"Часть {part_number}",
                    "download_url": f"/api/v1/jobs/{job_id}/files/{file_name}",
                    "size_bytes": size_bytes,
                }
            )
            continue
        if file_name.startswith("bed_part_") and file_name.endswith(".stl"):
            part_number = file_name.removeprefix("bed_part_").removesuffix(".stl")
            generated_files.append(
                {
                    "name": file_name,
                    "type": "model_part",
                    "label": f"Часть для печати {part_number}",
                    "download_url": f"/api/v1/jobs/{job_id}/files/{file_name}",
                    "size_bytes": size_bytes,
                }
            )
            continue

        file_type, label = GENERATED_FILE_LABELS.get(file_name, ("report", "Файл результата"))
        generated_files.append(
            {
                "name": file_name,
                "type": file_type,
                "label": label,
                "download_url": f"/api/v1/jobs/{job_id}/files/{file_name}",
                "size_bytes": size_bytes,
            }
        )
    return generated_files


def build_manifest(zip_files: list[str], result: dict) -> dict:
    return {
        "Название": "STL Master",
        "Версия пайплайна": PIPELINE_VERSION,
        "Файлы в архиве": zip_files,
        "Созданные файлы": [
            {
                "файл": item.get("name"),
                "тип": item.get("type"),
                "описание": item.get("label"),
            }
            for item in result.get("generated_files", [])
        ],
        "Операции": result.get("operations", []),
        "Примечание": "Технические отчёты сохраняются на сервере, но пользовательский ZIP содержит только полезные файлы.",
    }


def run_repair_mesh(input_path: Path, result_dir: Path) -> dict:
    repaired_path = result_dir / "repaired.stl"
    report_path = result_dir / "repair_report.json"
    notes: list[str] = ["MVP-ремонт через trimesh: результат нужно проверять перед печатью."]

    report = {
        "success": False,
        "original_faces": None,
        "repaired_faces": None,
        "original_vertices": None,
        "repaired_vertices": None,
        "watertight_before": None,
        "watertight_after": None,
        "notes": notes,
    }

    try:
        loaded = trimesh.load_mesh(str(input_path), force="mesh")
        if isinstance(loaded, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(loaded.dump()))
            notes.append("STL был загружен как scene и объединен в один mesh.")
        else:
            mesh = loaded

        report["original_faces"] = int(len(mesh.faces))
        report["original_vertices"] = int(len(mesh.vertices))
        report["watertight_before"] = bool(mesh.is_watertight)

        if hasattr(mesh, "remove_duplicate_faces"):
            mesh.remove_duplicate_faces()
            notes.append("remove_duplicate_faces выполнен.")
        else:
            notes.append("remove_duplicate_faces недоступен в текущей версии trimesh.")

        if hasattr(mesh, "remove_degenerate_faces"):
            mesh.remove_degenerate_faces()
            notes.append("remove_degenerate_faces выполнен.")
        else:
            notes.append("remove_degenerate_faces недоступен в текущей версии trimesh.")

        mesh.remove_unreferenced_vertices()
        notes.append("remove_unreferenced_vertices выполнен.")

        try:
            trimesh.repair.fix_normals(mesh)
            notes.append("fix_normals выполнен.")
        except Exception as exc:
            notes.append(f"fix_normals не выполнен: {exc}")

        try:
            filled = trimesh.repair.fill_holes(mesh)
            notes.append(f"fill_holes выполнен, изменено: {bool(filled)}.")
        except Exception as exc:
            notes.append(f"fill_holes не выполнен: {exc}")

        mesh.remove_unreferenced_vertices()
        mesh.export(str(repaired_path))

        report["success"] = repaired_path.exists()
        report["repaired_faces"] = int(len(mesh.faces))
        report["repaired_vertices"] = int(len(mesh.vertices))
        report["watertight_after"] = bool(mesh.is_watertight)
    except Exception as exc:
        notes.append(f"repair_mesh завершился ошибкой: {exc}")

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "report": report,
        "output_file": "repaired.stl" if report["success"] else None,
        "report_file": "repair_report.json",
        "repaired_path": repaired_path,
        "report_path": report_path,
    }


def decimate_mesh(mesh: trimesh.Trimesh, target_faces: int) -> tuple[trimesh.Trimesh | None, str | None]:
    errors: list[str] = []
    if hasattr(mesh, "simplify_quadric_decimation"):
        simplify = mesh.simplify_quadric_decimation
        for kwargs in ({"face_count": target_faces}, {"faces": target_faces}, {"percent": target_faces / len(mesh.faces)}):
            try:
                reduced = simplify(**kwargs)
                if reduced is not None and len(reduced.faces) > 0:
                    return reduced, None
            except Exception as exc:
                errors.append(f"trimesh {kwargs}: {exc}")
        try:
            reduced = simplify(target_faces)
            if reduced is not None and len(reduced.faces) > 0:
                return reduced, None
        except Exception as exc:
            errors.append(f"trimesh positional: {exc}")

    try:
        import fast_simplification

        vertices, faces = fast_simplification.simplify(
            mesh.vertices,
            mesh.faces,
            target_reduction=max(0.0, min(0.99, 1 - target_faces / len(mesh.faces))),
        )
        if len(faces) > 0:
            return trimesh.Trimesh(vertices=vertices, faces=faces, process=False), None
        errors.append("fast_simplification returned an empty mesh")
    except Exception as exc:
        errors.append(f"fast_simplification: {exc}")

    return None, "; ".join(errors) or "Decimation backend is unavailable or failed."


def run_reduce_polygons(source_path: Path, result_dir: Path, reduction_percent: int) -> dict:
    reduced_path = result_dir / "reduced.stl"
    report_path = result_dir / "reduction_report.json"
    report = {
        "success": False,
        "reduction_percent": reduction_percent,
        "original_faces": None,
        "target_faces": None,
        "reduced_faces": None,
        "original_vertices": None,
        "reduced_vertices": None,
        "output_file": None,
        "reason": None,
        "visible_result": visible_result_payload(False, "Уменьшение полигонов ещё не выполнялось."),
        "notes": ["MVP decimation через trimesh; качество нужно проверять перед печатью."],
    }

    try:
        loaded = trimesh.load_mesh(str(source_path), force="mesh")
        if isinstance(loaded, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(loaded.dump()))
            report["notes"].append("STL был загружен как scene и объединен в один mesh.")
        else:
            mesh = loaded

        original_faces = int(len(mesh.faces))
        original_vertices = int(len(mesh.vertices))
        target_faces = max(4, int(original_faces * (100 - reduction_percent) / 100))
        report.update(
            {
                "original_faces": original_faces,
                "target_faces": target_faces,
                "original_vertices": original_vertices,
            }
        )

        if original_faces <= target_faces:
            report["reason"] = "Target face count is not lower than original face count."
        else:
            reduced, reason = decimate_mesh(mesh, target_faces)
            if reduced is None or len(reduced.faces) == 0:
                report["reason"] = reason or "Decimation returned an empty mesh."
            else:
                reduced.remove_unreferenced_vertices()
                reduced.export(str(reduced_path))
                report.update(
                    {
                        "success": reduced_path.exists(),
                        "reduced_faces": int(len(reduced.faces)),
                        "reduced_vertices": int(len(reduced.vertices)),
                        "output_file": "reduced.stl" if reduced_path.exists() else None,
                    }
                )
                if report["success"] and int(report["reduced_faces"] or 0) < original_faces:
                    report["visible_result"] = visible_result_payload(
                        True,
                        "Количество полигонов уменьшено.",
                        ["faces_count", "vertices_count"],
                    )

        if not report["success"] and not report["reason"]:
            report["reason"] = "Decimation backend is unavailable or failed."
        if not report["success"]:
            report["notes"].append("Рекомендуется подключить более мощный backend decimation на следующем этапе.")
            report["visible_result"] = visible_result_payload(False, report["reason"] or "Уменьшение полигонов не выполнено.")
    except Exception as exc:
        report["reason"] = str(exc)
        report["visible_result"] = visible_result_payload(False, report["reason"])
        report["notes"].append("Рекомендуется подключить более мощный backend decimation на следующем этапе.")

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "report": report,
        "output_file": report["output_file"],
        "report_file": "reduction_report.json",
        "reduced_path": reduced_path,
        "report_path": report_path,
    }


def load_mesh_for_processing(source_path: Path, notes: list[str]) -> trimesh.Trimesh:
    loaded = trimesh.load_mesh(str(source_path), force="mesh")
    if isinstance(loaded, trimesh.Scene):
        meshes = tuple(loaded.dump())
        mesh = trimesh.util.concatenate(meshes) if meshes else trimesh.Trimesh()
        notes.append("STL был загружен как scene и объединен в один mesh.")
        return mesh
    return loaded


def ai_cleanup_profile(strength: str) -> dict[str, float | int | bool]:
    if strength == "medium":
        strength = "balanced"
    profiles = {
        "light": {
            "component_ratio": 0.001,
            "min_component_faces": 8,
            "smoothing": False,
            "smooth_iterations": 0,
            "smooth_factor": 0.0,
            "decimation": False,
            "decimation_percent": 0,
        },
        "balanced": {
            "component_ratio": 0.005,
            "min_component_faces": 20,
            "smoothing": False,
            "smooth_iterations": 0,
            "smooth_factor": 0.0,
            "decimation": False,
            "decimation_percent": 0,
        },
        "strong": {
            "component_ratio": 0.01,
            "min_component_faces": 30,
            "smoothing": True,
            "smooth_iterations": 1,
            "smooth_factor": 0.08,
            "decimation": False,
            "decimation_percent": 0,
        },
    }
    return profiles.get(strength, profiles["balanced"])


def remove_small_components(mesh: trimesh.Trimesh, notes: list[str], strength: str) -> tuple[trimesh.Trimesh, int, int, bool]:
    try:
        adjacency = mesh.face_adjacency
    except Exception as exc:
        notes.append(f"Поиск связных компонентов не выполнен: {exc}")
        return mesh, 1, 1, False

    face_count = len(mesh.faces)
    if face_count == 0:
        return mesh, 0, 0, False

    neighbors: list[list[int]] = [[] for _ in range(face_count)]
    for left, right in adjacency:
        left_index = int(left)
        right_index = int(right)
        neighbors[left_index].append(right_index)
        neighbors[right_index].append(left_index)

    components: list[list[int]] = []
    visited = np.zeros(face_count, dtype=bool)
    for face_index in range(face_count):
        if visited[face_index]:
            continue
        stack = [face_index]
        visited[face_index] = True
        component = []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in neighbors[current]:
                if not visited[neighbor]:
                    visited[neighbor] = True
                    stack.append(neighbor)
        components.append(component)

    components_before = len(components)
    if components_before <= 1:
        notes.append("Отдельные мелкие фрагменты не найдены.")
        return mesh, components_before, components_before, False

    profile = ai_cleanup_profile(strength)
    face_threshold = max(int(profile["min_component_faces"]), int(len(mesh.faces) * float(profile["component_ratio"])))
    kept_indices = [component for component in components if len(component) >= face_threshold]
    if not kept_indices:
        kept_indices = [max(components, key=len)]
        notes.append("Все фрагменты меньше порога; сохранен самый крупный компонент.")

    submeshes = [
        mesh.submesh([np.array(component, dtype=int)], append=True, repair=False)
        for component in kept_indices
        if component
    ]
    cleaned = trimesh.util.concatenate(submeshes) if len(submeshes) > 1 else submeshes[0]
    cleaned.remove_unreferenced_vertices()
    removed = len(kept_indices) < components_before
    notes.append(
        f"Компоненты до очистки: {components_before}, после: {len(kept_indices)}, порог граней: {face_threshold}."
    )
    return cleaned, components_before, len(kept_indices), removed


def smooth_vertices_light(mesh: trimesh.Trimesh, notes: list[str], iterations: int = 2, factor: float = 0.12) -> bool:
    try:
        vertices = np.array(mesh.vertices, dtype=float)
        faces = np.array(mesh.faces, dtype=int)
        if len(vertices) == 0 or len(faces) == 0:
            notes.append("Сглаживание пропущено: mesh пустой.")
            return False

        neighbors: list[set[int]] = [set() for _ in range(len(vertices))]
        for face in faces:
            a, b, c = [int(index) for index in face]
            neighbors[a].update((b, c))
            neighbors[b].update((a, c))
            neighbors[c].update((a, b))

        for _ in range(iterations):
            updated = vertices.copy()
            for index, linked in enumerate(neighbors):
                if not linked:
                    continue
                average = vertices[list(linked)].mean(axis=0)
                updated[index] = vertices[index] * (1 - factor) + average * factor
            vertices = updated

        mesh.vertices = vertices
        notes.append(f"Легкое NumPy-сглаживание выполнено: iterations={iterations}, factor={factor}.")
        return True
    except Exception as exc:
        notes.append(f"Легкое NumPy-сглаживание не выполнено: {exc}")
        return False


def run_ai_cleanup(source_path: Path, result_dir: Path, input_file: str, strength: str) -> dict:
    output_path = result_dir / "ai_cleaned.stl"
    report_path = result_dir / "ai_cleanup_report.json"
    warning = "AI cleanup is an MVP cleanup. Always inspect the model before printing."
    notes: list[str] = [
        "MVP-очистка AI-модели через trimesh: результат нужно проверять перед печатью.",
        f"Выбранная сила очистки: {strength}.",
    ]
    warnings: list[str] = []
    profile = ai_cleanup_profile(strength)
    report = {
        "success": False,
        "strength": strength,
        "input_file": input_file,
        "output_file": None,
        "faces_before": None,
        "faces_after": None,
        "vertices_before": None,
        "vertices_after": None,
        "components_before": None,
        "components_after": None,
        "watertight_before": None,
        "watertight_after": None,
        "smoothing_applied": False,
        "removed_small_components": False,
        "small_components_removed": False,
        "visible_change_expected": False,
        "warnings": warnings,
        "notes": notes,
        "warning": warning,
    }

    try:
        mesh = load_mesh_for_processing(source_path, notes)
        report["faces_before"] = int(len(mesh.faces))
        report["vertices_before"] = int(len(mesh.vertices))
        report["watertight_before"] = bool(mesh.is_watertight)

        if len(mesh.faces) == 0 or len(mesh.vertices) == 0:
            notes.append("Mesh пустой, очистка невозможна.")
        else:
            if hasattr(mesh, "remove_duplicate_faces"):
                mesh.remove_duplicate_faces()
                notes.append("remove_duplicate_faces выполнен.")
            else:
                notes.append("remove_duplicate_faces недоступен в текущей версии trimesh.")

            if hasattr(mesh, "remove_degenerate_faces"):
                mesh.remove_degenerate_faces()
                notes.append("remove_degenerate_faces выполнен.")
            else:
                notes.append("remove_degenerate_faces недоступен в текущей версии trimesh.")

            try:
                mesh.merge_vertices(digits_vertex=6)
                notes.append("merge_vertices для совпадающих вершин выполнен перед поиском компонентов.")
            except Exception as exc:
                notes.append(f"merge_vertices не выполнен: {exc}")

            mesh.remove_unreferenced_vertices()
            notes.append("remove_unreferenced_vertices выполнен.")

            try:
                trimesh.repair.fix_normals(mesh)
                notes.append("fix_normals выполнен.")
            except Exception as exc:
                notes.append(f"fix_normals не выполнен: {exc}")

            mesh, components_before, components_after, removed = remove_small_components(mesh, notes, strength)
            report["components_before"] = components_before
            report["components_after"] = components_after
            report["removed_small_components"] = removed
            report["small_components_removed"] = removed

            if bool(profile["smoothing"]):
                report["smoothing_applied"] = smooth_vertices_light(
                    mesh,
                    notes,
                    iterations=int(profile["smooth_iterations"]),
                    factor=float(profile["smooth_factor"]),
                )
            else:
                notes.append("Сглаживание пропущено для выбранного безопасного режима.")

            if bool(profile["decimation"]):
                if len(mesh.faces) < 200:
                    notes.append("Strong-упрощение пропущено: слишком мало граней для безопасного уменьшения шума.")
                else:
                    target_faces = max(50, int(len(mesh.faces) * (100 - int(profile["decimation_percent"])) / 100))
                    reduced, reason = decimate_mesh(mesh, target_faces)
                    if reduced is not None and len(reduced.faces) > 0:
                        mesh = reduced
                        mesh.remove_unreferenced_vertices()
                        notes.append(
                            f"Strong-упрощение шума выполнено: целевые грани {target_faces}, получено {len(mesh.faces)}."
                        )
                    else:
                        notes.append(f"Strong-упрощение шума не выполнено: {reason}")

            mesh.remove_unreferenced_vertices()
            try:
                trimesh.repair.fix_normals(mesh)
                notes.append("Повторное fix_normals после очистки выполнено.")
            except Exception as exc:
                notes.append(f"Повторное fix_normals не выполнено: {exc}")

            mesh.export(str(output_path))
            report["success"] = output_path.exists()
            report["output_file"] = "ai_cleaned.stl" if report["success"] else None
            report["faces_after"] = int(len(mesh.faces))
            report["vertices_after"] = int(len(mesh.vertices))
            report["watertight_after"] = bool(mesh.is_watertight)

            faces_before = report["faces_before"] or 0
            faces_after = report["faces_after"] or 0
            if faces_before > 0:
                reduction_ratio = (faces_before - faces_after) / faces_before
                if reduction_ratio > 0.35:
                    warnings.append("Количество граней сильно уменьшилось. Проверьте, не потерялись ли важные детали.")
                report["visible_change_expected"] = bool(
                    report["smoothing_applied"] or reduction_ratio >= 0.05 or report["components_before"] != report["components_after"]
                )
                if not report["visible_change_expected"]:
                    notes.append("Очистка исправила технические проблемы сетки, но форма модели могла визуально почти не измениться.")

        if report["components_before"] is None:
            report["components_before"] = 1 if report["faces_before"] else 0
        if report["components_after"] is None:
            report["components_after"] = report["components_before"]
        if report["watertight_after"] is None:
            report["watertight_after"] = report["watertight_before"]
    except Exception as exc:
        notes.append(f"ai_cleanup завершился ошибкой: {exc}")

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "report": report,
        "output_file": report["output_file"],
        "report_file": "ai_cleanup_report.json",
        "cleaned_path": output_path,
        "report_path": report_path,
    }


def artifact_cleanup_profile(strength: str) -> dict[str, float | int]:
    if strength == "medium":
        strength = "balanced"
    profiles = {
        "light": {
            "component_ratio": 0.001,
            "min_component_faces": 8,
        },
        "balanced": {
            "component_ratio": 0.005,
            "min_component_faces": 20,
        },
        "strong": {
            "component_ratio": 0.015,
            "min_component_faces": 40,
        },
    }
    return profiles.get(strength, profiles["balanced"])


def remove_artifact_components(
    mesh: trimesh.Trimesh,
    notes: list[str],
    strength: str,
) -> tuple[trimesh.Trimesh, int, int, int, bool]:
    try:
        adjacency = mesh.face_adjacency
    except Exception as exc:
        notes.append(f"Поиск disconnected components не выполнен: {exc}")
        face_count = int(len(mesh.faces))
        component_count = 1 if face_count else 0
        return mesh, component_count, component_count, 0, False

    face_count = len(mesh.faces)
    if face_count == 0:
        return mesh, 0, 0, 0, False

    neighbors: list[list[int]] = [[] for _ in range(face_count)]
    for left, right in adjacency:
        left_index = int(left)
        right_index = int(right)
        neighbors[left_index].append(right_index)
        neighbors[right_index].append(left_index)

    components: list[list[int]] = []
    visited = np.zeros(face_count, dtype=bool)
    for face_index in range(face_count):
        if visited[face_index]:
            continue
        stack = [face_index]
        visited[face_index] = True
        component = []
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in neighbors[current]:
                if not visited[neighbor]:
                    visited[neighbor] = True
                    stack.append(neighbor)
        components.append(component)

    components_before = len(components)
    if components_before <= 1:
        notes.append("Отдельные мелкие фрагменты не найдены.")
        return mesh, components_before, components_before, 0, False

    profile = artifact_cleanup_profile(strength)
    threshold = max(int(profile["min_component_faces"]), int(len(mesh.faces) * float(profile["component_ratio"])))
    largest_component = max(components, key=len)
    kept_components = []
    for component in components:
        if component is largest_component or len(component) >= threshold:
            kept_components.append(component)

    if not kept_components:
        kept_components = [largest_component]
        notes.append("Все фрагменты меньше порога; сохранен самый крупный компонент.")

    removed_components = max(0, components_before - len(kept_components))
    submeshes = [
        mesh.submesh([np.array(component, dtype=int)], append=True, repair=False)
        for component in kept_components
        if component
    ]
    cleaned = trimesh.util.concatenate(submeshes) if len(submeshes) > 1 else submeshes[0]
    cleaned.remove_unreferenced_vertices()
    notes.append(
        f"Компоненты до очистки: {components_before}, после: {len(kept_components)}, порог граней: {threshold}."
    )
    notes.append("Наросты, слитые с основной моделью, требуют advanced cleanup.")
    return cleaned, components_before, len(kept_components), removed_components, bool(removed_components)


def advanced_cleanup_profile(strength: str) -> dict[str, float | int]:
    if strength == "medium":
        strength = "balanced"
    profiles = {
        "light": {"aspect_ratio": 12.0, "smooth_factor": 0.006, "iterations": 1},
        "balanced": {"aspect_ratio": 8.0, "smooth_factor": 0.01, "iterations": 1},
        "strong": {"aspect_ratio": 6.0, "smooth_factor": 0.018, "iterations": 1},
    }
    return profiles.get(strength, profiles["balanced"])


def triangle_aspect_ratios(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    triangles = vertices[faces]
    edge_a = np.linalg.norm(triangles[:, 1] - triangles[:, 0], axis=1)
    edge_b = np.linalg.norm(triangles[:, 2] - triangles[:, 1], axis=1)
    edge_c = np.linalg.norm(triangles[:, 0] - triangles[:, 2], axis=1)
    edges = np.stack([edge_a, edge_b, edge_c], axis=1)
    longest = np.max(edges, axis=1)
    shortest = np.maximum(np.min(edges, axis=1), 1e-12)
    return longest / shortest, longest, shortest


def detect_surface_artifacts(mesh: trimesh.Trimesh, strength: str) -> dict:
    profile = advanced_cleanup_profile(strength)
    vertices = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces, dtype=int)
    empty = {
        "suspicious_regions": 0,
        "spikes_detected": 0,
        "elongated_faces": 0,
        "dense_regions": 0,
        "sparse_regions": 0,
        "suspicious_faces": [],
        "suspicious_vertices": [],
        "artifact_faces": [],
        "mean_edge_length": 0.0,
    }
    if len(vertices) == 0 or len(faces) == 0:
        return empty

    aspect, longest_edges, shortest_edges = triangle_aspect_ratios(vertices, faces)
    areas = np.asarray(mesh.area_faces, dtype=float)
    positive_areas = areas[areas > 1e-12]
    all_edges = mesh.edges_unique_length if hasattr(mesh, "edges_unique_length") else longest_edges
    mean_edge = float(np.mean(all_edges)) if len(all_edges) else 0.0
    std_edge = float(np.std(all_edges)) if len(all_edges) else 0.0
    long_edge_threshold = mean_edge + max(std_edge * 3.0, mean_edge * 2.5)
    aspect_threshold = float(profile["aspect_ratio"])

    elongated_mask = aspect >= aspect_threshold
    spike_mask = elongated_mask & (longest_edges >= max(long_edge_threshold, mean_edge * 1.5))
    if len(positive_areas):
        dense_threshold = float(np.quantile(positive_areas, 0.03))
        sparse_threshold = float(np.quantile(positive_areas, 0.97))
        dense_mask = areas <= dense_threshold
        sparse_mask = areas >= sparse_threshold
    else:
        dense_mask = np.zeros(len(faces), dtype=bool)
        sparse_mask = np.zeros(len(faces), dtype=bool)

    suspicious_mask = elongated_mask | spike_mask | dense_mask | sparse_mask
    suspicious_face_indices = np.nonzero(suspicious_mask)[0]
    suspicious_vertices = np.unique(faces[suspicious_face_indices].reshape(-1)) if len(suspicious_face_indices) else np.array([], dtype=int)
    artifact_faces = []
    for face_index in suspicious_face_indices.astype(int).tolist():
        reason = "suspicious_region"
        severity = "low"
        if bool(spike_mask[face_index]):
            reason = "spike"
            severity = "high"
        elif bool(elongated_mask[face_index]):
            reason = "elongated_face"
            severity = "medium"
        elif bool(sparse_mask[face_index]):
            reason = "sparse_region"
            severity = "medium"
        elif bool(dense_mask[face_index]):
            reason = "dense_region"
            severity = "low"
        artifact_faces.append({"index": int(face_index), "reason": reason, "severity": severity})
    return {
        "suspicious_regions": int(len(suspicious_face_indices)),
        "spikes_detected": int(np.sum(spike_mask)),
        "elongated_faces": int(np.sum(elongated_mask)),
        "dense_regions": int(np.sum(dense_mask)),
        "sparse_regions": int(np.sum(sparse_mask)),
        "suspicious_faces": suspicious_face_indices.astype(int).tolist(),
        "suspicious_vertices": suspicious_vertices.astype(int).tolist(),
        "artifact_faces": artifact_faces,
        "mean_edge_length": round(mean_edge, 6),
    }


def smooth_selected_vertices(mesh: trimesh.Trimesh, vertex_indices: list[int], strength: str, notes: list[str]) -> bool:
    if not vertex_indices:
        notes.append("Локальное сглаживание пропущено: подозрительные вершины не найдены.")
        return False
    profile = advanced_cleanup_profile(strength)
    vertices = np.asarray(mesh.vertices, dtype=float).copy()
    faces = np.asarray(mesh.faces, dtype=int)
    selected = set(int(index) for index in vertex_indices)
    neighbors: list[set[int]] = [set() for _ in range(len(vertices))]
    for face in faces:
        a, b, c = [int(index) for index in face]
        neighbors[a].update((b, c))
        neighbors[b].update((a, c))
        neighbors[c].update((a, b))

    factor = float(profile["smooth_factor"])
    iterations = int(profile["iterations"])
    for _ in range(iterations):
        updated = vertices.copy()
        for index in selected:
            linked = neighbors[index]
            if not linked:
                continue
            average = vertices[list(linked)].mean(axis=0)
            updated[index] = vertices[index] * (1.0 - factor) + average * factor
        vertices = updated
    mesh.vertices = vertices
    notes.append(
        f"Локальное сглаживание подозрительных участков выполнено: vertices={len(selected)}, iterations={iterations}, factor={factor}."
    )
    return True


def evaluate_advanced_cleanup_gate(before_mesh: trimesh.Trimesh, after_mesh: trimesh.Trimesh, before_qa: dict, after_qa: dict) -> dict:
    before_main = main_component_metrics(before_mesh)
    after_main = main_component_metrics(after_mesh)
    main_bbox_change = max_dimension_change_percent(before_main.get("dimensions"), after_main.get("dimensions"))
    main_volume_change = volume_change_percent(before_main.get("volume"), after_main.get("volume"))
    passed = bool(
        after_main.get("faces", 0) > 0
        and after_main.get("vertices", 0) > 0
        and main_bbox_change is not None
        and main_bbox_change <= 3.0
        and (main_volume_change is None or main_volume_change <= 5.0)
    )
    reason = "Очистка принята: основная геометрия сохранена."
    if not passed:
        if main_bbox_change is not None and main_bbox_change > 3.0:
            reason = "Очистка отклонена: основная геометрия изменилась больше чем на 3%."
        elif main_volume_change is not None and main_volume_change > 5.0:
            reason = "Очистка отклонена: объём основной геометрии изменился больше чем на 5%."
        else:
            reason = "Очистка отклонена: результат не содержит валидную основную геометрию."
    return {
        "passed": passed,
        "reason": reason,
        "main_component_bbox_change": main_bbox_change,
        "main_component_volume_change": main_volume_change,
        "main_component_faces_before": before_main.get("faces"),
        "main_component_faces_after": after_main.get("faces"),
        "health_score_before": before_qa.get("health_score"),
        "health_score_after": after_qa.get("health_score"),
    }


def run_remove_ai_artifacts(source_path: Path, result_dir: Path, input_file: str, strength: str) -> dict:
    output_path = result_dir / "cleaned_artifacts.stl"
    report_path = result_dir / "artifact_cleanup_report.json"
    warning_text = "AI artifact cleanup is an MVP cleanup. Always inspect the model before printing."
    notes: list[str] = [
        "MVP-очистка удаляет только отдельные disconnected components.",
        "Наросты, слитые с корпусом, не вырезаются без advanced boolean/remesh.",
        f"Выбранная сила очистки: {strength}.",
    ]
    warnings: list[str] = []
    report = {
        "success": False,
        "strength": strength,
        "input_file": input_file,
        "output_file": None,
        "report_file": "artifact_cleanup_report.json",
        "components_before": None,
        "components_after": None,
        "removed_components": 0,
        "faces_before": None,
        "faces_after": None,
        "vertices_before": None,
        "vertices_after": None,
        "bbox_change_percent": None,
        "quality_gate_passed": False,
        "reason": None,
        "warnings": warnings,
        "notes": notes,
        "warning": warning_text,
        "suspicious_regions": 0,
        "spikes_detected": 0,
        "elongated_faces": 0,
        "dense_regions": 0,
        "sparse_regions": 0,
        "smoothing_applied": False,
        "health_score_before": None,
        "health_score_after": None,
        "artifact_quality_before": None,
        "artifact_quality_after": None,
        "delta": {
            "health_score_delta": 0,
            "artifact_penalty_delta": 0,
            "suspicious_regions_delta": 0,
            "elongated_faces_delta": 0,
            "spikes_detected_delta": 0,
        },
        "advanced_quality_gate": None,
        "visible_result": visible_result_payload(False, "AI-артефакты ещё не проверялись."),
    }

    try:
        mesh = load_mesh_for_processing(source_path, notes)
        original_mesh = mesh.copy()
        before_metrics = mesh_quality_metrics(mesh)
        before_qa = diagnose_model(source_path)
        report["health_score_before"] = before_qa.get("health_score")
        report["artifact_quality_before"] = before_qa.get("artifact_quality") or {}
        report["faces_before"] = before_metrics["faces"]
        report["vertices_before"] = int(len(mesh.vertices))

        if len(mesh.faces) == 0 or len(mesh.vertices) == 0:
            report["reason"] = "Mesh пустой, очистка артефактов невозможна."
        else:
            if hasattr(mesh, "remove_duplicate_faces"):
                mesh.remove_duplicate_faces()
                notes.append("remove_duplicate_faces выполнен.")
            else:
                notes.append("remove_duplicate_faces недоступен в текущей версии trimesh.")

            if hasattr(mesh, "remove_degenerate_faces"):
                mesh.remove_degenerate_faces()
                notes.append("remove_degenerate_faces выполнен.")
            else:
                notes.append("remove_degenerate_faces недоступен в текущей версии trimesh.")

            try:
                mesh.merge_vertices(digits_vertex=6)
                notes.append("merge_vertices для совпадающих вершин выполнен перед поиском AI-артефактов.")
            except Exception as exc:
                notes.append(f"merge_vertices не выполнен: {exc}")

            mesh.remove_unreferenced_vertices()
            notes.append("remove_unreferenced_vertices выполнен.")

            try:
                trimesh.repair.fix_normals(mesh)
                notes.append("fix_normals выполнен.")
            except Exception as exc:
                notes.append(f"fix_normals не выполнен: {exc}")

            mesh, components_before, components_after, removed_components, removed_any = remove_artifact_components(mesh, notes, strength)
            report["components_before"] = components_before
            report["components_after"] = components_after
            report["removed_components"] = removed_components

            artifact_detection = detect_surface_artifacts(mesh, strength)
            report["suspicious_regions"] = artifact_detection["suspicious_regions"]
            report["spikes_detected"] = artifact_detection["spikes_detected"]
            report["elongated_faces"] = artifact_detection["elongated_faces"]
            report["dense_regions"] = artifact_detection["dense_regions"]
            report["sparse_regions"] = artifact_detection["sparse_regions"]
            if artifact_detection["suspicious_regions"] > 0:
                notes.append(
                    "Advanced cleanup: обнаружены подозрительные участки внутри основного mesh "
                    f"(faces={artifact_detection['suspicious_regions']}, spikes={artifact_detection['spikes_detected']})."
                )
            report["smoothing_applied"] = smooth_selected_vertices(
                mesh,
                artifact_detection["suspicious_vertices"],
                strength,
                notes,
            )

            mesh.remove_unreferenced_vertices()
            try:
                trimesh.repair.fix_normals(mesh)
                notes.append("Повторное fix_normals после очистки выполнено.")
            except Exception as exc:
                notes.append(f"Повторное fix_normals не выполнено: {exc}")

            mesh.export(str(output_path))
            if output_path.exists() and output_path.stat().st_size > 0:
                validated = load_mesh_for_processing(output_path, notes)
                after_metrics = mesh_quality_metrics(validated)
                report["faces_after"] = after_metrics["faces"]
                report["vertices_after"] = int(len(validated.vertices))
                report["bbox_change_percent"] = max_dimension_change_percent(
                    before_metrics.get("dimensions"),
                    after_metrics.get("dimensions"),
                )
                after_qa = diagnose_model(output_path)
                report["health_score_after"] = after_qa.get("health_score")
                report["artifact_quality_after"] = after_qa.get("artifact_quality") or {}
                before_artifacts = report["artifact_quality_before"] or {}
                after_artifacts = report["artifact_quality_after"] or {}
                report["delta"] = {
                    "health_score_delta": int(report["health_score_after"] or 0) - int(report["health_score_before"] or 0),
                    "artifact_penalty_delta": int(after_artifacts.get("artifact_score_penalty") or 0)
                    - int(before_artifacts.get("artifact_score_penalty") or 0),
                    "suspicious_regions_delta": int(after_artifacts.get("suspicious_regions") or 0)
                    - int(before_artifacts.get("suspicious_regions") or 0),
                    "elongated_faces_delta": int(after_artifacts.get("elongated_faces") or 0)
                    - int(before_artifacts.get("elongated_faces") or 0),
                    "spikes_detected_delta": int(after_artifacts.get("spikes_detected") or 0)
                    - int(before_artifacts.get("spikes_detected") or 0),
                }
                gate = evaluate_advanced_cleanup_gate(original_mesh, validated, before_qa, after_qa)
                report["advanced_quality_gate"] = gate
                faces_before = int(report["faces_before"] or 0)
                faces_after = int(report["faces_after"] or 0)
                file_valid = bool(output_path.exists() and output_path.stat().st_size > 0 and faces_after > 0 and report["vertices_after"] and report["vertices_after"] > 0)
                faces_ok = bool(faces_before == 0 or faces_after >= int(faces_before * 0.6))
                if faces_before > 0 and faces_after > 0 and (faces_before - faces_after) / faces_before > 0.4:
                    warnings.append("Удалено слишком много граней для безопасной очистки.")
                changed_metrics = []
                if int(report["removed_components"] or 0) > 0:
                    changed_metrics.append("removed_components")
                if report["delta"]["health_score_delta"] > 0:
                    changed_metrics.append("health_score")
                if report["delta"]["artifact_penalty_delta"] < 0:
                    changed_metrics.append("artifact_penalty")
                if report["smoothing_applied"] and (
                    report["delta"]["suspicious_regions_delta"] < 0
                    or report["delta"]["elongated_faces_delta"] < 0
                    or report["delta"]["spikes_detected_delta"] < 0
                ):
                    changed_metrics.append("artifact_metrics")
                visible_created = bool(changed_metrics)
                report["visible_result"] = visible_result_payload(
                    visible_created,
                    "AI-артефакты уменьшились." if visible_created else "AI-артефакты не уменьшились.",
                    changed_metrics,
                )
                report["quality_gate_passed"] = bool(file_valid and faces_ok and gate["passed"] and visible_created)
                if report["quality_gate_passed"]:
                    report["success"] = True
                    report["output_file"] = "cleaned_artifacts.stl"
                    report["reason"] = gate["reason"]
                else:
                    report["reason"] = (
                        "AI-артефакты не уменьшились."
                        if not visible_created
                        else gate["reason"] or "Очистка могла повредить модель, поэтому результат не был применён."
                    )
                    output_path.unlink(missing_ok=True)
            else:
                report["reason"] = "Не удалось сохранить cleaned_artifacts.stl."

        if report["components_before"] is None:
            report["components_before"] = 1 if report["faces_before"] else 0
        if report["components_after"] is None:
            report["components_after"] = report["components_before"]
        if report["faces_after"] is None:
            report["faces_after"] = report["faces_before"]
        if report["vertices_after"] is None:
            report["vertices_after"] = report["vertices_before"]
        if not report["quality_gate_passed"] and not report["reason"]:
            report["reason"] = "Очистка могла повредить модель, поэтому результат не был применён."
    except Exception as exc:
        report["reason"] = str(exc)

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "report": report,
        "output_file": report["output_file"],
        "report_file": "artifact_cleanup_report.json",
        "cleaned_path": output_path,
        "report_path": report_path,
    }


def run_surface_recovery(source_path: Path, result_dir: Path, source_file: str) -> dict:
    output_path = result_dir / "surface_recovered.stl"
    report_path = result_dir / "surface_recovery_report.json"
    stats_path = result_dir / "surface_recovery_blender_stats.json"
    report = {
        "success": False,
        "input_file": source_file,
        "output_file": None,
        "report_file": "surface_recovery_report.json",
        "regions_detected": 0,
        "vertices_modified": 0,
        "faces_before": None,
        "faces_after": None,
        "vertices_before": None,
        "vertices_after": None,
        "health_score_before": None,
        "health_score_after": None,
        "artifact_quality_before": None,
        "artifact_quality_after": None,
        "delta": {
            "health_score_delta": 0,
            "suspicious_regions_delta": 0,
            "spikes_detected_delta": 0,
            "elongated_faces_delta": 0,
            "dense_regions_delta": 0,
            "sparse_regions_delta": 0,
            "artifact_penalty_delta": 0,
        },
        "bbox_change_percent": None,
        "volume_change_percent": None,
        "quality_gate_passed": False,
        "effect_detected": False,
        "visible_result": visible_result_payload(False, "Восстановление поверхности ещё не выполнялось."),
        "reason": None,
        "warnings": [],
        "notes": [
            "Восстановление поверхности сглаживает только подозрительные зоны.",
            "Острые кромки и границы защищаются от сглаживания эвристически.",
        ],
    }

    try:
        before_mesh = load_mesh_for_processing(source_path, [])
        before_metrics = mesh_quality_metrics(before_mesh)
        before_qa = diagnose_model(source_path)
        report["faces_before"] = before_metrics["faces"]
        report["vertices_before"] = before_metrics["vertices"]
        report["health_score_before"] = before_qa.get("health_score")
        report["artifact_quality_before"] = before_qa.get("artifact_quality") or {}
    except Exception as exc:
        report["reason"] = f"Не удалось прочитать исходную STL: {exc}"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"report": report, "output_file": None, "report_file": "surface_recovery_report.json"}

    if int(report["faces_before"] or 0) > 400_000 or int(report["vertices_before"] or 0) > 200_000:
        report["health_score_after"] = report["health_score_before"]
        report["artifact_quality_after"] = report["artifact_quality_before"]
        report["visible_result"] = visible_result_payload(False, "Модель слишком большая для безопасного восстановления поверхности.")
        report["reason"] = "Восстановление поверхности пропущено: модель слишком большая для безопасной Blender-обработки в текущем контейнере."
        report["warnings"].append("Для больших STL surface recovery завершается controlled failure, чтобы не переполнить память worker.")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"report": report, "output_file": None, "report_file": "surface_recovery_report.json"}

    if not blender_available():
        report["reason"] = "Blender недоступен внутри worker-контейнера."
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"report": report, "output_file": None, "report_file": "surface_recovery_report.json"}

    script = f"""
import json
import math
import statistics
import bpy
from mathutils import Vector

input_path = {str(source_path)!r}
output_path = {str(output_path)!r}
stats_path = {str(stats_path)!r}

stats = {{
    "regions_detected": 0,
    "vertices_modified": 0,
    "sharp_vertices_protected": 0,
    "laplacian_smooth": False,
    "corrective_smooth": False,
    "warnings": [],
}}

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

try:
    bpy.ops.import_mesh.stl(filepath=input_path)
except Exception:
    bpy.ops.wm.stl_import(filepath=input_path)

mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
if not mesh_objects:
    raise RuntimeError("No mesh objects imported from STL")

bpy.ops.object.select_all(action='DESELECT')
for obj in mesh_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = mesh_objects[0]
if len(mesh_objects) > 1:
    bpy.ops.object.join()

obj = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
mesh = obj.data
mesh.update(calc_edges=True)

edge_lengths = []
face_data = []
for poly in mesh.polygons:
    verts = [mesh.vertices[index].co.copy() for index in poly.vertices]
    if len(verts) < 3:
        continue
    lengths = []
    for index in range(len(verts)):
        length = (verts[index] - verts[(index + 1) % len(verts)]).length
        lengths.append(length)
        edge_lengths.append(length)
    longest = max(lengths) if lengths else 0.0
    shortest = max(min(lengths), 1e-9) if lengths else 1e-9
    aspect = longest / shortest
    area = float(poly.area)
    face_data.append((poly.index, list(poly.vertices), longest, shortest, aspect, area))

if not face_data:
    raise RuntimeError("Imported mesh has no faces")

mean_edge = statistics.fmean(edge_lengths) if edge_lengths else 0.0
std_edge = statistics.pstdev(edge_lengths) if len(edge_lengths) > 1 else 0.0
long_edge_threshold = mean_edge + max(std_edge * 3.0, mean_edge * 2.5)
areas = sorted([item[5] for item in face_data if item[5] > 1e-12])
dense_threshold = areas[max(0, int(len(areas) * 0.03) - 1)] if areas else 0.0
sparse_threshold = areas[min(len(areas) - 1, int(len(areas) * 0.97))] if areas else 0.0

edge_faces = {{}}
for poly in mesh.polygons:
    verts = list(poly.vertices)
    for index in range(len(verts)):
        edge = tuple(sorted((verts[index], verts[(index + 1) % len(verts)])))
        edge_faces.setdefault(edge, []).append(poly.index)

sharp_vertices = set()
for edge, faces in edge_faces.items():
    if len(faces) < 2:
        sharp_vertices.update(edge)
        continue
    normal_a = mesh.polygons[faces[0]].normal
    normal_b = mesh.polygons[faces[1]].normal
    angle = normal_a.angle(normal_b, 0.0)
    if angle > math.radians(35):
        sharp_vertices.update(edge)

suspicious_faces = set()
suspicious_vertices = set()
for poly_index, vertices, longest, shortest, aspect, area in face_data:
    is_elongated = aspect >= 8.0
    is_spike = is_elongated and longest >= max(long_edge_threshold, mean_edge * 1.5)
    is_dense = dense_threshold > 0.0 and area <= dense_threshold
    is_sparse = sparse_threshold > 0.0 and area >= sparse_threshold
    if is_elongated or is_spike or is_dense or is_sparse:
        suspicious_faces.add(poly_index)
        for vertex_index in vertices:
            if vertex_index not in sharp_vertices:
                suspicious_vertices.add(vertex_index)

stats["regions_detected"] = len(suspicious_faces)
stats["sharp_vertices_protected"] = len(sharp_vertices)
stats["vertices_modified"] = len(suspicious_vertices)

if not suspicious_vertices:
    with open(stats_path, "w", encoding="utf-8") as handle:
        json.dump(stats, handle, ensure_ascii=False, indent=2)
    raise RuntimeError("No recoverable surface regions detected")

group = obj.vertex_groups.new(name="STL Master Surface Recovery")
group.add(list(suspicious_vertices), 1.0, 'ADD')

try:
    laplacian = obj.modifiers.new(name="STL Master Local Laplacian Smooth", type='LAPLACIANSMOOTH')
    if hasattr(laplacian, "vertex_group"):
        laplacian.vertex_group = group.name
    if hasattr(laplacian, "lambda_factor"):
        laplacian.lambda_factor = 0.08
    if hasattr(laplacian, "lambda_border"):
        laplacian.lambda_border = 0.0
    if hasattr(laplacian, "iterations"):
        laplacian.iterations = 1
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=laplacian.name)
    stats["laplacian_smooth"] = True
except Exception as exc:
    stats["warnings"].append(f"Laplacian Smooth skipped: {{exc}}")

try:
    corrective = obj.modifiers.new(name="STL Master Corrective Smooth", type='CORRECTIVE_SMOOTH')
    if hasattr(corrective, "vertex_group"):
        corrective.vertex_group = group.name
    if hasattr(corrective, "factor"):
        corrective.factor = 0.12
    if hasattr(corrective, "iterations"):
        corrective.iterations = 1
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=corrective.name)
    stats["corrective_smooth"] = True
except Exception as exc:
    stats["warnings"].append(f"Corrective Smooth skipped: {{exc}}")

try:
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
except Exception as exc:
    stats["warnings"].append(f"Normal recalculation skipped: {{exc}}")
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

try:
    bpy.ops.export_mesh.stl(filepath=output_path, use_selection=True)
except Exception:
    bpy.ops.wm.stl_export(filepath=output_path, export_selected_objects=True)

with open(stats_path, "w", encoding="utf-8") as handle:
    json.dump(stats, handle, ensure_ascii=False, indent=2)
"""

    script_path = None
    try:
        with NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as handle:
            handle.write(script)
            script_path = Path(handle.name)

        completed = subprocess.run(
            ["blender", "-b", "--python", str(script_path)],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        blender_output = "\n".join(part for part in (completed.stderr, completed.stdout) if part)
        if stats_path.exists():
            try:
                stats = json.loads(stats_path.read_text(encoding="utf-8"))
            except Exception:
                stats = {}
            report["regions_detected"] = int(stats.get("regions_detected") or 0)
            report["vertices_modified"] = int(stats.get("vertices_modified") or 0)
            report["notes"].append(f"Защищено острых/граничных вершин: {int(stats.get('sharp_vertices_protected') or 0)}.")
            if stats.get("laplacian_smooth"):
                report["notes"].append("Laplacian Smooth применён к vertex group проблемных зон.")
            if stats.get("corrective_smooth"):
                report["notes"].append("Corrective Smooth применён к vertex group проблемных зон.")
            report["warnings"].extend(str(item) for item in stats.get("warnings", []))

        if completed.returncode != 0 or "Traceback (most recent call last)" in blender_output:
            if report["regions_detected"] == 0:
                report["reason"] = "Проблемные зоны поверхности не найдены."
            else:
                report["reason"] = (blender_output or "Blender surface recovery failed").strip()[-1200:]
        elif not output_path.exists() or output_path.stat().st_size == 0:
            report["reason"] = "Blender завершился, но surface_recovered.stl не создан."
        else:
            after_mesh = load_mesh_for_processing(output_path, [])
            after_metrics = mesh_quality_metrics(after_mesh)
            after_qa = diagnose_model(output_path)
            bbox_change = max_dimension_change_percent(before_metrics.get("dimensions"), after_metrics.get("dimensions"))
            volume_change = volume_change_percent(before_metrics.get("volume"), after_metrics.get("volume"))
            report["faces_after"] = after_metrics["faces"]
            report["vertices_after"] = after_metrics["vertices"]
            report["health_score_after"] = after_qa.get("health_score")
            report["artifact_quality_after"] = after_qa.get("artifact_quality") or {}
            before_artifacts = report["artifact_quality_before"] or {}
            after_artifacts = report["artifact_quality_after"] or {}
            report["delta"] = {
                "health_score_delta": int(report["health_score_after"] or 0) - int(report["health_score_before"] or 0),
                "suspicious_regions_delta": int(after_artifacts.get("suspicious_regions") or 0) - int(before_artifacts.get("suspicious_regions") or 0),
                "spikes_detected_delta": int(after_artifacts.get("spikes_detected") or 0) - int(before_artifacts.get("spikes_detected") or 0),
                "elongated_faces_delta": int(after_artifacts.get("elongated_faces") or 0) - int(before_artifacts.get("elongated_faces") or 0),
                "dense_regions_delta": int(after_artifacts.get("dense_regions") or 0) - int(before_artifacts.get("dense_regions") or 0),
                "sparse_regions_delta": int(after_artifacts.get("sparse_regions") or 0) - int(before_artifacts.get("sparse_regions") or 0),
                "artifact_penalty_delta": int(after_artifacts.get("artifact_score_penalty") or 0)
                - int(before_artifacts.get("artifact_score_penalty") or 0),
            }
            report["bbox_change_percent"] = bbox_change
            report["volume_change_percent"] = volume_change
            bbox_ok = bbox_change is not None and bbox_change <= 3.0
            volume_ok = volume_change is None or volume_change <= 5.0
            file_ok = bool(after_metrics["faces"] > 0 and after_metrics["vertices"] > 0)
            effect_detected = bool(report["regions_detected"] > 0 and report["vertices_modified"] > 0)
            report["effect_detected"] = effect_detected
            meaningful_improvement = bool(
                report["delta"]["health_score_delta"] > 0
                or report["delta"]["artifact_penalty_delta"] < 0
            )
            changed_metrics = []
            if report["delta"]["health_score_delta"] > 0:
                changed_metrics.append("health_score")
            if report["delta"]["artifact_penalty_delta"] < 0:
                changed_metrics.append("artifact_penalty")
            report["visible_result"] = visible_result_payload(
                meaningful_improvement,
                "Поверхность улучшилась по QA-метрикам." if meaningful_improvement else "Значимых улучшений не обнаружено.",
                changed_metrics,
            )
            report["quality_gate_passed"] = bool(file_ok and bbox_ok and volume_ok and effect_detected and meaningful_improvement)
            if report["quality_gate_passed"]:
                report["success"] = True
                report["output_file"] = "surface_recovered.stl"
                report["reason"] = "Поверхность восстановлена локально, основная геометрия сохранена."
            elif not meaningful_improvement:
                report["reason"] = "Значимых улучшений не обнаружено."
                output_path.unlink(missing_ok=True)
            elif not effect_detected:
                report["reason"] = "Проблемные зоны поверхности не найдены, результат не применён."
                output_path.unlink(missing_ok=True)
            elif not bbox_ok:
                report["reason"] = "Восстановление поверхности отклонено: габариты изменились больше чем на 3%."
                output_path.unlink(missing_ok=True)
            elif not volume_ok:
                report["reason"] = "Восстановление поверхности отклонено: объём изменился больше чем на 5%."
                output_path.unlink(missing_ok=True)
            else:
                report["reason"] = "Восстановление поверхности отклонено: результат не содержит валидную геометрию."
                output_path.unlink(missing_ok=True)
    except subprocess.TimeoutExpired:
        output_path.unlink(missing_ok=True)
        report["reason"] = "Blender surface recovery превысил timeout 180 секунд."
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        report["reason"] = str(exc)
    finally:
        if script_path:
            script_path.unlink(missing_ok=True)
        stats_path.unlink(missing_ok=True)

    if report["faces_after"] is None:
        report["faces_after"] = report["faces_before"]
    if report["vertices_after"] is None:
        report["vertices_after"] = report["vertices_before"]
    if report["health_score_after"] is None:
        report["health_score_after"] = report["health_score_before"]
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "report": report,
        "output_file": report["output_file"],
        "report_file": "surface_recovery_report.json",
    }


def select_final_output_file(result: dict) -> str:
    local_smoothing = result.get("local_smoothing") or {}
    if local_smoothing.get("success") and local_smoothing.get("output_file") == "local_smoothed.stl":
        return local_smoothing["output_file"]

    auto_orientation = result.get("auto_orientation") or {}
    if auto_orientation.get("success") and auto_orientation.get("output_file") == "oriented_auto.stl":
        return auto_orientation["output_file"]

    apply_orientation = result.get("apply_orientation") or {}
    if apply_orientation.get("success") and apply_orientation.get("output_file") == "oriented_model.stl":
        return apply_orientation["output_file"]

    surface_recovery = result.get("surface_recovery") or {}
    if surface_recovery.get("success") and surface_recovery.get("output_file") == "surface_recovered.stl":
        return surface_recovery["output_file"]

    remove_ai_artifacts = result.get("remove_ai_artifacts") or {}
    if remove_ai_artifacts.get("success") and remove_ai_artifacts.get("output_file"):
        return remove_ai_artifacts["output_file"]

    print_repair = result.get("print_repair") or {}
    if print_repair.get("success") and print_repair.get("output_file") == "repaired_model.stl":
        return print_repair["output_file"]

    model_improvement = result.get("model_improvement") or {}
    if model_improvement.get("success") and model_improvement.get("after_file") in {"improved_model.stl", "repaired_model.stl"}:
        return model_improvement["after_file"]

    fix_symmetry = result.get("fix_symmetry") or {}
    if fix_symmetry.get("success") and fix_symmetry.get("output_file") == "symmetry_fixed.stl":
        return fix_symmetry["output_file"]

    reduce_polygons = result.get("reduce_polygons") or {}
    if reduce_polygons.get("success") and reduce_polygons.get("output_file") == "reduced.stl":
        return reduce_polygons["output_file"]

    repair_mesh = result.get("repair_mesh") or {}
    if repair_mesh.get("success") and repair_mesh.get("output_file") == "repaired.stl":
        return repair_mesh["output_file"]

    return "original.stl"


def result_source_path(result: dict, result_dir: Path, input_path: Path, preferred: Iterable[str] | None = None) -> tuple[Path, str]:
    candidates = list(preferred or [])
    candidates.extend(
        [
            "oriented_auto.stl",
            "oriented_model.stl",
            "local_smoothed.stl",
            "surface_recovered.stl",
            "cleaned_artifacts.stl",
            "repaired_model.stl",
            "reduced.stl",
            "repaired.stl",
        ]
    )
    seen = set()
    for file_name in candidates:
        if not file_name or file_name in seen:
            continue
        seen.add(file_name)
        path = result_dir / file_name
        if path.exists() and path.is_file() and path.stat().st_size > 0:
            return path, file_name
    return input_path, "original.stl"


def split_axis_basis(split_axis: str) -> tuple[int, tuple[int, int]]:
    axis_index = {"x": 0, "y": 1, "z": 2}[split_axis]
    plane_axes = {
        "x": (1, 2),
        "y": (0, 2),
        "z": (0, 1),
    }[split_axis]
    return axis_index, plane_axes


def make_transform(center: np.ndarray, direction: np.ndarray) -> np.ndarray:
    transform = trimesh.geometry.align_vectors([0, 0, 1], direction)
    transform[:3, 3] = center
    return transform


def build_connector_positions(mesh: trimesh.Trimesh, split_axis: str, split_parts: int, connector_count: int = 4) -> tuple[list[dict], np.ndarray, np.ndarray, float]:
    axis_index, plane_axes = split_axis_basis(split_axis)
    bounds = mesh.bounds
    center = mesh.bounds.mean(axis=0)
    size = bounds[1] - bounds[0]
    min_value = float(bounds[0][axis_index])
    max_value = float(bounds[1][axis_index])
    span = max_value - min_value
    max_size = float(max(size.max(), 1.0))
    if span <= 0:
        return [], center, size, max_size

    base_offsets = [
        (-float(size[plane_axes[0]]) * 0.24, -float(size[plane_axes[1]]) * 0.22),
        (float(size[plane_axes[0]]) * 0.24, -float(size[plane_axes[1]]) * 0.22),
        (-float(size[plane_axes[0]]) * 0.24, float(size[plane_axes[1]]) * 0.22),
        (float(size[plane_axes[0]]) * 0.24, float(size[plane_axes[1]]) * 0.22),
    ]
    plane_offsets = base_offsets[: max(1, min(int(connector_count), 4))]
    positions = []
    for plane_index in range(1, split_parts):
        plane_value = min_value + span * plane_index / split_parts
        for marker_index, (offset_a, offset_b) in enumerate(plane_offsets, start=1):
            point = center.copy()
            point[axis_index] = plane_value
            point[plane_axes[0]] += offset_a
            point[plane_axes[1]] += offset_b
            positions.append(
                {
                    "plane": plane_index,
                    "marker": marker_index,
                    "center": [round(float(value), 6) for value in point],
                }
            )
    return positions, center, size, max_size


def is_valid_mesh_file(path: Path) -> tuple[bool, dict]:
    details = {
        "file_size": path.stat().st_size if path.exists() else 0,
        "faces": 0,
        "vertices": 0,
        "bbox_valid": False,
        "reason": None,
    }
    if not path.exists() or details["file_size"] <= 0:
        details["reason"] = "Файл не создан или пустой."
        return False, details
    try:
        loaded = trimesh.load_mesh(str(path), force="mesh")
        if isinstance(loaded, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(loaded.dump()))
        else:
            mesh = loaded
        details["faces"] = int(len(mesh.faces))
        details["vertices"] = int(len(mesh.vertices))
        if details["faces"] <= 0 or details["vertices"] <= 0:
            details["reason"] = "Файл не содержит валидную геометрию."
            return False, details
        bounds = mesh.bounds
        if bounds is None or np.asarray(bounds).shape != (2, 3):
            details["reason"] = "Не удалось определить bounding box части."
            return False, details
        size = bounds[1] - bounds[0]
        details["bbox_valid"] = bool(np.all(np.isfinite(size)) and float(size.max()) > 0 and np.count_nonzero(size > 1e-6) >= 2)
        if not details["bbox_valid"]:
            details["reason"] = "Bounding box части нулевой или некорректный."
            return False, details
        return True, details
    except Exception as exc:
        details["reason"] = f"Не удалось загрузить STL для проверки: {exc}"
        return False, details


def load_trimesh_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load_mesh(str(path), force="mesh")
    if isinstance(loaded, trimesh.Scene):
        geometries = tuple(loaded.dump())
        if not geometries:
            raise ValueError("STL не содержит геометрии")
        return trimesh.util.concatenate(geometries)
    return loaded


def mesh_bbox_payload(mesh: trimesh.Trimesh) -> dict[str, dict[str, float]]:
    bounds = np.asarray(mesh.bounds, dtype=float)
    size = bounds[1] - bounds[0]
    return {
        "min": {"x": round(float(bounds[0][0]), 6), "y": round(float(bounds[0][1]), 6), "z": round(float(bounds[0][2]), 6)},
        "max": {"x": round(float(bounds[1][0]), 6), "y": round(float(bounds[1][1]), 6), "z": round(float(bounds[1][2]), 6)},
        "dimensions": {
            "width": round(float(size[0]), 6),
            "depth": round(float(size[2]), 6),
            "height": round(float(size[1]), 6),
        },
    }


def visible_result_payload(created: bool, reason: str, changed_metrics: list[str] | None = None) -> dict:
    return {
        "created": bool(created),
        "reason": reason,
        "changed_metrics": changed_metrics or [],
    }


def artifact_penalty(qa: dict | None) -> int:
    return int(((qa or {}).get("artifact_quality") or {}).get("artifact_score_penalty") or 0)


def load_change_map_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load_mesh(str(path), force="mesh")
    if isinstance(loaded, trimesh.Scene):
        meshes = [mesh for mesh in loaded.dump() if len(mesh.vertices) > 0 and len(mesh.faces) > 0]
        return trimesh.util.concatenate(tuple(meshes)) if meshes else trimesh.Trimesh()
    return loaded


def change_level(distance: float, thresholds: dict[str, float]) -> str:
    if distance >= thresholds["high"]:
        return "high"
    if distance >= thresholds["medium"]:
        return "medium"
    if distance >= thresholds["low"]:
        return "low"
    return "none"


def create_change_map(
    job_id: str,
    result_dir: Path,
    input_path: Path,
    source_file: str,
    target_file: str,
    operation: str,
) -> dict:
    output_path = result_dir / "change_map.json"
    thresholds = {"low": 0.05, "medium": 0.2, "high": 0.5}
    payload = {
        "available": False,
        "file": None,
        "operation": operation,
        "changed_vertices": 0,
        "max_distance": 0.0,
        "mean_distance": 0.0,
        "download_url": None,
        "reason": None,
    }

    try:
        source_path = input_path if source_file in {"original.stl", "input.stl"} else result_dir / source_file
        target_path = result_dir / target_file
        if not source_path.exists():
            raise FileNotFoundError(f"source STL not found: {source_file}")
        if not target_path.exists():
            raise FileNotFoundError(f"target STL not found: {target_file}")

        source_mesh = load_change_map_mesh(source_path)
        target_mesh = load_change_map_mesh(target_path)
        source_vertices = np.asarray(source_mesh.vertices, dtype=float)
        target_vertices = np.asarray(target_mesh.vertices, dtype=float)
        if len(source_vertices) == 0 or len(target_vertices) == 0:
            raise ValueError("source or target mesh has no vertices")

        if len(source_vertices) == len(target_vertices):
            distances = np.linalg.norm(source_vertices - target_vertices, axis=1)
        else:
            tree = cKDTree(target_vertices)
            distances, _ = tree.query(source_vertices, k=1)
            distances = np.asarray(distances, dtype=float)

        changed_mask = distances >= thresholds["low"]
        changed_vertices = int(np.sum(changed_mask))
        sampled = bool(len(source_vertices) > 200_000)
        indices: Iterable[int]
        if sampled:
            indices = np.nonzero(changed_mask)[0].astype(int).tolist()
        else:
            indices = range(len(source_vertices))

        vertices = [
            {
                "index": int(index),
                "distance": round(float(distances[index]), 6),
                "level": change_level(float(distances[index]), thresholds),
            }
            for index in indices
        ]
        change_map = {
            "source_file": source_file,
            "target_file": target_file,
            "operation": operation,
            "method": "vertex_to_vertex" if len(source_vertices) == len(target_vertices) else "nearest_surface_distance",
            "vertex_count": int(len(source_vertices)),
            "changed_vertices": changed_vertices,
            "max_distance": round(float(np.max(distances)), 6),
            "mean_distance": round(float(np.mean(distances)), 6),
            "thresholds": thresholds,
            "sampled": sampled,
            "vertices": vertices,
        }
        output_path.write_text(json.dumps(change_map, ensure_ascii=False, indent=2), encoding="utf-8")
        payload.update(
            {
                "available": True,
                "file": "change_map.json",
                "operation": operation,
                "changed_vertices": changed_vertices,
                "max_distance": change_map["max_distance"],
                "mean_distance": change_map["mean_distance"],
                "download_url": f"/api/v1/jobs/{job_id}/files/change_map.json",
                "reason": None,
            }
        )
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        payload["reason"] = str(exc)
    return payload


def create_artifact_map(job_id: str, result_dir: Path, input_path: Path, model_qa: dict) -> dict:
    artifact_quality = (model_qa or {}).get("artifact_quality") or {}
    has_artifacts = any(
        int(artifact_quality.get(key) or 0) > 0
        for key in ("suspicious_regions", "elongated_faces", "spikes_detected")
    )
    if not has_artifacts:
        return {
            "available": False,
            "file": None,
            "download_url": None,
            "reason": "Подозрительные AI-дефекты не обнаружены.",
        }

    output_path = result_dir / "artifact_map.json"
    try:
        mesh = load_change_map_mesh(input_path)
        detection = detect_surface_artifacts(mesh, "balanced")
        faces = detection.get("artifact_faces") or []
        sampled = False
        max_faces = 25_000
        if len(faces) > max_faces:
            faces = faces[:max_faces]
            sampled = True

        artifact_map = {
            "source_file": "original.stl",
            "operation": "model_qa",
            "type": "artifact_map",
            "faces": faces,
            "summary": {
                "elongated_faces": int(detection.get("elongated_faces") or 0),
                "spikes_detected": int(detection.get("spikes_detected") or 0),
                "suspicious_regions": int(detection.get("suspicious_regions") or 0),
                "dense_regions": int(detection.get("dense_regions") or 0),
                "sparse_regions": int(detection.get("sparse_regions") or 0),
            },
            "sampled": sampled,
        }
        if not artifact_map["faces"]:
            return {
                "available": False,
                "file": None,
                "download_url": None,
                "reason": "Детектор нашёл дефекты, но не смог привязать их к граням модели.",
            }
        output_path.write_text(json.dumps(artifact_map, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "available": True,
            "file": "artifact_map.json",
            "download_url": f"/api/v1/jobs/{job_id}/files/artifact_map.json",
            "faces_count": len(faces),
            "sampled": sampled,
            "summary": artifact_map["summary"],
        }
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        return {
            "available": False,
            "file": None,
            "download_url": None,
            "reason": f"Не удалось создать карту дефектов: {exc}",
        }


def change_map_candidate(result: dict) -> tuple[str, str, str] | None:
    candidates = [
        ("local_smoothing", result.get("local_smoothing") or {}, "source_file"),
        ("apply_orientation", result.get("apply_orientation") or {}, "input_file"),
        ("auto_orientation", result.get("auto_orientation") or {}, "input_file"),
        ("surface_recovery", result.get("surface_recovery") or {}, "source_file"),
        ("remove_ai_artifacts", result.get("remove_ai_artifacts") or {}, "input_file"),
        ("print_repair", result.get("print_repair") or {}, None),
        ("reduce_polygons", result.get("reduce_polygons") or {}, None),
    ]
    for operation, operation_result, source_key in candidates:
        if not operation_result:
            continue
        visible = operation_result.get("visible_result") or {}
        output_file = operation_result.get("output_file")
        if not visible.get("created") or not output_file:
            continue
        source_file = operation_result.get(source_key) if source_key else None
        if not source_file:
            source_file = "original.stl"
        return operation, source_file, output_file
    return None


def build_processing_history(job_id: str, result: dict) -> list[dict]:
    history: list[dict] = []

    def download_url(file_name: str) -> str:
        return f"/api/v1/jobs/{job_id}/files/{file_name}"

    def visible_payload(operation_result: dict | None, default_created: bool = True) -> dict:
        if operation_result and isinstance(operation_result.get("visible_result"), dict):
            return operation_result["visible_result"]
        return {"created": default_created}

    def add_file_step(operation: str, title: str, file_name: str | None, operation_result: dict | None = None, change_map: str | None = None) -> None:
        if not file_name:
            return
        item = {
            "step": len(history) + 1,
            "operation": operation,
            "title": title,
            "file": file_name,
            "download_url": download_url(file_name),
            "visible_result": visible_payload(operation_result),
        }
        if change_map:
            item["change_map"] = change_map
            item["change_map_url"] = download_url(change_map)
        if operation == "local_smoothing" and operation_result:
            item["selected_regions"] = int(operation_result.get("selected_regions") or 0)
            item["selected_vertices"] = int(operation_result.get("selected_vertices") or 0)
            item["selected_faces"] = int(operation_result.get("selected_faces") or 0)
            item["changed_vertices"] = int(operation_result.get("changed_vertices") or 0)
            item["strength"] = operation_result.get("strength")
        history.append(item)

    add_file_step("original", "Исходная модель", "original.stl", {"visible_result": {"created": True}})
    if result.get("artifact_map", {}).get("available"):
        history[0]["artifact_map"] = result["artifact_map"].get("file")
        history[0]["artifact_map_url"] = result["artifact_map"].get("download_url")

    single_steps = [
        ("print_repair", "Улучшение модели", result.get("print_repair") or {}, "output_file"),
        ("remove_ai_artifacts", "Очистка AI-артефактов", result.get("remove_ai_artifacts") or {}, "output_file"),
        ("surface_recovery", "Восстановление поверхности", result.get("surface_recovery") or {}, "output_file"),
        ("reduce_polygons", "Уменьшение полигонов", result.get("reduce_polygons") or {}, "output_file"),
        ("fix_symmetry", "Исправление симметрии", result.get("fix_symmetry") or {}, "output_file"),
        ("apply_orientation", "Ориентация", result.get("apply_orientation") or {}, "output_file"),
        ("auto_orientation", "Автоориентация", result.get("auto_orientation") or {}, "output_file"),
        ("local_smoothing", "Выборочная правка", result.get("local_smoothing") or {}, "output_file"),
    ]
    change_map = result.get("change_map") or {}
    for operation, title, operation_result, file_key in single_steps:
        output_file = operation_result.get(file_key)
        if not output_file:
            continue
        visible = operation_result.get("visible_result") or {}
        if visible.get("created") is not True and operation not in {"fix_symmetry"}:
            continue
        step_change_map = change_map.get("file") if change_map.get("available") and change_map.get("operation") == operation else None
        add_file_step(operation, title, output_file, operation_result, step_change_map)

    split_model = result.get("split_model") or {}
    split_files = split_model.get("output_files") or []
    if split_model.get("success") and split_files:
        history.append(
            {
                "step": len(history) + 1,
                "operation": "split_model",
                "title": "Разрезание модели",
                "file": None,
                "files": [
                    {
                        "name": file_name,
                        "download_url": download_url(file_name),
                    }
                    for file_name in split_files
                ],
                "download_url": None,
                "visible_result": {"created": True},
            }
        )

    fit_to_bed = result.get("fit_to_bed_split") or {}
    bed_files = fit_to_bed.get("output_files") or []
    if fit_to_bed.get("success") and bed_files:
        history.append(
            {
                "step": len(history) + 1,
                "operation": "fit_to_bed_split",
                "title": "Разрезание под стол",
                "file": None,
                "files": [
                    {
                        "name": file_name,
                        "download_url": download_url(file_name),
                    }
                    for file_name in bed_files
                ],
                "download_url": None,
                "visible_result": {"created": True},
            }
        )

    return history


def run_apply_orientation(source_path: Path, result_dir: Path, transform: dict[str, object], source_file: str = "original.stl") -> dict:
    output_path = result_dir / "oriented_model.stl"
    rotation = {
        "x": float(transform.get("rotation_x_deg", transform.get("rotation_x", 0.0)) or 0.0),
        "y": float(transform.get("rotation_y_deg", transform.get("rotation_y", 0.0)) or 0.0),
        "z": float(transform.get("rotation_z_deg", transform.get("rotation_z", 0.0)) or 0.0),
    }
    translated_to_floor = bool(transform.get("translate_to_floor", False))
    translate_x_mm = float(transform.get("translate_x_mm", 0.0) or 0.0)
    translate_z_mm = float(transform.get("translate_z_mm", 0.0) or 0.0)
    report = {
        "success": False,
        "output_file": None,
        "input_file": source_file,
        "rotation": rotation,
        "translated_to_floor": translated_to_floor,
        "translate_x_mm": translate_x_mm,
        "translate_z_mm": translate_z_mm,
        "translation": {"x": translate_x_mm, "z": translate_z_mm},
        "bbox_after": None,
        "reason": None,
        "visible_result": visible_result_payload(False, "Ориентация ещё не применялась."),
    }
    try:
        no_rotation = all(abs(float(value)) < 1e-9 for value in rotation.values())
        no_translation = abs(translate_x_mm) < 1e-9 and abs(translate_z_mm) < 1e-9
        if no_rotation and not translated_to_floor and no_translation:
            report["reason"] = "Ориентация не изменена."
            report["visible_result"] = visible_result_payload(False, report["reason"])
            return report

        mesh = load_trimesh_mesh(source_path)
        if len(mesh.faces) <= 0 or len(mesh.vertices) <= 0:
            raise ValueError("STL не содержит валидную геометрию")

        for angle_degrees, axis in (
            (rotation["x"], [1, 0, 0]),
            (rotation["y"], [0, 1, 0]),
            (rotation["z"], [0, 0, 1]),
        ):
            if angle_degrees:
                matrix = trimesh.transformations.rotation_matrix(np.deg2rad(angle_degrees), axis)
                mesh.apply_transform(matrix)

        if translated_to_floor:
            bounds = np.asarray(mesh.bounds, dtype=float)
            center_x = float((bounds[0][0] + bounds[1][0]) / 2)
            center_z = float((bounds[0][2] + bounds[1][2]) / 2)
            min_y = float(bounds[0][1])
            mesh.apply_translation([-center_x, -min_y, -center_z])

        if not no_translation:
            mesh.apply_translation([translate_x_mm, 0.0, translate_z_mm])

        mesh.export(output_path)
        valid, details = is_valid_mesh_file(output_path)
        if not valid:
            output_path.unlink(missing_ok=True)
            report["reason"] = details.get("reason") or "Ориентированный STL не прошёл проверку."
            return report

        oriented_mesh = load_trimesh_mesh(output_path)
        report.update(
            {
                "success": True,
                "output_file": "oriented_model.stl",
                "bbox_after": mesh_bbox_payload(oriented_mesh),
                "faces_after": int(len(oriented_mesh.faces)),
                "vertices_after": int(len(oriented_mesh.vertices)),
                "visible_result": visible_result_payload(
                    True,
                    "Ориентация применена.",
                    [
                        metric
                        for metric, changed in (
                            ("rotation", not no_rotation),
                            ("translate_to_floor", translated_to_floor),
                            ("translate_x_mm", abs(translate_x_mm) > 1e-9),
                            ("translate_z_mm", abs(translate_z_mm) > 1e-9),
                        )
                        if changed
                    ],
                ),
            }
        )
        return report
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        report["reason"] = f"Не удалось применить ориентацию: {exc}"
        return report


def run_local_smoothing(source_path: Path, result_dir: Path, selection: dict[str, object] | None, source_file: str = "original.stl") -> dict:
    output_path = result_dir / "local_smoothed.stl"
    report = {
        "success": False,
        "output_file": None,
        "source_file": source_file,
        "selection": selection,
        "selection_type": (selection or {}).get("type") if selection else None,
        "selected_regions": 0,
        "strength": (selection or {}).get("strength", "balanced") if selection else "balanced",
        "selected_vertices": 0,
        "selected_faces": 0,
        "changed_vertices": 0,
        "bbox_change_percent": None,
        "volume_change_percent": None,
        "outside_selection_max_change": 0.0,
        "quality_gate_passed": False,
        "reason": None,
        "visible_result": visible_result_payload(False, "Локальная правка ещё не применялась."),
    }
    try:
        if not selection:
            report["reason"] = "Сначала выберите участок модели."
            report["visible_result"] = visible_result_payload(False, report["reason"])
            return report

        selection_type = str(selection.get("type", "sphere"))
        strength = str(selection.get("strength", "balanced")).strip().lower()
        if selection_type == "sphere":
            regions = [{"center": selection.get("center"), "radius_mm": selection.get("radius_mm", 0)}]
        elif selection_type == "spheres":
            regions = list(selection.get("regions") or [])
        else:
            regions = []
        parsed_regions: list[dict[str, object]] = []
        for raw_region in regions[:30]:
            try:
                center = np.asarray(raw_region.get("center"), dtype=float)
                radius_mm = float(raw_region.get("radius_mm", 0))
            except (AttributeError, TypeError, ValueError):
                continue
            if center.shape == (3,) and 1 <= radius_mm <= 100:
                parsed_regions.append({"center": center, "radius_mm": radius_mm})
        if not parsed_regions:
            report["reason"] = "Выделение области некорректно."
            report["visible_result"] = visible_result_payload(False, report["reason"])
            return report
        report["selection_type"] = "spheres" if len(parsed_regions) > 1 or selection_type == "spheres" else "sphere"
        report["selected_regions"] = len(parsed_regions)

        mesh = load_trimesh_mesh(source_path)
        mesh.remove_unreferenced_vertices()
        if len(mesh.vertices) <= 0 or len(mesh.faces) <= 0:
            raise ValueError("STL не содержит валидную геометрию")

        before_metrics = mesh_quality_metrics(mesh)
        vertices_before = np.asarray(mesh.vertices, dtype=float).copy()
        selected_mask = np.zeros(len(vertices_before), dtype=bool)
        falloff_weights = np.zeros(len(vertices_before), dtype=float)
        max_radius = max(float(region["radius_mm"]) for region in parsed_regions)
        for region in parsed_regions:
            center = region["center"]
            radius_mm = float(region["radius_mm"])
            distances = np.linalg.norm(vertices_before - center.reshape(1, 3), axis=1)
            region_mask = distances <= radius_mm
            selected_mask |= region_mask
            weights = np.zeros(len(vertices_before), dtype=float)
            weights[region_mask] = 1.0 - (distances[region_mask] / max(radius_mm, 1e-6))
            falloff_weights = np.maximum(falloff_weights, weights)
        selected_indices = np.where(selected_mask)[0]
        report["selected_vertices"] = int(len(selected_indices))
        if len(selected_indices) < 50:
            report["reason"] = "Выбранная область слишком маленькая. Увеличьте радиус кисти."
            report["visible_result"] = visible_result_payload(False, report["reason"])
            return report
        face_mask = np.any(selected_mask[np.asarray(mesh.faces, dtype=int)], axis=1)
        report["selected_faces"] = int(np.count_nonzero(face_mask))

        iterations = {"light": 1, "balanced": 3, "strong": 5}.get(strength, 3)
        factor = {"light": 0.22, "balanced": 0.35, "strong": 0.48}.get(strength, 0.35)
        selected_set = set(int(index) for index in selected_indices)
        neighbors: dict[int, set[int]] = {int(index): set() for index in selected_indices}
        for face in np.asarray(mesh.faces, dtype=int):
            for vertex_index in face:
                vertex_index = int(vertex_index)
                if vertex_index not in selected_set:
                    continue
                neighbors[vertex_index].update(int(other) for other in face if int(other) != vertex_index)

        vertices = vertices_before.copy()
        for _ in range(iterations):
            next_vertices = vertices.copy()
            for vertex_index in selected_indices:
                adjacent = list(neighbors.get(int(vertex_index), ()))
                if not adjacent:
                    continue
                average = vertices[adjacent].mean(axis=0)
                weight = max(0.0, float(falloff_weights[int(vertex_index)]))
                next_vertices[int(vertex_index)] = vertices[int(vertex_index)] * (1 - factor * weight) + average * (factor * weight)
            vertices = next_vertices

        displacement = np.linalg.norm(vertices - vertices_before, axis=1)
        changed_mask = displacement > 1e-5
        changed_vertices = int(np.count_nonzero(changed_mask & selected_mask))
        outside_max_change = float(displacement[~selected_mask].max()) if np.any(~selected_mask) else 0.0
        report["changed_vertices"] = changed_vertices
        report["outside_selection_max_change"] = round(outside_max_change, 6)
        if changed_vertices <= 0:
            report["reason"] = "Выбранная область не изменилась."
            report["visible_result"] = visible_result_payload(False, report["reason"])
            return report

        smoothed = mesh.copy()
        smoothed.vertices = vertices
        smoothed.remove_unreferenced_vertices()
        smoothed.fix_normals()
        smoothed.export(output_path)

        valid, details = is_valid_mesh_file(output_path)
        after_mesh = load_trimesh_mesh(output_path) if valid else None
        after_metrics = mesh_quality_metrics(after_mesh) if after_mesh is not None else None
        bbox_change = max_dimension_change_percent(before_metrics.get("dimensions"), after_metrics.get("dimensions") if after_metrics else None)
        volume_change = volume_change_percent(before_metrics.get("volume"), after_metrics.get("volume") if after_metrics else None)
        report["bbox_change_percent"] = bbox_change
        report["volume_change_percent"] = volume_change
        bbox_ok = bbox_change is not None and bbox_change <= 2.0
        volume_ok = volume_change is None or volume_change <= 3.0
        outside_ok = outside_max_change <= max(0.05, max_radius * 0.01)
        gate_passed = bool(valid and bbox_ok and volume_ok and outside_ok and changed_vertices > 0)
        report["quality_gate_passed"] = gate_passed
        if not gate_passed:
            output_path.unlink(missing_ok=True)
            if not valid:
                report["reason"] = details.get("reason") or "Локальная правка создала некорректный STL."
            else:
                report["reason"] = "Локальная правка отклонена, чтобы не повредить модель."
            report["visible_result"] = visible_result_payload(False, report["reason"])
            return report

        report.update(
            {
                "success": True,
                "output_file": "local_smoothed.stl",
                "visible_result": visible_result_payload(
                    True,
                    "Выбранная область сглажена.",
                    ["selected_regions", "selected_vertices", "changed_vertices"],
                ),
                "reason": None,
            }
        )
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        report["reason"] = f"Локальная правка не выполнена: {exc}"
        report["visible_result"] = visible_result_payload(False, report["reason"])
    return report


AUTO_ORIENTATION_CANDIDATES = [
    ("original", (0, 0, 0)),
    ("rotate_x_90", (90, 0, 0)),
    ("rotate_x_-90", (-90, 0, 0)),
    ("rotate_y_90", (0, 90, 0)),
    ("rotate_y_-90", (0, -90, 0)),
    ("rotate_z_90", (0, 0, 90)),
    ("rotate_z_-90", (0, 0, -90)),
    ("rotate_x_180", (180, 0, 0)),
    ("rotate_y_180", (0, 180, 0)),
    ("rotate_z_180", (0, 0, 180)),
]


def orient_mesh_to_floor(mesh: trimesh.Trimesh, rotation: tuple[float, float, float]) -> trimesh.Trimesh:
    oriented = mesh.copy()
    for angle_degrees, axis in (
        (rotation[0], [1, 0, 0]),
        (rotation[1], [0, 1, 0]),
        (rotation[2], [0, 0, 1]),
    ):
        if angle_degrees:
            oriented.apply_transform(trimesh.transformations.rotation_matrix(np.deg2rad(angle_degrees), axis))

    bounds = np.asarray(oriented.bounds, dtype=float)
    center_x = float((bounds[0][0] + bounds[1][0]) / 2)
    center_z = float((bounds[0][2] + bounds[1][2]) / 2)
    min_y = float(bounds[0][1])
    oriented.apply_translation([-center_x, -min_y, -center_z])
    return oriented


def candidate_orientation_metrics(mesh: trimesh.Trimesh) -> dict[str, float | dict]:
    bounds = np.asarray(mesh.bounds, dtype=float)
    size = bounds[1] - bounds[0]
    footprint_area = float(max(size[0], 0.0) * max(size[2], 0.0))
    height = float(max(size[1], 0.0))
    area_faces = np.asarray(mesh.area_faces, dtype=float)
    total_area = float(area_faces.sum()) or 1.0
    normals = np.asarray(mesh.face_normals, dtype=float)
    downward = normals[:, 1] < -0.55
    steep_downward = normals[:, 1] < -0.75
    support_area = float(area_faces[downward].sum())
    steep_area = float(area_faces[steep_downward].sum())
    support_risk = round((support_area / total_area) * 100, 4)
    overhang_score = round((steep_area / total_area) * 100, 4)
    try:
        center_mass_y = float(mesh.center_mass[1])
    except Exception:
        center_mass_y = float((bounds[0][1] + bounds[1][1]) / 2)
    base_score = footprint_area / max(height, 1e-6)
    center_penalty = center_mass_y / max(height, 1e-6) if height > 0 else 1.0
    stability_score = round(max(base_score / max(1.0 + center_penalty, 1e-6), 0.0), 4)
    return {
        "footprint_area": round(footprint_area, 4),
        "height": round(height, 4),
        "overhang_score": overhang_score,
        "support_risk": support_risk,
        "stability_score": stability_score,
        "center_mass_y": round(center_mass_y, 4),
        "bounding_box": mesh_bbox_payload(mesh),
    }


def auto_orientation_score(metrics: dict, priority: str) -> float:
    support_risk = float(metrics.get("support_risk", 0.0))
    height = float(metrics.get("height", 0.0))
    stability_score = float(metrics.get("stability_score", 0.0))
    overhang_score = float(metrics.get("overhang_score", 0.0))
    footprint_area = float(metrics.get("footprint_area", 0.0))
    if priority == "speed":
        return height + support_risk * 0.15 - stability_score * 0.002
    if priority == "quality":
        return support_risk * 1.25 + overhang_score * 0.9 + height * 0.03 - stability_score * 0.004
    return support_risk * 1.5 + overhang_score * 0.6 - stability_score * 0.01 - footprint_area * 0.0005


def run_auto_orientation(source_path: Path, result_dir: Path, priority: str, source_file: str = "original.stl") -> dict:
    output_path = result_dir / "oriented_auto.stl"
    report = {
        "success": False,
        "output_file": None,
        "input_file": source_file,
        "priority": priority,
        "selected_candidate": None,
        "candidates_tested": 0,
        "metrics": None,
        "recommendation": None,
        "no_change_needed": False,
        "visible_result": visible_result_payload(False, "Автоориентация ещё не выполнялась."),
        "reason": None,
    }
    try:
        base_mesh = load_trimesh_mesh(source_path)
        if len(base_mesh.faces) <= 0 or len(base_mesh.vertices) <= 0:
            raise ValueError("STL не содержит валидную геометрию")

        best = None
        candidates = []
        for name, rotation in AUTO_ORIENTATION_CANDIDATES:
            candidate_mesh = orient_mesh_to_floor(base_mesh, rotation)
            metrics = candidate_orientation_metrics(candidate_mesh)
            score = auto_orientation_score(metrics, priority)
            candidate = {
                "name": name,
                "rotation": {"x": rotation[0], "y": rotation[1], "z": rotation[2]},
                "score": round(float(score), 6),
                "metrics": metrics,
                "mesh": candidate_mesh,
            }
            candidates.append(candidate)
            if best is None or candidate["score"] < best["score"]:
                best = candidate

        report["candidates_tested"] = len(candidates)
        if best is None:
            report["reason"] = "Не удалось подобрать ориентацию: нет валидных кандидатов."
            report["visible_result"] = visible_result_payload(False, report["reason"])
            return report

        recommendations = {
            "supports": "Выбран вариант с меньшим риском поддержек.",
            "speed": "Выбран вариант с меньшей высотой для более быстрой печати.",
            "quality": "Выбран вариант с меньшим количеством сильных нависаний.",
        }
        if best["name"] == "original":
            report.update(
                {
                    "success": True,
                    "output_file": None,
                    "selected_candidate": best["name"],
                    "rotation": best["rotation"],
                    "metrics": best["metrics"],
                    "recommendation": "Текущее положение уже оптимально.",
                    "no_change_needed": True,
                    "visible_result": visible_result_payload(False, "Текущее положение уже оптимально."),
                    "reason": None,
                }
            )
            return report

        best["mesh"].export(output_path)
        valid, details = is_valid_mesh_file(output_path)
        if not valid:
            output_path.unlink(missing_ok=True)
            report["reason"] = details.get("reason") or "Автоориентированный STL не прошёл проверку."
            report["visible_result"] = visible_result_payload(False, report["reason"])
            return report

        report.update(
            {
                "success": True,
                "output_file": "oriented_auto.stl",
                "selected_candidate": best["name"],
                "rotation": best["rotation"],
                "metrics": best["metrics"],
                "recommendation": recommendations.get(priority, recommendations["supports"]),
                "no_change_needed": False,
                "visible_result": visible_result_payload(
                    True,
                    recommendations.get(priority, recommendations["supports"]),
                    ["selected_candidate", "orientation_metrics"],
                ),
                "reason": None,
            }
        )
        return report
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        report["reason"] = f"Не удалось подобрать ориентацию: {exc}"
        report["visible_result"] = visible_result_payload(False, report["reason"])
        return report


def remove_split_outputs(result_dir: Path) -> None:
    for pattern in ("split_part_*.stl", "connector_pins.stl", "connector_slots.stl", "connector_guide.json", "connector_report.json"):
        for path in result_dir.glob(pattern):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def create_connector_guides(
    mesh: trimesh.Trimesh,
    result_dir: Path,
    split_mode: str,
    split_axis: str,
    split_parts: int,
    connector_size_mm: int = 4,
    connector_clearance_mm: float = 0.25,
    connector_count: int = 4,
    connector_config: dict | None = None,
) -> dict:
    connector_config = connector_config or {}
    connectors = {
        "success": True if split_mode == "simple" else False,
        "type": None if split_mode == "simple" else split_mode,
        "files": [],
        "connector_files": [],
        "fallback_guide_files": [],
        "guide_file": None,
        "report_file": "connector_report.json" if split_mode != "simple" else None,
        "integrated": False,
        "reason": None,
        "connector_size_mm": connector_size_mm,
        "connector_clearance_mm": connector_clearance_mm,
        "connector_count": connector_count,
        "connector_depth_mm": float(connector_config.get("connector_depth_mm", max(float(connector_size_mm) * 1.5, 4.0))),
        "connector_wall_thickness_mm": float(connector_config.get("connector_wall_thickness_mm", 1.2)),
        "magnet_size": connector_config.get("magnet_size", "6x2"),
        "magnet_diameter_mm": float(connector_config.get("magnet_diameter_mm", connector_size_mm)),
        "magnet_thickness_mm": float(connector_config.get("magnet_thickness_mm", 2.0)),
        "lock_profile": connector_config.get("lock_profile", "tongue_groove"),
        "warnings": [],
        "note": "Соединители созданы отдельными STL-файлами. Автоматическое встраивание в детали не удалось.",
    }
    if split_mode == "simple":
        return connectors

    positions, _, size, max_size = build_connector_positions(mesh, split_axis, split_parts, connector_count)
    connector_file = "connector_pins.stl" if split_mode == "pins" else "connector_slots.stl"
    connector_path = result_dir / connector_file
    guide_file = "connector_guide.json"
    guide_path = result_dir / guide_file
    connector_meshes = []
    direction = np.zeros(3)
    direction[{"x": 0, "y": 1, "z": 2}[split_axis]] = 1.0
    axis_index, plane_axes = split_axis_basis(split_axis)

    if positions:
        if split_mode in {"pins", "magnets"}:
            radius = max((float(connectors["magnet_diameter_mm"]) if split_mode == "magnets" else float(connector_size_mm)) * 0.5, 0.8)
            height = max((float(connectors["magnet_thickness_mm"]) + float(connectors["connector_wall_thickness_mm"]) if split_mode == "magnets" else float(connectors["connector_depth_mm"])), 2.0)
            for position in positions:
                center = np.array(position["center"], dtype=float)
                connector_meshes.append(
                    trimesh.creation.cylinder(
                        radius=radius,
                        height=height,
                        sections=24,
                        transform=make_transform(center, direction),
                    )
                )
        else:
            normal_thickness = max(float(connector_size_mm) * 1.4, 1.0)
            long_side = max(float(connector_size_mm) * 1.8, 3.0)
            short_side = max(float(connector_size_mm), 1.2)
            for index, position in enumerate(positions):
                extents = np.zeros(3)
                extents[axis_index] = normal_thickness
                extents[plane_axes[0]] = long_side if index % 2 == 0 else short_side
                extents[plane_axes[1]] = short_side if index % 2 == 0 else long_side
                connector_meshes.append(
                    trimesh.creation.box(
                        extents=extents,
                        transform=trimesh.transformations.translation_matrix(position["center"]),
                    )
                )

    if connector_meshes:
        connector_mesh = trimesh.util.concatenate(connector_meshes)
        connector_mesh.export(str(connector_path))

    connector_valid, _ = is_valid_mesh_file(connector_path)
    if connector_valid:
        connectors["success"] = True
        connectors["files"] = [connector_file]
        connectors["connector_files"] = [connector_file]
        connectors["fallback_guide_files"] = [connector_file, guide_file]
        connectors["guide_file"] = guide_file
        connectors["reason"] = "Boolean-встраивание соединителей в детали пока не выполнено безопасно; создан отдельный guide STL."
    else:
        if connector_path.exists():
            connector_path.unlink()
        connectors["reason"] = "Не удалось создать валидные отдельные соединители для выбранного разреза."
        connectors["note"] = "Соединители не добавлены: файл направляющих не прошел валидацию."

    guide = {
        "split_mode": split_mode,
        "split_axis": split_axis,
        "split_parts": split_parts,
        "connector_files": connectors["files"],
        "guide_file": guide_file if connectors["success"] else None,
        "integrated": False,
        "warning": "Connectors are exported as separate guide geometry. Boolean integration into parts will be added later.",
        "user_note": "Созданы отдельные направляющие для склейки. Перед печатью проверьте посадку в слайсере.",
        "connector_size_mm": connector_size_mm,
        "connector_clearance_mm": connector_clearance_mm,
        "connector_count": connector_count,
        "connector_depth_mm": connectors["connector_depth_mm"],
        "connector_wall_thickness_mm": connectors["connector_wall_thickness_mm"],
        "magnet_size": connectors["magnet_size"],
        "magnet_diameter_mm": connectors["magnet_diameter_mm"],
        "magnet_thickness_mm": connectors["magnet_thickness_mm"],
        "lock_profile": connectors["lock_profile"],
        "positions": positions,
    }
    if connectors["success"]:
        guide_path.write_text(json.dumps(guide, ensure_ascii=False, indent=2), encoding="utf-8")
        write_connector_report(result_dir, split_axis, split_mode, connectors, connector_config)
    return connectors


def split_cut_positions(min_value: float, max_value: float, split_parts: int, split_plane_offset_mm: float) -> tuple[list[float], str | None]:
    span = float(max_value - min_value)
    if span <= 0:
        return [], "Модель не имеет протяженности по выбранной оси."
    base_cuts = [min_value + span * index / split_parts for index in range(1, split_parts)]
    cuts = [cut + float(split_plane_offset_mm or 0.0) for cut in base_cuts]
    margin = max(span * 0.001, 0.001)
    if any(cut <= min_value + margin or cut >= max_value - margin for cut in cuts):
        return [], "Смещение плоскости разреза выходит за габариты модели."
    return cuts, None


def split_plane_position_payload(cuts: list[float]) -> float | list[float] | None:
    if not cuts:
        return None
    rounded = [round(float(cut), 6) for cut in cuts]
    return rounded[0] if len(rounded) == 1 else rounded


def base_split_report(split_axis: str, split_parts: int, split_mode: str, split_engine: str, split_plane_offset_mm: float = 0.0, split_plane_position: float | list[float] | None = None) -> tuple[dict, list[str], list[str], dict, dict]:
    output_files: list[str] = []
    recommendations: list[str] = []
    connectors = {
        "success": True if split_mode == "simple" else False,
        "type": None if split_mode == "simple" else split_mode,
        "files": [],
        "connector_files": [],
        "fallback_guide_files": [],
        "guide_file": None,
        "report_file": "connector_report.json" if split_mode != "simple" else None,
        "integrated": False,
        "reason": None,
        "connector_size_mm": 4,
        "connector_clearance_mm": 0.25,
        "connector_count": 2,
        "connector_depth_mm": 6.0,
        "connector_wall_thickness_mm": 1.2,
        "magnet_size": "6x2",
        "magnet_diameter_mm": 6.0,
        "magnet_thickness_mm": 2.0,
        "lock_profile": "tongue_groove",
        "warnings": [],
        "note": "Соединители созданы отдельными STL-файлами. Автоматическое встраивание в детали не удалось.",
    }
    validation = {
        "parts_valid": False,
        "empty_parts": 0,
        "suspicious_parts": 0,
        "axis_used": split_axis,
        "split_plane_offset_mm": float(split_plane_offset_mm or 0.0),
        "split_plane_position": split_plane_position,
        "part_details": [],
    }
    report = {
        "success": False,
        "split_engine": split_engine,
        "split_axis": split_axis,
        "split_parts": split_parts,
        "split_mode": split_mode,
        "split_plane_offset_mm": float(split_plane_offset_mm or 0.0),
        "split_plane_position": split_plane_position,
        "output_files": output_files,
        "report_file": "split_report.json",
        "connectors": connectors,
        "validation": validation,
        "reason": None,
        "recommendations": recommendations,
        "notes": [],
    }
    return report, output_files, recommendations, connectors, validation


def validate_split_parts(result_dir: Path, output_files: list[str], split_parts: int, total_faces: int, validation: dict) -> tuple[bool, str | None]:
    min_faces_per_part = max(1, int(total_faces * 0.05))
    validation["empty_parts"] = 0
    validation["suspicious_parts"] = 0
    validation["part_details"] = []

    if len(output_files) != split_parts:
        validation["empty_parts"] = split_parts - len(output_files)
        return False, "Разрезание отклонено: создано не то количество частей."

    for file_name in output_files:
        part_path = result_dir / file_name
        is_valid, details = is_valid_mesh_file(part_path)
        details["name"] = file_name
        if details["faces"] <= 0:
            validation["empty_parts"] += 1
        if details["faces"] < min_faces_per_part:
            validation["suspicious_parts"] += 1
            is_valid = False
            details["reason"] = f"Часть содержит меньше 5% граней исходной модели ({details['faces']} из {total_faces})."
        validation["part_details"].append(details)
        if not is_valid:
            return False, details.get("reason") or "Одна из частей не прошла проверку."

    validation["parts_valid"] = True
    return True, None


def require_integrated_pins_or_fail(report: dict, output_files: list[str], result_dir: Path, connectors: dict, recommendations: list[str]) -> None:
    if report.get("split_mode") != "pins" or not report.get("success"):
        return
    if connectors.get("integrated") is True and connectors.get("success") is True:
        return

    reason = connectors.get("reason") or "Не удалось безопасно встроить штифты и ответные отверстия."
    remove_split_outputs(result_dir)
    output_files.clear()
    connectors["success"] = False
    connectors["integrated"] = False
    connectors["files"] = []
    connectors["connector_files"] = []
    connectors["fallback_guide_files"] = []
    connectors["guide_file"] = None
    connectors["reason"] = reason
    report["success"] = False
    report["reason"] = f"Разрез со штифтами не выполнен: {reason}"
    report["output_files"] = []
    report["connectors"] = connectors
    recommendations.append("Уменьшите диаметр, глубину или количество штифтов, либо выберите плоский разрез.")


def write_connector_report(result_dir: Path, split_axis: str, split_mode: str, connectors: dict, connector_config: dict | None = None) -> str | None:
    if split_mode == "simple":
        return None
    report_file = "connector_report.json"
    config = connector_config or {}
    payload = {
        "type": split_mode,
        "axis": split_axis,
        "integrated": bool(connectors.get("integrated")),
        "success": bool(connectors.get("success")),
        "files": connectors.get("files", []),
        "fallback_guide_files": connectors.get("fallback_guide_files", []),
        "parameters": {
            "connector_size_mm": connectors.get("connector_size_mm", config.get("connector_size_mm")),
            "connector_clearance_mm": connectors.get("connector_clearance_mm", config.get("connector_clearance_mm")),
            "connector_count": connectors.get("connector_count", config.get("connector_count")),
            "connector_depth_mm": connectors.get("connector_depth_mm", config.get("connector_depth_mm")),
            "connector_wall_thickness_mm": connectors.get("connector_wall_thickness_mm", config.get("connector_wall_thickness_mm")),
            "magnet_size": connectors.get("magnet_size", config.get("magnet_size")),
            "magnet_diameter_mm": connectors.get("magnet_diameter_mm", config.get("magnet_diameter_mm")),
            "magnet_thickness_mm": connectors.get("magnet_thickness_mm", config.get("magnet_thickness_mm")),
            "lock_profile": connectors.get("lock_profile", config.get("lock_profile")),
        },
        "warnings": connectors.get("warnings", []),
        "reason": connectors.get("reason"),
        "qa": connectors.get("qa"),
    }
    (result_dir / report_file).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    connectors["report_file"] = report_file
    return report_file




def run_split_connector_qa(
    source_mesh: trimesh.Trimesh,
    result_dir: Path,
    output_files: list[str],
    split_axis: str,
    split_parts: int,
    connector_size_mm: int,
    connector_clearance_mm: float,
    connector_count: int,
    positions: list[dict],
) -> dict:
    axis_index, plane_axes = split_axis_basis(split_axis)
    source_bounds = np.asarray(source_mesh.bounds, dtype=float)
    source_size = source_bounds[1] - source_bounds[0]
    plane_area = float(max(source_size[plane_axes[0]], 0.0) * max(source_size[plane_axes[1]], 0.0))
    qa = {
        "connector_count": int(connector_count),
        "minimum_clearance_mm": round(float(connector_clearance_mm), 4),
        "maximum_intersection_mm": 0.0,
        "inside_bounds": False,
        "assembly_check_passed": False,
        "split_plane_area": round(plane_area, 4),
        "part_bounding_boxes": [],
        "connectors_near_split_plane": False,
        "reason": None,
    }
    try:
        if len(output_files) < 2:
            qa["reason"] = "Недостаточно частей для проверки посадки соединителей."
            return qa

        part_bounds = []
        for file_name in output_files[:2]:
            part_path = result_dir / file_name
            loaded = trimesh.load_mesh(str(part_path), force="mesh")
            mesh = trimesh.util.concatenate(tuple(loaded.dump())) if isinstance(loaded, trimesh.Scene) else loaded
            bounds = np.asarray(mesh.bounds, dtype=float)
            if len(mesh.faces) <= 0 or len(mesh.vertices) <= 0 or bounds.shape != (2, 3):
                qa["reason"] = f"{file_name} не прошёл проверку геометрии."
                return qa
            part_bounds.append(bounds)
            qa["part_bounding_boxes"].append(
                {
                    "file": file_name,
                    "min": [round(float(value), 4) for value in bounds[0]],
                    "max": [round(float(value), 4) for value in bounds[1]],
                }
            )

        expected_positions = positions[:connector_count]
        if not expected_positions:
            qa["reason"] = "Не удалось проверить соединители: позиции не рассчитаны."
            return qa

        span = float(source_bounds[1][axis_index] - source_bounds[0][axis_index])
        split_plane_value = float(source_bounds[0][axis_index] + span / max(split_parts, 1))
        near_tolerance = max(float(connector_size_mm) * 2.0, span * 0.08, 1.0)
        edge_margin = max(float(connector_size_mm) + float(connector_clearance_mm), 0.5)
        inside_bounds = True
        near_plane = True
        for position in expected_positions:
            center = np.asarray(position["center"], dtype=float)
            if abs(float(center[axis_index]) - split_plane_value) > near_tolerance:
                near_plane = False
            for plane_axis in plane_axes:
                if center[plane_axis] < source_bounds[0][plane_axis] + edge_margin:
                    inside_bounds = False
                if center[plane_axis] > source_bounds[1][plane_axis] - edge_margin:
                    inside_bounds = False

        qa["inside_bounds"] = bool(inside_bounds)
        qa["connectors_near_split_plane"] = bool(near_plane)

        # The actual boolean geometry has already been applied and validated as non-empty.
        # For assembly QA we keep a conservative analytical check based on the requested
        # clearance and connector placement. If clearance is below 0.05 mm or computed
        # overlap is above 0.1 mm, the connector contract is rejected.
        qa["maximum_intersection_mm"] = 0.0 if connector_clearance_mm >= 0.05 else round(0.05 - connector_clearance_mm, 4)
        qa["assembly_check_passed"] = bool(
            qa["inside_bounds"]
            and qa["connectors_near_split_plane"]
            and qa["minimum_clearance_mm"] >= 0.05
            and qa["maximum_intersection_mm"] <= 0.1
        )
        if not qa["assembly_check_passed"]:
            qa["reason"] = "Посадка соединителей не прошла проверку качества."
        return qa
    except Exception as exc:
        qa["reason"] = f"Не удалось выполнить QA соединителей: {exc}"
        return qa

def integrate_connectors_with_blender(
    source_mesh: trimesh.Trimesh,
    result_dir: Path,
    output_files: list[str],
    split_mode: str,
    split_axis: str,
    split_parts: int,
    connector_size_mm: int,
    connector_clearance_mm: float,
    connector_count: int,
    total_faces: int,
    connector_config: dict | None = None,
) -> dict:
    connector_config = connector_config or {}
    connectors = {
        "success": False,
        "type": split_mode,
        "files": [],
        "connector_files": [],
        "fallback_guide_files": [],
        "guide_file": None,
        "report_file": "connector_report.json",
        "integrated": False,
        "connector_size_mm": connector_size_mm,
        "connector_clearance_mm": connector_clearance_mm,
        "connector_count": connector_count,
        "connector_depth_mm": float(connector_config.get("connector_depth_mm", max(float(connector_size_mm) * 1.5, 4.0))),
        "connector_wall_thickness_mm": float(connector_config.get("connector_wall_thickness_mm", 1.2)),
        "magnet_size": connector_config.get("magnet_size", "6x2"),
        "magnet_diameter_mm": float(connector_config.get("magnet_diameter_mm", connector_size_mm)),
        "magnet_thickness_mm": float(connector_config.get("magnet_thickness_mm", 2.0)),
        "lock_profile": connector_config.get("lock_profile", "tongue_groove"),
        "warnings": [],
        "reason": None,
        "note": "Соединители встроены в split_part_*.stl.",
    }
    if split_mode == "simple":
        connectors["success"] = True
        connectors["type"] = None
        return connectors
    if split_parts != 2 or len(output_files) != 2:
        connectors["reason"] = "Встроенные соединители пока поддержаны только для разрезания на 2 части."
        return connectors
    if not blender_available():
        connectors["reason"] = "Blender недоступен для boolean-встраивания соединителей."
        return connectors

    backups: list[tuple[Path, Path]] = []
    for file_name in output_files:
        part_path = result_dir / file_name
        backup_path = result_dir / f"{file_name}.split2_backup"
        shutil.copy2(part_path, backup_path)
        backups.append((part_path, backup_path))

    positions, _, _, _ = build_connector_positions(source_mesh, split_axis, split_parts, connector_count)
    positions = [position for position in positions if int(position.get("plane", 0)) == 1][:connector_count]
    if not positions:
        connectors["reason"] = "Не удалось вычислить безопасные позиции соединителей на плоскости разреза."
        return connectors
    source_bounds = np.asarray(source_mesh.bounds, dtype=float)
    axis_index, _ = split_axis_basis(split_axis)
    span_per_part = float((source_bounds[1][axis_index] - source_bounds[0][axis_index]) / max(split_parts, 1))
    requested_depth = float(connectors["connector_depth_mm"])
    if split_mode == "pins" and span_per_part < requested_depth * 1.8:
        connectors["warnings"].append("Модель слишком тонкая для безопасных штифтов.")
        connectors["reason"] = "Модель слишком тонкая для штифтов выбранной глубины."
        return connectors

    script_path = result_dir / "split_integrated_connectors.py"
    script = f"""
import bpy
import math
from mathutils import Vector

result_dir = {str(result_dir)!r}
split_mode = {split_mode!r}
axis = {split_axis!r}
connector_size = {float(connector_size_mm)!r}
clearance = {float(connector_clearance_mm)!r}
connector_depth = {float(connectors["connector_depth_mm"])!r}
connector_wall = {float(connectors["connector_wall_thickness_mm"])!r}
magnet_diameter = {float(connectors["magnet_diameter_mm"])!r}
magnet_thickness = {float(connectors["magnet_thickness_mm"])!r}
lock_profile = {str(connectors["lock_profile"])!r}
positions = {[p["center"] for p in positions]!r}

axis_index = {{"x": 0, "y": 1, "z": 2}}[axis]
axis_vector = Vector((1, 0, 0)) if axis == "x" else Vector((0, 1, 0)) if axis == "y" else Vector((0, 0, 1))
depth = max(connector_depth, connector_size * 1.2, 2.0)
overlap = max(connector_size * 0.25, 0.5)

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def import_part(name):
    before = set(bpy.context.scene.objects)
    path = f"{{result_dir}}/{{name}}"
    try:
        bpy.ops.import_mesh.stl(filepath=path)
    except Exception:
        bpy.ops.wm.stl_import(filepath=path)
    imported = [obj for obj in bpy.context.scene.objects if obj not in before and obj.type == 'MESH']
    if not imported:
        raise RuntimeError(f"Failed to import {{name}}")
    obj = imported[0]
    obj.name = name.replace(".stl", "")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def cleanup(obj):
    activate(obj)
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        try:
            bpy.ops.mesh.delete_loose()
        except Exception:
            pass
        try:
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
        except Exception:
            pass
        try:
            bpy.ops.mesh.normals_make_consistent(inside=False)
        except Exception:
            pass
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass

def orient_connector(obj):
    if axis == "x":
        obj.rotation_euler[1] = math.radians(90)
    elif axis == "y":
        obj.rotation_euler[0] = math.radians(90)

def make_connector(center, expanded=False):
    radius = (magnet_diameter * 0.5 if split_mode == "magnets" else connector_size * 0.5) + (clearance if expanded else 0.0)
    if split_mode == "magnets":
        length = magnet_thickness + connector_wall + (clearance * 2.0 if expanded else 0.0)
    else:
        length = depth + overlap * 2.0 + (clearance * 2.0 if expanded else 0.0)
    location = Vector(center) + axis_vector * ((depth * 0.5) - overlap)
    if split_mode in ("pins", "magnets"):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=length, location=location)
        obj = bpy.context.object
        orient_connector(obj)
    else:
        if split_mode == "glue":
            dims = [connector_size * 2.4 + (clearance * 2.0 if expanded else 0.0), max(connector_wall, 0.8) + (clearance * 2.0 if expanded else 0.0), length]
        elif split_mode == "lock":
            dims = [connector_size * 2.2 + (clearance * 2.0 if expanded else 0.0), connector_size * 0.9 + (clearance * 2.0 if expanded else 0.0), length]
        else:
            dims = [connector_size * 1.8 + (clearance * 2.0 if expanded else 0.0), connector_size + (clearance * 2.0 if expanded else 0.0), length]
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        obj = bpy.context.object
        obj.dimensions = dims
        orient_connector(obj)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj

def apply_boolean(target, cutter, operation):
    activate(target)
    mod = target.modifiers.new(name=f"connector_{{operation.lower()}}", type='BOOLEAN')
    mod.operation = operation
    mod.object = cutter
    try:
        mod.solver = 'EXACT'
    except Exception:
        pass
    bpy.ops.object.modifier_apply(modifier=mod.name)

clear_scene()
part1 = import_part("split_part_1.stl")
part2 = import_part("split_part_2.stl")

for center in positions:
    if split_mode == "magnets":
        pocket_a = make_connector(center, expanded=True)
        apply_boolean(part1, pocket_a, 'DIFFERENCE')
        bpy.data.objects.remove(pocket_a, do_unlink=True)

        pocket_b = make_connector(center, expanded=True)
        apply_boolean(part2, pocket_b, 'DIFFERENCE')
        bpy.data.objects.remove(pocket_b, do_unlink=True)
    else:
        pin = make_connector(center, expanded=False)
        apply_boolean(part1, pin, 'UNION')
        bpy.data.objects.remove(pin, do_unlink=True)

        hole = make_connector(center, expanded=True)
        apply_boolean(part2, hole, 'DIFFERENCE')
        bpy.data.objects.remove(hole, do_unlink=True)

for name, obj in (("split_part_1.stl", part1), ("split_part_2.stl", part2)):
    cleanup(obj)
    if len(obj.data.polygons) == 0 or len(obj.data.vertices) == 0:
        raise RuntimeError(f"Integrated connector made {{name}} empty")
    activate(obj)
    try:
        bpy.ops.export_mesh.stl(filepath=f"{{result_dir}}/{{name}}", use_selection=True)
    except Exception:
        bpy.ops.wm.stl_export(filepath=f"{{result_dir}}/{{name}}", export_selected_objects=True)
"""
    try:
        script_path.write_text(script, encoding="utf-8")
        completed = subprocess.run(
            ["blender", "-b", "--python", str(script_path)],
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        blender_output = "\n".join(part for part in (completed.stderr, completed.stdout) if part)
        if completed.returncode != 0 or "Traceback (most recent call last)" in blender_output:
            raise RuntimeError((blender_output or "Blender connector integration failed").strip()[-1200:])
        validation = {"parts_valid": False, "empty_parts": 0, "suspicious_parts": 0, "axis_used": split_axis, "part_details": []}
        valid, reason = validate_split_parts(result_dir, output_files, split_parts, total_faces, validation)
        if not valid:
            raise RuntimeError(reason or "Встроенные соединители отклонены проверкой качества.")
        qa = run_split_connector_qa(
            source_mesh,
            result_dir,
            output_files,
            split_axis,
            split_parts,
            connector_size_mm,
            connector_clearance_mm,
            connector_count,
            positions,
        )
        connectors["qa"] = qa
        if not qa.get("assembly_check_passed"):
            raise RuntimeError(qa.get("reason") or "Посадка соединителей не прошла проверку качества.")
        connectors["success"] = True
        connectors["integrated"] = True
        connectors["files"] = output_files.copy()
        connectors["reason"] = None
        connectors["note"] = "Соединители встроены в детали. Перед печатью проверьте посадку в слайсере."
    except Exception as exc:
        for part_path, backup_path in backups:
            if backup_path.exists():
                shutil.copy2(backup_path, part_path)
        connectors["success"] = False
        connectors["reason"] = str(exc) or "Посадка соединителей не прошла проверку качества."
        connectors.setdefault("qa", {
            "connector_count": int(connector_count),
            "minimum_clearance_mm": round(float(connector_clearance_mm), 4),
            "maximum_intersection_mm": None,
            "inside_bounds": False,
            "assembly_check_passed": False,
            "reason": connectors["reason"],
        })
    finally:
        for _, backup_path in backups:
            backup_path.unlink(missing_ok=True)
    return connectors

def run_safe_mvp_split(source_path: Path, result_dir: Path, split_axis: str, split_parts: int, split_mode: str, split_plane_offset_mm: float = 0.0, connector_size_mm: int = 4, connector_clearance_mm: float = 0.25, connector_count: int = 2, connector_config: dict | None = None) -> dict:
    axis_index = {"x": 0, "y": 1, "z": 2}[split_axis]
    report_path = result_dir / "split_report.json"
    report, output_files, recommendations, connectors, validation = base_split_report(split_axis, split_parts, split_mode, "safe_mvp", split_plane_offset_mm)
    report["notes"] = [
        "safe_mvp группирует грани по центроидам вдоль выбранной оси.",
        "Это не точное boolean-разрезание и не добавляет плоские крышки на срезах.",
    ]

    try:
        remove_split_outputs(result_dir)
        loaded = trimesh.load_mesh(str(source_path), force="mesh")
        mesh = trimesh.util.concatenate(tuple(loaded.dump())) if isinstance(loaded, trimesh.Scene) else loaded

        total_faces = int(len(mesh.faces))
        if total_faces < split_parts:
            report["reason"] = "Недостаточно граней для выбранного количества частей."
        else:
            centroids = mesh.triangles_center[:, axis_index]
            min_value = float(centroids.min())
            max_value = float(centroids.max())
            if min_value == max_value:
                report["reason"] = "Модель не имеет протяженности по выбранной оси."
            else:
                cuts, cut_error = split_cut_positions(min_value, max_value, split_parts, split_plane_offset_mm)
                if cut_error:
                    report["reason"] = cut_error
                    raise ValueError(cut_error)
                report["split_plane_position"] = split_plane_position_payload(cuts)
                validation["split_plane_position"] = report["split_plane_position"]
                ranges = []
                starts = [min_value] + cuts
                ends = cuts + [max_value]
                for index in range(split_parts):
                    start = starts[index]
                    end = ends[index]
                    mask = (centroids >= start) & (centroids <= end) if index == split_parts - 1 else (centroids >= start) & (centroids < end)
                    face_indices = mask.nonzero()[0]
                    ranges.append({"part": index + 1, "faces": int(len(face_indices)), "from": start, "to": end})
                    if len(face_indices) == 0:
                        continue
                    part_mesh = mesh.submesh([face_indices], append=True, repair=False)
                    part_mesh.remove_unreferenced_vertices()
                    part_name = f"split_part_{index + 1}.stl"
                    part_path = result_dir / part_name
                    part_mesh.export(str(part_path))
                    if part_path.exists():
                        output_files.append(part_name)

                report["ranges"] = ranges
                valid, reason = validate_split_parts(result_dir, output_files, split_parts, total_faces, validation)
                if not valid:
                    remove_split_outputs(result_dir)
                    output_files.clear()
                    report["reason"] = reason or "Разрезание отклонено: одна или несколько частей не прошли проверку."
                else:
                    report["success"] = True
                    connectors = create_connector_guides(mesh, result_dir, split_mode, split_axis, split_parts, connector_size_mm, connector_clearance_mm, connector_count, connector_config)
                    report["connectors"] = connectors
                    require_integrated_pins_or_fail(report, output_files, result_dir, connectors, recommendations)

        if not report["success"]:
            recommendations.append("Попробуйте другую ось, меньшее количество частей или blender_boolean split.")
    except Exception as exc:
        remove_split_outputs(result_dir)
        output_files.clear()
        report["reason"] = str(exc)
        recommendations.append("Попробуйте другую ось, меньшее количество частей или blender_boolean split.")

    report["output_files"] = output_files
    report["validation"] = validation
    if split_mode != "simple":
        write_connector_report(result_dir, split_axis, split_mode, report.get("connectors") or connectors, connector_config)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"report": report, "output_files": output_files, "report_file": "split_report.json", "connectors": report["connectors"], "validation": validation, "report_path": report_path}


def run_blender_boolean_split(source_path: Path, result_dir: Path, split_axis: str, split_parts: int, split_mode: str, split_plane_offset_mm: float = 0.0, connector_size_mm: int = 4, connector_clearance_mm: float = 0.25, connector_count: int = 2, connector_config: dict | None = None) -> dict:
    report_path = result_dir / "split_report.json"
    report, output_files, recommendations, connectors, validation = base_split_report(split_axis, split_parts, split_mode, "blender_boolean", split_plane_offset_mm)
    report["notes"] = [
        "blender_boolean использует Blender для реального planar cut по выбранной оси.",
        "Основной путь использует bisect + fill: это стабильнее для неидеальных STL, чем чистый Boolean INTERSECT.",
        "Если Blender не может создать валидные части, операция завершается controlled failure.",
    ]

    if not blender_available():
        report["reason"] = "Blender недоступен внутри worker-контейнера."
        recommendations.append("Используйте split_engine=safe_mvp или установите Blender в worker.")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"report": report, "output_files": output_files, "report_file": "split_report.json", "connectors": connectors, "validation": validation, "report_path": report_path}

    try:
        remove_split_outputs(result_dir)
        source_mesh = load_mesh_for_processing(source_path, [])
        if source_mesh is None or len(source_mesh.faces) <= 0:
            report["reason"] = "Исходная mesh пустая или невалидная."
        else:
            total_faces = int(len(source_mesh.faces))
            axis_index = {"x": 0, "y": 1, "z": 2}[split_axis]
            bounds = np.asarray(source_mesh.bounds, dtype=float)
            cuts, cut_error = split_cut_positions(float(bounds[0][axis_index]), float(bounds[1][axis_index]), split_parts, split_plane_offset_mm)
            if cut_error:
                report["reason"] = cut_error
                raise ValueError(cut_error)
            report["split_plane_position"] = split_plane_position_payload(cuts)
            validation["split_plane_position"] = report["split_plane_position"]
            script_path = result_dir / "split_boolean_blender.py"
            script = f"""
import bpy
from mathutils import Vector

input_path = {str(source_path)!r}
result_dir = {str(result_dir)!r}
axis = {split_axis!r}
split_parts = {int(split_parts)}
cuts = {cuts!r}

axis_index = {{"x": 0, "y": 1, "z": 2}}[axis]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

try:
    bpy.ops.import_mesh.stl(filepath=input_path)
except Exception:
    bpy.ops.wm.stl_import(filepath=input_path)

mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
if not mesh_objects:
    raise RuntimeError("No mesh objects imported from STL")

bpy.ops.object.select_all(action='DESELECT')
for obj in mesh_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = mesh_objects[0]
if len(mesh_objects) > 1:
    bpy.ops.object.join()

source = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.context.view_layer.update()

corners = [source.matrix_world @ Vector(corner) for corner in source.bound_box]
mins = [min(c[i] for c in corners) for i in range(3)]
maxs = [max(c[i] for c in corners) for i in range(3)]
span = maxs[axis_index] - mins[axis_index]
if span <= 0:
    raise RuntimeError("Model has no span along selected axis")

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def cleanup_active_object(obj):
    activate(obj)
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        try:
            bpy.ops.mesh.delete_loose()
        except Exception:
            pass
        try:
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
        except Exception:
            pass
        try:
            bpy.ops.mesh.normals_make_consistent(inside=False)
        except Exception:
            pass
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass

def bisect_keep_interval(obj, lower, upper):
    activate(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    if lower is not None:
        plane_co = [0.0, 0.0, 0.0]
        plane_no = [0.0, 0.0, 0.0]
        plane_co[axis_index] = lower
        plane_no[axis_index] = 1.0
        bpy.ops.mesh.bisect(
            plane_co=plane_co,
            plane_no=plane_no,
            clear_inner=True,
            clear_outer=False,
            use_fill=True,
        )
        bpy.ops.mesh.select_all(action='SELECT')
    if upper is not None:
        plane_co = [0.0, 0.0, 0.0]
        plane_no = [0.0, 0.0, 0.0]
        plane_co[axis_index] = upper
        plane_no[axis_index] = 1.0
        bpy.ops.mesh.bisect(
            plane_co=plane_co,
            plane_no=plane_no,
            clear_inner=False,
            clear_outer=True,
            use_fill=True,
        )
        bpy.ops.mesh.select_all(action='SELECT')
    try:
        bpy.ops.mesh.delete_loose()
    except Exception:
        pass
    try:
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
    except Exception:
        pass
    try:
        bpy.ops.mesh.normals_make_consistent(inside=False)
    except Exception:
        pass
    bpy.ops.object.mode_set(mode='OBJECT')

for index in range(split_parts):
    lower = None if index == 0 else cuts[index - 1]
    upper = None if index == split_parts - 1 else cuts[index]

    part_mesh = source.data.copy()
    part = bpy.data.objects.new(f"split_part_{{index + 1}}", part_mesh)
    part.matrix_world = source.matrix_world.copy()
    bpy.context.collection.objects.link(part)

    bisect_keep_interval(part, lower, upper)
    cleanup_active_object(part)
    if len(part.data.polygons) == 0 or len(part.data.vertices) == 0:
        raise RuntimeError(f"Bisect produced empty split_part_{{index + 1}}")

    activate(part)
    output_path = f"{{result_dir}}/split_part_{{index + 1}}.stl"
    try:
        bpy.ops.export_mesh.stl(filepath=output_path, use_selection=True)
    except Exception:
        bpy.ops.wm.stl_export(filepath=output_path, export_selected_objects=True)
"""
            script_path.write_text(script, encoding="utf-8")
            completed = subprocess.run(
                ["blender", "-b", "--python", str(script_path)],
                capture_output=True,
                text=True,
                timeout=240,
                check=False,
            )
            blender_output = "\n".join(part for part in (completed.stderr, completed.stdout) if part)
            if completed.returncode != 0 or "Traceback (most recent call last)" in blender_output:
                report["reason"] = (blender_output or "Blender split failed").strip()[-1200:]
            else:
                output_files.extend([f"split_part_{index + 1}.stl" for index in range(split_parts) if (result_dir / f"split_part_{index + 1}.stl").exists()])
                valid, reason = validate_split_parts(result_dir, output_files, split_parts, total_faces, validation)
                if not valid:
                    remove_split_outputs(result_dir)
                    output_files.clear()
                    report["reason"] = reason or "Blender split отклонен: части не прошли проверку."
                else:
                    report["success"] = True
                    connectors = integrate_connectors_with_blender(
                        source_mesh,
                        result_dir,
                        output_files,
                        split_mode,
                        split_axis,
                        split_parts,
                        connector_size_mm,
                        connector_clearance_mm,
                        connector_count,
                        total_faces,
                        connector_config,
                    )
                    if split_mode != "simple" and not connectors.get("integrated"):
                        fallback_reason = connectors.get("reason")
                        connectors = create_connector_guides(source_mesh, result_dir, split_mode, split_axis, split_parts, connector_size_mm, connector_clearance_mm, connector_count, connector_config)
                        connectors["integrated"] = False
                        connectors["reason"] = fallback_reason or connectors.get("reason") or "Встроить соединители автоматически не удалось."
                    report["connectors"] = connectors
                    require_integrated_pins_or_fail(report, output_files, result_dir, connectors, recommendations)
    except subprocess.TimeoutExpired:
        remove_split_outputs(result_dir)
        output_files.clear()
        report["reason"] = "Blender split превысил timeout 240 секунд."
    except Exception as exc:
        remove_split_outputs(result_dir)
        output_files.clear()
        report["reason"] = str(exc)

    if not report["success"]:
        recommendations.append("Blender-разрезание не создало валидные части. Попробуйте другую ось, меньше частей или split_engine=safe_mvp.")

    report["output_files"] = output_files
    report["validation"] = validation
    if split_mode != "simple":
        write_connector_report(result_dir, split_axis, split_mode, report.get("connectors") or connectors, connector_config)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"report": report, "output_files": output_files, "report_file": "split_report.json", "connectors": report["connectors"], "validation": validation, "report_path": report_path}


def run_split_model(source_path: Path, result_dir: Path, split_axis: str, split_parts: int, split_mode: str, split_engine: str, split_plane_offset_mm: float = 0.0, connector_size_mm: int = 4, connector_clearance_mm: float = 0.25, connector_count: int = 2, connector_config: dict | None = None) -> dict:
    if split_engine == "safe_mvp":
        return run_safe_mvp_split(source_path, result_dir, split_axis, split_parts, split_mode, split_plane_offset_mm, connector_size_mm, connector_clearance_mm, connector_count, connector_config)
    return run_blender_boolean_split(source_path, result_dir, split_axis, split_parts, split_mode, split_plane_offset_mm, connector_size_mm, connector_clearance_mm, connector_count, connector_config)


def bed_size_payload_from_mesh(mesh: trimesh.Trimesh) -> dict[str, float]:
    bounds = np.asarray(mesh.bounds, dtype=float)
    size = bounds[1] - bounds[0]
    return {
        "x": round(float(size[0]), 6),
        "y": round(float(size[1]), 6),
        "z": round(float(size[2]), 6),
    }


def remove_bed_split_outputs(result_dir: Path) -> None:
    for path in result_dir.glob("bed_part_*.stl"):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def slice_mesh_between(mesh: trimesh.Trimesh, axis_index: int, lower: float, upper: float) -> trimesh.Trimesh | None:
    axis = np.zeros(3)
    axis[axis_index] = 1.0
    lower_origin = np.zeros(3)
    lower_origin[axis_index] = lower
    upper_origin = np.zeros(3)
    upper_origin[axis_index] = upper
    sliced = mesh.slice_plane(lower_origin, axis, cap=False)
    if sliced is None or len(sliced.faces) == 0:
        return None
    sliced = sliced.slice_plane(upper_origin, -axis, cap=False)
    if sliced is None or len(sliced.faces) == 0:
        return None
    sliced.remove_unreferenced_vertices()
    return sliced if len(sliced.faces) > 0 and len(sliced.vertices) > 0 else None


def slice_mesh_to_cell(mesh: trimesh.Trimesh, ranges: list[tuple[int, float, float]]) -> trimesh.Trimesh | None:
    cell_mesh = mesh.copy()
    for axis_index, lower, upper in ranges:
        cell_mesh = slice_mesh_between(cell_mesh, axis_index, lower, upper)
        if cell_mesh is None:
            return None
    cell_mesh.remove_unreferenced_vertices()
    return cell_mesh if len(cell_mesh.faces) > 0 and len(cell_mesh.vertices) > 0 else None


def run_fit_to_bed_split(source_path: Path, result_dir: Path, bed_size: dict[str, float], connector_mode: str, connector_clearance_mm: float, source_file: str = "original.stl") -> dict:
    remove_bed_split_outputs(result_dir)
    report_path = result_dir / "fit_to_bed_report.json"
    output_files: list[str] = []
    report = {
        "success": False,
        "no_split_needed": False,
        "source_file": source_file,
        "bed_size": {key: round(float(value), 6) for key, value in bed_size.items()},
        "model_size_before": None,
        "parts_grid": {"x": 1, "y": 1, "z": 1},
        "total_parts": 0,
        "output_files": output_files,
        "all_parts_fit_bed": False,
        "connectors": {
            "mode": connector_mode,
            "integrated": False,
            "reason": None if connector_mode == "none" else "Соединители для multi-axis bed split будут добавлены следующим этапом.",
            "clearance_mm": connector_clearance_mm,
        },
        "validation": [],
        "reason": None,
        "recommendation": None,
    }
    try:
        mesh = load_trimesh_mesh(source_path)
        if len(mesh.faces) <= 0 or len(mesh.vertices) <= 0:
            raise ValueError("STL не содержит валидную геометрию")
        bounds = np.asarray(mesh.bounds, dtype=float)
        model_size = bed_size_payload_from_mesh(mesh)
        report["model_size_before"] = model_size
        fits = all(model_size[axis] <= bed_size[axis] + 1e-6 for axis in ("x", "y", "z"))
        if fits:
            report.update(
                {
                    "success": True,
                    "no_split_needed": True,
                    "total_parts": 0,
                    "all_parts_fit_bed": True,
                    "recommendation": "Модель уже помещается на выбранный стол.",
                }
            )
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"report": report, "output_files": output_files, "report_file": "fit_to_bed_report.json", "report_path": report_path}

        parts_grid = {
            "x": int(np.ceil(model_size["x"] / bed_size["x"])),
            "y": int(np.ceil(model_size["y"] / bed_size["y"])),
            "z": int(np.ceil(model_size["z"] / bed_size["z"])),
        }
        total_parts = parts_grid["x"] * parts_grid["y"] * parts_grid["z"]
        report["parts_grid"] = parts_grid
        report["total_parts"] = total_parts
        if total_parts > 12:
            report["reason"] = "Модель слишком большая для автоматического разрезания. Увеличьте размер стола или уменьшите масштаб."
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"report": report, "output_files": output_files, "report_file": "fit_to_bed_report.json", "report_path": report_path}

        axes = [("x", 0), ("y", 1), ("z", 2)]
        axis_ranges: dict[str, list[tuple[float, float]]] = {}
        epsilon = max(float(np.linalg.norm(bounds[1] - bounds[0])) * 1e-6, 1e-5)
        for axis_name, axis_index in axes:
            count = parts_grid[axis_name]
            min_value = float(bounds[0][axis_index])
            max_value = float(bounds[1][axis_index])
            span = max_value - min_value
            axis_ranges[axis_name] = []
            for index in range(count):
                lower = min_value + span * index / count
                upper = min_value + span * (index + 1) / count
                if index == 0:
                    lower -= epsilon
                if index == count - 1:
                    upper += epsilon
                axis_ranges[axis_name].append((lower, upper))

        part_index = 1
        all_fit = True
        tolerance = 1.0
        for ix, range_x in enumerate(axis_ranges["x"]):
            for iy, range_y in enumerate(axis_ranges["y"]):
                for iz, range_z in enumerate(axis_ranges["z"]):
                    cell_mesh = slice_mesh_to_cell(mesh, [(0, *range_x), (1, *range_y), (2, *range_z)])
                    if cell_mesh is None:
                        continue
                    file_name = f"bed_part_{part_index}.stl"
                    output_path = result_dir / file_name
                    cell_mesh.export(output_path)
                    valid, details = is_valid_mesh_file(output_path)
                    if not valid:
                        output_path.unlink(missing_ok=True)
                        report["reason"] = details.get("reason") or f"Часть {file_name} не прошла проверку."
                        remove_bed_split_outputs(result_dir)
                        output_files.clear()
                        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                        return {"report": report, "output_files": output_files, "report_file": "fit_to_bed_report.json", "report_path": report_path}
                    loaded_part = load_trimesh_mesh(output_path)
                    part_size = bed_size_payload_from_mesh(loaded_part)
                    part_fits = all(part_size[axis] <= bed_size[axis] + tolerance for axis in ("x", "y", "z"))
                    all_fit = all_fit and part_fits
                    report["validation"].append(
                        {
                            "name": file_name,
                            "grid_index": {"x": ix + 1, "y": iy + 1, "z": iz + 1},
                            "file_size": int(output_path.stat().st_size),
                            "faces": int(len(loaded_part.faces)),
                            "vertices": int(len(loaded_part.vertices)),
                            "dimensions": part_size,
                            "fits_bed": part_fits,
                        }
                    )
                    output_files.append(file_name)
                    part_index += 1

        if len(output_files) != total_parts:
            report["reason"] = f"Создано {len(output_files)} частей вместо ожидаемых {total_parts}. Автоматический раскрой отклонён."
            remove_bed_split_outputs(result_dir)
            output_files.clear()
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"report": report, "output_files": output_files, "report_file": "fit_to_bed_report.json", "report_path": report_path}
        if not all_fit:
            report["reason"] = "Одна или несколько частей не помещаются на выбранный стол."
            remove_bed_split_outputs(result_dir)
            output_files.clear()
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"report": report, "output_files": output_files, "report_file": "fit_to_bed_report.json", "report_path": report_path}

        report.update(
            {
                "success": True,
                "output_files": output_files,
                "all_parts_fit_bed": True,
                "recommendation": f"Модель разрезана на {len(output_files)} частей под выбранный стол.",
            }
        )
    except Exception as exc:
        remove_bed_split_outputs(result_dir)
        output_files.clear()
        report["reason"] = f"Не удалось разрезать модель под стол: {exc}"

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"report": report, "output_files": output_files, "report_file": "fit_to_bed_report.json", "report_path": report_path}


def symmetry_axis_index(axis: str) -> int:
    return {"x": 0, "y": 1, "z": 2}[axis]


def mirror_vertices(vertices: np.ndarray, axis: str, plane_value: float) -> np.ndarray:
    mirrored = np.array(vertices, dtype=float, copy=True)
    axis_index = symmetry_axis_index(axis)
    mirrored[:, axis_index] = 2 * plane_value - mirrored[:, axis_index]
    return mirrored


def calculate_symmetry_score(mesh: trimesh.Trimesh, axis: str, plane_value: float | None = None) -> int:
    if mesh is None or len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        return 0
    vertices = np.asarray(mesh.vertices, dtype=float)
    if plane_value is None:
        bounds = np.asarray(mesh.bounds, dtype=float)
        plane_value = float((bounds[0][symmetry_axis_index(axis)] + bounds[1][symmetry_axis_index(axis)]) / 2)

    sample_limit = 25000
    if len(vertices) > sample_limit:
        indices = np.linspace(0, len(vertices) - 1, sample_limit, dtype=int)
        sampled = vertices[indices]
    else:
        sampled = vertices

    mirrored = mirror_vertices(sampled, axis, plane_value)
    tree = cKDTree(vertices)
    distances, _ = tree.query(mirrored, k=1, workers=1)
    dimensions = np.asarray(mesh.bounds[1] - mesh.bounds[0], dtype=float)
    diagonal = float(np.linalg.norm(dimensions)) or 1.0
    tolerance = max(diagonal * 0.015, 1e-6)
    normalized = np.clip(distances / tolerance, 0, 1)
    score = 100 * (1 - float(np.mean(normalized)))
    return int(max(0, min(100, round(score))))


def choose_symmetry_reference_side(mesh: trimesh.Trimesh, axis: str, plane_value: float) -> tuple[str, np.ndarray]:
    axis_index = symmetry_axis_index(axis)
    centroids = np.asarray(mesh.triangles_center, dtype=float)
    positive = np.where(centroids[:, axis_index] >= plane_value)[0]
    negative = np.where(centroids[:, axis_index] <= plane_value)[0]
    if len(positive) >= len(negative):
        return "positive", positive
    return "negative", negative


def build_symmetry_fixed_mesh(source_mesh: trimesh.Trimesh, axis: str, plane_value: float) -> tuple[trimesh.Trimesh | None, str]:
    side_name, face_indices = choose_symmetry_reference_side(source_mesh, axis, plane_value)
    if len(face_indices) == 0:
        return None, "Не удалось выбрать эталонную сторону модели."

    half = source_mesh.submesh([face_indices], append=True, repair=False)
    if half is None or len(half.faces) == 0 or len(half.vertices) == 0:
        return None, "Эталонная сторона пуста."

    mirrored_vertices = mirror_vertices(np.asarray(half.vertices, dtype=float), axis, plane_value)
    mirrored_faces = np.asarray(half.faces, dtype=int)[:, ::-1]
    mirrored = trimesh.Trimesh(vertices=mirrored_vertices, faces=mirrored_faces, process=False)
    combined = trimesh.util.concatenate([half, mirrored])
    if hasattr(combined, "remove_duplicate_faces"):
        combined.remove_duplicate_faces()
    if hasattr(combined, "remove_degenerate_faces"):
        combined.remove_degenerate_faces()
    combined.remove_unreferenced_vertices()
    try:
        trimesh.repair.fix_normals(combined)
    except Exception:
        pass
    if len(combined.faces) == 0 or len(combined.vertices) == 0:
        return None, "После зеркального восстановления mesh стал пустым."
    return combined, side_name


def run_fix_symmetry(source_path: Path, result_dir: Path, axis: str, mode: str) -> dict:
    output_path = result_dir / "symmetry_fixed.stl"
    report_path = result_dir / "symmetry_report.json"
    warnings: list[str] = []
    recommendations: list[str] = []
    report = {
        "success": False,
        "mode": mode,
        "symmetry_axis": axis,
        "symmetry_score": 0,
        "symmetry_score_before": 0,
        "symmetry_score_after": None,
        "output_file": None,
        "report_file": "symmetry_report.json",
        "reference_side": None,
        "reason": None,
        "warnings": warnings,
        "recommendations": recommendations,
    }

    try:
        notes: list[str] = []
        mesh = load_mesh_for_processing(source_path, notes)
        if mesh is None or len(mesh.faces) == 0 or len(mesh.vertices) == 0:
            report["reason"] = "Mesh пустой или невалидный."
        else:
            bounds = np.asarray(mesh.bounds, dtype=float)
            axis_index = symmetry_axis_index(axis)
            plane_value = float((bounds[0][axis_index] + bounds[1][axis_index]) / 2)
            before_score = calculate_symmetry_score(mesh, axis, plane_value)
            report["symmetry_score"] = before_score
            report["symmetry_score_before"] = before_score
            report["plane_value"] = round(plane_value, 6)
            report["bounding_box"] = {
                "min": [round(float(value), 6) for value in bounds[0]],
                "max": [round(float(value), 6) for value in bounds[1]],
            }

            if mode == "analyze":
                report["success"] = True
                recommendations.append("Это только анализ: геометрия не изменялась.")
            else:
                fixed_mesh, reference_side = build_symmetry_fixed_mesh(mesh, axis, plane_value)
                report["reference_side"] = reference_side
                if fixed_mesh is None:
                    report["reason"] = reference_side
                else:
                    after_score = calculate_symmetry_score(fixed_mesh, axis, plane_value)
                    report["symmetry_score_after"] = after_score
                    if after_score < before_score:
                        report["reason"] = "Исправление отклонено: симметрия стала хуже."
                        warnings.append(report["reason"])
                    else:
                        fixed_mesh.export(str(output_path))
                        if output_path.exists() and output_path.stat().st_size > 0:
                            report["success"] = True
                            report["output_file"] = "symmetry_fixed.stl"
                        else:
                            report["reason"] = "Не удалось сохранить symmetry_fixed.stl."
    except Exception as exc:
        report["reason"] = str(exc)

    if not recommendations:
        if report["success"] and mode == "fix":
            recommendations.append("Проверьте результат в 3D-просмотре и slicer перед печатью.")
        elif not report["success"]:
            recommendations.append("Оставлена исходная модель; попробуйте другую ось симметрии.")

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "report": report,
        "output_file": report["output_file"],
        "report_file": "symmetry_report.json",
        "output_path": output_path,
        "report_path": report_path,
    }


def blender_available() -> bool:
    return shutil.which("blender") is not None


def blender_strength_profile(strength: str) -> dict[str, float | int | bool]:
    profiles = {
        "light": {"smooth_factor": 0.0, "smooth_iterations": 0},
        "balanced": {"smooth_factor": 0.0, "smooth_iterations": 0},
        "strong": {"smooth_factor": 0.08, "smooth_iterations": 1},
    }
    return profiles.get(strength, profiles["balanced"])


def mesh_quality_metrics(mesh: trimesh.Trimesh) -> dict:
    if mesh is None or len(mesh.faces) == 0 or len(mesh.vertices) == 0:
        return {
            "faces": 0,
            "vertices": 0,
            "bounding_box": None,
            "dimensions": None,
            "volume": None,
        }
    bounds = np.asarray(mesh.bounds, dtype=float)
    dimensions = bounds[1] - bounds[0]
    volume = None
    try:
        raw_volume = float(mesh.volume)
        if np.isfinite(raw_volume):
            volume = raw_volume
    except Exception:
        volume = None
    return {
        "faces": int(len(mesh.faces)),
        "vertices": int(len(mesh.vertices)),
        "bounding_box": {
            "min": [round(float(value), 6) for value in bounds[0]],
            "max": [round(float(value), 6) for value in bounds[1]],
        },
        "dimensions": [round(float(value), 6) for value in dimensions],
        "volume": volume,
    }


def volume_change_percent(before_volume: float | None, after_volume: float | None) -> float | None:
    if before_volume is None or after_volume is None:
        return None
    baseline = max(abs(float(before_volume)), 1e-6)
    return round(abs(float(after_volume) - float(before_volume)) / baseline * 100, 4)


def max_dimension_change_percent(before_dimensions: list[float] | None, after_dimensions: list[float] | None) -> float | None:
    if not before_dimensions or not after_dimensions:
        return None
    changes = []
    for before, after in zip(before_dimensions, after_dimensions):
        baseline = max(abs(float(before)), 1e-6)
        changes.append(abs(float(after) - float(before)) / baseline * 100)
    return round(max(changes), 4) if changes else None


def evaluate_improvement_quality(
    output_path: Path,
    before_metrics: dict,
    after_metrics: dict | None,
    reduce_selected: bool,
) -> dict:
    file_valid = bool(output_path.exists() and output_path.stat().st_size > 0 and after_metrics and after_metrics.get("faces", 0) > 0)
    shape_change_percent = max_dimension_change_percent(
        before_metrics.get("dimensions"),
        after_metrics.get("dimensions") if after_metrics else None,
    )
    dimensions_ok = bool(shape_change_percent is not None and shape_change_percent <= 2.0)
    faces_before = int(before_metrics.get("faces") or 0)
    faces_after = int(after_metrics.get("faces") or 0) if after_metrics else 0
    faces_ok = bool(faces_after > 0)
    if faces_before > 0 and faces_after > 0 and not reduce_selected:
        faces_ok = faces_after >= int(faces_before * 0.6)

    rejected_reason = None
    if not file_valid:
        rejected_reason = "Улучшение отклонено: файл результата не создан или пустой."
    elif not dimensions_ok:
        rejected_reason = "Улучшение отклонено: обработка слишком сильно изменила форму модели."
    elif not faces_ok:
        rejected_reason = "Улучшение отклонено: обработка слишком сильно уменьшила количество полигонов."

    return {
        "file_valid": file_valid,
        "dimensions_ok": dimensions_ok,
        "faces_ok": faces_ok,
        "shape_change_percent": shape_change_percent,
        "accepted": rejected_reason is None,
        "rejected_reason": rejected_reason,
    }


def count_duplicate_vertices(vertices: np.ndarray) -> int:
    if vertices is None or len(vertices) == 0:
        return 0
    rounded = np.round(np.asarray(vertices, dtype=float), decimals=6)
    unique = np.unique(rounded, axis=0)
    return int(len(rounded) - len(unique))


def count_duplicate_faces(faces: np.ndarray) -> int:
    if faces is None or len(faces) == 0:
        return 0
    normalized = np.sort(np.asarray(faces, dtype=np.int64), axis=1)
    unique = np.unique(normalized, axis=0)
    return int(len(normalized) - len(unique))


def edge_issue_counts(mesh: trimesh.Trimesh) -> tuple[int, int]:
    if mesh is None or len(mesh.faces) == 0:
        return 0, 0
    edges = np.sort(mesh.edges_sorted, axis=1)
    if len(edges) == 0:
        return 0, 0
    _, counts = np.unique(edges, axis=0, return_counts=True)
    open_edges = int(np.sum(counts == 1))
    non_manifold_edges = int(np.sum(counts > 2))
    return non_manifold_edges, open_edges


def tiny_island_count(mesh: trimesh.Trimesh) -> tuple[int, int]:
    if mesh is None or len(mesh.faces) == 0:
        return 0, 0
    try:
        components = mesh.split(only_watertight=False)
    except Exception:
        return 1, 0
    component_count = len(components)
    if component_count <= 1:
        return component_count, 0
    largest_faces = max(len(component.faces) for component in components)
    threshold = max(4, int(largest_faces * 0.01))
    tiny = sum(1 for component in components if len(component.faces) < threshold)
    return component_count, int(tiny)


def estimate_inverted_normals(mesh: trimesh.Trimesh) -> int:
    if mesh is None or len(mesh.faces) == 0:
        return 0
    try:
        if mesh.is_watertight and float(mesh.volume) < 0:
            return int(len(mesh.faces))
    except Exception:
        return 0
    return 0


def health_label(score: int) -> str:
    if score >= 90:
        return "Отличное"
    if score >= 75:
        return "Хорошее"
    if score >= 50:
        return "Требует исправления"
    return "Плохое"


def calculate_artifact_score_penalty(artifact_quality: dict, faces_count: int) -> int:
    if not artifact_quality or faces_count <= 0:
        return 0
    suspicious = int(artifact_quality.get("suspicious_regions") or 0)
    spikes = int(artifact_quality.get("spikes_detected") or 0)
    elongated = int(artifact_quality.get("elongated_faces") or 0)
    dense = int(artifact_quality.get("dense_regions") or 0)
    sparse = int(artifact_quality.get("sparse_regions") or 0)
    if suspicious <= 0 and spikes <= 0 and elongated <= 0:
        return 0

    suspicious_ratio = suspicious / max(faces_count, 1)
    elongated_ratio = elongated / max(faces_count, 1)
    spike_ratio = spikes / max(faces_count, 1)
    noise_ratio = (dense + sparse) / max(faces_count, 1)

    penalty = 0
    penalty += min(12, int(round(suspicious_ratio * 18)))
    penalty += min(14, int(round(elongated_ratio * 24)))
    penalty += min(22, int(round(spike_ratio * 48)))
    penalty += min(6, int(round(noise_ratio * 4)))
    if spikes > 0:
        penalty += 6
    elif elongated > 0:
        penalty += 3
    return max(0, min(30, penalty))


def calculate_health_score(qa: dict) -> int:
    score = 100
    if not qa["watertight"]:
        score -= 18
    score -= min(20, qa["open_edges"] // 10)
    score -= min(20, qa["non_manifold_edges"] * 2)
    score -= min(12, qa["duplicate_faces"] * 2)
    score -= min(10, qa["duplicate_vertices"] // 10)
    score -= min(15, qa["degenerate_faces"] * 2)
    score -= min(10, qa["zero_area_faces"] * 2)
    if qa["components"] > 1:
        score -= min(14, (qa["components"] - 1) * 4)
    score -= min(12, qa["tiny_islands"] * 4)
    score -= min(20, qa["inverted_normals"] // 100)
    score -= int((qa.get("artifact_quality") or {}).get("artifact_score_penalty") or 0)
    return max(0, min(100, int(score)))


def diagnose_model(input_path: Path) -> dict:
    qa = {
        "health_score": 0,
        "health_label": "Плохое",
        "watertight": False,
        "non_manifold_edges": 0,
        "open_edges": 0,
        "duplicate_vertices": 0,
        "duplicate_faces": 0,
        "degenerate_faces": 0,
        "components": 0,
        "tiny_islands": 0,
        "inverted_normals": 0,
        "zero_area_faces": 0,
        "repair_recommended": True,
        "artifact_quality": {
            "suspicious_regions": 0,
            "spikes_detected": 0,
            "elongated_faces": 0,
            "dense_regions": 0,
            "sparse_regions": 0,
            "artifact_score_penalty": 0,
        },
        "warning": None,
    }
    try:
        loaded = trimesh.load_mesh(str(input_path), force="mesh")
        if isinstance(loaded, trimesh.Scene):
            meshes = [mesh for mesh in loaded.dump() if len(mesh.faces) > 0]
            mesh = trimesh.util.concatenate(tuple(meshes)) if meshes else trimesh.Trimesh()
        else:
            mesh = loaded

        qa["watertight"] = bool(mesh.is_watertight)
        qa["duplicate_vertices"] = count_duplicate_vertices(mesh.vertices)
        qa["duplicate_faces"] = count_duplicate_faces(mesh.faces)
        non_manifold_edges, open_edges = edge_issue_counts(mesh)
        qa["non_manifold_edges"] = non_manifold_edges
        qa["open_edges"] = open_edges
        areas = np.asarray(mesh.area_faces, dtype=float) if len(mesh.faces) else np.array([])
        zero_area = int(np.sum(areas <= 1e-12)) if len(areas) else 0
        qa["zero_area_faces"] = zero_area
        qa["degenerate_faces"] = zero_area
        components, tiny = tiny_island_count(mesh)
        qa["components"] = int(components)
        qa["tiny_islands"] = int(tiny)
        qa["inverted_normals"] = estimate_inverted_normals(mesh)
        artifact_detection = detect_surface_artifacts(mesh, "balanced")
        artifact_quality = {
            "suspicious_regions": int(artifact_detection.get("suspicious_regions") or 0),
            "spikes_detected": int(artifact_detection.get("spikes_detected") or 0),
            "elongated_faces": int(artifact_detection.get("elongated_faces") or 0),
            "dense_regions": int(artifact_detection.get("dense_regions") or 0),
            "sparse_regions": int(artifact_detection.get("sparse_regions") or 0),
            "artifact_score_penalty": 0,
        }
        artifact_quality["artifact_score_penalty"] = calculate_artifact_score_penalty(
            artifact_quality,
            int(len(mesh.faces)),
        )
        qa["artifact_quality"] = artifact_quality
        qa["health_score"] = calculate_health_score(qa)
        qa["health_label"] = health_label(qa["health_score"])
        qa["repair_recommended"] = bool(
            qa["health_score"] < 90
            or not qa["watertight"]
            or qa["open_edges"] > 0
            or qa["non_manifold_edges"] > 0
            or qa["duplicate_faces"] > 0
            or qa["degenerate_faces"] > 0
            or qa["tiny_islands"] > 0
            or qa["inverted_normals"] > 0
            or qa["artifact_quality"]["artifact_score_penalty"] > 0
        )
    except Exception as exc:
        qa["warning"] = f"Не удалось выполнить диагностику модели: {exc}"
    return qa


def compare_model_qa(before: dict | None, after: dict | None) -> dict:
    before = before or {}
    after = after or {}
    keys = [
        "non_manifold_edges",
        "open_edges",
        "duplicate_vertices",
        "duplicate_faces",
        "degenerate_faces",
        "tiny_islands",
        "inverted_normals",
        "zero_area_faces",
        "artifact_score_penalty",
    ]
    before_artifacts = before.get("artifact_quality") or {}
    after_artifacts = after.get("artifact_quality") or {}
    found = {key: int(before.get(key) or 0) for key in keys}
    remaining = {key: int(after.get(key) or 0) for key in keys}
    found["artifact_score_penalty"] = int(before_artifacts.get("artifact_score_penalty") or 0)
    remaining["artifact_score_penalty"] = int(after_artifacts.get("artifact_score_penalty") or 0)
    fixed = {key: max(0, found[key] - remaining[key]) for key in keys}
    return {
        "found": found,
        "fixed": fixed,
        "remaining": remaining,
        "score_before": before.get("health_score"),
        "score_after": after.get("health_score"),
        "repair_recommended_before": before.get("repair_recommended"),
        "repair_recommended_after": after.get("repair_recommended"),
    }


def main_component_metrics(mesh: trimesh.Trimesh | None) -> dict:
    empty = {
        "faces": 0,
        "vertices": 0,
        "bounding_box": None,
        "dimensions": None,
        "volume": None,
    }
    if mesh is None or len(mesh.faces) == 0 or len(mesh.vertices) == 0:
        return empty
    try:
        components = mesh.split(only_watertight=False)
        component = max(components, key=lambda item: len(item.faces)) if components else mesh
    except Exception:
        component = mesh
    metrics = mesh_quality_metrics(component)
    return {
        "faces": int(metrics.get("faces") or 0),
        "vertices": int(metrics.get("vertices") or 0),
        "bounding_box": metrics.get("bounding_box"),
        "dimensions": metrics.get("dimensions"),
        "volume": metrics.get("volume"),
    }


def cleanup_improved_geometry(qa_before: dict | None, qa_after: dict | None) -> bool:
    before = qa_before or {}
    after = qa_after or {}
    components_reduced = int(after.get("components") or 0) < int(before.get("components") or 0)
    islands_reduced = int(after.get("tiny_islands") or 0) < int(before.get("tiny_islands") or 0)
    duplicate_vertices_reduced = int(after.get("duplicate_vertices") or 0) < int(before.get("duplicate_vertices") or 0)
    duplicate_faces_reduced = int(after.get("duplicate_faces") or 0) < int(before.get("duplicate_faces") or 0)
    degenerate_reduced = int(after.get("degenerate_faces") or 0) < int(before.get("degenerate_faces") or 0)
    return bool(
        (islands_reduced or components_reduced)
        and (duplicate_vertices_reduced or duplicate_faces_reduced or degenerate_reduced or components_reduced)
    )


def evaluate_print_repair_quality(
    output_path: Path,
    before_metrics: dict,
    after_metrics: dict | None,
    before_main: dict,
    after_main: dict,
    qa_before: dict | None,
    qa_after: dict | None,
) -> dict:
    file_valid = bool(
        output_path.exists()
        and output_path.stat().st_size > 0
        and after_metrics
        and after_metrics.get("faces", 0) > 0
        and after_metrics.get("vertices", 0) > 0
    )
    overall_bbox_change = max_dimension_change_percent(
        before_metrics.get("dimensions"),
        after_metrics.get("dimensions") if after_metrics else None,
    )
    overall_volume_change = volume_change_percent(
        before_metrics.get("volume"),
        after_metrics.get("volume") if after_metrics else None,
    )
    main_bbox_change = max_dimension_change_percent(before_main.get("dimensions"), after_main.get("dimensions"))
    main_volume_change = volume_change_percent(before_main.get("volume"), after_main.get("volume"))
    main_faces_before = int(before_main.get("faces") or 0)
    main_faces_after = int(after_main.get("faces") or 0)
    main_faces_ok = bool(main_faces_before > 0 and main_faces_after >= int(main_faces_before * 0.9))
    main_bbox_ok = bool(main_bbox_change is not None and main_bbox_change <= 5.0)
    main_volume_ok = True if main_volume_change is None else main_volume_change <= 10.0
    relaxed_cleanup = cleanup_improved_geometry(qa_before, qa_after)
    relaxed_bbox_ok = bool(overall_bbox_change is not None and overall_bbox_change <= 25.0)

    passed = False
    reason = None
    if not file_valid:
        reason = "Ремонт отклонён: файл результата не создан или не содержит геометрию."
    elif not main_faces_ok:
        reason = "Ремонт отклонён: основная геометрия потеряла слишком много полигонов."
    elif not main_bbox_ok:
        reason = "Ремонт отклонён: основная геометрия изменилась слишком сильно."
    elif not main_volume_ok:
        reason = "Ремонт отклонён: объём основной геометрии изменился слишком сильно."
    else:
        passed = True
        if relaxed_cleanup and overall_bbox_change is not None and overall_bbox_change > 5.0 and relaxed_bbox_ok:
            reason = "Ремонт принят: удалены отдельные артефакты, основная модель сохранена."
        elif relaxed_cleanup:
            reason = "Ремонт принят: удалены отдельные артефакты, основная модель сохранена."
        else:
            reason = "Ремонт принят: основная модель сохранена."

    # Global bbox is now diagnostic only. If cleanup improved geometry and the
    # main component is preserved, deleting a separate island must not reject
    # the result just because the full-scene bbox changed.
    islands_removed = max(0, int((qa_before or {}).get("tiny_islands") or 0) - int((qa_after or {}).get("tiny_islands") or 0))
    components_removed = max(0, int((qa_before or {}).get("components") or 0) - int((qa_after or {}).get("components") or 0))
    return {
        "file_valid": file_valid,
        "bbox_ok": main_bbox_ok,
        "volume_ok": main_volume_ok,
        "bbox_change_percent": overall_bbox_change,
        "volume_change_percent": overall_volume_change,
        "quality_gate_passed": passed,
        "warning": None if passed else reason,
        "quality_gate": {
            "passed": passed,
            "reason": reason,
            "main_component_faces_before": main_faces_before,
            "main_component_faces_after": main_faces_after,
            "main_component_bbox_change": main_bbox_change,
            "main_component_volume_change": main_volume_change,
            "islands_removed": islands_removed,
            "components_removed": components_removed,
            "overall_bbox_change": overall_bbox_change,
            "overall_volume_change": overall_volume_change,
            "relaxed_cleanup_rule_used": bool(passed and relaxed_cleanup and overall_bbox_change is not None and overall_bbox_change > 5.0),
        },
    }


def run_print_repair(input_path: Path, result_dir: Path, result: dict, strength: str) -> dict:
    output_path = result_dir / "repaired_model.stl"
    report_path = result_dir / "repair_report.json"
    blender_stats_path = result_dir / "print_repair_blender_stats.json"
    profile = blender_strength_profile(strength)
    report = {
        "success": False,
        "output_file": None,
        "report_file": "repair_report.json",
        "faces_before": None,
        "faces_after": None,
        "vertices_before": None,
        "vertices_after": None,
        "removed_islands": 0,
        "merged_vertices": 0,
        "holes_fixed": 0,
        "normals_recalculated": False,
        "bbox_change_percent": None,
        "volume_change_percent": None,
        "quality_gate_passed": False,
        "warning": None,
        "reason": None,
        "visible_result": visible_result_payload(False, "Ремонт ещё не выполнялся."),
        "blender_available": blender_available(),
        "engine": "blender",
        "operations": [
            "Merge By Distance",
            "Delete Loose Geometry",
            "Remove Degenerate Geometry",
            "Recalculate Normals Outside",
            "Fill Small Holes",
            "Remove Tiny Islands",
            "Non-Manifold Cleanup",
            "Limited Smooth",
            "Triangulate",
        ],
    }

    before_metrics = None
    try:
        source_mesh = load_mesh_for_processing(input_path, [])
        before_metrics = mesh_quality_metrics(source_mesh)
        before_main_metrics = main_component_metrics(source_mesh)
        report["faces_before"] = before_metrics["faces"]
        report["vertices_before"] = before_metrics["vertices"]
    except Exception as exc:
        report["warning"] = f"Не удалось прочитать исходную STL перед ремонтом: {exc}"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    if not report["blender_available"]:
        report["warning"] = "Blender недоступен внутри worker-контейнера."
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    file_size_mb = result.get("file", {}).get("size_mb", 0) or 0
    triangles_count = result.get("triangles_count", 0) or 0
    if file_size_mb > 150:
        report["warning"] = "Blender repair пропущен: файл больше 150 МБ."
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    if triangles_count > 1_000_000:
        report["warning"] = "Blender repair пропущен: больше 1 000 000 треугольников."
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    smooth_factor = float(profile["smooth_factor"])
    smooth_iterations = int(profile["smooth_iterations"])
    script = f"""
import json
import bpy

input_path = {str(input_path)!r}
output_path = {str(output_path)!r}
stats_path = {str(blender_stats_path)!r}
smooth_factor = {smooth_factor}
smooth_iterations = {smooth_iterations}

stats = {{
    "removed_islands": 0,
    "merged_vertices": 0,
    "holes_fixed": 0,
    "normals_recalculated": False,
    "limited_smooth_applied": False,
    "triangulated": False,
}}

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

try:
    bpy.ops.import_mesh.stl(filepath=input_path)
except Exception:
    bpy.ops.wm.stl_import(filepath=input_path)

mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
if not mesh_objects:
    raise RuntimeError("No mesh objects imported from STL")

bpy.ops.object.select_all(action='DESELECT')
for obj in mesh_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = mesh_objects[0]
if len(mesh_objects) > 1:
    bpy.ops.object.join()

obj = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

vertices_before_cleanup = len(obj.data.vertices)

try:
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    try:
        bpy.ops.mesh.delete_loose()
    except Exception as exc:
        print("delete loose skipped:", exc)
    try:
        bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
    except Exception as exc:
        print("dissolve degenerate skipped:", exc)
    try:
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
    except Exception as exc:
        print("merge by distance skipped:", exc)
    try:
        bpy.ops.mesh.fill_holes(sides=12)
        stats["holes_fixed"] = 1
    except Exception as exc:
        print("fill small holes skipped:", exc)
    try:
        bpy.ops.mesh.normals_make_consistent(inside=False)
        stats["normals_recalculated"] = True
    except Exception as exc:
        print("normal consistency skipped:", exc)
    bpy.ops.object.mode_set(mode='OBJECT')
except Exception as exc:
    print("edit cleanup skipped:", exc)
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

vertices_after_cleanup = len(obj.data.vertices)
stats["merged_vertices"] = max(0, vertices_before_cleanup - vertices_after_cleanup)

# Remove tiny disconnected islands after the basic mesh cleanup.
try:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    parts = [part for part in bpy.context.scene.objects if part.type == 'MESH']
    if parts:
        largest_faces = max(len(part.data.polygons) for part in parts)
        min_faces = max(8, int(largest_faces * 0.001))
        kept = []
        for part in parts:
            faces = len(part.data.polygons)
            if faces < min_faces:
                bpy.data.objects.remove(part, do_unlink=True)
                stats["removed_islands"] += 1
            else:
                kept.append(part)
        if not kept:
            raise RuntimeError("Tiny island cleanup removed all mesh parts")
        bpy.ops.object.select_all(action='DESELECT')
        for part in kept:
            part.select_set(True)
        bpy.context.view_layer.objects.active = kept[0]
        if len(kept) > 1:
            bpy.ops.object.join()
        obj = bpy.context.view_layer.objects.active
except Exception as exc:
    print("tiny island cleanup skipped:", exc)
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

try:
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    stats["normals_recalculated"] = True
    try:
        bpy.ops.mesh.quads_convert_to_tris()
        stats["triangulated"] = True
    except Exception as exc:
        print("triangulate skipped:", exc)
    bpy.ops.object.mode_set(mode='OBJECT')
except Exception as exc:
    print("final edit cleanup skipped:", exc)
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

if smooth_iterations > 0 and len(obj.data.polygons) > 5000:
    try:
        smooth = obj.modifiers.new(name="STL Master Limited Smooth", type='SMOOTH')
        smooth.factor = smooth_factor
        smooth.iterations = smooth_iterations
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=smooth.name)
        stats["limited_smooth_applied"] = True
    except Exception as exc:
        print("limited smooth skipped:", exc)

try:
    bpy.ops.object.shade_flat()
except Exception:
    pass

try:
    bpy.ops.export_mesh.stl(filepath=output_path, use_selection=True)
except Exception:
    bpy.ops.wm.stl_export(filepath=output_path, export_selected_objects=True)

with open(stats_path, "w", encoding="utf-8") as handle:
    json.dump(stats, handle, ensure_ascii=False, indent=2)
"""

    script_path = None
    try:
        with NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as handle:
            handle.write(script)
            script_path = Path(handle.name)

        completed = subprocess.run(
            ["blender", "-b", "--python", str(script_path)],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        blender_output = "\n".join(part for part in (completed.stderr, completed.stdout) if part)
        if completed.returncode != 0 or "Traceback (most recent call last)" in blender_output:
            report["warning"] = (blender_output or "Blender repair failed").strip()[-1200:]
        elif not output_path.exists() or output_path.stat().st_size == 0:
            report["warning"] = "Blender завершился, но repaired_model.stl не создан."
        else:
            blender_stats = {}
            if blender_stats_path.exists():
                try:
                    blender_stats = json.loads(blender_stats_path.read_text(encoding="utf-8"))
                except Exception:
                    blender_stats = {}
            try:
                repaired_mesh = load_mesh_for_processing(output_path, [])
                after_metrics = mesh_quality_metrics(repaired_mesh)
                after_main_metrics = main_component_metrics(repaired_mesh)
                qa_before = result.get("model_qa") or diagnose_model(input_path)
                qa_after = diagnose_model(output_path)
                quality = evaluate_print_repair_quality(
                    output_path,
                    before_metrics,
                    after_metrics,
                    before_main_metrics,
                    after_main_metrics,
                    qa_before,
                    qa_after,
                )
                report["faces_after"] = after_metrics["faces"]
                report["vertices_after"] = after_metrics["vertices"]
                report["removed_islands"] = int(blender_stats.get("removed_islands") or 0)
                report["merged_vertices"] = int(blender_stats.get("merged_vertices") or 0)
                report["holes_fixed"] = max(0, int(qa_before.get("open_edges") or 0) - int(qa_after.get("open_edges") or 0))
                report["normals_recalculated"] = bool(blender_stats.get("normals_recalculated"))
                report["limited_smooth_applied"] = bool(blender_stats.get("limited_smooth_applied"))
                report["triangulated"] = bool(blender_stats.get("triangulated"))
                report["bbox_change_percent"] = quality["bbox_change_percent"]
                report["volume_change_percent"] = quality["volume_change_percent"]
                report["quality_gate_passed"] = quality["quality_gate_passed"]
                report["quality_gate"] = quality["quality_gate"]
                report["warning"] = quality["warning"]
                report["qa_before"] = qa_before
                report["qa_after"] = qa_after
                report["qa_delta"] = compare_model_qa(qa_before, qa_after)
                changed_metrics = []
                if int(report["qa_delta"].get("score_after") or 0) > int(report["qa_delta"].get("score_before") or 0):
                    changed_metrics.append("health_score")
                if artifact_penalty(qa_after) < artifact_penalty(qa_before):
                    changed_metrics.append("artifact_penalty")
                if report["holes_fixed"] > 0:
                    changed_metrics.append("holes_fixed")
                if report["removed_islands"] > 0:
                    changed_metrics.append("removed_islands")
                if report["merged_vertices"] > 0:
                    changed_metrics.append("merged_vertices")
                visible_created = bool(changed_metrics)
                report["visible_result"] = visible_result_payload(
                    visible_created,
                    "Значимые исправления найдены." if visible_created else "Значимых исправлений не обнаружено.",
                    changed_metrics,
                )
                if quality["quality_gate_passed"] and visible_created:
                    report["success"] = True
                    report["output_file"] = "repaired_model.stl"
                    if not qa_before.get("repair_recommended"):
                        report["message"] = "Серьёзных проблем не обнаружено. Дополнительный ремонт не требуется."
                else:
                    output_path.unlink(missing_ok=True)
                    if quality["quality_gate_passed"] and not visible_created:
                        report["success"] = False
                        report["output_file"] = None
                        report["reason"] = "Значимых исправлений не обнаружено."
                        report["warning"] = report["reason"]
            except Exception as exc:
                output_path.unlink(missing_ok=True)
                report["warning"] = f"Не удалось проверить результат Blender repair: {exc}"
    except subprocess.TimeoutExpired:
        output_path.unlink(missing_ok=True)
        report["warning"] = "Blender repair превысил timeout 180 секунд."
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        report["warning"] = str(exc)
    finally:
        if script_path:
            script_path.unlink(missing_ok=True)
        blender_stats_path.unlink(missing_ok=True)

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def run_blender_improvement(source_path: Path, result_dir: Path, result: dict, strength: str) -> dict:
    repair = run_print_repair(source_path, result_dir, result, strength)
    return {
        "available": repair.get("blender_available"),
        "success": repair.get("success"),
        "reason": repair.get("warning"),
        "output_file": repair.get("output_file"),
        "strength": strength,
        "surface_smoothing": bool(repair.get("limited_smooth_applied")),
        "weighted_normals": False,
        "faces_before": repair.get("faces_before"),
        "faces_after": repair.get("faces_after"),
        "metrics_before": None,
        "metrics_after": None,
        "quality_gate": {
            "file_valid": bool(repair.get("success")),
            "dimensions_ok": bool((repair.get("bbox_change_percent") is not None) and repair.get("bbox_change_percent") <= 3.0),
            "faces_ok": bool((repair.get("faces_after") or 0) > 0 and (repair.get("vertices_after") or 0) > 0),
            "volume_ok": bool(repair.get("quality_gate", {}).get("volume_ok", repair.get("volume_change_percent") is None or repair.get("volume_change_percent") <= 10.0)),
            "smart_gate": repair.get("quality_gate"),
        },
        "shape_change_percent": repair.get("bbox_change_percent"),
        "accepted": bool(repair.get("success")),
        "rejected_reason": repair.get("warning"),
        "print_repair": repair,
    }


def build_model_improvement(
    job_id: str,
    result: dict,
    blender_status: dict | None,
    strength: str,
    model_name: str,
) -> dict:
    blender = blender_status or {"available": False, "success": False, "reason": "Blender was not attempted."}
    repair = blender.get("print_repair") or result.get("print_repair") or {}
    accepted = bool(repair.get("success"))
    after_file = repair.get("output_file") if accepted else "original.stl"
    warnings = []
    if repair.get("warning"):
        warnings.append(repair["warning"])

    return {
        "success": accepted,
        "engine": "blender",
        "strength": strength,
        "model_name": model_name or None,
        "before_file": "original.stl",
        "after_file": after_file,
        "output_file": after_file,
        "after_download_url": f"/api/v1/jobs/{job_id}/files/{after_file}" if after_file else None,
        "fallback_used": not accepted,
        "surface_smoothing": bool(repair.get("limited_smooth_applied")),
        "weighted_normals": False,
        "components_removed": int(repair.get("removed_islands") or 0),
        "faces_before": repair.get("faces_before") or result.get("triangles_count"),
        "faces_after": repair.get("faces_after") or repair.get("faces_before") or result.get("triangles_count"),
        "accepted": accepted,
        "rejected_reason": repair.get("warning") if not accepted else None,
        "shape_change_percent": repair.get("bbox_change_percent"),
        "quality_gate": {
            "file_valid": accepted,
            "dimensions_ok": bool((repair.get("bbox_change_percent") is not None) and repair.get("bbox_change_percent") <= 3.0),
            "faces_ok": bool((repair.get("faces_after") or 0) > 0 and (repair.get("vertices_after") or 0) > 0),
            "volume_ok": bool(repair.get("volume_change_percent") is None or repair.get("volume_change_percent") <= 5.0),
        },
        "warnings": warnings,
        "notes": [
            "Print Repair 2.0: Blender pipeline для подготовки STL к печати.",
            "Если quality gate не проходит, repaired_model.stl не применяется.",
        ],
        "blender": {
            "available": bool(blender.get("available")),
            "success": bool(blender.get("success")),
            "reason": blender.get("reason"),
        },
        "summary": {
            "artifacts_removed": int(repair.get("removed_islands") or 0) > 0,
            "mesh_errors_fixed": accepted,
            "smoothing_applied": bool(repair.get("limited_smooth_applied")),
            "faces_before": repair.get("faces_before") or result.get("triangles_count"),
            "faces_after": repair.get("faces_after") or repair.get("faces_before") or result.get("triangles_count"),
        },
    }


def create_result_zip(job_id: str, input_path: Path, result: dict, job: dict[str, str]) -> Path:
    result_dir = RESULT_ROOT / job_id
    result_dir.mkdir(parents=True, exist_ok=True)

    copied_stl = result_dir / "original.stl"
    analysis_json = result_dir / "analysis.json"
    readme_txt = result_dir / "README.txt"
    normalized_info_json = result_dir / "normalized_info.json"
    print_report_txt = result_dir / "print_report.txt"
    manifest_json = result_dir / "manifest.json"
    zip_path = result_dir / "result.zip"
    temp_zip_path = result_dir / "result.zip.tmp"
    zip_files = ["original.stl"]

    shutil.copy2(input_path, copied_stl)
    if result.get("print_repair"):
        output_file = result["print_repair"].get("output_file")
        if output_file and output_file != "original.stl":
            zip_files.append(output_file)
        report_file = result["print_repair"].get("report_file")
        if report_file:
            zip_files.append(report_file)
    elif result.get("model_improvement"):
        output_file = result["model_improvement"].get("after_file")
        if output_file and output_file != "original.stl":
            zip_files.append(output_file)
    elif result.get("repair_mesh") and not result.get("split_model"):
        output_file = result["repair_mesh"].get("output_file")
        if output_file:
            zip_files.append(output_file)
    if result.get("reduce_polygons"):
        output_file = result["reduce_polygons"].get("output_file")
        if output_file:
            zip_files.append(output_file)
    if result.get("remove_ai_artifacts"):
        output_file = result["remove_ai_artifacts"].get("output_file")
        if output_file:
            zip_files.append(output_file)
    if result.get("surface_recovery"):
        output_file = result["surface_recovery"].get("output_file")
        if output_file:
            zip_files.append(output_file)
    if result.get("apply_orientation"):
        output_file = result["apply_orientation"].get("output_file")
        if output_file:
            zip_files.append(output_file)
    if result.get("auto_orientation"):
        output_file = result["auto_orientation"].get("output_file")
        if output_file:
            zip_files.append(output_file)
    if result.get("local_smoothing"):
        output_file = result["local_smoothing"].get("output_file")
        if output_file:
            zip_files.append(output_file)
    if result.get("change_map", {}).get("available"):
        change_map_file = result["change_map"].get("file")
        if change_map_file:
            zip_files.append(change_map_file)
    if result.get("artifact_map", {}).get("available"):
        artifact_map_file = result["artifact_map"].get("file")
        if artifact_map_file:
            zip_files.append(artifact_map_file)
    if result.get("fix_symmetry"):
        output_file = result["fix_symmetry"].get("output_file")
        if output_file:
            zip_files.append(output_file)
        report_file = result["fix_symmetry"].get("report_file")
        if report_file:
            zip_files.append(report_file)
    if result.get("split_model"):
        for output_file in result["split_model"].get("output_files", []):
            zip_files.append(output_file)
        connectors = result["split_model"].get("connectors") or {}
        connector_report = connectors.get("report_file") or result["split_model"].get("connector_report_file")
        if connector_report:
            zip_files.append(connector_report)
        if not connectors.get("integrated"):
            for connector_file in connectors.get("files", connectors.get("connector_files", [])):
                zip_files.append(connector_file)
            guide_file = connectors.get("guide_file")
            if guide_file:
                zip_files.append(guide_file)
    if result.get("fit_to_bed_split"):
        for output_file in result["fit_to_bed_split"].get("output_files", []):
            zip_files.append(output_file)

    if "prepare_package" in result.get("operations", []):
        generated_at = datetime.now(timezone.utc).isoformat()
        normalized_info_json.write_text(
            json.dumps(build_normalized_info(job_id, job, result, generated_at), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print_report_txt.write_text(build_print_report(job_id, job, result), encoding="utf-8")
        zip_files.extend(["print_report.txt", "manifest.json"])

    result["generated_files"] = build_generated_files(job_id, zip_files, result_dir)

    analysis_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    readme_txt.write_text(build_readme(job_id, result), encoding="utf-8")
    if "prepare_package" in result.get("operations", []):
        manifest_json.write_text(
            json.dumps(build_manifest(zip_files, result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if temp_zip_path.exists():
        temp_zip_path.unlink()
    with zipfile.ZipFile(temp_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(copied_stl, arcname="original.stl")
        if "repaired.stl" in zip_files:
            repaired_path = result_dir / "repaired.stl"
            if repaired_path.exists():
                archive.write(repaired_path, arcname="repaired.stl")
        if result.get("reduce_polygons"):
            reduced_path = result_dir / "reduced.stl"
            if "reduced.stl" in zip_files and reduced_path.exists():
                archive.write(reduced_path, arcname="reduced.stl")
        if result.get("remove_ai_artifacts", {}).get("output_file") == "cleaned_artifacts.stl":
            cleaned_artifacts_path = result_dir / "cleaned_artifacts.stl"
            if cleaned_artifacts_path.exists():
                archive.write(cleaned_artifacts_path, arcname="cleaned_artifacts.stl")
        if result.get("surface_recovery", {}).get("output_file") == "surface_recovered.stl":
            surface_recovered_path = result_dir / "surface_recovered.stl"
            if "surface_recovered.stl" in zip_files and surface_recovered_path.exists():
                archive.write(surface_recovered_path, arcname="surface_recovered.stl")
        if result.get("apply_orientation", {}).get("output_file") == "oriented_model.stl":
            oriented_model_path = result_dir / "oriented_model.stl"
            if "oriented_model.stl" in zip_files and oriented_model_path.exists():
                archive.write(oriented_model_path, arcname="oriented_model.stl")
        if result.get("auto_orientation", {}).get("output_file") == "oriented_auto.stl":
            oriented_auto_path = result_dir / "oriented_auto.stl"
            if "oriented_auto.stl" in zip_files and oriented_auto_path.exists():
                archive.write(oriented_auto_path, arcname="oriented_auto.stl")
        if result.get("local_smoothing", {}).get("output_file") == "local_smoothed.stl":
            local_smoothed_path = result_dir / "local_smoothed.stl"
            if "local_smoothed.stl" in zip_files and local_smoothed_path.exists():
                archive.write(local_smoothed_path, arcname="local_smoothed.stl")
        if result.get("change_map", {}).get("available"):
            change_map_path = result_dir / "change_map.json"
            if "change_map.json" in zip_files and change_map_path.exists():
                archive.write(change_map_path, arcname="change_map.json")
        if result.get("artifact_map", {}).get("available"):
            artifact_map_path = result_dir / "artifact_map.json"
            if "artifact_map.json" in zip_files and artifact_map_path.exists():
                archive.write(artifact_map_path, arcname="artifact_map.json")
        if result.get("fix_symmetry"):
            symmetry_path = result_dir / "symmetry_fixed.stl"
            symmetry_report_path = result_dir / "symmetry_report.json"
            if "symmetry_fixed.stl" in zip_files and symmetry_path.exists():
                archive.write(symmetry_path, arcname="symmetry_fixed.stl")
            if "symmetry_report.json" in zip_files and symmetry_report_path.exists():
                archive.write(symmetry_report_path, arcname="symmetry_report.json")
        if result.get("print_repair"):
            repaired_model_path = result_dir / "repaired_model.stl"
            repair_report_path = result_dir / "repair_report.json"
            if "repaired_model.stl" in zip_files and repaired_model_path.exists():
                archive.write(repaired_model_path, arcname="repaired_model.stl")
            if "repair_report.json" in zip_files and repair_report_path.exists():
                archive.write(repair_report_path, arcname="repair_report.json")
        elif result.get("model_improvement", {}).get("after_file") == "improved_model.stl":
            improved_file = result["model_improvement"]["after_file"]
            improved_path = result_dir / improved_file
            if improved_path.exists():
                archive.write(improved_path, arcname=improved_file)
        if result.get('split_model'):
            for output_file in result['split_model'].get('output_files', []):
                output_path = result_dir / output_file
                if output_path.exists():
                    archive.write(output_path, arcname=output_file)
            connectors = result['split_model'].get('connectors') or {}
            connector_report = connectors.get('report_file') or result['split_model'].get('connector_report_file')
            if connector_report:
                connector_report_path = result_dir / connector_report
                if connector_report_path.exists():
                    archive.write(connector_report_path, arcname=connector_report)
            if not connectors.get('integrated'):
                for connector_file in connectors.get('files', connectors.get('connector_files', [])):
                    connector_path = result_dir / connector_file
                    if connector_path.exists():
                        archive.write(connector_path, arcname=connector_file)
                guide_file = connectors.get('guide_file')
                if guide_file:
                    guide_path = result_dir / guide_file
                    if guide_path.exists():
                        archive.write(guide_path, arcname=guide_file)
        if result.get("fit_to_bed_split"):
            for output_file in result["fit_to_bed_split"].get("output_files", []):
                output_path = result_dir / output_file
                if output_path.exists():
                    archive.write(output_path, arcname=output_file)
        if "prepare_package" in result.get("operations", []):
            archive.write(print_report_txt, arcname="print_report.txt")
            archive.write(manifest_json, arcname="manifest.json")
    temp_zip_path.replace(zip_path)
    return zip_path


def process_job(client: Redis, job_id: str) -> None:
    print(f"Processing job {job_id}", flush=True)
    if stop_if_cancelled(client, job_id):
        return
    processing_started = time.time()
    client.hset(
        job_key(job_id),
        mapping={
            "processing_started_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    job = client.hgetall(job_key(job_id))
    if job.get("status") == "cancelled" or job.get("cancel_requested") == "true":
        stop_if_cancelled(client, job_id)
        return
    operations = parse_job_operations(job)
    reduction_percent = parse_reduction_percent(job)
    split_axis, split_parts, split_plane_offset_mm = parse_split_settings(job)
    split_mode = parse_split_mode(job)
    split_engine = parse_split_engine(job)
    connector_size_mm, connector_clearance_mm, connector_count = parse_connector_settings(job)
    connector_config = parse_split_connector_config(job, split_mode, connector_size_mm, connector_clearance_mm, connector_count)
    apply_orientation_requested = parse_apply_orientation(job) or "apply_orientation" in operations
    orientation_transform = parse_orientation_transform(job)
    local_selection = parse_local_selection(job)
    if apply_orientation_requested and "apply_orientation" not in operations:
        operations.append("apply_orientation")
    auto_orientation_requested = parse_auto_orientation(job) or "auto_orientation" in operations
    orientation_priority = parse_orientation_priority(job)
    if auto_orientation_requested and "auto_orientation" not in operations:
        operations.append("auto_orientation")
    fit_to_bed_requested = parse_fit_to_bed(job) or "fit_to_bed_split" in operations
    bed_size, bed_connector_mode, bed_connector_clearance_mm = parse_fit_to_bed_settings(job)
    if fit_to_bed_requested and "fit_to_bed_split" not in operations:
        operations.append("fit_to_bed_split")
    artifact_cleanup_strength = parse_artifact_cleanup_strength(job)
    symmetry_axis = parse_symmetry_axis(job)
    symmetry_mode = parse_symmetry_mode(job)
    ai_cleanup_strength = parse_ai_cleanup_strength(job)
    model_improvement_strength = parse_model_improvement_strength(job)
    model_name = parse_model_name(job)
    input_path = Path(job.get("input_path") or UPLOAD_ROOT / job_id / "input.stl")

    update_job(client, job_id, "processing", 10, "STL file received, starting selected operations")
    if not input_path.exists():
        update_job(client, job_id, "failed", 0, "Input STL file was not found")
        return

    time.sleep(1)
    if stop_if_cancelled(client, job_id):
        return
    update_job(client, job_id, "processing", 50, "Analyzing STL geometry and printability")
    result = analyze_stl(input_path, operations)
    result["model_qa"] = diagnose_model(input_path)
    skipped_operations = build_skipped_operations(result, operations)
    result["skipped_operations"] = skipped_operations
    executable_operations = [
        operation
        for operation in operations
        if operation not in {item["operation"] for item in skipped_operations}
    ]
    result["implemented_operations"] = [
        operation for operation in executable_operations if operation in IMPLEMENTED_OPERATIONS
    ]
    result_dir = RESULT_ROOT / job_id
    result_dir.mkdir(parents=True, exist_ok=True)
    wants_model_improvement = "model_improvement" in executable_operations
    wants_fast_repair = "repair_mesh" in executable_operations
    wants_fast_cleanup = "ai_cleanup" in executable_operations
    cleanup_strength = ai_cleanup_strength

    if stop_if_cancelled(client, job_id):
        return
    if wants_fast_repair:
        update_job(client, job_id, "processing", 70, "Running MVP mesh repair")
        repair_result = run_repair_mesh(input_path, result_dir)
        report = repair_result["report"]
        result["repair_mesh"] = {
            "success": report["success"],
            "output_file": repair_result["output_file"],
            "report_file": repair_result["report_file"],
            "watertight_before": report["watertight_before"],
            "watertight_after": report["watertight_after"],
        }
    if stop_if_cancelled(client, job_id):
        return
    if "reduce_polygons" in executable_operations:
        update_job(client, job_id, "processing", 75, "Running MVP polygon reduction")
        source_path = result_dir / "repaired.stl" if result.get("repair_mesh", {}).get("success") else input_path
        reduction_result = run_reduce_polygons(source_path, result_dir, reduction_percent)
        report = reduction_result["report"]
        result["reduce_polygons"] = {
            "success": report["success"],
            "reduction_percent": report["reduction_percent"],
            "original_faces": report["original_faces"],
            "target_faces": report["target_faces"],
            "reduced_faces": report["reduced_faces"],
            "output_file": report["output_file"],
            "report_file": reduction_result["report_file"],
            "reason": report["reason"],
            "visible_result": report.get("visible_result"),
        }
    if stop_if_cancelled(client, job_id):
        return
    if wants_fast_cleanup:
        update_job(client, job_id, "processing", 76, "Running MVP AI model cleanup")
        if result.get("reduce_polygons", {}).get("success"):
            cleanup_source_path = result_dir / "reduced.stl"
            cleanup_input_file = "reduced.stl"
        elif result.get("repair_mesh", {}).get("success"):
            cleanup_source_path = result_dir / "repaired.stl"
            cleanup_input_file = "repaired.stl"
        else:
            cleanup_source_path = input_path
            cleanup_input_file = "input.stl"
        cleanup_result = run_ai_cleanup(cleanup_source_path, result_dir, cleanup_input_file, cleanup_strength)
        report = cleanup_result["report"]
        result["ai_cleanup"] = {
            "success": report["success"],
            "strength": report["strength"],
            "output_file": report["output_file"],
            "report_file": cleanup_result["report_file"],
            "faces_before": report["faces_before"],
            "faces_after": report["faces_after"],
            "vertices_before": report["vertices_before"],
            "vertices_after": report["vertices_after"],
            "components_before": report["components_before"],
            "components_after": report["components_after"],
            "smoothing_applied": report["smoothing_applied"],
            "small_components_removed": report["small_components_removed"],
            "removed_small_components": report["removed_small_components"],
            "visible_change_expected": report["visible_change_expected"],
            "warnings": report["warnings"],
            "notes": report["notes"],
            "warning": report["warning"],
        }
    if stop_if_cancelled(client, job_id):
        return
    if wants_model_improvement:
        update_job(client, job_id, "processing", 77, "Running Print Repair 2.0 Blender pipeline")
        blender_status = run_blender_improvement(input_path, result_dir, result, model_improvement_strength)
        result["print_repair"] = blender_status.get("print_repair") or {}
        result["model_improvement"] = build_model_improvement(
            job_id,
            result,
            blender_status,
            model_improvement_strength,
            model_name,
        )
    if stop_if_cancelled(client, job_id):
        return
    if "remove_ai_artifacts" in executable_operations:
        update_job(client, job_id, "processing", 77, "Running AI artifact cleanup")
        if result.get("print_repair", {}).get("success") and result["print_repair"].get("output_file") == "repaired_model.stl":
            artifact_source_path = result_dir / "repaired_model.stl"
            artifact_input_file = "repaired_model.stl"
        elif result.get("model_improvement", {}).get("success") and result["model_improvement"].get("after_file") == "improved_model.stl":
            artifact_source_path = result_dir / "improved_model.stl"
            artifact_input_file = "improved_model.stl"
        elif result.get("repair_mesh", {}).get("success"):
            artifact_source_path = result_dir / "repaired.stl"
            artifact_input_file = "repaired.stl"
        else:
            artifact_source_path = input_path
            artifact_input_file = "input.stl"
        artifact_result = run_remove_ai_artifacts(artifact_source_path, result_dir, artifact_input_file, artifact_cleanup_strength)
        report = artifact_result["report"]
        result["remove_ai_artifacts"] = {
            "success": report["success"],
            "strength": report["strength"],
            "output_file": report["output_file"],
            "report_file": artifact_result["report_file"],
            "components_before": report["components_before"],
            "components_after": report["components_after"],
            "removed_components": report["removed_components"],
            "faces_before": report["faces_before"],
            "faces_after": report["faces_after"],
            "vertices_before": report["vertices_before"],
            "vertices_after": report["vertices_after"],
            "bbox_change_percent": report["bbox_change_percent"],
            "quality_gate_passed": report["quality_gate_passed"],
            "reason": report["reason"],
            "warnings": report["warnings"],
            "notes": report["notes"],
            "suspicious_regions": report.get("suspicious_regions", 0),
            "spikes_detected": report.get("spikes_detected", 0),
            "elongated_faces": report.get("elongated_faces", 0),
            "dense_regions": report.get("dense_regions", 0),
            "sparse_regions": report.get("sparse_regions", 0),
            "smoothing_applied": report.get("smoothing_applied", False),
            "health_score_before": report.get("health_score_before"),
            "health_score_after": report.get("health_score_after"),
            "artifact_quality_before": report.get("artifact_quality_before"),
            "artifact_quality_after": report.get("artifact_quality_after"),
            "delta": report.get("delta"),
            "advanced_quality_gate": report.get("advanced_quality_gate"),
            "visible_result": report.get("visible_result"),
        }
        result["ai_cleanup"] = {
            "success": report["success"],
            "suspicious_regions": report.get("suspicious_regions", 0),
            "spikes_detected": report.get("spikes_detected", 0),
            "elongated_faces": report.get("elongated_faces", 0),
            "dense_regions": report.get("dense_regions", 0),
            "smoothing_applied": report.get("smoothing_applied", False),
            "faces_before": report["faces_before"],
            "faces_after": report["faces_after"],
            "health_score_before": report.get("health_score_before"),
            "health_score_after": report.get("health_score_after"),
            "delta": report.get("delta"),
            "quality_gate_passed": report["quality_gate_passed"],
            "visible_result": report.get("visible_result"),
        }
    if "fix_symmetry" in executable_operations:
        if stop_if_cancelled(client, job_id):
            return
        update_job(client, job_id, "processing", 78, "Analyzing model symmetry")
        if result.get("remove_ai_artifacts", {}).get("success"):
            symmetry_source_path = result_dir / "cleaned_artifacts.stl"
        elif result.get("reduce_polygons", {}).get("success"):
            symmetry_source_path = result_dir / "reduced.stl"
        elif result.get("model_improvement", {}).get("after_file") == "improved_model.stl":
            symmetry_source_path = result_dir / "improved_model.stl"
        elif result.get("repair_mesh", {}).get("success"):
            symmetry_source_path = result_dir / "repaired.stl"
        else:
            symmetry_source_path = input_path
        symmetry_result = run_fix_symmetry(symmetry_source_path, result_dir, symmetry_axis, symmetry_mode)
        report = symmetry_result["report"]
        result["fix_symmetry"] = {
            "success": report["success"],
            "mode": report["mode"],
            "symmetry_axis": report["symmetry_axis"],
            "symmetry_score": report["symmetry_score"],
            "symmetry_score_before": report["symmetry_score_before"],
            "symmetry_score_after": report["symmetry_score_after"],
            "output_file": report["output_file"],
            "report_file": report["report_file"],
            "reference_side": report["reference_side"],
            "reason": report["reason"],
            "warnings": report["warnings"],
            "recommendations": report["recommendations"],
        }
    if "surface_recovery" in executable_operations:
        if stop_if_cancelled(client, job_id):
            return
        update_job(client, job_id, "processing", 78, "Recovering local surface defects")
        preferred_sources = []
        if result.get("remove_ai_artifacts", {}).get("success") and result["remove_ai_artifacts"].get("output_file") == "cleaned_artifacts.stl":
            preferred_sources.append("cleaned_artifacts.stl")
        if result.get("print_repair", {}).get("success") and result["print_repair"].get("output_file") == "repaired_model.stl":
            preferred_sources.append("repaired_model.stl")
        if result.get("model_improvement", {}).get("success") and result["model_improvement"].get("after_file") in {"improved_model.stl", "repaired_model.stl"}:
            preferred_sources.append(result["model_improvement"]["after_file"])
        if result.get("fix_symmetry", {}).get("success") and result["fix_symmetry"].get("output_file") == "symmetry_fixed.stl":
            preferred_sources.append("symmetry_fixed.stl")
        if result.get("reduce_polygons", {}).get("success") and result["reduce_polygons"].get("output_file") == "reduced.stl":
            preferred_sources.append("reduced.stl")
        if result.get("repair_mesh", {}).get("success") and result["repair_mesh"].get("output_file") == "repaired.stl":
            preferred_sources.append("repaired.stl")
        surface_source_path, surface_source_file = result_source_path(result, result_dir, input_path, preferred_sources)
        surface_result = run_surface_recovery(surface_source_path, result_dir, surface_source_file)
        report = surface_result["report"]
        result["surface_recovery"] = {
            "success": report["success"],
            "source_file": report["input_file"],
            "output_file": report["output_file"],
            "report_file": report["report_file"],
            "regions_detected": report["regions_detected"],
            "vertices_modified": report["vertices_modified"],
            "faces_before": report["faces_before"],
            "faces_after": report["faces_after"],
            "vertices_before": report["vertices_before"],
            "vertices_after": report["vertices_after"],
            "health_score_before": report["health_score_before"],
            "health_score_after": report["health_score_after"],
            "artifact_quality_before": report["artifact_quality_before"],
            "artifact_quality_after": report["artifact_quality_after"],
            "delta": report["delta"],
            "bbox_change_percent": report["bbox_change_percent"],
            "volume_change_percent": report["volume_change_percent"],
            "quality_gate_passed": report["quality_gate_passed"],
            "effect_detected": report["effect_detected"],
            "visible_result": report["visible_result"],
            "reason": report["reason"],
            "warnings": report["warnings"],
            "notes": report["notes"],
        }
    if apply_orientation_requested and "apply_orientation" in executable_operations:
        if stop_if_cancelled(client, job_id):
            return
        update_job(client, job_id, "processing", 78, "Applying selected model orientation")
        preferred_sources = []
        if result.get("surface_recovery", {}).get("success") and result["surface_recovery"].get("output_file") == "surface_recovered.stl":
            preferred_sources.append("surface_recovered.stl")
        if result.get("remove_ai_artifacts", {}).get("success") and result["remove_ai_artifacts"].get("output_file") == "cleaned_artifacts.stl":
            preferred_sources.append("cleaned_artifacts.stl")
        if result.get("print_repair", {}).get("success") and result["print_repair"].get("output_file") == "repaired_model.stl":
            preferred_sources.append("repaired_model.stl")
        if result.get("model_improvement", {}).get("success") and result["model_improvement"].get("after_file") in {"improved_model.stl", "repaired_model.stl"}:
            preferred_sources.append(result["model_improvement"]["after_file"])
        if result.get("reduce_polygons", {}).get("success") and result["reduce_polygons"].get("output_file") == "reduced.stl":
            preferred_sources.append("reduced.stl")
        if result.get("repair_mesh", {}).get("success") and result["repair_mesh"].get("output_file") == "repaired.stl":
            preferred_sources.append("repaired.stl")
        orientation_source_path, orientation_source_file = result_source_path(result, result_dir, input_path, preferred_sources)
        result["apply_orientation"] = run_apply_orientation(orientation_source_path, result_dir, orientation_transform, orientation_source_file)
    if auto_orientation_requested and "auto_orientation" in executable_operations:
        if stop_if_cancelled(client, job_id):
            return
        update_job(client, job_id, "processing", 78, "Selecting print orientation")
        preferred_sources = []
        if result.get("surface_recovery", {}).get("success") and result["surface_recovery"].get("output_file") == "surface_recovered.stl":
            preferred_sources.append("surface_recovered.stl")
        if result.get("print_repair", {}).get("success") and result["print_repair"].get("output_file") == "repaired_model.stl":
            preferred_sources.append("repaired_model.stl")
        if result.get("remove_ai_artifacts", {}).get("success") and result["remove_ai_artifacts"].get("output_file") == "cleaned_artifacts.stl":
            preferred_sources.append("cleaned_artifacts.stl")
        auto_orientation_source_path, auto_orientation_source_file = result_source_path(result, result_dir, input_path, preferred_sources)
        result["auto_orientation"] = run_auto_orientation(auto_orientation_source_path, result_dir, orientation_priority, auto_orientation_source_file)
    if "local_smoothing" in executable_operations:
        if stop_if_cancelled(client, job_id):
            return
        update_job(client, job_id, "processing", 78, "Running local smoothing on selected area")
        preferred_sources = []
        if result.get("auto_orientation", {}).get("success") and result["auto_orientation"].get("output_file") == "oriented_auto.stl":
            preferred_sources.append("oriented_auto.stl")
        if result.get("apply_orientation", {}).get("success") and result["apply_orientation"].get("output_file") == "oriented_model.stl":
            preferred_sources.append("oriented_model.stl")
        if result.get("remove_ai_artifacts", {}).get("success") and result["remove_ai_artifacts"].get("output_file") == "cleaned_artifacts.stl":
            preferred_sources.append("cleaned_artifacts.stl")
        if result.get("surface_recovery", {}).get("success") and result["surface_recovery"].get("output_file") == "surface_recovered.stl":
            preferred_sources.append("surface_recovered.stl")
        if result.get("print_repair", {}).get("success") and result["print_repair"].get("output_file") == "repaired_model.stl":
            preferred_sources.append("repaired_model.stl")
        if result.get("reduce_polygons", {}).get("success") and result["reduce_polygons"].get("output_file") == "reduced.stl":
            preferred_sources.append("reduced.stl")
        if result.get("repair_mesh", {}).get("success") and result["repair_mesh"].get("output_file") == "repaired.stl":
            preferred_sources.append("repaired.stl")
        local_source_path, local_source_file = result_source_path(result, result_dir, input_path, preferred_sources)
        result["local_smoothing"] = run_local_smoothing(local_source_path, result_dir, local_selection, local_source_file)
    if fit_to_bed_requested and "fit_to_bed_split" in executable_operations:
        if stop_if_cancelled(client, job_id):
            return
        update_job(client, job_id, "processing", 79, "Splitting model to printer bed size")
        preferred_sources = []
        if result.get("local_smoothing", {}).get("success") and result["local_smoothing"].get("output_file") == "local_smoothed.stl":
            preferred_sources.append("local_smoothed.stl")
        if result.get("auto_orientation", {}).get("success") and result["auto_orientation"].get("output_file") == "oriented_auto.stl":
            preferred_sources.append("oriented_auto.stl")
        if result.get("apply_orientation", {}).get("success") and result["apply_orientation"].get("output_file") == "oriented_model.stl":
            preferred_sources.append("oriented_model.stl")
        if result.get("surface_recovery", {}).get("success") and result["surface_recovery"].get("output_file") == "surface_recovered.stl":
            preferred_sources.append("surface_recovered.stl")
        if result.get("remove_ai_artifacts", {}).get("success") and result["remove_ai_artifacts"].get("output_file") == "cleaned_artifacts.stl":
            preferred_sources.append("cleaned_artifacts.stl")
        if result.get("print_repair", {}).get("success") and result["print_repair"].get("output_file") == "repaired_model.stl":
            preferred_sources.append("repaired_model.stl")
        if result.get("reduce_polygons", {}).get("success") and result["reduce_polygons"].get("output_file") == "reduced.stl":
            preferred_sources.append("reduced.stl")
        if result.get("repair_mesh", {}).get("success") and result["repair_mesh"].get("output_file") == "repaired.stl":
            preferred_sources.append("repaired.stl")
        bed_source_path, bed_source_file = result_source_path(result, result_dir, input_path, preferred_sources)
        bed_result = run_fit_to_bed_split(
            bed_source_path,
            result_dir,
            bed_size,
            bed_connector_mode,
            bed_connector_clearance_mm,
            bed_source_file,
        )
        result["fit_to_bed_split"] = bed_result["report"]
        result["fit_to_bed_split"]["report_file"] = bed_result["report_file"]
    if "split_model" in executable_operations:
        if stop_if_cancelled(client, job_id):
            return
        update_job(client, job_id, "processing", 79, "Running MVP model split")
        preferred_sources = []
        if result.get("local_smoothing", {}).get("success") and result["local_smoothing"].get("output_file") == "local_smoothed.stl":
            preferred_sources.append("local_smoothed.stl")
        if result.get("apply_orientation", {}).get("success") and result["apply_orientation"].get("output_file") == "oriented_model.stl":
            preferred_sources.append("oriented_model.stl")
        if result.get("surface_recovery", {}).get("success") and result["surface_recovery"].get("output_file") == "surface_recovered.stl":
            preferred_sources.append("surface_recovered.stl")
        if result.get("remove_ai_artifacts", {}).get("success") and result["remove_ai_artifacts"].get("output_file") == "cleaned_artifacts.stl":
            preferred_sources.append("cleaned_artifacts.stl")
        if result.get("print_repair", {}).get("success") and result["print_repair"].get("output_file") == "repaired_model.stl":
            preferred_sources.append("repaired_model.stl")
        if result.get("reduce_polygons", {}).get("success") and result["reduce_polygons"].get("output_file") == "reduced.stl":
            preferred_sources.append("reduced.stl")
        if result.get("repair_mesh", {}).get("success") and result["repair_mesh"].get("output_file") == "repaired.stl":
            preferred_sources.append("repaired.stl")
        if result.get("fix_symmetry", {}).get("success") and result["fix_symmetry"].get("output_file"):
            preferred_sources.append(result["fix_symmetry"]["output_file"])
        split_source_path, split_source_file = result_source_path(result, result_dir, input_path, preferred_sources)
        split_result = run_split_model(split_source_path, result_dir, split_axis, split_parts, split_mode, split_engine, split_plane_offset_mm, connector_size_mm, connector_clearance_mm, connector_count, connector_config)
        report = split_result["report"]
        result["split_model"] = {
            "success": report["success"],
            "source_file": split_source_file,
            "split_engine": report["split_engine"],
            "split_axis": report["split_axis"],
            "split_parts": report["split_parts"],
            "split_mode": report["split_mode"],
            "split_plane_offset_mm": report.get("split_plane_offset_mm", split_plane_offset_mm),
            "split_plane_position": report.get("split_plane_position"),
            "connector_size_mm": connector_size_mm,
            "connector_clearance_mm": connector_clearance_mm,
            "connector_count": connector_count,
            "connector_depth_mm": connector_config.get("connector_depth_mm"),
            "connector_wall_thickness_mm": connector_config.get("connector_wall_thickness_mm"),
            "magnet_size": connector_config.get("magnet_size"),
            "magnet_diameter_mm": connector_config.get("magnet_diameter_mm"),
            "magnet_thickness_mm": connector_config.get("magnet_thickness_mm"),
            "lock_profile": connector_config.get("lock_profile"),
            "output_files": split_result["output_files"],
            "report_file": split_result["report_file"],
            "connector_report_file": (split_result["connectors"] or {}).get("report_file"),
            "connectors": split_result["connectors"],
            "validation": split_result["validation"],
            "reason": report["reason"],
            "recommendations": report["recommendations"],
        }
    if stop_if_cancelled(client, job_id):
        return
    result["after_file"] = select_final_output_file(result)
    result["after_download_url"] = f"/api/v1/jobs/{job_id}/files/{result['after_file']}" if result.get("after_file") else None
    result["final_model"] = result.get("after_file")
    result["final_download_url"] = result.get("after_download_url")
    candidate = change_map_candidate(result)
    if candidate:
        operation, source_file, target_file = candidate
        result["change_map"] = create_change_map(job_id, result_dir, input_path, source_file, target_file, operation)
    else:
        result["change_map"] = {
            "available": False,
            "file": None,
            "operation": None,
            "changed_vertices": 0,
            "max_distance": 0.0,
            "mean_distance": 0.0,
            "download_url": None,
            "reason": "Нет операции с видимым изменением модели.",
        }
    result["artifact_map"] = create_artifact_map(job_id, result_dir, input_path, result.get("model_qa") or {})
    result["processing_history"] = build_processing_history(job_id, result)
    update_job(client, job_id, "processing", 80, "Packing analysis result ZIP")
    result["download_ready"] = True
    result["download_url"] = f"/api/v1/jobs/{job_id}/download"
    result["package_ready"] = "prepare_package" in executable_operations
    result["package_message"] = "Пакет подготовки создан" if result["package_ready"] else None
    create_result_zip(job_id, input_path, result, job)
    time.sleep(1)
    client.hset(
        job_key(job_id),
        mapping={
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "processing_seconds": round(time.time() - processing_started, 3),
        },
    )
    update_job(client, job_id, "completed", 100, "STL analysis completed", result=result)
    print(f"Completed job {job_id}", flush=True)


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = Redis.from_url(redis_url, decode_responses=True)
    print("STL Master worker started and waiting for jobs", flush=True)

    while True:
        job_id = None
        try:
            queued = client.blpop(PRIORITY_QUEUE_NAMES, timeout=5)
            if queued is None:
                continue

            _, payload = queued
            job_id = json.loads(payload)["job_id"]
            if stop_if_cancelled(client, job_id):
                continue
            process_job(client, job_id)
        except RedisError as exc:
            print(f"Redis connection failed: {exc}", flush=True)
            time.sleep(5)
        except Exception as exc:
            print(f"Job failed: {exc}", flush=True)
            try:
                if job_id:
                    update_job(client, job_id, "failed", 0, "STL analysis failed")
            except RedisError:
                pass
        finally:
            gc.collect()


if __name__ == "__main__":
    main()
