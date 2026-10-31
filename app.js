'use strict';
const M=HandoffModel,$=s=>document.querySelector(s),REPO='https://github.com/asimfish/safelab-handoff';
let data,board,shared=[],rawIssues=[],syncing=false,feedError='',lastSync=null,query='',statusFilter='all',selectedTask='3',selectedVersion='';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const camera=c=>M.CAMERAS[c]||'相机待确认';
const dt=d=>{try{return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',dateStyle:'short',timeStyle:'short'}).format(new Date(d));}catch{return '时间待核对';}};
const badge=(s,text)=>`<span class="badge ${esc(s)}">${esc(text||M.STATES[s]||s)}</span>`;
const toast=s=>{$('#toast').textContent=s;$('#toast').className='show';setTimeout(()=>$('#toast').className='',4000);};
function safeLink(url,text){try{const u=new URL(url);return u.protocol==='https:'?`<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">${esc(text)} ↗</a>`:esc(text);}catch{return esc(text);}}
const path=p=>p?`<div class="path"><code>${esc(p)}</code><button data-copy="${esc(p)}" aria-label="复制路径">复制</button></div>`:'<span class="muted">尚未提供</span>';
const allStates=['all','untested','evaluating','results','training','blocked','verify'];
function versionList(task){return board.datasets.filter(d=>d.task===task).sort((a,b)=>{const v=M.TASKS.find(t=>t.id===task)?.versions||[];return (v.includes(a.id)?v.indexOf(a.id):99)-(v.includes(b.id)?v.indexOf(b.id):99);});}
function rebuild(){board=M.buildBoard(data,shared);render();}
function route(){const parts=location.hash.slice(1).split('/');if(parts[0]==='task'){selectedTask=['3','5','7','10','other'].includes(parts[1])?parts[1]:'3';selectedVersion=parts[2]||'';}render();}
function nav(){const items=[...M.TASKS,{id:'other',name:'待归属',sub:'待补数据与相机'}];$('#nav').innerHTML=`<a href="#overview" class="${!location.hash||location.hash==='#overview'?'active':''}">测试成功率总览</a><a href="#queue" class="${location.hash==='#queue'?'active':''}">待测权重清单 <b>${M.pendingRows(board).length}</b></a><div class="nav-divider"></div>`+items.map(t=>`<a class="${location.hash.startsWith('#task/'+t.id)?'active':''}" href="#task/${t.id}"><span>${esc(t.name)}<small>${esc(t.sub)}</small></span><b>${board.rows.filter(r=>r.task===t.id).length}</b></a>`).join('')+`<div class="nav-divider"></div><a href="#updates" class="${location.hash==='#updates'?'active':''}">共享更新 <b>${shared.length}</b></a><a href="#collection" class="${location.hash==='#collection'?'active':''}">采集 / Agent 进度</a>`;}
function scoreHTML(score){if(!score)return '<span class="no-score">—<small>尚无已核对结果</small></span>';return `<strong class="score">${(100*score.success/score.trials).toFixed(1)}<small>%</small></strong><span class="score-meta">${score.success}/${score.trials} · ${esc(score.label)}${score.unknown?` · ${score.unknown}无法判定`:''}</span>`;}
function render(){if(!board)return;nav();const page=location.hash.slice(1).split('/')[0];if(!page||page==='overview')return renderOverview();if(page==='queue')return renderQueue();if(page==='updates')return renderUpdates();if(page==='collection')return renderCollection();renderTask();}
function compactScore(score){return score?`${(100*score.success/score.trials).toFixed(1)}% <small>(${score.success}/${score.trials}${score.unknown?' · '+score.unknown+'无法判定':''})</small>`:'<span class="muted">未测 / 待归档</span>';}
function auditNote(task){return (data.coverage_notes||[]).filter(n=>n.task===task).map(n=>`<div class="notice audit-note"><strong>${esc(n.method)} · ${esc(n.state)}</strong><p>${esc(n.note)}</p></div>`).join('');}
function overviewCell(rows){
 if(!rows.length)return '<span class="not-delivered">交付 / 评测记录待核对</span>';
 const step=Math.max(...rows.map(r=>r.step)),latest=rows.filter(r=>r.step===step);
 return latest.map(r=>`<button class="summary-cell" data-detail="${esc(r.key)}"><strong>${r.step?(r.step/1000)+'k':'权重待补'}</strong> ${badge(r.state)}<small class="secondary">${esc(r.h4?.label||r.h8?.label||'结果待核对')}</small><span>4步　${compactScore(r.h4)}</span><span>8步　${compactScore(r.h8)}</span></button>`).join('')+(rows.filter(r=>r.state==='untested').length?`<a class="secondary" href="#queue">该方法 ${rows.filter(r=>r.state==='untested').length}份权重待测 →</a>`:'');
}
function renderOverview(){
 $('#crumb').textContent='各任务 / 各方法 · 测试成功率';
 const methods=['Mem-0','TTC（ours）','pi0.5','MemoryVLA'];
 $('#main').innerHTML=`<div class="page-title"><div><p class="eyebrow">一张表看测试，一张清单安排部署</p><h1>各任务测试成功率</h1><p class="muted">按数据版本和相机分别对齐；每个方法展示最新训练步数；SR任务成功率与严格验收分别标注，详情保留全部实验。</p></div><a class="primary button-link" href="#queue">${M.pendingRows(board).length}份权重待测 →</a></div><div class="quick-actions"><button data-new>＋ 训练同学：交付新权重与数据集</button><a href="#queue">评测同学：查看所有待测内容 →</a></div>
 ${M.TASKS.map(t=>`<section class="camera-group"><div class="group-title"><h2>${esc(t.name)} · ${esc(t.sub)}</h2><a href="#task/${t.id}">查看全部权重 / 更新交接 →</a></div>${auditNote(t.id)}<div class="table-scroll"><table class="overview-table"><thead><tr><th>训练数据版本 / 输入相机</th>${methods.map(m=>`<th>${esc(m)}</th>`).join('')}</tr></thead><tbody>${versionList(t.id).map(d=>['third_person','chest','unknown'].filter(c=>board.rows.some(r=>r.dataset===d.id&&r.camera===c)).map(c=>{const rows=board.rows.filter(r=>r.dataset===d.id&&r.camera===c),variants=rows.filter(r=>!methods.includes(r.method));return `<tr><td><a href="#task/${t.id}/${esc(d.id)}"><strong>${esc(d.version)}</strong></a><span class="secondary">${esc(camera(c))}</span>${variants.length?`<span class="secondary">其他变体：${variants.map(r=>esc(r.method)).join('、')}</span>`:''}</td>${methods.map(m=>`<td>${overviewCell(rows.filter(r=>r.method===m))}</td>`).join('')}</tr>`;}).join('')).join('')}</tbody></table></div></section>`).join('')}
 <p class="footnote">未登记交付不等于未训练；训练同学可直接新增。0%是已测结果，空白表示缺少已归档成绩。<br>评测记录最近核对：${esc(dt(data.evaluation_audit?.checked_at||data.updated_at))}；团队新增和状态更新以共享交接单为准。${data.evaluation_audit?`本次已回读8个会话的${data.evaluation_audit.visible_messages_read.toLocaleString()}条可见消息；不同验收口径不可直接横比。`:""}</p>`;
}
function renderQueue(){
 $('#crumb').textContent='全局待测权重 · 安排部署';const pending=M.pendingRows(board),verify=board.rows.filter(r=>r.state==='verify');
 $('#main').innerHTML=`<div class="page-title"><div><p class="eyebrow">训练已交付 → 等待部署评测</p><h1>待测权重清单 <span>${pending.length}份权重</span></h1><p class="muted">这里集中列出已登记路径、尚未测试的权重。认领后更新为评测中，即移出待测清单。</p></div><button class="primary" data-new>＋ 新增权重</button></div><div class="notice">部署前查看交付说明，确认基座、归一化、输入相机与测试条件。点击「复制测试交接」可带走权重、数据集、配置和负责人信息；路径可用性仍以服务器核验为准。</div>
 ${[...M.TASKS,{id:'other',name:'待归属'}].filter(t=>pending.some(r=>r.task===t.id)).map(t=>`<section class="camera-group"><div class="group-title"><h2>${esc(t.name)}</h2><span>${pending.filter(r=>r.task===t.id).length}份待测</span></div><div class="table-scroll"><table><thead><tr><th>数据版本 / 相机</th><th>方法 / 权重</th><th>交付信息</th><th>部署测试</th></tr></thead><tbody>${pending.filter(r=>r.task===t.id).map(r=>{const d=board.datasets.find(d=>d.id===r.dataset);return `<tr data-pending="${esc(r.key)}"><td><strong>${esc(d?.version||r.dataset)}</strong><span class="secondary">${esc(camera(r.camera))}</span></td><td><strong>${esc(r.method)}</strong><span class="secondary">${r.step.toLocaleString()} step · ${esc(r.owner)}</span></td><td><details><summary>权重与训练数据路径</summary>${path(r.path)}${path(d?.path)}</details><span class="secondary">${esc(r.availability)}</span></td><td><div class="row-actions"><button class="primary" data-packet="${esc(r.key)}">复制测试交接</button><button data-detail="${esc(r.key)}">交付详情</button><button data-edit="${esc(r.key)}">认领 / 开始评测</button></div></td></tr>`;}).join('')}</tbody></table></div></section>`).join('')||'<div class="empty">当前没有已交付待测权重。</div>'}
 <details class="queue-other"><summary>另有 ${verify.length}条信息待核验（尚不能作为明确待测交付）</summary>${verify.map(r=>`<p>${esc(r.method)} · ${esc(board.datasets.find(d=>d.id===r.dataset)?.version||'数据集待确认')} · ${esc(camera(r.camera))} <button data-detail="${esc(r.key)}">查看缺失信息</button></p>`).join('')}</details>`;
}
function renderTask(){
 const task=M.TASKS.find(t=>t.id===selectedTask)||{name:'待归属',sub:'需要补齐训练数据、相机或权重'};const versions=versionList(selectedTask);
 if(!versions.some(d=>d.id===selectedVersion))selectedVersion=versions[0]?.id||'unknown';
 const d=board.datasets.find(d=>d.id===selectedVersion);
 const taskRows=board.rows.filter(r=>r.task===selectedTask);
 let rows=taskRows.filter(r=>r.dataset===selectedVersion);
 if(selectedTask==='other')rows=taskRows;
 const total=rows.length,has=rows.filter(r=>r.h4||r.h8||r.evaluations.some(e=>e.success!==null)).length;
 $('#crumb').textContent=task.name+' / '+(d?.version||'待确认版本');
 $('#main').innerHTML=`<div class="page-title"><div><p class="eyebrow">任务 → 数据版本 → 相机 → 权重</p><h1>${esc(task.name)}<span>${esc(task.sub)}</span></h1></div><button class="primary" data-new>＋ 新增本任务权重</button></div>
 <div class="version-tabs">${versions.map(v=>`<a href="#task/${selectedTask}/${esc(v.id)}" class="${selectedVersion===v.id?'active':''}"><strong>${esc(v.version)}</strong><small>${v.episodes??'待核对'}条数据 · ${board.rows.filter(r=>r.dataset===v.id).length}个条目</small></a>`).join('')}</div>
 ${d?`<section class="dataset-box"><div><span class="caption">当前训练数据版本</span><h2>${esc(d.slug||d.label)}</h2><p>${esc(d.note)}</p></div><details><summary>数据路径与来源</summary>${path(d.path)}<p class="muted">${esc(d.source||'团队新增版本')}</p></details></section>`:'<div class="notice">以下条目尚未绑定明确的数据版本，补齐后会进入对应任务。</div>'}
 <div class="counts"><button data-state="all" class="${statusFilter==='all'?'chosen':''}"><span>当前版本条目</span><b>${total}</b></button><button data-state="untested" class="${statusFilter==='untested'?'chosen':''}"><span>已交付待评测</span><b>${rows.filter(r=>r.state==='untested').length}</b></button><button data-state="evaluating" class="${statusFilter==='evaluating'?'chosen':''}"><span>评测 / 复测中</span><b>${rows.filter(r=>r.state==='evaluating').length}</b></button><button data-state="results" class="${statusFilter==='results'?'chosen':''}"><span>已有成绩的权重</span><b>${has}</b></button></div>
 <div class="toolbar"><div class="filters">${allStates.map(s=>`<button data-state="${s}" class="${statusFilter===s?'selected':''}">${s==='all'?'全部':M.STATES[s]}</button>`).join('')}</div><input id="search" placeholder="查找方法、训练步数、负责人…" aria-label="搜索权重" value="${esc(query)}"></div>
 ${auditNote(selectedTask)}<div id="weight-groups"></div><div class="footnote">4步 / 8步指每次执行的动作步数。成绩绑定本行权重与相机；不同条件的历史成绩在详情中分别列出。<br>结果基线核对于 ${esc(dt(data.updated_at))}；「评测中」依据该来源快照，最新团队状态见共享更新。</div>`;
 const missing=['Mem-0','TTC（ours）','pi0.5','MemoryVLA'].filter(method=>!taskRows.some(r=>r.dataset===selectedVersion&&r.method===method));
 if(missing.length){const box=document.createElement('div');box.className='missing-methods';box.textContent='本版本交付 / 评测记录待核对：'+missing.join('、')+'。如训练已完成，请新增权重。';$('#weight-groups').after(box);}
 renderRows(rows);
 $('#search').oninput=e=>{query=e.target.value;renderRows(rows);};
}
function filtered(rows){const q=query.toLowerCase().trim();return rows.filter(r=>(statusFilter==='all'||statusFilter==='results'?(statusFilter==='all'||r.h4||r.h8||r.evaluations.some(e=>e.success!==null)):r.state===statusFilter)&&(!q||[r.method,r.step,r.path,r.owner,r.run].join(' ').toLowerCase().includes(q)));}
function renderRows(all){
 const rows=filtered(all);const groups=['third_person','chest','unknown'].filter(c=>rows.some(r=>r.camera===c));
 $('#weight-groups').innerHTML=groups.length?groups.map(c=>`<section class="camera-group"><div class="group-title"><h2>${esc(camera(c))}</h2><span>${rows.filter(r=>r.camera===c).length}个交接条目 · 相同视角单独评测</span></div><div class="table-scroll"><table><thead><tr><th>方法 / 训练权重</th><th>当前状态</th><th>执行4步</th><th>执行8步</th><th>交接负责人</th><th>操作</th></tr></thead><tbody>${rows.filter(r=>r.camera===c).map(r=>`<tr data-row="${esc(r.key)}"><td><strong>${esc(r.method)}</strong><span class="secondary">${r.step?r.step.toLocaleString()+' step':'尚无具体权重'}</span>${r.shared?'<span class="team-mark">团队更新</span>':''}</td><td>${badge(r.state)}${r.state==='evaluating'&&(r.h4||r.h8)?'<span class="secondary">历史成绩已保留</span>':''}${!r.path?'<span class="secondary">交付信息未齐</span>':''}</td><td>${scoreHTML(r.h4)}</td><td>${scoreHTML(r.h8)}</td><td>${esc(r.owner)}<span class="secondary">${r.shared?esc(dt(r.updated)):'基线快照'}</span></td><td><div class="row-actions"><button data-detail="${esc(r.key)}">详情</button><button data-edit="${esc(r.key)}">编辑交接</button></div></td></tr>`).join('')}</tbody></table></div></section>`).join(''):'<div class="empty">该筛选下暂无条目。可切换状态或新增权重。</div>';
}
function openDetail(key){
 const r=board.rows.find(r=>r.key===key);if(!r)return;const d=board.datasets.find(d=>d.id===r.dataset);
 $('#detail-body').innerHTML=`<p class="eyebrow">${esc(M.TASKS.find(t=>t.id===r.task)?.name||'待归属')} / ${esc(d?.version||r.dataset)} / ${esc(camera(r.camera))}</p><h2>${esc(r.method)} · ${r.step?r.step.toLocaleString()+' step':'交付待补'}</h2>${badge(r.state)}<p>${esc(r.note)}</p><h3>训练与交付</h3><dl><dt>训练数据</dt><dd>${esc(d?.slug||d?.label||'待确认')}</dd><dt>相机</dt><dd>${esc(camera(r.camera))}</dd><dt>负责人</dt><dd>${esc(r.owner)}</dd><dt>训练 run</dt><dd>${esc(r.run||'待提供')}</dd><dt>可用性</dt><dd>${esc(r.availability)}</dd></dl><h4>权重路径</h4>${path(r.path)}<h4>训练数据路径</h4>${path(d?.path)}<h4>交付说明</h4>${path(r.doc)}
 <details><summary>查看完整训练配置与归一化信息</summary><pre>${esc(JSON.stringify({training:r.training,normalization:r.record?.norm||'待核对'},null,2))}</pre></details><h3>评测记录</h3><p class="muted">不同协议分别保留。历史多环境差异实验不替代当前闭环结果。</p>
 ${r.shared?`<div class="notice">${safeLink(r.shared.url,'共享交接单 #'+r.shared.issue)} · ${esc(r.shared.author)} · ${esc(dt(r.shared.updated))}<p>${esc(r.shared.protocol||'尚未填写评测条件')}</p><div class="inline-scores">4步 ${scoreHTML(r.h4)}　8步 ${scoreHTML(r.h8)}</div></div>`:''}
 ${r.evaluations.length?`<div class="table-scroll"><table class="evidence"><thead><tr><th>执行步数 / 实验</th><th>结果</th><th>条件 / 来源</th></tr></thead><tbody>${r.evaluations.map(e=>`<tr><td>H${e.horizon}<span class="secondary">${esc(e.kind)}<br>${esc(e.status)}</span></td><td>${e.success===null?(e.progress?e.progress.map(p=>`${p.condition==='single'?'单环境':'并发'}：${p.success}/${p.audited}已测，目标${p.target}`).join('<br>'):'尚无成绩'):`${e.success}/${e.trials}<span class="secondary">${e.unknown}条无法判定</span>`}</td><td><p>${esc(e.protocol)}</p>${e.report_url?safeLink(e.report_url,'原实验报告 / 视频'):''}<details><summary>原始结果文件</summary><code>${esc(e.source)}</code><p>${esc(e.note||'')}</p></details></td></tr>`).join('')}</tbody></table></div>`:'<div class="empty">尚未归档该权重的环境评测结果。</div>'}
 <p class="footnote">原始交付来源：${esc(r.source)}</p><div class="dialog-actions"><button class="primary" data-edit="${esc(r.key)}">更新状态 / 补充交接</button></div>`;
 $('#detail').showModal();
}
function renderUpdates(){
 $('#crumb').textContent='共享更新';
 $('#main').innerHTML=`<div class="page-title"><div><p class="eyebrow">团队共同维护</p><h1>共享交接动态</h1><p class="muted">新增权重、认领评测和填写成绩，都通过 GitHub 交接单保存。</p></div><button class="primary" data-new>＋ 新增训练权重</button></div><div class="notice">填写表单 → 到 GitHub 点击 Submit new issue → 返回本页同步。仓库协作者直接生效；外部提交由维护者添加 safelab-approved 标签后生效。关闭交接单会保留记录，添加 safelab-archived 标签才移出面板。</div><div class="steps"><div><b>01</b><strong>训练同学交付</strong><p>选择任务、数据版本与相机，填写权重和文档路径。</p></div><div><b>02</b><strong>评测同学接手</strong><p>点击权重行的编辑交接，填写负责人并选择评测中。</p></div><div><b>03</b><strong>结果回到同一条目</strong><p>补充4/8步成绩与测试条件。历史原始成绩始终保留。</p></div></div>
 <section class="camera-group"><div class="group-title"><h2>共享记录 ${shared.length}</h2><span>${lastSync?'同步于 '+esc(dt(lastSync)):'尚未成功同步'}${feedError?' · 同步异常':''}</span></div>${feedError?`<p class="error padded">${esc(feedError)}</p>`:''}${shared.length?shared.slice().sort((a,b)=>b.updated.localeCompare(a.updated)).map(e=>`<article class="update"><div>${badge(e.trusted?'results':'verify',e.trusted?'已进入交接台':'待维护者确认')} ${safeLink(e.url,'#'+e.issue+' '+e.method+' · '+e.step+' step')}</div><p>${esc(e.version)} · ${esc(camera(e.camera))} · ${esc(M.STATES[e.state])} · ${esc(e.owner||'未指定负责人')}</p><small>${esc(e.author)} · ${esc(dt(e.updated))}</small></article>`).join(''):'<div class="empty">暂时没有共享新增记录。上方「新增训练权重」提交后会出现在这里。</div>'}</section><p class="footnote">共享数据来自 ${safeLink(REPO+'/issues','GitHub Issues')}。未成功保存或未通过校验的记录不会改变权重表。页面每5分钟同步一次，切回本页也会检查更新。</p>`;
}
function renderCollection(){
 $('#crumb').textContent='采集 / Agent 进度';$('#main').innerHTML=`<div class="page-title"><div><p class="eyebrow">后台证据 · ${esc(dt(data.updated_at))}</p><h1>采集与 Agent 进度</h1><p class="muted">以下是来源快照；训练权重交接请回到具体任务。</p></div></div><h2>采集工作</h2><div class="progress-grid">${data.collection.map(c=>`<article><h3>${esc(c.title)}</h3>${badge('verify',c.status)}<p>${esc(c.count)}</p><p>${esc(c.detail)}</p><small>${esc(c.source)}</small></article>`).join('')}</div><h2>Agent 来源记录</h2><div class="progress-grid">${data.agents.map(a=>`<article><h3>${esc(a.title||a.role||a.id)}</h3><p>${esc(a.summary||a.latest_summary||a.latest_message||a.last_message_summary||'')}</p><details><summary>来源详情</summary><pre>${esc(JSON.stringify(a,null,2))}</pre></details></article>`).join('')}</div><h2>历史视频与诊断面板</h2><div class="links">${data.links.map(l=>safeLink(l.url,l.label)).join('')}</div>`;
}
function populateVersions(task,chosen){const select=$('[name="dataset"]');select.innerHTML=versionList(task).map(d=>`<option value="${esc(d.id)}">${esc(d.version)}</option>`).join('')+'<option value="__new">＋ 新的数据版本</option>';select.value=chosen||select.options[0].value;toggleNew();}
function toggleNew(){const fresh=$('[name="dataset"]').value==='__new';document.querySelectorAll('.new-version').forEach(el=>el.hidden=!fresh);for(const k of ['new_dataset','version'])$('[name="'+k+'"]').required=fresh;}
function openEditor(key){
 const row=key?board.rows.find(r=>r.key===key):null;
 $('#detail').close();const form=$('#edit-form');form.reset();$('#edit-error').textContent='';$('#editor-title').textContent=row?'更新这份权重的交接':'新增训练权重';
 const task=row?.task||selectedTask;form.elements.task.value=task;populateVersions(task,row?.dataset||selectedVersion);
 const values={target:row?.path?row.key:'',camera:row?.camera||'third_person',method:row?.method||'',step:row?.step||'',path:row?.path||'',doc:row?.doc||'',state:row?.state||'untested',run:row?.run||'',owner:row?.owner==='未指定'?'':row?.owner||'',note:row?.note||'',h4:row?.shared?.h4||'',h8:row?.shared?.h8||'',h4unknown:row?.shared?.h4unknown||0,h8unknown:row?.shared?.h8unknown||0,protocol:row?.shared?.protocol||''};
 for(const [k,v] of Object.entries(values))form.elements[k].value=v;
 // Existing weight identity is read-only. Use a new record for a new run, camera or dataset.
 for(const k of ['task','dataset','camera','method','step','path'])form.elements[k].disabled=!!row&&!!row.path;
 $('#editor').showModal();
}
function submitEdit(event){
 event.preventDefault();const f=$('#edit-form'),v=n=>f.elements[n].value.trim();const d=board.datasets.find(d=>d.id===v('dataset'));const fresh=v('dataset')==='__new';
 const edit={schema:2,kind:'checkpoint',target:v('target'),task:v('task'),dataset:fresh?v('new_dataset'):v('dataset'),version:fresh?v('version'):d?.version||'',data_path:fresh?v('data_path'):d?.path||'',camera:v('camera'),method:/^(TTC|ours)$/i.test(v('method'))?'TTC（ours）':v('method'),step:Number(v('step')),path:v('path'),doc:v('doc'),state:v('state'),owner:v('owner'),run:v('run'),note:v('note'),h4:v('h4'),h8:v('h8'),h4unknown:Number(v('h4unknown')),h8unknown:Number(v('h8unknown')),protocol:v('protocol')};
 try{M.validateEdit(edit);const body=M.issueBody(edit);const url=new URL(REPO+'/issues/new');url.searchParams.set('title','[交接] '+edit.version+' / '+edit.method+' / '+edit.step);url.searchParams.set('body',body);
 if(url.href.length>8100){navigator.clipboard.writeText(body).then(()=>{window.open(REPO+'/issues/new','_blank','noopener');toast('交接内容较长，已复制。请在 GitHub 正文中粘贴后提交。');}).catch(()=>{$('#edit-error').textContent='内容过长，请缩短备注或路径后重试。';});return;}
 window.open(url.href,'_blank','noopener');toast('请在 GitHub 确认提交，返回后点击同步更新。');
 }catch(e){$('#edit-error').textContent=e.message;}
}
async function sync(){
 if(syncing||!data)return;syncing=true;$('#sync').disabled=true;$('#sync-status').textContent='正在同步共享交接单…';
 try{const issues=[];let complete=false;for(let page=1;page<=10;page++){
  const response=await fetch(`https://api.github.com/repos/asimfish/safelab-handoff/issues?state=all&per_page=100&sort=created&direction=asc&page=${page}`,{headers:{Accept:'application/vnd.github+json'},cache:'no-store',signal:AbortSignal.timeout(20000)});
  if(!response.ok)throw Error(response.status===403||response.status===429?'GitHub读取额度暂时受限，请稍后同步。':'GitHub共享记录读取失败（'+response.status+'）。');
  const batch=await response.json();if(!Array.isArray(batch))throw Error('共享数据格式不正确');issues.push(...batch);if(batch.length<100){complete=true;break;}}
  if(!complete)throw Error('共享记录超过1000条，需扩展同步分页。当前保留上次完整读取。');
  rawIssues=issues;shared=issues.map(M.parseIssue).filter(Boolean);lastSync=new Date().toISOString();feedError='';rebuild();
  $('#sync-status').textContent='共享已同步 · '+shared.length+'条 · '+dt(lastSync);
 }catch(e){feedError=e.message;$('#sync-status').textContent='共享同步失败 · 显示基线/上次记录';if(location.hash==='#updates')renderUpdates();toast(feedError);}finally{syncing=false;$('#sync').disabled=false;}
}
async function start(){try{const response=await fetch('data.json',{cache:'no-store'});if(!response.ok)throw Error('基线数据加载失败');data=await response.json();if(data.schema_version!==1||!Array.isArray(data.datasets)||!Array.isArray(data.records)||!Array.isArray(data.evaluations))throw Error('基线格式不符');board=M.buildBoard(data);route();await sync();}catch(e){$('#main').textContent=e.message;$('#sync-status').textContent='加载失败，请刷新重试';}}
$('#add').onclick=()=>openEditor();$('#sync').onclick=sync;$('#edit-form').onsubmit=submitEdit;
$('[name="task"]').onchange=e=>populateVersions(e.target.value);$('[name="dataset"]').onchange=toggleNew;
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.packet){const row=board.rows.find(r=>r.key===b.dataset.packet);if(row)navigator.clipboard.writeText(JSON.stringify(M.handoffPacket(board,row),null,2)).then(()=>toast('已复制测试交接信息：数据、权重、相机和配置')).catch(()=>toast('复制失败，请在详情中逐项复制'));}if(b.dataset.close)$('#'+b.dataset.close).close();if(b.hasAttribute('data-new'))openEditor();if(b.dataset.detail)openDetail(b.dataset.detail);if(b.hasAttribute('data-edit'))openEditor(b.dataset.edit);if(b.dataset.state){statusFilter=b.dataset.state;render();}if(b.dataset.copy)navigator.clipboard.writeText(b.dataset.copy).then(()=>toast('已复制路径')).catch(()=>toast('请选中路径复制'));});
window.addEventListener('hashchange',()=>{query='';statusFilter='all';route();});
let lastAutoSync=0;document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-lastAutoSync>60000){lastAutoSync=Date.now();sync();}});setInterval(()=>{if(!document.hidden)sync();},300000);
start();
