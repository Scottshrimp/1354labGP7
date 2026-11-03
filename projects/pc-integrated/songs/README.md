# PC 版歌曲素材

源码仓库包含歌曲描述和谱面，不包含录音或自动生成的 `cache.wav`。没有有效音频的歌曲不会出现在设备菜单中；两首歌都缺少音频时，PC 主机会报告 `No valid songs/*/song.json + audio files`。

当前预设路径（相对仓库根目录）：

| 曲目 | 自行放置的音频 | 谱面 |
| --- | --- | --- |
| ILLADELPH | `projects/pc-integrated/songs/illadelph/audio.aac` | 同目录 `chart.json` |
| TOUT DEPEND DE TOI | `projects/pc-integrated/songs/tout-depend-de-toi/audio.aac` | 同目录 `chart.json` |

请使用有权使用的对应录音。现有谱面针对原录音时间轴，替换为其他版本或不同歌曲时应重新检查时长和同步。

新增歌曲时创建 `songs/<ascii-song-id>/`，放入音频、`chart.json` 和 `song.json`：

```json
{
  "title": "MY SONG",
  "audio": "audio.aac",
  "duration_ms": 60000,
  "chart": "chart.json"
}
```

谱面包含 `duration_ms` 和 `notes`，每个音符使用整数毫秒 `time_ms` 与 `UP`、`RIGHT`、`DOWN`、`LEFT` 之一的 `direction`。可用编辑器生成。保持目录名和素材文件名为 ASCII，避免不同文件系统的 Unicode 规范化差异。

其他音频格式可修改 `song.json` 的 `audio` 路径，并交由 FFmpeg 解码。分享前检查新增素材是否需要补充忽略规则。
