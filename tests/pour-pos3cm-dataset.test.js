const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Model = require('../model.js');
const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../data.json')));
const id = '3-pos3cm-200';
const approvedRoot = '/projects/a02012413/buckets/zenith-a02012413/liyufeng/psibot_3_pour_pos3cm_pilot20_20261103_1749/psibot_3_pour_pos3cm_v1_final200_L100R100_R700_lossless_20261108';

test('pour pos3cm has one distinct dataset identity in the three-task selector', () => {
  assert.equal(data.datasets.filter(d => d.id === id).length, 1);
  const dataset = Model.buildBoard(data).datasets.find(d => d.id === id);
  assert.equal(dataset.task, '3');
  assert.equal(Model.VERSIONS[id], '±3cm · 200条');
  assert.equal(dataset.version, Model.VERSIONS[id]);
  assert.ok(!['3-latest', '3-v13', '3-jitter'].includes(dataset.id));
  assert.equal(data.records.filter(r => r.dataset === id).length, 0);
  assert.equal(Model.buildBoard(data).rows.filter(r => r.dataset === id).length, 0);
});

test('pour pos3cm preserves the accepted count and original temporal/camera contract', () => {
  const dataset = data.datasets.find(d => d.id === id);
  const delivery = dataset.delivery;
  assert.deepEqual([dataset.episodes, dataset.frames], [200, 240589]);
  assert.deepEqual([delivery.left_episodes, delivery.right_episodes], [100, 100]);
  assert.deepEqual(delivery.formats, ['LeRobot v2.1', 'LeRobot v3.0']);
  assert.equal(dataset.path, approvedRoot);
  assert.deepEqual(delivery.format_paths, {
    'LeRobot v2.1': approvedRoot + '/lerobot_v21',
    'LeRobot v3.0': approvedRoot + '/lerobot_v30'
  });
  assert.deepEqual(delivery.cameras, ['head', 'chest', 'third_person']);
  assert.deepEqual([delivery.video_width, delivery.video_height, delivery.video_fps], [640, 480, 15]);
  assert.equal(delivery.state_dim, 13);
  assert.equal(delivery.native_hz, delivery.video_fps * delivery.native_ticks_per_frame);
  assert.equal(delivery.native_ticks_per_frame, 8);
  assert.equal(delivery.action_semantics, 'interval_end');
  assert.equal(delivery.qualified_ledger_sha256, '46506f893fdb33d73b6fa864147777819edb52c3798cd171216cbe67731d93f5');
  assert.equal(delivery.frozen_lossless_acceptance_sha256, '172da8b1b904655f04f7d806e84d35579c792a36f7abddf5ee5e527fdf96adce');
});

test('a final delivery claim requires both completion evidence hashes', () => {
  const dataset = data.datasets.find(d => d.id === id);
  const delivery = dataset.delivery;
  const proofs = [delivery.r700_delivery_status_sha256, delivery.r936_metadata_receipt_sha256];
  assert.ok(['pending_final_delivery_verification', 'complete'].includes(delivery.state));
  if (delivery.state === 'complete') {
    for (const hash of proofs) assert.match(hash, /^[a-f0-9]{64}$/);
    assert.ok(dataset.path.trim(), 'completed delivery needs a reviewed access location');
  } else {
    assert.deepEqual(proofs, [null, null]);
    assert.match(dataset.note, /待实际完成核验/);
  }
  const document = path.resolve(__dirname, '..', dataset.source);
  assert.ok(fs.existsSync(document));
  const documentText = fs.readFileSync(document, 'utf8');
  for (const accessPath of Object.values(delivery.format_paths)) assert.ok(documentText.includes(accessPath));
  assert.ok(!documentText.includes('待交接台确认'));
});
