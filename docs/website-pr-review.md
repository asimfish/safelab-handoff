# 评测网站 PR 合并检查

维护者负责合并。以最新 docs/publish 为基准，不把其他agent旧快照覆盖回去。

1. 固定PR head SHA，检查变更文件；本地运行 `node --test tests/*.test.js`。
2. 按id对比datasets、records、evaluations、campaigns及diagnostics。保留其他agent的记录和已有字段；新增schema字段只能补缺失，不能改旧口径或旧数字。进度更新须明确对应的配置与来源。
3. `completed < trials` 时 `success` 必须为null；诊断不能进入正式表。缺v1准入证据不得升格为A/B正式成绩。
4. 有冲突先整合最新发布分支，逐记录保留双方内容；不强推、不整份采用旧data.json。重新运行测试并检查最终diff。
5. schema不合格退回，说明具体id、字段、期望值和复查命令。
6. 通过后合并，核对对应SHA的Pages构建/部署及线上数据。审核通过表示站点数据与发布检查通过，不替代专家回放、真实模型、渲染一致性等物理评测准入。

已知交接条件：Pro6000评测在资源区10，训练交付多在资源区5；两区public相互独立，交付不可见时先查资源区5。
