# voxx 设计草案

> 状态：草案（2026-10-24）。用作 `/grill-with-docs` 的输入，拷问后沉淀为 `GLOSSARY.md` + ADR，再 `/to-spec` → `/to-tickets` → `/implement`。

## 一句话

voxx 是一个**只给 agent 用**的本地语音 CLI + 一个 skill：CLI 提供确定性的原子能力（列模型、下载、内置音色、克隆、合成、对齐），skill 提供方法论（怎么选模型、怎么切句、怎么自检、什么时候问用户）。

## 核心原则：确定性写死，判断交给 agent

| 写死在 CLI（确定、可测试） | 交给 agent（靠 skill 指导） |
|---|---|
| 模型注册表：repo id、许可证、能力、语言、大小、采样率 | 选哪个模型、哪个尺寸 |
| “能否商用”的判定（基于注册表里核实过的许可证） | 文本怎么切段、怎么写 instruct/风格描述 |
| 下载前的同意门（consent gate） | 什么时候向用户请求下载同意、怎么解释 |
| 任务 → 具体 checkpoint 的映射（例：内置音色→CustomVoice，克隆→Base） | 合成质量好不好、要不要换 seed 重试 |
| 音色档案的存储格式、参考音频规范化 | 拼接、混音、响度（agent 自己调 ffmpeg） |
| JSON 输出、错误码、退出码 | 整体工作流编排 |

判断标准：**同样输入是否总该得到同样结果**。是 → CLI；否 → skill。

## 模型（v0.1 已核实）

