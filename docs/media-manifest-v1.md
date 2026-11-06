# SafeLab 媒体清单 v1

Refs: T-1263。供评测 agent 发布、交接台合并、对比页每 5 分钟消费。与 [SafeLab-Eval-v1/v1.1](evaluation-schema-v1.md) 配套；历史素材不得追认 v1。规范只登记来源和展示证据，不改变物理验收。

## 发布位置与上限

- 交接台 `media/index.json` 是唯一入口，schema 为 `safelab-media-index-v1`，含 `updated_at` 及 `manifests:[{url,sha256,updated_at}]`。也可由 data.json 的 `media_manifest_index` 显式指定 HTTPS 索引地址。
- 每个 agent 提交小型清单 `media/manifests/<task>/<run>.json`（`safelab-media-v1`）；只维护自己的文件和索引项，PR 保留其他 agent。每清单 ≤1 MB，索引 ≤256 KB，最多80清单；单清单最多2000案例。
- **视频放授权对象存储的稳定公开只读 HTTPS 路径** `liyufeng/safelab-public/media-v1/<task>/<record>/<checkpoint>/<condition>/<case_id>/`，不得把整批二进制提交 Pages。视频能播放不代表JSON可跨域fetch；逐帧日志按下方同源补充规则发布。外部清单须实际核验CORS允许对比页GET；不得使用需要登录或含 token 的临时签名链接。SHA-256 是文件实际字节，不是源视频或解压前后混用的摘要。
- 每视频 H.264 MP4、yuv420p、faststart、**≤2,000,000 bytes**；优先640×480/15Hz，保留完整时间范围并记录真实 fps，禁止删去失败或静止时段而不修改时钟元数据。转码后重新计算 hash。例：`ffmpeg -i input.mp4 -an -c:v libx264 -crf 30 -pix_fmt yuv420p -movflags +faststart preview.mp4`；超限继续降低码率/分辨率并核验完整时长，不以该命令保证体积。
- 每逐帧 JSON ≤2 MB；选择低冗余必需字段，观察频率采样，物理事件保留原始精确 t_sim。原120Hz日志和高清全量录像仍留原存储，清单只发布派生的去敏只读日志。不得以超限为由删去切换或物理事件。
- 原有已发布400条录像和日志为 legacy 兼容入口，不要求仅为媒体格式重新转码；源路径迁移仍按用户17:50规则复制核验后更新；新增媒体执行上述上限。Pages允许必要的公开派生帧日志，现行快照总预算见下方（原始日志不入库）；清单自身仍≤20MB且计入总预算。外部JSON不得在未通过CORS实测时作为回退。

## 每个 case 一条记录

见 [JSON Schema](media-manifest-v1.schema.json)。必填：

| 字段 | 含义 |
|---|---|
| case_id / task | 唯一案例ID；任务字符串3/5/7/10 |
| record / issue | canonical data.json record id或交接单号；两个键都存在，至少一个非null，配置不能仅靠方法名匹配 |
| checkpoint / horizon | 实际权重步数、执行步数4/8/30；30只保留既有历史 |
| protocol_version / evaluation_id / condition_version / stage | 精确协议与评测行ID（支持v1/v1.1/legacy）、接触条件不可变版本、A/B/diagnostic/legacy；attach不能冒充original |
| scene_id / scene_list_hash / side / seed | 相同初始场景的稳定ID、有序100场景列表哈希、left/right或forward/reverse、推理seed；对照必须哈希、场景和seed一致 |
| outcome / max_phase | success/fail/unknown；物理oracle最大完成阶段数，未知null，不能由Planner序号推断 |
| videos | third_person/head/chest三个键均存在，缺视角null；资产为{url,sha256,bytes}，记录转码后文件。旁观与策略输入视角不能混淆 |
| frame_log | {url,sha256,bytes,encoding?,decoded_bytes?,decoded_sha256?}或null，引用逐帧JSON；没有日志就null |
| render_config_hash | 相机外参、内参、光照、渲染配置序列化后的SHA256，禁止猜测 |
| timebase | {fps,video_time_origin_s,log_time_origin_s}；video.currentTime=t_sim-log_time_origin_s+video_time_origin_s。所有视角必须同步、无独立剪辑 |
| subtask_physical_targets | 第i条指令应完成的oracle阶段编号数组；无法证明语义映射为null，不计算切换错误率 |

