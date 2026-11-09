# voxx v0.1 设计

> 状态：已拷问定稿（2026-10-30）。术语见 [GLOSSARY.md](../GLOSSARY.md)，关键决策见 [docs/adr/](adr/)，模型调研见 [research/tts-models-2026-10.md](research/tts-models-2026-10.md)。下一步：`/to-spec` → `/to-tickets`。

## 一句话

voxx 是**只给 agent 用**的本地语音 CLI 加一个 skill：agent 给它一份旁白（Narration），它把每个 Line 一次连续念完，交回每句一个音频文件和词级时间戳。主要用途是给 CueTake 录屏配音：先有口播，再按口播录屏，画面跟着声音走。

## 核心原则：确定的写死在 CLI，判断交给 agent

| 写死在 CLI（同样输入总得到同样结果） | 交给 agent（skill 指导） |
|---|---|
| 模型注册表、许可证、任务到 checkpoint 的映射 | 选模型、选音色、写 `style` |
| 合成、响度归一、静音裁剪、强制对齐、自检打分 | 看错字率决定要不要换 seed 重配 |
| 旁白文件格式、JSON 输出、退出码 | 下载前把大小和许可证告诉用户、等用户同意 |
| 不隐式下载、不在 Line 内拼接音频 | 克隆前提醒用户确认有权使用这段声音；发布时提醒声明 AI 生成 |
| | 句子之间停多久（在 CueTake 的 Scenario 里定） |

## 和 CueTake 的关系

```
agent 写旁白 ──► voxx narrate ──► 旁白文件（补全 audio + words）+ 每句 WAV
                                         │
                                         ▼
                         cuetake record --narration <文件>
```

两个工具只靠文件交接，不互相调用（[ADR 0001](adr/0001-narration-file-is-the-contract.md)）。旁白格式与 levyxdev/cuetake#7 一致，但由 voxx 自己定义，代码里不依赖 CueTake。

## 旁白文件

输入：

```json
{
  "language": "zh",
  "voice": "my-voice",
  "style": "语气轻松，语速稍慢",
  "lines": [
    { "id": "intro", "text": "这是一个新的发送流程。" },
    { "id": "send",  "text": "点一下发送就完成了。", "style": "语气兴奋" }
  ]
}
```

- `language`：BCP 47 标签（规范大小写，如 zh、yue、en-US），一份旁白一种语言，必须和 Model 登记的语言完全一致（ADR 0005）。能用哪些语言跟随念它的 Model（Qwen3-TTS 支持 zh、en、ja、ko、fr、de、it、pt、ru、es），voxx 不另设限制；Model 不念这种语言时退出码 4。
- `voice`、`style`、`seed` 在顶层设默认值，单个 Line 可以覆盖。`style` 是自然语言，直接作为 instruct 传给模型。不支持 `style` 的 Model（0.6B 快速档、Qwen3-TTS Base）照样念这个 Line，只在它的 `warnings` 里说明忽略了 `style`。
- 四个 Delivery Control 也是顶层默认、Line 覆盖：`emotion`（happy、sad、angry、fearful、disgusted、surprised、neutral）、`speed`（slow、medium、fast）、`pitch`、`volume`（都是 low、medium、high）。只有 Ming-3.0-tts 跟随它们：voxx 把取值翻成 Ming 的中文取值，和 Preset Voice 一起拼成 Ming 读的 caption（一段 JSON）；克隆时还要给它一个全零的说话人向量，否则短句常常只念出零点几秒的杂音。Ming 不跟随 `style`（带 Preset Voice 或参考录音时音色还在，但 `style` 没有效果，levyxdev/voxx#33 实测），所以忽略并警告。其他 Model 照样念这个 Line，在 `warnings` 里用 `controls_ignored` 说明忽略了哪些。Line 最后仍规范化到 -18 LUFS，所以 `volume` 改变不了响度。实测（levyxdev/voxx#33）情绪最明显；语速只差 5% 到 20%，和情绪一起用时更小；音高只在中文里有一点；音量测不出差别。
- 没写 `voice` 时，用 Model 里第一个以这种语言为母语的音色（中文 vivian、英文 ryan），没有就用它的第一个音色。
- 没写 `seed` 时由 voxx 随机生成。每个 Line 合成前都重新设 seed，所以同一个 Model、音色、`style`、文字和 seed 在同一台机器上念出逐字节相同的 WAV（真实模型测试验证过），也和 Line 的先后无关。输出的旁白文件原样当输入、带上同样的 `--model`，就能复现上一次（输入不读 Line 上的 `model`）。

