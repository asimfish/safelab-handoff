# SafeLab 媒体清单 v1

Refs: T-1263。供评测 agent 发布、交接台合并、对比页每 5 分钟消费。与 [SafeLab-Eval-v1](evaluation-schema-v1.md) 配套；历史素材不得追认 v1。规范只登记来源和展示证据，不改变物理验收。

## 发布位置与上限

- 交接台 `media/index.json` 是唯一入口，schema 为 `safelab-media-index-v1`，含 `updated_at` 及 `manifests:[{url,sha256,updated_at}]`。也可由 data.json 的 `media_manifest_index` 显式指定 HTTPS 索引地址。
- 每个 agent 提交小型清单 `media/manifests/<task>/<run>.json`（`safelab-media-v1`）；只维护自己的文件和索引项，PR 保留其他 agent。每清单 ≤1 MB，索引 ≤256 KB，最多80清单；单清单最多2000案例。
- **视频放授权对象存储的稳定公开只读 HTTPS 路径** `safelab-public/media-v1/<task>/<record>/<checkpoint>/<condition>/<case_id>/`，不得把整批二进制提交 Pages。视频直接用无crossorigin的video.src播放，不要求bucket CORS；不得用fetch→blob或canvas/WebGL取视频像素作为播放前置条件。清单、索引与逐帧JSON仍必须同源或允许CORS GET；不得使用需要登录或含 token 的临时签名链接。SHA-256 是文件实际字节，不是源视频或解压前后混用的摘要。
- 每视频 H.264 MP4、yuv420p、faststart、**≤2,000,000 bytes**；优先640×480/15Hz，保留完整时间范围并记录真实 fps，禁止删去失败或静止时段而不修改时钟元数据。转码后重新计算 hash。例：`ffmpeg -i input.mp4 -an -c:v libx264 -crf 30 -pix_fmt yuv420p -movflags +faststart preview.mp4`；超限继续降低码率/分辨率并核验完整时长，不以该命令保证体积。
- 每逐帧 JSON ≤2 MB；选择低冗余必需字段，观察频率采样（任何抽稀均须满足下述事件/累计器保真限制），物理事件保留原始精确 t_sim。原120Hz日志和高清全量录像仍留原存储，清单只发布派生的去敏只读日志。不得以超限为由删去切换或物理事件。
- 原有已发布400条录像和日志为 legacy 兼容入口，**不要求复制或重新转码**；新增媒体执行上述上限。Pages 仓库允许小清单及下述有总预算的逐帧日志，新增清单总预算≤20 MB；超出时索引指向对象存储。

## 每个 case 一条记录

见 [JSON Schema](media-manifest-v1.schema.json)。必填：

| 字段 | 含义 |
|---|---|
| case_id / task | 唯一案例ID；任务字符串3/5/7/10 |
| record / issue | canonical data.json record id或交接单号；两个键都存在，至少一个非null，配置不能仅靠方法名匹配 |
| checkpoint / horizon | 实际权重步数、执行步数4/8/30；30只保留既有历史 |
| protocol_version / oracle_version / evaluation_id / condition_version / stage | 精确协议与评测行ID、接触条件不可变版本、A/B/diagnostic/legacy；attach不能冒充original |
| scene_id / scene_list_hash / side / seed | 相同初始场景的稳定ID、有序100场景列表哈希、left/right或forward/reverse、推理seed；对照必须哈希、场景和seed一致 |
| outcome / max_phase | success/fail/unknown；物理oracle最大完成阶段数，未知null，不能由Planner序号推断 |
| videos | third_person/head/chest三个键均存在，缺视角null；资产为{url,sha256,bytes}，记录转码后文件。旁观与策略输入视角不能混淆 |
| frame_log | {url,sha256,bytes}或null，引用逐帧JSON；没有日志就null |
| render_config_hash | 相机外参、内参、光照、渲染配置序列化后的SHA256，禁止猜测 |
| timebase | {fps,video_time_origin_s,log_time_origin_s}；video.currentTime=t_sim-log_time_origin_s+video_time_origin_s。所有视角必须同步、无独立剪辑 |
| subtask_physical_targets | 第i条指令应完成的oracle阶段编号数组；无法证明语义映射为null，不计算切换错误率 |

清单 `schema_version:safelab-media-v1, updated_at:ISO8601, cases:[...]`。不得包含 SSH、私有磁盘路径、提示词、密钥或原始RPC。公共URL不得含用户名/密码、签名、访问令牌。发布者与消费端必须先用URL解析器拒绝userinfo、查询参数、片段、localhost/私有IP/内网域名；该语义校验不由JSON Schema的format:uri替代。另须校验case_id唯一、日志时钟严格递增、体积与bytes/SHA/真实时长及采样数量，不得只跑schema就宣称通过。客户端核验清单和日志hash仅证明字节身份，不等于科学验收。视频仍由发布者核验转码后SHA/bytes，并交维护者复核；直连播放器必须标注浏览器未核验视频SHA，不得显示“视频SHA通过”。

