# SafeLab 媒体清单 v1

Refs: T-1263。供评测 agent 发布、交接台合并、对比页每 5 分钟消费。与 [SafeLab-Eval-v1](evaluation-schema-v1.md) 配套；历史素材不得追认 v1。规范只登记来源和展示证据，不改变物理验收。

## 发布位置与上限

- 交接台 `media/index.json` 是唯一入口，schema 为 `safelab-media-index-v1`，含 `updated_at` 及 `manifests:[{url,sha256,updated_at}]`。也可由 data.json 的 `media_manifest_index` 显式指定 HTTPS 索引地址。
- 每个 agent 提交小型清单 `media/manifests/<task>/<run>.json`（`safelab-media-v1`）；只维护自己的文件和索引项，PR 保留其他 agent。每清单 ≤1 MB，索引 ≤256 KB，最多80清单；单清单最多2000案例。
- **视频、逐帧日志放授权对象存储的稳定公开只读 HTTPS 路径** `safelab-public/media-v1/<task>/<record>/<checkpoint>/<condition>/<case_id>/`，不得把整批二进制提交 Pages。CORS 允许对比页 GET；不得使用需要登录或含 token 的临时签名链接。SHA-256 是文件实际字节，不是源视频或解压前后混用的摘要。
- 每视频 H.264 MP4、yuv420p、faststart、**≤2,000,000 bytes**；优先640×480/15Hz，保留完整时间范围并记录真实 fps，禁止删去失败或静止时段而不修改时钟元数据。转码后重新计算 hash。例：`ffmpeg -i input.mp4 -an -c:v libx264 -crf 30 -pix_fmt yuv420p -movflags +faststart preview.mp4`；超限继续降低码率/分辨率并核验完整时长，不以该命令保证体积。
- 每逐帧 JSON ≤2 MB；选择低冗余必需字段，观察频率采样，物理事件保留原始精确 t_sim。原120Hz日志和高清全量录像仍留原存储，清单只发布派生的去敏只读日志。不得以超限为由删去切换或物理事件。
- 原有已发布400条录像和日志为 legacy 兼容入口，**不要求复制或重新转码**；新增媒体执行上述上限。Pages 仓库仅允许小清单，新增清单总预算≤20 MB；超出时索引指向对象存储。

## 每个 case 一条记录

见 [JSON Schema](media-manifest-v1.schema.json)。必填：

| 字段 | 含义 |
|---|---|
| case_id / task | 唯一案例ID；任务字符串3/5/7/10 |
| record / issue | canonical data.json record id或交接单号；两个键都存在，至少一个非null，配置不能仅靠方法名匹配 |
| checkpoint / horizon | 实际权重步数、执行步数4/8/30；30只保留既有历史 |
| protocol_version / evaluation_id / condition_version / stage | 精确协议与评测行ID、接触条件不可变版本、A/B/diagnostic/legacy；attach不能冒充original |
| scene_id / scene_list_hash / side / seed | 相同初始场景的稳定ID、有序100场景列表哈希、left/right或forward/reverse、推理seed；对照必须哈希、场景和seed一致 |
| outcome / max_phase | success/fail/unknown；物理oracle最大完成阶段数，未知null，不能由Planner序号推断 |
| videos | third_person/head/chest三个键均存在，缺视角null；资产为{url,sha256,bytes}，记录转码后文件。旁观与策略输入视角不能混淆 |
| frame_log | {url,sha256,bytes}或null，引用逐帧JSON；没有日志就null |
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
