import json
import os
import re
import shutil
import hashlib
import hmac
import base64
import secrets
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from redis import Redis
from redis.exceptions import RedisError

MAX_UPLOAD_SIZE = 500 * 1024 * 1024
UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", "/data/uploads"))
RESULT_ROOT = Path(os.getenv("RESULT_ROOT", "/data/results"))
FEATURES_PATH = Path(os.getenv("FEATURES_PATH", "/app/config/features.json"))
FEEDBACK_ROOT = Path(os.getenv("FEEDBACK_ROOT", "/data/results/feedback"))
FEEDBACK_TEST_ARCHIVE_ROOT = Path(os.getenv("FEEDBACK_TEST_ARCHIVE_ROOT", "/data/results/feedback_test_archive"))
USERS_ROOT = Path(os.getenv("USERS_ROOT", "/data/results/users"))
USERS_PATH = USERS_ROOT / "users.json"
APPLICATIONS_ROOT = Path(os.getenv("APPLICATIONS_ROOT", "/data/results/applications"))
EARLY_ACCESS_APPLICATIONS_ROOT = APPLICATIONS_ROOT / "early_access"
PREMIUM_APPLICATIONS_ROOT = APPLICATIONS_ROOT / "premium"
AUDIT_ROOT = Path(os.getenv("AUDIT_ROOT", "/data/results/audit"))
AUDIT_PATH = AUDIT_ROOT / "admin_actions.jsonl"
CLEANUP_PLANS_ROOT = Path(os.getenv("CLEANUP_PLANS_ROOT", "/data/results/admin_cleanup_plans"))
QUARANTINE_ROOT = Path(os.getenv("QUARANTINE_ROOT", "/data/quarantine"))
ADMIN_CLEANUP_TEST_ROOT = Path(os.getenv("ADMIN_CLEANUP_TEST_ROOT", "/data/admin-cleanup-test"))
TEST_DATA_PLANS_ROOT = Path(os.getenv("TEST_DATA_PLANS_ROOT", "/data/results/admin_test_data_plans"))
ACCESS_CODE_SALT = os.getenv("ACCESS_CODE_SALT", "stl-master-beta-local-salt")
QUEUE_NAME = "stl:jobs"
PRIORITY_QUEUE_NAMES = {
    "premium": "stl:jobs:premium",
    "early_access": "stl:jobs:early_access",
    "free": "stl:jobs:free",
}
ALL_QUEUE_NAMES = [PRIORITY_QUEUE_NAMES["premium"], PRIORITY_QUEUE_NAMES["early_access"], PRIORITY_QUEUE_NAMES["free"], QUEUE_NAME]
QUEUE_GLOBAL_LIMIT = 50
DEFAULT_ESTIMATED_JOB_SECONDS = 90
PROCESSING_STALE_SECONDS = 5 * 60
HEAVY_OPERATIONS = {"model_improvement", "repair_mesh", "split_model", "fit_to_bed_split", "remove_ai_artifacts", "ai_cleanup", "surface_recovery", "local_smoothing"}
QUEUE_LIMITS = {
    "free": {"active": 1, "queued": 2, "uploads_per_hour": 5, "priority": "free"},
    "early_access": {"active": 1, "queued": 3, "uploads_per_hour": 15, "priority": "early_access"},
    "premium": {"active": 2, "queued": 10, "uploads_per_hour": 50, "priority": "premium"},
}
DEFAULT_FEATURES = {
    "beta_mode": True,
    "beta_upload_limit_mb": 100,
    "surface_recovery": False,
    "local_smoothing": True,
    "split": True,
    "fit_to_bed_split": True,
    "orientation": True,
    "auto_orientation": True,
    "compare_view": True,
    "remove_ai_artifacts": True,
    "print_repair": True,
    "reduce_polygons": True,
    "fix_symmetry": False,
}
ALLOWED_OPERATIONS = {
    "analyze",
    "print_check",
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
    "prepare_package",
}
DEFAULT_OPERATIONS = ["analyze", "print_check"]
ALLOWED_REDUCTION_PERCENT = {25, 50, 75}
ALLOWED_SPLIT_AXIS = {"x", "y", "z"}
ALLOWED_SPLIT_MODE = {"simple", "glue", "pins", "magnets", "lock", "slots"}
ALLOWED_SPLIT_ENGINE = {"safe_mvp", "blender_boolean"}
ALLOWED_CONNECTOR_SIZE_MM = {3, 4, 6}
ALLOWED_CONNECTOR_CLEARANCE_MM = {0.15, 0.25, 0.4}
ALLOWED_CONNECTOR_COUNT = {2, 3, 4}
ALLOWED_MAGNET_SIZES = {"5x2", "6x2", "8x3", "10x3"}
ALLOWED_AI_CLEANUP_STRENGTH = {"light", "medium", "strong"}
ALLOWED_MODEL_IMPROVEMENT_STRENGTH = {"light", "balanced", "strong"}
ALLOWED_SYMMETRY_AXIS = {"x", "y", "z"}
ALLOWED_SYMMETRY_MODE = {"analyze", "fix"}
ALLOWED_ORIENTATION_PRIORITY = {"supports", "speed", "quality"}
ALLOWED_BED_CONNECTOR_MODE = {"none", "pins", "slots"}
ALLOWED_LOCAL_SMOOTHING_STRENGTH = {"light", "balanced", "strong"}
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")

app = FastAPI(title="STL Master API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_redis() -> Redis:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(redis_url, decode_responses=True)


def job_key(job_id: str) -> str:
    return f"stl:job:{job_id}"


def write_job(client: Redis, job_id: str, data: dict[str, str | int]) -> None:
    client.hset(job_key(job_id), mapping=data)


def sanitize_filename(filename: str) -> str:
    basename = Path(filename or "input.stl").name
    sanitized = SAFE_FILENAME_PATTERN.sub("_", basename).strip("._")
    if not sanitized:
        return "input.stl"
    return sanitized[:160]


def sanitize_text(value: str | None, max_length: int = 120) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[\r\n\t]+", " ", value).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned[:max_length]


def sanitize_multiline(value: str | None, max_length: int = 2000) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"\r\n?", "\n", value).strip()
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned[:max_length]


def log_event(message: str, **fields: object) -> None:
    print(json.dumps({"message": message, **fields}, ensure_ascii=False), flush=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_days_iso(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def parse_iso_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or "unknown"
    return request.client.host if request.client else "unknown"


def audit_event(event: str, request: Request | None = None, **details: object) -> None:
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": utc_now_iso(),
        "event": event,
        "ip": client_ip(request) if request else None,
        "details": details,
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as target:
        target.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_audit_events(limit: int = 30) -> list[dict[str, object]]:
    if not AUDIT_PATH.exists():
        return []
    try:
        lines = AUDIT_PATH.read_text(encoding="utf-8").splitlines()[-limit:]
    except OSError:
        return []
    events: list[dict[str, object]] = []
    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def verify_password_hash(password: str, stored_hash: str) -> bool:
    try:
        scheme, iterations_text, salt, digest = stored_hash.split("$", 3)
        iterations = int(iterations_text)
    except (ValueError, TypeError):
        return False
    if scheme != "pbkdf2_sha256" or iterations < 100000:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
    return hmac.compare_digest(candidate, digest)


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def b64url_decode(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def create_admin_session_token() -> dict[str, str]:
    secret = os.getenv("ADMIN_SESSION_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Admin session secret is not configured")
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=12)
    payload = {
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "nonce": secrets.token_urlsafe(16),
    }
    payload_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return {"session_token": f"{payload_b64}.{b64url_encode(signature)}", "expires_at": expires.isoformat()}


def verify_admin_session_token(token: str) -> bool:
    secret = os.getenv("ADMIN_SESSION_SECRET", "")
    if not secret or "." not in token:
        return False
    payload_b64, signature_b64 = token.split(".", 1)
    expected = b64url_encode(hmac.new(secret.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature_b64, expected):
        return False
    try:
        payload = json.loads(b64url_decode(payload_b64))
    except (json.JSONDecodeError, ValueError):
        return False
    return int(payload.get("exp", 0) or 0) >= int(datetime.now(timezone.utc).timestamp())


def redis_rate_limited(key: str, limit: int, window_seconds: int, lock_key: str | None = None, lock_seconds: int = 0) -> bool:
    client = get_redis()
    if lock_key and client.exists(lock_key):
        return True
    count = client.incr(key)
    if count == 1:
        client.expire(key, window_seconds)
    if lock_key and count >= limit:
        client.setex(lock_key, lock_seconds, "1")
    return count > limit


def require_admin_auth(request: Request, authorization: str | None = None, x_admin_token: str | None = None) -> None:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if verify_admin_session_token(token):
            return
    expected = os.getenv("ADMIN_TOKEN", "")
    if expected and x_admin_token and secrets.compare_digest(x_admin_token, expected):
        return
    raise HTTPException(status_code=401, detail="Admin authentication required")


def hash_access_code(code: str) -> str:
    return hashlib.sha256(f"{ACCESS_CODE_SALT}:{code}".encode("utf-8")).hexdigest()


def generate_access_code() -> str:
    return secrets.token_urlsafe(18)


REQUEST_NUMBER_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_premium_access_code() -> str:
    chunks = ["".join(secrets.choice(REQUEST_NUMBER_ALPHABET) for _ in range(4)) for _ in range(3)]
    return f"STL-{'-'.join(chunks)}"


def generate_unique_premium_access_code() -> str:
    existing_hashes = {str(user.get("access_code_hash") or "") for user in read_users()}
    for _ in range(40):
        code = generate_premium_access_code()
        if hash_access_code(code) not in existing_hashes:
            return code
    raise HTTPException(status_code=500, detail="Unable to generate a unique premium code")


def normalize_access_code_input(code: object) -> str:
    normalized = str(code or "").strip()
    normalized = re.sub(r"\s+", "", normalized)
    if len(normalized) > 80:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "invalid_code"})
    if normalized and not re.fullmatch(r"[A-Za-z0-9_-]+", normalized):
        raise HTTPException(status_code=400, detail={"ok": False, "error": "invalid_code"})
    return normalized


def read_users() -> list[dict[str, object]]:
    if not USERS_PATH.exists():
        return []
    try:
        with USERS_PATH.open("r", encoding="utf-8") as source:
            payload = json.load(source)
    except (OSError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


def write_users(users: list[dict[str, object]]) -> None:
    USERS_ROOT.mkdir(parents=True, exist_ok=True)
    with USERS_PATH.open("w", encoding="utf-8") as target:
        json.dump(users, target, ensure_ascii=False, indent=2)


def public_user(user: dict[str, object], access_code: str | None = None) -> dict[str, object]:
    payload = {key: value for key, value in user.items() if key != "access_code_hash"}
    if access_code:
        payload["access_code"] = access_code
    payload["has_access_code"] = bool(user.get("access_code_hash"))
    return payload


def find_user_by_access_code(code: str | None) -> dict[str, object] | None:
    if not code:
        return None
    code_hash = hash_access_code(code.strip())
    for user in read_users():
        stored_hash = str(user.get("access_code_hash") or "")
        if stored_hash and hmac.compare_digest(stored_hash, code_hash):
            return user
    return None


def update_user_by_access_code(code: str, updater) -> dict[str, object] | None:
    code_hash = hash_access_code(code.strip())
    users = read_users()
    for index, user in enumerate(users):
        stored_hash = str(user.get("access_code_hash") or "")
        if stored_hash and hmac.compare_digest(stored_hash, code_hash):
            users[index] = updater(user)
            write_users(users)
            return users[index]
    return None


def beta_access_for_code(code: str | None, ip: str = "unknown") -> dict[str, object]:
    user = find_user_by_access_code(code)
    if code and not user:
        if redis_rate_limited(f"access_code_fail:{ip}", 20, 3600):
            raise HTTPException(status_code=429, detail="Слишком много попыток ввода access-code. Попробуйте позже.")
    if not user:
        return {"access_level": "free", "upload_limit_bytes": beta_upload_limit_bytes(), "user": None}
    expires_at = parse_iso_datetime(user.get("expires_at"))
    if expires_at and expires_at < datetime.now(timezone.utc):
        return {"access_level": "expired", "upload_limit_bytes": 0, "user": user}
    access_level = str(user.get("access_level") or "free")
    if access_level == "blocked":
        return {"access_level": "blocked", "upload_limit_bytes": 0, "user": user}
    if access_level == "premium":
        return {"access_level": "premium", "upload_limit_bytes": min(MAX_UPLOAD_SIZE, 300 * 1024 * 1024), "user": user}
    if access_level == "early_access":
        return {"access_level": "early_access", "upload_limit_bytes": beta_upload_limit_bytes(), "user": user}
    return {"access_level": "free", "upload_limit_bytes": beta_upload_limit_bytes(), "user": user}


def application_root(kind: str) -> Path:
    normalized = kind.strip().lower()
    if normalized in {"early_access", "early-access", "access"}:
        return EARLY_ACCESS_APPLICATIONS_ROOT
    if normalized == "premium":
        return PREMIUM_APPLICATIONS_ROOT
    raise HTTPException(status_code=404, detail="Application type not found")


def application_country(request: Request) -> str:
    for header in ("cf-ipcountry", "x-country", "cloudfront-viewer-country"):
        value = sanitize_text(request.headers.get(header), 40)
        if value:
            return value
    return "unknown"


def public_application(payload: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if key != "_path"}


def read_applications(kind: str | None = None) -> list[dict[str, object]]:
    roots = [application_root(kind)] if kind else [EARLY_ACCESS_APPLICATIONS_ROOT, PREMIUM_APPLICATIONS_ROOT]
    applications: list[dict[str, object]] = []
    for root in roots:
        if not root.exists():
            continue
        for item in sorted(root.glob("*.json"), reverse=True):
            try:
                with item.open("r", encoding="utf-8") as source:
                    payload = json.load(source)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                applications.append(public_application(payload))
    applications.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return applications


def read_application_with_path(kind: str, application_id: str) -> tuple[dict[str, object], Path]:
    safe_id = sanitize_filename(application_id).replace(".json", "")
    path = application_root(kind) / f"{safe_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Application not found")
    try:
        with path.open("r", encoding="utf-8") as source:
            payload = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=404, detail="Application not found") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=404, detail="Application not found")
    return payload, path


def normalize_request_number(value: object) -> str:
    return sanitize_text(str(value or ""), 80).strip().upper()


def find_application_by_request_number(kind: str, request_number: object) -> tuple[dict[str, object], Path] | tuple[None, None]:
    normalized = normalize_request_number(request_number)
    if not normalized:
        return None, None
    root = application_root(kind)
    if not root.exists():
        return None, None
    for item in root.glob("*.json"):
        try:
            with item.open("r", encoding="utf-8") as source:
                payload = json.load(source)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and normalize_request_number(payload.get("request_number")) == normalized:
            return payload, item
    return None, None


def generate_request_number() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    existing_numbers = {normalize_request_number(item.get("request_number")) for item in read_applications("premium")}
    for _ in range(40):
        suffix = "".join(secrets.choice(REQUEST_NUMBER_ALPHABET) for _ in range(6))
        candidate = f"STL-{date_part}-{suffix[:3]}{suffix[3:]}"
        if candidate not in existing_numbers:
            return candidate
    raise HTTPException(status_code=500, detail="Unable to generate a unique request number")


def write_application(kind: str, payload: dict[str, object]) -> dict[str, object]:
    root = application_root(kind)
    root.mkdir(parents=True, exist_ok=True)
    application_id = str(payload.get("id") or uuid4())
    payload["id"] = application_id
    with (root / f"{application_id}.json").open("w", encoding="utf-8") as target:
        json.dump(payload, target, ensure_ascii=False, indent=2)
    return public_application(payload)


def pagination_params(payload: dict[str, object] | None = None) -> tuple[int, int]:
    payload = payload or {}
    try:
        page = int(payload.get("page", 1) or 1)
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(payload.get("per_page", 25) or 25)
    except (TypeError, ValueError):
        per_page = 25
    return max(1, page), min(100, max(1, per_page))


def paginate_items(items: list[dict[str, object]], page: int = 1, per_page: int = 25) -> dict[str, object]:
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "per_page": per_page,
        "from": start + 1 if total and start < total else 0,
        "to": min(end, total),
    }


def admin_plan_path(plan_id: str) -> Path:
    safe_id = sanitize_filename(plan_id).replace(".json", "")
    TEST_DATA_PLANS_ROOT.mkdir(parents=True, exist_ok=True)
    return TEST_DATA_PLANS_ROOT / f"{safe_id}.json"


def write_admin_plan(plan: dict[str, object]) -> dict[str, object]:
    TEST_DATA_PLANS_ROOT.mkdir(parents=True, exist_ok=True)
    with admin_plan_path(str(plan.get("plan_id"))).open("w", encoding="utf-8") as target:
        json.dump(plan, target, ensure_ascii=False, indent=2)
    return plan


def read_admin_plan(plan_id: str) -> dict[str, object]:
    path = admin_plan_path(plan_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Admin plan not found")
    try:
        with path.open("r", encoding="utf-8") as source:
            payload = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=410, detail="Admin plan is unavailable") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=410, detail="Admin plan is invalid")
    expires_at = parse_iso_datetime(payload.get("expires_at"))
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Admin plan expired")
    return payload


def lower_join(*values: object) -> str:
    return " ".join(str(value or "") for value in values).lower()


def is_example_contact(value: object) -> bool:
    text = str(value or "").lower()
    return "@example.com" in text or "@example.test" in text or text.endswith(".test") or "stlmaster.test" in text


def classify_payload(payload: dict[str, object], entity: str, linked_test: bool = False) -> dict[str, object]:
    reasons: list[str] = []
    weak: list[str] = []
    source = str(payload.get("source") or "").lower()
    environment = str(payload.get("environment") or "").lower()
    text = lower_join(
        payload.get("id"),
        payload.get("name"),
        payload.get("contact"),
        payload.get("email"),
        payload.get("telegram"),
        payload.get("comment"),
        payload.get("use_case"),
        payload.get("notes"),
        payload.get("job_id"),
        payload.get("client_id"),
        payload.get("idempotency_key"),
        payload.get("request_number"),
        payload.get("test_run_id"),
        payload.get("test_name"),
    )
    if payload.get("is_test") is True or str(payload.get("is_test") or "").lower() == "true":
        reasons.append("metadata.is_test")
    if source in {"smoke_test", "admin_smoke", "test_fixture", "test", "smoke"} or source.startswith("smoke"):
        reasons.append(f"source:{source}")
    if environment in {"test", "smoke"}:
        reasons.append(f"environment:{environment}")
    if payload.get("test_run_id"):
        reasons.append("test_run_id")
    if linked_test:
        reasons.append("linked_test_record")
    if any(token in text for token in ["launch smoke", "premium smoke", "queue smoke", "queue free", "queue real"]):
        reasons.append("known_smoke_name")
    if any(token in text for token in ["smoke user", "premium reject smoke", "проверка публичного запуска", "smoke rejected"]):
        reasons.append("known_smoke_comment")
    if any(str(payload.get("ip") or "").startswith(prefix) for prefix in ["203.0.113.", "198.51.100.", "192.0.2."]):
        weak.append(f"documentation_ip:{payload.get('ip')}")
    if is_example_contact(payload.get("contact")) or is_example_contact(payload.get("email")):
        weak.append("example_contact")
    if any(token in text for token in ["@launch_smoke", "@premium_smoke", "launch-", "premium-", "queue-", "beta-smoke", "beta-admin-smoke", "beta-real-admin"]):
        weak.append("legacy_smoke_pattern")
    if reasons:
        return {"classification": "test", "reasons": reasons + weak}
    if len(weak) >= 2:
        return {"classification": "test", "reasons": weak}
    if weak:
        return {"classification": "uncertain", "reasons": weak}
    return {"classification": "real", "reasons": []}


def classify_application_payload(payload: dict[str, object], linked_test: bool = False) -> dict[str, object]:
    base = classify_payload(payload, "application", linked_test)
    if base["classification"] in {"test", "uncertain"}:
        if base["classification"] == "uncertain" and "legacy_smoke_pattern" in base.get("reasons", []):
            return {"classification": "legacy_test_candidate", "reasons": base["reasons"] + ["legacy_application_candidate"]}
        return base
    score = 0
    reasons: list[str] = []
    text = lower_join(
        payload.get("contact"),
        payload.get("email"),
        payload.get("telegram"),
        payload.get("client_id"),
        payload.get("comment"),
        payload.get("request_number"),
    )
    if str(payload.get("status") or "").lower() == "rejected":
        score += 2
        reasons.append("status.rejected")
    if not payload.get("user_id"):
        score += 2
        reasons.append("no_linked_user")
    if not payload.get("access_code") and not payload.get("premium_code") and not payload.get("code_id"):
        score += 1
        reasons.append("no_linked_code")
    if "web-test" in text:
        score += 4
        reasons.append("contact.web-test")
    if any(token in text for token in ["web-", "premium-smoke", "launch-", "premium-"]):
        score += 2
        reasons.append("web_or_legacy_contact_pattern")
    if payload.get("admin_comment") or payload.get("manual_note"):
        score -= 3
        reasons.append("manual_admin_note_present")
    if score >= 5:
        return {"classification": "legacy_test_candidate", "reasons": reasons, "legacy_score": score}
    if reasons:
        return {"classification": "uncertain", "reasons": reasons, "legacy_score": score}
    return base


def smoke_audit_windows() -> list[tuple[datetime, datetime]]:
    windows: list[tuple[datetime, datetime]] = []
    for event in read_audit_events(5000):
        event_name = str(event.get("event") or "").lower()
        details = event.get("details") if isinstance(event.get("details"), dict) else {}
        text = lower_join(event_name, details)
        if not any(token in text for token in ["smoke", "test_run_id", "test_data", "legacy_data_scan", "cleanup"]):
            continue
        timestamp = parse_iso_datetime(event.get("timestamp"))
        if timestamp is None:
            continue
        windows.append((timestamp - timedelta(hours=2), timestamp + timedelta(hours=2)))
    return windows


def datetime_in_windows(value: object, windows: list[tuple[datetime, datetime]]) -> bool:
    timestamp = parse_iso_datetime(value)
    if timestamp is None:
        return False
    return any(start <= timestamp <= end for start, end in windows)


def repeated_job_series_counts(jobs: list[dict[str, object]]) -> dict[tuple[str, str, str], int]:
    counts: dict[tuple[str, str, str], int] = {}
    for job in jobs:
        timestamp = parse_iso_datetime(job.get("queued_at") or job.get("completed_at"))
        bucket = timestamp.strftime("%Y-%m-%dT%H") if timestamp else "unknown"
        key = (
            bucket,
            ",".join(sorted(job_operations(job))),
            lower_join(job.get("filename"), job.get("original_filename")),
        )
        counts[key] = counts.get(key, 0) + 1
    return counts


def job_series_key(job: dict[str, object]) -> tuple[str, str, str]:
    timestamp = parse_iso_datetime(job.get("queued_at") or job.get("completed_at"))
    bucket = timestamp.strftime("%Y-%m-%dT%H") if timestamp else "unknown"
    return (
        bucket,
        ",".join(sorted(job_operations(job))),
        lower_join(job.get("filename"), job.get("original_filename")),
    )


def normalize_plan_name(access_level: object) -> str:
    mapping = {
        "free": "Бесплатный",
        "early_access": "Ранний доступ",
        "premium": "Premium",
        "blocked": "Заблокирован",
        "expired": "Истёк",
    }
    return mapping.get(str(access_level or "free"), "Не определено")