输出在每个 Line 上补上：`audio`、`words`（`[{ text, start, end }]`，相对该 Line 音频起点；中文按字）、`model`、`voice`、`seed`、`sample_rate`、自检错字率、`warnings`。

## 命令

```
voxx narrate <narration.json> --out <dir> [--model <id>] [--line <id>...] [--voices-dir <dir>]   # 合成整份旁白；--model 选念它的 Model；--line 只重配指定 Line
voxx voice add <name> --ref <录音> [--ref-text <文字>] [--model <id>] [--voices-dir <dir>] [--overwrite]   # 存一个 Cloned Voice
voxx voice design --describe <描述>... --text <试读稿> --language <tag> --out <dir> [--takes <n>] [--model <id>]   # 按描述生成 Design Take，供用户试听挑选
voxx voice add <name> --from-design <dir> --take <n> [--model <id>] [--voices-dir <dir>] [--overwrite]   # 把选中的 Design Take 存成 Designed Voice
voxx voices [--model <id>] [--language <tag>] [--voices-dir <dir>]   # 列出 Preset Voice、Cloned Voice 和 Designed Voice
voxx models                                                   # 注册表（只含可商用模型）
voxx install <model>                                          # 唯一会下载的命令，连同 Model 的额外仓库
voxx doctor                                                   # 平台、已装模型、磁盘
voxx schema                                                   # 所有命令的参数和返回结构
```

不对外提供 `align`、`transcribe`、`batch`：它们都只是 `narrate` 的内部步骤。

## 一份旁白的处理流程

1. CLI 校验旁白文件、确认所需模型已安装，然后启动 worker。
2. worker 加载一次模型。
3. 逐个 Line：整句一次合成 → 首尾静音裁到 50 ms → 响度归一到 -18 LUFS，峰值超过 -1 dBFS 的瞬间用限幅器压下去（压完仍差 0.5 LU 以上时加警告）→ 强制对齐得到 `words`（失败则不带 `words`，只加警告）→ 传了 `--check` 时 ASR 听写回来算错字率（默认不做，[ADR 0008](adr/0008-the-self-check-is-opt-in.md)）→ 写单声道 WAV（保留模型原生采样率）。
4. worker 退出，CLI 写出补全的旁白文件，在 stdout 打印一个 JSON 结果。

## CLI 和 worker

agent 只运行 `voxx` 这个 CLI，永远看不到 worker。

- CLI 是轻的：解析参数、读注册表和旁白文件、管理音色、输出 JSON。它不 import mlx，所以 `models`、`schema` 这类命令立刻返回。
- 需要合成时，CLI 把 `python -m voxx.worker` 作为**子进程**启动，通过它的 stdin/stdout 收发 JSON-RPC 消息（「加载模型」「合成这一句」「对齐这一句」……），stderr 用来转发进度。
- 旁白念完，worker 退出，模型占用的内存随之释放。worker 崩溃（比如显存不够）时，CLI 仍然能给 agent 返回一个结构化的 JSON 错误。

JSON-RPC over stdio 和 MCP、LSP 用的是同一种传输方式，但这里它只是 voxx 内部两半之间的私有管道，不是给 agent 的接口。对 agent 的接口只有 CLI，和 CueTake 一样不做 MCP。决策见 [ADR 0002](adr/0002-synthesis-runs-in-a-worker-process.md)。

v0.1 的 worker 和 CLI 在同一个 Python 环境里。等第一个依赖冲突的引擎（比如 PyTorch 系的 CosyVoice 官方包）进来时，再给它单独建一个 venv，协议不变。

## 模型

只登记权重许可证允许商用的模型（[ADR 0003](adr/0003-models-are-installed-only-by-an-explicit-command.md)），全部用 mlx 8bit，通过 mlx-audio 运行：

| 用途 | 模型 |
|---|---|
| Preset Voice（默认） | Qwen3-TTS-12Hz-1.7B-CustomVoice；0.6B 为快速档 |
| Cloned Voice、Designed Voice（默认），设计音色 | VoxCPM2 |
| Cloned Voice（对比项） | Qwen3-TTS-12Hz-1.7B-Base |
| Preset Voice、Cloned Voice、设计音色、Delivery Control | Ming-3.0-tts-0.5B（levyxdev/voxx#33） |
| 设计音色（10 种语言） | Qwen3-TTS-12Hz-1.7B-VoiceDesign（levyxdev/voxx#36） |
| 强制对齐 | Qwen3-ForcedAligner-0.6B |
| 自检听写、补参考录音文字 | Qwen3-ASR-0.6B |

