# 权重 × 评测覆盖

数据源包括开放及已关闭的 checkpoint issue。关闭issue不代表评测完成。每个issue绑定到records内一个确定的record+checkpoint；原record ID及evaluations绑定保持稳定，多checkpoint的历史record仍按权重分成独立行，不迁移成绩。

`record.checkpoint_issues`保存issue号、checkpoint步数、issue状态及更新时间、交付入口、交接人和明确的评测负责agent。各issue只对应一个权重行；#8按用户核对与#7重复，两者引用保留在同一行，不自动关闭。

## 交付和占位

真实checkpoint路径放在weights.path。只有START_HERE.md的issue保留交付文档入口，实际路径为空并标待核验；不将Markdown假装成权重。已核验的相机/权重不会被旧issue的空字段或待确认值覆盖。

mem0-ablated绑定#5；ttc-aligned绑定#16；ttc-aligned-ablated分别绑定#19（30k）、#22（20k）。无法绑定的训练占位保留在首页“历史/占位”区，不算已交付权重，不自动标成已测。

## 覆盖状态

- 未开始：无对应v1 A/B行；旧协议成绩不能替代。
- 准入中：已登记v1行，但准入或统计字段尚未齐全。
- 冒烟：前三项准入已通过、20条闭环冒烟尚未通过。
- 阶段A/B进行中：至少一个配置具备准入后产生进度，或4/8步只完成其中一项。
- 完成：对应条件版本的4步、8步均有完成且通过formalIssues的正式结果。

A/B分别显示，条件版本分别列示，H4/H8分别标注；诊断不算完成。相同物理checkpoint的附着/缩放策略只占一行，保留全部条件和record成员。不同数据、相机、训练步数不合并。

**遗漏未评测**红色仅指从未有任何SafeLab-Eval-v1行；不代表历史上完全没有测试。只有v1诊断的权重不会假装完成A/B，会另注“只有诊断，正式A/B未开始”。未登记负责agent的显示待分配，不把WPS训练交接人当成已分配的评测agent。

最近更新时间取该权重明确关联的评测行、issue及record更新时间，不用全站更新时间冒充。没有记录则显示待核对。

## 更新方式

继续通过checkpoint issue登记，维护者审核后将绑定写入records；后续issue更新有精确时间戳，旧快照不覆盖已核验事实。手动维护记录时保留checkpoint_issues。维护者可运行：

```
node scripts/sync-checkpoint-issues.cjs reviewed-issues.json
node scripts/sync-checkpoint-issues.cjs reviewed-issues.json --write
node --test tests/*.test.js
```

脚本仅包含本轮明确审核过的issue映射，不自动批准所有公开提交。更新前拉取最新分支，任何新增issue或修改checkpoint身份须重新审核；脚本不会修改evaluations、campaigns、datasets或诊断证据。
