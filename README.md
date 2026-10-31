# SafeLab 任务交接台

https://asimfish.github.io/safelab-handoff/

按 **任务 → 精确数据版本 → 相机 → 方法 / run / checkpoint** 交接。

## 团队日常使用

1. 训练同学选择任务与数据版本，点击「新增训练权重」，填写路径、相机、步数和负责人。
2. 点击「到 GitHub 确认保存」，登录 GitHub 并点击 **Submit new issue**。
3. 返回面板点击「同步更新」。团队成员会看到同一条记录，无需重新部署网站。
4. 评测同学点击对应权重的「编辑交接」，更新状态、负责人、4/8步成绩与测试条件，再到 GitHub 确认。
5. 新版本请选择「新的数据版本」，不要覆盖旧版本的路径。不同 run、不同相机或不同权重路径是新条目。

GitHub Issues 是共享存储和审计记录。OWNER、MEMBER、COLLABORATOR 作者的合法记录直接生效。
外部作者需维护者添加 `safelab-approved` 标签。关闭交接单不删除记录；
添加 `safelab-archived` 标签才停止使用该单。不要在交接单写任何凭据。
同一权重的多份更新以更新时间最新为准；原始评测证据不被覆盖。
网页编辑会生成新的更新单；也可在 GitHub 原单的正文中修改其 JSON 数据块。

## 数据与发布

- `data.json`：经过来源核对的导入基线，保留全部历史实验条件和证据。
- GitHub 共享交接单：新增权重、团队状态和团队填报成绩，动态读取。
- `model.js`：严格校验、身份关联和结果归并；`app.js`：任务导航、表单及同步。
- `node --test tests/model.test.js`：数据绑定、分母、并发更新与不可信输入回归。
- Pages 发布源：`docs/publish` 分支根目录。

页面每5分钟读取共享记录，切回页面和手动同步也会更新。GitHub 未认证读取有额度限制，
失败时页面会明确显示同步错误并保留基线或上次成功记录。浏览器不保存任何 GitHub token。
这是公开站点，GitHub 确认提交后的权重路径、负责人和结果均为公开内容。

设计与边界见 [ADR](docs/designs/001-shared-handoff.md)。
