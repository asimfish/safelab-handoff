'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const M = require('../model.js');
const root = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'data.json')));
const diagnostic = e => /^task7-memoryvla83-raw15-clock15-h(?:2|8)-.*-20261111$/.test(e.id);

test('raw15 changed-history diagnostics cannot replace baseline scores or progress', () => {
  const rows = data.evaluations.filter(diagnostic);
  assert.equal(rows.length, 8);
  for (const row of rows) {
    assert.equal(row.stage, 'diagnostic');
    assert.equal(row.formal_score_eligible, false);
    assert.equal(M.resultFor([row], row.horizon), null);
    assert.equal(M.progressFor([{...row, success: null}], row.horizon), null);
  }
  const baseline = {...data, evaluations: data.evaluations.filter(e => !diagnostic(e))};
  const scores = d => M.buildBoard(d).rows.map(r => ({id: r.id, h4: r.h4, h8: r.h8}));
  assert.deepEqual(scores(data), scores(baseline));
});

test('the task7 public all-phase summary fits the evidence budget and retains findings', () => {
  const file = path.join(root, 'reports/task7-pi05-allphase-AB-20261111.json');
  assert.ok(fs.statSync(file).size <= 200000);
  const report = JSON.parse(fs.readFileSync(file));
  assert.equal(report.actual_NN_queries, 740);
  assert.equal(report.allphase_training_frame_count, 700);
  assert.equal(report.fixed_episodes.length, 20);
  assert.ok(report.allphase && report.initial_A_B_Q && report.paired_RMSE_difference_rad);
  assert.ok(report.full_evidence.sha256.match(/^[a-f0-9]{64}$/));
  assert.ok(report.full_evidence.bytes > 200000);
  assert.ok(report.limits.length > 0);
});