## 逐帧日志

[Schema](media-frame-log-v1.schema.json)：`{schema_version:"safelab-frame-log-v1",case_id,rows:[...]}`。每行所有字段必须存在：

`t_sim, frame, subtask_index, completion_score, threshold, positive_count, switched, physical_phase, physical_events`。

- `t_sim` 为从该 episode 开始的真实仿真秒，`frame`递增，`subtask_index`零起。阈值/分数/阳性计数缺失都用null，不能补0。Mem-0可仅有切换事件；pi0.5没有子任务分类器时同样null。
- `completion_score`为实际分类器输出；缓存分数可以保留，**不能把每个缓存帧当作一次新分类器调用**。`positive_count`仅取真实累计器日志，不根据分数重建。切换帧的score/threshold/positive_count属于**切换前指令**，`subtask_index`是切换后位置。
- `switched`为实际Planner指令切换，不是物理完成；初始指令不是一次切换。无法判定为null。
- `physical_phase`为原oracle累计完成阶段数，独立于Planner。`physical_events:[{t_sim,phase,event}]`只在首次完成时写入该观测间隔内真实事件，已记录且无事件为[]，整条未记录为null。
- 保留末帧和所有切换。t_sim与frame严格递增；所有视频完整覆盖日志时间；物理oracle名称和版本由evaluation_id对应的protocol说明。

## 代表案例采样与配对

每配置（record+ckpt+horizon+condition_version+stage）至少8条：4成功、4失败；每类优先左/右或正/反各2条。无成功时选阶段最高的4条，加4条其他失败；不足4成功时选全部成功，其余补阶段最高失败。报告实际成功/失败/unknown和左右数，不复制同一case凑数，unknown不冒充失败。候选不足8条则明确不足并等待后续发布。

优先各方法共享scene_id，且scene_list_hash、seed、condition_version、stage均相同；同任务同清单不意味着每种方法都已发布同scene。每栏保留各自checkpoint/执行步数，数据版本、策略相机、render_config_hash不同则不进入同一自动配对组，不能拿另一配置补空。对比页仅展示真正共同场景；缺pi0.5显示未发布，不把Mem-0复制成第三栏。

## 切换错误率的展示定义

仅在有明确subtask_physical_targets且oracle日志完整时统计。对非末条指令i：提前切换=离开i时对应目标oracle阶段尚未达到；分母为已观察到的有效离开事件。该切未切=oracle首次达到i目标阶段、但到轨迹结束没有离开i；分母为已达到目标且曾进入i的非末条指令。临近末帧未留观察窗口须显式标记右删失，不计该切未切分母；窗口长度作为诊断参数发布，不追改正式SR。延迟秒数另外报告。

这些是视频诊断定义，不是成功判定，不与不同oracle/协议的数据混算。目标语义或日志不完整显示未发布。历史3任务SR400使用其原task_event_sr_v1 oracle，永远标legacy；不能当作SafeLab-Eval-v1结论。

## 合并与验证

1. 评测 agent 先校验自己清单、逐帧schema及实际SHA/时长/采样数量，上传只读对象。
2. PR 添加自己的清单及索引项；交接台 agent 核对配置绑定、验收协议、公开URL、体积与SHA后合并。
3. 客户端每5分钟读取 data.json 与 media/index.json，逐清单检查 SHA。数据源分别显示更新时间；失败保留上次内容并标明旧快照。
4. 完整v1成绩仍由evaluations和准入门槛决定；代表视频不得反推整组成功率。


## 跨域播放与同源日志托管（2026-11-03 第2轮）

### Origin 与播放器

`https://asimfish.github.io/psibot-dashboard/` 与 `https://asimfish.github.io/safelab-handoff/` 的origin都是 `https://asimfish.github.io`：路径和仓库名不同不构成跨域。因此索引、manifest及日志优先直接放交接台Pages；视频继续放public-read对象存储。视频标签**不设crossorigin**，不以fetch/blob/HEAD/hash校验阻塞播放，不用canvas/WebGL取视频帧；图表canvas只绘制JSON数值。以currentTime/真实timebase联播。匿名GET可播不保证Range、编码、Content-Type正确，发布者仍须验证实际浏览器播放、拖动和完整时长。

### 日志路径、压缩和哈希