清单 `schema_version:safelab-media-v1, updated_at:ISO8601, cases:[...]`。不得包含 SSH、私有磁盘路径、提示词、密钥或原始RPC。公共URL不得含用户名/密码、签名、访问令牌。发布者与消费端必须先用URL解析器拒绝userinfo、查询参数、片段、localhost/私有IP/内网域名；该语义校验不由JSON Schema的format:uri替代。另须校验case_id唯一、日志时钟严格递增、体积与bytes/SHA/真实时长及采样数量，不得只跑schema就宣称通过。客户端核验 hash 证明字节身份，不等于证明科学验收。

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


## 2026-11-03 同源帧日志 / CORS 补充（本节优先）

视频继续放对象存储；由video标签播放成功不能证明fetch JSON的CORS通过。派生浏览器逐帧日志进入`media/frame_logs/<task>/<run>/<case>.json`，manifest使用同源绝对HTTPS URL，例如`https://asimfish.github.io/safelab-handoff/media/frame_logs/10/run/case.json`。不将CORS失败当成“没有日志”；页面应明确读取失败并保留视频与旧快照。

**预算：当前Git跟踪的发布快照总计≤50,000,000 bytes（十进制50MB）**，包含源码、报告、清单、派生帧日志；不含.git历史与ignored临时测试目录。帧日志不是额外再加50MB。各任务媒体初始软配额10MB，余量可经PR说明共享，不提高总上限。Git历史对象大小独立报告，不自动改写历史或删旧科学证据来腾空间。每PR同时报告旧快照/新增/合并后字节、每文件SHA及帧数。`node scripts/check-media-budget.cjs`在CI检查预算、同源引用、实际bytes/SHA和受限解压；该检查不替代完整schema或原日志事件保留核验。

普通JSON优先minify。仍超预算时使用事件保留抽稀：保留首末帧、所有真实切换行和物理事件所在行，原事件精确t_sim与timebase不变；保留空值语义，不删掉失败或静止区间来加速视频。可增加`sampling:{method:"event-preserving-v1",original_rows,retained_rows,baseline_hz,source_sha256?}`，retained_rows必须等于rows.length且不大于original_rows。发布者附源日志对照证明所有必保事件保留；仅在派生文件上看不到事件不代表源日志没有事件。抽稀会改变观测密度，消费者不得据抽稀间隔外推未观察到的切换。

gzip使用`.json.gz`和`encoding:"gzip"`；bytes/sha256是仓库中压缩文件实际字节，必须另给decoded_bytes/decoded_sha256描述解压JSON。压缩文件与解压内容各≤2,000,000 bytes，防止解压膨胀；普通JSON缺encoding时按identity，原清单保持兼容。GitHub Pages不会保证将`.gz`自动解压；消费者须先核对下载bytes/SHA，再以DecompressionStream('gzip')有界解压（超过decoded上限立即终止），核对解压bytes/SHA后解析JSON和校验schema。必须核验服务器没有自动Content-Encoding解压导致wire哈希语义变化。**gzip只在消费者PR同步实现并通过Pages同源端到端验收后启用；不能只上传.gz或改后缀。**

合并前测试真实页面下的fetch→HTTP成功→bytes/SHA→（gzip解压/decoded SHA）→JSON schema→视频时钟对齐；开发机curl能下载并不证明跨域浏览器fetch能读。首版没有可验收的gzip消费者时，提交普通JSON或进一步抽稀，保持必保事件。

### 源存储与迁移（用户17:50规定）

- 大件：`/projects/a02012413/buckets/zenith-a02012413/liyufeng/`下对应目录；小件报告/配置/清单：`/project_a02012413/public/liyufeng/`下对应目录。两处合计≤2TB。仓库只收展示必需的公开派生小日志，不承担原始日志/视频/权重归档。
- 禁止新输出到`/projects/a02012413/241106039`、`/public_fast_storage`或其他生产数据位置。在旧位置运行的任务完成当前批次，不中途打断。
- 迁移严格按复制→逐文件SHA核对→更新网站/报告引用；原件先保留，删除需用户批准。不得先改URL后补复制，也不把GitHub链接存在当成源数据SHA已核对。
- 本项在CPU完成，不新增GPU，不开卡等待上传、准入或人工确认。已有卡由评测负责人维持N1×k+只读模型池混跑配置和补位，持续利用率<80%不申请新卡。
- 每次回执列两允许位置占用及旧位置待迁移量，明确节点/路径/统计范围和时间；不可访问或未全量统计的写未核实，不填0。

媒体v1.1案例还必须写oracle_version=placement-v1.1；strict-v1对照分开绑定evaluation_id，不把旧漂移候选日志改名为放置判定。物理phase/events使用对应oracle，不复用不一致的阶段统计。


