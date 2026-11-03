# SafeLab-Eval-v1 / v1.1 网站写入约定

现行标准全文：[SafeLab-Eval-v1.1](../eval-v1.1.html)；[strict-v1 对照](../eval-v1.html)。成功判定已由v1.1取代。2026-11-03前的167条评测已标为legacy，不补猜缺失元数据。原protocol保留，并额外存于legacy_protocol。

## 更新入口

训练同学仍用首页「新增一行/编辑」登记权重、训练数据、训练状态。此共享表单填写的旧式h4/h8成绩属于团队填报，不自动进入正式v1对比。

评测agent通过PR更新data.json的evaluations，每个配置（权重×执行步数×条件版本×阶段）一行；保留其他agent的记录，不覆盖整份旧快照。先fetch最新分支再提交。运行 `node --test tests/*.test.js` 校验。正式成绩只读取完整完成的v1/v1.1 A/B记录；legacy、diagnostic及字段不完整记录仅在折叠区域展示。stage只能为A/B/diagnostic/legacy；协议名为SafeLab-Eval-v1或SafeLab-Eval-v1.1，两轨独立登记，不混合。

## 字段

保留id、record、dataset、method、checkpoint、horizon、success、trials、unknown、completed、protocol、kind、status、source等原字段。record必须绑定已登记的权重记录及checkpoint；相机由该record提供。

新增：
- protocol_version：SafeLab-Eval-v1、SafeLab-Eval-v1.1或legacy。
- stage：A/B/diagnostic/legacy。A=100，B=500。阶段B为5个不同推理seed，每seed100条；含seed0。阶段A仅seed0。
- topology：{num_envs_actual:1,procs_per_gpu:2,gpu_type:"Pro6000"}。仅独立进程N1×k允许正式展示；不能将旧vectorized记录改名冒充N1。
- preprocess_resize：{implementation:"training_tensor",mode:"bilinear",antialias:true,source:"训练预处理代码路径及版本"}。
- condition_version：original-v1 / attach-v1 / attach-v2_solver128等明确且不可变版本。十任务attach v1与v2_solver128分组展示，不合并。
- scene_list_hash：sha256:加64位小写十六进制；对有序100场景清单计算并记录序列化约定。A/B复用同一清单，B不要对500条展开后的清单取哈希。
- lr_split：{left:{trials:50,success:0,unknown:0},right:{trials:50,success:0,unknown:0}}。B每侧250；正反场景映射left/right并在protocol说明。每侧 success + failure + unknown = trials，failure 未填时由 trials − success − unknown 推导；成功、失败、unknown分别与总数一致。
- seed_results：[{seed:0,trials:100,success:0,unknown:0}]；B5项。每个seed的 success + failure + unknown = trials；failure可省略并推导；各项必须与总数守恒。
- mean_phase：仅按有效轨迹（trials − unknown）计算的平均完成阶段数；phase_hist：阶段数到有效轨迹数量的映射，其总计必须等于 trials − unknown。unknown不能塞入第0阶段。mean_phase = Σ(阶段数×数量)/(trials − unknown)，必须与直方图一致。全部unknown时phase_hist为{}、mean_phase为null，界面显示无有效轨迹。缺失不得猜测为0。
- unknown_reasons（可选）：原因到数量的映射，例如 {"infrastructure":1,"unjudged":1}；如填写，计数总和须等于unknown。无需补写既有记录。
- wilson95：{low:0,high:0.03699,confidence:0.95}；概率单位0至1。正式表根据原始成功数和完整分母独立重算，不信任上传区间。unknown保留在trials内。
- admission：expert_replay/open_loop/render_multiframe/smoke20四项，各为{passed:true,report:"证据路径或链接"}。记录20条冒烟的左右10/10及阶段0分布；报告中保留多帧MAE。passed只是报告者声明，维护者仍须核对报告。
- 如使用stall_timeout，必须记录参数及不会截掉成功轨迹的证据。

未完成时success=null，completed写实际数量；不得提前填最终百分比。原始条件与attach、A与B、不同数据/相机/场景哈希分别分组，每种方法组内取最高成功率，平局取平均完成阶段数较高者。执行30步的旧记录仅留历史。

所有旧数字保留，不重新解释其拓扑。首页历史文字以「历史并行拓扑」表达未核验并发，正式成绩统一写「N1×k 多进程并行」。标准原文和证据档案保持原样。

## 2026-11-03 unknown补充规则

trials始终是完整分母，unknown属于trials。主表成功率为success/trials，Wilson 95%同样使用success和完整trials；同时展示unknown数及敏感性上界(success + unknown)/trials。敏感性上界仅表示未知轨迹全成功的极端情况，不是正式成绩或置信区间。

例如阶段A：trials=100、success=3、unknown=2，失败为95；phase_hist={"0":95,"3":3}合计98，mean_phase=9/98。正式成功率3%，unknown全部成功的上界5%。左右拆分和seed汇总保持三类结局守恒；显式提供failure时也必须满足该恒等式，缺省仍可推导。

此变更不批量改写旧数据、不追认legacy，也不要求给既有记录新增failure或unknown_reasons。十任务含unknown的新记录在下一次发布时，只要其余v1字段与准入证据齐全，即可进入正式主表。按旧规则把unknown计入phase_hist的历史数字保持原样，不自动重解释或迁入正式表。

## 2026-11-03 启动标记与旧候选档案（候选规则已作废）