def operation_label(operation: object) -> str:
    labels = {
        "analyze": "Анализ модели",
        "print_check": "Проверка печати",
        "model_improvement": "Подготовка модели",
        "fix_symmetry": "Исправление симметрии",
        "repair_mesh": "Ремонт сетки",
        "reduce_polygons": "Уменьшение полигонов",
        "split_model": "Разрез модели",
        "fit_to_bed_split": "Подгонка под печатный стол",
        "apply_orientation": "Ориентация под печать",
        "auto_orientation": "Автоориентация",
        "ai_cleanup": "Очистка AI-артефактов",
        "remove_ai_artifacts": "Очистка AI-артефактов",
        "surface_recovery": "Восстановление поверхности",
        "local_smoothing": "Выборочное сглаживание",
        "prepare_package": "Подготовка пакета",
    }
    return labels.get(str(operation or ""), str(operation or "Не определено"))


def normalized_user(user: dict[str, object]) -> dict[str, object]:
    payload = public_user(user)
    expires_at = parse_iso_datetime(user.get("expires_at"))
    raw_level = str(user.get("access_level") or "free")
    blocked = raw_level == "blocked" or bool(user.get("blocked"))
    premium_active = raw_level == "premium" and not blocked and (expires_at is None or expires_at >= datetime.now(timezone.utc))
    if blocked:
        effective = "blocked"
    elif raw_level == "premium" and not premium_active:
        effective = "free"
    else:
        effective = raw_level if raw_level in {"free", "early_access", "premium"} else "free"
    payload["raw_access_level"] = raw_level
    payload["access_level"] = effective
    payload["plan"] = normalize_plan_name(effective)
    payload["blocked"] = blocked
    payload["premium_active"] = premium_active
    payload["premium_started_at"] = user.get("activated_at") or user.get("approved_at") or user.get("created_at")
    payload["premium_expires_at"] = expires_at.isoformat() if expires_at else None
    if expires_at:
        days_left = (expires_at - datetime.now(timezone.utc)).total_seconds() / 86400
        payload["premium_days_left"] = max(0, int(days_left + 0.999))
    else:
        payload["premium_days_left"] = None
    classification = classify_payload(user, "user")
    payload["classification"] = classification["classification"]
    payload["classification_reasons"] = classification["reasons"]
    payload["archived"] = bool(user.get("archived_at"))
    return payload


def access_limits_payload(access_level: str, upload_limit_bytes: int) -> dict[str, object]:
    normalized_level = normalize_access_level(access_level)
    queue_limits = QUEUE_LIMITS[normalized_level]
    return {
        "max_file_size_mb": int(upload_limit_bytes) // 1024 // 1024,
        "daily_jobs": None,
        "active_jobs": int(queue_limits["active"]),
        "queued_jobs": int(queue_limits["queued"]),
        "uploads_per_hour": int(queue_limits["uploads_per_hour"]),
        "priority": str(queue_limits["priority"]),
    }


def current_user_payload(code: str | None, ip: str = "unknown") -> dict[str, object]:
    normalized_code = normalize_access_code_input(code)
    access = beta_access_for_code(normalized_code, ip)
    access_level = str(access.get("access_level") or "free")
    upload_limit_bytes = int(access.get("upload_limit_bytes") or 0)
    user = access.get("user") if isinstance(access.get("user"), dict) else None
    if user:
        payload = normalized_user(user)
        try:
            uses_count = int(user.get("uses", 0) or 0)
        except (TypeError, ValueError):
            uses_count = 0
        payload["user_id"] = payload.get("id")
        payload["plan"] = str(payload.get("access_level") or access_level)
        payload["plan_label"] = normalize_plan_name(payload.get("access_level"))
        payload["premium_active"] = (
            str(payload.get("access_level") or "") == "premium"
            and bool(user.get("activated_at") or uses_count > 0)
            and not bool(payload.get("blocked"))
        )
        if access_level == "expired":
            payload["access_level"] = "free"
            payload["plan"] = "free"
            payload["plan_label"] = normalize_plan_name("expired")
            payload["premium_active"] = False
        payload["limits"] = access_limits_payload(str(payload.get("access_level") or access_level), upload_limit_bytes)
        return payload
    return {
        "ok": True,
        "user_id": None,
        "access_level": "free",
        "plan": "free",
        "plan_label": normalize_plan_name("free"),
        "premium_active": False,
        "premium_started_at": None,
        "premium_expires_at": None,
        "premium_days_left": None,
        "blocked": False,
        "limits": access_limits_payload("free", upload_limit_bytes or beta_upload_limit_bytes()),
        "has_access_code": bool(normalized_code),
    }


def read_applications_with_paths(kind: str | None = None) -> list[dict[str, object]]:
    roots = [application_root(kind)] if kind else [EARLY_ACCESS_APPLICATIONS_ROOT, PREMIUM_APPLICATIONS_ROOT]
    applications: list[dict[str, object]] = []
    for root in roots:
        if not root.exists():
            continue
        for item in sorted(root.glob("*.json"), reverse=True):
            try:
                with item.open("r", encoding="utf-8") as source:
                    payload = json.load(source)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                payload["_path"] = str(item)
                applications.append(payload)
    applications.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return applications


def safe_job_records(client: Redis | None = None) -> list[dict[str, object]]:
    own_client = client
    if own_client is None:
        own_client = get_redis()
    records: list[dict[str, object]] = []
    try:
        keys = own_client.keys("stl:job:*")
    except RedisError:
        keys = []
    for key in keys:
        job_id = key.rsplit(":", 1)[-1]
        try:
            payload = own_client.hgetall(key)
        except RedisError:
            continue
        if not isinstance(payload, dict):
            continue
        payload["job_id"] = job_id
        records.append(payload)
    records.sort(key=lambda item: str(item.get("queued_at") or item.get("completed_at") or ""), reverse=True)
    return records


def job_operations(job: dict[str, object]) -> list[str]:
    try:
        decoded = json.loads(str(job.get("operations") or "[]"))
    except json.JSONDecodeError:
        decoded = []
    return [str(item) for item in decoded] if isinstance(decoded, list) else []


def is_test_like_artifact_set(job_id: str) -> bool:
    result_dir = RESULT_ROOT / job_id
    if not result_dir.exists() or not is_cleanup_path_allowed(result_dir):
        return False
    names = {item.name for item in result_dir.iterdir() if item.is_file()}
    smoke_sets = [
        {"artifact_map.json", "print_report.txt", "manifest.json"},
        {"change_map.json", "artifact_map.json", "print_report.txt", "manifest.json"},
        {"split_part_1.stl", "split_part_2.stl", "print_report.txt", "manifest.json"},
        {"fit_to_bed_report.json", "print_report.txt", "manifest.json"},
    ]
    return any(pattern.issubset(names) for pattern in smoke_sets)


def job_linked_file_paths(job_id: str) -> list[dict[str, object]]:
    linked: list[dict[str, object]] = []
    for label, root in (("uploads", UPLOAD_ROOT), ("results", RESULT_ROOT)):
        target = root / job_id
        if not target.exists() or not is_cleanup_path_allowed(target):
            continue
        linked.append({
            "kind": label,
            "path": str(target),
            "size_bytes": directory_size(target),
            "exists": True,
        })
    return linked


def classify_job_payload(
    job: dict[str, object],
    test_user_ids: set[str] | None = None,
    real_user_ids: set[str] | None = None,
    smoke_windows: list[tuple[datetime, datetime]] | None = None,
    series_counts: dict[tuple[str, str, str], int] | None = None,
) -> dict[str, object]:
    test_user_ids = test_user_ids or set()
    real_user_ids = real_user_ids or set()
    user_id = str(job.get("beta_user_id") or job.get("user_id") or "")
    base = classify_payload(job, "job", linked_test=bool(user_id and user_id in test_user_ids))
    if base["classification"] == "test":
        return base | {"legacy_score": 0}

    source = str(job.get("source") or "").lower()
    environment = str(job.get("environment") or "").lower()
    access_level = normalize_access_level(job.get("access_level"))
    operations = set(job_operations(job))
    job_id = str(job.get("job_id") or "")

    positive_real: list[str] = []
    if user_id and user_id in real_user_ids:
        positive_real.append("linked_existing_non_test_user")
    if source in {"public_user", "frontend_user"}:
        positive_real.append(f"source:{source}")
    if environment == "production" and source in {"public_user", "frontend_user"} and (job.get("client_id") or job.get("contact") or job.get("ip")):
        positive_real.append("client_identity_present")
    if positive_real:
        return {"classification": "real", "reasons": positive_real, "legacy_score": 0}

    smoke_ops = {
        "analyze",
        "print_check",
        "repair_mesh",
        "model_improvement",
        "remove_ai_artifacts",
        "ai_cleanup",
        "surface_recovery",
        "local_smoothing",
        "reduce_polygons",
        "apply_orientation",
        "auto_orientation",
        "fit_to_bed_split",
        "split_model",
        "prepare_package",
    }
    score = 0
    reasons: list[str] = []
    if not user_id:
        score += 3
        reasons.append("no_user_id")
    if not source:
        score += 3
        reasons.append("no_source")
    if not environment:
        score += 3
        reasons.append("no_environment")
    if smoke_windows and datetime_in_windows(job.get("queued_at") or job.get("completed_at"), smoke_windows):
        score += 3
        reasons.append("known_smoke_window")
    if operations and operations.issubset(smoke_ops):
        score += 2
        reasons.append("operations_match_smoke_matrix")
    if access_level == "free" and not user_id:
        score += 2
        reasons.append("free_access_without_user")
    filename_text = lower_join(job.get("filename"), job.get("original_filename"), job.get("input_path"))
    if any(token in filename_text for token in ["geely", "public-smoke", "smoke", "test", "box", "fixture"]):
        score += 2
        reasons.append("test_fixture_filename")
    if job_id and is_test_like_artifact_set(job_id):
        score += 2
        reasons.append("test_like_artifact_set")
    if not job.get("ip") and not job.get("contact") and not job.get("client_id"):
        score += 2
        reasons.append("no_ip_or_contact")
    if series_counts and series_counts.get(job_series_key(job), 0) >= 3:
        score += 2
        reasons.append("same_parameter_series")
    if not job.get("is_test") and not job.get("test_run_id") and not source and not environment:
        score += 3
        reasons.append("legacy_missing_test_metadata")
    if score >= 11:
        return {"classification": "legacy_test_candidate", "reasons": reasons, "legacy_score": score}
    if score >= 6:
        return {"classification": "uncertain", "reasons": reasons, "legacy_score": score}
    return {"classification": "uncertain", "reasons": reasons or ["no_positive_real_signal"], "legacy_score": score}


def job_public_payload(
    job: dict[str, object],
    test_user_ids: set[str] | None = None,
    real_user_ids: set[str] | None = None,
    smoke_windows: list[tuple[datetime, datetime]] | None = None,
    series_counts: dict[tuple[str, str, str], int] | None = None,
) -> dict[str, object]:
    test_user_ids = test_user_ids or set()
    job_id = str(job.get("job_id") or "")
    stale_processing = str(job.get("status") or "") == "processing" and not is_fresh_processing_job({str(k): str(v) for k, v in job.items()})
    classification = classify_job_payload(job, test_user_ids, real_user_ids, smoke_windows, series_counts)
    return {
        "job_id": job_id,
        "status": "stale_processing" if stale_processing else str(job.get("status") or "unknown"),
        "operations": job_operations(job),
        "user_id": job.get("beta_user_id") or "",
        "access_level": normalize_access_level(job.get("access_level")),
        "priority": job.get("priority") or queue_priority_for_access(job.get("access_level")),
        "created_at": job.get("queued_at"),
        "started_at": job.get("processing_started_at"),
        "completed_at": job.get("completed_at"),
        "file_size_mb": round(int(job.get("size_bytes", 0) or 0) / 1024 / 1024, 2),
        "classification": classification["classification"],
        "classification_reasons": classification["reasons"],
        "legacy_score": classification.get("legacy_score", 0),
        "test_run_id": job.get("test_run_id") or "",
        "test_name": job.get("test_name") or "",
        "linked_files": job_linked_file_paths(job_id),
        "active": str(job.get("status") or "") in {"queued", "processing"},
    }


def relation_index() -> dict[str, object]:
    users = read_users()
    user_ids = {str(user.get("id")) for user in users}
    user_classification = {str(user.get("id")): classify_payload(user, "user") for user in users}
    test_user_ids = {user_id for user_id, item in user_classification.items() if item.get("classification") == "test"}
    real_user_ids = {user_id for user_id, item in user_classification.items() if item.get("classification") == "real"}
    applications = read_applications_with_paths()
    app_by_user: dict[str, list[dict[str, object]]] = {}
    for application in applications:
        user_id = str(application.get("user_id") or "")
        if user_id:
            app_by_user.setdefault(user_id, []).append(application)
    jobs = safe_job_records()
    job_by_user: dict[str, list[dict[str, object]]] = {}
    job_by_id = {str(job.get("job_id")): job for job in jobs}
    for job in jobs:
        user_id = str(job.get("beta_user_id") or "")
        if user_id:
            job_by_user.setdefault(user_id, []).append(job)
    feedback_entries = read_feedback_entries_with_paths()
    feedback_by_job: dict[str, list[dict[str, object]]] = {}
    for entry in feedback_entries:
        job_id = str(entry.get("job_id") or "")
        if job_id:
            feedback_by_job.setdefault(job_id, []).append(entry)
    return {
        "users": users,
        "user_ids": user_ids,
        "test_user_ids": test_user_ids,
        "real_user_ids": real_user_ids,
        "applications": applications,
        "app_by_user": app_by_user,
        "jobs": jobs,
        "job_by_user": job_by_user,
        "job_by_id": job_by_id,
        "feedback_entries": feedback_entries,
        "feedback_by_job": feedback_by_job,
    }


def file_size_for_job(job_id: str) -> int:
    total = 0
    for root in (UPLOAD_ROOT, RESULT_ROOT):
        target = root / job_id
        if target.exists() and is_cleanup_path_allowed(target):
            total += directory_size(target)
    return total


def test_data_scan_payload(include_items: bool = True) -> dict[str, object]:
    rel = relation_index()
    users = rel["users"]
    test_user_ids: set[str] = rel["test_user_ids"]  # type: ignore[assignment]
    real_user_ids: set[str] = rel["real_user_ids"]  # type: ignore[assignment]
    apps = rel["applications"]
    jobs = rel["jobs"]
    feedback_entries = rel["feedback_entries"]
    job_by_id: dict[str, dict[str, object]] = rel["job_by_id"]  # type: ignore[assignment]
    feedback_by_job: dict[str, list[dict[str, object]]] = rel["feedback_by_job"]  # type: ignore[assignment]
    smoke_windows = smoke_audit_windows()
    series_counts = repeated_job_series_counts(jobs)
    categories = {
        "users": [],
        "applications": [],
        "premium_codes": [],
        "jobs": [],
        "feedback": [],
        "files": [],
    }
    legacy_categories = {
        "applications": [],
        "jobs": [],
        "files": [],
    }
    uncertain: list[dict[str, object]] = []
    for user in users:
        payload = normalized_user(user)
        if payload["classification"] == "test":
            categories["users"].append(payload)
            if user.get("access_code_hash"):
                categories["premium_codes"].append({
                    "id": str(user.get("id")),
                    "user_id": str(user.get("id")),
                    "masked_code": "STL-••••-••••-••••" if user.get("access_level") == "premium" else "••••••",
                    "status": "activated" if user.get("activated_at") else "issued",
                    "classification": "test",
                    "classification_reasons": payload["classification_reasons"],
                })
        elif payload["classification"] == "uncertain":
            uncertain.append({"entity": "user", "id": user.get("id"), "label": user.get("contact") or user.get("name"), "reasons": payload["classification_reasons"]})
    for app_item in apps:
        linked = str(app_item.get("user_id") or "") in test_user_ids
        classification = classify_application_payload(app_item, linked)
        item = public_application(app_item) | {
            "classification": classification["classification"],
            "classification_reasons": classification["reasons"],
            "legacy_score": classification.get("legacy_score", 0),
        }
        if classification["classification"] == "test":
            categories["applications"].append(item)
        elif classification["classification"] == "legacy_test_candidate":
            legacy_categories["applications"].append(item)
        elif classification["classification"] == "uncertain":
            uncertain.append({"entity": "application", "id": app_item.get("id"), "label": app_item.get("request_number") or app_item.get("email"), "reasons": classification["reasons"]})
    for job in jobs:
        item = job_public_payload(job, test_user_ids, real_user_ids, smoke_windows, series_counts)
        if item["classification"] == "test":
            categories["jobs"].append(item)
            size_bytes = file_size_for_job(str(item["job_id"]))
            categories["files"].append({
                "id": str(item["job_id"]),
                "job_id": str(item["job_id"]),
                "category": "test_job_artifacts",
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / 1024 / 1024, 2),
                "classification": "test",
            })
        elif item["classification"] == "legacy_test_candidate":
            legacy_categories["jobs"].append(item)
            size_bytes = file_size_for_job(str(item["job_id"]))
            legacy_categories["files"].append({
                "id": str(item["job_id"]),
                "job_id": str(item["job_id"]),
                "category": "legacy_job_artifacts",
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / 1024 / 1024, 2),
                "classification": "legacy_test_candidate",
            })
        elif item["classification"] == "uncertain":
            uncertain.append({"entity": "job", "id": item["job_id"], "label": ", ".join(item["operations"]), "reasons": item["classification_reasons"]})
    for entry in feedback_entries:
        job_id = str(entry.get("job_id") or "")
        linked_job_classification = ""
        if job_id in job_by_id:
            linked_job_classification = str(job_public_payload(job_by_id[job_id], test_user_ids, real_user_ids, smoke_windows, series_counts)["classification"])
        linked = linked_job_classification in {"test", "legacy_test_candidate"}
        classification = classify_payload(entry, "feedback", linked or bool(entry.get("is_test")))
        item = {key: value for key, value in entry.items() if key != "_path"} | {"classification": classification["classification"], "classification_reasons": classification["reasons"]}
        if classification["classification"] == "test":
            categories["feedback"].append(item)
        elif classification["classification"] == "uncertain":
            uncertain.append({"entity": "feedback", "id": entry.get("feedback_id") or entry.get("_path"), "label": entry.get("contact") or entry.get("comment"), "reasons": classification["reasons"]})
    test_fixture_size = directory_size(ADMIN_CLEANUP_TEST_ROOT) if ADMIN_CLEANUP_TEST_ROOT.exists() else 0
    if test_fixture_size:
        categories["files"].append({
            "id": "admin-cleanup-test",
            "category": "admin_cleanup_test_root",
            "size_bytes": test_fixture_size,
            "size_mb": round(test_fixture_size / 1024 / 1024, 2),
            "classification": "test",
        })
    totals = {
        "users": len(users),
        "applications": len(apps),
        "premium_codes": len([user for user in users if user.get("access_code_hash")]),
        "jobs": len(jobs),
        "feedback": len(feedback_entries),
        "files": len(categories["files"]),
    }
    test_counts = {key: len(value) for key, value in categories.items()}
    legacy_counts = {key: len(value) for key, value in legacy_categories.items()}
    uncertain_counts: dict[str, int] = {}
    for item in uncertain:
        entity = str(item.get("entity") or "unknown")
        uncertain_counts[entity] = uncertain_counts.get(entity, 0) + 1
    real_counts = {
        key: max(0, totals.get(key, 0) - test_counts.get(key, 0) - legacy_counts.get(key, 0) - uncertain_counts.get(key.rstrip("s"), 0))
        for key in totals
    }
    total_size = sum(int(item.get("size_bytes", 0) or 0) for item in categories["files"])
    legacy_size = sum(int(item.get("size_bytes", 0) or 0) for item in legacy_categories["files"])
    payload = {
        "generated_at": utc_now_iso(),
        "summary": {
            "total": totals,
            "test": test_counts,
            "legacy_test_candidate": legacy_counts,
            "real": real_counts,
            "uncertain": uncertain_counts,
            "test_size_bytes": total_size,
            "test_size_mb": round(total_size / 1024 / 1024, 2),
            "legacy_size_bytes": legacy_size,
            "legacy_size_mb": round(legacy_size / 1024 / 1024, 2),
        },
        "uncertain": uncertain[:100],
    }
    if include_items:
        payload["items"] = {key: value[:200] for key, value in categories.items()}
        payload["legacy_items"] = {key: value[:200] for key, value in legacy_categories.items()}
    return payload


def filter_test_scan_by_run_id(scan: dict[str, object], test_run_id: str) -> dict[str, object]:
    if not test_run_id:
        return scan
    items = scan.get("items") if isinstance(scan.get("items"), dict) else {}
    if not isinstance(items, dict):
        return scan
    filtered_items: dict[str, list[dict[str, object]]] = {}
    matching_job_ids: set[str] = set()
    for key, values in items.items():
        filtered: list[dict[str, object]] = []
        if isinstance(values, list):
            for value in values:
                if not isinstance(value, dict):
                    continue
                if str(value.get("test_run_id") or "") == test_run_id:
                    filtered.append(value)
                    if key == "jobs":
                        matching_job_ids.add(str(value.get("job_id") or ""))
        filtered_items[str(key)] = filtered
    if "files" in items:
        filtered_files: list[dict[str, object]] = []
        for value in items.get("files", []) if isinstance(items.get("files"), list) else []:
            if not isinstance(value, dict):
                continue
            if str(value.get("test_run_id") or "") == test_run_id or str(value.get("job_id") or "") in matching_job_ids:
                filtered_files.append(value)
        filtered_items["files"] = filtered_files
    run_counts = {key: len(value) for key, value in filtered_items.items()}
    payload = dict(scan)
    payload["items"] = filtered_items
    payload["filtered_test_run_id"] = test_run_id
    payload["filtered_test_counts"] = run_counts
    return payload


