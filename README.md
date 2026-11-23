# 《克里姆林宫危机：冷战》简体中文汉化补丁

**[下载 Windows 安装程序（.exe）](https://github.com/lingjieheti/crisis-in-the-kremlin-cold-war-zh-cn/releases/latest/download/crisis-in-the-kremlin-cold-war-zh-cn-Setup.exe)**

退出游戏，双击安装程序。它会自动找到 Steam 游戏目录，点击 **安装汉化** 即可。从 Steam 启动游戏即可使用中文。

首次安装如缺少社区翻译底包，请保持 Steam 已登录，安装器会请求 Steam 下载。也可手动选择目录。需要恢复原版时，再次打开安装程序，点击 **还原原版**。

适配 Steam Windows x64 构建 **26243566**。[校对记录](games/coldwar/AUDIT.md) · [补丁来源与技术说明](games/coldwar/README.md) · [游戏内截图](docs/coldwar-changelog.webp)

<details>
<summary>从源码构建安装程序</summary>

在 Windows x64 和 Python 3.12 环境中运行：

```powershell
py -3.12 tools/build_setup.py
```

生成的独立 EXE 与 SHA-256 校验文件保存在 `dist` 目录。构建器从 Python.org 获取固定哈希的 Windows 嵌入式运行时。玩家直接使用上方的安装程序。

</details>
