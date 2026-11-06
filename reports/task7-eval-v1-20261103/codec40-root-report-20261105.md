# 七任务编解码诊断：最终结果

评测已完成，完整归档仍有22条路由拒绝待补。所有结果均为diagnostic，正式主表保持Mem-0 5/100、TTC对齐版7/100。

两种方法均为30k、训练侧缩放、h8、原K-cubic链、原scene/seed/oracle/time_limit；固定取主表前20场景（正逆各10），未按结果挑选。每个case取第一次有效原CPU/SDK闭合，基础设施中断只重试一次。40个原始计分闭合回执均独立全文件SHA核对。

| 方法 | 原版成功 | codecB0成功 | 原版平均阶段 | codecB0平均阶段 | 配对阶段差及95% bootstrap CI |
|---|---:|---:|---:|---:|---|
| Mem-0 | 1/20 | 0/20 | 2.45 | 2.50 | +0.05 [-1.10, 1.15] |
| TTC 对齐 | 2/20 | 1/20 | 3.25 | 2.95 | -0.30 [-1.60, 0.95] |

配对bootstrap为10,000次、seed20261105、正逆各10的共享抽样；两种阶段差CI均跨0。本次低延迟编解码没有显示闭环收益，不支持据此推断正式主表需要改用该处理。小样本不能证明不存在任何编解码效应。

## 三口径与unknown

| 方法/条件 | placement S/F/U | strict S/F/U | FD S/F/U |
|---|---|---|---|
| Mem-0 原版 | 1/19/0 | 0/19/1 | 0/19/1 |
| Mem-0 codecB0 | 0/20/0 | 0/20/0 | 0/20/0 |
| TTC对齐 原版 | 2/18/0 | 0/18/2 | 0/18/2 |
| TTC对齐 codecB0 | 1/19/0 | 0/19/1 | 0/19/1 |

placement最终基础设施unknown均为0。codecB0 TTC发生过2次基础设施中断，两者同seed重试均恢复有效结果。strict/FD的unknown是原判定在episode结束时截尾，不是基础设施失败；不报成完整0%成功率。七任务原strict没有可替换的瞬时速度谓词，因此此处FD计分与strict相同。

额外敏感性“出现过unknown一律按失败”保留用户原主表inclusive startup-abort边界：前20原版Mem-0/TTC分别0/0条成功，codecB0分别0/1条；原版runtime-only分别1/1条。该差异包含历史启动事件，不能作为图像处理的因果增益。完整counts/CI/左右拆分/阶段分布/漏斗见配对JSON。

## 开环与输入审计

每种方法固定20个训练前缀、8,380查询的A/B/C已全部完成；分接近/闭手/搬运、h8/h30和all/tail40/trim40统计已独立验收并按episode做bootstrap。图像MAE由2.581965降到2.103409/255。h8手臂误差两模型约降6%；Mem-0手部改善CI跨0，TTC手部小幅改善；h30手臂未见改善证据。完整表见OPENLOOP20_RESULT.md与其引用的原始JSON/TXT。

Mem-0/TTC各5个固定训练帧通过部署最终张量及固定噪声动作对照；pi0.5复用已完成原审计并重新核对源码。范围限于这些帧与固定规划上下文，不扩展为所有变体、所有帧或Gen网络的完整审计。

离线C恢复训练的B3/lookahead40；闭环为低延迟B0/lookahead0、不同x264构建，二者不是同一个bitstream条件。B还有记录位姿晚于训练曝光3tick及渲染历史不全的限制；这些边界均保留，不能把A/B差异全部认定为纯光学原因。

## 资源与归档

平台job-pskhre7moc4h最终SUCCEEDED，原运行返回0，队列40/40闭合，Native进程与原NN进程均已清理；本轮当前0任务、0卡。原k4/链/物理/判定未改；记录的稳态全四卡600秒均值50.74%，未达80%目标。

最终上传队列为空、1,936对象已由原上传器PUT/GET SHA核验；归档journal仍有22条small路由拒绝，文件名/原SHA尚unknown，完整归档标记保持pending。当前OpenAPI无已验证exec/terminal/files读取路线，已向用户询问既有容器/归档可读入口。拒绝错误没有清除，也没有把未知文件假定为缓存。

原单次回信接口在本轮处理前已过期，未成功POST；结果在本地与授权S目录交付，网站更新走既有PR由交接台审核。

最终配对JSON：/home/liyufeng/ops/safelab_mem0_7weigh_eval_20261027/eval_v11_admission_20261104/stream_codec_closedloop20_cpu_v1/paired20_cpu_v1/FINAL_BOTH20_CODEC_DIAGNOSTIC.json
SHA256: 85f020be251a4a58e3b7516046f9f9b4cc385538e82d25fe7bc07a3129eca174
完整交付JSON：/home/liyufeng/ops/safelab_mem0_7weigh_eval_20261027/eval_v11_admission_20261104/stream_codec_closedloop20_cpu_v1/FINAL_DIAGNOSTIC_DELIVERY.json
SHA256: 9412fa6d84dd85333aba34f710afd554793562ab239be5d1a4f59d63019fc783
