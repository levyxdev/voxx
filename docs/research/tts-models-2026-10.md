# 开源权重 TTS 模型调研（2026-10）

## 1. 范围

问题：voxx v0.1（只跑在 Apple Silicon Mac 上，只给 agent 用，给 CueTake 的录屏演示配旁白）应该默认用哪个开源权重 TTS 模型、克隆用哪个、以后再加哪些；以及用什么做中英文词级强制对齐。硬性要求：权重许可证允许商用；简体中文和英文都达到可发布质量；支持用参考录音零样本克隆。加分项：内置音色；能用 instruct 文本或参数控制语速和情绪。

调研日期：2026-10-29。所有许可证读自 Hugging Face API 的 `cardData.license`（`curl -s https://huggingface.co/api/models/<repo>`）、模型卡正文、GitHub 仓库的 license 字段；mlx-audio 的支持情况读自上游源码，克隆于 commit `8c244a1`（2026-10-28，v0.6.3，[Blaizzy/mlx-audio](https://github.com/Blaizzy/mlx-audio)）。

标注约定：
- **自报**：项目方在自己的模型卡、README 或论文里报告的数字。
- **第三方**：别的项目或排行榜测的数字。注意：很多“第三方”表格互相抄数字（比如 FireRedTTS3 和 dots.tts 表里的 Qwen3-TTS 行和 VoxCPM 表里完全一样），不能算独立复现。
- **未核实**：没找到一手来源。

Seed-TTS-eval 的 CER/WER 衡量的是可懂度，SIM 衡量的是音色相似度。两者都不衡量自然度。可以拿来比自然度的只有两个竞技场，而两个都**只测英文**（见 §3.11）。

---

## 2. 对比表（通过或接近通过硬性要求的候选）

Seed-TTS-eval 的数字格式为 zh CER / en WER（%，越低越好），SIM 格式为 zh / en。没有特别说明的都是自报。

| 模型 | 权重许可证 / 代码许可证 | Seed zh CER / en WER | SIM zh / en | 克隆 | 内置音色 | 语速 / 情绪控制 | Mac 运行 | 大小 |
|---|---|---|---|---|---|---|---|---|
| **Qwen3-TTS-12Hz-1.7B**（Base / CustomVoice / VoiceDesign） | Apache-2.0 / Apache-2.0 | 0.77 / 1.24（Base，自报）；1.22 / 1.23（VoxCPM 测）；1.33 / 1.50（MOSS 测） | 自报的 Seed 表没给 SIM；77.0 / 71.7（VoxCPM 测） | Base：参考音频 + 转写（ICL），或只用参考音频（x-vector，质量会降） | CustomVoice：9 个（中文 5 个，英文 2 个，都是男声） | CustomVoice 和 VoiceDesign 支持 instruct；**没有语速参数** | mlx-audio 上游 ✅，有 bf16/4/5/6/8bit | 原始 4.5 GB；mlx 8bit 3.1 GB |
| **Qwen3-TTS-12Hz-0.6B**（Base / CustomVoice） | Apache-2.0 / Apache-2.0 | 0.92 / 1.32（自报）；1.23 / 1.68（MOSS 测） | 76.4 / 70.4（MOSS 测） | 同上 | 同上（9 个） | CustomVoice 支持 instruct | mlx-audio 上游 ✅，有 bf16/4/5/6/8bit | 原始 2.5 GB；mlx 8bit 2.0 GB |
| **VoxCPM2**（2B） | Apache-2.0 / Apache-2.0 | 0.97 / 1.84 | 79.5 / 75.3 | 只用参考音频；参考音频 + 转写效果最好；克隆时可以叠加 instruct | 无（只有 Voice Design） | instruct 文本（“(描述)正文”），能控制情绪和语速 | mlx-audio 上游 ✅，有 bf16/8bit/4bit；也支持 llama.cpp-omni GGUF 和 torch MPS | 原始 4.96 GB；mlx 8bit 3.23 GB |
| **Ming-3.0-tts-0.5B**（2026-10 新发布） | MIT / MIT | 0.80 / 1.58 | 75.8 / 69.1 | 参考音频 + 转写（`seed` 任务）；情绪和语速任务只要参考音频 | 中文 100 多个，英文 3 到 5 个（US_Emma、UK_George、UK_Charlotte 等） | **有显式参数**：语速（慢/中/快）、情绪 7 类、音高、音量；还支持自由 instruct 和 14 种副语言标签 | mlx-audio 上游 ✅（v0.6.0 起，2026-10-19 合并，还很新）；mlx 有 bf16/8bit | 原始 3.0 GB；mlx 8bit 1.62 GB |
| **Fun-CosyVoice3-0.5B-2512**（RL 版） | Apache-2.0 / Apache-2.0 | 0.81 / 1.68 | 77.4 / 69.5 | 参考音频 + 转写（zero_shot），或只用参考音频（cross_lingual） | 无 | instruct2 预设句式（快、慢、开心、伤心、生气、方言等） | ⚠️ 上游 mlx-audio **没有**，PR #861 仍未合并；只有 mlx-audio-plus 分叉支持 | 原始仓库 9.75 GB（含 base 和 RL 两份 LLM）；mlx 8bit 1.41 GB（分叉格式） |
| **FireRedTTS3-Base**（2026-08） | Apache-2.0 / Apache-2.0 | 1.01 / 1.64 | 80.9 / 77.2 | 参考音频 + 转写（可以为空） | 无（Instruct 模型有 Voice Design） | Instruct 模型支持编辑语速、音高、音量（0.5–2.0 倍） | ❌ mlx-audio 不支持；只有社区 GGUF | 每个 checkpoint 8.48 GB（fp32，约 2B，按文件大小推算） |
| **dots.tts-soar**（2B，2026-06） | Apache-2.0 / Apache-2.0 | 0.94 / 1.30 | 81.0 / 77.1 | 参考音频 + 转写 | 无 | 未见 | ❌ 上游 PR #844/#845 都已关闭；只有社区 mlx 转换 | 5.16 GB |
| **MOSS-TTS-Nano-100M** | Apache-2.0 / Apache-2.0 | 未发布 TTS 指标 | 未发布 | 只用参考音频 | 有（ONNX 版写着 “built-in voices”，名单未核实） | 未见 | mlx-audio 上游 ✅；ONNX 可以纯 CPU 跑 | 0.24 GB |
| **Chatterbox Multilingual V3**（0.5B） | MIT / MIT | 未发布 | 未发布 | 只用参考音频 | 未核实（官方示例都要求给参考音频） | `exaggeration` 控制情绪强度，`cfg_weight` 控制节奏 | mlx-audio 上游 ✅（v2/v3）；官方 torch 支持 `mps` | mlx v3 2.71 GB |

接近通过但有短板（详见 §3）：Audio8-TTS-Realistic-0.6B（Apache-2.0，TTS Arena 第一，但没有 mlx 支持，发布才两周）、MOSS-TTS v1.5 / Local-Transformer v1.5（Apache-2.0，4B 到 8B，太大）、GLM-TTS（MIT 权重，英文没有自报指标，也没有 mlx 支持）、Kokoro（Apache-2.0，**不能克隆**，中文音色全是 D 级）。

---

## 3. 逐个候选

### 3.1 Qwen3-TTS（0.6B / 1.7B；Base、CustomVoice、VoiceDesign）

- **许可证**：五个 checkpoint 的 `cardData.license` 都是 `apache-2.0`（[1.7B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)、[1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)、[1.7B-VoiceDesign](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign)、[0.6B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base)、[0.6B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice)）。代码仓库 [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) 也是 Apache-2.0。论文 arXiv:2601.15621。
- **客观指标**（[GitHub README 评测节](https://github.com/QwenLM/Qwen3-TTS)）：
  - Seed-TTS test-zh / test-en WER：12Hz-1.7B-Base 0.77 / 1.24，12Hz-0.6B-Base 0.92 / 1.32。**自报**，表里没有 SIM。
  - MiniMax 多语种测试集，12Hz-1.7B-Base：zh 0.928 / en 0.934，SIM 0.799 / 0.775；12Hz-0.6B-Base：zh 1.145 / en 0.836，SIM 0.811 / 0.829。**自报**。
  - 第三方：VoxCPM 表测 1.7B 为 zh 1.22 / en 1.23，SIM 77.0 / 71.7，test-hard 6.76（[VoxCPM README](https://github.com/OpenBMB/VoxCPM#-performance)）；MOSS 表测 1.7B 为 zh 1.33 / en 1.50，SIM 76.72 / 71.45，0.6B 为 1.23 / 1.68（[MOSS-TTS README](https://github.com/OpenMOSS/MOSS-TTS)）。三家对中文 CER 的数字差了将近一倍，说明评测设置影响很大。
  - InstructTTSEval-ZH（VoiceDesign）：APS 85.2 / DSD 81.1 / RP 65.1。**自报**。
- **主观指标**：Artificial Analysis Provider Voice 榜上的 “Qwen3 TTS”（2026-01）为 Elo 929±13，排第 88；“Qwen3 TTS Flash” 为 941。**第三方**。但这一行标的是 API 价格（$13.8/1M chars），没有 HF 链接，**未核实**测的是不是开源权重的 checkpoint。TTS Arena V2 没有收录。没找到 MOS/CMOS（**未核实**）。
- **克隆**：Base 模型需要 `ref_audio` + `ref_text`（ICL 模式）。设 `x_vector_only_mode=True` 时只用说话人向量，不需要转写，但官方 README 说“cloning quality may be reduced”。官方宣传为“3-second rapid voice clone”。mlx-audio 的实现里，同时给 `ref_audio` 和 `ref_text` 才走 ICL；只给 `ref_audio` 时走说话人向量路径（`qwen3_tts.py` 第 410 行附近，是读源码推断的）。Base 模型没有内置音色，传 `voice` 会报错。
- **内置音色**（CustomVoice，官方 README）：Vivian（中文，年轻女声）、Serena（中文，温柔女声）、Uncle_Fu（中文，低沉男声）、Dylan（北京话男声）、Eric（四川话男声）、Ryan（英文男声）、Aiden（美式英文男声）、Ono_Anna（日语女声）、Sohee（韩语女声）。**以英文为母语的音色只有两个，而且都是男声**；英文女声只能让中文女声讲英文，或者先用 VoiceDesign 设计再转成克隆。
- **语速和情绪**：CustomVoice 和 VoiceDesign 通过 `instruct` 自然语言控制，例如官方示例“用特别愤怒的语气说”。没有数值语速参数：mlx-audio 的 `speed` 参数注释写着“not directly supported yet”，README 写着“Sampling and voice/style instructions can still affect speaking rate”。VoiceDesign 只有 1.7B 版本。
- **Mac**：mlx-audio 上游有完整支持，包括 `generate_custom_voice` / `generate_voice_design`、批量生成和流式。mlx-community 上 Base、CustomVoice、VoiceDesign 都有 bf16 和 4/5/6/8bit 版本。mlx-audio README 给了一个 6bit 1.7B CustomVoice 的批量基准：batch 1 时 1.67 倍实时、首包 84.8 ms、内存 3.88 GB。**第三方**（mlx-audio 测），但**没写用的什么芯片**。官方 qwen-tts 包的示例全是 `cuda:0`，源码里没搜到 `mps`，所以 torch MPS **未核实**。社区有 GGUF（例如 ggml-org/Qwen3-TTS-12Hz-1.7B-Base-GGUF），能不能用、怎么用**未核实**。
- **大小**：1.7B CustomVoice 原始 4.52 GB，mlx 8bit 3.08 GB；0.6B CustomVoice mlx 8bit 1.97 GB（HF tree API）。
- **水印**：README 未提及。
- **维护**：GitHub 最后一次推送是 2026-03-17（“fix finetuning bug”），HF 权重最后一次更新是 2026-01-29。已经 7 个月没有代码更新。

### 3.2 VoxCPM2（2B）

- **许可证**：[openbmb/VoxCPM2](https://huggingface.co/openbmb/VoxCPM2) 的 `cardData.license` 是 `apache-2.0`，模型卡写着“free for commercial use”。代码 [OpenBMB/VoxCPM](https://github.com/OpenBMB/VoxCPM) 也是 Apache-2.0。
- **客观指标**（[GitHub README](https://github.com/OpenBMB/VoxCPM#-performance)，**自报**）：
  - Seed-TTS-eval：test-zh CER 0.97 / SIM 79.5，test-en WER 1.84 / SIM 75.3，test-hard 8.13 / 75.3。
  - CV3-eval：zh 3.65，en 5.00，hard-zh 8.55，hard-en 8.48。
  - MiniMax 多语种：zh 1.136 / en 2.289，SIM 82.5 / 85.4。
  - InstructTTSEval：ZH 的 APS / DSD / RP 为 85.2 / 71.5 / 60.8，EN 为 84.2 / 83.2 / 71.4。
  - 第三方：Ming-3.0 用 MiniMax 子集复测了德、西、法、韩、日，没有测中英（[Ming-3.0 模型卡](https://huggingface.co/inclusionAI/Ming-3.0-tts-0.5B)）。
- **主观指标**：Artificial Analysis 两个榜和 TTS Arena V2 都**没有收录**。没找到 MOS（**未核实**）。
- **克隆**：三种用法。① 只给 `reference_wav_path`（不需要转写）；② “Controllable Cloning”：参考音频加风格描述，控制情绪和语速；③ “Ultimate Cloning”：参考音频加准确转写做续写，相似度最高。参考音频采样率 16 kHz，输出 48 kHz（模型卡）。模型卡只说“short clip”，**没给参考音频的具体时长要求**。
- **内置音色**：没有。Voice Design 可以只用文字描述生成新音色，但模型卡提醒“results may vary between runs; generating 1–3 times is recommended”。
- **语速和情绪**：用 instruct 文本描述（性别、年龄、语气、情绪、语速）。mlx-audio 的实现是把它拼成 `({instruct}){text}`，克隆时也能叠加（读 `voxcpm2.py` 第 443 行确认）。
- **Mac**：
  - mlx-audio 上游支持，有 `mlx-community/VoxCPM2-bf16`（4.96 GB）、`-8bit`（3.23 GB）、`-4bit`（2.30 GB），见 [mlx-audio voxcpm2 README](https://github.com/Blaizzy/mlx-audio/tree/main/mlx_audio/tts/models/voxcpm2)。
  - 官方 `voxcpm` 包会自动选设备，顺序是 CUDA、MPS、CPU（`src/voxcpm/core.py`）。
  - llama.cpp-omni 有 GGUF，官方 README 写着“RTF ~1.76 (Q8_0) on Apple M4 Pro / Metal”。**自报**。注意 RTF 大于 1，比实时还慢。
  - RTX 4090 上 RTF 约 0.30（自报）。mlx 在 M 系列芯片上的 RTF **没有公开数据**。
- **大小**：2B，原始 4.96 GB。
- **水印**：README 未提及。
- **维护**：最新 release 是 v2.0.3（2026-05-11），最后一次推送是 2026-10-08，活跃。

### 3.3 Ming-3.0-tts-0.5B（蚂蚁 inclusionAI，2026-10，**新的强候选**）

- **许可证**：[inclusionAI/Ming-3.0-tts-0.5B](https://huggingface.co/inclusionAI/Ming-3.0-tts-0.5B) 的 `cardData.license` 是 `mit`，代码 [inclusionAI/Ming-3.0-tts](https://github.com/inclusionAI/Ming-3.0-tts) 也是 MIT。同系列的 MoE 版 [Ming-3.0-tts-tiny](https://huggingface.co/inclusionAI/Ming-3.0-tts-tiny)（总参数 7.9B，激活 1.3B）也是 MIT。
- **客观指标**（模型卡，**自报**；卡上说明“Each open-source model was evaluated using its recommended inference settings under a unified ASR-based WER/CER evaluation protocol”）：
  - Seed-TTS：zh 0.800% / SIM 0.758，en 1.584% / SIM 0.691。tiny 为 zh 0.820 / 0.781，en 1.666 / 0.728。
  - 基础属性控制：语速准确率 99.0%，音量 95.0%，音高 86.0%。
  - CV3 情绪控制：平均 72.33%。
  - InstructTTSEval-ZH（Voice Design）：平均 72.29%。
  - 方言：WSC-Eval-TTS-easy CER 2.27%。
  - 卡上的 “Limitations” 自己承认：“Speaker similarity is weaker than content accuracy”。
- **主观指标**（**第三方**，Artificial Analysis，2026-10-29 实测抓取）：
  - [Controlled Voice](https://artificialanalysis.ai/text-to-speech/leaderboard/controlled-voice)：Elo 1068±15，排第 16（置信区间 13–23）。
  - [Provider Voice](https://artificialanalysis.ai/text-to-speech/leaderboard/provider-voice)：Elo 1187±13，排第 23，开源权重模型里排第三，测了 3 个音色。
  - 这两项和 Ming 自己 README 引用的 1069 / 1188 基本一致。对比：Provider Voice 榜上 Kokoro 为 1062，Chatterbox 为 1024，“Qwen3 TTS” 为 929。
  - 两个榜都**只测英文**。AA 链接的是 0.5B 的 HF 页面，但实际测的是 0.5B 还是 tiny **未核实**。
- **克隆**：官方任务表里，`seed` / `multilingual` / `paralinguistic` 任务需要参考音频和转写；`basic`（语速、音高、音量）、`emotion`、`dialect` 任务需要参考音频，**不接受**转写。官方推荐加 `--use_spk_emb`（CAM++ 说话人向量）。参考音频时长**未说明**。mlx-audio 的限制（[dense README](https://github.com/Blaizzy/mlx-audio/tree/main/mlx_audio/tts/models/dense)）：“Automatic CAM++ speaker embedding extraction is not implemented. Cloning uses the supplied audio and transcript”，所以在 mlx 上克隆走的是和官方推荐不同的路径，相似度可能低于自报值（**未核实**）。
- **内置音色**（[voice catalog](https://github.com/inclusionAI/Ming-3.0-tts/blob/main/cookbooks/instruction_en.md#built-in-premium-voices)）：
  - 英文：`US_Emma`、`UK_George`、`UK_Charlotte`。mlx-audio README 另外列了 `US_James`、`US_Stella`。
  - 中文：100 多个，例如 灵小柔、灵楷、灵卓然（新闻和纪录片男声）、灵叙柔（新闻女声）；部分有情绪变体（`_高兴` / `_悲伤` 等）。
  - ⚠️ 音色表里还有影视角色和 IP 音色：`康熙王朝_康熙`、`西游记_唐僧`、`小猪佩奇_佩奇`、`蜡笔小新_野原美伢`、`悟空` 等。这类音色有肖像权和版权风险，voxx 如果接入，应该在注册表里**白名单**通用音色，不暴露 IP 音色。
- **语速和情绪**：控制项最全。显式参数有语速（慢速 / 中速 / 快速）、情绪（高兴、悲伤、愤怒、恐惧、厌恶、惊讶、中性）、音高和音量（低 / 中 / 高）、方言（川渝话、广粤话）；另外支持 FREEFORM 自由 instruct 和 14 种副语言标签（`[Laughter]`、`[Sigh]` 等）。在 mlx 里用 `ming3_instruction()` 生成 JSON caption。不同任务模式**不能任意组合**（官方原话：“Capabilities use separate task modes, not arbitrary combinations”）。
- **Mac**：
  - mlx-audio 上游从 v0.6.0 开始支持（PR #1048 于 2026-10-20 合并，#1047 于 2026-10-19 合并，之后又合并了 #1054、#1062、#1075 等修复）。
  - 还有一个修复 PR **没合并**：[#1059 “Ming-3.0: cap runaway decodes and cut the trailing hum”](https://github.com/Blaizzy/mlx-audio/pull/1059)。
  - mlx README 写着“On an M4 Pro it runs at about real time and peaks at about 4.4 GB”。**第三方**（mlx-audio 测）。
  - mlx 实现的其他限制：不做文本正则化（数字要写成文字）；freeform 和 voice design 一次最多约 30 秒；偶尔会出现长尾，需要换 seed 重试。
  - mlx-community 有 `Ming-3.0-tts-0.5B-bf16`（3.00 GB）和 `-8bit`（1.62 GB）。官方推理代码只在 NVIDIA H800/H20 上测过。
- **大小**：0.5B（Qwen2.5-0.5B 骨干加 DiT 头），原始 3.0 GB，输出 44.1 kHz。
- **水印**：未提及。
- **维护**：GitHub 仓库 2026-10-19 才创建，最后推送 2026-10-27；HF 权重最后更新 2026-10-27。非常新。

### 3.4 Fun-CosyVoice3-0.5B-2512

- **许可证**：[FunAudioLLM/Fun-CosyVoice3-0.5B-2512](https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512) 的 `cardData.license` 是 `apache-2.0`。代码仓库 FunAudioLLM/CosyVoice 现在会**重定向到 QwenAudio/CosyVoice**（GitHub API 返回 `QwenAudio/CosyVoice`），也是 Apache-2.0。论文 arXiv:2505.17589。
- **客观指标**（模型卡，**自报**）：Seed-TTS 上，0.5B-2512 为 zh 1.21 / SIM 78.0、en 2.24 / SIM 71.8、hard 6.71；RL 版为 zh 0.81 / SIM 77.4、en 1.68 / SIM 69.5、hard 5.44。CV3-eval 只有 1.5B（没开源）的数字。NVBench 和情绪数字见 Ming 卡（第三方）。
- **主观指标**：两个竞技场都没收录。
- **克隆**：`inference_zero_shot(text, prompt_text, prompt_wav)` 需要转写；`inference_cross_lingual(text, prompt_wav)` 不需要。mlx-audio-plus 的说明是：只给 `ref_audio` 是默认模式，加上 `ref_text` “Better quality”。
- **内置音色**：无。
- **语速和情绪**：`inference_instruct2` 加预设 instruct 句式（[`cosyvoice/utils/common.py`](https://github.com/FunAudioLLM/CosyVoice/blob/main/cosyvoice/utils/common.py)），包括“尽可能慢/快地语速”、开心、伤心、生气、大声、小声、17 种方言，还有 `[breath]` 等细粒度标签。
- **Mac**：
  - ⚠️ 上游 mlx-audio 没有 cosyvoice 模型目录。[PR #861](https://github.com/Blaizzy/mlx-audio/pull/861) 仍然是 OPEN（最后更新 2026-10-27）。
  - mlx-community 上的 `Fun-CosyVoice3-0.5B-2512-fp16/8bit/4bit` 是用 [mlx-audio-plus](https://github.com/DePasqualeOrg/mlx-audio-plus) 0.1.4 转的，模型卡写着 `library_name: mlx-audio-plus`，上游 mlx-audio 加载不了。
  - torch MPS **未核实**。社区有 GGUF（cstr/cosyvoice3-0.5b-2512-GGUF）。
- **大小**：0.5B。HF 仓库 9.75 GB，因为同时带了 `llm.pt` 和 `llm.rl.pt` 各 2.0 GB，还有 onnx/pt 两份 flow。
- **水印**：未提及。
- **维护**：GitHub 最后推送 2026-05-25，HF 最后更新 2026-02-03。

### 3.5 FireRedTTS3（小红书 FireRed，2026-08）

- **许可证**：[FireRedTeam/FireRedTTS3](https://huggingface.co/FireRedTeam/FireRedTTS3) 是 `apache-2.0`，[GitHub](https://github.com/FireRedTeam/FireRedTTS3) 也是 Apache-2.0。论文 arXiv:2608.17492。
- **客观指标**（README，**自报**）：Seed-TTS 上 Base 为 en 1.64 / 77.2、zh 1.01 / 80.9、hard 6.50 / 78.4，SIM 在列出的开源模型里最高。MiniMax 多语种：zh 0.91 / SIM 84.2，en 2.12 / SIM 86.8。
- **克隆**：`prompt_text` 可以留空。官方建议参考音频和目标语言一致。
- **语速和情绪**：Instruct 模型支持 Voice Design，也支持把已有音频的语速、音高、音量改成 0.5–2.0 倍（这是编辑，不是合成参数）。
- **Mac**：mlx-audio 没有对应模型目录，也没搜到 PR；只有社区 GGUF（cstr/fireredtts3-GGUF）。文本正则化默认用 wetext（只支持中英）；可以改用 LLM 正则化，但要配外部 API，比如 DeepSeek，voxx 不应该走这条路。
- **大小**：base 和 instruct 各 8.48 GB（config 写着 `dtype: float32`，所以约 2B，是推算的），另外 redae 3.78 GB，整个仓库 20.8 GB。
- **维护**：最后推送 2026-09-08。

### 3.6 dots.tts（小红书 rednote-hilab，现在挂在 dots-studio 名下，2026-06）

- **许可证**：[dots-studio/dots.tts-soar](https://huggingface.co/dots-studio/dots.tts-soar)、`-base`、`-mf` 都是 `apache-2.0`，[studio-dots-ai/dots.tts](https://github.com/studio-dots-ai/dots.tts) 也是 Apache-2.0。
- **客观指标**（模型卡，**自报**）：Seed-TTS 上 soar 为 en 1.30 / 77.1、zh 0.94 / 81.0，平均 SIM 79.2。MiniMax 24 种语言平均 SIM 83.9。
- **克隆**：参考音频加准确转写（续写式）。没看到内置音色，也没看到 instruct 控制。
- **Mac**：上游 mlx-audio 的 [#844](https://github.com/Blaizzy/mlx-audio/pull/844) 和 #845 都已关闭、没有合并；只有社区转换（smcleod/dots.tts-soar-mlx）。
- **大小**：2B（Qwen2.5-1.5B 骨干加 AR flow-matching 头），5.16 GB，输出 48 kHz。
- **维护**：GitHub 最后推送 2026-10-28，活跃。

### 3.7 MOSS-TTS-Nano-100M 和 MOSS-TTS v1.5

- **许可证**：[MOSS-TTS-Nano-100M](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M) 的 `cardData` 是 `apache-2.0`，[GitHub](https://github.com/OpenMOSS/MOSS-TTS-Nano) 也是 Apache-2.0。⚠️ 但 HF 模型卡正文还留着一句：“If you are reading this before that file is published, please treat the repository as not yet licensed for redistribution”，而且 HF 仓库里**没有 LICENSE 文件**（tree API 查过）。以 GitHub LICENSE 为准是 Apache-2.0，但这里存在不一致。
- **指标**：Nano **没有发布 TTS 指标**，只发布了 tokenizer 的重建指标。MOSS-TTS 1.0 自报 Seed-TTS：MossTTSDelay-8B 为 en 1.84 / 70.86、zh 1.37 / 76.98；MossTTSLocal-1.7B 为 en 1.93 / 73.28、zh 1.44 / 79.62。v1.5 没有给新的 Seed 数字。
- **克隆和音色**：Nano 以克隆模式为主，ONNX 版写着支持 “built-in voices”，名单**未核实**。MOSS-TTS 支持 token 级时长控制（`${token:N}`），对“把旁白塞进固定时长”的场景很有价值。
- **Mac**：Nano、MOSS-TTS 8B、Local-Transformer v1.5 都在 mlx-audio 上游（mlx-community 有 Local-Transformer-v1.5 的 4bit 2.62 GB 和 8bit）。Nano 有 ONNX 纯 CPU 版，README 写着“on a MacBook Air M4, we observed smooth inference with only 1 CPU core”，**自报**。
- **大小**：Nano 0.24 GB；MOSS-TTS v1.5 8B（17 GB）；Local-Transformer v1.5 4B（9.1 GB）。
- **维护**：最后推送 2026-09-06。

### 3.8 Chatterbox / Chatterbox Multilingual V3（Resemble AI）

- **许可证**：[ResembleAI/chatterbox](https://huggingface.co/ResembleAI/chatterbox) 是 `mit`，代码 [resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox) 也是 MIT。中文单语包 [ResembleAI/Chatterbox-Multilingual-zh-cmn](https://huggingface.co/ResembleAI/Chatterbox-Multilingual-zh-cmn) 也是 `mit`。
- **指标**：没有发布中文 CER 或任何 Seed-TTS 数字（**未核实**）。主观指标（**第三方**）：Artificial Analysis Controlled Voice Elo 935±14，Provider Voice 1024±11（标的是 2025-05 的原版 Chatterbox）；TTS Arena V2 1467±20。都只测英文。
- **克隆**：只用参考音频即可。Multilingual V3 支持 23 种语言，包括 zh。
- **控制**：`exaggeration`（情绪强度）、`cfg_weight`。Turbo 版有副语言标签，但只支持英文。
- **Mac**：mlx-audio 上游支持 v2 和 v3（`mlx-community/chatterbox-multilingual-v3`，2.71 GB）。官方 torch 示例写着 `device = "cuda"  # or "cpu" / "mps"`。
- **水印**：官方包内置 [Perth](https://github.com/resemble-ai/perth) 水印。mlx-audio 源码里**没搜到** perth 或 watermark 的引用，所以走 mlx 生成的音频大概率没有水印（读源码推断）。
- **维护**：最后推送 2026-07-21。
- **结论**：许可证和 Mac 支持都没问题，但中文质量没有任何公开数据，必须先试听。

### 3.9 Audio8-TTS-Realistic-0.6B（Edge0，2026-10-14，新）

- **许可证**：[Edge0/Audio8-TTS-Realistic-0.6b](https://huggingface.co/Edge0/Audio8-TTS-Realistic-0.6b) 是 `apache-2.0`，[GitHub](https://github.com/Edge0-AI/Audio8_TTS) 也是 Apache-2.0。架构是“DualAR … inspired by Fish Audio S2 Pro”。训练数据来源，以及是否用了 Fish 的权重，**未核实**。如果是从 Fish 权重派生的，就会受 Fish 许可证约束。
- **指标**：Seed-TTS 上 en WER 1.464 / SIM 0.663，zh CER 1.029 / SIM 0.745，**自报**。[TTS Arena V2](https://tts-agi-tts-arena-v2.hf.space/leaderboard) 第 1 名，Elo 1668±52，但只有 215 票，标记为 preliminary，**第三方**。
- **Mac**：没有 mlx 支持；官方建议用 CUDA GPU。0.6B 加 44.1 kHz codec，仓库 2.56 GB。
- **结论**：值得关注，但太新，没有 Mac 运行时，来源也需要核实。

### 3.10 Kokoro-82M（不能克隆，只能当兜底）

- [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) 的权重和代码都是 Apache-2.0。**不支持零样本克隆**，所以不满足硬性要求。
- v1.0 的 [VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) 里 8 个中文音色全部是 D 级（自报）。[v1.1-zh](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh) 加了 100 个中文说话人，也是 Apache-2.0，但作者写明“not a strict upgrade”，丢了很多英文音色。
- Artificial Analysis Provider Voice Elo 1062±11，TTS Arena V2 1464±23，都是第三方、只测英文。
- mlx-audio 上游支持（bf16 0.39 GB），中文需要 `misaki[zh]`。

### 3.11 竞技场汇总（全部**第三方**，2026-10-29 抓取）

- **Artificial Analysis**（[controlled-voice](https://artificialanalysis.ai/text-to-speech/leaderboard/controlled-voice)：语言写着“English (US & UK)”；[provider-voice](https://artificialanalysis.ai/text-to-speech/leaderboard/provider-voice)）：
  - Provider Voice 榜开源权重模型的前五名是 Fish Audio Drama 3 Preview 1240、Breeze TTS 2 1228、**Ming-3.0-tts 1187**、Fish S2 Pro 1109、Step Audio EditX 1099。前两名和第四名都是非商用许可证。
  - 其余：Kokoro 1062、Higgs Audio V3 1039、Chatterbox 1024、VibeVoice 1.5B 955、“Qwen3 TTS” 929。
  - VoxCPM2 和 CosyVoice3 没有收录。
- **TTS Arena V2**（数据来自页面背后的 `https://tts-agi-tts-arena-v2.hf.space/api/leaderboard` JSON）：
  - 开源模型：Audio8-TTS-Realistic-0.6B 1668（preliminary）、Chatterbox 1467、Kokoro v1.0 1464、Magpie Multilingual 1392。
  - Qwen3-TTS、VoxCPM2、CosyVoice3、Ming-3.0 都**没有收录**。
- 结论：**没有任何第三方的中文自然度数据**。中文听感只能靠自己做试听测试。

---

## 4. 已排除

| 模型 | 排除原因 | 来源 |
|---|---|---|
| IndexTTS2 / IndexTTS-2.5 | 权重用的是 **bilibili Model Use License Agreement**（2.5 的 `cardData.license_name` = `bilibili-model-license`；2 的 HF 仓库里有 `LICENSE.txt`，`cardData` 为空）。代码 [index-tts/index-tts](https://github.com/index-tts/index-tts) 的 GitHub 许可证显示为 NOASSERTION。**许可证没变**。但要注意：这份协议本身是“royalty-free”的，只有月活超过 1 亿或年营收超过 10 亿元人民币才需要另外申请授权；另外它可以因违约被撤销，适用中国法律，并且禁止用产出去改进其他模型。所以它并不是“禁止商用”，而是一份非标准的自定义协议。按 voxx 只收标准宽松许可证的原则，继续排除。 | [IndexTTS-2 LICENSE.txt](https://huggingface.co/IndexTeam/IndexTTS-2/blob/main/LICENSE.txt)、[IndexTTS-2.5](https://huggingface.co/IndexTeam/IndexTTS-2.5) |
| IndexTTS-1.5 | ⚠️ HF 的 `cardData.license` 写的是 `apache-2.0`，但 GitHub 在 2025-09-09 的提交（#300）里“remove old license for v1.5”，换成了 bilibili 协议。两边矛盾，**未核实**以哪个为准，所以排除。 | [IndexTTS-1.5](https://huggingface.co/IndexTeam/IndexTTS-1.5) |
| F5-TTS | 权重 `cc-by-nc-4.0`（未变），代码 MIT | [SWivid/F5-TTS](https://huggingface.co/SWivid/F5-TTS) |
| Fish Audio S2 Pro | 权重是 `fish-audio-research-license`，商用需要另签书面协议（未变） | [fishaudio/s2-pro LICENSE.md](https://huggingface.co/fishaudio/s2-pro/blob/main/LICENSE.md) |
| Fish Audio Drama 3（35B MoE） | ⚠️ HF 仓库里的 `LICENSE` 文件今天（2026-10-29）显示为 **Fish Audio Community License**：年营收低于 50 万美元可以有限商用，不允许做托管服务。但 `cardData.license_name` 仍然写着 `fish-audio-research-license`，两者不一致。另外这个模型 81 GB，在 Mac 上也太大。 | [fishaudio/drama-3](https://huggingface.co/fishaudio/drama-3) |
| OmniVoice | `cardData.license` 为空；模型卡写着“The pre-trained model is licensed under the CC-BY-NC due to constraints from its training data (e.g., Emilia)”（未变）。代码是 Apache-2.0。 | [k2-fsa/OmniVoice](https://huggingface.co/k2-fsa/OmniVoice) |
| ZipVoice | 同上，因为用了 Emilia 数据，权重是 CC-BY-NC（未变） | [k2-fsa/ZipVoice](https://huggingface.co/k2-fsa/ZipVoice) |
| Higgs Audio v3（4B） | `boson-higgs-tts-3-research-and-non-commercial-license`。只给“digital creators”的创作内容开了一个例外，不是开源许可证。 | [bosonai/higgs-tts-3-4b](https://huggingface.co/bosonai/higgs-tts-3-4b) |
| Higgs Audio v2（3B） | Boson Higgs Audio 2 Community License：基于 Llama 3 协议改的，年活超过 10 万要另外授权，还要求署名。此外中文 test-hard CER 55.07（VoxCPM 测，第三方）。 | [higgs-audio-v2 LICENSE](https://huggingface.co/bosonai/higgs-audio-v2-generation-3B-base/blob/main/LICENSE) |
| Breeze TTS 2 | `breezeblue-research-and-non-commercial-license` | [BreezeBlue/Breeze-TTS-2](https://huggingface.co/BreezeBlue/Breeze-TTS-2) |
| Voxtral-4B-TTS（Mistral） | `cc-by-nc-4.0`，而且语言里没有 zh | [mistralai/Voxtral-4B-TTS-2603](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603) |
| Spark-TTS-0.5B | `cc-by-nc-sa-4.0` | [SparkAudio/Spark-TTS-0.5B](https://huggingface.co/SparkAudio/Spark-TTS-0.5B) |
| MegaTTS3 | 权重 Apache-2.0，但官方说“For security issues, we do not upload the parameters of WaveVAE encoder”，只能用预先提取好的 latent，**没法克隆任意声音** | [bytedance/MegaTTS3](https://github.com/bytedance/MegaTTS3) |
| VibeVoice-1.5B / 7B | 权重 MIT，但模型卡写着“limited to research purpose”和“We do not recommend using VibeVoice in commercial”；微软已经从仓库里删掉了 TTS 代码（2025-09-05），自带可听免责声明和水印 | [microsoft/VibeVoice-1.5B](https://huggingface.co/microsoft/VibeVoice-1.5B)、[GitHub](https://github.com/microsoft/VibeVoice) |
| Step-Audio-EditX（3B） | 代码是 Apache-2.0，但 HF 上的权重 `cardData.license` 为空，模型卡只写了“The code … is licensed under Apache 2.0”。**权重许可证未核实**。 | [stepfun-ai/Step-Audio-EditX](https://huggingface.co/stepfun-ai/Step-Audio-EditX) |
| GLM-TTS（1.5B） | 权重 MIT、代码 Apache-2.0，许可证没问题。但 README 写着“Primarily supports Chinese, while also supporting English mixed text”，英文没有自报指标（MOSS 测为 en 1.91，第三方）；没有 mlx 支持；2026-04 以后没有推送。中文自报 Seed zh 0.89（RL 版）。 | [zai-org/GLM-TTS](https://huggingface.co/zai-org/GLM-TTS)、arXiv:2512.14291 |
| SoulX-Podcast-1.7B | Apache-2.0，但主要做播客式多人对话；没有 mlx 支持；2025-12 以后没有更新 | [Soul-AILab/SoulX-Podcast-1.7B](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B) |
| MOSS-TTSD v1.0 | Apache-2.0，但它是 8B 的多人对话模型，不适合单人旁白 | [OpenMOSS-Team/MOSS-TTSD-v1.0](https://huggingface.co/OpenMOSS-Team/MOSS-TTSD-v1.0) |
| Kimi-Audio-7B | MIT，但它是 7B 的音频大模型，不是专门的克隆 TTS | [moonshotai/Kimi-Audio-7B-Instruct](https://huggingface.co/moonshotai/Kimi-Audio-7B-Instruct) |
| MiniMax | 没找到 MiniMax 发布的开源权重 TTS（HF 上只有 MiniMax 的视频和文本模型，以及第三方转的音乐模型 GGUF） | HF 搜索 |
| Magpie TTS Multilingual 357M（NVIDIA） | NVIDIA Open Model License，可以商用，语言含 zh；但只有 5 个预设音色，零样本克隆版（Magpie TTS Zeroshot）只通过 NIM 提供。开源版是否支持克隆**未核实**。 | [nvidia/magpie_tts_multilingual_357m](https://huggingface.co/nvidia/magpie_tts_multilingual_357m) |
| Kokoro | 不能克隆（见 §3.10） | — |

---

## 5. 词级强制对齐

voxx 需要为每条 Line 的音频返回 `{text, start, end}`。

### 5.1 Qwen3-ForcedAligner-0.6B（推荐）

- **许可证**：[Qwen/Qwen3-ForcedAligner-0.6B](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) 是 `apache-2.0`，代码 [QwenLM/Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR) 也是 Apache-2.0。论文 arXiv:2601.21337。
- **语言和限制**（模型卡，自报）：支持 11 种语言（中文、英文、粤语、法语、德语、意大利语、日语、韩语、葡萄牙语、俄语、西班牙语）。“timestamp prediction for arbitrary units within up to 5 minutes of speech”，即单段音频最长 5 分钟。非自回归推理。
- **精度**（模型卡里的 Forced Alignment Benchmarks，AAS ms，越低越好，**自报**）：

  | 测试集 | 语言 | Qwen3-ForcedAligner | NFA | WhisperX | Monotonic-Aligner |
  |---|---|---|---|---|---|
  | MFA-Labeled Raw | 中文 | 33.1 | 109.8 | – | 161.1 |
  | MFA-Labeled Raw | 英文 | 37.5 | 107.5 | 92.1 | – |
  | Concat-300s | 中文 | 36.5 | 235.0 | – | 1742.4 |
  | Concat-300s | 英文 | 58.6 | 226.7 | 227.2 | – |

  对比方的数字也是 Qwen 测的，没有独立复现。
- **粒度**：中文按**字**对齐，不是按词。mlx 实现里 `tokenize_chinese_mixed` 把每个 CJK 字切成一个 token，英文按空格分词，日文用 nagisa 分词。voxx 如果要给中文返回“词”级时间，需要自己分词（比如用 jieba）再合并字的时间戳。
- **时间粒度**：mlx 配置里有 `timestamp_segment_time: 80.0`，推测是 80 ms 一格，**未在官方文档核实**。
- **Mac**：mlx-audio 上游支持（`mlx_audio/stt/models/qwen3_asr/qwen3_forced_aligner.py`）。mlx-community 有 bf16（1.84 GB）、8bit（1.28 GB）、6/5/4bit 版本。mlx 实现一次处理整段音频，没有分块逻辑，这对 voxx 每条 Line 几秒到几十秒的长度没有影响。
- **配套**：给克隆参考音频自动补转写可以用 Qwen3-ASR-0.6B（Apache-2.0，mlx 8bit 1.01 GB）。

### 5.2 其他可商用的对齐方案

| 方案 | 代码许可证 | 权重许可证 | 中文 | 备注 |
|---|---|---|---|---|
| torchaudio `MMS_FA` | BSD-2 | ❌ **CC-BY-NC 4.0**（[torchaudio 文档](https://docs.pytorch.org/audio/stable/generated/torchaudio.pipelines.MMS_FA.html)） | 有（需要先转成罗马字） | **不能商用**。`facebook/mms-1b-all` 也是 cc-by-nc-4.0。 |
| WhisperX 对齐（wav2vec2 CTC） | BSD-2-Clause（[m-bain/whisperX](https://github.com/m-bain/whisperX)） | en 默认 `WAV2VEC2_ASR_BASE_960H`，对应 [facebook/wav2vec2-base-960h](https://huggingface.co/facebook/wav2vec2-base-960h)，apache-2.0；zh 默认 [jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn)，apache-2.0 | 有，按字对齐 | 来源：[`alignment.py`](https://github.com/m-bain/whisperX/blob/main/whisperx/alignment.py) 里的 `DEFAULT_ALIGN_MODELS_*`。voxx 已经有原文，只需要对齐这一步，不需要跑 Whisper ASR；但要用 torch（CPU 或 MPS），也没有 mlx 版。精度明显不如 Qwen3-ForcedAligner（上表，Qwen 自报）。 |
| NeMo Forced Aligner（NFA） | Apache-2.0（NeMo） | 用 CTC 模型。zh：[nvidia/stt_zh_citrinet_1024_gamma_0_25](https://huggingface.co/nvidia/stt_zh_citrinet_1024_gamma_0_25)，`cc-by-4.0`；en：例如 [nvidia/parakeet-ctc-0.6b](https://huggingface.co/nvidia/parakeet-ctc-0.6b)，`cc-by-4.0` | 有 | CC-BY-4.0 允许商用但要求署名。NeMo 依赖很重，在 Mac 上能不能装好**未核实**。 |
| mlx-audio 里的 ASR 自带时间戳（Parakeet、Whisper 等） | MIT | 看具体模型 | 看具体模型 | 这是识别出来的时间戳，不是对已知原文做强制对齐。可以当自检用，不适合当主要方案。 |

**建议**：v0.1 只用 Qwen3-ForcedAligner-0.6B（mlx 8bit）。以后如果要备选，选 WhisperX 那套 Apache-2.0 的 wav2vec2 模型，用 torch 跑。不要用 MMS_FA。

---

## 6. 建议

### v0.1 默认模型：Qwen3-TTS-12Hz CustomVoice（1.7B 8bit 为主，0.6B 8bit 为快速档）

理由：
- 权重和代码都是 Apache-2.0。
- mlx-audio 上游已经支持了 9 个月，而且是 mlx-audio README 第一个示例，checkpoint 档位（bf16、4/5/6/8bit）最全。
- 在 Mac 能跑的模型里，自报的 Seed zh CER 和 en WER 最好。
- 有 9 个内置音色，可以直接给 agent 当默认音色；支持 instruct 控制情绪。
- 同一族里还有 Base（克隆）和 VoiceDesign（设计音色再转成克隆），正好对应 DESIGN.md 里“任务映射到 checkpoint”的设计。

已知短板：
- 英文母语音色只有 Ryan 和 Aiden，都是男声。
- 没有数值语速参数，只能靠 instruct 控制语速。
- 代码从 2026-03 以后就没更新过。
- Artificial Analysis 上的 “Qwen3 TTS” Elo 只有 929。但那一行可能是 API 版，未核实。

**最强挑战者是 Ming-3.0-tts-0.5B**：
- MIT 许可证；第三方英文竞技场 Elo 1187，是所有可商用开源模型里最高的。
- 有显式的语速、情绪、音高参数，便于把旁白卡进视频节奏。
- 英文有女声（US_Emma、UK_Charlotte），中文音色超过 100 个；体积更小（8bit 1.62 GB）。

没把 Ming 定为 v0.1 默认，是因为它的 mlx 支持 10 天前才合并，还有一个修复 PR（#1059）没合并；mlx 里也没有实现 CAM++ 说话人向量和文本正则化。如果试听结果明显更好，可以把 Ming 也放进 v0.1 注册表，作为第二个内置音色模型。

### 克隆的首选：VoxCPM2（mlx 8bit）

理由：
- Apache-2.0。
- mlx-audio 上游支持，有 bf16/8bit/4bit。
- 在 Mac 能跑的模型里，自报 SIM 最高（zh 79.5 / en 75.3，高于 VoxCPM 自己测的 Qwen3-TTS-1.7B 的 77.0 / 71.7）。
- 只给参考音频也能克隆，不强制要转写；有转写时可以走“Ultimate Cloning”。
- 克隆时可以叠加 instruct 控制情绪和语速。输出 48 kHz。
- 维护活跃（2026-10 还有推送）。

备选：Qwen3-TTS-12Hz-1.7B-Base。好处是和默认模型同一族、少装一个模型；ICL 模式需要转写，可以用 Qwen3-ASR 自动补。

短板：VoxCPM2 的英文 WER 1.84，比 Qwen3 的 1.24 差（都是自报）；llama.cpp 在 M4 Pro 上的 RTF 是 1.76（比实时慢），mlx 下的速度要自己测。

### 以后再加

1. **Ming-3.0-tts-0.5B**：等 mlx 支持稳定下来（#1059 合并、CAM++ 实现），再按试听结果决定是否升为默认。接入时只白名单通用音色，排除康熙、唐僧、佩奇这类 IP 音色。
2. **Fun-CosyVoice3-0.5B-2512**：等 PR #861 合并进上游 mlx-audio，不依赖 mlx-audio-plus 分叉（和 DESIGN.md 的决定一致）。
3. **FireRedTTS3 / dots.tts**：Apache-2.0，自报 SIM 最高（80.9 到 81.0），但上游 mlx-audio 不支持，只能等，或者走 v0.2 的 torch worker。
4. **MOSS-TTS-Nano**：在没有 GPU、只想快速出声的场景当 CPU 兜底；MOSS-TTS 的 token 级时长控制以后做“按时长合成”时值得再看。
5. **Audio8-TTS-Realistic-0.6B**：TTS Arena 第一。等它有 Mac 运行时，并且确认训练和派生来源以后再看。
6. **Chatterbox Multilingual V3**：许可证和 mlx 支持都没问题，但中文没有任何指标，要试听后再决定。注意 mlx 版没有 Perth 水印。

### 试听测试还需要回答的问题

- 自然度：所有第三方竞技场都只测英文，**中文自然度完全没有外部数据**。要用同一批 CueTake 风格的中文和英文旁白（含中英混排、数字、产品名、代码术语），盲听比较 Qwen3-TTS 1.7B CustomVoice、Qwen3-TTS 0.6B CustomVoice、Ming-3.0-tts-0.5B（mlx）、VoxCPM2（mlx 8bit），有条件的话加上 CosyVoice3（分叉版）。
- 克隆：用同一段 5 到 15 秒的用户本人录音，比较 VoxCPM2（只给参考音频，以及参考音频加转写）、Qwen3-1.7B-Base（ICL 和 x-vector 两种模式）、Ming-3.0（mlx，没有 CAM++）的中英文相似度和稳定性。
- 量化损失：8bit 和 bf16 的听感差距（目前没有任何公开对比）。
- 速度：在目标 M 系列机器上测每个模型的 RTF 和峰值内存。目前只有 mlx-audio 对 Ming 的说法（M4 Pro 上约实时、4.4 GB）、Qwen3 的 6bit 批量数据（芯片未知），以及 VoxCPM2 在 llama.cpp 上的 RTF 1.76。
- 对齐自检：用 Qwen3-ForcedAligner 对合成结果做对齐，检查中文按字的时间戳合并成词以后是否可用；顺便统计每个模型的漏字和多字率。

---

## 7. 待解决和未核实

1. **Qwen3-TTS 在 Artificial Analysis 上的条目**（Elo 929）测的是开源 checkpoint 还是阿里云 API，未核实。
2. **Ming-3.0 在 AA 上测的是 0.5B 还是 tiny**，未核实（AA 链接的是 0.5B）。
3. **Ming-3.0 在 mlx 上的克隆相似度**：mlx 没有 CAM++ 说话人向量，相似度可能低于自报的 0.758 / 0.691，未测。
4. **MOSS-TTS-Nano 的 HF 模型卡**还写着“treat the repository as not yet licensed”，而且 HF 仓库没有 LICENSE 文件；GitHub 是 Apache-2.0。voxx 注册表应该以哪个为准，需要决定。
5. **IndexTTS-1.5**：HF 写 Apache-2.0，GitHub 已经换成 bilibili 协议，两者矛盾。
6. **Fish Audio Drama 3**：HF 上的 LICENSE 文件（今天显示为 Community License，有 50 万美元营收门槛）和 cardData（research license）不一致。对 voxx 影响不大，因为模型太大。
7. **Step-Audio-EditX 的权重许可证**：HF 上没写。
8. **Audio8-TTS 的训练数据和派生来源**（会不会受 Fish 许可证约束），未核实。
9. **各模型对参考音频时长的要求**：除了 Qwen3 写了“3 秒”、GLM-TTS 写了“3–10 秒”，其他模型都没给具体数字。voxx 的“5–15 秒干净人声”规范还需要实测确认。
10. **Qwen3-TTS 和 CosyVoice3 的官方 torch 包能不能在 MPS 上跑**，未核实。只有 VoxCPM 的源码明确支持 MPS。
11. **Qwen3-ForcedAligner 的 80 ms 时间粒度**，是从 mlx 配置推断的。
12. **水印**：Qwen3-TTS、VoxCPM2、CosyVoice3、Ming-3.0、FireRedTTS3、dots.tts、MOSS 的 README 都没提内置水印。Chatterbox 的 Perth 水印在 mlx 路径上不会加。voxx 是否要自己加水印（例如 AudioSeal，许可证需要另查），需要决定。
13. **MOSS、VoxCPM、Ming 等表里 Qwen3-TTS 的中文 CER 差很多**（0.77 到 1.33），说明评测设置差异大；不同团队之间的 Seed-TTS 数字不能直接比较。