| 族 | 许可证（权重+代码） | Mac/mlx-audio | 能力 |
|---|---|---|---|
| Qwen3-TTS 0.6B/1.7B | Apache-2.0 | ✅ 上游已支持 | 内置音色（CustomVoice，9 个）、3 秒克隆（Base）、音色设计（1.7B VoiceDesign）、情绪 instruct、10 语言 |
| VoxCPM2 2B | Apache-2.0 | ✅ 上游已支持（bf16/8bit/4bit） | 克隆、可控克隆、音色设计、48kHz、30 语言 |
| Fun-CosyVoice3 0.5B | Apache-2.0 | ⚠️ 上游 PR [Blaizzy/mlx-audio#861](https://github.com/Blaizzy/mlx-audio/pull/861) 未合并；只有 mlx-audio-plus 分叉支持 | 克隆、跨语种、instruct、9 语言 |
| Qwen3-ForcedAligner 0.6B（对齐） | Apache-2.0 | ✅ | 词/字级时间戳，11 语言，≤300 秒 |
| Qwen3-ASR 0.6B（转写参考音频） | Apache-2.0 | ✅ | 克隆时自动补 ref_text |

注意：
- **“可商用”只针对权重许可证**。克隆他人声音需要本人授权，这是使用方的责任（VoxCPM 官方在 [OpenBMB/VoxCPM#238](https://github.com/OpenBMB/VoxCPM/issues/238) 里也这么说）。voxx 在音色档案里记录来源和授权声明，skill 要求 agent 确认。
- 非商用模型（如 F5-TTS 的 CC-BY-NC 权重、Fish Speech 的 CC-BY-NC-SA）也可以进注册表，但 `voxx models` 默认隐藏，`--all` 才显示，并标 `commercial: false`。
- CosyVoice3 在 Mac 上的路线二选一（待 grill）：等 #861 合并；或先走 torch(MPS) worker。**不依赖 mlx-audio-plus 分叉**（维护者关系紧张，长期风险大）。
- 注册表里每条许可证都带 `source_url` + `verified_at`，CI 里跑脚本对比 HF 的 `cardData.license`，变了就报警。

## CLI 契约

### 输出
- stdout 永远是**一个 JSON 对象**：`{"ok": true, "data": {...}}` 或 `{"ok": false, "error": {"code", "message", "hint", "details"}}`。
- 进度事件写 stderr，NDJSON（下载进度、加载中）。
- 不做彩色、表格、交互式提示——没有人类用户。
- `voxx schema` 输出所有命令的参数和返回结构（JSON Schema），agent 用它自我发现，skill 不必复述每个参数。

### 退出码
| 码 | 含义 | agent 该做什么 |
|---|---|---|
| 0 | 成功 | — |
| 1 | 内部错误 | 报告 |
| 2 | 参数错误 | 改参数 |
| 3 | 需要用户同意 | **停下来问用户** |
| 4 | 模型未安装 | 走 `pull`（会触发 3） |
| 5 | 模型不支持该能力 | 换模型 |

### 命令
```
voxx doctor                       # 平台、后端(mlx/cuda/cpu)、磁盘、已装模型
voxx models [--all] [--installed] [--capability clone|design|builtin|align]
voxx pull <model> [--consent <token>]
voxx voices [--model <m>]         # 内置音色 + 用户音色档案
voxx voice clone <name> --ref a.wav [--ref-text ...] [--attest "本人授权/自有素材"]
voxx voice design <name> --describe "低沉的中年男声，语速偏慢" --model ...
voxx speak --model <m> --voice <v> (--text|--text-file|-) --out x.wav
           [--instruct ...] [--lang ...] [--seed N] [--align]
voxx align --audio x.wav --text ... [--lang ...] [--format json|srt|vtt]
voxx transcribe --audio x.wav
voxx batch jobs.jsonl             # 模型只加载一次，逐行输出结果
```

`speak` 返回：`path, duration_s, sample_rate, model, checkpoint, voice, seed, alignment?`。所有让结果可复现的东西都回传。

### 下载同意门
1. agent 调 `voxx pull qwen3-tts-1.7b`（或 `speak` 时发现未安装）。
2. CLI 不下载，退出码 3，返回 `{model, checkpoints, total_bytes, license, license_url, commercial, consent_token}`。
3. skill 规定：agent 必须把大小和许可证原样告诉用户，得到明确同意后才能 `voxx pull ... --consent <token>`。
4. token 绑定 `model + 文件清单哈希`，短期有效；清单变了 token 失效。
5. 人类可以设 `VOXX_ALLOW_DOWNLOAD=qwen3-tts-*,voxcpm2`（CI、已授权场景）。
6. **任何命令都不会隐式下载**，包括克隆时缺 ASR 模型——同样返回 3。

诚实地说：CLI 无法验证“真的有人类点头”，token 的作用是让绕过成为一个显式、可审计的动作，而不是默认行为。

### 音色设计 → 固化
音色设计的结果每次不同。`voice design` 先生成一段样本，再把样本当参考音频存成克隆档案，此后用克隆路径合成，音色稳定。这是写死的流程。

## 架构

```
voxx (轻量核心：CLI、注册表、同意门、音色库、JSON 契约；不依赖 torch/mlx)
  │  JSON-RPC over stdio
  ├─ worker: mlx    (mlx-audio；Qwen3-TTS / VoxCPM2 / 对齐 / ASR)
  ├─ worker: torch  (v0.2：CUDA/MPS，官方 qwen-tts / voxcpm / cosyvoice)
  └─ ...
```

- **核心与引擎分进程**：各模型官方包的依赖（transformers 版本等）互相冲突，CosyVoice 尤其重。每个 worker 有自己的 uv 管理的 venv（`~/.voxx/envs/<worker>`），`pull` 时连同 env 一起建，大小计入同意门。
- 核心不 import 任何重依赖，`voxx models` / `schema` 秒回。
- worker 协议从第一天就定好，`batch` 和未来的 `voxx serve --stdio`（常驻、给 CueTake 这类长期运行的 agent 用）都是同一协议，只是生命周期不同。
- 每个引擎一个 adapter，实现 `capabilities()`、`synthesize(req)`、`align(req)`；“任务→checkpoint”映射在核心注册表，不在 adapter。

### 存储
```
$VOXX_HOME (默认 ~/.voxx)
  models/          # HF 缓存
  envs/            # worker venv
  voices/<name>/   # voice.json（来源、授权声明、ref_text、创建模型）+ ref.wav（规范化为 24k/16k mono）
  consent.log      # 每次同意下载的记录
```
项目可以用 `VOXX_HOME` 或 `--voices-dir` 指向项目内目录，CueTake 这类工具可以把音色跟项目走。

## Skill（方法论，非参数手册）
`skills/voxx/SKILL.md`，随 CLI 发布，同时用 `npx skills add` 可装。内容：
- 先 `voxx doctor` + `voxx schema`，不要猜参数。
- 选型决策：中文/方言 → Qwen3-TTS；48kHz 或冷门语言 → VoxCPM2；需要稳定内置音色 → Qwen3 CustomVoice。
- 遇到退出码 3：怎么向用户说明（大小、许可证、用途）。
- 长文本：按句切、每段 ≤ N 秒，`batch` 合成。
- 自检回路：`speak --align` 或 `transcribe` 对比原文，偏差大就换 seed 重试，最多 K 次。
- 克隆前确认参考音频的授权；5–15 秒干净人声。

## 本项目许可证：Apache-2.0
- 上游三个模型和对齐/ASR 全是 Apache-2.0，风格一致；mlx-audio 是 MIT，兼容。
- 比 MIT 多了专利授权，语音合成领域有专利风险，这一条有价值。
- voxx 不分发任何权重，只从 HF 拉取，所以不受权重许可证传染；注册表和同意门负责把许可证展示给用户。
- 仓库放 `LICENSE` + `NOTICE`（注明依赖的上游项目）。

## 开发流程（Matt Pocock skills）
1. `git init`，装 skills：`claude plugin install mattpocock-skills@claude-plugins-official`
2. `/setup-matt-pocock-skills`：issue tracker 选 GitHub（或本地 markdown），生成 `docs/agents/`
3. `/grill-with-docs`：拿这份文档拷问，产出 `GLOSSARY.md`（model / checkpoint / voice / engine / worker / consent token 等术语）和 ADR（分进程架构、同意门、许可证）
4. `/to-spec` → `/to-tickets`：按 tracer bullet 切票
5. `/implement` 逐票走 `/tdd`，收尾 `/code-review`

建议的第一颗 tracer bullet：`voxx models` + `voxx pull`（同意门）+ `voxx speak` 用 Qwen3-TTS 0.6B CustomVoice 内置音色出一个 wav——贯通注册表、同意门、worker 协议、JSON 契约四层。

## 待拷问的问题
1. CosyVoice3 在 Mac 上：等上游 #861，还是 v0.1 就上 torch(MPS) worker？
2. 是否把 Linux/CUDA 放进 v0.1，还是 v0.1 只做 Mac？
3. consent token 的有效期和作用域（单模型？单次？）
4. `serve --stdio` 进 v0.1 吗？CueTake 的调用频率决定。
5. 注册表格式：TOML 文件 vs Python 数据类（后者类型安全，前者便于 agent/贡献者编辑）。
6. 包名：PyPI 上 `voxx` 是否可用，要先查。
