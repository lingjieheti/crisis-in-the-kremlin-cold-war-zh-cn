# 构建 26977018 文字覆盖清单

同一 Steam 安装包含英文和俄文两份 XML，以及启动时由界面控件或程序组装的内容。下列文件按对象表清点。外文资料链接保留原版提供的目标，打开后的网页语言取决于该网站。

## 游戏语言 XML

两份原版 XML 位于 `CrisisInTheKremlin2_Data/resources.assets`。当前游戏 19,631 个字段中，19,620 个非空英文字段均有中文内容或对应网址。九个事件空字段沿用原版留白，俄文公文用的两个缩写在中、英资源中留空。表中的“本版改动”与同一游戏构建上 v1.2.5 的成品比较。

| 游戏 XML 分区 | 字段 | 英文非空 | 最终中文非空 | 叶属性 | 本版改动 |
|---|---:|---:|---:|---:|---:|
| `system` | 55 | 55 | 55 | 5 | 0 |
| `uow` | 26 | 26 | 26 | 0 | 0 |
| `ui` | 83 | 83 | 83 | 2 | 0 |
| `save_load_menu` | 19 | 19 | 19 | 0 | 0 |
| `coordinates_system` | 4 | 4 | 4 | 0 | 0 |
| `gender` | 2 | 2 | 2 | 0 | 0 |
| `event_document_desc` | 15 | 13 | 13 | 0 | 1 |
| `tutorial` | 136 | 136 | 136 | 0 | 1 |
| `statistic_impact_source_name` | 67 | 67 | 67 | 0 | 0 |
| `statistic_value_group_name` | 6 | 6 | 6 | 0 | 0 |
| `warSectorNames` | 117 | 117 | 117 | 0 | 0 |
| `flag_desc` | 10 | 10 | 10 | 0 | 0 |
| `hotkey` | 2 | 2 | 2 | 0 | 0 |
| `mod_creation` | 53 | 53 | 53 | 0 | 0 |
| `science_points_types` | 4 | 4 | 4 | 0 | 0 |
| `wars_window` | 104 | 104 | 104 | 0 | 0 |
| `wars_buttons_name` | 50 | 50 | 50 | 0 | 0 |
| `wars_buttons_desc` | 30 | 30 | 30 | 0 | 0 |
| `war_sides_names` | 91 | 91 | 91 | 0 | 0 |
| `wars` | 15 | 15 | 15 | 0 | 0 |
| `dlcs` | 8 | 8 | 8 | 0 | 0 |
| `science_type` | 6 | 6 | 6 | 0 | 0 |
| `custom_images` | 11 | 11 | 11 | 2 | 0 |
| `base_type` | 2 | 2 | 2 | 0 | 0 |
| `threshold` | 36 | 36 | 36 | 0 | 0 |
| `scenesNames` | 8 | 8 | 8 | 0 | 0 |
| `citations` | 103 | 103 | 103 | 103 | 0 |
| `text_formatting` | 49 | 49 | 49 | 0 | 0 |
| `map_type_name` | 22 | 22 | 22 | 0 | 0 |
| `zone_names` | 11 | 11 | 11 | 0 | 0 |
| `leader_type_name` | 10 | 10 | 10 | 0 | 0 |
| `regions` | 337 | 337 | 337 | 0 | 0 |
| `puppet_type_name` | 7 | 7 | 7 | 0 | 0 |
| `diplomacy_country_icons` | 62 | 62 | 62 | 0 | 1 |
| `map_left_panel_ui` | 87 | 87 | 87 | 0 | 0 |
| `event_window` | 7 | 7 | 7 | 0 | 0 |
| `government_type` | 17 | 17 | 17 | 0 | 0 |
| `positions_wiki` | 16 | 16 | 16 | 0 | 0 |
| `char_wiki_links` | 365 | 365 | 365 | 0 | 98 |
| `player_country_desc` | 571 | 571 | 571 | 0 | 0 |
| `foreign_party_names` | 1117 | 1117 | 1117 | 0 | 0 |
| `foreign_leader_names` | 117 | 117 | 117 | 0 | 0 |
| `foreign_party_desc` | 1119 | 1119 | 1119 | 0 | 0 |
| `encyclopedia` | 2 | 2 | 2 | 0 | 0 |
| `encyclopedia_sections` | 1 | 1 | 1 | 0 | 0 |
| `encyclopedia_subsections` | 2 | 2 | 2 | 0 | 0 |
| `encyclopedia_texts` | 2 | 2 | 2 | 0 | 0 |
| `notifications_names` | 72 | 72 | 72 | 0 | 0 |
| `notifications_descs` | 102 | 102 | 102 | 7 | 0 |
| `income_source_names` | 9 | 9 | 9 | 0 | 0 |
| `conspiracy_type_names` | 19 | 19 | 19 | 0 | 0 |
| `conspiracy_desc` | 125 | 125 | 125 | 0 | 0 |
| `statistic_window` | 4 | 4 | 4 | 0 | 0 |
| `statistic_values_names` | 73 | 73 | 73 | 0 | 0 |
| `statistic_values_descs` | 70 | 70 | 70 | 90 | 1 |
| `high_council_window` | 83 | 83 | 83 | 0 | 0 |
| `pseudoModificator` | 446 | 446 | 446 | 4 | 4 |
| `economic_window` | 94 | 94 | 94 | 2 | 0 |
| `politics_window` | 327 | 327 | 327 | 1 | 0 |
| `politic_position_name` | 53 | 53 | 53 | 0 | 0 |
| `endings_names` | 27 | 27 | 27 | 0 | 0 |
| `endings_desc` | 374 | 374 | 374 | 745 | 8 |
| `country_additionalDescription` | 15 | 15 | 15 | 0 | 0 |
| `factions_names` | 39 | 39 | 39 | 0 | 0 |
| `SupremeSoviet_names` | 36 | 36 | 36 | 0 | 0 |
| `faction_window` | 18 | 18 | 18 | 0 | 0 |
| `decisions_window` | 65 | 65 | 65 | 0 | 0 |
| `doctrines_window` | 169 | 169 | 169 | 8 | 1 |
| `doctrine_type_names` | 25 | 25 | 25 | 0 | 0 |
| `doctrine_variant_names` | 177 | 177 | 177 | 0 | 0 |
| `doctrine_variant_descs` | 177 | 177 | 177 | 323 | 2 |
| `expense_group` | 8 | 8 | 8 | 0 | 0 |
| `expense_type` | 34 | 34 | 34 | 0 | 0 |
| `expense_effects` | 26 | 26 | 26 | 0 | 1 |
| `expense_desc` | 11 | 11 | 11 | 14 | 1 |
| `science_window` | 36 | 36 | 36 | 0 | 0 |
| `country_names` | 638 | 638 | 638 | 0 | 0 |
| `military_alliance_type` | 7 | 7 | 7 | 0 | 0 |
| `economy_alliance_type` | 11 | 11 | 11 | 0 | 0 |
| `science_names` | 60 | 60 | 60 | 0 | 0 |
| `science_descs` | 60 | 60 | 60 | 120 | 1 |
| `thirdWorld_texts` | 20 | 20 | 20 | 0 | 0 |
| `icon_desc` | 144 | 144 | 144 | 2 | 0 |
| `country_bar` | 9 | 9 | 9 | 0 | 0 |
| `buttons_names` | 238 | 238 | 238 | 0 | 2 |
| `buttons_desc` | 148 | 148 | 148 | 4 | 5 |
| `settings` | 72 | 72 | 72 | 0 | 0 |
| `credits` | 1 | 1 | 1 | 2 | 0 |
| `gamestart` | 58 | 58 | 58 | 0 | 0 |
| `autosavetype` | 4 | 4 | 4 | 0 | 0 |
| `quality_preset` | 18 | 18 | 18 | 0 | 0 |
| `tooltip_pin_type` | 3 | 3 | 3 | 0 | 0 |
| `secondary_button_type` | 5 | 5 | 5 | 0 | 0 |
| `secondary_button_name` | 11 | 11 | 11 | 0 | 0 |
| `music_start_type` | 4 | 4 | 4 | 0 | 0 |
| `keep_pinned_tooltip` | 2 | 2 | 2 | 0 | 0 |
| `reduced_motion` | 2 | 2 | 2 | 0 | 0 |
| `ui_platform` | 5 | 5 | 5 | 0 | 0 |
| `only_unmet_conditions` | 2 | 2 | 2 | 0 | 0 |
| `camera_scale` | 2 | 2 | 2 | 0 | 0 |
| `map_settings_type` | 5 | 5 | 5 | 0 | 0 |
| `politics_names` | 418 | 418 | 418 | 0 | 0 |
| `politics_desc` | 19 | 19 | 19 | 17 | 0 |
| `politics_long_desc` | 19 | 19 | 19 | 1 | 0 |
| `scenario_desc` | 4 | 4 | 4 | 0 | 0 |
| `character_creation` | 38 | 38 | 38 | 8 | 1 |
| `character_characteristics` | 3 | 3 | 3 | 0 | 0 |
| `trait_titles` | 61 | 61 | 61 | 0 | 0 |
| `trait_desc` | 4 | 4 | 4 | 0 | 0 |
| `track_names` | 100 | 100 | 100 | 0 | 0 |
| `albums` | 7 | 7 | 7 | 0 | 0 |
| `albums_descs` | 7 | 7 | 7 | 0 | 0 |
| `input_management` | 4 | 4 | 4 | 0 | 0 |
| `decision_names` | 257 | 257 | 257 | 0 | 0 |
| `decision_desc` | 263 | 263 | 263 | 294 | 1 |
| `modif_names` | 157 | 157 | 157 | 2 | 0 |
| `modif_desc` | 733 | 733 | 733 | 71 | 5 |
| `usa_presidents` | 11 | 11 | 11 | 0 | 0 |
| `conditions` | 686 | 686 | 686 | 41 | 0 |
| `achievement_conditions` | 46 | 46 | 46 | 2 | 0 |
| `achievement_texts` | 196 | 196 | 196 | 0 | 1 |
| `achievements_window` | 39 | 39 | 39 | 0 | 0 |
| `exhibition_window` | 53 | 53 | 53 | 0 | 0 |
| `notifications_window` | 20 | 20 | 20 | 0 | 0 |
| `map_journal` | 30 | 30 | 30 | 0 | 0 |
| `what_if_window` | 24 | 24 | 24 | 0 | 0 |
| `events` | 6181 | 6172 | 6172 | 5885 | 62 |
| `patchnotes` | 20 | 20 | 20 | 8 | 0 |
| `statistics` | 2 | 2 | 2 | 0 | 0 |
| `modtool` | 299 | 299 | 299 | 0 | 2 |
| `doctrine_wiki_links` | 154 | 154 | 154 | 0 | 41 |
| `decision_wiki_links` | 160 | 160 | 160 | 0 | 49 |
| `parliament_polls` | 39 | 39 | 39 | 0 | 0 |
| `ruler_polls` | 33 | 33 | 33 | 0 | 1 |
| `electoral_system` | 14 | 14 | 14 | 0 | 0 |
| `nuclear_outro` | 161 | 161 | 161 | 0 | 8 |
| `onscreen_keyboard` | 6 | 6 | 6 | 0 | 0 |
| `orrery` | 69 | 69 | 69 | 0 | 0 |
| `desk` | 22 | 22 | 22 | 0 | 0 |
| `statistic_event_triggers` | 2 | 2 | 2 | 0 | 0 |
| `bug_report` | 43 | 43 | 43 | 0 | 0 |