def build_legacy_cleanup_plan() -> dict[str, object]:
    rel = relation_index()
    test_user_ids: set[str] = rel["test_user_ids"]  # type: ignore[assignment]
    real_user_ids: set[str] = rel["real_user_ids"]  # type: ignore[assignment]
    jobs: list[dict[str, object]] = rel["jobs"]  # type: ignore[assignment]
    apps: list[dict[str, object]] = rel["applications"]  # type: ignore[assignment]
    active = set(active_job_ids())
    smoke_windows = smoke_audit_windows()
    series_counts = repeated_job_series_counts(jobs)
    cleanup_id = str(uuid4())
    quarantine = QUARANTINE_ROOT / f"legacy-jobs-{cleanup_id}"
    legacy_jobs: list[dict[str, object]] = []
    protected_jobs: list[dict[str, object]] = []
    uncertain_jobs: list[dict[str, object]] = []
    real_jobs: list[dict[str, object]] = []
    completed = failed = cancelled = 0
    estimated_size = 0
    for job in jobs:
        item = job_public_payload(job, test_user_ids, real_user_ids, smoke_windows, series_counts)
        job_id = str(item.get("job_id") or "")
        status = str(item.get("status") or "")
        if status == "completed":
            completed += 1
        elif status == "failed":
            failed += 1
        elif status == "cancelled":
            cancelled += 1
        if item.get("classification") == "legacy_test_candidate":
            linked_files = job_linked_file_paths(job_id)
            size = sum(int(file.get("size_bytes", 0) or 0) for file in linked_files)
            candidate = item | {
                "protected": job_id in active or status in {"queued", "processing", "stale_processing"},
                "linked_files": linked_files,
                "estimated_size_bytes": size,
            }
            if candidate["protected"]:
                protected_jobs.append(candidate)
            else:
                estimated_size += size
                legacy_jobs.append(candidate)
        elif item.get("classification") == "uncertain":
            uncertain_jobs.append(item)
        elif item.get("classification") == "real":
            real_jobs.append(item)
    legacy_apps: list[dict[str, object]] = []
    uncertain_apps: list[dict[str, object]] = []
    real_apps: list[dict[str, object]] = []
    for app_item in apps:
        classification = classify_application_payload(app_item)
        public_item = public_application(app_item) | {
            "classification": classification["classification"],
            "classification_reasons": classification["reasons"],
            "legacy_score": classification.get("legacy_score", 0),
        }
        if classification["classification"] == "legacy_test_candidate":
            legacy_apps.append(public_item)
        elif classification["classification"] == "uncertain":
            uncertain_apps.append(public_item)
        elif classification["classification"] == "real":
            real_apps.append(public_item)
    plan_id = str(uuid4())
    plan = {
        "plan_id": plan_id,
        "type": "legacy_cleanup",
        "created_at": utc_now_iso(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=45)).isoformat(),
        "cleanup_id": cleanup_id,
        "quarantine": str(quarantine),
        "manifest_path": str(quarantine / "manifest.json"),
        "confirmation_token": f"QUARANTINE LEGACY {len(legacy_jobs)} JOBS {len(legacy_apps)} APPLICATIONS",
        "summary": {
            "jobs_total": len(jobs),
            "jobs_legacy_test_candidate": len(legacy_jobs),
            "jobs_real": len(real_jobs),
            "jobs_uncertain": len(uncertain_jobs),
            "jobs_active_protected": len(protected_jobs),
            "jobs_completed": completed,
            "jobs_failed": failed,
            "jobs_cancelled": cancelled,
            "applications_total": len(apps),
            "applications_legacy_test_candidate": len(legacy_apps),
            "applications_real": len(real_apps),
            "applications_uncertain": len(uncertain_apps),
            "estimated_files": sum(len(item.get("linked_files", [])) for item in legacy_jobs),
            "estimated_size_bytes": estimated_size,
            "estimated_size_mb": round(estimated_size / 1024 / 1024, 2),
        },
        "jobs": legacy_jobs,
        "protected_jobs": protected_jobs,
        "real_jobs": real_jobs[:100],
        "uncertain_jobs": uncertain_jobs[:100],
        "applications": legacy_apps,
        "real_applications": real_apps,
        "uncertain_applications": uncertain_apps,
        "restore": {
            "jobs": "docker exec stl-master-backend python /data/quarantine/<legacy-cleanup>/restore_jobs.py",
            "applications": "cp /data/quarantine/<legacy-cleanup>/applications/*.json /data/results/applications/premium/",
        },
    }
    write_admin_plan(plan)
    return plan


def build_user_deletion_plan(user_ids: list[str], mode: str = "archive", options: dict[str, object] | None = None) -> dict[str, object]:
    options = options or {}
    rel = relation_index()
    users = rel["users"]
    app_by_user: dict[str, list[dict[str, object]]] = rel["app_by_user"]  # type: ignore[assignment]
    job_by_user: dict[str, list[dict[str, object]]] = rel["job_by_user"]  # type: ignore[assignment]
    feedback_by_job: dict[str, list[dict[str, object]]] = rel["feedback_by_job"]  # type: ignore[assignment]
    requested = {str(item) for item in user_ids if str(item).strip()}
    plan_users = [user for user in users if str(user.get("id")) in requested]
    if not plan_users:
        raise HTTPException(status_code=404, detail="No users found for deletion preview")
    protected: list[dict[str, object]] = []
    plan_items: list[dict[str, object]] = []
    estimated_size = 0
    active = set(active_job_ids())
    for user in plan_users:
        user_id = str(user.get("id"))
        classification = classify_payload(user, "user")
        user_jobs = job_by_user.get(user_id, [])
        active_jobs = [str(job.get("job_id")) for job in user_jobs if str(job.get("job_id")) in active or str(job.get("status")) in {"queued", "processing"}]
        if active_jobs:
            protected.append({"user_id": user_id, "reason": "active_jobs", "jobs": active_jobs})
        size = sum(file_size_for_job(str(job.get("job_id"))) for job in user_jobs)
        estimated_size += size
        job_ids = [str(job.get("job_id")) for job in user_jobs]
        plan_items.append({
            "user": normalized_user(user),
            "classification": classification["classification"],
            "applications": [public_application(app) for app in app_by_user.get(user_id, [])],
            "jobs": [job_public_payload(job, {user_id}) for job in user_jobs],
            "feedback": [entry for job_id in job_ids for entry in feedback_by_job.get(job_id, [])],
            "files_size_bytes": size,
            "can_delete_permanently": classification["classification"] == "test",
        })
    plan_id = str(uuid4())
    plan = {
        "plan_id": plan_id,
        "type": "user_deletion",
        "mode": mode if mode in {"archive", "delete"} else "archive",
        "created_at": utc_now_iso(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        "confirmation_token": f"УДАЛИТЬ ПОЛЬЗОВАТЕЛЕЙ {len(plan_items)}",
        "user_ids": [str(user.get("id")) for user in plan_users],
        "options": {
            "delete_uploads": bool(options.get("delete_uploads")),
            "delete_results": bool(options.get("delete_results")),
            "delete_feedback": bool(options.get("delete_feedback")),
            "revoke_codes": bool(options.get("revoke_codes", True)),
            "keep_audit": True,
        },
        "items": plan_items,
        "protected_items": protected,
        "estimated_size_bytes": estimated_size,
        "estimated_size_mb": round(estimated_size / 1024 / 1024, 2),
    }
    write_admin_plan(plan)
    return plan


def approval_message(access_level: str, access_code: str, expires_at: str | None) -> str:
    term = "Premium" if access_level == "premium" else "ранний доступ"
    duration = expires_at or "без ограничения срока"
    return (
        "Здравствуйте!\n\n"
        "Ваша заявка одобрена.\n\n"
        f"Ваш код доступа:\n{access_code}\n\n"
        f"Тип доступа:\n{term}\n\n"
        f"Срок действия:\n{duration}\n\n"
        "Добро пожаловать в STL Master!"
    )


def public_premium_application_status(application: dict[str, object]) -> dict[str, object]:
    status = str(application.get("status") or "pending")
    return {
        "ok": True,
        "application_id": application.get("id"),
        "request_number": application.get("request_number"),
        "status": status,
        "created_at": application.get("created_at"),
        "updated_at": application.get("updated_at") or application.get("approved_at") or application.get("created_at"),
        "approved_at": application.get("approved_at"),
        "code_issued": status in {"code_issued", "activated"},
        "activated": status == "activated" or bool(application.get("activated_at")),
        "activated_at": application.get("activated_at"),
        "rejected_reason": application.get("rejected_reason") if status == "rejected" else None,
    }


def update_user_seen(user_id: str | None) -> None:
    if not user_id:
        return
    users = read_users()
    changed = False
    for user in users:
        if user.get("id") == user_id:
            user["jobs_count"] = int(user.get("jobs_count", 0) or 0) + 1
            user["last_seen_at"] = utc_now_iso()
            changed = True
            break
    if changed:
        write_users(users)


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                continue
    return total


def active_job_ids() -> list[str]:
    try:
        client = get_redis()
        active: list[str] = []
        for key in client.keys("stl:job:*"):
            job = client.hgetall(key)
            if job.get("status") in {"queued", "processing"}:
                active.append(str(job.get("job_id") or key.rsplit(":", 1)[-1]))
        return sorted(set(active))
    except RedisError:
        return []


def normalize_access_level(access_level: str | None) -> str:
    normalized = str(access_level or "free").strip().lower()
    return normalized if normalized in QUEUE_LIMITS else "free"


def queue_priority_for_access(access_level: str | None) -> str:
    return str(QUEUE_LIMITS[normalize_access_level(access_level)]["priority"])


def queue_name_for_priority(priority: str | None) -> str:
    return PRIORITY_QUEUE_NAMES.get(str(priority or "free"), PRIORITY_QUEUE_NAMES["free"])


def is_local_ip(ip: str) -> bool:
    return ip in {"127.0.0.1", "::1", "localhost"} or ip.startswith("172.") or ip.startswith("10.") or ip.startswith("192.168.")


def queue_owner_key(beta_access: dict[str, object], ip: str) -> str:
    user = beta_access.get("user")
    if isinstance(user, dict) and user.get("id"):
        return f"user:{user['id']}"
    return f"ip:{ip or 'unknown'}"


def queued_payloads(client: Redis) -> list[tuple[str, str]]:
    payloads: list[tuple[str, str]] = []
    for queue_name in ALL_QUEUE_NAMES:
        try:
            for raw in client.lrange(queue_name, 0, -1):
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                job_id = str(payload.get("job_id") or "")
                if job_id:
                    payloads.append((queue_name, job_id))
        except RedisError:
            continue
    return payloads


def queue_size(client: Redis) -> int:
    return len(queued_payloads(client))


def queue_position_for_job(client: Redis, job_id: str) -> int | None:
    for index, (_, queued_job_id) in enumerate(queued_payloads(client), start=1):
        if queued_job_id == job_id:
            return index
    return None


def active_queue_counts(client: Redis, owner_key: str | None = None) -> dict[str, int]:
    counts = {"queued": 0, "processing": 0, "stale_processing": 0, "completed_24h": 0, "failed_24h": 0}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    for key in client.keys("stl:job:*"):
        job = client.hgetall(key)
        if owner_key and job.get("queue_owner_key") != owner_key:
            continue
        status = job.get("status")
        if status == "queued":
            counts["queued"] += 1
        elif status == "processing" and is_fresh_processing_job(job):
            counts["processing"] += 1
        elif status == "stale_processing" or status == "processing":
            counts["stale_processing"] += 1
        elif status in {"completed", "failed"}:
            timestamp = job.get("completed_at") or job.get("updated_at")
            try:
                parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")) if timestamp else None
            except ValueError:
                parsed = None
            if parsed and parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            if parsed and parsed >= cutoff:
                counts["completed_24h" if status == "completed" else "failed_24h"] += 1
    return counts


def parse_job_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_fresh_processing_job(job: dict[str, str]) -> bool:
    if job.get("status") != "processing":
        return False
    timestamp = parse_job_datetime(job.get("updated_at") or job.get("processing_started_at"))
    if not timestamp:
        return False
    return (datetime.now(timezone.utc) - timestamp).total_seconds() <= PROCESSING_STALE_SECONDS


def job_lock_keys(job_id: str) -> list[str]:
    return [
        f"stl:job:{job_id}:lock",
        f"stl:job_lock:{job_id}",
        f"stl:lock:{job_id}",
        f"job_lock:{job_id}",
    ]


def job_runtime_diagnostics(client: Redis, job_id: str, job: dict[str, str]) -> dict[str, object]:
    heartbeat_value = job.get("worker_heartbeat") or job.get("heartbeat_at") or job.get("updated_at") or ""
    heartbeat_at = parse_job_datetime(heartbeat_value)
    heartbeat_age = None
    if heartbeat_at:
        heartbeat_age = round((datetime.now(timezone.utc) - heartbeat_at).total_seconds())
    lock_keys = job_lock_keys(job_id)
    existing_locks: list[str] = []
    try:
        existing_locks = [key for key in lock_keys if client.exists(key)]
    except RedisError:
        existing_locks = []
    return {
        "pid": job.get("worker_pid") or job.get("pid") or "",
        "worker": job.get("worker_id") or job.get("worker") or "",
        "started_at": job.get("processing_started_at") or "",
        "last_heartbeat": heartbeat_value,
        "heartbeat_age_seconds": heartbeat_age,
        "last_update": job.get("updated_at") or job.get("completed_at") or job.get("queued_at") or "",
        "container": job.get("worker_container") or os.getenv("HOSTNAME", ""),
        "redis_key": job_key(job_id),
        "lock_status": "locked" if existing_locks or str(job.get("locked") or "").lower() == "true" else "unlocked",
        "lock_keys": existing_locks,
        "owner": job.get("queue_owner_key") or job.get("beta_user_id") or job.get("user_id") or "",
        "has_process": bool(job.get("worker_pid") or job.get("pid")),
        "has_worker": bool(job.get("worker_id") or job.get("worker")),
    }


def job_can_regular_delete(client: Redis, job_id: str, job: dict[str, str]) -> tuple[bool, str]:
    status = str(job.get("status") or "")
    diagnostics = job_runtime_diagnostics(client, job_id, job)
    if status in {"queued", "processing"}:
        return False, "задание ещё активно"
    if diagnostics.get("lock_status") == "locked":
        return False, "найден lock"
    if diagnostics.get("has_process"):
        return False, "указан процесс обработки"
    if diagnostics.get("has_worker"):
        return False, "указан worker"
    return True, "можно удалить"


def move_job_artifacts(job_id: str, target_root: Path) -> tuple[int, int]:
    moved = 0
    size = 0
    for root in (UPLOAD_ROOT, RESULT_ROOT):
        source = root / job_id
        if source.exists() and is_cleanup_path_allowed(source) and not source.is_symlink():
            destination_root = target_root / root.name
            destination_root.mkdir(parents=True, exist_ok=True)
            destination = destination_root / job_id
            if destination.exists():
                destination = destination_root / f"{job_id}-{uuid4().hex[:8]}"
            shutil.move(str(source), str(destination))
            moved += 1
            size += directory_size(destination)
    return moved, size


def delete_feedback_for_job(job_id: str, target_root: Path | None = None) -> int:
    moved = 0
    for entry in read_feedback_entries_with_paths():
        if str(entry.get("job_id") or "") != job_id:
            continue
        source = Path(str(entry.get("_path") or ""))
        if not source.exists() or source.parent != FEEDBACK_ROOT:
            continue
        if target_root is not None:
            target = target_root / "feedback"
            target.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target / source.name))
        else:
            source.unlink(missing_ok=True)
        moved += 1
    return moved


def force_delete_job(client: Redis, job_id: str, target_root: Path) -> dict[str, object]:
    job = client.hgetall(job_key(job_id))
    manifest: dict[str, object] = {"job_id": job_id, "redis_hash": job, "files": 0, "bytes": 0, "feedback": 0, "locks": []}
    files, size = move_job_artifacts(job_id, target_root)
    manifest["files"] = files
    manifest["bytes"] = size
    manifest["feedback"] = delete_feedback_for_job(job_id, target_root)
    for key in job_lock_keys(job_id):
        try:
            if client.exists(key):
                client.delete(key)
                manifest["locks"].append(key)  # type: ignore[index]
        except RedisError:
            continue
    client.delete(job_key(job_id))
    remove_job_from_queues(client, job_id)
    return manifest


def admin_integrity_check(auto_fix: bool = False) -> dict[str, object]:
    issues: dict[str, list[dict[str, object]]] = {
        "orphan_jobs": [],
        "orphan_files": [],
        "redis": [],
        "locks": [],
        "uploads": [],
        "results": [],
        "feedback": [],
        "users": [],
        "applications": [],
    }
    fixed: list[dict[str, object]] = []
    try:
        client = get_redis()
        job_ids = {key.rsplit(":", 1)[-1] for key in client.keys("stl:job:*")}
        queued_ids = {job_id for _, job_id in queued_payloads(client)}
        for job_id in sorted(queued_ids - job_ids):
            issues["orphan_jobs"].append({"job_id": job_id, "reason": "очередь ссылается на отсутствующий Redis hash"})
            if auto_fix:
                remove_job_from_queues(client, job_id)
                fixed.append({"entity": "queue", "id": job_id})
        for key in client.keys("stl:*lock*"):
            issues["locks"].append({"key": key})
    except RedisError as exc:
        issues["redis"].append({"error": str(exc)})
        job_ids = set()
    for root, bucket in [(UPLOAD_ROOT, "uploads"), (RESULT_ROOT, "results")]:
        if not root.exists():
            continue
        for item in root.iterdir():
            if item.name in {"feedback", "feedback_test_archive", "users", "applications", "audit", "admin_cleanup_plans", "admin_test_data_plans"}:
                continue
            if item.is_dir() and item.name not in job_ids:
                issues["orphan_files"].append({"path": str(item), "kind": bucket, "size_bytes": directory_size(item)})
    for entry in read_feedback_entries_with_paths():
        job_id = str(entry.get("job_id") or "")
        if job_id and job_id not in job_ids:
            issue = {"feedback_id": entry.get("feedback_id"), "job_id": job_id}
            issues["feedback"].append(issue)
            if auto_fix:
                source = Path(str(entry.get("_path") or ""))
                if source.exists() and source.is_file() and source.is_relative_to(FEEDBACK_ROOT):
                    quarantine = QUARANTINE_ROOT / "integrity-feedback" / str(uuid4())
                    quarantine.mkdir(parents=True, exist_ok=True)
                    target = quarantine / source.name
                    shutil.move(str(source), str(target))
                    fixed.append({"entity": "feedback", "id": entry.get("feedback_id"), "from": str(source), "to": str(target)})
    summary = {key: len(value) for key, value in issues.items()}
    return {"ok": not any(summary.values()), "summary": summary, "issues": issues, "fixed": fixed}


def queued_jobs_for_owner(client: Redis, owner_key: str) -> int:
    return active_queue_counts(client, owner_key)["queued"]


def processing_jobs_for_owner(client: Redis, owner_key: str) -> int:
    return active_queue_counts(client, owner_key)["processing"]


def enforce_queue_limits(client: Redis, beta_access: dict[str, object], ip: str, selected_operations: list[str]) -> tuple[str, str]:
    access_level = normalize_access_level(str(beta_access.get("access_level") or "free"))
    limits = QUEUE_LIMITS[access_level]
    owner_key = queue_owner_key(beta_access, ip)
    global_size = queue_size(client)
    if global_size >= QUEUE_GLOBAL_LIMIT:
        raise HTTPException(status_code=429, detail="Сервер сейчас перегружен. Попробуйте позже.")
    active_count = processing_jobs_for_owner(client, owner_key)
    queued_count = queued_jobs_for_owner(client, owner_key)
    if active_count >= int(limits["active"]) or queued_count >= int(limits["queued"]):
        raise HTTPException(status_code=429, detail="Сейчас у вас уже есть задача в обработке. Дождитесь завершения или используйте Premium-доступ.")
    if not is_local_ip(ip):
        rate_key = f"upload_rate:{owner_key}"
        if redis_rate_limited(rate_key, int(limits["uploads_per_hour"]), 3600):
            raise HTTPException(status_code=429, detail="Слишком много загрузок за час. Попробуйте позже.")
    return owner_key, queue_priority_for_access(access_level)


def enqueue_job(client: Redis, job_id: str, priority: str) -> None:
    client.rpush(queue_name_for_priority(priority), json.dumps({"job_id": job_id, "priority": priority}))


def remove_job_from_queues(client: Redis, job_id: str) -> bool:
    removed = False
    for queue_name in ALL_QUEUE_NAMES:
        for raw in client.lrange(queue_name, 0, -1):
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if str(payload.get("job_id") or "") == job_id:
                client.lrem(queue_name, 0, raw)
                removed = True
    return removed


def job_queue_status(client: Redis, job_id: str, job: dict[str, str]) -> dict[str, object]:
    current_size = queue_size(client)
    position = queue_position_for_job(client, job_id)
    status = job.get("status")
    if status == "queued" and position is None:
        position = current_size + 1
    estimated = int((position or 0) * DEFAULT_ESTIMATED_JOB_SECONDS) if status == "queued" else 0
    return {
        "queue_position": position,
        "queue_size": current_size,
        "estimated_wait_seconds": estimated,
        "priority": job.get("priority") or queue_priority_for_access(job.get("access_level")),
        "access_level": normalize_access_level(job.get("access_level")),
    }


def admin_queue_snapshot(client: Redis) -> dict[str, object]:
    queued_ids = [job_id for _, job_id in queued_payloads(client)]
    jobs: list[dict[str, object]] = []
    durations: list[float] = []
    counts = {"queued": 0, "processing": 0, "stale_processing": 0, "completed_24h": 0, "failed_24h": 0}
    by_access: dict[str, int] = {}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    for key in client.keys("stl:job:*"):
        job_id = key.rsplit(":", 1)[-1]
        job = client.hgetall(key)
        status = job.get("status", "unknown")
        stale_processing = status == "processing" and not is_fresh_processing_job(job)
        if stale_processing:
            status = "stale_processing"
            try:
                client.hset(key, mapping={
                    "status": "stale_processing",
                    "message": "Задание зависло: heartbeat отсутствует более 5 минут.",
                    "stale_detected_at": utc_now_iso(),
                })
                job["status"] = "stale_processing"
            except RedisError:
                pass
        include = status in {"queued", "processing"}
        if status == "stale_processing":
            include = True
        if status in {"completed", "failed"}:
            timestamp = job.get("completed_at")
            try:
                parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")) if timestamp else None
            except ValueError:
                parsed = None
            include = bool(parsed and parsed >= cutoff)
            if include and job.get("processing_seconds"):
                try:
                    durations.append(float(job["processing_seconds"]))
                except ValueError:
                    pass
        if not include:
            continue
        if status == "queued":
            counts["queued"] += 1
        elif status == "processing" and not stale_processing:
            counts["processing"] += 1
        elif stale_processing or status == "stale_processing":
            counts["stale_processing"] += 1
        elif status == "completed":
            counts["completed_24h"] += 1
        elif status == "failed":
            counts["failed_24h"] += 1
        access_level = normalize_access_level(job.get("access_level"))
        by_access[access_level] = by_access.get(access_level, 0) + 1
        try:
            operations = json.loads(job.get("operations", "[]"))
        except json.JSONDecodeError:
            operations = []
        diagnostics = job_runtime_diagnostics(client, job_id, job)
        jobs.append({
            "job_id": job_id,
            "status": "stale_processing" if stale_processing else status,
            "operations": operations if isinstance(operations, list) else [],
            "operation_labels": [operation_label(str(operation)) for operation in operations] if isinstance(operations, list) else [],
            "user_id": job.get("beta_user_id") or "",
            "access_level": access_level,
            "priority": job.get("priority") or queue_priority_for_access(access_level),
            "created_at": job.get("queued_at"),
            "started_at": job.get("processing_started_at"),
            "completed_at": job.get("completed_at"),
            "duration": float(job.get("processing_seconds", 0) or 0),
            "file_size_mb": round(int(job.get("size_bytes", 0) or 0) / 1024 / 1024, 2),
            "queue_position": queued_ids.index(job_id) + 1 if job_id in queued_ids else None,
            "cancel_requested": job.get("cancel_requested") == "true",
            "classification": job_public_payload(job | {"job_id": job_id}).get("classification"),
            "classification_reasons": job_public_payload(job | {"job_id": job_id}).get("classification_reasons"),
            "runtime": diagnostics,
            "pid": diagnostics.get("pid"),
            "worker": diagnostics.get("worker"),
            "last_heartbeat": diagnostics.get("last_heartbeat"),
            "heartbeat_age_seconds": diagnostics.get("heartbeat_age_seconds"),
            "last_update": diagnostics.get("last_update"),
            "container": diagnostics.get("container"),
            "redis_key": diagnostics.get("redis_key"),
            "lock_status": diagnostics.get("lock_status"),
            "owner": diagnostics.get("owner"),
        })
    status_order = {"stale_processing": 0, "processing": 1, "queued": 2, "failed": 3, "completed": 4}
    jobs.sort(key=lambda item: (status_order.get(str(item["status"]), 9), item.get("queue_position") or 99999, str(item.get("created_at") or "")))
    return {
        "queue_size": len(queued_ids),
        "queued_jobs": counts["queued"],
        "processing_jobs": counts["processing"],
        "stale_processing_jobs": counts["stale_processing"],
        "completed_24h": counts["completed_24h"],
        "failed_24h": counts["failed_24h"],
        "average_processing_seconds": round(sum(durations) / len(durations), 2) if durations else 0,
        "by_access_level": by_access,
        "jobs": jobs[:100],
    }


