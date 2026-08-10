# v1.1.2 发布说明

这是面向 Windows 持续集成环境的修复版本，保留 v1.1.1 的产品功能和发布包结构。

## 修复内容

- 在 Windows CI runner 中安装 LibreOffice 和 Poppler。
- 将视觉工具路径写入后续 CI 步骤，确保三类 K12 验收案例执行真实分页检查。
- 保持 Linux 核心测试、Windows 编码修复和固定测试夹具。

## 验证

- 本地针对性测试：61 passed。
- 本地发布审计：pass。
- 本地干净安装验收：pass。
- 远程 Linux 核心 CI：通过。
