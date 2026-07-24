#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"

if [[ -n "${ADMIN_PASSWORD:-}" ]]; then
  password="${ADMIN_PASSWORD}"
else
  read -r -s -p "New admin password: " password
  printf '\n'
  read -r -s -p "Repeat admin password: " password_repeat
  printf '\n'
  if [[ "${password}" != "${password_repeat}" ]]; then
    echo "Passwords do not match" >&2
    exit 1
  fi
fi

if [[ -z "${password}" || "${#password}" -lt 12 ]]; then
  echo "Admin password must be at least 12 characters." >&2
  exit 1
fi

hash_value="$(ADMIN_PASSWORD_VALUE="${password}" python3 - <<'PY'
import hashlib
import os
import secrets

password = os.environ["ADMIN_PASSWORD_VALUE"]
iterations = 200000
salt = secrets.token_hex(16)
digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
print(f"pbkdf2_sha256${iterations}${salt}${digest}")
PY
)"

session_secret="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"

umask 077
touch "${ENV_FILE}"

update_env() {
  local key="$1"
  local value="$2"
  local quoted_value
  quoted_value="'${value}'"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    tmp_file="$(mktemp)"
    awk -v key="${key}" -v value="${quoted_value}" 'BEGIN{done=0} $0 ~ "^" key "=" {print key "=" value; done=1; next} {print} END{if(!done) print key "=" value}' "${ENV_FILE}" > "${tmp_file}"
    mv "${tmp_file}" "${ENV_FILE}"
  else
    printf '%s=%s\n' "${key}" "${quoted_value}" >> "${ENV_FILE}"
  fi
}

update_env "ADMIN_PASSWORD_HASH" "${hash_value}"
if ! grep -q "^ADMIN_SESSION_SECRET=" "${ENV_FILE}"; then
  update_env "ADMIN_SESSION_SECRET" "${session_secret}"
fi
if ! grep -q "^ACCESS_CODE_SALT=" "${ENV_FILE}"; then
  update_env "ACCESS_CODE_SALT" "$(python3 - <<'PY'
import secrets
print(secrets.token_hex(24))
PY
)"
fi

echo "Admin password hash updated."