def safe_job_dirs(root: Path, older_than_hours: float, active_ids: set[str]) -> list[Path]:
    if not root.exists():
        return []
    cutoff = datetime.now(timezone.utc).timestamp() - older_than_hours * 3600
    candidates: list[Path] = []
    for item in root.iterdir():
        if not item.is_dir() or item.name in {"feedback", "feedback_test_archive", "users"} or item.name in active_ids:
            continue
        try:
            if item.stat().st_mtime < cutoff:
                candidates.append(item)
        except OSError:
            continue
    return candidates


def cleanup_allowed_roots() -> list[Path]:
    return [UPLOAD_ROOT, RESULT_ROOT, ADMIN_CLEANUP_TEST_ROOT]


def safe_resolve(path: Path) -> Path:
    return path.resolve(strict=False)


def is_path_inside(path: Path, root: Path) -> bool:
    try:
        safe_resolve(path).relative_to(safe_resolve(root))
        return True
    except ValueError:
        return False


def is_cleanup_path_allowed(path: Path) -> bool:
    resolved = safe_resolve(path)
    return any(is_path_inside(resolved, root) for root in cleanup_allowed_roots())


def masked_path(path: Path) -> str:
    resolved = safe_resolve(path)
    for root in cleanup_allowed_roots():
        if is_path_inside(resolved, root):
            try:
                return f"{root.name}/{resolved.relative_to(safe_resolve(root))}"
            except ValueError:
                continue
    return resolved.name


def cleanup_item_id(path: Path, category: str) -> str:
    digest = hashlib.sha256(f"{category}:{safe_resolve(path)}".encode("utf-8")).hexdigest()
    return digest[:24]


def cleanup_plan_path(scan_id: str) -> Path:
    safe_id = sanitize_filename(scan_id).replace(".json", "")
    return CLEANUP_PLANS_ROOT / f"{safe_id}.json"


def read_cleanup_plan(scan_id: str) -> dict[str, object]:
    path = cleanup_plan_path(scan_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Cleanup scan not found")
    try:
        with path.open("r", encoding="utf-8") as source:
            payload = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=410, detail="Cleanup scan is unavailable") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=410, detail="Cleanup scan is invalid")
    expires_at = parse_iso_datetime(payload.get("expires_at"))
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Cleanup scan expired")
    return payload


def file_age_hours(path: Path) -> float:
    try:
        modified = path.lstat().st_mtime
    except OSError:
        return 0.0
    return max(0.0, (datetime.now(timezone.utc).timestamp() - modified) / 3600)


def cleanup_candidate_item(path: Path, category: str, reason: str, safe_to_delete: bool) -> dict[str, object]:
    try:
        size_bytes = directory_size(path) if path.is_dir() and not path.is_symlink() else path.lstat().st_size
    except OSError:
        size_bytes = 0
    return {
        "id": cleanup_item_id(path, category),
        "category": category,
        "path": str(safe_resolve(path)),
        "path_masked": masked_path(path),
        "size_bytes": size_bytes,
        "age_hours": round(file_age_hours(path), 2),
        "reason": reason,
        "safe_to_delete": safe_to_delete,
    }


def build_cleanup_plan(older_than_hours: float = 6.0) -> dict[str, object]:
    active = set(active_job_ids())
    items: list[dict[str, object]] = []
    protected: list[dict[str, object]] = []
    for root, category, reason in [
        (UPLOAD_ROOT, "expired_upload", "upload_ttl_exceeded"),
        (RESULT_ROOT, "expired_result", "result_retention_exceeded"),
        (ADMIN_CLEANUP_TEST_ROOT, "marked_test_fixture", "admin_cleanup_test_fixture"),
    ]:
        if not root.exists():
            continue
        for item in root.iterdir():
            if item.name in {"feedback", "feedback_test_archive", "users", "applications", "audit", "admin_cleanup_plans"}:
                continue
            if item.is_symlink():
                protected.append(cleanup_candidate_item(item, "protected_symlink", "symlink_not_followed", False))
                continue
            if not item.is_dir() and root != ADMIN_CLEANUP_TEST_ROOT:
                continue
            if not is_cleanup_path_allowed(item):
                protected.append(cleanup_candidate_item(item, "protected_path", "outside_allowlisted_roots", False))
                continue
            if item.name in active:
                protected.append(cleanup_candidate_item(item, "active_job", "job_is_queued_or_processing", False))
                continue
            if root != ADMIN_CLEANUP_TEST_ROOT and file_age_hours(item) < older_than_hours:
                continue
            items.append(cleanup_candidate_item(item, category, reason, True))

    scan_id = str(uuid4())
    created_at = utc_now_iso()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    total_size = sum(int(item.get("size_bytes", 0) or 0) for item in items)
    by_category: dict[str, dict[str, int]] = {}
    for item in items:
        category = str(item.get("category") or "unknown")
        bucket = by_category.setdefault(category, {"count": 0, "size_bytes": 0})
        bucket["count"] += 1
        bucket["size_bytes"] += int(item.get("size_bytes", 0) or 0)
    plan = {
        "scan_id": scan_id,
        "created_at": created_at,
        "expires_at": expires_at,
        "older_than_hours": older_than_hours,
        "items": [{key: value for key, value in item.items() if key != "path"} for item in items],
        "_items": items,
        "total_size_bytes": total_size,
        "protected_count": len(protected),
        "protected_examples": [{key: value for key, value in item.items() if key != "path"} for item in protected[:12]],
        "categories": by_category,
        "confirmation_token": f"УДАЛИТЬ {len(items)}",
    }
    CLEANUP_PLANS_ROOT.mkdir(parents=True, exist_ok=True)
    with cleanup_plan_path(scan_id).open("w", encoding="utf-8") as target:
        json.dump(plan, target, ensure_ascii=False, indent=2)
    return {key: value for key, value in plan.items() if key != "_items"}


def execute_cleanup_plan(scan_id: str, selected_ids: set[str], confirmation_token: str, request: Request) -> dict[str, object]:
    plan = read_cleanup_plan(scan_id)
    expected_token = str(plan.get("confirmation_token") or "")
    if not expected_token or confirmation_token != expected_token:
        raise HTTPException(status_code=400, detail="Invalid cleanup confirmation token")
    raw_items = plan.get("_items")
    if not isinstance(raw_items, list):
        raw_items = []
    active = set(active_job_ids())
    cleanup_id = str(uuid4())
    deleted = 0
    quarantined = 0
    protected = 0
    skipped = 0
    not_found = 0
    errors = 0
    freed = 0
    results: list[dict[str, object]] = []
    quarantine_target = QUARANTINE_ROOT / cleanup_id
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "")
        if selected_ids and item_id not in selected_ids:
            skipped += 1
            results.append({"id": item_id, "status": "skipped", "path_masked": item.get("path_masked")})
            continue
        path = Path(str(item.get("path") or ""))
        category = str(item.get("category") or "")
        if path.name in active or not bool(item.get("safe_to_delete")) or not is_cleanup_path_allowed(path) or path.is_symlink():
            protected += 1
            results.append({"id": item_id, "status": "protected", "path_masked": item.get("path_masked")})
            continue
        if not path.exists():
            not_found += 1
            results.append({"id": item_id, "status": "not_found", "path_masked": item.get("path_masked")})
            continue
        size_before = directory_size(path) if path.is_dir() else path.stat().st_size
        try:
            if category in {"expired_result"}:
                quarantine_target.mkdir(parents=True, exist_ok=True)
                destination = quarantine_target / path.name
                if destination.exists():
                    destination = quarantine_target / f"{path.name}-{uuid4().hex[:8]}"
                shutil.move(str(path), str(destination))
                quarantined += 1
                status = "quarantined"
            elif path.is_dir():
                shutil.rmtree(path)
                deleted += 1
                status = "deleted"
            else:
                path.unlink()
                deleted += 1
                status = "deleted"
            freed += size_before
            results.append({"id": item_id, "status": status, "path_masked": item.get("path_masked"), "size_bytes": size_before})
        except OSError as exc:
            errors += 1
            results.append({"id": item_id, "status": "error", "path_masked": item.get("path_masked"), "error": str(exc)})
    payload = {
        "cleanup_id": cleanup_id,
        "scan_id": scan_id,
        "deleted": deleted,
        "quarantined": quarantined,
        "protected": protected,
        "skipped": skipped,
        "not_found": not_found,
        "errors": errors,
        "failed": errors,
        "freed_bytes": freed,
        "freed_mb": round(freed / 1024 / 1024, 2),
        "quarantine": str(quarantine_target) if quarantined else None,
        "results": results,
    }
    audit_event("cleanup_execution", request, cleanup_id=cleanup_id, scan_id=scan_id, deleted=deleted, quarantined=quarantined, freed_mb=payload["freed_mb"], errors=errors)
    return payload


def load_features() -> dict[str, object]:
    features = DEFAULT_FEATURES.copy()
    if FEATURES_PATH.exists():
        try:
            with FEATURES_PATH.open("r", encoding="utf-8") as source:
                configured = json.load(source)
            if isinstance(configured, dict):
                features.update({str(key): value for key, value in configured.items()})
        except (OSError, json.JSONDecodeError):
            log_event("features_config_read_failed", path=str(FEATURES_PATH))
    return features


def beta_upload_limit_bytes() -> int:
    raw_limit = os.getenv("BETA_UPLOAD_LIMIT_MB") or load_features().get("beta_upload_limit_mb", 100)
    try:
        limit_mb = int(raw_limit)
    except (TypeError, ValueError):
        limit_mb = 100
    limit_mb = max(1, min(limit_mb, 500))
    return min(MAX_UPLOAD_SIZE, limit_mb * 1024 * 1024)


def upload_limit_message(limit_bytes: int) -> str:
    return f"Для раннего доступа принимаются STL до {limit_bytes // 1024 // 1024} МБ"


def parse_operations(raw_operations: str | None) -> list[str]:
    if not raw_operations:
        return DEFAULT_OPERATIONS

    try:
        decoded = json.loads(raw_operations)
        if not isinstance(decoded, list):
            raise ValueError
        operations = [str(item).strip() for item in decoded]
    except (json.JSONDecodeError, ValueError, TypeError):
        operations = [item.strip() for item in raw_operations.split(",")]

    normalized = []
    for operation in operations:
        if not operation:
            continue
        if operation not in ALLOWED_OPERATIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported operation: {operation}")
        if operation not in normalized:
            normalized.append(operation)

    return normalized or DEFAULT_OPERATIONS


def parse_reduction_percent(raw_percent: int | str | None) -> int:
    if raw_percent is None or raw_percent == "":
        return 50
    try:
        percent = int(raw_percent)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="reduction_percent must be 25, 50 or 75") from exc
    if percent not in ALLOWED_REDUCTION_PERCENT:
        raise HTTPException(status_code=400, detail="reduction_percent must be 25, 50 or 75")
    return percent


def parse_split_axis(raw_axis: str | None) -> str:
    if not raw_axis:
        return "z"
    axis = raw_axis.lower().strip()
    if axis not in ALLOWED_SPLIT_AXIS:
        raise HTTPException(status_code=400, detail="split_axis must be x, y or z")
    return axis


def parse_split_parts(raw_parts: int | str | None) -> int:
    if raw_parts is None or raw_parts == "":
        return 2
    try:
        parts = int(raw_parts)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="split_parts must be an integer from 2 to 4") from exc
    if parts < 2 or parts > 4:
        raise HTTPException(status_code=400, detail="split_parts must be an integer from 2 to 4")
    return parts


def parse_split_mode(raw_mode: str | None) -> str:
    if not raw_mode:
        return "simple"
    mode = raw_mode.lower().strip()
    if mode not in ALLOWED_SPLIT_MODE:
        raise HTTPException(status_code=400, detail="split_mode must be simple, glue, pins, magnets, lock or slots")
    return mode


def parse_split_engine(raw_engine: str | None) -> str:
    if not raw_engine:
        return "blender_boolean"
    engine = raw_engine.lower().strip()
    if engine not in ALLOWED_SPLIT_ENGINE:
        raise HTTPException(status_code=400, detail="split_engine must be safe_mvp or blender_boolean")
    return engine


def parse_connector_size(raw_size: int | str | None) -> int:
    if raw_size is None or raw_size == "":
        return 4
    try:
        size = int(raw_size)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="connector_size_mm must be 3, 4 or 6") from exc
    if size not in ALLOWED_CONNECTOR_SIZE_MM:
        raise HTTPException(status_code=400, detail="connector_size_mm must be 3, 4 or 6")
    return size


def parse_connector_clearance(raw_clearance: float | str | None) -> float:
    if raw_clearance is None or raw_clearance == "":
        return 0.25
    try:
        clearance = float(raw_clearance)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="connector_clearance_mm must be 0.15, 0.25 or 0.4") from exc
    if clearance not in ALLOWED_CONNECTOR_CLEARANCE_MM:
        raise HTTPException(status_code=400, detail="connector_clearance_mm must be 0.15, 0.25 or 0.4")
    return clearance


def parse_connector_count(raw_count: int | str | None) -> int:
    if raw_count is None or raw_count == "":
        return 2
    try:
        count = int(raw_count)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="connector_count must be 2, 3 or 4") from exc
    if count not in ALLOWED_CONNECTOR_COUNT:
        raise HTTPException(status_code=400, detail="connector_count must be 2, 3 or 4")
    return count


def parse_connector_depth(raw_depth: int | float | str | None) -> float:
    if raw_depth is None or raw_depth == "":
        return 6.0
    try:
        depth = float(raw_depth)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="connector_depth_mm must be between 2 and 30") from exc
    if depth < 2 or depth > 30:
        raise HTTPException(status_code=400, detail="connector_depth_mm must be between 2 and 30")
    return depth


def parse_connector_wall_thickness(raw_thickness: int | float | str | None) -> float:
    if raw_thickness is None or raw_thickness == "":
        return 1.2
    try:
        thickness = float(raw_thickness)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="connector_wall_thickness_mm must be between 0.4 and 5") from exc
    if thickness < 0.4 or thickness > 5:
        raise HTTPException(status_code=400, detail="connector_wall_thickness_mm must be between 0.4 and 5")
    return thickness


def parse_magnet_size(raw_size: str | None) -> tuple[str, float, float]:
    size = (raw_size or "6x2").lower().strip().replace("×", "x")
    if size not in ALLOWED_MAGNET_SIZES:
        raise HTTPException(status_code=400, detail="magnet_size must be 5x2, 6x2, 8x3 or 10x3")
    diameter, thickness = size.split("x", 1)
    return size, float(diameter), float(thickness)


def parse_ai_cleanup_strength(raw_strength: str | None) -> str:
    if not raw_strength:
        return "medium"
    strength = raw_strength.lower().strip()
    if strength not in ALLOWED_AI_CLEANUP_STRENGTH:
        raise HTTPException(status_code=400, detail="ai_cleanup_strength must be light, medium or strong")
    return strength


def parse_artifact_cleanup_strength(raw_strength: str | None) -> str:
    if not raw_strength:
        return "balanced"
    strength = raw_strength.lower().strip()
    if strength == "medium":
        strength = "balanced"
    if strength not in {"light", "balanced", "strong"}:
        raise HTTPException(status_code=400, detail="artifact_cleanup_strength must be light, balanced or strong")
    return strength


def parse_model_improvement_strength(raw_strength: str | None) -> str:
    if not raw_strength:
        return "balanced"
    strength = raw_strength.lower().strip()
    if strength == "medium":
        strength = "balanced"
    if strength not in ALLOWED_MODEL_IMPROVEMENT_STRENGTH:
        raise HTTPException(status_code=400, detail="model_improvement_strength must be light, balanced or strong")
    return strength


def parse_symmetry_axis(raw_axis: str | None) -> str:
    if not raw_axis:
        return "x"
    axis = raw_axis.lower().strip()
    if axis not in ALLOWED_SYMMETRY_AXIS:
        raise HTTPException(status_code=400, detail="symmetry_axis must be x, y or z")
    return axis


def parse_symmetry_mode(raw_mode: str | None) -> str:
    if not raw_mode:
        return "analyze"
    mode = raw_mode.lower().strip()
    if mode not in ALLOWED_SYMMETRY_MODE:
        raise HTTPException(status_code=400, detail="symmetry_mode must be analyze or fix")
    return mode


def parse_bool(raw_value: bool | str | None, default: bool = False) -> bool:
    if raw_value is None or raw_value == "":
        return default
    if isinstance(raw_value, bool):
        return raw_value
    value = str(raw_value).strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise HTTPException(status_code=400, detail="Значение должно быть true или false")


def parse_orientation_transform(raw_transform: str | None) -> dict[str, object]:
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
    if not raw_transform:
        return defaults
    try:
        decoded = json.loads(raw_transform)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="orientation_transform must be a JSON object") from exc
    if not isinstance(decoded, dict):
        raise HTTPException(status_code=400, detail="orientation_transform must be a JSON object")

    transform = defaults.copy()
    for axis in ("x", "y", "z"):
        key = f"rotation_{axis}"
        deg_key = f"rotation_{axis}_deg"
        try:
            value = float(decoded.get(deg_key, decoded.get(key, defaults[key])))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"{key} must be a number") from exc
        if abs(value) > 36000:
            raise HTTPException(status_code=400, detail=f"{key} is outside the allowed range")
        transform[key] = value
        transform[deg_key] = value
    for key in ("translate_x_mm", "translate_z_mm"):
        try:
            value = float(decoded.get(key, defaults[key]))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"{key} must be a number") from exc
        if abs(value) > 100000:
            raise HTTPException(status_code=400, detail=f"{key} is outside the allowed range")
        transform[key] = value
    translate_value = decoded.get("translate_to_floor", defaults["translate_to_floor"])
    if isinstance(translate_value, bool):
        transform["translate_to_floor"] = translate_value
    elif isinstance(translate_value, str) and translate_value.lower() in {"true", "false"}:
        transform["translate_to_floor"] = translate_value.lower() == "true"
    else:
        raise HTTPException(status_code=400, detail="translate_to_floor must be a boolean")
    return transform


def parse_split_plane_offset(raw_offset: int | float | str | None) -> float:
    if raw_offset is None or raw_offset == "":
        return 0.0
    try:
        offset = float(raw_offset)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="split_plane_offset_mm must be a number") from exc
    if abs(offset) > 100000:
        raise HTTPException(status_code=400, detail="split_plane_offset_mm is outside the allowed range")
    return offset


def parse_local_selection(raw_selection: str | None) -> dict[str, object] | None:
    if not raw_selection:
        return None
    try:
        decoded = json.loads(raw_selection)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="local_selection must be a JSON object") from exc
    if not isinstance(decoded, dict):
        raise HTTPException(status_code=400, detail="local_selection must be a JSON object")

    def parse_region(region: object, index: int) -> dict[str, object]:
        if not isinstance(region, dict):
            raise HTTPException(status_code=400, detail=f"local_selection.regions[{index}] must be an object")
        center = region.get("center")
        if not isinstance(center, list) or len(center) != 3:
            raise HTTPException(status_code=400, detail=f"local_selection.regions[{index}].center must contain 3 numbers")
        try:
            parsed_center = [float(value) for value in center]
            radius_mm = float(region.get("radius_mm"))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="local_selection center and radius must be numeric") from exc
        if radius_mm < 1 or radius_mm > 100:
            raise HTTPException(status_code=400, detail="local_selection.radius_mm must be between 1 and 100")
        return {"center": parsed_center, "radius_mm": radius_mm}

    strength = str(decoded.get("strength", "balanced")).strip().lower()
    if strength not in ALLOWED_LOCAL_SMOOTHING_STRENGTH:
        raise HTTPException(status_code=400, detail="local_selection.strength must be light, balanced or strong")

    selection_type = decoded.get("type")
    if selection_type == "sphere":
        region = parse_region(decoded, 0)
        return {
            "type": "sphere",
            "center": region["center"],
            "radius_mm": region["radius_mm"],
            "strength": strength,
        }
    if selection_type == "spheres":
        regions = decoded.get("regions")
        if not isinstance(regions, list) or not regions:
            raise HTTPException(status_code=400, detail="local_selection.regions must contain at least one region")
        if len(regions) > 30:
            raise HTTPException(status_code=400, detail="local_selection.regions supports at most 30 regions")
        parsed_regions = [parse_region(region, index) for index, region in enumerate(regions)]
        return {
            "type": "spheres",
            "regions": parsed_regions,
            "strength": strength,
        }

    raise HTTPException(status_code=400, detail="local_selection.type must be sphere or spheres")


def parse_orientation_priority(raw_priority: str | None) -> str:
    if not raw_priority:
        return "supports"
    priority = raw_priority.lower().strip()
    if priority not in ALLOWED_ORIENTATION_PRIORITY:
        raise HTTPException(status_code=400, detail="orientation_priority must be supports, speed or quality")
    return priority


def parse_bed_size(raw_size: int | float | str | None, default: float, field_name: str) -> float:
    if raw_size is None or raw_size == "":
        return default
    try:
        value = float(raw_size)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} must be a positive number") from exc
    if value <= 0 or value > 2000:
        raise HTTPException(status_code=400, detail=f"{field_name} must be between 1 and 2000")
    return value


def parse_bed_connector_mode(raw_mode: str | None) -> str:
    if not raw_mode:
        return "none"
    mode = raw_mode.lower().strip()
    if mode not in ALLOWED_BED_CONNECTOR_MODE:
        raise HTTPException(status_code=400, detail="bed_connector_mode must be none, pins or slots")
    return mode


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/status")
def status() -> dict[str, str]:
    redis_state = "unknown"
    try:
        client = get_redis()
        redis_state = "ok" if client.ping() else "unavailable"
    except RedisError:
        redis_state = "unavailable"

    return {
        "service": "stl-master-backend",
        "status": "ok",
        "redis": redis_state,
    }


@app.get("/api/v1/config/features")
def features() -> dict[str, object]:
    configured_features = load_features()
    configured_features["absolute_upload_limit_mb"] = MAX_UPLOAD_SIZE // 1024 // 1024
    configured_features["active_upload_limit_mb"] = beta_upload_limit_bytes() // 1024 // 1024
    return configured_features


@app.get("/api/v1/me")
def current_user(request: Request, x_beta_access_code: str | None = Header(default=None, alias="X-Beta-Access-Code")) -> dict[str, object]:
    payload = current_user_payload(x_beta_access_code, client_ip(request))
    payload["ok"] = True
    return payload


