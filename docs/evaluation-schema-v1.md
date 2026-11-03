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
- lr_split：{left:{trials:50,success:0,unknown:0},right:{trials:50,success:0,unknown:0}}。B每侧250；正反场景映射left/right并在protocol说明。成功及unknown分别与总数一致。
- seed_results：[{seed:0,trials:100,success:0,unknown:0}]；B5项。必须与总数守恒。
- mean_phase：平均完成阶段数；phase_hist：{"0":100}这类阶段数到数量的映射，总计trials；mean_phase必须与直方图一致。缺失不得猜测为0。
- wilson95：{low:0,high:0.03699,confidence:0.95}；概率单位0至1。正式表根据原始成功数和完整分母独立重算，不信任上传区间。unknown保留在trials内。
- admission：expert_replay/open_loop/render_multiframe/smoke20四项，各为{passed:true,report:"证据路径或链接"}。记录20条冒烟的左右10/10及阶段0分布；报告中保留多帧MAE。passed只是报告者声明，维护者仍须核对报告。
- 如使用stall_timeout，必须记录参数及不会截掉成功轨迹的证据。

未完成时success=null，completed写实际数量；不得提前填最终百分比。原始条件与attach、A与B、不同数据/相机/场景哈希分别分组，每种方法组内取最高成功率，平局取平均完成阶段数较高者。执行30步的旧记录仅留历史。

所有旧数字保留，不重新解释其拓扑。首页历史文字以「历史并行拓扑」表达未核验并发，正式成绩统一写「N1×k 多进程并行」。标准原文和证据档案保持原样。
