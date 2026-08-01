#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/codex/projects/vk-stl-master"
cd "${PROJECT_DIR}"

tests=(
  "tests/smoke_model_qa.sh"
  "tests/smoke_print_repair.sh"
  "tests/smoke_ai_cleanup.sh"
  "tests/smoke_surface_recovery.sh"
  "tests/smoke_surface_recovery_quality.sh"
  "tests/smoke_local_smoothing.sh"
  "tests/smoke_local_smoothing_preview.sh"
  "tests/smoke_visible_result_contract.sh"
  "tests/smoke_frontend_workflow_contract.sh"
  "tests/smoke_studio_legacy_contract.sh"
  "tests/smoke_premium_ui_contract.sh"
  "tests/smoke_beta_feedback_ui_contract.sh"
  "tests/smoke_admin_feedback.sh"
  "tests/smoke_admin_auth_users_cleanup.sh"
  "tests/smoke_admin_security.sh"
  "tests/smoke_queue_limits.sh"
  "tests/smoke_public_launch.sh"
  "tests/smoke_premium_flow.sh"
  "tests/smoke_public_design_contract.sh"
  "tests/smoke_beta_readiness.sh"
  "tests/smoke_compare_view_contract.sh"
  "tests/smoke_change_map.sh"
  "tests/smoke_artifact_map.sh"
  "tests/smoke_processing_history.sh"
  "tests/smoke_visual_contract.sh"
  "tests/smoke_split_real_model.sh"
  "tests/smoke_split_glue_connector.sh"
  "tests/smoke_split_pins.sh"
  "tests/smoke_split_pins_geometry.sh"
  "tests/smoke_split_magnets.sh"
  "tests/smoke_split_lock.sh"
  "tests/smoke_final_model_contract.sh"
  "tests/smoke_apply_orientation.sh"
  "tests/smoke_apply_orientation_from_viewer_contract.sh"
  "tests/smoke_orientation_manual_transform.sh"
  "tests/smoke_auto_orientation.sh"
  "tests/smoke_chained_processing.sh"
  "tests/smoke_fit_to_bed_split.sh"
  "tests/smoke_split_plane_offset.sh"
)

echo "STL Master smoke regression pack"

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

echo "All smoke tests passed."
