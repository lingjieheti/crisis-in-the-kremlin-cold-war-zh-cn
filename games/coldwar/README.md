# 《克里姆林宫危机：冷战》简体中文校订

适用于 Steam Windows 版《Crisis in the Kremlin: The Cold War》1.2.5.6，构建号 26243566。本补丁从玩家的“社区中文翻译”生成本地模组，包含 769 项中文校订和 437 个中文百科链接。安装器只需 Python 3.10 或更高版本。安装后的游戏不需要 Python 常驻。

## 安装与还原

1. 在 Steam 安装游戏，下载工坊模组“社区中文翻译”。等待 Steam 下载完成后，退出游戏。[社区中文翻译 · 创意工坊物品 3523398274](https://steamcommunity.com/sharedfiles/filedetails/?id=3523398274)
2. 在本目录运行下方命令。安装会启用“社区中文翻译 · 本地校订”，并记录原先的基包启用状态。

```powershell
py -3 patch.py install
py -3 patch.py verify
```

需要指定目录时，可向 `install` 添加 `--base "工坊模组的实际目录"` 和 `--game-dir "游戏的实际目录"`。如电脑使用 `python` 命令，可以用它代替 `py -3`。

已安装三款合集 v1.0.0 的玩家也可直接运行同一条 `install` 命令。升级核对原有三个模组文件，更新中文文本，保留最初的字体备份和游戏里当前的各项模组开关。如果此前主动停用了本地校订，升级后仍可在游戏内自行启用。`verify` 会告诉你模组是否已启用。升级过程中若被中断，退出游戏后重新运行 `install` 可以继续，运行 `restore` 可以回退。

退出游戏后运行以下命令还原。程序会还原汉化字体文件和先前的基包启用状态，其他模组的后续开关调整会保留。

```powershell
py -3 patch.py restore
```

原字体资源备份在 `%USERPROFILE%\AppData\LocalLow\Nostalgames\CrisisInTheKremlin2\.zhcn-original-sharedassets0.assets`。安装记录保存在同目录的 `.zhcn-coldwar-install.json`。游戏或社区基包更新后，旧补丁会检查资源指纹。在重新适配前，保留原始备份。

## 内容与校验

- 校订全部 397 个玩家国家、加盟共和国、特殊政体及王朝名称项。动态地名使用类似“俄罗斯-RUS”的写法，照顾引擎按大写字母生成地图简称的规则。架空政体名称可直接显示为“俄罗斯总督区”“高棉伊斯兰民主共和国”等。
- 修订主菜单、开局选项、存档版本说明、通知和事件叙述。政治事件中的职务变化、时间、引语和人名占位符均与英文和俄文资源交叉核对。
- 重译两份更新日志。其中 1.2.5.5 有 88 项，1.2.5.6 有 13 项。补丁适配了游戏按大小写识别标题的方式，纯中文正文可以正确计入相应小节。
- 汉字采用 Noto Sans SC 字形，保留原多语种备用字体的覆盖。字体处理了 3,110 个码位，本版全部 3,077 个汉字和 3,209 个不同可打印字符均有字形。补全了原字库缺少的 9 个汉字及 5 个符号，包含氘、氚、钚、锕和趋势箭头。Unity 资源包中 831 个对象仅有一个字体对象发生变化。
- 本轮细读并校订了 171 条正文，涉及结局错段、政体、外交资格和阵营条件、议会席位、科技词条、人物能力与决议效果。百科资料中 277 个空链接补上了对应中文页，160 个外文链接改用了已确认的中文目的地。
- 英俄中三份资源的 18,133 项均已按键检查。决议有 12 条按游戏实际传入的参数核验，其余行按官方英文的 .NET 格式串核验。原地升级、新装、校验、回退、用户停用模组及中断处理均已隔离验证。范围、命令和剩余疑点见 [本版审校记录](AUDIT.md)。
- 已在 Windows 实机打开主菜单、开局选项、人物卡、战略地图和中国外交面板，观察到中文正常显示。两份更新日志分别显示 88 和 13 项，正文、项目符号和缩进均已在窗口核实。
- 其余文本沿用社区译本。190 个有官方外文来源的链接字段仍为空。两段百科示例正文按开发者提供的占位文字翻译。上述窗口测试对应沿用的菜单、公告及字体；本轮新译的剧情分支已审读资源，未逐一在游戏中触发。

## 来源与维护

社区基包由风过回廊、clovem、东德龙鸣政委亚里莎等维护。原项目还鸣谢 motandsea、Komulaium（Komoon）、苍井绘梨花、Artoria-123、clovem1188 和 LTY-360（LTY_360）。游戏原始资源与社区完整译本均来自玩家的本机安装。[社区汉化项目](https://steamcommunity.com/sharedfiles/filedetails/?id=3523398274) · [Steam 游戏页](https://store.steampowered.com/app/1922740/)

`patch.json` 保存本次原创译文。`font.bsdiff` 保存开源字体的差分。字体采用 SIL Open Font License 1.1，新生成的字体内部名称为 Kremlin UI SC Regular。许可与署名见 [FONT-LICENSE.txt](FONT-LICENSE.txt)。[Go Noto Universal](https://github.com/satbyy/go-noto-universal/tree/0f4be64) · [Noto Sans CJK](https://github.com/notofonts/noto-cjk)

维护者可使用 `build_font_delta.py` 从原始 Go Noto Kurrent 字体、原捐赠字体 `fonts/UI-Regular.ttf` 和原字形清单所用的 v1.0.0 中文 `text.xml` 重建沿用的字体差分。该构建步骤使用 fonttools 和 bsdiff4。日常安装、校验与还原全部使用 Python 标准库。[首版合集源码与字体](https://github.com/lingjieheti/nostalgames-zh-cn/tree/v1.0.0)


重建字体差分时使用的基准字重已固定至合集 v1.0.0。[下载常规字体](https://github.com/lingjieheti/nostalgames-zh-cn/raw/c4aa567c284c7795d0df1db091fff53599b3f53b/fonts/UI-Regular.ttf)