@app.post("/api/v1/access-requests")
async def submit_access_request(request: Request) -> dict[str, str]:
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Application payload must be JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Application payload must be an object")

    name = sanitize_text(str(payload.get("name", "")), 120)
    email = sanitize_text(str(payload.get("email", "")), 180)
    if not name or not email:
        raise HTTPException(status_code=400, detail="Имя и email обязательны")
    application = {
        "id": str(uuid4()),
        "type": "early_access",
        "name": name,
        "email": email,
        "telegram": sanitize_text(str(payload.get("telegram", "")), 120),
        "occupation": sanitize_text(str(payload.get("occupation", "")), 240),
        "use_case": sanitize_multiline(str(payload.get("use_case", "")), 2000),
        "comment": sanitize_multiline(str(payload.get("use_case", "")), 2000),
        "ip": client_ip(request),
        "country": application_country(request),
        "created_at": utc_now_iso(),
        "status": "new",
        "approved_at": None,
        "user_id": None,
        "is_test": bool(payload.get("is_test") is True),
        "source": sanitize_text(str(payload.get("source", "website")), 80) or "website",
        "environment": sanitize_text(str(payload.get("environment", "production")), 80) or "production",
        "test_run_id": sanitize_text(str(payload.get("test_run_id", "")), 120),
        "test_name": sanitize_text(str(payload.get("test_name", "")), 120),
    }
    saved = write_application("early_access", application)
    log_event("access_request_saved", application_id=saved["id"], type="early_access")
    return {"status": "ok", "application_id": str(saved["id"])}


@app.post("/api/v1/premium-requests")
async def submit_premium_request(request: Request, idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key")) -> dict[str, object]:
    if redis_rate_limited(f"premium_request_create:{client_ip(request)}", 20, 3600):
        raise HTTPException(status_code=429, detail={"ok": False, "error": "rate_limited"})
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Premium payload must be JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Premium payload must be an object")

    name = sanitize_text(str(payload.get("name", "")), 120)
    email = sanitize_text(str(payload.get("email", "")), 180)
    client_identifier = sanitize_text(str(payload.get("client_id", "")), 180)
    contact = sanitize_text(str(payload.get("contact", "")), 180)
    idempotency_key = sanitize_text(str(idempotency_key_header or payload.get("idempotency_key") or ""), 180)
    if idempotency_key:
        for existing in read_applications("premium"):
            if str(existing.get("idempotency_key") or "") == idempotency_key:
                return {
                    "ok": True,
                    "status": str(existing.get("status") or "pending"),
                    "application_id": str(existing.get("id") or ""),
                    "request_number": str(existing.get("request_number") or ""),
                    "created_at": existing.get("created_at"),
                }
    created_at = utc_now_iso()
    application = {
        "id": str(uuid4()),
        "type": "premium",
        "request_number": generate_request_number(),
        "name": name or "Premium request",
        "email": email,
        "telegram": sanitize_text(str(payload.get("telegram", "")), 120),
        "occupation": "",
        "use_case": "",
        "comment": sanitize_multiline(str(payload.get("comment", "")), 2000),
        "source": sanitize_text(str(payload.get("source", "website")), 80) or "website",
        "requested_plan": sanitize_text(str(payload.get("requested_plan", "premium_monthly_299")), 80),
        "tariff": "Premium",
        "client_id": client_identifier,
        "contact": contact,
        "idempotency_key": idempotency_key,
        "ip": client_ip(request),
        "country": application_country(request),
        "created_at": created_at,
        "updated_at": created_at,
        "status": "pending",
        "approved_at": None,
        "activated_at": None,
        "user_id": None,
        "is_test": bool(payload.get("is_test") is True),
        "environment": sanitize_text(str(payload.get("environment", "production")), 80) or "production",
        "test_run_id": sanitize_text(str(payload.get("test_run_id", "")), 120),
        "test_name": sanitize_text(str(payload.get("test_name", "")), 120),
    }
    saved = write_application("premium", application)
    log_event("access_request_saved", application_id=saved["id"], request_number=saved.get("request_number"), type="premium")
    return {
        "ok": True,
        "status": str(saved.get("status") or "pending"),
        "application_id": str(saved["id"]),
        "request_number": str(saved.get("request_number") or ""),
        "created_at": saved.get("created_at"),
    }


@app.get("/api/v1/premium-requests/by-number/{request_number}")
def premium_request_status_by_number(request_number: str, request: Request) -> dict[str, object]:
    if redis_rate_limited(f"premium_request_status:{client_ip(request)}", 120, 3600):
        raise HTTPException(status_code=429, detail={"ok": False, "error": "rate_limited"})
    application, _ = find_application_by_request_number("premium", request_number)
    if application is None:
        raise HTTPException(status_code=404, detail={"ok": False, "error": "request_not_found"})
    return public_premium_application_status(application)


@app.get("/api/v1/premium-requests/{application_id}")
def premium_request_status(application_id: str, request: Request) -> dict[str, object]:
    if redis_rate_limited(f"premium_request_status:{client_ip(request)}", 120, 3600):
        raise HTTPException(status_code=429, detail={"ok": False, "error": "rate_limited"})
    try:
        application, _ = read_application_with_path("premium", application_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            raise HTTPException(status_code=404, detail={"ok": False, "error": "request_not_found"}) from exc
        raise
    return public_premium_application_status(application)


@app.post("/api/v1/premium/activate")
async def activate_premium_code(request: Request) -> dict[str, object]:
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "invalid_code"}) from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail={"ok": False, "error": "invalid_code"})

    code = normalize_access_code_input(payload.get("code"))
    application_id = sanitize_text(str(payload.get("application_id", "")), 120)
    request_number = normalize_request_number(payload.get("request_number"))
    if not code:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "invalid_code"})

    application: dict[str, object] | None = None
    application_path: Path | None = None
    if request_number:
        application, application_path = find_application_by_request_number("premium", request_number)
        if application is None:
            raise HTTPException(status_code=404, detail={"ok": False, "error": "request_not_found"})
        application_id = str(application.get("id") or "")
    elif application_id:
        try:
            application, application_path = read_application_with_path("premium", application_id)
        except HTTPException as exc:
            if exc.status_code == 404:
                raise HTTPException(status_code=404, detail={"ok": False, "error": "request_not_found"}) from exc
            raise
        application_status = str(application.get("status") or "")
        if application_status == "rejected":
            raise HTTPException(status_code=403, detail={"ok": False, "error": "request_rejected"})

    user = find_user_by_access_code(code)
    if not user:
        if redis_rate_limited(f"premium_code_fail:{client_ip(request)}", 20, 3600):
            raise HTTPException(status_code=429, detail={"ok": False, "error": "rate_limited"})
        raise HTTPException(status_code=404, detail={"ok": False, "error": "invalid_code"})

    expires_at = parse_iso_datetime(user.get("expires_at"))
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail={"ok": False, "error": "expired_code"})
    access_level = str(user.get("access_level") or "free")
    if access_level == "blocked":
        raise HTTPException(status_code=403, detail={"ok": False, "error": "user_blocked"})
    if access_level != "premium":
        raise HTTPException(status_code=400, detail={"ok": False, "error": "invalid_code"})
    if user.get("activated_at"):
        raise HTTPException(status_code=409, detail={"ok": False, "error": "already_used"})

    activated_at = utc_now_iso()

    def mark_activated(current: dict[str, object]) -> dict[str, object]:
        current["activated_at"] = current.get("activated_at") or activated_at
        current["last_seen_at"] = activated_at
        current["uses"] = 1
        if application_id:
            current["activated_application_id"] = application_id
        if request_number:
            current["activated_request_number"] = request_number
        return current

    updated_user = update_user_by_access_code(code, mark_activated) or user

    if application is not None and application_path is not None:
        application["status"] = "activated"
        application["activated_at"] = application.get("activated_at") or activated_at
        application["updated_at"] = activated_at
        application["code_status"] = "activated"
        application["user_id"] = updated_user.get("id")
        with application_path.open("w", encoding="utf-8") as target:
            json.dump(application, target, ensure_ascii=False, indent=2)

    audit_event("premium_code_activated", request, user_id=updated_user.get("id"), application_id=application_id or None)
    current_user = current_user_payload(code, client_ip(request))
    return {
        "ok": True,
        "premium": True,
        "user_id": updated_user.get("id"),
        "access_level": "premium",
        "expires_at": updated_user.get("expires_at"),
        "plan": "STL Master Premium",
        "upload_limit_mb": 300,
        "request_number": request_number or (application.get("request_number") if application else None),
        "current_user": current_user,
        "message": "Premium activated",
    }


@app.post("/api/v1/premium/status")
async def premium_status(request: Request) -> dict[str, object]:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    code = normalize_access_code_input(payload.get("code"))
    if not code:
        current_user = current_user_payload(None, client_ip(request))
        return {"ok": True, "premium": False, "access_level": "free", "current_user": current_user}
    user = find_user_by_access_code(code)
    if not user:
        current_user = current_user_payload(None, client_ip(request))
        current_user["has_access_code"] = True
        return {"ok": True, "premium": False, "access_level": "free", "current_user": current_user}
    beta_access = beta_access_for_code(code, client_ip(request))
    access_level = str(beta_access.get("access_level") or "free")
    activated = bool(user.get("activated_at"))
    current_user = current_user_payload(code, client_ip(request))
    return {
        "ok": True,
        "premium": access_level == "premium" and activated,
        "access_level": access_level,
        "activated": activated,
        "user_id": user.get("id"),
        "expires_at": user.get("expires_at"),
        "plan": "STL Master Premium" if access_level == "premium" else user.get("access_level"),
        "current_user": current_user,
    }


@app.post("/api/v1/feedback")
async def submit_feedback(request: Request) -> dict[str, str]:
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Feedback payload must be JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Feedback payload must be an object")

    rating = sanitize_text(str(payload.get("rating", "")), 40)
    if rating not in {"good", "problem"}:
        raise HTTPException(status_code=400, detail="Feedback rating must be good or problem")

    job_id = sanitize_text(str(payload.get("job_id", "")), 80)
    operations = payload.get("operations")
    if not isinstance(operations, list):
        operations = []
    operations = [sanitize_text(str(operation), 80) for operation in operations if str(operation).strip()]
    if job_id and not operations:
        try:
            client = get_redis()
            job = client.hgetall(job_key(job_id))
            if job.get("operations"):
                decoded_operations = json.loads(job["operations"])
                if isinstance(decoded_operations, list):
                    operations = [
                        sanitize_text(str(operation), 80)
                        for operation in decoded_operations
                        if str(operation).strip()
                    ]
        except (RedisError, json.JSONDecodeError):
            operations = []

    feedback_id = str(uuid4())
    timestamp = utc_now_iso()
    feedback = {
        "feedback_id": feedback_id,
        "created_at": timestamp,
        "timestamp": timestamp,
        "job_id": job_id,
        "operations": operations,
        "rating": rating,
        "comment": sanitize_text(str(payload.get("comment", "")), 2000),
        "contact": sanitize_text(str(payload.get("contact", "")), 180),
        "user_agent": sanitize_text(request.headers.get("user-agent"), 240),
        "is_test": bool(payload.get("is_test") is True),
        "source": sanitize_text(str(payload.get("source", "app")), 80),
        "environment": sanitize_text(str(payload.get("environment", "production")), 80),
        "test_run_id": sanitize_text(str(payload.get("test_run_id", "")), 120),
        "test_name": sanitize_text(str(payload.get("test_name", "")), 120),
    }
    FEEDBACK_ROOT.mkdir(parents=True, exist_ok=True)
    target = FEEDBACK_ROOT / f"{feedback_id}.json"
    with target.open("w", encoding="utf-8") as destination:
        json.dump(feedback, destination, ensure_ascii=False, indent=2)
    log_event("feedback_saved", feedback_id=feedback_id, job_id=feedback["job_id"], rating=rating)
    return {"status": "ok", "feedback_id": feedback_id}


def read_feedback_entries() -> list[dict[str, object]]:
    return [
        {key: value for key, value in entry.items() if key != "_path"}
        for entry in read_feedback_entries_with_paths()
    ]


def is_test_feedback_entry(payload: dict[str, object], job_id: object, comment: object, contact: object) -> bool:
    if payload.get("is_test") is True:
        return True
    if str(payload.get("source") or "").lower() in {"smoke_test", "admin_smoke", "test_fixture"}:
        return True
    if str(payload.get("environment") or "").lower() in {"test", "smoke"}:
        return True
    job_id_text = str(job_id or "").lower()
    comment_text = str(comment or "").lower()
    contact_text = str(contact or "").lower()
    return (
        "smoke" in job_id_text
        or "smoke" in comment_text
        or "example.com" in contact_text
        or "tester@" in contact_text
        or job_id_text.startswith("beta-smoke")
        or job_id_text.startswith("beta-admin-smoke")
    )


def read_feedback_entries_with_paths() -> list[dict[str, object]]:
    if not FEEDBACK_ROOT.exists():
        return []
    entries: list[dict[str, object]] = []
    for item in sorted(FEEDBACK_ROOT.glob("*.json"), reverse=True):
        try:
            with item.open("r", encoding="utf-8") as source:
                payload = json.load(source)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        operations = payload.get("operations")
        if not isinstance(operations, list):
            operations = []
        raw_rating = payload.get("rating", 0)
        if raw_rating == "good":
            rating = 5
        elif raw_rating == "problem":
            rating = 1
        else:
            try:
                rating = int(raw_rating or 0)
            except (TypeError, ValueError):
                rating = 0
        job_id = payload.get("job_id")
        comment = payload.get("comment", "")
        contact = payload.get("contact", "")
        entries.append(
            {
                "timestamp": payload.get("timestamp"),
                "feedback_id": payload.get("feedback_id"),
                "job_id": job_id,
                "operations": [str(operation) for operation in operations],
                "rating": rating,
                "comment": comment,
                "contact": contact,
                "status": payload.get("status", "new"),
                "is_test": is_test_feedback_entry(payload, job_id, comment, contact),
                "source": payload.get("source", "legacy"),
                "environment": payload.get("environment", "unknown"),
                "test_run_id": payload.get("test_run_id"),
                "test_name": payload.get("test_name"),
                "_path": str(item),
            }
        )
    return entries


def summarize_feedback(entries: list[dict[str, object]]) -> dict[str, object]:
    ratings = [int(entry["rating"]) for entry in entries if isinstance(entry.get("rating"), int) and int(entry["rating"]) > 0]
    problems = [entry for entry in entries if int(entry.get("rating", 0) or 0) <= 2]
    positive = [entry for entry in entries if int(entry.get("rating", 0) or 0) >= 4]
    by_operation: dict[str, dict[str, float | int]] = {}
    for entry in entries:
        rating = int(entry.get("rating", 0) or 0)
        for operation in entry.get("operations", []):
            bucket = by_operation.setdefault(str(operation), {"count": 0, "rating_sum": 0.0, "problems": 0, "test": 0, "real": 0})
            bucket["count"] = int(bucket["count"]) + 1
            bucket["rating_sum"] = float(bucket["rating_sum"]) + rating
            if rating <= 2:
                bucket["problems"] = int(bucket["problems"]) + 1
            if entry.get("is_test"):
                bucket["test"] = int(bucket["test"]) + 1
            else:
                bucket["real"] = int(bucket["real"]) + 1
    return {
        "total": len(entries),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
        "problems_count": len(problems),
        "positive_count": len(positive),
        "by_operation": {
            operation: {
                "count": int(stats["count"]),
                "average_rating": round(float(stats["rating_sum"]) / int(stats["count"]), 2) if int(stats["count"]) else 0.0,
                "problems_count": int(stats["problems"]),
                "test_feedback": int(stats["test"]),
                "real_feedback": int(stats["real"]),
            }
            for operation, stats in by_operation.items()
        },
    }


@app.post("/api/v1/admin/login")
async def admin_login(request: Request) -> dict[str, str]:
    ip = client_ip(request)
    lock_key = f"admin_login_lock:{ip}"
    fail_key = f"admin_login_fail:{ip}"
    client = get_redis()
    if client.exists(lock_key):
        audit_event("admin_locked", request)
        raise HTTPException(status_code=429, detail="Too many login attempts")
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Login payload must be JSON") from exc
    password = str(payload.get("password", "")) if isinstance(payload, dict) else ""
    password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    if not password_hash or not verify_password_hash(password, password_hash):
        count = client.incr(fail_key)
        if count == 1:
            client.expire(fail_key, 600)
        if count >= 5:
            client.setex(lock_key, 900, "1")
            audit_event("admin_locked", request)
            raise HTTPException(status_code=429, detail="Too many login attempts")
        audit_event("admin_login_failed", request)
        raise HTTPException(status_code=401, detail="Invalid admin password")
    client.delete(fail_key)
    session = create_admin_session_token()
    audit_event("admin_login_success", request)
    return session


