# GitHub 发布说明

本项目的 GitHub 发布分为两步：先把源码和版本标签推送到公开仓库，再在 GitHub 页面创建 Release。仓库本身不会自动进入 Codex Plugin Directory。

## 1. 创建空仓库

创建一个公开 GitHub 仓库。不要初始化 README、`.gitignore` 或 License，以免与本地历史产生无关冲突。

## 2. 推送源码和标签

在项目根目录运行干运行检查：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_github.ps1 `
  -RepositoryUrl https://github.com/<owner>/<repository> `
  -DryRun
```

确认输出中的仓库、分支和标签正确后，去掉 `-DryRun` 再运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_github.ps1 `
  -RepositoryUrl https://github.com/<owner>/<repository>
```

脚本会检查：

- 工作区没有未提交修改；
- `v1.1.1` 标签存在并指向当前提交；
- `origin` 不存在，或已经指向同一个 GitHub 仓库；
- 只推送当前分支和明确的版本标签；
- 不保存 GitHub 密码、令牌或教师资料。

脚本不会创建 GitHub 仓库，也不会强制覆盖远程分支。认证由 Git Credential Manager、SSH 或用户当前的 GitHub 登录方式负责。

## 3. 创建 GitHub Release

在仓库页面以 `v1.1.1` 标签创建 Release，附加：

- `dist/dc-designer-core-v1.1.1.zip`；
- `dist/dc-designer-core-v1.1.1.release.json`；
- `dist/dc-designer-core-v1.1.1.zip.sha256`（如果发布包目录中已生成）。

Release 说明使用 `docs/release_notes.md`，并明确当前只支持中国大陆 K12 信息科技/信息技术，不支持高校、职教、企业培训和其他学科。

## 4. Codex Plugin Directory

GitHub Release 只解决源码和安装包分发。是否能在 Codex 的 Plugin Directory 中被发现，还取决于 OpenAI 工作区的插件目录、应用发布入口、账号权限和审核流程。提交前必须再次核对官方入口，不把“本地可安装”或“GitHub 已公开”表述成“官方目录已上架”。
