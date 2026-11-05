# 七任务 P1 策略对照与 A/B/C 指令对齐

核验时间：2026-11-05T20:55:03.872728+00:00。

这条启动指令所要求的 P1 策略对照已有完整结果。原任务 job-txdf93hin5hn 的归档平台回执为 SUCCEEDED，原实际使用一个4卡低优任务、每卡k4，已跑满100个同场景同seed案例。原监控已关闭。本轮只核验已有证据，没有重新提交两个重复4卡任务，Zenith/模型/仿真新增调用均为0。

**P1 与 K-cubic：同 placement-v1.1 判定**

| 执行链 | 成功 / N | 最终基础设施 unknown | 平均完成阶段 |
|---|---:|---:|---:|
| K-cubic + 训练侧缩放 | 5/100 | 0 | 2.38 |
| P1 + 训练侧缩放 | 4/100 | 0 | 2.60 |

这里的 K-cubic 平均阶段2.38属于原 v1.1 配对对照；不把之后 v1.2-relaxed 的2.59混入。

- P1−K 成功率差：−1个百分点；95%配对 bootstrap 区间 [−7,+5] 个百分点。
- P1−K 平均阶段差：+0.22；95%区间 [−0.32,+0.76]。
- P1 平均阶段自身区间：[2.22,3.01]。原始正序/反序各50条，成功为3/1。
- 全100条按原始 case_id、paired_source_case_id、seed、order 配对；100份闭合回执完整SHA通过，10,000次分层配对bootstrap独立重现。
- P1四条成功与K五条成功无重叠。P1累计到达阶段1至7的条数为87/58/44/33/22/12/4。
- 原过程中出现过4条基础设施unknown，已按同seed重试闭合；最终placement unknown为0。把出现过unknown的案例一律算失败，成功数仍4。strict/FD各为0确认成功、96失败、4删失unknown，不能写成完整0%。

**结论与条件续测**

没有证据证明 P1 明显优于 K-cubic；成功数反而4对5。因此用户设定的“Mem-0明显更好后才跑TTC-P1”条件尚未满足，本轮不追加TTC-P1，主表执行链不替换。

P1专家回放成功数10/10，与原生10/10相同；但q13 RMSE=0.0083018484 rad，仍超过0.005，手臂/手部分别0.0007715754/0.0121915383。每侧10个专家路径仅3个不同轨迹内容SHA。这些限制不因策略对照完成而消失，P1只保留为diagnostic。

**A/B/C 已完成，不需要再等待**

两种模型各固定20条训练episode（0–9、50–59），各8380帧，40份原始episode统计回执完整SHA通过，24个动作RMSE分量从SSE/元素数独立汇总复现。下表为前8预测步对标签的RMSE，单位rad：

| 模型 / 部位 | A 训练解码图 | B 近似重渲染 | C 编解码后的B |
|---|---:|---:|---:|
| mem0_30k / arm7 | 0.011638 | 0.019095 | 0.017885 |
| mem0_30k / hand6 | 0.011229 | 0.042315 | 0.042032 |
| ours_aligned_30k / arm7 | 0.013476 | 0.020177 | 0.018934 |
| ours_aligned_30k / hand6 | 0.011376 | 0.045478 | 0.043556 |

B是记录观测位姿的近似重渲染：训练曝光tick=121+8i，记录状态tick=124+8i，相差3个120Hz tick（25ms），原始精确曝光状态和完整渲染历史未知。后来找回的30Hz physics状态与render tick没有精确交集；没有把它插值或冒充训练原生120Hz。

C采用已读取的H264 High/yuv420p、CRF23、GOP250、B3/lookahead40进行往返；preset未知，未猜测。完整数据还保留全30步、接近/闭手/搬运分段及尾部窗口分析。C能降低部分误差，但没有恢复到A；这仍不能把差异唯一归因于渲染。之前闭环20条的低延迟B0/lookahead0配置是另一项已完成诊断，不等同于本次离线C。

**证据入口**

- P1原结果：/home/liyufeng/ops/safelab_mem0_7weigh_eval_20261027/eval_v11_admission_20261104/low_sr_diagnostic_traininit_p1_v1/p1_mem0_policy100_cpu_v1/FINAL_P1_POLICY100_DIAGNOSTIC.json，SHA256 `466e62ac73cb778153e4c0d720e6e9df23a625f7feef7019fef7b725fd2747b8`。
- 本轮100条独立配对核验：/home/liyufeng/ops/safelab_mem0_7weigh_eval_20261027/eval_v11_admission_20261104/low_sr_diagnostic_traininit_p1_v1/p1_instruction_reconcile_20261105/ROOT_P1_PAIR_VERIFICATION.json，SHA256 `15867cabd04356d9381e0051c9abb02cc019f13f1922f2ceec3628944cd7cbd9`。
- 本轮A/B/C核验：/home/liyufeng/ops/safelab_mem0_7weigh_eval_20261027/eval_v11_admission_20261104/low_sr_diagnostic_traininit_p1_v1/p1_instruction_reconcile_20261105/ROOT_ABC20_VERIFICATION.json，SHA256 `59a45fff48048b7254d4283a96e56f4613a8e7a09088fc61403d1a230f29f051`。
- P1配对明细：/home/liyufeng/ops/safelab_mem0_7weigh_eval_20261027/eval_v11_admission_20261104/low_sr_diagnostic_traininit_p1_v1/p1_instruction_reconcile_20261105/PAIRED100.json。
- A/B/C完整统计：/home/liyufeng/ops/safelab_mem0_7weigh_eval_20261027/eval_v11_admission_20261104/low_sr_diagnostic_traininit_p1_v1/ABC20_statistics_cpu_v1/FINAL_20EP_1793899601480232608/ABC20_FINAL_STATISTICS.json。

网站：独立P1诊断行将更新到既有PR54，不替换正式主表、不自merge。最新指令附带回信通道已过期（expires_at_ms=1793884303440），没有请求该接口或复用其他凭据。