@app.get("/api/v1/admin/security")
def admin_security(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    ip = client_ip(request)
    fail_count = 0
    locked = False
    try:
        client = get_redis()
        fail_count = int(client.get(f"admin_login_fail:{ip}") or 0)
        locked = bool(client.exists(f"admin_login_lock:{ip}"))
    except RedisError:
        pass
    return {
        "admin_auth_enabled": bool(os.getenv("ADMIN_PASSWORD_HASH")),
        "emergency_token_enabled": bool(os.getenv("ADMIN_TOKEN")),
        "failed_login_attempts": fail_count,
        "locked": locked,
        "audit_events": read_audit_events(20),
    }


@app.get("/api/v1/admin/overview")
def admin_overview(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    redis_state = "unavailable"
    queue_snapshot: dict[str, object] = {"queue_size": 0, "queued_jobs": 0, "processing_jobs": 0, "stale_processing_jobs": 0, "completed_24h": 0, "failed_24h": 0, "jobs": []}
    try:
        client = get_redis()
        redis_state = "ok" if client.ping() else "unavailable"
        queue_snapshot = admin_queue_snapshot(client)
    except RedisError:
        pass
    users = read_users()
    applications = read_applications()
    premium_applications = read_applications("premium")
    cleanup = admin_cleanup_status(request, authorization, x_admin_token)
    features_payload = load_features()
    pending = [item for item in applications if str(item.get("status") or "pending") in {"pending", "new"}]
    premium_users = [user for user in users if str(user.get("access_level") or "") == "premium"]
    blocked_users = [user for user in users if str(user.get("access_level") or "") == "blocked"]
    attention: list[dict[str, object]] = []
    if redis_state != "ok":
        attention.append({"type": "redis", "severity": "critical", "title": "Redis недоступен", "target": "queue"})
    if int(queue_snapshot.get("stale_processing_jobs", 0) or 0) > 0:
        attention.append({"type": "stale_jobs", "severity": "warning", "title": "Есть зависшие задания", "target": "queue", "count": queue_snapshot.get("stale_processing_jobs")})
    if pending:
        attention.append({"type": "pending_applications", "severity": "info", "title": "Есть заявки без ответа", "target": "applications", "count": len(pending)})
    if blocked_users:
        attention.append({"type": "blocked_users", "severity": "warning", "title": "Есть заблокированные пользователи", "target": "users", "count": len(blocked_users)})
    return {
        "backend": {"status": "ok", "version": app.version},
        "redis": {"status": redis_state},
        "worker": {"status": "unknown", "note": "heartbeat endpoint is not implemented"},
        "queue": queue_snapshot,
        "users": {"total": len(users), "premium": len(premium_users), "blocked": len(blocked_users)},
        "applications": {
            "total": len(applications),
            "pending": len(pending),
            "premium_pending": len([item for item in premium_applications if str(item.get("status") or "pending") in {"pending", "new"}]),
        },
        "storage": cleanup,
        "features": features_payload,
        "attention": attention,
        "audit_events": read_audit_events(8),
    }


@app.get("/api/v1/admin/premium-codes")
def admin_premium_codes(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    applications_by_user = {str(item.get("user_id") or ""): item for item in read_applications("premium") if item.get("user_id")}
    items: list[dict[str, object]] = []
    for user in read_users():
        if str(user.get("access_level") or "") != "premium" and not user.get("activated_application_id") and not user.get("request_number"):
            continue
        application = applications_by_user.get(str(user.get("id") or ""))
        activated = bool(user.get("activated_at"))
        revoked = str(user.get("access_level") or "") == "blocked"
        items.append({
            "id": user.get("id"),
            "masked_code": "STL-••••-••••-••••" if user.get("has_access_code") or user.get("access_code_hash") else "—",
            "user_id": user.get("id"),
            "application_id": application.get("id") if application else user.get("activated_application_id"),
            "request_number": user.get("request_number") or (application.get("request_number") if application else None),
            "status": "revoked" if revoked else ("activated" if activated else "issued"),
            "created_at": user.get("created_at"),
            "activated_at": user.get("activated_at"),
            "expires_at": user.get("expires_at"),
            "uses": user.get("uses", 0),
            "max_uses": user.get("max_uses", 1),
            "revoked": revoked,
            "revoked_reason": "user_blocked" if revoked else None,
        })
    return {"items": items, "total": len(items)}


@app.get("/api/v1/admin/features")
def admin_features(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    configured = load_features()
    feature_names = {
        "print_repair": "Ремонт сетки",
        "ai_cleanup": "Очистка AI-моделей",
        "local_smoothing": "Выборочное сглаживание",
        "reduce_polygons": "Уменьшение полигонов",
        "split": "Разрез модели",
        "fit_to_bed_split": "Подгонка под печатный стол",
        "pins": "Штифты",
        "magnets": "Магниты",
        "lock": "Замок",
        "slots": "Пазы и направляющие",
        "auto_orientation": "Автоориентация",
        "surface_recovery": "Восстановление поверхности",
        "fix_symmetry": "Исправление симметрии",
    }
    status_labels = {"stable": "Стабильно", "beta": "Бета", "disabled": "Выключено", "unavailable": "Недоступно", "partial": "Частично доступно"}
    feature_ids = [
        "print_repair",
        "ai_cleanup",
        "local_smoothing",
        "reduce_polygons",
        "split",
        "fit_to_bed_split",
        "pins",
        "magnets",
        "lock",
        "slots",
        "auto_orientation",
        "surface_recovery",
        "fix_symmetry",
    ]
    items = []
    for feature_id in feature_ids:
        backend_enabled = bool(configured.get(feature_id, feature_id in {"pins", "magnets", "lock", "slots"} and configured.get("split")))
        worker_available = feature_id not in {"surface_recovery", "fix_symmetry"} or bool(configured.get(feature_id))
        status = "stable" if backend_enabled and worker_available and feature_id not in {"surface_recovery", "fix_symmetry"} else ("beta" if backend_enabled else "disabled")
        reason = "" if backend_enabled and worker_available else "backend_or_worker_not_ready"
        items.append({
            "id": feature_id,
            "name": feature_names.get(feature_id, feature_id.replace("_", " ")),
            "status": status,
            "status_label": status_labels.get(status, status),
            "frontend_visible": backend_enabled,
            "backend_enabled": backend_enabled,
            "worker_available": worker_available,
            "access": "premium" if feature_id in {"surface_recovery", "local_smoothing"} else "free",
            "reason": reason,
        })
    return {"items": items, "total": len(items), "config_path": str(FEATURES_PATH)}


@app.post("/api/v1/admin/test-data/scan")
async def admin_test_data_scan(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    include_items = not isinstance(payload, dict) or payload.get("include_items", True) is not False
    cleanup_run_id = sanitize_text(str(payload.get("test_run_id", "")), 120) if isinstance(payload, dict) else ""
    scan = test_data_scan_payload(include_items=include_items)
    if cleanup_run_id and include_items:
        scan = filter_test_scan_by_run_id(scan, cleanup_run_id)
    audit_event("test_data_scan", request, summary=scan.get("summary"))
    return scan


@app.post("/api/v1/admin/test-data/cleanup")
async def admin_test_data_cleanup(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Cleanup payload must be JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Cleanup payload must be an object")
    if str(payload.get("confirmation") or "") != "УДАЛИТЬ ТЕСТОВЫЕ ДАННЫЕ":
        raise HTTPException(status_code=400, detail="Cleanup requires exact confirmation phrase")
    cleanup_run_id = sanitize_text(str(payload.get("test_run_id", "")), 120)
    scan = test_data_scan_payload(include_items=True)
    if cleanup_run_id:
        scan = filter_test_scan_by_run_id(scan, cleanup_run_id)
    items = scan.get("items") if isinstance(scan.get("items"), dict) else {}
    if not isinstance(items, dict):
        items = {}
    counts = {"feedback": 0, "jobs": 0, "applications": 0, "users": 0, "files": 0, "errors": 0}
    cleanup_id = str(uuid4())
    quarantine = QUARANTINE_ROOT / f"test-data-{cleanup_id}"
    quarantine.mkdir(parents=True, exist_ok=True)

    feedback_ids = {str(item.get("feedback_id") or "") for item in items.get("feedback", []) if isinstance(item, dict)}
    for entry in read_feedback_entries_with_paths():
        if str(entry.get("feedback_id") or "") not in feedback_ids:
            continue
        source = Path(str(entry.get("_path") or ""))
        try:
            FEEDBACK_TEST_ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
            if source.exists() and source.parent == FEEDBACK_ROOT:
                shutil.move(str(source), str(FEEDBACK_TEST_ARCHIVE_ROOT / source.name))
            counts["feedback"] += 1
        except OSError:
            counts["errors"] += 1

    app_ids = {str(item.get("id") or "") for item in items.get("applications", []) if isinstance(item, dict)}
    app_archive = APPLICATIONS_ROOT / "test_archive" / cleanup_id
    for application in read_applications_with_paths():
        if str(application.get("id") or "") not in app_ids:
            continue
        source = Path(str(application.get("_path") or ""))
        try:
            if source.exists() and source.suffix == ".json" and source.parent in {EARLY_ACCESS_APPLICATIONS_ROOT, PREMIUM_APPLICATIONS_ROOT}:
                app_archive.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(app_archive / f"{source.parent.name}-{source.name}"))
            counts["applications"] += 1
        except OSError:
            counts["errors"] += 1

    active = set(active_job_ids())
    job_ids = {str(item.get("job_id") or "") for item in items.get("jobs", []) if isinstance(item, dict)}
    try:
        client = get_redis()
    except RedisError:
        client = None
    for job_id in sorted(job_ids):
        if job_id in active:
            if cleanup_run_id:
                for _ in range(20):
                    time.sleep(0.5)
                    active = set(active_job_ids())
                    if job_id not in active:
                        break
            if job_id in active:
                continue
        try:
            if client is not None:
                client.delete(job_key(job_id))
                remove_job_from_queues(client, job_id)
            for root in (UPLOAD_ROOT, RESULT_ROOT):
                source = root / job_id
                if source.exists() and is_cleanup_path_allowed(source) and not source.is_symlink():
                    target_root = quarantine / root.name
                    target_root.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source), str(target_root / job_id))
                    counts["files"] += 1
            counts["jobs"] += 1
        except (OSError, RedisError):
            counts["errors"] += 1

    test_user_ids = {str(item.get("id") or "") for item in items.get("users", []) if isinstance(item, dict)}
    if test_user_ids:
        users = read_users()
        kept = [user for user in users if str(user.get("id") or "") not in test_user_ids]
        counts["users"] = len(users) - len(kept)
        write_users(kept)

    if not cleanup_run_id and ADMIN_CLEANUP_TEST_ROOT.exists():
        try:
            shutil.rmtree(ADMIN_CLEANUP_TEST_ROOT)
            counts["files"] += 1
        except OSError:
            counts["errors"] += 1

    remaining_scan = test_data_scan_payload(include_items=True)
    if cleanup_run_id:
        remaining_scan = filter_test_scan_by_run_id(remaining_scan, cleanup_run_id)
    audit_event("admin_test_data_cleanup", request, cleanup_id=cleanup_id, counts=counts, quarantine=str(quarantine), test_run_id=cleanup_run_id or None)
    return {
        "ok": counts["errors"] == 0,
        "cleanup_id": cleanup_id,
        "test_run_id": cleanup_run_id or None,
        "counts": counts,
        "quarantine": str(quarantine),
        "remaining": remaining_scan.get("summary"),
        "remaining_test_counts": remaining_scan.get("filtered_test_counts") if cleanup_run_id else None,
    }


@app.post("/api/v1/admin/legacy-data/scan")
async def admin_legacy_data_scan(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    plan = build_legacy_cleanup_plan()
    audit_event("legacy_data_scan", request, plan_id=plan.get("plan_id"), summary=plan.get("summary"))
    return {
        key: value
        for key, value in plan.items()
        if key not in {"jobs", "applications"}
    } | {
        "jobs": plan.get("jobs", [])[:100],
        "applications": plan.get("applications", []),
    }


@app.post("/api/v1/admin/legacy-data/quarantine")
async def admin_legacy_data_quarantine(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Legacy cleanup payload must be JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Legacy cleanup payload must be an object")
    plan = read_admin_plan(str(payload.get("plan_id") or ""))
    if plan.get("type") != "legacy_cleanup":
        raise HTTPException(status_code=400, detail="Plan is not a legacy cleanup plan")
    if str(payload.get("confirmation") or "") != str(plan.get("confirmation_token") or ""):
        raise HTTPException(status_code=400, detail="Legacy cleanup requires exact confirmation token")

    quarantine = Path(str(plan.get("quarantine") or ""))
    if not str(quarantine).startswith(str(QUARANTINE_ROOT)):
        raise HTTPException(status_code=400, detail="Invalid quarantine path")
    quarantine.mkdir(parents=True, exist_ok=True)
    manifest = {
        "cleanup_id": plan.get("cleanup_id"),
        "created_at": utc_now_iso(),
        "plan_id": plan.get("plan_id"),
        "summary_before": plan.get("summary"),
        "jobs": [],
        "applications": [],
        "protected_jobs": [],
        "errors": [],
        "restore_notes": {
            "jobs": "Move job folders from quarantine uploads/results back to /data/uploads/<job_id> and /data/results/<job_id>, then restore Redis hashes from manifest.",
            "applications": "Move application JSON files from quarantine/applications back to the matching /data/results/applications/<kind>/ directory.",
        },
    }
    counts = {"jobs": 0, "applications": 0, "files": 0, "protected": 0, "errors": 0}
    active = set(active_job_ids())
    try:
        client = get_redis()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc
    rel = relation_index()
    test_user_ids: set[str] = rel["test_user_ids"]  # type: ignore[assignment]
    real_user_ids: set[str] = rel["real_user_ids"]  # type: ignore[assignment]
    all_jobs: list[dict[str, object]] = rel["jobs"]  # type: ignore[assignment]
    smoke_windows = smoke_audit_windows()
    series_counts = repeated_job_series_counts(all_jobs)

    planned_job_ids = {str(item.get("job_id") or "") for item in plan.get("jobs", []) if isinstance(item, dict)}
    for job_id in sorted(planned_job_ids):
        try:
            job = client.hgetall(job_key(job_id))
            if not job:
                continue
            job["job_id"] = job_id
            public_job = job_public_payload(job, test_user_ids, real_user_ids, smoke_windows, series_counts)
            status = str(public_job.get("status") or "")
            if job_id in active or status in {"queued", "processing", "stale_processing"}:
                counts["protected"] += 1
                manifest["protected_jobs"].append({"job_id": job_id, "status": status, "reason": "active_or_processing"})
                continue
            if public_job.get("classification") != "legacy_test_candidate":
                counts["protected"] += 1
                manifest["protected_jobs"].append({"job_id": job_id, "status": status, "reason": "classification_changed", "classification": public_job.get("classification")})
                continue
            job_manifest = {
                "job_id": job_id,
                "redis_hash": job,
                "classification_reasons": public_job.get("classification_reasons"),
                "legacy_score": public_job.get("legacy_score"),
                "files": [],
            }
            for root in (UPLOAD_ROOT, RESULT_ROOT):
                source = root / job_id
                if source.exists() and is_cleanup_path_allowed(source) and not source.is_symlink():
                    target_root = quarantine / root.name
                    target_root.mkdir(parents=True, exist_ok=True)
                    target = target_root / job_id
                    shutil.move(str(source), str(target))
                    counts["files"] += 1
                    job_manifest["files"].append({"from": str(source), "to": str(target), "size_bytes": directory_size(target)})
            client.delete(job_key(job_id))
            remove_job_from_queues(client, job_id)
            manifest["jobs"].append(job_manifest)
            counts["jobs"] += 1
        except (OSError, RedisError) as exc:
            counts["errors"] += 1
            manifest["errors"].append({"job_id": job_id, "error": str(exc)})

    planned_app_ids = {str(item.get("id") or "") for item in plan.get("applications", []) if isinstance(item, dict)}
    for application in read_applications_with_paths():
        app_id = str(application.get("id") or "")
        if app_id not in planned_app_ids:
            continue
        classification = classify_application_payload(application)
        if classification["classification"] != "legacy_test_candidate":
            continue
        source = Path(str(application.get("_path") or ""))
        try:
            if source.exists() and source.parent in {EARLY_ACCESS_APPLICATIONS_ROOT, PREMIUM_APPLICATIONS_ROOT}:
                target_root = quarantine / "applications" / source.parent.name
                target_root.mkdir(parents=True, exist_ok=True)
                target = target_root / source.name
                shutil.move(str(source), str(target))
                manifest["applications"].append({
                    "id": app_id,
                    "request_number": application.get("request_number"),
                    "from": str(source),
                    "to": str(target),
                    "classification_reasons": classification.get("reasons"),
                    "legacy_score": classification.get("legacy_score"),
                })
                counts["applications"] += 1
        except OSError as exc:
            counts["errors"] += 1
            manifest["errors"].append({"application_id": app_id, "error": str(exc)})

    manifest["counts"] = counts
    manifest_path = quarantine / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as target:
        json.dump(manifest, target, ensure_ascii=False, indent=2)
    audit_event("legacy_data_quarantined", request, plan_id=plan.get("plan_id"), counts=counts, quarantine=str(quarantine), manifest_path=str(manifest_path))
    return {
        "ok": counts["errors"] == 0,
        "counts": counts,
        "quarantine": str(quarantine),
        "manifest_path": str(manifest_path),
        "remaining": test_data_scan_payload(include_items=False).get("summary"),
    }


@app.get("/api/v1/admin/feedback")
def admin_feedback_list(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> list[dict[str, object]]:
    require_admin_auth(request, authorization, x_admin_token)
    return read_feedback_entries()


@app.get("/api/v1/admin/feedback/summary")
def admin_feedback_summary(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    entries = read_feedback_entries()
    real_entries = [entry for entry in entries if not entry.get("is_test")]
    test_entries = [entry for entry in entries if entry.get("is_test")]
    all_summary = summarize_feedback(entries)
    real_summary = summarize_feedback(real_entries)
    return {
        "total_feedback": len(entries),
        "real_feedback": len(real_entries),
        "test_feedback": len(test_entries),
        "average_rating": real_summary["average_rating"],
        "real_average_rating": real_summary["average_rating"],
        "all_average_rating": all_summary["average_rating"],
        "problems_count": real_summary["problems_count"],
        "real_problems_count": real_summary["problems_count"],
        "test_problems_count": summarize_feedback(test_entries)["problems_count"],
        "positive_count": real_summary["positive_count"],
        "by_operation": all_summary["by_operation"],
        "real_by_operation": real_summary["by_operation"],
        "latest": entries[:10],
        "latest_real": real_entries[:10],
    }


@app.post("/api/v1/admin/feedback/cleanup-test")
def admin_feedback_cleanup_test(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    entries = read_feedback_entries_with_paths()
    FEEDBACK_TEST_ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    archived: list[str] = []
    for entry in entries:
        if not entry.get("is_test"):
            continue
        source = Path(str(entry.get("_path", "")))
        if not source.exists() or source.parent != FEEDBACK_ROOT:
            continue
        target = FEEDBACK_TEST_ARCHIVE_ROOT / source.name
        if target.exists():
            target = FEEDBACK_TEST_ARCHIVE_ROOT / f"{source.stem}-{uuid4().hex[:8]}{source.suffix}"
        shutil.move(str(source), str(target))
        archived.append(source.name)
    return {
        "archived": len(archived),
        "archive": "feedback_test_archive",
        "files": archived,
    }


@app.post("/api/v1/admin/feedback/delete-test")
async def admin_feedback_delete_test(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    selected = {str(item) for item in payload.get("feedback_ids", [])} if isinstance(payload.get("feedback_ids"), list) else set()
    deleted = 0
    for entry in read_feedback_entries_with_paths():
        classification = classify_payload(entry, "feedback", bool(entry.get("is_test")))
        if classification["classification"] != "test":
            continue
        feedback_id = str(entry.get("feedback_id") or "")
        if selected and feedback_id not in selected:
            continue
        source = Path(str(entry.get("_path") or ""))
        if source.exists() and source.parent == FEEDBACK_ROOT:
            FEEDBACK_TEST_ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(FEEDBACK_TEST_ARCHIVE_ROOT / source.name))
            deleted += 1
    audit_event("test_feedback_deleted", request, deleted=deleted)
    return {"ok": True, "deleted": deleted}


@app.get("/api/v1/admin/applications")
def admin_applications_list(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, list[dict[str, object]]]:
    require_admin_auth(request, authorization, x_admin_token)
    def classified(kind: str) -> list[dict[str, object]]:
        rows = []
        for application in read_applications(kind):
            classification = classify_application_payload(application)
            rows.append(application | {
                "classification": classification["classification"],
                "classification_reasons": classification["reasons"],
                "legacy_score": classification.get("legacy_score", 0),
            })
        return rows
    return {
        "early_access": classified("early_access"),
        "premium": classified("premium"),
    }


@app.post("/api/v1/admin/applications/delete-test")
async def admin_applications_delete_test(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    selected = {str(item) for item in payload.get("application_ids", [])} if isinstance(payload.get("application_ids"), list) else set()
    deleted = 0
    archive = APPLICATIONS_ROOT / "test_archive" / str(uuid4())
    for application in read_applications_with_paths():
        classification = classify_payload(application, "application")
        if classification["classification"] != "test":
            continue
        if selected and str(application.get("id") or "") not in selected:
            continue
        source = Path(str(application.get("_path") or ""))
        if source.exists() and source.parent in {EARLY_ACCESS_APPLICATIONS_ROOT, PREMIUM_APPLICATIONS_ROOT}:
            archive.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(archive / f"{source.parent.name}-{source.name}"))
            deleted += 1
    audit_event("test_applications_deleted", request, deleted=deleted, archive=str(archive))
    return {"ok": True, "deleted": deleted, "archive": str(archive)}


@app.post("/api/v1/admin/applications/bulk")
async def admin_applications_bulk(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Тело запроса должно быть JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Тело запроса должно быть объектом")
    action = str(payload.get("action") or "").strip()
    ids = {str(item) for item in payload.get("ids", []) if str(item).strip()} if isinstance(payload.get("ids"), list) else set()
    if not action or not ids:
        raise HTTPException(status_code=400, detail="Нужно указать действие и список заявок")
    premium_days = int(payload.get("premium_days", 30) or 30)
    premium_days = max(1, min(premium_days, 365))
    archive = QUARANTINE_ROOT / f"applications-bulk-{uuid4()}"
    report = {"success": [], "skipped": [], "protected": [], "errors": []}
    users = read_users()
    changed_users = False
    for application in read_applications_with_paths():
        app_id = str(application.get("id") or "")
        if app_id not in ids:
            continue
        source = Path(str(application.get("_path") or ""))
        kind = "premium" if str(application.get("type") or source.parent.name) == "premium" else "early_access"
        try:
            status = str(application.get("status") or "pending")
            if action == "delete":
                if source.exists() and source.parent in {EARLY_ACCESS_APPLICATIONS_ROOT, PREMIUM_APPLICATIONS_ROOT}:
                    target_root = archive / source.parent.name
                    target_root.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source), str(target_root / source.name))
                report["success"].append({"id": app_id, "action": action})
            elif action == "archive":
                application["archived_at"] = utc_now_iso()
                application["status"] = "archived"
                if source.exists():
                    with source.open("w", encoding="utf-8") as target:
                        json.dump(application, target, ensure_ascii=False, indent=2)
                report["success"].append({"id": app_id, "action": action})
            elif action == "reject":
                if status in {"approved", "code_issued", "activated"}:
                    report["protected"].append({"id": app_id, "reason": "заявка уже одобрена"})
                    continue
                application["status"] = "rejected"
                application["rejected_at"] = utc_now_iso()
                application["rejected_reason"] = sanitize_text(str(payload.get("reason") or "Массовое отклонение"), 500)
                if source.exists():
                    with source.open("w", encoding="utf-8") as target:
                        json.dump(application, target, ensure_ascii=False, indent=2)
                report["success"].append({"id": app_id, "action": action})
            elif action == "approve":
                if status not in {"pending", "new"}:
                    report["skipped"].append({"id": app_id, "reason": "заявка уже обработана"})
                    continue
                access_level = "premium" if kind == "premium" else "early_access"
                access_code = generate_unique_premium_access_code() if access_level == "premium" else generate_access_code()
                approved_at = utc_now_iso()
                user = {
                    "id": str(uuid4()),
                    "contact": sanitize_text(str(application.get("email") or application.get("telegram") or application.get("contact") or application.get("client_id") or ""), 180),
                    "name": sanitize_text(str(application.get("name") or ""), 120),
                    "access_level": access_level,
                    "created_at": approved_at,
                    "expires_at": add_days_iso(premium_days if access_level == "premium" else 7),
                    "notes": sanitize_text(f"Массовое одобрение заявки {application.get('request_number') or app_id}", 1000),
                    "jobs_count": 0,
                    "last_seen_at": None,
                    "activated_at": None,
                    "activated_application_id": None,
                    "request_number": application.get("request_number"),
                    "max_uses": 1 if access_level == "premium" else None,
                    "uses": 0,
                    "access_code_hash": hash_access_code(access_code),
                    "is_test": bool(application.get("is_test") is True),
                    "source": sanitize_text(str(application.get("source", "admin")), 80),
                    "environment": sanitize_text(str(application.get("environment", "production")), 80),
                    "test_run_id": sanitize_text(str(application.get("test_run_id", "")), 120),
                    "test_name": sanitize_text(str(application.get("test_name", "")), 120),
                }
                users.append(user)
                changed_users = True
                application["status"] = "code_issued" if access_level == "premium" else "approved"
                application["approved_at"] = approved_at
                application["updated_at"] = approved_at
                application["user_id"] = user["id"]
                application["code_status"] = "issued"
                if source.exists():
                    with source.open("w", encoding="utf-8") as target:
                        json.dump(application, target, ensure_ascii=False, indent=2)
                report["success"].append({"id": app_id, "action": action, "user_id": user["id"], "access_code": access_code, "request_number": application.get("request_number")})
            else:
                raise HTTPException(status_code=400, detail="Неизвестное действие")
        except OSError as exc:
            report["errors"].append({"id": app_id, "error": str(exc)})
    missing = ids - {str(item.get("id") or "") for item in read_applications_with_paths()} - {str(item.get("id") or "") for item in report["success"]}
    for app_id in missing:
        report["skipped"].append({"id": app_id, "reason": "заявка не найдена или уже перенесена"})
    if changed_users:
        write_users(users)
    integrity = admin_integrity_check(auto_fix=True) if action in {"delete", "archive"} else None
    audit_event("applications_bulk", request, action=action, ids=list(ids), report={key: len(value) for key, value in report.items()}, archive=str(archive))
    return {"ok": not report["errors"], "action": action, "report": report, "archive": str(archive), "integrity": integrity}


@app.post("/api/v1/admin/applications/{kind}/{application_id}/approve")
async def admin_application_approve(kind: str, application_id: str, request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    application, path = read_application_with_path(kind, application_id)
    normalized_kind = "premium" if str(application.get("type") or kind) == "premium" else "early_access"
    if normalized_kind == "premium" and str(application.get("status") or "pending") not in {"pending", "new"}:
        raise HTTPException(status_code=409, detail="Premium request is not pending")
    try:
        premium_days = int(payload.get("premium_days", 30) or 30)
    except (TypeError, ValueError):
        premium_days = 30
    premium_days = max(1, min(premium_days, 365))
    expires_at = add_days_iso(premium_days if normalized_kind == "premium" else 7)
    access_level = "premium" if normalized_kind == "premium" else "early_access"
    access_code = generate_unique_premium_access_code() if access_level == "premium" else generate_access_code()
    contact = sanitize_text(str(application.get("email") or application.get("telegram") or application.get("contact") or application.get("client_id") or ""), 180)
    approved_at = utc_now_iso()
    user = {
        "id": str(uuid4()),
        "contact": contact,
        "name": sanitize_text(str(application.get("name") or ""), 120),
        "access_level": access_level,
        "created_at": approved_at,
        "expires_at": expires_at,
        "notes": sanitize_text(f"Заявка {normalized_kind}: {application.get('request_number') or application.get('id')}", 1000),
        "jobs_count": 0,
        "last_seen_at": None,
        "activated_at": None,
        "activated_application_id": None,
        "request_number": application.get("request_number"),
        "max_uses": 1 if access_level == "premium" else None,
        "uses": 0,
        "access_code_hash": hash_access_code(access_code),
        "is_test": bool(application.get("is_test") is True),
        "source": sanitize_text(str(application.get("source", "admin")), 80),
        "environment": sanitize_text(str(application.get("environment", "production")), 80),
        "test_run_id": sanitize_text(str(application.get("test_run_id", "")), 120),
        "test_name": sanitize_text(str(application.get("test_name", "")), 120),
    }
    users = read_users()
    users.append(user)
    write_users(users)

    application["status"] = "code_issued" if normalized_kind == "premium" else "approved"
    application["approved_at"] = approved_at
    application["updated_at"] = approved_at
    if normalized_kind == "premium":
        application["code_issued_at"] = approved_at
        application["code_status"] = "issued"
        application["activated_at"] = None
        application["max_uses"] = 1
    application["user_id"] = user["id"]
    with path.open("w", encoding="utf-8") as target:
        json.dump(application, target, ensure_ascii=False, indent=2)
    audit_event("application_approved", request, application_id=application.get("id"), user_id=user["id"], access_level=access_level)
    return {
        "application": public_application(application),
        "user": public_user(user),
        "access_code": access_code,
        "message": approval_message(access_level, access_code, expires_at),
        "request_number": application.get("request_number"),
    }


@app.post("/api/v1/admin/applications/{kind}/{application_id}/reject")
async def admin_application_reject(kind: str, application_id: str, request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    application, path = read_application_with_path(kind, application_id)
    application["status"] = "rejected"
    application["rejected_at"] = utc_now_iso()
    application["updated_at"] = application["rejected_at"]
    application["rejected_reason"] = sanitize_multiline(str(payload.get("reason", "")), 1000)
    application["approved_at"] = application.get("approved_at")
    with path.open("w", encoding="utf-8") as target:
        json.dump(application, target, ensure_ascii=False, indent=2)
    audit_event("application_rejected", request, application_id=application.get("id"), access_level=str(application.get("type") or kind))
    return {"application": public_application(application)}


@app.get("/api/v1/admin/users")
def admin_users_list(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> list[dict[str, object]]:
    require_admin_auth(request, authorization, x_admin_token)
    return [normalized_user(user) for user in read_users() if not user.get("archived_at")]


@app.post("/api/v1/admin/users/deletion-preview")
async def admin_users_deletion_preview(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Preview payload must be an object")
    user_ids = payload.get("user_ids")
    if not isinstance(user_ids, list):
        user_ids = [payload.get("user_id")]
    plan = build_user_deletion_plan([str(item) for item in user_ids if item], str(payload.get("mode") or "archive"), payload.get("options") if isinstance(payload.get("options"), dict) else {})
    audit_event("user_deletion_preview", request, plan_id=plan.get("plan_id"), user_count=len(plan.get("items", [])), mode=plan.get("mode"))
    return plan


@app.post("/api/v1/admin/users/delete")
async def admin_users_delete(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Delete payload must be an object")
    plan = read_admin_plan(str(payload.get("plan_id") or ""))
    if plan.get("type") != "user_deletion":
        raise HTTPException(status_code=400, detail="Invalid user deletion plan")
    if str(payload.get("confirmation") or "") != str(plan.get("confirmation_token") or ""):
        raise HTTPException(status_code=400, detail="Invalid user deletion confirmation")
    if plan.get("protected_items"):
        raise HTTPException(status_code=409, detail={"error": "active_jobs", "protected_items": plan.get("protected_items")})
    mode = str(plan.get("mode") or "archive")
    selected_ids = {str(item) for item in plan.get("user_ids", []) if str(item)}
    options = plan.get("options") if isinstance(plan.get("options"), dict) else {}
    users = read_users()
    changed = 0
    removed = 0
    now = utc_now_iso()
    if mode == "delete":
        allowed_delete = {str(item.get("user", {}).get("id")) for item in plan.get("items", []) if isinstance(item, dict) and item.get("can_delete_permanently") is True and isinstance(item.get("user"), dict)}
        if selected_ids - allowed_delete:
            raise HTTPException(status_code=400, detail="Permanent deletion is allowed only for confirmed test users")
        users = [user for user in users if str(user.get("id") or "") not in selected_ids]
        removed = len(selected_ids)
    else:
        for user in users:
            if str(user.get("id") or "") in selected_ids:
                user["archived_at"] = now
                user["access_level"] = "blocked"
                if options.get("revoke_codes", True):
                    user["access_code_hash"] = ""
                changed += 1
    write_users(users)
    if mode == "delete":
        try:
            client = get_redis()
        except RedisError:
            client = None
        for item in plan.get("items", []):
            if not isinstance(item, dict) or not isinstance(item.get("user"), dict):
                continue
            user_id = str(item["user"].get("id") or "")
            if user_id not in selected_ids:
                continue
            for job in item.get("jobs", []) if isinstance(item.get("jobs"), list) else []:
                if not isinstance(job, dict):
                    continue
                job_id = str(job.get("job_id") or "")
                if client is not None:
                    try:
                        client.delete(job_key(job_id))
                        remove_job_from_queues(client, job_id)
                    except RedisError:
                        pass
                for root, flag in [(UPLOAD_ROOT, "delete_uploads"), (RESULT_ROOT, "delete_results")]:
                    path = root / job_id
                    if options.get(flag) and path.exists() and is_cleanup_path_allowed(path) and not path.is_symlink():
                        shutil.rmtree(path, ignore_errors=True)
            if options.get("delete_feedback"):
                for entry in item.get("feedback", []) if isinstance(item.get("feedback"), list) else []:
                    source = Path(str(entry.get("_path") or ""))
                    if source.exists() and source.parent == FEEDBACK_ROOT:
                        source.unlink(missing_ok=True)
    audit_event("user_deletion_executed", request, mode=mode, user_ids=list(selected_ids), changed=changed, removed=removed)
    return {"ok": True, "mode": mode, "archived": changed, "removed": removed, "users": [normalized_user(user) for user in read_users() if not user.get("archived_at")]}


def user_related_stats(user_id: str, rel: dict[str, object] | None = None) -> dict[str, object]:
    rel = rel or relation_index()
    job_by_user: dict[str, list[dict[str, object]]] = rel["job_by_user"]  # type: ignore[assignment]
    feedback_by_job: dict[str, list[dict[str, object]]] = rel["feedback_by_job"]  # type: ignore[assignment]
    users = rel["users"]  # type: ignore[assignment]
    user = next((item for item in users if str(item.get("id") or "") == user_id), {})
    jobs = job_by_user.get(user_id, [])
    job_ids = [str(job.get("job_id") or "") for job in jobs if str(job.get("job_id") or "")]
    upload_bytes = sum(directory_size(UPLOAD_ROOT / job_id) for job_id in job_ids)
    result_bytes = sum(directory_size(RESULT_ROOT / job_id) for job_id in job_ids)
    feedback_count = sum(len(feedback_by_job.get(job_id, [])) for job_id in job_ids)
    return {
        "jobs": len(job_ids),
        "premium": 1 if user.get("access_code_hash") or user.get("access_level") == "premium" else 0,
        "feedback": feedback_count,
        "uploads": upload_bytes,
        "results": result_bytes,
        "bytes": upload_bytes + result_bytes,
    }


@app.post("/api/v1/admin/users/bulk")
async def admin_users_bulk(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Тело запроса должно быть JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Тело запроса должно быть объектом")
    action = str(payload.get("action") or "").strip()
    ids = [str(item) for item in payload.get("ids", []) if str(item).strip()] if isinstance(payload.get("ids"), list) else []
    if not action or not ids:
        raise HTTPException(status_code=400, detail="Нужно указать действие и список пользователей")
    deletion_actions = {"delete", "delete_with_jobs", "delete_with_premium", "delete_with_feedback", "delete_with_all"}
    if action in deletion_actions and str(payload.get("confirmation") or "") != "УДАЛИТЬ ПОЛЬЗОВАТЕЛЕЙ":
        raise HTTPException(status_code=400, detail="Для удаления нужно точное подтверждение")
    premium_days = int(payload.get("premium_days", 30) or 30)
    premium_days = max(1, min(premium_days, 365))
    now = utc_now_iso()
    selected = set(ids)
    users = read_users()
    rel = relation_index()
    job_by_user: dict[str, list[dict[str, object]]] = rel["job_by_user"]  # type: ignore[assignment]
    app_by_user: dict[str, list[dict[str, object]]] = rel["app_by_user"]  # type: ignore[assignment]
    report = {"success": [], "skipped": [], "protected": [], "errors": []}
    deleted_stats = {"jobs": 0, "premium": 0, "feedback": 0, "uploads": 0, "results": 0, "bytes": 0}
    changed = False
    try:
        client = get_redis()
    except RedisError:
        client = None
    quarantine = QUARANTINE_ROOT / f"users-bulk-{uuid4()}"
    issued_code_hashes = {str(user.get("access_code_hash") or "") for user in users if user.get("access_code_hash")}

    for user in users:
        user_id = str(user.get("id") or "")
        if user_id not in selected:
            continue
        try:
            if action == "block":
                user["access_level"] = "blocked"
                user["blocked_at"] = now
                changed = True
                report["success"].append({"id": user_id, "action": action})
            elif action == "unblock":
                user["access_level"] = "free"
                user.pop("blocked_at", None)
                user["unblocked_at"] = now
                changed = True
                report["success"].append({"id": user_id, "action": action})
            elif action == "grant_premium":
                access_code = ""
                for _ in range(40):
                    candidate = generate_premium_access_code()
                    candidate_hash = hash_access_code(candidate)
                    if candidate_hash not in issued_code_hashes:
                        access_code = candidate
                        issued_code_hashes.add(candidate_hash)
                        break
                if not access_code:
                    raise HTTPException(status_code=500, detail="Не удалось создать уникальный код")
                user["access_level"] = "premium"
                user["expires_at"] = add_days_iso(premium_days)
                user["access_code_hash"] = hash_access_code(access_code)
                user["max_uses"] = 1
                user["uses"] = 0
                changed = True
                report["success"].append({"id": user_id, "action": action, "access_code": access_code})
            elif action == "remove_premium":
                user["access_level"] = "free"
                user["expires_at"] = None
                user["access_code_hash"] = ""
                user["max_uses"] = None
                user["uses"] = 0
                changed = True
                report["success"].append({"id": user_id, "action": action})
            elif action in deletion_actions:
                stats = user_related_stats(user_id, rel)
                for key in deleted_stats:
                    deleted_stats[key] += int(stats.get(key, 0) or 0)
                if action in {"delete_with_jobs", "delete_with_all"} and client is not None:
                    for job in job_by_user.get(user_id, []):
                        job_id = str(job.get("job_id") or "")
                        if job_id:
                            force_delete_job(client, job_id, quarantine / "jobs")
                if action in {"delete_with_feedback", "delete_with_all"}:
                    for job in job_by_user.get(user_id, []):
                        job_id = str(job.get("job_id") or "")
                        if job_id:
                            delete_feedback_for_job(job_id, quarantine)
                if action in {"delete_with_premium", "delete_with_all", "delete"}:
                    user["access_code_hash"] = ""
                    user["max_uses"] = None
                    user["uses"] = 0
                for application in app_by_user.get(user_id, []):
                    source = Path(str(application.get("_path") or ""))
                    if source.exists() and source.parent in {EARLY_ACCESS_APPLICATIONS_ROOT, PREMIUM_APPLICATIONS_ROOT}:
                        target_root = quarantine / "applications" / source.parent.name
                        target_root.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(source), str(target_root / source.name))
                user["deleted_at"] = now
                user["archived_at"] = now
                user["access_level"] = "blocked"
                changed = True
                report["success"].append({"id": user_id, "action": action, "stats": stats})
            else:
                raise HTTPException(status_code=400, detail="Неизвестное действие")
        except (OSError, RedisError) as exc:
            report["errors"].append({"id": user_id, "error": str(exc)})

    processed = {str(item.get("id") or "") for item in report["success"]}
    for missing_id in selected - processed:
        if not any(str(item.get("id") or "") == missing_id for item in users):
            report["skipped"].append({"id": missing_id, "reason": "пользователь не найден"})
    if action in deletion_actions:
        users = [user for user in users if str(user.get("id") or "") not in processed]
        changed = True
    if changed:
        write_users(users)
    integrity = admin_integrity_check(auto_fix=True) if action in deletion_actions else None
    audit_event("users_bulk", request, action=action, ids=ids, report={key: len(value) for key, value in report.items()}, deleted_stats=deleted_stats, quarantine=str(quarantine))
    return {
        "ok": not report["errors"],
        "action": action,
        "report": report,
        "deleted_stats": deleted_stats,
        "quarantine": str(quarantine),
        "integrity": integrity,
        "users": [normalized_user(user) for user in read_users() if not user.get("archived_at")],
    }


@app.post("/api/v1/admin/users")
async def admin_users_create(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="User payload must be an object")
    contact = sanitize_text(str(payload.get("contact", "")), 180)
    if not contact:
        raise HTTPException(status_code=400, detail="contact is required")
    access_code = generate_access_code()
    user = {
        "id": str(uuid4()),
        "contact": contact,
        "name": sanitize_text(str(payload.get("name", "")), 120),
        "access_level": str(payload.get("access_level") or "free") if str(payload.get("access_level") or "free") in {"free", "early_access", "premium", "blocked"} else "free",
        "created_at": utc_now_iso(),
        "expires_at": sanitize_text(str(payload.get("expires_at", "")), 80) or None,
        "notes": sanitize_text(str(payload.get("notes", "")), 1000),
        "jobs_count": 0,
        "last_seen_at": None,
        "access_code_hash": hash_access_code(access_code),
        "is_test": bool(payload.get("is_test") is True),
        "source": sanitize_text(str(payload.get("source", "admin")), 80),
        "environment": sanitize_text(str(payload.get("environment", "production")), 80),
        "test_run_id": sanitize_text(str(payload.get("test_run_id", "")), 120),
        "test_name": sanitize_text(str(payload.get("test_name", "")), 120),
    }
    users = read_users()
    users.append(user)
    write_users(users)
    audit_event("user_created", request, user_id=user["id"])
    return public_user(user, access_code)


def update_user(user_id: str, updater) -> dict[str, object]:
    users = read_users()
    for index, user in enumerate(users):
        if user.get("id") == user_id:
            users[index] = updater(user)
            write_users(users)
            return public_user(users[index])
    raise HTTPException(status_code=404, detail="User not found")


@app.patch("/api/v1/admin/users/{user_id}")
async def admin_users_patch(user_id: str, request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="User payload must be an object")

    def apply_patch(user: dict[str, object]) -> dict[str, object]:
        for key in ["contact", "name", "expires_at", "notes"]:
            if key in payload:
                user[key] = sanitize_text(str(payload.get(key, "")), 1000 if key == "notes" else 180) or (None if key == "expires_at" else "")
        if payload.get("access_level") in {"free", "early_access", "premium", "blocked"}:
            user["access_level"] = payload["access_level"]
        return user

    return update_user(user_id, apply_patch)


@app.post("/api/v1/admin/users/{user_id}/premium")
async def admin_users_premium(user_id: str, request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    expires_at = sanitize_text(str(payload.get("expires_at", "")), 80) if isinstance(payload, dict) else ""
    audit_event("user_premium_granted", request, user_id=user_id)
    return update_user(user_id, lambda user: {**user, "access_level": "premium", "expires_at": expires_at or user.get("expires_at")})


@app.post("/api/v1/admin/users/{user_id}/block")
def admin_users_block(user_id: str, request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    audit_event("user_blocked", request, user_id=user_id)
    return update_user(user_id, lambda user: {**user, "access_level": "blocked"})


@app.post("/api/v1/admin/users/{user_id}/unblock")
def admin_users_unblock(user_id: str, request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    audit_event("user_unblocked", request, user_id=user_id)
    return update_user(user_id, lambda user: {**user, "access_level": "free"})


@app.post("/api/v1/admin/users/{user_id}/reset-code")
def admin_users_reset_code(user_id: str, request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    existing = next((user for user in read_users() if user.get("id") == user_id), None)
    access_code = generate_unique_premium_access_code() if existing and existing.get("access_level") == "premium" else generate_access_code()
    audit_event("access_code_reset", request, user_id=user_id)
    return update_user(user_id, lambda user: {**user, "access_code_hash": hash_access_code(access_code), "activated_at": None, "activated_application_id": None, "uses": 0}) | {"access_code": access_code}


@app.get("/api/v1/admin/cleanup/status")
def admin_cleanup_status(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    disk = shutil.disk_usage("/")
    active = active_job_ids()
    return {
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
            "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
        },
        "uploads_size_bytes": directory_size(UPLOAD_ROOT),
        "results_size_bytes": directory_size(RESULT_ROOT),
        "feedback_size_bytes": directory_size(FEEDBACK_ROOT),
        "users_size_bytes": directory_size(USERS_ROOT),
        "quarantine_size_bytes": directory_size(QUARANTINE_ROOT),
        "tests_results_size_bytes": directory_size(Path("/app/tests/results")),
        "job_dirs": {
            "uploads": len([item for item in UPLOAD_ROOT.iterdir() if item.is_dir()]) if UPLOAD_ROOT.exists() else 0,
            "results": len([item for item in RESULT_ROOT.iterdir() if item.is_dir() and item.name not in {"feedback", "feedback_test_archive", "users"}]) if RESULT_ROOT.exists() else 0,
        },
        "active_jobs": active,
    }


@app.post("/api/v1/admin/cleanup/scan")
async def admin_cleanup_scan(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    try:
        older_than_hours = float(payload.get("older_than_hours", 6) or 6)
    except (TypeError, ValueError):
        older_than_hours = 6
    older_than_hours = max(1, min(older_than_hours, 24 * 90))
    plan = build_cleanup_plan(older_than_hours)
    audit_event("cleanup_scan", request, scan_id=plan.get("scan_id"), items=len(plan.get("items", [])), total_size_bytes=plan.get("total_size_bytes"))
    return plan


@app.post("/api/v1/admin/cleanup/execute")
async def admin_cleanup_execute(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Cleanup payload must be JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Cleanup payload must be an object")
    scan_id = sanitize_text(str(payload.get("scan_id", "")), 80)
    selected = payload.get("item_ids")
    selected_ids = {str(item) for item in selected} if isinstance(selected, list) else set()
    confirmation_token = str(payload.get("confirmation_token") or "")
    if not scan_id:
        raise HTTPException(status_code=400, detail="scan_id is required")
    return execute_cleanup_plan(scan_id, selected_ids, confirmation_token, request)


@app.post("/api/v1/admin/cleanup/run")
async def admin_cleanup_run(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    try:
        older_than_hours = float(payload.get("older_than_hours", 6) or 6)
    except (TypeError, ValueError):
        older_than_hours = 6
    dry_run = payload.get("dry_run", True) is not False
    plan = build_cleanup_plan(max(1, min(older_than_hours, 24 * 90)))
    candidates = plan.get("items", []) if isinstance(plan.get("items"), list) else []
    result = {
        "dry_run": dry_run,
        "would_delete": len(candidates),
        "would_free_mb": round(int(plan.get("total_size_bytes", 0) or 0) / 1024 / 1024, 2),
        "deleted": 0,
        "freed_mb": 0,
        "skipped_active_jobs": active_job_ids(),
        "scan_id": plan.get("scan_id"),
        "confirmation_token": plan.get("confirmation_token"),
        "protected_count": plan.get("protected_count", 0),
    }
    if not dry_run:
        confirmation_token = str(payload.get("confirmation_token") or "")
        if confirmation_token != str(plan.get("confirmation_token") or ""):
            raise HTTPException(status_code=400, detail="Real cleanup requires confirmation_token from scan")
        execution = execute_cleanup_plan(str(plan.get("scan_id")), {str(item.get("id")) for item in candidates if isinstance(item, dict)}, confirmation_token, request)
        result.update(execution)
    audit_event("cleanup_run", request, dry_run=dry_run, deleted=result.get("deleted"), freed_mb=result["freed_mb"], scan_id=result.get("scan_id"))
    return result


def remove_empty_cleanup_dirs() -> dict[str, object]:
    removed = 0
    errors: list[dict[str, str]] = []
    for root in (UPLOAD_ROOT, RESULT_ROOT, ADMIN_CLEANUP_TEST_ROOT):
        if not root.exists():
            continue
        for current_root, dirs, files in os.walk(root, topdown=False):
            path = Path(current_root)
            if path == root or not is_cleanup_path_allowed(path) or path.is_symlink():
                continue
            try:
                if not dirs and not files and not any(path.iterdir()):
                    path.rmdir()
                    removed += 1
            except OSError as exc:
                errors.append({"path": masked_path(path), "error": str(exc)})
    return {"removed": removed, "errors": errors}


def clear_quarantine_root() -> dict[str, object]:
    QUARANTINE_ROOT.mkdir(parents=True, exist_ok=True)
    freed_bytes = directory_size(QUARANTINE_ROOT)
    deleted_entries = 0
    errors: list[dict[str, str]] = []
    for item in list(QUARANTINE_ROOT.iterdir()):
        try:
            if item.is_symlink():
                errors.append({"path": str(item), "error": "символические ссылки в карантине не удаляются автоматически"})
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            deleted_entries += 1
        except OSError as exc:
            errors.append({"path": str(item), "error": str(exc)})
    QUARANTINE_ROOT.mkdir(parents=True, exist_ok=True)
    return {"deleted_entries": deleted_entries, "freed_bytes": freed_bytes, "errors": errors}


@app.post("/api/v1/admin/system-cleanup")
async def admin_system_cleanup(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    actions = [str(item) for item in payload.get("actions", []) if str(item).strip()] if isinstance(payload.get("actions"), list) else []
    if not actions:
        raise HTTPException(status_code=400, detail="Нужно указать действия очистки")
    result: dict[str, object] = {"ok": True, "actions": {}, "freed_bytes": 0}
    for action in actions:
        try:
            if action == "orphan_files":
                plan = build_cleanup_plan(6)
                candidates = [item for item in plan.get("items", []) if isinstance(item, dict) and item.get("safe_to_delete")]
                execution = execute_cleanup_plan(str(plan.get("scan_id")), {str(item.get("id")) for item in candidates}, str(plan.get("confirmation_token")), request)
                result["actions"][action] = execution  # type: ignore[index]
                result["freed_bytes"] = int(result.get("freed_bytes", 0) or 0) + int(execution.get("freed_bytes", 0) or 0)
            elif action == "empty_dirs":
                result["actions"][action] = remove_empty_cleanup_dirs()  # type: ignore[index]
            elif action == "redis":
                result["actions"][action] = admin_integrity_check(auto_fix=True)  # type: ignore[index]
            elif action == "stale_jobs":
                client = get_redis()
                quarantine = QUARANTINE_ROOT / f"stale-jobs-{uuid4()}"
                deleted: list[str] = []
                protected: list[dict[str, str]] = []
                for key in client.keys("stl:job:*"):
                    job_id = key.rsplit(":", 1)[-1]
                    job = client.hgetall(key)
                    stale = job.get("status") == "stale_processing" or (job.get("status") == "processing" and not is_fresh_processing_job(job))
                    if not stale:
                        continue
                    diagnostics = job_runtime_diagnostics(client, job_id, job)
                    if diagnostics.get("lock_status") == "locked":
                        protected.append({"id": job_id, "reason": "есть блокировка"})
                        continue
                    force_delete_job(client, job_id, quarantine)
                    deleted.append(job_id)
                result["actions"][action] = {"deleted": len(deleted), "protected": protected, "quarantine": str(quarantine)}  # type: ignore[index]
            elif action == "quarantine":
                if str(payload.get("confirmation") or "") != "ОЧИСТИТЬ КАРАНТИН":
                    raise HTTPException(status_code=400, detail="Для очистки карантина нужно точное подтверждение")
                cleanup = clear_quarantine_root()
                result["actions"][action] = cleanup  # type: ignore[index]
                result["freed_bytes"] = int(result.get("freed_bytes", 0) or 0) + int(cleanup.get("freed_bytes", 0) or 0)
            elif action in {"cache", "temp"}:
                result["actions"][action] = {"skipped": True, "reason": "операция требует отдельного подтверждения"}  # type: ignore[index]
            else:
                result["actions"][action] = {"skipped": True, "reason": "неизвестное действие"}  # type: ignore[index]
        except (OSError, RedisError) as exc:
            result["ok"] = False
            result["actions"][action] = {"error": str(exc)}  # type: ignore[index]
    result["integrity"] = admin_integrity_check(auto_fix=True)
    audit_event("system_cleanup", request, actions=actions, ok=result.get("ok"), freed_bytes=result.get("freed_bytes"))
    return result


@app.get("/api/v1/admin/queue")
def admin_queue(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        client = get_redis()
        return admin_queue_snapshot(client)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc


@app.post("/api/v1/admin/integrity-check")
async def admin_integrity_check_endpoint(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    result = admin_integrity_check(auto_fix=bool(payload.get("auto_fix")))
    audit_event("integrity_check", request, auto_fix=bool(payload.get("auto_fix")), summary=result.get("summary"))
    return result


@app.post("/api/v1/admin/jobs/bulk")
async def admin_jobs_bulk(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Тело запроса должно быть JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Тело запроса должно быть объектом")
    action = str(payload.get("action") or "").strip()
    job_ids = [str(item) for item in payload.get("ids", []) if str(item).strip()] if isinstance(payload.get("ids"), list) else []
    if not action or not job_ids:
        raise HTTPException(status_code=400, detail="Нужно указать действие и список заданий")
    if action == "force_delete" and str(payload.get("confirmation") or "") != "ПРИНУДИТЕЛЬНО УДАЛИТЬ":
        raise HTTPException(status_code=400, detail="Для принудительного удаления нужно точное подтверждение")
    try:
        client = get_redis()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis недоступен") from exc
    quarantine = QUARANTINE_ROOT / f"jobs-bulk-{uuid4()}"
    report = {"success": [], "skipped": [], "protected": [], "errors": []}
    for job_id in job_ids:
        try:
            key = job_key(job_id)
            job = client.hgetall(key)
            if not job:
                report["skipped"].append({"id": job_id, "reason": "задание не найдено"})
                continue
            status = str(job.get("status") or "")
            if action == "release_lock":
                removed = []
                for lock_key in job_lock_keys(job_id):
                    if client.exists(lock_key):
                        client.delete(lock_key)
                        removed.append(lock_key)
                client.hset(key, mapping={"locked": "false", "message": "Lock освобождён администратором.", "updated_at": utc_now_iso()})
                report["success"].append({"id": job_id, "action": action, "removed_locks": removed})
            elif action == "retry":
                if status in {"queued", "processing"}:
                    report["protected"].append({"id": job_id, "reason": "задание уже активно"})
                    continue
                client.hset(key, mapping={"status": "queued", "progress": 0, "message": "Повторная обработка поставлена администратором.", "queued_at": utc_now_iso(), "cancel_requested": "false"})
                enqueue_job(client, job_id, str(job.get("priority") or queue_priority_for_access(job.get("access_level"))))
                report["success"].append({"id": job_id, "action": action})
            elif action == "delete":
                allowed, reason = job_can_regular_delete(client, job_id, job)
                if not allowed:
                    report["protected"].append({"id": job_id, "reason": reason})
                    continue
                manifest = force_delete_job(client, job_id, quarantine)
                report["success"].append({"id": job_id, "action": action, "manifest": manifest})
            elif action == "force_delete":
                manifest = force_delete_job(client, job_id, quarantine)
                report["success"].append({"id": job_id, "action": action, "manifest": manifest})
            elif action == "quarantine":
                allowed, reason = job_can_regular_delete(client, job_id, job)
                if not allowed:
                    report["protected"].append({"id": job_id, "reason": reason})
                    continue
                manifest = force_delete_job(client, job_id, quarantine)
                report["success"].append({"id": job_id, "action": action, "manifest": manifest})
            else:
                raise HTTPException(status_code=400, detail="Неизвестное действие")
        except (OSError, RedisError) as exc:
            report["errors"].append({"id": job_id, "error": str(exc)})
    integrity = admin_integrity_check(auto_fix=True) if action in {"delete", "force_delete", "quarantine"} else None
    audit_event("jobs_bulk", request, action=action, ids=job_ids, report={key: len(value) for key, value in report.items()}, quarantine=str(quarantine))
    return {"ok": not report["errors"], "action": action, "report": report, "quarantine": str(quarantine), "integrity": integrity}


@app.post("/api/v1/admin/jobs/delete-test")
async def admin_jobs_delete_test(request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    selected = {str(item) for item in payload.get("job_ids", [])} if isinstance(payload.get("job_ids"), list) else set()
    active = set(active_job_ids())
    try:
        client = get_redis()
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc
    deleted = 0
    skipped_active = 0
    files = 0
    quarantine = QUARANTINE_ROOT / f"test-jobs-{uuid4()}"
    for job in safe_job_records(client):
        public_job = job_public_payload(job)
        job_id = str(public_job.get("job_id") or "")
        if public_job.get("classification") != "test":
            continue
        if selected and job_id not in selected:
            continue
        if job_id in active or public_job.get("active"):
            skipped_active += 1
            continue
        client.delete(job_key(job_id))
        remove_job_from_queues(client, job_id)
        for root in (UPLOAD_ROOT, RESULT_ROOT):
            source = root / job_id
            if source.exists() and is_cleanup_path_allowed(source) and not source.is_symlink():
                target_root = quarantine / root.name
                target_root.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(target_root / job_id))
                files += 1
        deleted += 1
    audit_event("test_jobs_deleted", request, deleted=deleted, files=files, skipped_active=skipped_active, quarantine=str(quarantine))
    return {"ok": True, "deleted": deleted, "files": files, "skipped_active": skipped_active, "quarantine": str(quarantine)}


@app.post("/api/v1/admin/jobs/{job_id}/cancel")
def admin_cancel_job(job_id: str, request: Request, authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, object]:
    require_admin_auth(request, authorization, x_admin_token)
    try:
        client = get_redis()
        key = job_key(job_id)
        job = client.hgetall(key)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        status = job.get("status")
        if status == "queued":
            remove_job_from_queues(client, job_id)
            client.hset(key, mapping={
                "status": "cancelled",
                "progress": 0,
                "message": "Задача отменена администратором.",
                "cancelled_at": utc_now_iso(),
            })
            audit_event("job_cancelled", request, job_id=job_id, previous_status=status)
            return {"job_id": job_id, "status": "cancelled", "cancel_requested": False}
        if status == "processing":
            client.hset(key, mapping={
                "cancel_requested": "true",
                "message": "Запрошена отмена задачи. Обработка остановится между этапами.",
            })
            audit_event("job_cancel_requested", request, job_id=job_id)
            return {"job_id": job_id, "status": "processing", "cancel_requested": True}
        return {"job_id": job_id, "status": status, "cancel_requested": False}
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc


@app.post("/api/v1/jobs/upload")
def upload_stl(
    request: Request,
    file: UploadFile = File(...),
    operations: str | None = Form(None),
    reduction_percent: int | str | None = Form(None),
    split_axis: str | None = Form(None),
    split_parts: int | str | None = Form(None),
    split_mode: str | None = Form(None),
    split_engine: str | None = Form(None),
    split_plane_offset_mm: int | float | str | None = Form(None),
    connector_size_mm: int | str | None = Form(None),
    connector_clearance_mm: float | str | None = Form(None),
    connector_count: int | str | None = Form(None),
    connector_depth_mm: int | float | str | None = Form(None),
    connector_wall_thickness_mm: int | float | str | None = Form(None),
    magnet_size: str | None = Form(None),
    magnet_diameter_mm: int | float | str | None = Form(None),
    magnet_thickness_mm: int | float | str | None = Form(None),
    lock_profile: str | None = Form(None),
    ai_cleanup_strength: str | None = Form(None),
    artifact_cleanup_strength: str | None = Form(None),
    model_improvement_strength: str | None = Form(None),
    model_name: str | None = Form(None),
    vehicle_name: str | None = Form(None),
    symmetry_axis: str | None = Form(None),
    symmetry_mode: str | None = Form(None),
    apply_orientation: bool | str | None = Form(None),
    orientation_transform: str | None = Form(None),
    auto_orientation: bool | str | None = Form(None),
    orientation_priority: str | None = Form(None),
    fit_to_bed: bool | str | None = Form(None),
    bed_size_x: int | float | str | None = Form(None),
    bed_size_y: int | float | str | None = Form(None),
    bed_size_z: int | float | str | None = Form(None),
    bed_connector_mode: str | None = Form(None),
    bed_connector_clearance_mm: float | str | None = Form(None),
    local_selection: str | None = Form(None),
    is_test: bool | str | None = Form(None),
    source: str | None = Form(None),
    environment: str | None = Form(None),
    test_run_id: str | None = Form(None),
    test_name: str | None = Form(None),
    x_beta_access_code: str | None = Header(default=None, alias="X-Beta-Access-Code"),
) -> dict[str, object]:
    request_id = str(uuid4())
    selected_operations = parse_operations(operations)
    request_ip = client_ip(request)
    beta_access = beta_access_for_code(x_beta_access_code, request_ip)
    if not x_beta_access_code and not is_local_ip(request_ip):
        raise HTTPException(status_code=403, detail="Для обработки собственных STL нужен ранний доступ или Premium.")
    if x_beta_access_code and beta_access.get("user") is None:
        raise HTTPException(status_code=403, detail="Код доступа не найден или истёк.")
    if beta_access["access_level"] == "blocked":
        raise HTTPException(status_code=403, detail="Доступ ограничен.")
    if beta_access["access_level"] == "expired":
        raise HTTPException(status_code=403, detail="Срок действия кода доступа истёк.")
    try:
        client = get_redis()
        queue_owner, queue_priority = enforce_queue_limits(client, beta_access, request_ip, selected_operations)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc
    active_upload_limit = int(beta_access["upload_limit_bytes"])
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            content_length_value = int(content_length)
        except ValueError:
            content_length_value = 0
        if content_length_value > active_upload_limit + 1024 * 1024:
            log_event("upload_rejected_content_length", request_id=request_id, content_length=content_length_value)
            raise HTTPException(status_code=413, detail=upload_limit_message(active_upload_limit))

    original_filename = file.filename or "input.stl"
    if not original_filename.lower().endswith(".stl"):
        log_event("upload_rejected_extension", request_id=request_id, original_filename=original_filename)
        raise HTTPException(status_code=400, detail="Разрешены только файлы .stl")
    safe_filename = sanitize_filename(original_filename)

    selected_reduction_percent = parse_reduction_percent(reduction_percent)
    selected_split_axis = parse_split_axis(split_axis)
    selected_split_parts = parse_split_parts(split_parts)
    selected_split_mode = parse_split_mode(split_mode)
    selected_split_engine = parse_split_engine(split_engine)
    selected_split_plane_offset = parse_split_plane_offset(split_plane_offset_mm)
    selected_connector_size = parse_connector_size(connector_size_mm)
    selected_connector_clearance = parse_connector_clearance(connector_clearance_mm)
    selected_connector_count = parse_connector_count(connector_count)
    selected_connector_depth = parse_connector_depth(connector_depth_mm)
    selected_connector_wall_thickness = parse_connector_wall_thickness(connector_wall_thickness_mm)
    selected_magnet_size, default_magnet_diameter, default_magnet_thickness = parse_magnet_size(magnet_size)
    selected_magnet_diameter = float(magnet_diameter_mm or default_magnet_diameter)
    selected_magnet_thickness = float(magnet_thickness_mm or default_magnet_thickness)
    if selected_magnet_diameter < 3 or selected_magnet_diameter > 20:
        raise HTTPException(status_code=400, detail="magnet_diameter_mm must be between 3 and 20")
    if selected_magnet_thickness < 1 or selected_magnet_thickness > 10:
        raise HTTPException(status_code=400, detail="magnet_thickness_mm must be between 1 and 10")
    selected_lock_profile = (lock_profile or "tongue_groove").strip().lower()
    if selected_lock_profile not in {"tongue_groove", "dovetail", "wave"}:
        selected_lock_profile = "tongue_groove"
    selected_ai_cleanup_strength = parse_ai_cleanup_strength(ai_cleanup_strength)
    selected_artifact_cleanup_strength = parse_artifact_cleanup_strength(artifact_cleanup_strength)
    selected_model_improvement_strength = parse_model_improvement_strength(model_improvement_strength)
    selected_model_name = sanitize_text(model_name or vehicle_name)
    selected_symmetry_axis = parse_symmetry_axis(symmetry_axis)
    selected_symmetry_mode = parse_symmetry_mode(symmetry_mode)
    selected_apply_orientation = parse_bool(apply_orientation, "apply_orientation" in selected_operations)
    selected_orientation_transform = parse_orientation_transform(orientation_transform)
    if selected_apply_orientation and "apply_orientation" not in selected_operations:
        selected_operations.append("apply_orientation")
    selected_auto_orientation = parse_bool(auto_orientation, "auto_orientation" in selected_operations)
    selected_orientation_priority = parse_orientation_priority(orientation_priority)
    if selected_auto_orientation and "auto_orientation" not in selected_operations:
        selected_operations.append("auto_orientation")
    selected_fit_to_bed = parse_bool(fit_to_bed, "fit_to_bed_split" in selected_operations)
    selected_bed_size_x = parse_bed_size(bed_size_x, 220, "bed_size_x")
    selected_bed_size_y = parse_bed_size(bed_size_y, 250, "bed_size_y")
    selected_bed_size_z = parse_bed_size(bed_size_z, 220, "bed_size_z")
    selected_bed_connector_mode = parse_bed_connector_mode(bed_connector_mode)
    selected_bed_connector_clearance = parse_connector_clearance(bed_connector_clearance_mm)
    if selected_fit_to_bed and "fit_to_bed_split" not in selected_operations:
        selected_operations.append("fit_to_bed_split")
    selected_local_selection = parse_local_selection(local_selection)
    job_id = str(uuid4())
    log_event("upload_started", request_id=request_id, job_id=job_id, original_filename=original_filename)
    upload_dir = UPLOAD_ROOT / job_id
    result_dir = RESULT_ROOT / job_id
    upload_dir.mkdir(parents=True, exist_ok=False)
    result_dir.mkdir(parents=True, exist_ok=True)
    target_path = upload_dir / "input.stl"

    size = 0
    try:
        with target_path.open("wb") as target:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > active_upload_limit:
                    shutil.rmtree(upload_dir, ignore_errors=True)
                    shutil.rmtree(result_dir, ignore_errors=True)
                    log_event("upload_rejected_stream_size", request_id=request_id, job_id=job_id, size_bytes=size)
                    raise HTTPException(status_code=413, detail=upload_limit_message(active_upload_limit))
                target.write(chunk)
    finally:
        file.file.close()

    try:
        job_payload = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "message": "Job queued",
            "filename": safe_filename,
            "original_filename": original_filename,
            "input_path": str(target_path),
            "result_dir": str(result_dir),
            "size_bytes": size,
            "queued_at": utc_now_iso(),
            "operations": json.dumps(selected_operations),
            "reduction_percent": selected_reduction_percent,
            "split_axis": selected_split_axis,
            "split_parts": selected_split_parts,
            "split_mode": selected_split_mode,
            "split_engine": selected_split_engine,
            "split_plane_offset_mm": selected_split_plane_offset,
            "connector_size_mm": selected_connector_size,
            "connector_clearance_mm": selected_connector_clearance,
            "connector_count": selected_connector_count,
            "connector_depth_mm": selected_connector_depth,
            "connector_wall_thickness_mm": selected_connector_wall_thickness,
            "magnet_size": selected_magnet_size,
            "magnet_diameter_mm": selected_magnet_diameter,
            "magnet_thickness_mm": selected_magnet_thickness,
            "lock_profile": selected_lock_profile,
            "ai_cleanup_strength": selected_ai_cleanup_strength,
            "artifact_cleanup_strength": selected_artifact_cleanup_strength,
            "model_improvement_strength": selected_model_improvement_strength,
            "model_name": selected_model_name,
            "vehicle_name": selected_model_name,
            "symmetry_axis": selected_symmetry_axis,
            "symmetry_mode": selected_symmetry_mode,
            "apply_orientation": str(selected_apply_orientation).lower(),
            "orientation_transform": json.dumps(selected_orientation_transform, ensure_ascii=False),
            "auto_orientation": str(selected_auto_orientation).lower(),
            "orientation_priority": selected_orientation_priority,
            "fit_to_bed": str(selected_fit_to_bed).lower(),
            "bed_size_x": selected_bed_size_x,
            "bed_size_y": selected_bed_size_y,
            "bed_size_z": selected_bed_size_z,
            "bed_connector_mode": selected_bed_connector_mode,
            "bed_connector_clearance_mm": selected_bed_connector_clearance,
            "local_selection": json.dumps(selected_local_selection, ensure_ascii=False) if selected_local_selection else "",
            "access_level": str(beta_access["access_level"]),
            "beta_user_id": str((beta_access.get("user") or {}).get("id", "")) if isinstance(beta_access.get("user"), dict) else "",
            "queue_owner_key": queue_owner,
            "priority": queue_priority,
            "heavy_job": str(bool(set(selected_operations).intersection(HEAVY_OPERATIONS))).lower(),
            "is_test": str(parse_bool(is_test, False)).lower(),
            "source": sanitize_text(source or "app", 80),
            "environment": sanitize_text(environment or "production", 80),
            "test_run_id": sanitize_text(test_run_id or "", 120),
            "test_name": sanitize_text(test_name or "", 120),
        }
        write_job(client, job_id, job_payload)
        enqueue_job(client, job_id, queue_priority)
        update_user_seen(job_payload["beta_user_id"])
        log_event("upload_queued", request_id=request_id, job_id=job_id, size_bytes=size)
    except RedisError as exc:
        shutil.rmtree(upload_dir, ignore_errors=True)
        shutil.rmtree(result_dir, ignore_errors=True)
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc

    queue_info = job_queue_status(client, job_id, job_payload)
    return {"job_id": job_id, "status": "queued", **queue_info}


@app.get("/api/v1/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    try:
        client = get_redis()
        job = client.hgetall(job_key(job_id))
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response: dict[str, object] = {
        "job_id": job_id,
        "status": job.get("status", "failed"),
        "progress": int(job.get("progress", 0)),
        "message": job.get("message", ""),
    }
    response.update(job_queue_status(client, job_id, job))
    if job.get("size_bytes"):
        response["size_bytes"] = int(job["size_bytes"])
    if job.get("queued_at"):
        response["queued_at"] = job["queued_at"]
    if job.get("processing_started_at"):
        response["processing_started_at"] = job["processing_started_at"]
    if job.get("completed_at"):
        response["completed_at"] = job["completed_at"]
    if job.get("processing_seconds"):
        response["processing_seconds"] = float(job["processing_seconds"])
    if job.get("reduction_percent"):
        response["reduction_percent"] = int(job["reduction_percent"])
    if job.get("split_axis"):
        response["split_axis"] = job["split_axis"]
    if job.get("split_parts"):
        response["split_parts"] = int(job["split_parts"])
    if job.get("split_mode"):
        response["split_mode"] = job["split_mode"]
    if job.get("split_engine"):
        response["split_engine"] = job["split_engine"]
    if job.get("split_plane_offset_mm"):
        response["split_plane_offset_mm"] = float(job["split_plane_offset_mm"])
    if job.get("connector_size_mm"):
        response["connector_size_mm"] = int(job["connector_size_mm"])
    if job.get("connector_clearance_mm"):
        response["connector_clearance_mm"] = float(job["connector_clearance_mm"])
    if job.get("connector_count"):
        response["connector_count"] = int(job["connector_count"])
    if job.get("connector_depth_mm"):
        response["connector_depth_mm"] = float(job["connector_depth_mm"])
    if job.get("connector_wall_thickness_mm"):
        response["connector_wall_thickness_mm"] = float(job["connector_wall_thickness_mm"])
    if job.get("magnet_size"):
        response["magnet_size"] = job["magnet_size"]
    if job.get("magnet_diameter_mm"):
        response["magnet_diameter_mm"] = float(job["magnet_diameter_mm"])
    if job.get("magnet_thickness_mm"):
        response["magnet_thickness_mm"] = float(job["magnet_thickness_mm"])
    if job.get("lock_profile"):
        response["lock_profile"] = job["lock_profile"]
    if job.get("ai_cleanup_strength"):
        response["ai_cleanup_strength"] = job["ai_cleanup_strength"]
    if job.get("artifact_cleanup_strength"):
        response["artifact_cleanup_strength"] = job["artifact_cleanup_strength"]
    if job.get("model_improvement_strength"):
        response["model_improvement_strength"] = job["model_improvement_strength"]
    if job.get("model_name") or job.get("vehicle_name"):
        response["model_name"] = job.get("model_name") or job.get("vehicle_name")
    if job.get("symmetry_axis"):
        response["symmetry_axis"] = job["symmetry_axis"]
    if job.get("symmetry_mode"):
        response["symmetry_mode"] = job["symmetry_mode"]
    if job.get("apply_orientation"):
        response["apply_orientation"] = job["apply_orientation"].lower() == "true"
    if job.get("orientation_transform"):
        try:
            response["orientation_transform"] = json.loads(job["orientation_transform"])
        except json.JSONDecodeError:
            response["orientation_transform"] = None
    if job.get("auto_orientation"):
        response["auto_orientation"] = job["auto_orientation"].lower() == "true"
    if job.get("orientation_priority"):
        response["orientation_priority"] = job["orientation_priority"]
    if job.get("fit_to_bed"):
        response["fit_to_bed"] = job["fit_to_bed"].lower() == "true"
    if job.get("bed_size_x"):
        response["bed_size_x"] = float(job["bed_size_x"])
    if job.get("bed_size_y"):
        response["bed_size_y"] = float(job["bed_size_y"])
    if job.get("bed_size_z"):
        response["bed_size_z"] = float(job["bed_size_z"])
    if job.get("bed_connector_mode"):
        response["bed_connector_mode"] = job["bed_connector_mode"]
    if job.get("bed_connector_clearance_mm"):
        response["bed_connector_clearance_mm"] = float(job["bed_connector_clearance_mm"])
    if job.get("local_selection"):
        try:
            response["local_selection"] = json.loads(job["local_selection"])
        except json.JSONDecodeError:
            response["local_selection"] = None
    if job.get("access_level"):
        response["access_level"] = job["access_level"]
    if job.get("operations"):
        try:
            response["operations"] = json.loads(job["operations"])
        except json.JSONDecodeError:
            response["operations"] = []
    if job.get("result"):
        try:
            response["result"] = json.loads(job["result"])
        except json.JSONDecodeError:
            response["result"] = None
    return response


def get_job_result(job_id: str) -> dict:
    try:
        client = get_redis()
        job = client.hgetall(job_key(job_id))
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis is unavailable") from exc

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.get("result"):
        raise HTTPException(status_code=404, detail="Job result is not ready")

    try:
        result = json.loads(job["result"])
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=404, detail="Job result is not ready") from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=404, detail="Job result is not ready")
    return result


@app.get("/api/v1/jobs/{job_id}/download")
def download_job_result(job_id: str) -> FileResponse:
    zip_path = RESULT_ROOT / job_id / "result.zip"
    if not zip_path.exists() or not zip_path.is_file():
        raise HTTPException(status_code=404, detail="Result ZIP is not ready")

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"stl-master-{job_id}.zip",
    )


@app.head("/api/v1/jobs/{job_id}/download")
def head_job_result(job_id: str) -> FileResponse:
    return download_job_result(job_id)


def result_file_media_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".stl":
        return "model/stl"
    if suffix == ".json":
        return "application/json"
    if suffix == ".txt":
        return "text/plain; charset=utf-8"
    return "application/octet-stream"


@app.get("/api/v1/jobs/{job_id}/files/{filename}")
def download_job_file(job_id: str, filename: str) -> FileResponse:
    if filename != Path(filename).name or "/" in filename or "\\" in filename or filename in ("", ".", ".."):
        raise HTTPException(status_code=404, detail="File not found")

    result = get_job_result(job_id)
    generated_files = result.get("generated_files", [])
    allowed_files = {
        item.get("name")
        for item in generated_files
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    if filename not in allowed_files:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = RESULT_ROOT / job_id / filename
    result_dir = (RESULT_ROOT / job_id).resolve()
    try:
        resolved_path = file_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc

    if resolved_path.parent != result_dir or not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=resolved_path,
        filename=filename,
        media_type=result_file_media_type(filename),
    )


@app.head("/api/v1/jobs/{job_id}/files/{filename}")
def head_job_file(job_id: str, filename: str) -> FileResponse:
    return download_job_file(job_id, filename)
