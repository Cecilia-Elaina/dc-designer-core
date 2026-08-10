# v1.1.4 发布说明

## 修复内容

- Windows CI 优先通过 Chocolatey 的 `pdftoppm` 命令 shim 定位 Poppler。
- 保留真实路径探测作为回退，避免不同 Runner 安装布局导致视觉门禁误报未验证。
- 保持视觉工具缺失时阻断最终导出的质量要求。

## 验证

- Linux 核心测试、Windows 视觉验收和干净安装验收均纳入发布门禁。