`evaluation_started` 为可选布尔字段，兼容既有记录；未填写沿用原行为。新建但尚无 worker 开始的配置填写 `false`、`success:null`、`completed:0`、`unknown:0`、`phase_hist:{}`、`mean_phase:null`。`trials` 可预登记计划分母（A=100/B=500），也可为0并用 `target` 单列计划数；这都不是已评测数量。该标记为false时，不显示为正在执行，不进入正式成绩。worker实际开始后改为true；未完成时success仍必须为null。准入中/冒烟状态仍由admission证据决定。

**以下旧候选规则作废，不得据此新增成绩；现行placement-v1.1以末节为准。**

静止判定重算候选（历史说明）：另增独立evaluation，使用 `stage:"diagnostic"`、`metric_role:"rescored_v1.1_candidate"`、`source_evaluation_id:"原评测id"`，保留原任务、数据、权重、场景、执行步数、拓扑和输入元数据，并通过report_url或source提供逐轨迹重算依据。不得修改原strict-v1记录或复用其id。候选判定的具体参数、代码版本和逐条变化写入报告；协议是否采用等待用户决定。

候选行完成后遵守相同计数规则：success/trials、unknown保留完整分母、phase_hist合计trials−unknown、mean_phase按有效轨迹计算。未完成success=null。主页“判定口径”默认strict-v1；切换v1.1-candidate仅展示完成、来源齐全且计数守恒的诊断行，逐配置列示，不进行组内最佳选择。即使候选行误填stage A/B，也不得混进严格正式表、历史成功率格或阶段A/B覆盖。该视图不宣布v1.1正式生效。


## 2026-11-03 17:05 用户采用 SafeLab-Eval-v1.1（本节优先）

- 新结果：`protocol_version:"SafeLab-Eval-v1.1"`、`oracle_version:"placement-v1.1"`。原判定对照：`protocol_version:"SafeLab-Eval-v1"`、`oracle_version:"strict-v1"`。旧v1记录未填oracle_version时仅按strict-v1读取以兼容，不改原始值。v1.1必须显式写placement-v1.1；错配协议/判定不能进入主表。
- 阶段A/B的100/500完整分母、unknown、seed_results、lr_split、phase_hist、mean_phase、Wilson和原四项准入规则全部保留。缺少120Hz日志的轨迹在新重算行记unknown，仍在完整分母内；不得用旧成功率或平均数外推。
- `admission.executor_parity`新增为v1.1必需的第五项：`{passed:true,report:"执行链专家回放验收报告路径或链接"}`。只有通过且报告非空才进入正式表。报告须写执行链源码、标签约定及参数，15Hz loader标签经同一执行链复现原生120Hz专家轨迹的关节RMSE≤0.005rad、左右各5共10条、端点链成功数≥原生链−1，说明旧链是否相同/是否需重跑。网站声明校验不能代替维护者核对报告里的数值与证据。
- 建议报告或gate附带joint_rmse_rad、native_success、endpoint_success、trials:10、left_trials:5、right_trials:5。Mem-0/TTC所有变体/pi0.5复用同一已验收链，五任务current_row映射单列；若修改执行链，受影响配置的阶段A须重跑，不能仅改protocol字段。
- `admission.expert_replay.report`须包含新放置判定函数源码及参数、专家通过、握持/倾倒/出区域各10条负例视频核验、初始已在目标区域不误推进顺序的证据。0.25秒去抖不是速度稳定性条件。完整新规则见现行标准全文。
- 双轨以不同evaluation id发布，不覆盖原行。建议`paired_evaluation_id`相互引用；离线新重算记录用`source_evaluation_id`指向原记录，并在source/report_url记录120Hz原日志和重算报告、oracle源码版本、场景列表哈希和执行链是否相同。逐seed和左右拆分也要按新结果重算。
- 每个任务一旦有满足全部守恒及五项准入的v1.1 A/B结果，主表自动优先显示该任务v1.1；其余方法暂缺v1.1时不塞入旧成绩。尚无通过验证v1.1的任务继续显示strict-v1对照并明确口径。用户可显式切换placement-v1.1或strict-v1查看，绝不跨协议求和或组内取优。
- `rescored_v1.1_candidate`是旧漂移判定，已作废。原始JSON保留作审计，但从全部页面表格、主表、历史成绩格、诊断详情和覆盖计算排除；不能把它重命名后冒充placement-v1.1。
- 覆盖只统计v1.1。物理权重仍可合并为一行，但每个record变种×H4/H8×明确条件单列A/B状态。缺登记/未开始标红，显示pending_reason和expected_start_at；未提供排期明确写“待负责人排期”，维护者不猜时间。默认列原始条件，既有附着及其他明确条件分别列示，不把诊断偏置搜索列为正式配置。既有strict记录不计v1.1覆盖。

最小新准入片段（其余完整统计字段仍必需）：
```json
{"protocol_version":"SafeLab-Eval-v1.1","oracle_version":"placement-v1.1","stage":"A","admission":{"expert_replay":{"passed":false,"report":"oracle验收待完成"},"open_loop":{"passed":false,"report":"待完成"},"render_multiframe":{"passed":false,"report":"待完成"},"smoke20":{"passed":false,"report":"待完成"},"executor_parity":{"passed":false,"report":"执行链验收待完成"}},"evaluation_started":false,"success":null,"completed":0,"unknown":0,"pending_reason":"等待执行链与放置判定验收","expected_start_at":null}
```
该片段是待测状态示例，不能作为已完成成绩。请保留其他agent记录，仅按id追加或更新自己的配置。

媒体的跨域播放、同源JSON/gzip日志与50MB共享预算提案见[媒体清单规范](media-manifest-v1.md#跨域播放与同源日志托管2026-11-03-第2轮)。媒体case必须与evaluation的protocol_version和oracle_version精确绑定；strict旧媒体可兼容省略oracle_version。
