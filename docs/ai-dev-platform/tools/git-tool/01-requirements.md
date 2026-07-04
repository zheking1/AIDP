# git-tool 需求说明

## 1. 背景

AI 开发时需要理解“当前改了什么、历史为什么这样改、某个文件是谁引入的、提交里有什么上下文”。直接让 AI 执行任意 Git 命令有风险，也缺少结构化输出。`git-tool` 通过受控 capability 提供 Git 上下文。

## 2. 场景

- 开发前查看当前工作区状态。
- 修复 bug 前查看相关文件历史。
- 代码审查时生成 diff 摘要。
- AI 完成修改后可选生成提交。
- 与 error-tool 关联修复提交。

## 3. 功能需求

- 登记仓库路径和 project 绑定。
- 获取 branch、HEAD、dirty files。
- 获取 staged/unstaged diff。
- 对 diff 生成按文件摘要。
- 查询 commit history。
- 查看 commit 详情。
- 查询 file history。
- 可选创建 commit。

## 4. 非目标

MVP 不做远程托管平台完整替代，不管理复杂 PR，不自动 push，不自动 rebase/merge，不执行 destructive Git 操作。

## 5. 安全要求

- 默认禁用写操作。
- 禁止 `reset --hard`、`clean -fd`、强制 push。
- 所有路径必须 canonical 后位于 repo root 内。
- 响应中可截断超大 diff。

## 6. 验收范围

- 能读取本地 Git 仓库状态。
- 能返回结构化 diff。
- 能查看提交历史和提交详情。
- 能按文件查历史。
- 写操作关闭时 `git.create_commit` 返回 `FORBIDDEN`。