中文听感没有任何第三方评测，默认值等实际试听后再调整。理由和数据见调研报告。

## 音色

- Preset Voice 按名字选，来自模型自带的音色。`voxx voices` 列出每个音色的母语、上游给的一句描述和能念它的 Model，agent 据此让用户挑。Qwen3-TTS CustomVoice 的 9 个音色全部登记，1.7B 和 0.6B 共用；不指定 `--model` 时由默认的 1.7B 念。Ming-3.0-tts 的 241 个音色抄自上游 cookbook（commit `9332fb9`），`US_`、`UK_` 开头的 3 个是英文，其余是中文，带情绪后缀的变体各算一个；音色超过 20 个的 Model 在 `voxx voices` 默认输出里只有 `unlisted` 里的一行摘要（数量和列出全部的命令），`--model` 列出它的全部音色，`--language` 只留母语是这种语言的。
- Cloned Voice 先存再用：`voice add` 把参考录音规范化（单声道、24 kHz、-18 LUFS、首尾静音 50 ms）、补好文字（没给 `--ref-text` 时用 Qwen3-ASR 听写，这时它必须已安装），存成有名字的音色；旁白里用 `voice: "<名字>"` 引用。默认存在 `~/.voxx/voices/`，也可以用 `--voices-dir` 指向项目目录，`narrate` 和 `voices` 传同一个目录。`voice.json` 记下 `voice add --model` 选的克隆 Model（默认 VoxCPM2），`narrate` 默认用它念，`narrate --model` 可以换成另一个克隆 Model。VoxCPM2 跟随 `style`：有 `style` 的 Line 只拿参考录音定声音、`style` 作为 instruct，不再接着参考录音续写（续写会把 `style` 当正文念出来），所以可能没那么像；没 `style` 的 Line 照旧续写，克隆最像。Qwen3-TTS Base 不接受 instruct，忽略 `style` 并在 `warnings` 里说明。Ming-3.0-tts 也忽略 `style`，但跟随 Delivery Control。
- Designed Voice 分两步（[ADR 0007](adr/0007-designed-voice-is-fixed-by-a-chosen-take.md)）：`voice design` 按每个描述生成 `--takes` 个念同一段试读稿的 Design Take，写进 `--out` 的 take-<n>.wav 和 design.json，并像 Line 一样听写回来自检；用户挑中后，`voice add --from-design <dir> --take <n>` 把那个 Design Take 当参考录音、试读稿当文字存成音色，`voice.json` 记 `kind: "designed"` 和描述。之后它和 Cloned Voice 一样由克隆 Model 念，不限语言。描述只写特征，不指向真实人物，由 skill 约束（ADR 0004）。
- 代码不做授权校验，使用者对所克隆的声音负责，README 写免责声明（[ADR 0004](adr/0004-cloning-does-not-check-consent.md)）。不加水印。

## CLI 契约

- stdout 永远是一个 JSON 对象：`{"ok": true, "data": {...}}` 或 `{"ok": false, "error": {"code", "message", "hint", "details"}}`。
- stderr 输出 NDJSON 进度。没有彩色、表格和交互式提示。

| 退出码 | 含义 | agent 该做什么 |
|---|---|---|
| 0 | 成功 | — |
| 1 | 内部错误 | 报告 |
| 2 | 参数错误 | 改参数 |
| 3 | 模型未安装 | 把大小和许可证告诉用户，同意后 `voxx install` |
| 4 | 模型不支持该能力 | 换模型 |

## 存储

```
$VOXX_HOME（默认 ~/.voxx）
  models/            # 模型文件
  voices/<name>/     # voice.json（kind、来源、参考文字、念它的克隆 Model、听写它的 Model、创建时间；Designed Voice 另有描述、设计它的 Model、take 和 seed）+ reference.wav（规范化后的参考录音）
```

## 平台与分发

- v0.1 只支持 Apple Silicon Mac。
- Python 实现，发布为 PyPI 上的 `voxx`。skill 里一行启动脚本运行 `uvx voxx@<固定版本>`，skill 和 CLI 从同一个 tag 发布。
- 本项目 Apache-2.0；不分发任何权重，依赖的上游项目见 `NOTICE`。

## 待定 / 以后

- **发音处理**：模型念错产品名、缩写时怎么办。候选方案是发音词典加句内 `{原文|读法}` 标注，在合成前替换文字（整句仍一次念完），词级时间戳映射回原文。先试实际效果再决定。
- 数值语速、常驻服务模式、每个引擎独立 venv、Linux/CUDA、CosyVoice3。
