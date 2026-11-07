const test=require('node:test');
const assert=require('node:assert/strict');
const M=require('./model.js'),P=require('./presentation.js');
test('r1-released is a separate diagnostic oracle and cannot overwrite r1',()=>{
 const old={task:'7',record:'7-aligned',method:'TTC',checkpoint:30000,horizon:8,condition_version:'same',stage:'diagnostic',id:'old',protocol_version:'SafeLab-Eval-v1.4-r1',success:9,trials:50,completed:50,unknown:0};
 const released={...old,id:'new',protocol_version:'SafeLab-Eval-v1.4-r1-released',success:8};
 assert.equal(M.protocol(released.protocol_version),'v1.4-r1-released');
 const [g]=P.rows([old,released],[],'7');
 assert.equal(g.protocols['v1.4-r1'].success,9);
 assert.equal(g.protocols['v1.4-r1-released'].success,8);
 assert.ok(P.versions.includes('v1.4-r1-released'));
});
