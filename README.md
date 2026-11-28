# 《克里姆林宫危机：冷战》简体中文汉化补丁

**[下载 Windows 安装程序（.exe）](https://github.com/lingjieheti/crisis-in-the-kremlin-cold-war-zh-cn/releases/latest/download/crisis-in-the-kremlin-cold-war-zh-cn-Setup.exe)**

退出游戏，双击安装程序。它会自动找到 Steam 游戏目录，点击 **安装汉化** 即可。从 Steam 启动游戏即可使用中文。

首次安装如缺少社区翻译底包，请保持 Steam 已登录，安装器会请求 Steam 下载。也可手动选择目录。游戏更新后，可点 **核验汉化** 检查当前安装。需要恢复原版时，点击 **还原原版**。

本版适配 Steam Windows **1.2.5.8 热修（构建 26977018）**。本次校订 110 条游戏文本，恢复 188 个百科入口，并为 Steam Deck 等八种默认手柄布局和动作清单补入 127 项中文。较早构建 26955082、26891377、26243566 仍可安装与还原。[v1.2.6 修订和验证记录](games/coldwar/COMMUNITY-1.2.6.md) · [模组编辑器中英俄对照](docs/mod-editor-zh.md) · [逐文件文字覆盖](docs/resource-coverage.md) · [技术说明](games/coldwar/README.md)

<details>
<summary>从源码构建安装程序</summary>

在 Windows x64 和 Python 3.12 环境中运行：

```powershell
py -3.12 tools/build_setup.py
```

生成的独立 EXE 与 SHA-256 校验文件保存在 `dist` 目录。构建器从 Python.org 获取固定哈希的 Windows 嵌入式运行时。玩家直接使用上方的安装程序。

</details>
