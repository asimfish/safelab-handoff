# 评测网站 PR 合并检查

维护者负责合并。以最新 docs/publish 为基准，不把其他agent旧快照覆盖回去。

1. 固定PR head SHA，检查变更文件；本地运行 `node --test tests/*.test.js`。
2. 按id对比datasets、records、evaluations、campaigns及diagnostics。保留其他agent的记录和已有字段；新增schema字段只能补缺失，不能改旧口径或旧数字。进度更新须明确对应的配置与来源。
3. `completed < trials` 时 `success` 必须为null；诊断不能进入正式表。缺v1准入证据不得升格为A/B正式成绩。
4. 有冲突先整合最新发布分支，逐记录保留双方内容；不强推、不整份采用旧data.json。重新运行测试并检查最终diff。
5. schema不合格退回，说明具体id、字段、期望值和复查命令。
6. 通过后合并，核对对应SHA的Pages构建/部署及线上数据。审核通过表示站点数据与发布检查通过，不替代专家回放、真实模型、渲染一致性等物理评测准入。

已知交接条件：Pro6000评测在资源区10，训练交付多在资源区5；两区public相互独立，交付不可见时先查资源区5。

## 旧进度脚本的发布兼容

Pages构建前运行现有 `scripts/fill-legacy-schema.py`，仅为非v1历史记录补缺失的元数据；脚本逐字段断言旧值不变，并跳过v1记录。该修补仅作用于构建工作区和发布产物，不改源分支的评测数字。随后仍执行全套测试：v1准入、unknown守恒、checkpoint唯一绑定等错误继续阻止发布。

这不是允许提交删字段的PR；审核仍须退回覆盖新字段或其他agent记录的改动。源端生成器仍应保留schema。此步骤只防止历史缺项让其他已审核更新长期停留在上一快照。


## SafeLab-Eval-v1.1 上线后

现行放置判定使用protocol_version=SafeLab-Eval-v1.1、oracle_version=placement-v1.1；strict-v1双轨独立保留。审核新增executor_parity验收报告，仍核对完整分母、unknown、seed、左右及阶段统计。作废漂移候选不显示；不得以改名代替重算或必要的执行链重跑。覆盖只统计v1.1所有变种/步数/条件，缺项不得伪造开测或排期。

Pages构建还运行两组真实Chrome页面检查（unknown/oracle切换与覆盖表）；通过才上传。临时页面测试样例只在runner内存与.qa产生，发布前清理，不写入data.json或成绩档案。本机浏览器受共享工作站I/O阻塞时，由CI实际执行验收，不声称本机已通过。
