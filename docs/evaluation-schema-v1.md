# SafeLab-Eval-v1 网站写入约定

标准全文：[评测标准](../eval-v1.html)。2026-11-03前的167条评测已标为legacy，不补猜缺失元数据。原protocol保留，并额外存于legacy_protocol。

## 更新入口

训练同学仍用首页「新增一行/编辑」登记权重、训练数据、训练状态。此共享表单填写的旧式h4/h8成绩属于团队填报，不自动进入正式v1对比。

评测agent通过PR更新data.json的evaluations，每个配置（权重×执行步数×条件版本×阶段）一行；保留其他agent的记录，不覆盖整份旧快照。先fetch最新分支再提交。运行 `node --test tests/*.test.js` 校验。正式成绩只读取完整完成的v1 A/B记录；legacy、diagnostic及字段不完整记录仅在折叠区域展示。stage只能为A/B/diagnostic/legacy；协议名精确为SafeLab-Eval-v1。

## 字段

保留id、record、dataset、method、checkpoint、horizon、success、trials、unknown、completed、protocol、kind、status、source等原字段。record必须绑定已登记的权重记录及checkpoint；相机由该record提供。

新增：
- protocol_version：SafeLab-Eval-v1或legacy。
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
