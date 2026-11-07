const test=require('node:test');
const assert=require('node:assert/strict');
const M=require('./model.js'),P=require('./presentation.js');
const legacy={id:'legacy7',task:'7',record:'7-aligned',method:'TTC',checkpoint:30000,horizon:8,stage:'diagnostic',protocol_version:'SafeLab-Eval-v1.1',oracle_version:'placement-v1.1',condition_version:'contact_preserving_native32_v6_time480_unheld_tilt_nonterminal',assistance_protocol:'v1.4-A',grasp_attachment:'contact_preserving_native32_v6',dataset:'7-weigh',policy_camera:'chest',render_config_hash:'a'.repeat(64),scene_list_hash:'b'.repeat(64),scene_id:'0',seed:0,side:'left',success:17,trials:100,completed:100,target:100,unknown:0};
test('seven-task fixed termination remains distinct for every published revision marker',()=>{
 for(const field of ['assistance_protocol','termination_rule_version','variant','protocol_version','condition_version','id']){
  const fixed={...legacy,[field]:'v1.4-A-fixed'};
  assert.notEqual(M.config(fixed),M.config(legacy),field+' configuration collision');
  assert.notEqual(M.pairKey(fixed),M.pairKey(legacy),field+' physical-pair collision');
  assert.match(P.title(fixed),/v1\.4-A-fixed.*修正后终止规则/,field+' visible revision missing');
 }
});
test('fixed pending rows cannot replace an old final result or acquire its score',()=>{
 const fixed={...legacy,id:'fixed7',assistance_protocol:'v1.4-A-fixed',success:null,completed:0,status:'running'};
 const rows=P.rows([legacy,fixed],[],'7');
 assert.equal(rows.length,2);
 const old=rows.find(g=>g.item.id==='legacy7'),next=rows.find(g=>g.item.id==='fixed7');
 assert.equal(P.metricCell(old.protocols['v1.1']),'17/100');
 assert.equal(P.metricCell(next.protocols['v1.1']),'在跑 0/100');
 assert.equal(M.rates(next.protocols['v1.1']),null);
});
