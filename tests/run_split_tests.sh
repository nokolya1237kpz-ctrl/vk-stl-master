#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/codex/projects/vk-stl-master"
cd "${PROJECT_DIR}"

tests=(
  "tests/smoke_split_real_model.sh"
  "tests/smoke_split_connectors.sh"
  "tests/smoke_split_assembly.sh"
)

echo "STL Master Split smoke test pack"

for test_script in "${tests[@]}"; do
  echo "START ${test_script}"
  if "${PROJECT_DIR}/${test_script}"; then
    echo "OK ${test_script}"
  else
    status=$?
    echo "FAILED ${test_script}"
    exit "${status}"
  fi
done

echo "All split smoke tests passed."