## 游戏场景和资源容器

在 24 个场景、26 个独立资源容器和 24 个 Addressables 内容包中枚举了 69,219 个对象。其中 1,749 个 TMP 文本组件用于承载界面。500 个 SimpleTranslator 绑定引用 286 个不同的中文字段，均可在本版 XML 找到。其他组件还有从当前存档、外交状态、图表、程序或输入系统即时生成的文字。场景中的设计占位文字不能直接代表玩家看到的文字。

| 文件 | Unity 对象 | TMP 文本组件 | SimpleTranslator 绑定 | TextAsset |
|---|---:|---:|---:|---:|
| `level0` | 640 | 24 | 1 | 0 |
| `level1` | 450 | 28 | 12 | 0 |
| `level2` | 25 | 1 | 0 | 0 |
| `level3` | 1707 | 111 | 53 | 0 |
| `level4` | 913 | 61 | 37 | 0 |
| `level5` | 2020 | 97 | 27 | 0 |
| `level6` | 8846 | 123 | 19 | 0 |
| `level7` | 3134 | 77 | 14 | 0 |
| `level8` | 583 | 31 | 22 | 0 |
| `level9` | 2420 | 43 | 9 | 0 |
| `level10` | 4240 | 103 | 32 | 0 |
| `level11` | 5092 | 189 | 48 | 0 |
| `level12` | 2839 | 79 | 32 | 0 |
| `level13` | 5023 | 188 | 33 | 0 |
| `level14` | 4382 | 144 | 49 | 0 |
| `level15` | 3533 | 98 | 13 | 0 |
| `level16` | 2816 | 85 | 20 | 0 |
| `level17` | 137 | 3 | 1 | 0 |
| `level18` | 3177 | 103 | 31 | 0 |
| `level19` | 340 | 26 | 18 | 0 |
| `level20` | 762 | 61 | 15 | 0 |
| `level21` | 394 | 25 | 11 | 0 |
| `level22` | 266 | 19 | 2 | 0 |
| `level23` | 253 | 24 | 1 | 0 |
| `sharedassets0.assets` | 889 | 0 | 0 | 0 |
| `sharedassets1.assets` | 68 | 0 | 0 | 0 |
| `sharedassets10.assets` | 19 | 0 | 0 | 0 |
| `sharedassets11.assets` | 55 | 0 | 0 | 0 |
| `sharedassets12.assets` | 1 | 0 | 0 | 0 |
| `sharedassets13.assets` | 9 | 0 | 0 | 0 |
| `sharedassets14.assets` | 1 | 0 | 0 | 0 |
| `sharedassets15.assets` | 1 | 0 | 0 | 0 |
| `sharedassets16.assets` | 1 | 0 | 0 | 0 |
| `sharedassets17.assets` | 49 | 0 | 0 | 0 |
| `sharedassets18.assets` | 1 | 0 | 0 | 0 |
| `sharedassets19.assets` | 1 | 0 | 0 | 0 |
| `sharedassets2.assets` | 1 | 0 | 0 | 0 |
| `sharedassets20.assets` | 1 | 0 | 0 | 0 |
| `sharedassets21.assets` | 35 | 4 | 0 | 0 |
| `sharedassets22.assets` | 1 | 0 | 0 | 0 |
| `sharedassets23.assets` | 1 | 0 | 0 | 0 |
| `sharedassets3.assets` | 58 | 0 | 0 | 0 |
| `sharedassets4.assets` | 142 | 0 | 0 | 0 |
| `sharedassets5.assets` | 628 | 0 | 0 | 0 |
| `sharedassets6.assets` | 2262 | 0 | 0 | 0 |
| `sharedassets7.assets` | 1 | 0 | 0 | 0 |
| `sharedassets8.assets` | 6 | 0 | 0 | 0 |
| `sharedassets9.assets` | 35 | 0 | 0 | 0 |
| `globalgamemanagers.assets` | 3267 | 0 | 0 | 0 |
| `resources.assets` | 303 | 2 | 0 | 12 |
| `StreamingAssets/aa/StandaloneWindows64/2aa1e9a04743df76a8078378c29f7a8b_unitybuiltinshaders_7db5a15cdd62a57400473bb20b836010.bundle` | 2 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/character_ussr_assets_all_6446aefd9651a95328746b7067a740ee.bundle` | 420 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/decision_icons_assets_all_794dabe1e05687c05e8a780c88ae75da.bundle` | 223 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/ending_icons_assets_all_953b53d0c52f79c7306799a8efba2b4a.bundle` | 40 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/event_icons_assets_all_47cd4bdf87f7a6ebc2d51c408c43bd29.bundle` | 536 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/interface_skins_assets_interface_skin_capitalism_a12cd6045f6c01a785dda2602b3e9c1d.bundle` | 16 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/interface_skins_assets_interface_skin_monarchy_0b79a3b67429a7bb6637562ac74e3c05.bundle` | 16 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/interface_skins_assets_interface_skin_nationalism_38b787ed85aed76bd4b595be45245911.bundle` | 16 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/interface_skins_assets_interface_skin_religiosity_46b9d5898b3d00396253297223feb8d2.bundle` | 16 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/modificator_icons_assets_all_628f8a1774563272916334a96d69308c.bundle` | 120 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/position_sov_icons_assets_all_f9e64d7b73f2bda9561a048c453436af.bundle` | 32 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war0_assets_all_2e91e99abdaa2f133677a636b5cc3447.bundle` | 436 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war10_assets_all_185d4f0fe95e83a18872bc177e6fbac0.bundle` | 329 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war11_assets_all_6e7f3f6deaf9f430fb8657bfa454385a.bundle` | 453 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war12_assets_all_2a65ac4984b27cad4ab41afb8028fd06.bundle` | 320 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war13_assets_all_92490da10845946565ed51af7c332520.bundle` | 552 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war1_assets_all_bceb569f55a14c15d22f65600aeaa486.bundle` | 354 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war2_assets_all_4382d6b982bef0cc976164ae79449e06.bundle` | 466 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war3_assets_all_b2b853b33da0f971bcc5529e64367b25.bundle` | 708 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war4_assets_all_28d19e2a1d66e1fa001985bc4447eabc.bundle` | 341 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war5_assets_all_daf65eceff342942ced96b5ffb21c56a.bundle` | 486 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war6_assets_all_12467c0bb83f3a7a463f704160ae1ece.bundle` | 362 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war7_assets_all_8958cadedd3fa2ba73ac39f091768bfe.bundle` | 762 | 0 | 0 | 0 |
| `StreamingAssets/aa/StandaloneWindows64/war9_assets_all_bb1b74a5b56b0094a6a32f6031c741da.bundle` | 385 | 0 | 0 | 0 |

