# 《克里姆林宫危机：冷战》简体中文汉化补丁

**[下载 Windows 安装程序（.exe）](https://github.com/lingjieheti/crisis-in-the-kremlin-cold-war-zh-cn/releases/latest/download/crisis-in-the-kremlin-cold-war-zh-cn-Setup.exe)**

退出游戏，双击安装程序。它会自动找到 Steam 游戏目录，点击 **安装汉化** 即可。从 Steam 启动游戏即可使用中文。

首次安装如缺少社区翻译底包，请保持 Steam 已登录，安装器会请求 Steam 下载。也可手动选择目录。游戏更新后，可点 **核验汉化** 检查当前安装。需要恢复原版时，点击 **还原原版**。

本版适配 Steam Windows 版 **1.2.5.8 热修（构建 26977018）**。新增中文说明涵盖选举前三党得票预测、支持者转投和领导方针偏移，另校订了三条乌克兰选举结局。也支持较早的 1.2.5.8（26955082）、1.2.5.7（26891377）与 1.2.5.6（26243566）。沿用原版程序和签名，更新后可在安装器中点击 **安装汉化**。[本版修订说明](games/coldwar/COMMUNITY-1.2.5.md) · [本版支持者奖章实机图](docs/steam-hotfix-26977018.webp) · [文本审校记录](games/coldwar/AUDIT.md) · [技术说明](games/coldwar/README.md)

<details>
<summary>从源码构建安装程序</summary>

在 Windows x64 和 Python 3.12 环境中运行：

```powershell
py -3.12 tools/build_setup.py
```

生成的独立 EXE 与 SHA-256 校验文件保存在 `dist` 目录。构建器从 Python.org 获取固定哈希的 Windows 嵌入式运行时。玩家直接使用上方的安装程序。

</details>
