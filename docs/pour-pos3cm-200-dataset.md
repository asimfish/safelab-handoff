# 三子任务 pour ±3cm · 200 条数据登记

登记 ID：`3-pos3cm-200`。这是独立于 latest/V14 和 V13 的新位置泛化数据版本。

**交付完成：200 条，左100 / 右100，共240,589个15 Hz帧。** 合并包已通过全视频解码和 LeRobot v2.1、v3.0 两个官方读取器验证；两版均检查全部200条及每个物理子任务。最终质量报告、逐条种子与偏移、相机参数和 README 已归档。

| 数据契约 | 登记值 |
|---|---|
| 数据目录名 | `psibot_3_pour_pos3cm_v1_final200_L100R100_R700_lossless_20261108` |
| 布局扰动 | A、B 各自独立采样 world X/Y ±0.03 m；物体与起始垫一起移动，归位目标跟随随机起点 |
| 正式接受条数 | 200；left100 / right100 |
| 总帧数 | 240,589；三路相机共享时间轴，不将相机数乘入帧数 |
| 交付格式 | LeRobot v2.1、LeRobot v3.0；两版官方 reader 均通过 |
| 相机 | head、chest、third_person；各640×480、15 fps，原安装位姿和标定 |
| 状态 | 13维实测关节状态 |
| 原始控制 | 120 Hz；每个15 Hz帧对应8个Native tick |
| 动作标签 | interval_end：下一个八tick控制块最后有效的issued target；保留部分尾块、padding语义及完整8×13控制块 |
| 子任务 | 抓取、倾倒、归位三个物理子任务；开头并入第一个子任务，无独立初始状态段 |
| 共享 Bucket 根目录 | `/projects/a02012413/buckets/zenith-a02012413/liyufeng/psibot_3_pour_pos3cm_pilot20_20261103_1749/psibot_3_pour_pos3cm_v1_final200_L100R100_R700_lossless_20261108` |
| LeRobot v2.1 目录 | `/projects/a02012413/buckets/zenith-a02012413/liyufeng/psibot_3_pour_pos3cm_pilot20_20261103_1749/psibot_3_pour_pos3cm_v1_final200_L100R100_R700_lossless_20261108/lerobot_v21` |
| LeRobot v3.0 目录 | `/projects/a02012413/buckets/zenith-a02012413/liyufeng/psibot_3_pour_pos3cm_pilot20_20261103_1749/psibot_3_pour_pos3cm_v1_final200_L100R100_R700_lossless_20261108/lerobot_v30` |

## 实测质量与验收

逐条验收包含源轨迹物理条件、全120 Hz几何与相机检查、独立COLD动作回放、冻结的无损PNG与噪声检查，以及双格式导出。合并交付再做全视频解码与两版官方读取验证，科学阈值保持不变。

| 实测指标 | 中位数 | p95 | 最大值 |
|---|---:|---:|---:|
| 轨迹时长（秒） | 79.0833 | 92.2104 | 99.4 |
| 臂关节峰值加速度（rad/s²） | 1.38987 | 1.87557 | 1.97570 |
| 臂关节峰值jerk（rad/s³） | 178.122 | 224.960 | 247.462 |
| COLD逐关节最大RMSE（rad） | 0.00179824 | 0.00452756 | 0.00491441 |

以上轨迹指标覆盖200条；噪声统计覆盖200条×3相机的600个单元。原始布局的共享参考图像对比单独记录，不将它重复计作200次独立参考实验。接受集经过质量筛选，偏移分布是条件化的；完整尝试分母缺失，不能从200条接受数据推算总体采集通过率。

## 可核对证据

| 证据 | SHA256 |
|---|---|
| 正式接受200条的不可变ledger | `46506f893fdb33d73b6fa864147777819edb52c3798cd171216cbe67731d93f5` |
| 冻结无损验收契约 | `172da8b1b904655f04f7d806e84d35579c792a36f7abddf5ee5e527fdf96adce` |
| R700最终交付STATUS | `34681250eda80a53d2b726110c1ee5e584c6c3142aec18996821e96db1de840c` |
| R936元数据与README receipt | `6df558f23665e251494bb639aeb8337998f72223c3b43098706e4db1d0c090f7` |
| 最终小型质量报告 | `e688d61c8118596132fa01aa5e082a6629c1d7c5f2cbaedafffe0d4bd4785c5b` |

大文件、原始120 Hz轨迹和验收证据保存在上述Bucket目录。最终小报告：`/project_a02012413/public/liyufeng/psibot_3_pour_pos3cm_pilot20_20261103_1749/PHASE2_FINAL200_QUALITY_SUMMARY_R936.json`。

Bucket内的主要文件：

- `FINAL200_DELIVERY_STATUS.json`：200 / 左100右100、帧数和两版官方读取结果。
- `OFFICIAL_LEROBOT_LOADER_VALIDATION.json`、`official_reader_evidence/`：实际官方reader证据。
- `R700_FULL_VIDEO_FORMAT_VERIFICATION.json`：全部保存视频的解码证据。
- `FINAL200_METRIC_ROWS.json`、`FINAL200_QUALITY_DISTRIBUTIONS.json`：逐条指标与分布。
- `r936_quality_provenance/EPISODE_PROVENANCE_200.jsonl`：种子、逐物体偏移、冻结场景、渲染和原C3的身份。
- `r936_quality_provenance/CAMERA_PARAMETER_GROUPS.json`：原相机参数与逐条覆盖。
- `raw/episodes/`、`qualification/`、`labels/`：原始状态控制、逐条验收和物理子任务标签。

登记按[网站PR流程](website-pr-review.md)交维护者审核合并。仓库只保存登记元数据；模型训练权重和评测成绩另行登记。
