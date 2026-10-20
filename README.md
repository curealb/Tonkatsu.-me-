# Tonkatsu.(me)

**月村手毬眼中的炸猪排。外表冷静，后台的每一个进程，都在请求下一块。**

一个非官方 ASCII 角色概念 MV 原型。按 Mili《world.execute(me);》约 **3:31.9** 的时间结构编排，画面改写为手毬的炸猪排幻想：初始化 → 香气与酥脆 → 暂时克制 → 盘子被端走 → 食欲系统异常 → 咬下去 → 幸福 99%，再来一块。

当前版本 **0.1.0**：31 个连续分镜、15 类场景渲染器、四种角色表情占位、程序化炸猪排、可替换食物素材槽、终端播放、浏览器音频同步预览。不是只改标题的主题皮肤，也不是已经完成角色美术的成片。

> **项目仓库：[`curealb/Tonkatsu.-me-`](https://github.com/curealb/Tonkatsu.-me-)。**
> 当前为可运行原型；角色图仍为占位，音乐需自行提供。

## 立即运行

需要 **Python 3.10 或更高版本**。核心运行不需要 `pip install`。

### 浏览器预览：优先使用这一入口

```sh
python3 preview.py
```

Windows 可执行 `python preview.py`，也可双击 `preview.bat`。macOS 可双击 `预览.command`。

打开的页面支持无声分镜播放；点击 **载入原曲**，选择你本机的 MP3/WAV 等浏览器支持的音频。选择的音乐使用浏览器本地文件 URL，不上传给 Python 或任何第三方。也可预先将音频放到 `media/song.mp3`，服务会在本机提供该文件，支持拖动进度。

播放器读取实际 `audio.currentTime` 驱动画面，支持暂停、拖动进度、逐分镜跳转、音量、画面偏移和减弱动态。Python 渲染器与终端版是同一个；网页不是另写一套动画。服务只监听 `127.0.0.1`，不提供文件上传或任意目录访问。不要将它改成公网服务。

```sh
# 不自动打开浏览器，或更换端口
python3 preview.py --no-open --port 8766
# 指定本机音频（不写入仓库）
python3 preview.py --audio "/path/to/your/song.mp3"
```

**音源说明：仓库不包含音乐、整首歌词或原项目频谱。** 时间点按参考项目的版本编排，尚未使用你的实际音乐做逐帧校准。其他版本可能有片头、静音或剪辑差异。画面偏移的正值表示提前画面；偏移只能纠正固定延迟，不能补偿不同剪辑或变速。

### 真实终端

```sh
# 无声演示，不需要音频组件；先按空格开始
python3 player.py --demo
# 直接从第一口开始看
python3 player.py --demo --start 66.601 --autoplay
# 实际音乐：macOS / Linux，需本机已有 mpv
python3 player.py --audio media/song.mp3 --autoplay
# 任意平台可生成静态文本帧
python3 player.py --snapshot 180 --plain --width 120 --height 42
```

实时终端后端目前面向 **macOS/Linux**；Windows 使用浏览器预览或快照。终端音频通过 mpv JSON IPC 获取播放位置，不用 `sleep()` 假装音乐时钟。mpv 不在本仓库内，安装方式应按你的系统选择。没有 mpv 时，优先使用浏览器入口。

建议终端至少 100 列 × 36 行，最低 64 × 24。全屏后缩小字号更容易看到细节。默认目标 24 FPS；性能取决于终端、窗口大小和机器，不保证恒定帧率。

| 操作 | 浏览器 | 终端 |
|---|---|---|
| 播放／暂停 | 按钮 / 空格 | 空格 / Enter |
| 前后 5 秒 | 方向键 | 方向键 |
| 从头开始 | 重播 / R | R |
| 分镜跳转 | 右侧 31 段目录 | 1–5 跳转主要段落 |
| 减弱动态 | 勾选 / M | M |
| 画面偏移 | 数字输入框 | `[` / `]`，步进 0.1 秒 |
| 音量 | 音量滑块 | `+` / `-` |
| 退出 | 关闭页面，终端 Ctrl+C 停服务 | Q / Esc / Ctrl+C |

### 单文件离线分镜预览

```sh
python3 tools/export_preview.py
```

生成 `dist/tonkatsu-preview.html`，可直接用现代浏览器打开，无需服务器。它是 **100 × 36、6 FPS、预先采样并减弱动态** 的分镜预览，不等同于 24 FPS 实时版；支持本地选曲与按音频时间定位，不包含音乐。需要浏览器提供 `DecompressionStream`；不支持时请使用 `preview.py`。离线版不实时响应音频能量。

## 你需要画什么

详细需求见 [绘图需求](docs/ART_BRIEF.md)。第一批只需 **同一构图的四张手毬透明半身图**：冷静、嘴馋、咬下一口、满足。食物可继续使用程序化字符形状，不阻塞角色图迭代。

| 槽位 | 用途 | 原图建议 | 默认转换 |
|---|---|---|---|
| `temari_calm` | 表面冷静、试图否认 | 1024×1024 透明 PNG | 40 列，缩放到左侧角色区 |
| `temari_tempted` | 目光被食物吸引 | 同上，头身位置一致 | 同上 |
| `temari_bite` | 筷子送入口中／正在咬 | 同上 | 同上 |
| `temari_happy` | 闭眼咀嚼、放松满足 | 同上 | 同上 |
| `tonkatsu_hero` | 完整炸猪排 | 1536×1024 透明 PNG | 42 列 |
| `tonkatsu_slice` | 切面与断面 | 1536×1024 透明 PNG | 42 列 |

```sh
# 只有导入 PNG 才需要这个可选依赖
python3 -m pip install -r requirements-art.txt
python3 tools/import_art.py assets/source/temari_calm.png --slot temari_calm
# 轮廓图也可试 edges 或 silhouette；--invert 反转灰度
python3 tools/import_art.py assets/source/temari_happy.png --slot temari_happy --mode edges
```

导入会写入 `assets/ascii/<slot>.txt` 并把 `assets/manifest.json` 的该槽标记为 `ready`。重启预览服务即可。原始图片默认被 Git 忽略，ASCII 结果可提交。全部图像转换在本地执行；不使用在线图像服务。

## 工程结构

```text
player.py                  终端播放与快照入口
preview.py                 仅本机可访问的浏览器预览服务
web/                       网页控制界面，不重复实现场景
  app.js                   audio.currentTime → /api/frame → 字符画布
  index.html / style.css
tonkatsu/
  canvas.py                宽字符、裁剪、ANSI、JSON 样式行
  timeline.py              校验并查找数据化时间轴
  film.py                  场景、字幕栏和播放信息的组合
  scenes.py                15 类原创新场景；31 段通过参数复用
  primitives.py            面包糠、盘子、热气、字形等图元
  art.py                   占位素材与用户绘图转换结果
  clock.py                 明确标识为无声的预览时钟
  audio.py                 可选 mpv 真实音频时钟（macOS/Linux）
timeline.json              分镜时间、独白、表情、场景参数
assets/ascii/              6 个占位素材槽
assets/manifest.json       placeholder / ready 状态
docs/                      分镜、绘图、架构和验证说明
tools/                     图片转换、离线预览导出、GitHub 发布
tests/                     标准库 unittest 测试
```

角色名、歌曲名与参考项目的关系在 [来源与权利说明](NOTICE.md) 中记录。本项目独立编写渲染与播放代码，没有复制原项目的播放器、场景、字幕、频谱或打包资源。

## 测试与已知限制

```sh
python3 -m unittest discover -s tests -v
```

当前验证记录见 [VALIDATION.md](docs/VALIDATION.md)。无实际原曲时可以验证时间轴和定位，不等于验证了歌曲逐拍同步。当前头像是通用占位，并不能代替手毬正式立绘。极小窗口会裁减细节；低分辨率 ASCII 也无法保留精细五官、发丝或复杂服装纹样。

浏览器渲染经本地 HTTP 请求返回，存在请求和绘制延迟；画面跟随音频时间，但不是零延迟硬实时输出。音频能量只用于局部参数，不是复刻原项目的离线频谱。

## 获取与更新源码

```sh
git clone https://github.com/curealb/Tonkatsu.-me-.git
cd Tonkatsu.-me-
python3 preview.py
```

在已有克隆中运行 `git pull --ff-only` 获取更新。不要将原曲、个人凭据或未获授权的原始图片提交到公开仓库。

`tools/publish_github.py` 保留为另建全新仓库的可选工具，默认创建私有仓库。它会拒绝已经存在的仓库和 `origin`，**不是本仓库的更新工具**。

核心源代码采用 MIT 许可；音乐、角色设计和未来导入的第三方素材不因此获得额外许可。本项目为非官方同人创作。
