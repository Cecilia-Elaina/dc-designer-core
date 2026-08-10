# v1.1.3 发布说明

## 修复内容

- Windows 视觉质量门禁现在支持通过 `PDFTOPPM_PATH` 显式定位 Poppler 的 `pdftoppm.exe`。
- Windows CI 安装视觉工具后自动探测 LibreOffice 和 Poppler 的实际安装路径，并对工具版本进行探测。
- 保持缺少视觉工具时返回 `unverified` 并阻断最终导出的质量要求。

## 验证

- 新增显式 `pdftoppm` 路径解析回归测试。
- Linux 核心测试、Windows 视觉验收和干净安装验收均纳入发布门禁。
