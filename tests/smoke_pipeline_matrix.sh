#!/usr/bin/env bash
set -euo pipefail

SMOKE_TEST_NAME="$(basename "$0")"
SMOKE_TEST_RUN_ID="${SMOKE_TEST_RUN_ID:-$(python3 - <<'PY_SMOKE_ID'
import uuid
print(uuid.uuid4())
PY_SMOKE_ID
)}"
SMOKE_UPLOAD_FIELDS=(
  -F "is_test=true"
  -F "source=smoke_test"
  -F "environment=test"
  -F "test_run_id=${SMOKE_TEST_RUN_ID}"
  -F "test_name=${SMOKE_TEST_NAME}"
)
SMOKE_JSON_META="\"is_test\":true,\"source\":\"smoke_test\",\"environment\":\"test\",\"test_run_id\":\"${SMOKE_TEST_RUN_ID}\",\"test_name\":\"${SMOKE_TEST_NAME}\""

smoke_cleanup_run() {
  local api="${API_BASE:-http://localhost:8000}"
  if [[ "${SMOKE_SKIP_CLEANUP:-0}" == "1" || -z "${ADMIN_TOKEN:-}" ]]; then
    return 0
  fi
  local cleanup_response
  cleanup_response="$(curl --max-time 15 -sS     -H "X-Admin-Token: ${ADMIN_TOKEN}"     -H 'Content-Type: application/json'     -d "{\"confirmation\":\"УДАЛИТЬ ТЕСТОВЫЕ ДАННЫЕ\",\"test_run_id\":\"${SMOKE_TEST_RUN_ID}\"}"     "${api}/api/v1/admin/test-data/cleanup" || true)"
  if [[ -z "${cleanup_response}" ]]; then
    return 0
  fi
  python3 - "${cleanup_response}" <<'PY_SMOKE_CLEANUP'
import json
import sys
try:
    payload = json.loads(sys.argv[1])
except Exception:
    raise SystemExit(0)
if payload.get("ok") is not True:
    raise SystemExit("smoke cleanup failed")
remaining = payload.get("remaining_test_counts") or {}
if any(int(value or 0) for value in remaining.values()):
    raise SystemExit(f"smoke cleanup left test records: {remaining}")
print("smoke cleanup OK")
PY_SMOKE_CLEANUP
}
trap smoke_cleanup_run EXIT


PROJECT_DIR="/home/codex/projects/vk-stl-master"
API_BASE="http://localhost:8000"
REAL_MODEL="${PROJECT_DIR}/test-data/Geely_atlas_pro.stl"
RESULTS_DIR="${PROJECT_DIR}/tests/results"
ORIENTATION_TRANSFORM='{"rotation_x":90,"rotation_y":0,"rotation_z":0,"translate_to_floor":true}'

cd "${PROJECT_DIR}"
mkdir -p "${RESULTS_DIR}"

if [[ ! -f "${REAL_MODEL}" ]]; then
  echo "BROKEN missing real test STL: ${REAL_MODEL}" >&2
  exit 1
fi

json_value() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); value=${expr}; print(value if value is not None else '')"
}

upload_and_wait() {
  local label="$1"
  shift
  local response job_id job_json status
  response="$(curl -sS -X POST "$@" ${SMOKE_UPLOAD_FIELDS[@]} "${API_BASE}/api/v1/jobs/upload")"
  job_id="$(printf '%s' "${response}" | json_value "data.get('job_id')")"
  if [[ -z "${job_id}" ]]; then
    echo "BROKEN ${label}: upload did not return job_id: ${response}" >&2
    exit 1
  fi
  for _ in $(seq 1 220); do
    job_json="$(curl -sS "${API_BASE}/api/v1/jobs/${job_id}")"
    status="$(printf '%s' "${job_json}" | json_value "data.get('status')")"
    if [[ "${status}" == "completed" || "${status}" == "failed" ]]; then
      break
    fi
    sleep 2
  done
  if [[ "${status}" != "completed" ]]; then
    echo "BROKEN ${label}: job status=${status}, job_id=${job_id}" >&2
    printf '%s\n' "${job_json}" >&2
  fi
  printf '%s\n' "${job_json}"
}

