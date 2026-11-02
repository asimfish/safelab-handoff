const test=require('node:test');
const assert=require('node:assert/strict');
const Model=require('../model.js');

function fixture(){
 const document='safelab_docs/inference/psibot_10_weigh_5beakers_v180/mem0_weak/START_HERE.md';
 const updated='2026-11-02T05:45:38Z';
 const data={updated_at:'2026-11-02T16:30:00Z',datasets:[{id:'10-weigh',label:'五杯'}],
  records:[{id:'10-mem0-weak',dataset:'10-weigh',method:'Mem-0 · 削弱版',camera:'chest',
   weights:[{step:30000,path:'/verified/weak/executor_step30000.pt'}]}],
  evaluations:[{id:'weak-h4',record:'10-mem0-weak',checkpoint:30000,horizon:4,
   success:null,completed:12,trials:500,unknown:0,kind:'自主闭环 · 5-seed'}],
  handoff_resolutions:[{issue:21,issue_updated_at:updated,record:'10-mem0-weak',
   checkpoint:30000,delivery_document:document}]};
 const edit={...Model.validateEdit({schema:2,kind:'checkpoint',target:'',task:'10',dataset:'10-weigh',
  version:'v180 · 五杯',data_path:'',camera:'chest',method:'Mem-0 · 削弱版',step:30000,
  path:document,doc:document,state:'untested',owner:'WPS训练',run:'',protocol:'',note:'',
  h4:'',h8:'',h30:'',h4unknown:0,h8unknown:0,h30unknown:0}),
  issue:21,updated,trusted:true,url:'https://github.com/asimfish/safelab-handoff/issues/21'};
 return {data,edit};
}

test('a resolved document-only handoff preserves the actual weight and evaluation progress',()=>{
 const {data,edit}=fixture();
 const board=Model.buildBoard(data,[edit]);
 assert.equal(board.rows.length,1);
 assert.equal(board.rows[0].path,'/verified/weak/executor_step30000.pt');
 assert.equal(board.rows[0].state,'evaluating');
 assert.equal(Model.progressFor(board.rows[0].evaluations,4).completed,12);
 assert.equal(board.rows[0].owner,'WPS训练');
});

test('a later handoff revision is visible until explicitly reconciled again',()=>{
 const {data,edit}=fixture();edit.updated='2026-11-02T17:00:00Z';
 const board=Model.buildBoard(data,[edit]);
 assert.equal(board.rows.length,2);
 assert.equal(board.rows.find(r=>r.record).state,'evaluating');
 assert.equal(board.rows.find(r=>!r.record).state,'untested');
});

test('a document resolution cannot redirect a different method onto an evaluated identity',()=>{
 const {data,edit}=fixture();edit.method='TTC · 对齐loss';
 const board=Model.buildBoard(data,[edit]);
 assert.equal(board.rows.length,2);
 assert.equal(board.rows.find(r=>r.record).method,'Mem-0 · 削弱版');
 assert.equal(board.rows.find(r=>r.record).path,'/verified/weak/executor_step30000.pt');
});
