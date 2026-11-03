# GitHub 发布准备

## 当前发布范围

- `projects/pc-integrated/`：最新版 PC 整合版 v4.1、歌曲描述和谱面。
- `projects/standalone/`：独立运行版源码、构建器、编辑器、测试、MIDI 和生成的刷入文件。
- `tools/chart-studio/`：音频版 Chart Studio v1.3。
- 根目录 README、依赖清单、忽略规则和桌面 CI。

`Legacy/` 保持原样且不加入 Git。`local-assets/` 保存从根目录和 PC 包根目录移出的原始/重复音频，同样不加入 Git。PC 歌曲目录的音频和 WAV 缓存仍在原歌曲目录中，仅改用 ASCII 路径；这些音频和缓存也被忽略。没有删除历史版本或录音。

## 路径迁移

| 原位置 | 当前位置 |
| --- | --- |
| `Rhythm_Hold_v4.1_Single_Chart/` | `projects/pc-integrated/` |
| `1354Labdev_component02/` | `projects/standalone/` |
| `Rhythm_Chart_Studio_v1.3_audio_fix/` | `tools/chart-studio/` |
| 根目录 `*.aac` | `local-assets/original-audio/` |
| PC 包根目录重复的 `*.aac` | `local-assets/duplicates/pc-integrated/` |
| PC `songs/Tout dépend de toi/` | `projects/pc-integrated/songs/tout-depend-de-toi/` |
| PC 两首歌的 AAC 文件名 | 各歌曲目录内 `audio.aac`，`song.json` 已同步 |

## 发布前需要确定

- **代码许可证**：当前没有擅自添加 MIT 等许可证；由代码权利人确定后添加 `LICENSE`。
- **音乐素材**：PC 录音已排除；独立版仍包含用户提供的 MEGALOVANIA `source.mid` 及其生成的内嵌旋律。当前文件未记录具体来源或授权，需补充来源和允许再分发的依据，或替换成已获授权的 MIDI 并重新生成谱面及设备文件。只忽略 MIDI 不会移除设备文件里的旋律。
- **硬件验收**：两版都需实际检查输入、显示、暂停恢复和计分；PC 版需验证串口及音频同步，独立版需验证 P12 声音。

## 本地检查

从仓库根目录运行：

```sh
git rev-parse --show-toplevel
git status --short
git ls-files --others --exclude-standard
python -m unittest discover -s projects/standalone/src/tests -v
python projects/standalone/src/tools/build_song.py
```

第一条应输出本项目目录 `1354Labdev`，而非用户主目录。该目录原先没有独立的 Git 元数据，误继承了父目录仓库；本次建立本项目自己的 Git 仓库，未继承父目录的 remote。

`.github/workflows/checks.yml` 在 push 和 pull request 时，使用 Python 3.10 和 3.13 检查两版 Python 语法、独立版测试及重新构建。生成文件的逐字节一致性以 Python 3.13 为基准，因为不同版本的 `ast.unparse` 会产生不同的括号格式；各版本构建器均检查生成代码的 AST 与源码一致。CI 不需要 PC 音频、pygame 或实体设备。

## 提交与上传

本次整理已于 2026-11-03 完成本地检查：保留原有 215 个文件；发布清单为 35 个文件、约 228 KB；新路径和不含本地素材的干净导出均通过 11 项独立版测试，重建结果逐字节一致。PC 版两首歌曲的描述和谱面可读取，本地音频路径匹配。两版 Python 语法和 README 内部文件链接检查通过，常见凭据模式扫描未发现匹配。首次 GitHub Actions 运行中，Python 3.10 和 3.13 均通过 11 项测试及构建；针对 3.10 的括号格式差异，文件快照检查改用 3.13 为基准。实体设备尚未验收。

目标仓库为 [Scottshrimp/1354labGP7](https://github.com/Scottshrimp/1354labGP7)，本地 `origin` 已配置到该地址，发布分支为 `main`。首次上传保留远端原有的初始化提交；后续修改可按以下命令检查并提交：

```sh
git add README.md .gitignore .gitattributes .github docs projects tools
git diff --cached --stat
git diff --cached --name-only
git commit -m "Describe the project changes"
git push -u origin main
```

暂存文件中不应出现 `Legacy/`、`local-assets/`、AAC、WAV、虚拟环境、凭据或缓存。
