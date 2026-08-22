# Selfuse IPA Source

SideStore / AltStore 自动更新个人侧载源。

## 1. 订阅源地址

在 SideStore 或 AltStore 的 Sources 页面添加以下源地址：

```text
https://donald-trump86.github.io/Selfuse-IPA-Source/source.json
```

## 2. 收录应用列表

| 应用名称 | 开发者 | 简介 | 上游仓库 |
| :--- | :--- | :--- | :--- |
| **PiliPlus** | bggRGjQaUbCoE | 哔哩哔哩第三方开源 iOS 客户端 | [bggRGjQaUbCoE/PiliPlus](https://github.com/bggRGjQaUbCoE/PiliPlus) |
| **PiliNara** | Starfallan | PiliPlus 第三方增强改版 | [Starfallan/PiliNara](https://github.com/Starfallan/PiliNara) |
| **uYouEnhanced** | arichornlover | YouTube 修改版（去广告/画中画/下载） | [Timothywag/uYouEnhanced](https://github.com/Timothywag/uYouEnhanced) |

## 3. 本地开发与环境管理

本项目使用 [uv](https://github.com/astral-sh/uv) 进行 Python 环境与依赖管理。

### 环境初始化与同步

```bash
# 同步并安装依赖
uv sync

# 手动执行源数据同步
uv run scripts/sync_source.py
```

### 添加新应用

在 `config/apps.json` 中追加应用配置对象即可：

```json
{
  "name": "AppName",
  "bundleIdentifier": "com.example.app",
  "developerName": "Developer",
  "repo": "owner/repo",
  "assetPattern": ".*\\.ipa$",
  "iconURL": "https://example.com/icon.png",
  "tintColor": "007AFF",
  "subtitle": "副标题",
  "localizedDescription": "应用介绍"
}
```

## 4. 自动化机制

- **定时同步**：由 GitHub Actions 每日自动触发运行 `scripts/sync_source.py`，拉取上游仓库最新 Release 中的 `.ipa` 元数据并生成 `source.json`。
- **静态部署**：通过 GitHub Pages 分发 `source.json`，提供稳定的订阅接口。