## T-1263 对比页播放与首批容量核对

播放器使用公开URL直接赋值video.src，**不设置crossorigin**，不用fetch/blob/HEAD/SHA校验作为视频播放前置，也不用canvas/WebGL读取视频像素。图表canvas只绘制已读取JSON数值，联播使用currentTime与timebase。浏览器明确显示“未核验视频SHA”；转码视频的bytes/SHA由发布者和维护者核验，不把清单SHA成功当成视频SHA成功。发布前还需在真实浏览器验证H.264、Range、拖动与完整时长；匿名GET不单独证明这些条件通过。日志失败独立显示，不阻塞直连视频。

同源是scheme+host+port：两个仓库站点均属于https://asimfish.github.io，仓库路径不同不构成跨域。逐帧日志按上节frame_logs同源规则提交；视频继续public-read对象存储。`.json.gz`除下载bytes/SHA外，消费者还流式限制解压大小并核对decoded_bytes/decoded_sha256再解析。文件作为application/gzip发布，不配置Content-Encoding自动解压；wire/decoded语义不符须拒绝，不能跳过校验。缺DecompressionStream的浏览器显示不支持日志解压，视频继续播放。

事件保留抽稀还须保留指令、真实阳性累计器、物理阶段的变化行；不能从保留分数重建positive_count。首末帧、全部实际切换/物理事件及事件精确时间均保留，并给原始来源SHA和采样规则；界面标注抽稀，只展示保留观测，不外推未观察到的切换。

容量依据（不是发布回执）：十任务CPU导出MEDIA_PREP_PROGRESS的48份日志、64,406行，合计11,584,309 bytes（11.58MB），每份27,120–794,074、均值241,339.77。96段双视角视频共享48份日志，不复制两份。未实测gzip总体积，不使用估计压缩比冒充实测。

基线为交接台commit366f6a0的Git跟踪快照：128文件、24,957,142 bytes；这是git树中tracked文件大小，不是.git历史或远端数据盘占用。加十任务未压缩首批约36,541,451 bytes，低于**整个快照**50,000,000预算，但11.58MB超过单任务10MB软配额；普通JSON发布应在PR申请额外共享约1.58MB，或先gzip并报告实测大小。其他任务未发布同格式首批清单，不能填0或声称已测。

按十任务均值估算8case/配置约1.93MB；如果四任务各48case，日志小计约46.34MB，加上述基线约71.29MB，**超过全仓50MB**，不可全部原样提交。各任务须先gzip或按事件保真规则抽稀，以实际文件运行预算CI；任何新报告/源码/清单也占全仓预算。每次PR用最新基线报告旧/新增/合并后大小，不能把这里的历史基线当成后续可用余量。

媒体新协议使用protocol_version=SafeLab-Eval-v1.1且oracle_version=placement-v1.1，并绑定对应evaluation_id；其完整成绩另须第五项executor_parity等准入。strict媒体可省略旧oracle_version以兼容，若填写则必须strict-v1。旧严格日志若未按新物理判定重新生成，不得仅改case_id或版本冒充放置判定。


## 2026-11-03 第11轮：逐帧日志统一同源发布（取代有条件 CORS 路径）

十任务已确认现有 STS 对 `GetBucketCORS` 返回 HTTP 403 AccessDenied，当前对象存储 CORS 路径不可用。**全部浏览器逐帧日志统一走本仓库 `media/frame_logs/<task>/<run>/<case>.json` 同源路径**；视频继续使用下节规定的 `liyufeng/safelab-public/media-v1/<task>/…` 公开对象路径。不得把对象存储中的源 JSON 地址作为浏览器回退，也不得因视频能播放而宣称 JSON 可跨域读取。

现行 schema 与 CI 的同源日志限制保持不变。源 JSON 可保留在对象存储用于来源 SHA 与事件保留核对，但 manifest 的 `frame_log.url` 必须指向 Pages 派生日志。所有任务均受全仓 50,000,000-byte 预算、单文件上限和首末帧/切换/物理事件保留规则约束；超预算时按已验收的抽稀或 gzip 契约处理，不放宽 CORS 白名单，不删除科学证据。

本轮未请求更改 bucket 策略、ACL 或 CORS，未删除任何原对象。如将来获得权限并拟重新启用外部 JSON，须另提规范与消费者/CI 修改 PR，附真实浏览器读取和完整性证据；本轮不预授权。


## 2026-11-03 第9轮：公开媒体前缀纠正（本节优先）

