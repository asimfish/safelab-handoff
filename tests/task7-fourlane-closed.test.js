const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');
const report = JSON.parse(fs.readFileSync(path.join(root, 'reports/task7-eval-v1-20261103/fullpool4-closed-reference-audit-20261104.json'), 'utf8'));

test('four-lane infrastructure proof cannot grant physical admission or a formal score', () => {
  assert.equal(report.formal_stage_A_trials_added, 0);
  assert.equal(report.formal_success, null);
  assert.equal(report.formal_rows_changed, 0);
  assert.equal(report.model_smoke_admission_granted, false);
  assert.equal(report.execution_gate.full10_expert_admission_passed, false);
  assert.equal(report.execution_gate.model_StageA_authorized, false);
  const q = report.four_lane_model_qualification;
  assert.equal(q.qualification_inherited_to_Gen_or_weak, false);
  assert.equal(q.N1x4_Native_image_gate_passed, false);
  assert.equal(q.combined_model_and_Native_memory_passed, false);
  assert.equal(q.qualified_variant_horizons.length, 4);
  assert.deepEqual(q.qualified_variant_horizons.map(x => `${x.variant}:${x.horizon}`).sort(), [
    'mem0_30k:4', 'mem0_30k:8',
    'ours_aligned_30k_native_classifier_switch_v1:4',
    'ours_aligned_30k_native_classifier_switch_v1:8'
  ]);
  assert.equal(q.archive.independent_mirror_SHA_verified, true);
  assert.equal(q.full_Policy_return_action_status_RNG_semantic_max_difference, 0);
  assert.equal(report.control_reference_audit.measured_states_interpolated, false);
  assert.equal(report.control_reference_audit.full120_state_gate_claimed, false);
  assert.equal(report.control_reference_audit.full120_source_recovered, false);
  assert.ok(report.GPU_utilization.actual_sample_span_seconds >= 600);
  assert.equal(report.GPU_utilization.sustained_80_percent_achieved, false);
});
