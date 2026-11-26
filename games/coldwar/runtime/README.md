# 界面文字的本地构建

游戏从自己的程序生成语言名称、天象馆按键和启动提示。安装程序用 Windows 自带的 .NET Framework 编译器和随包的 Mono.Cecil 0.11.6，在临时目录从玩家当前构建的程序集生成界面修订。每次写入都先验证原件和输出的 SHA-256。还原时使用该构建单独保留的原件。

`LabelText.cs` 处理中文提示语和原生按键名称。`BuildLabels.cs` 修改对应的显示方法，并在游戏载入语言时按当前目标语言应用已启用的本翻译。游戏运行期间沿用本身的模组、输入系统和消息队列，无需额外插件。游戏的原始文件和生成后的游戏程序集均在本机处理。

Mono.Cecil 使用 MIT 许可，此目录保留了官方 NuGet 包及其许可。安装器校验包后仅使用 `lib/net40/Mono.Cecil.dll` 构建本地副本。[官方 NuGet 包](https://www.nuget.org/packages/Mono.Cecil/0.11.6) · [源码](https://github.com/jbevain/cecil/tree/0.11.6) · [许可](Mono.Cecil-LICENSE.txt)