资源文件的 12 个 TextAsset 包括两份语言 XML、八份开局配置及两份 Unicode 换行字符表。对 1985、1988、1991 开局的 JSON 字段检查发现，带自然语言或空格的非结构值是开发者注释和一个末尾带空格的特质 ID。24 个 Addressables 包包括事件/决议图标、人物头像、战争地图和四款界面皮肤。其中的 1,522 个行为均可解析为事件触发器、悬停组件、颜色切换器或战争地图对象，没有独立语言 TextAsset。

安装目录的 `1.png`、`2.png`、`3.png` 是 2048×1080 的插画。插画、旗帜和宣传画上的原图文字保留原作。支持者版 DLC「突击手」奖章与证书的合并悬停文字取自 `/desk/desk_patron`。游戏内成就名称和说明在上述 XML 表中；Steam 商店、平台成就页和系统通知由其各自的服务提供。[Steam 支持者版](https://store.steampowered.com/app/3637930/)

## Steam Input 默认布局

仅对本构建的游戏目录 `steam_input` 中九份已验证文件的 localization 字段添加简体中文。原来的英俄项和按键绑定全部保留。Valve 的动作清单支持 `schinese` 本地化段。[Steamworks 手柄本地化说明](https://partner.steamgames.com/doc/features/steam_controller/iga_file#localization)

| 文件 | 本地化标签 |
|---|---:|
| `controller_generic.vdf` | 15 |
| `controller_neptune.vdf` | 20 |
| `controller_ps4.vdf` | 15 |
| `controller_ps5.vdf` | 15 |
| `controller_switch_pro.vdf` | 15 |
| `controller_xbox360.vdf` | 15 |
| `controller_xboxelite.vdf` | 15 |
| `controller_xboxone.vdf` | 15 |
| `steam_input_manifest.vdf` | 2 |

## 程序生成的文字

在本机构建的官方游戏程序中只读枚举 37,771 次字符串装载和 8,491 个不同字面串。其中包括语言键、调试日志、路径、格式串和少量用于界面的英俄文字。语言选择器的 English、输入系统返回的完整按键名（例如 Press O）、Steam 初始化失败时程序附加的原始诊断和原生文件选择框依赖程序、Steam 或 Windows。安装器保留原版程序、签名和 DLC 校验。游戏设置已用中文说明语言槽。

模组编辑器中的 99 个条件名字和 103 个效果名字直接来自原程序的英文、俄文字段。类别、菜单、提示及帮助使用模组编辑器的中文 XML。程序中另有一组旧式编辑条目，含 13 条条件、21 条效果，也可按中英俄任一语言查询。[模组编辑器三语对照表](mod-editor-zh.md)
