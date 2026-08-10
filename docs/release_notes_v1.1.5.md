# v1.1.5 发布说明

## 修复内容

- Windows CI 改用 Poppler Windows 官方预编译包，不再使用只包含源码的 Chocolatey `poppler` 包。
- 固定 Poppler `26.02.0-0`，解压后显式传递 `PDFTOPPM_PATH`，保证逐页 Word 视觉验收可以执行。
- 继续保持视觉工具缺失时阻断最终导出的质量要求。

## 验证

- Linux 核心测试、Windows 视觉验收和干净安装验收均纳入发布门禁。
