# git-tool 测试与验收

## 1. 单元测试

- 路径越界被拒绝。
- porcelain status 正确分类。
- diff parser 正确统计 additions/deletions。
- 超大 patch 被截断。

## 2. 集成测试

创建临时 Git 仓库：

1. 初始化提交。
2. 修改文件。
3. 调用 repo_status。
4. 调用 diff_summary。
5. 调用 commit_history。
6. 写操作关闭时 create_commit 返回 FORBIDDEN。

## 3. 安全验收

- 用户无法传入任意 Git 命令。
- 不执行 reset/clean/push。
- 文件路径必须在 repo root 内。
- command timeout 生效。

## 4. 完成标准

全部 MVP capability 可通过 `/tool/invoke` 调用，响应符合工具协议，错误模型统一。
