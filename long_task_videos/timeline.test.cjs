const {test}=require('node:test'),assert=require('node:assert/strict'),{analyze}=require('./timeline.js');
test('physical progress is never fabricated as model switching',()=>{const a=analyze([{t:0,phase11:0},{t:2,phase11:1}],{failure_time:2,reason:'stuck'});assert.equal(a.events.length,1);assert.equal(a.events[0].delta,null);assert.match(a.coverage,/未发布/);assert.match(a.failure,/阶段 1/);});
test('initial nonzero phase is not timed as a completion',()=>assert.equal(analyze([{t:0,phase13:3}],{}).events.length,0));
test('explicit correspondence permits signed model minus physical delta',()=>{const a=analyze([{t:0,subtask_index:0},{t:3,subtask_index:1,matched_physical_completion_t:2}],{});assert.equal(a.events[0].delta,1);});
test('unmapped switch has unknown delta and phases stay separate',()=>{const a=analyze([{t:0,phase11:0,phase13:0,subtask_index:0},{t:2,phase13:1,subtask_index:1}],{});assert.equal(a.events.length,2);assert.ok(a.events.every(e=>e.delta===null));});