- 日志提交 `media/frame_logs/<task>/<run>/<case_id>.json` 或 `.json.gz`，通过PR由交接台核验后合并。manifest使用完整稳定公开URL；SHA/bytes必须匹配**URL实际文件**。禁止带凭据、签名查询串及私有路径。
- 首选紧凑JSON；需要压缩时 `gzip -n -9`，`.json.gz`作为静态gzip文件发布，**不要设置Content-Encoding:gzip**，推荐Content-Type:application/gzip。客户端先校验下载gzip字节的bytes/SHA，再显式流式解压、解析、校验case_id与行结构。若HTTP自动解压导致哈希与清单不符，应拒绝，不能跳过校验。
- 每个上传文件≤2,000,000 bytes，解压后JSON亦≤2,000,000 bytes；日志最多60,000行。解压须流式限额，防止压缩炸弹。缺日志=null；无解压能力的旧浏览器显示不支持，不阻塞视频。
- 不压缩/抽稀原始实验档案。派生日志可降采样，但必须额外保留首末帧、全部实际切换、指令/阳性累计器变化、物理阶段变化与原始事件精确t_sim；不得平滑分数、重建阳性计数或漏掉末端事件。文档/清单来源注明原始采样频率与派生规则。事件时钟与视频范围保持不变。

### 仓库预算（提交交接台确认）

新增 `media/frame_logs/` 的**所有任务合计上限50,000,000 bytes（50MB）**，按git跟踪的上传文件字节计，不是每任务50MB；包含本次PR与此前已合并日志。清单索引另遵守已有20MB预算，视频不得新增进Pages。原已发布SR400等legacy资产留原位置，不复制、不迁移，不计入新frame_logs预算。Git历史不会因删除自动缩小，禁止频繁覆盖/重复提交同日志；使用不可变文件并按需发布代表案例。

交接台合并前统计 `git ls-files media/frame_logs/` 中每个文件实际字节与PR新增字节，要求合计不超50MB，并检查单文件及解压上限。临近上限先gzip去冗余；仍超限时按保真规则抽稀或减少重复视角对应的同一日志（每case只存一份）。仍不足则暂停新增、交协调者批准独立日志托管/CORS，不能通过不断换路径绕过预算，也不得无确认改变bucket权限。

首批测量依据：十任务CPU导出MEDIA_PREP_PROGRESS回执，48份、64,406行，共11,584,309 bytes（11.58MB；单份27,120–794,074，均值241,339.77）。这是导出字节总数，**不是已发布或gzip实测**。同一case的两个视频共享一份日志，不重复96份。其他三任务尚无已发布同格式首批清单；按同均值估算8case/配置约1.93MB，若每任务48case约11.58MB，四任务合计约46.34MB，距50MB仅3.66MB；这些是容量估算，不是已采样数量。实际合并时按文件重新统计。所有任务更多配置一律不能据此假定仍可放下，优先gzip并提交实际压缩大小回执。

## 放置判定v1.1与strict-v1隔离

用户已选择正式**放置判定**：物体到目标区域、直立、已放下，三者连续0.25秒；不要求角速度稳定。新正式结果/媒体使用明确 `protocol_version:"SafeLab-Eval-v1.1"` 与 `oracle_version:"placement-v1.1"`，保留阶段A/B、完整分母/seed/左右拆分等要求；必须通过现行标准五项准入，含新增 `admission.executor_parity:{passed:true,report:"非空执行链回放报告"}`。缺新判定字段或第五项准入不得进入主表。执行链RMSE≤0.005rad、左右各5条及端点成功条件以[正式评测约定](evaluation-schema-v1.md)为准。物理报告记录区域和直立/释放阈值及oracle代码版本。旧strict媒体可省略oracle_version以兼容；若提供必须为strict-v1，protocol与oracle错配拒绝。原 `SafeLab-Eval-v1` 始终表示strict-v1；不得覆盖原行、复用旧id或仅因数值更好而重命名。现有 `rescored_v1.1_candidate` **漂移候选作废**，即便误填A/B或新协议也不得进入主表。

如果旧录像有足够逐帧物理证据，可另建v1.1 evaluation（唯一新id、source_evaluation_id及可审计报告），重新计算结局、阶段直方图、oracle逐帧事件并引用精确新evaluation_id；视频字节可复用，旧strict日志不可冒充v1.1日志。证据不足则重跑，不能推测放置判定是否通过。

消费端：某任务出现完整且通过准入的v1.1结果后默认v1.1；可手动切strict-v1，保留该任务的显式选择。protocol_version纳入排名cohort、媒体绑定与同场景配对键，绝不跨判定混算。没有v1.1正式结果时继续strict-v1并明确所选口径。unknown仍在success/trials分母；phase_hist合计trials−unknown，mean_phase按有效轨迹计算，全unknown时直方图{}、mean_phase=null。