zip_contents_for_job() {
  local job_id="$1"
  docker-compose exec -T worker python - "${job_id}" <<'PY'
import sys
from pathlib import Path
from zipfile import ZipFile
zip_path = Path('/data/results') / sys.argv[1] / 'result.zip'
if not zip_path.exists():
    print('__ZIP_MISSING__')
    raise SystemExit(0)
with ZipFile(zip_path) as archive:
    print('\n'.join(archive.namelist()))
PY
}

validate_case() {
  local label="$1"
  local json_path="$2"
  local zip_path_txt="$3"
  local expected_kind="$4"
  shift 4
  python3 - "${label}" "${json_path}" "${zip_path_txt}" "${expected_kind}" "$@" <<'PY'
import json
import sys
from pathlib import Path

label, json_path, zip_path_txt, expected_kind, *expected_sources = sys.argv[1:]
data = json.loads(Path(json_path).read_text())
result = data.get('result') or {}
zip_files = [line.strip() for line in Path(zip_path_txt).read_text().splitlines() if line.strip()]
generated = result.get('generated_files') or []
generated_names = [item.get('name') for item in generated]
operations = result.get('operations') or []
implemented = result.get('implemented_operations') or []
issues = []
warnings = []

if data.get('status') != 'completed':
    issues.append(f"status={data.get('status')}")
if 'original.stl' not in zip_files:
    issues.append('ZIP missing original.stl')
if 'prepare_package' in operations:
    for name in ('print_report.txt', 'manifest.json'):
        if name not in zip_files:
            issues.append(f'ZIP missing {name}')
if sorted(set(generated_names)) != sorted(set(zip_files)):
    issues.append(f'generated_files != ZIP ({generated_names} vs {zip_files})')
for name in generated_names:
    if name not in zip_files:
        issues.append(f'generated file not in ZIP: {name}')

unexpected_ops = [op for op in implemented if op not in operations]
if unexpected_ops:
    issues.append(f'implemented operation not requested: {unexpected_ops}')

model_names = {name for name in zip_files if name.endswith('.stl')}
known_allowed = {'original.stl'}
source_file = None
output_files = []
operation_success = None
final_model = result.get('final_model')

if expected_kind == 'model_improvement':
    repair = result.get('print_repair') or {}
    improvement = result.get('model_improvement') or {}
    operation_success = bool(repair.get('success') or improvement.get('success'))
    source_file = 'original.stl'
    out = repair.get('output_file') or improvement.get('after_file')
    if out:
        output_files.append(out)
    if operation_success and final_model != out:
        issues.append(f'final_model {final_model} != output {out}')
    if operation_success is False:
        warnings.append(repair.get('reason') or repair.get('warning') or 'model improvement controlled no-op')
    known_allowed.update({'repaired_model.stl', 'improved_model.stl'})
elif expected_kind == 'remove_ai_artifacts':
    cleanup = result.get('remove_ai_artifacts') or {}
    operation_success = cleanup.get('success')
    source_file = cleanup.get('input_file') or 'original.stl'
    out = cleanup.get('output_file')
    if out:
        output_files.append(out)
    if operation_success and final_model != out:
        issues.append(f'final_model {final_model} != cleanup output {out}')
    if operation_success is False:
        warnings.append(cleanup.get('reason') or 'cleanup controlled failure')
    known_allowed.add('cleaned_artifacts.stl')
elif expected_kind == 'reduce_polygons':
    reduction = result.get('reduce_polygons') or {}
    operation_success = reduction.get('success')
    source_file = 'repaired.stl' if result.get('repair_mesh', {}).get('success') else 'original.stl'
    out = reduction.get('output_file')
    if out:
        output_files.append(out)
    if operation_success and final_model != out:
        issues.append(f'final_model {final_model} != reduce output {out}')
    known_allowed.add('reduced.stl')
elif expected_kind == 'fix_symmetry':
    symmetry = result.get('fix_symmetry') or {}
    operation_success = symmetry.get('success')
    source_file = 'original.stl'
    out = symmetry.get('output_file')
    if out:
        output_files.append(out)
    if operation_success and final_model != out:
        issues.append(f'final_model {final_model} != symmetry output {out}')
    if operation_success is False:
        warnings.append(symmetry.get('reason') or 'symmetry controlled failure')
    known_allowed.add('symmetry_fixed.stl')
elif expected_kind == 'apply_orientation':
    orientation = result.get('apply_orientation') or {}
    operation_success = orientation.get('success')
    source_file = orientation.get('input_file')
    output_files.append(orientation.get('output_file'))
    if operation_success and final_model != 'oriented_model.stl':
        issues.append(f'final_model {final_model} != oriented_model.stl')
    known_allowed.add('oriented_model.stl')
elif expected_kind == 'auto_orientation':
    orientation = result.get('auto_orientation') or {}
    operation_success = orientation.get('success')
    source_file = orientation.get('input_file') or 'original.stl'
    out = orientation.get('output_file')
    if out:
        output_files.append(out)
    if operation_success and not orientation.get('no_change_needed') and final_model != 'oriented_auto.stl':
        issues.append(f'final_model {final_model} != oriented_auto.stl')
    if operation_success and orientation.get('no_change_needed') and out:
        issues.append('auto_orientation no_change_needed exposed output_file')
    if operation_success and orientation.get('no_change_needed'):
        warnings.append(orientation.get('recommendation') or 'auto_orientation no change needed')
    known_allowed.add('oriented_auto.stl')
elif expected_kind == 'split_model':
    split = result.get('split_model') or {}
    operation_success = split.get('success')
    source_file = split.get('source_file')
    output_files.extend(split.get('output_files') or [])
    if operation_success and not output_files:
        issues.append('split success without output files')
    if operation_success and final_model not in {source_file, 'original.stl', 'oriented_model.stl', 'cleaned_artifacts.stl', 'repaired_model.stl', 'reduced.stl', 'repaired.stl', 'symmetry_fixed.stl'}:
        issues.append(f'unexpected split final_model={final_model}')
    known_allowed.update(output_files)
elif expected_kind == 'fit_to_bed_split':
    fit = result.get('fit_to_bed_split') or {}
    operation_success = fit.get('success')
    source_file = fit.get('source_file')
    output_files.extend(fit.get('output_files') or [])
    if operation_success and not fit.get('no_split_needed') and not output_files:
        issues.append('fit_to_bed success without parts and no_split_needed=false')
    if operation_success and final_model not in {source_file, 'original.stl', 'oriented_auto.stl', 'oriented_model.stl', 'cleaned_artifacts.stl', 'repaired_model.stl', 'reduced.stl', 'repaired.stl'}:
        issues.append(f'unexpected fit_to_bed final_model={final_model}')
    known_allowed.update(output_files)
else:
    issues.append(f'unknown expected_kind={expected_kind}')

for src in expected_sources:
    if src and source_file != src:
        issues.append(f'source_file {source_file} != expected {src}')

for out in output_files:
    if out and out not in zip_files:
        issues.append(f'output missing from ZIP: {out}')

# Detect unrelated stale outputs in ZIP for the selected operation set.
requested = set(operations)
allowed_by_request = set(known_allowed)
if 'model_improvement' in requested:
    allowed_by_request.update({'repaired_model.stl', 'improved_model.stl'})
if 'repair_mesh' in requested:
    allowed_by_request.add('repaired.stl')
if 'remove_ai_artifacts' in requested:
    allowed_by_request.add('cleaned_artifacts.stl')
if 'reduce_polygons' in requested:
    allowed_by_request.add('reduced.stl')
if 'apply_orientation' in requested:
    allowed_by_request.add('oriented_model.stl')
if 'auto_orientation' in requested:
    allowed_by_request.add('oriented_auto.stl')
if 'fix_symmetry' in requested:
    allowed_by_request.add('symmetry_fixed.stl')
if 'split_model' in requested:
    allowed_by_request.update(name for name in zip_files if name.startswith('split_part_'))
if 'fit_to_bed_split' in requested:
    allowed_by_request.update(name for name in zip_files if name.startswith('bed_part_'))

unrelated = sorted(name for name in model_names if name not in allowed_by_request)
if unrelated:
    issues.append(f'unrelated STL in ZIP: {unrelated}')

# Geometry presence check is delegated to API/worker smoke; here ensure file links exist in generated_files.
for name in zip_files:
    if name.endswith('.stl') and name not in generated_names:
        issues.append(f'STL in ZIP missing generated_files entry: {name}')

if operation_success is False and expected_kind not in {'remove_ai_artifacts', 'fix_symmetry', 'model_improvement'}:
    issues.append(f'{expected_kind} success=false')

status = 'BROKEN' if issues else ('WARNING' if warnings else 'SAFE')
summary = {
    'case': label,
    'status': status,
    'job_id': data.get('job_id'),
    'operation': expected_kind,
    'input_stl': source_file or 'original.stl',
    'output_stl': ','.join([x for x in output_files if x]) or '-',
    'final_model': final_model,
    'generated_files': ','.join(generated_names),
    'zip': ','.join(zip_files),
    'issues': '; '.join(issues),
    'warnings': '; '.join(warnings),
}
print('\t'.join(str(summary[key]) for key in ['status','case','operation','input_stl','output_stl','final_model','generated_files','zip','issues','warnings']))
Path('tests/results/pipeline_matrix_summary.tsv').open('a', encoding='utf-8').write('\t'.join(str(summary[key]) for key in ['status','case','operation','input_stl','output_stl','final_model','generated_files','zip','issues','warnings']) + '\n')
PY
}

