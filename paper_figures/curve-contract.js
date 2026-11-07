'use strict';
function validate(data){
 for(const task of [3,5,7,10])for(const method of ['TTS-Memory','Mem-0']){
  const matches=data.curves.filter(c=>c.task===task&&c.method===method);
  if(matches.length!==1)throw Error(`Expected one ${method} task ${task} curve`);
  const values=matches[0].srk;
  if(!Array.isArray(values)||values.length!==task)throw Error(`${method} task ${task}: expected ${task} SR@k points`);
  if(values.some((v,i)=>!Number.isFinite(v)||v<0||v>100||(i>0&&v>values[i-1])))throw Error(`${method} task ${task}: invalid SR@k values`);
 }
 for(const method of ['TTS-Memory','Mem-0']){
  const episode=data.episode_curves.find(c=>c.method===method),row=data.rows.find(r=>r[0]===method);
  if(!episode||episode.tasks.join(',')!=='3,7,10'||episode.success_rate.length!==3||episode.success_rate.some((v,i)=>v!==Number.parseFloat(row[i+1])))throw Error(`${method}: episode curve differs from Table 2`);
 }
 return data;
}
if(typeof module!=='undefined')module.exports={validate};
else globalThis.SafeLabPaperContract={validate};