唯一允许的新公开对象键为 `liyufeng/safelab-public/media-v1/<task>/…`，位于 `zenith-a02012413` bucket，对应大文件目录 `/projects/a02012413/buckets/zenith-a02012413/liyufeng/safelab-public/media-v1/`。仅逐对象设置 `public-read`，不得为此公开整桶或变更整桶ACL。当前已审核的HTTPS端点为 `zenith-a02012413.tos-cn-beijing.volces.com` 和 `zenith-a02012413.bj.bcebos.com`；只允许该bucket及精确目录前缀，无签名、token、userinfo、查询或片段。新增端点须附公开读验证后单独审核，不接受任意外链。

旧 `safelab-public/media-v1/` **只在已有素材迁移期间兼容**，不是新发布路径。CI输出 `legacy_public_media_references` 作为待迁移数；收尾后移除旧前缀。十任务/pi0.5迁移PR必须遵循复制→逐文件匿名GET及bytes/SHA核对→更新引用，保持case_id、evaluation_id、协议、stage、视频字节和时钟不变。原对象先保留，删除需用户批准。只改URL但没有完成复制和SHA核验的PR不合并。

同源 `media/frame_logs/` 日志继续适用现有规则，本次不开放未经CORS验收的外部JSON；视频可播不证明JSON可fetch。播放器和完整schema/来源核验要求不变，CI白名单也不代替实际匿名读取和SHA证据。

## 2026-11-06 gzip 容量迁移

现有消费者已通过 `DecompressionStream('gzip')` 的双 SHA、2MB 有界解压和视频时钟验收。仅压缩原文件字节，不改 JSON 序列化、不抽稀、不更改事件或帧数。压缩身份使用 frame_log.bytes/sha256，解压身份使用 decoded_bytes/decoded_sha256（与迁移前原文件完全相同）。

滚动发布保留 `frame_log_previous` 为原同源 identity 资产；CI 同时检查新旧文件、case_id 和解压内容逐字节相等，不能把兼容字段指向不相关日志。旧路径在启用 gzip 的已部署版本中继续可 GET，下一版本且至少跨过一次5分钟同步窗口后才移除；移除仅指 GitHub 的过期派生副本，源日志及已核对的归档不删除。迁移清单记录在 `media/migrations/`，压缩脚本复用意图必须先退出，不能重复改写。

因为首版保留原路径，压缩副本会暂时增加快照，不得把预期节省计作现有余量。先用剩余预算上线第一批，再在后继版本释放该批旧派生副本、上线下一批；每个版本都检查全仓50MB上限。不改变 CORS、bucket ACL、视频路径、评分或配对身份。

### 辅助协议展示

`SafeLab-Eval-v1.4-A` 或显式 `assisted:true` / `assistance_protocol` / `time_limit_multiplier`、`timeout_multiplier`、`time_budget_multiplier` 大于1的配置，进入“辅助协议”分区。只读已声明的倍率，不能从录像时长推定倍率。协议/倍率进入配置和物理配对身份，不与同权重的纯物理行合并；v1.4只是重评分时仍按对应来源批次展示。新口径必须填写真实 oracle_version，不猜测或沿用v1.1；原v1.1/strict的oracle约束不变。各口径单列x/n，不拿宽松结果填正式列。辅助均值的阶段上限未发布时分母用“–”，不把杯数误当成子任务数。

R2 实施说明：首批原URL已通过线上双SHA核验，并在后继版本提交前等待≥600秒；仅退役该批GitHub派生JSON。其余185份启用gzip时继续保留各自 frame_log_previous。`scripts/retire-frame-log-compat.py` 默认只预览，apply需要完整线上回执、保留窗口、case绑定、新旧及归档逐字节一致；拒绝符号链接、超2MB解压、重复意图或不匹配归档。归档及TOS原对象永不在此脚本中删除。

既有大报告 `long_task_videos/task7-diagnostics.json`（1,326,742B）已按原字节复制到授权TOS `reports-v1/visualization-gzip-20261106/<sha>/`，匿名GET/SHA核对记录在 `media/migrations/report-task7-diagnostics-20261106.json`。页面下载链接指向TOS，不做跨域fetch；仓库仅保留62KB、带原报告SHA的回归事实摘要。旧完整报告路径保留R2一个发布周期后，仅移除其GitHub副本，归档与TOS原件保留。根 data.json 为实时控制清单，非报告归档，不随报告迁移。

### 2026-11-06 capacity exception

Explicit user instruction supersedes the compatibility retention window for the R2 backlog: remove verified derived plain JSON copies in the same PR as gzip migration. Original producer archives remain intact; wire and decoded SHA verification remains required. This exception does not assert that R2 was previously published.