run_case() {
  local label="$1"
  local kind="$2"
  shift 2
  local safe_label json_path zip_path_txt job_id json zip_contents status
  safe_label="$(printf '%s' "${label}" | tr ' /' '__' | tr -cd '[:alnum:]_+-')"
  json="$(upload_and_wait "${label}" "$@")"
  job_id="$(printf '%s' "${json}" | json_value "data.get('job_id')")"
  json_path="${RESULTS_DIR}/pipeline_matrix_${safe_label}_${job_id}.json"
  zip_path_txt="${RESULTS_DIR}/pipeline_matrix_${safe_label}_${job_id}_zip.txt"
  printf '%s' "${json}" > "${json_path}"
  zip_contents_for_job "${job_id}" > "${zip_path_txt}"
  validate_case "${label}" "${json_path}" "${zip_path_txt}" "${kind}" "${EXPECTED_SOURCE:-}"
}

: > tests/results/pipeline_matrix_summary.tsv
printf 'STATUS\tCASE\tOPERATION\tINPUT_STL\tOUTPUT_STL\tFINAL_MODEL\tGENERATED_FILES\tZIP\tISSUES\tWARNINGS\n'

# Individual operation audit.
EXPECTED_SOURCE="" run_case "single model_improvement" "model_improvement" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,model_improvement,prepare_package' \
  -F 'model_improvement_strength=balanced'

