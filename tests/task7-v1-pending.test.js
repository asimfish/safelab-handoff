'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),M=require('../model');
const data=JSON.parse(fs.readFileSync('data.json'));
const inventory=JSON.parse(fs.readFileSync('reports/task7-eval-v1-20261103.json'));
const rows=data.evaluations.filter(e=>e.id.startsWith('task7-eval-v1-A-original-'));
test('task7 registers five30k checkpoints at h4/h8, using existing record and delivery',()=>{
 assert.equal(rows.length,10);assert.equal(new Set(rows.map(r=>r.variant)).size,5);
 for(const row of rows){
  const record=data.records.find(r=>r.id===row.record);assert.ok(record,row.id);
  assert.ok(record.weights.some(w=>w.step===row.checkpoint&&w.path===row.checkpoint_path));
  assert.equal(row.checkpoint,30000);assert.ok([4,8].includes(row.horizon));
  assert.equal(row.protocol_version,M.PROTOCOL);assert.equal(row.stage,'A');assert.equal(row.condition_version,'original-v1');
  assert.equal(record.camera,'chest');assert.equal(row.camera,'chest');assert.equal(row.target,100);
 }
});
test('unstarted task7 rows do not fabricate trials, unknown failures, averages, hashes or readiness',()=>{
 for(const row of rows){
  assert.equal(row.status,'admission_pending');assert.equal(row.success,null);assert.equal(row.completed,0);assert.equal(row.trials,0);assert.equal(row.unknown,0);
  assert.deepEqual(row.phase_hist,{});assert.equal(Object.values(row.phase_hist).reduce((a,b)=>a+b,0),row.trials-row.unknown);
  assert.equal(row.mean_phase,null);assert.equal(row.wilson95,null);assert.equal(row.scene_list_hash,'sha256:f6d728df04ff3d87927700173aa7f83c5ffa5de699d750f6da819e97156fae6f');
  assert.equal(row.expected_start_at,null);assert.ok(row.pending_reason);assert.ok(row.expected_start_conditions);
  assert.equal(row.topology.num_envs_actual,null);assert.equal(row.topology.procs_per_gpu,null);assert.equal(row.topology.actual_Apps,0);
  assert.equal(row.performance_observation.actual_GPUs,0);
  assert.deepEqual(Object.keys(row.admission).sort(),['expert_replay','open_loop','render_multiframe','smoke20'].sort());
  for(const gate of Object.values(row.admission)){assert.equal(gate.passed,false);assert.equal(gate.status,'pending');assert.ok(gate.report);}
  assert.equal(row.seed_results.length,1);assert.equal(row.seed_results[0].seed,0);assert.equal(row.seed_results[0].trials,0);
  assert.equal(row.lr_split.left.label,'order1234');assert.equal(row.lr_split.right.label,'order4321');
  assert.equal(row.lr_split.left.planned_trials,50);assert.equal(row.lr_split.right.planned_trials,50);
  assert.equal(row.legacy_metrics_reused,false);assert.equal(row.attach_results_reused,false);
 }
});
test('pending rows stay outside formal comparison and weak delivery issues are not substituted',()=>{
 const formal=M.formalComparisons(M.buildBoard(data));assert.ok(!formal.some(e=>rows.some(r=>r.id===e.id)));
 for(const row of rows){
  if(row.variant==='mem0_weak_30k')assert.equal(row.handoff_issue,3);
  else if(row.variant==='ttc_weak_aligned_30k')assert.equal(row.handoff_issue,18);
  else assert.equal(row.handoff_issue,null);
  assert.notEqual(row.handoff_issue,24);
 }
 assert.deepEqual(inventory.task7_checkpoint_issues,[3,18,24]);assert.equal(inventory.old_10500_expansion_not_promised,true);
 assert.equal(inventory.excluded.pi05_issue24,'another agent; no run or edit here');
});

test('task7 fixed100 scene hash is exact and orders interleave from start',()=>{const crypto=require('node:crypto'),raw=fs.readFileSync('reports/task7-eval-v1-20261103/scenes.json');assert.equal('sha256:'+crypto.createHash('sha256').update(raw).digest('hex'),rows[0].scene_list_hash);const scenes=JSON.parse(raw);assert.equal(scenes.length,100);assert.equal(scenes.filter(s=>s.order==='1234').length,50);for(let i=0;i<scenes.length;i++){assert.equal(scenes[i].dispatch_index,i);assert.equal(scenes[i].order,i%2?'4321':'1234');assert.equal(scenes[i].position_jitter_m,0);}});

test('legacy broad campaign is stopped with zero current resources and no score migration',()=>{for(const id of ['task7-all-20261101','task7-grasp-attach-20261101']){const campaign=data.campaigns.find(c=>c.id===id);assert.equal(campaign.status,'legacy_partial_stopped');assert.equal(campaign.active_apps,0);assert.equal(campaign.gpus,0);assert.equal(campaign.old_expansion_restart_authorized,false);assert.equal(campaign.legacy_terminal_summary.accepted,3287);assert.equal(campaign.legacy_terminal_summary.successes,50);assert.equal(campaign.legacy_terminal_summary.accepted_is_not_total_dispatched_denominator,true);}const terminal=JSON.parse(fs.readFileSync('reports/task7-eval-v1-20261103/legacy-platform-terminal.json'));assert.ok(terminal.all_platform_terminal);assert.ok(terminal.jobs.every(j=>j.status==='STOPPED'));assert.equal(terminal.reserved_GPU_until_terminal,0);});