EXPECTED_SOURCE="" run_case "single remove_ai_artifacts" "remove_ai_artifacts" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,remove_ai_artifacts,prepare_package' \
  -F 'artifact_cleanup_strength=balanced'

EXPECTED_SOURCE="" run_case "single reduce_polygons" "reduce_polygons" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,reduce_polygons,prepare_package' \
  -F 'reduction_percent=50'

EXPECTED_SOURCE="" run_case "single fix_symmetry" "fix_symmetry" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,fix_symmetry,prepare_package' \
  -F 'symmetry_axis=x' \
  -F 'symmetry_mode=fix'

EXPECTED_SOURCE="original.stl" run_case "single apply_orientation" "apply_orientation" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,apply_orientation,prepare_package' \
  -F 'apply_orientation=true' \
  -F "orientation_transform=${ORIENTATION_TRANSFORM}"

EXPECTED_SOURCE="original.stl" run_case "single auto_orientation" "auto_orientation" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,auto_orientation,prepare_package' \
  -F 'auto_orientation=true' \
  -F 'orientation_priority=supports'

EXPECTED_SOURCE="original.stl" run_case "single split_model" "split_model" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,split_model,prepare_package' \
  -F 'split_axis=y' \
  -F 'split_parts=2' \
  -F 'split_mode=simple' \
  -F 'split_engine=blender_boolean'

EXPECTED_SOURCE="original.stl" run_case "single fit_to_bed_split" "fit_to_bed_split" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,fit_to_bed_split,prepare_package' \
  -F 'fit_to_bed=true' \
  -F 'bed_size_x=220' \
  -F 'bed_size_y=250' \
  -F 'bed_size_z=220' \
  -F 'bed_connector_mode=none'

# Split chains.
EXPECTED_SOURCE="oriented_model.stl" run_case "chain orientation -> split" "split_model" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,apply_orientation,split_model,prepare_package' \
  -F 'apply_orientation=true' \
  -F "orientation_transform=${ORIENTATION_TRANSFORM}" \
  -F 'split_axis=y' \
  -F 'split_parts=2' \
  -F 'split_mode=pins' \
  -F 'split_engine=blender_boolean'

EXPECTED_SOURCE="cleaned_artifacts.stl" run_case "chain cleanup -> split" "split_model" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,remove_ai_artifacts,split_model,prepare_package' \
  -F 'artifact_cleanup_strength=balanced' \
  -F 'split_axis=y' \
  -F 'split_parts=2' \
  -F 'split_mode=simple' \
  -F 'split_engine=blender_boolean'

EXPECTED_SOURCE="original.stl" run_case "chain repair -> split" "split_model" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,model_improvement,split_model,prepare_package' \
  -F 'model_improvement_strength=balanced' \
  -F 'split_axis=y' \
  -F 'split_parts=2' \
  -F 'split_mode=simple' \
  -F 'split_engine=blender_boolean'

EXPECTED_SOURCE="reduced.stl" run_case "chain reduce -> split" "split_model" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,reduce_polygons,split_model,prepare_package' \
  -F 'reduction_percent=50' \
  -F 'split_axis=y' \
  -F 'split_parts=2' \
  -F 'split_mode=simple' \
  -F 'split_engine=blender_boolean'

# Fit-to-bed chains.
EXPECTED_SOURCE="oriented_model.stl" run_case "chain orientation -> fit_to_bed" "fit_to_bed_split" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,apply_orientation,fit_to_bed_split,prepare_package' \
  -F 'apply_orientation=true' \
  -F "orientation_transform=${ORIENTATION_TRANSFORM}" \
  -F 'fit_to_bed=true' \
  -F 'bed_size_x=220' \
  -F 'bed_size_y=250' \
  -F 'bed_size_z=220' \
  -F 'bed_connector_mode=none'

EXPECTED_SOURCE="cleaned_artifacts.stl" run_case "chain cleanup -> fit_to_bed" "fit_to_bed_split" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,remove_ai_artifacts,fit_to_bed_split,prepare_package' \
  -F 'artifact_cleanup_strength=balanced' \
  -F 'fit_to_bed=true' \
  -F 'bed_size_x=220' \
  -F 'bed_size_y=250' \
  -F 'bed_size_z=220' \
  -F 'bed_connector_mode=none'

EXPECTED_SOURCE="original.stl" run_case "chain repair -> fit_to_bed" "fit_to_bed_split" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,model_improvement,fit_to_bed_split,prepare_package' \
  -F 'model_improvement_strength=balanced' \
  -F 'fit_to_bed=true' \
  -F 'bed_size_x=220' \
  -F 'bed_size_y=250' \
  -F 'bed_size_z=220' \
  -F 'bed_connector_mode=none'

EXPECTED_SOURCE="reduced.stl" run_case "chain reduce -> fit_to_bed" "fit_to_bed_split" \
  -F "file=@${REAL_MODEL}" \
  -F 'operations=analyze,print_check,reduce_polygons,fit_to_bed_split,prepare_package' \
  -F 'reduction_percent=50' \
  -F 'fit_to_bed=true' \
  -F 'bed_size_x=220' \
  -F 'bed_size_y=250' \
  -F 'bed_size_z=220' \
  -F 'bed_connector_mode=none'

printf '\nMatrix summary saved to tests/results/pipeline_matrix_summary.tsv\n'
if awk -F '\t' 'NR>0 && $1=="BROKEN" {found=1} END{exit found?0:1}' tests/results/pipeline_matrix_summary.tsv; then
  echo "Pipeline matrix contains BROKEN cases." >&2
  exit 1
fi
