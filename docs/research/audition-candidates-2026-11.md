# 试听候选的许可证和上游核实（2026-11）

## 1. 范围

问题：[levyxdev/voxx#25](https://github.com/levyxdev/voxx/issues/25) 第 1 步。五个候选（Ming-3.0-tts-0.5B、Chatterbox Multilingual V3、MOSS-TTS-Nano-100M、Audio8-TTS-Realistic-0.6B、Qwen3-TTS-12Hz-1.7B-VoiceDesign）能不能按 ADR 0003 登记进注册表；mlx-audio 要不要升级。背景见 [tts-models-2026-10.md](tts-models-2026-10.md)，这里只写重新核实的结果和新发现。

核实日期：2026-11-06。方法：
- 许可证、HEAD sha、文件列表读自 HF API（`https://huggingface.co/api/models/<repo>` 和 `.../tree/main?recursive=true`）。大小是 tree API 里所有文件大小之和（LFS 文件取 `lfs.size`）。
- GitHub 许可证读自 `gh api repos/<owner>/<repo>` 的 `license.spdx_id`。
- mlx-audio 读自上游源码和 release notes。仓库已经改名为 [Neywa-Labs/mlx-audio](https://github.com/Neywa-Labs/mlx-audio)，旧地址 Blaizzy/mlx-audio 会重定向（commit `e083358`，2026-11-03）。
- 没有下载任何权重。Audio8 的 codec 比对只用 HTTP Range 读了两个 `codec.pth` 的 zip 中央目录和 `data.pkl`（共约 1.2 MB 元数据：张量名、每个张量的 CRC32 和字节数），没有读张量数据，也没有反序列化 pickle。

标注约定沿用上一份调研：**自报**、**第三方**、**未核实**。

---

## 2. 汇总

| 模型 | 权重许可证（原始 / mlx） | LICENSE 文件（原始 / mlx / GitHub） | voxx 会钉住的 mlx 仓库 · HEAD · 大小 | 能登记？ | 阻碍和注意 |
|---|---|---|---|---|---|
| Ming-3.0-tts-0.5B | MIT / MIT | 无 / 有（MIT）/ 有（MIT） | `mlx-community/Ming-3.0-tts-0.5B-8bit` · `d0d1da6f627e4b3f20cc2db6ba4aee86d45343ad` · 1,617,181,518 B（1.62 GB） | **能** | 修复 PR #1059 仍未合并；mlx 不提取 CAM++ |
| Chatterbox Multilingual V3 | MIT / MIT | 无 / 无 / 有（MIT） | `mlx-community/chatterbox-multilingual-v3` · `03565773edd72e949572557597af8063bb49a18a` · 2,713,107,406 B（2.71 GB）；加载时另拉 `mlx-community/S3TokenizerV2` · `e0c9886f0e1c35ae85b1f27277416fb19fc72bec` · 494,869,110 B | **能**，但要把 S3TokenizerV2 一起钉住安装 | S3TokenizerV2 仓库没写许可证（上游 CosyVoice2-0.5B 是 Apache-2.0）；mlx 版必须给参考音频；没有 Perth 水印 |
| MOSS-TTS-Nano-100M | Apache-2.0 / Apache-2.0 | 无 / 无 / 有（Apache-2.0） | `mlx-community/MOSS-TTS-Nano-100M` · `229a9c51bb0ffff6fd0dbe53b5bf0c441e438a79` · 285,462,910 B（0.29 GB）；加载时另拉 `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` · `6aa02b01e445cc585582cf0ba480bc3ea6c8dd68` · 87,976,790 B | **能**，但要把音频 tokenizer 一起钉住安装 | HF 卡上那句“不要再分发”是过时的，发布方已在 GitHub 确认权重是 Apache-2.0；没有 TTS 质量指标；mlx 版只能克隆 |
| Audio8-TTS-Realistic-0.6B（现名 Realistic-Air） | Apache-2.0 / Apache-2.0 | 有（Apache-2.0 + NOTICE）/ 无 / 有（Apache-2.0） | `mlx-community/Audio8-TTS-Realistic-0.6b-bf16` · `f2addfde1a6196399bf23330dfd66c47b2fe10ea` · 2,565,175,187 B（2.57 GB） | **不能** | 自带 codec 的 535 个张量里有 462 个和 Fish Audio S2 Pro 的 codec 逐字节相同，受 Fish 许可证约束（商用要另签协议）；另外要 mlx-audio 0.6.4 |
| Qwen3-TTS-12Hz-1.7B-VoiceDesign | Apache-2.0 / Apache-2.0 | 无 / 无 / 有（Apache-2.0） | `mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit` · `f90d617701d9f7f4ca499291e0b57f2b3c2fd2ee` · 3,080,140,867 B（3.08 GB） | **能** | 无新问题；mlx-audio 0.6.3 已支持 |

“LICENSE 文件”一列：原始仓库里五个只有 Audio8 带了 LICENSE 文件，其余只在 `cardData.license` 里声明。voxx 不再分发权重，只按用户命令从 HF 下载，所以缺 LICENSE 文件本身不算阻碍；以 `cardData.license` 加 GitHub LICENSE 为准，和注册表现有六个 Model 的做法一致。

---

## 3. 逐个模型

### 3.1 Ming-3.0-tts-0.5B

- **许可证**：原始仓库 [inclusionAI/Ming-3.0-tts-0.5B](https://huggingface.co/inclusionAI/Ming-3.0-tts-0.5B) 的 `cardData.license` 是 `mit`，HEAD `7247f4c94a5b2e987404ed28a5cfec41b1a4ca61`（2026-10-27，没变），3,004,401,795 B，**没有** LICENSE 文件，模型卡结尾链接到 GitHub 的 LICENSE。mlx 仓库 [mlx-community/Ming-3.0-tts-0.5B-8bit](https://huggingface.co/mlx-community/Ming-3.0-tts-0.5B-8bit) 是 `mit`，`base_model` 指向原始仓库，**带** LICENSE 文件（MIT，“Copyright (c) 2025 inclusionAI”）。代码 [inclusionAI/Ming-3.0-tts](https://github.com/inclusionAI/Ming-3.0-tts) 是 MIT。
- **卡上的其他限制**：“Usage Disclaimer”写着克隆和内置角色音色“provided for research and legitimate creative use”，不得未经同意冒充真人，可能被误认为真实录音时要标注是合成的。这是使用声明，不是许可证条款，没有“仅限研究”或水印要求。
- **IP 音色**：音色表里有康熙、唐僧、佩奇等，接入时不屏蔽（用户 2026-11-06 决定）。
- **mlx 仓库里的 CAM++**：8bit 仓库带了 `campplus.safetensors`（27,699,096 B），但 mlx-audio 的 [dense README](https://github.com/Neywa-Labs/mlx-audio/tree/main/mlx_audio/tts/models/dense) 仍写着“Automatic CAM++ speaker embedding extraction is not implemented”，只能手动传 `spk_emb=`。CAM++ 权重本身的许可证**未核实**。
- **上游修复**：见 §4.1，#1059 仍未合并。0.6.3 到 0.6.4 之间没有改 Ming 的代码（compare 里没有 `dense` 或 `bailingmm` 的改动）。
- **结论**：许可证没问题，**能登记**。质量风险（失控解码、尾部嗡声）留给试听判断。

### 3.2 Chatterbox Multilingual V3

- **许可证**：V3 没有单独的仓库，权重 `t3_mtl23ls_v3.safetensors` 和 `s3gen_v3.safetensors` 就在 [ResembleAI/chatterbox](https://huggingface.co/ResembleAI/chatterbox) 里，`cardData.license` 是 `mit`，HEAD `5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18`（2026-06-10），整个仓库 13,866,212,931 B（含 v1/v2/v3 各版本），**没有** LICENSE 文件。mlx 仓库 [mlx-community/chatterbox-multilingual-v3](https://huggingface.co/mlx-community/chatterbox-multilingual-v3) 是 `mit`，没有 LICENSE 文件，卡上写着用 mlx-audio 0.4.7 从 ResembleAI/chatterbox 转换。代码 [resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox) 是 MIT（“Copyright (c) 2025 Resemble AI”）。
- **加载时的第二个仓库**：mlx 卡写着“requires the S3Tokenizer weights from mlx-community/S3TokenizerV2, which will be downloaded automatically”。源码（[chatterbox.py](https://github.com/Neywa-Labs/mlx-audio/blob/v0.6.4/mlx_audio/tts/models/chatterbox/chatterbox.py) 第 586 行起）在加载时无条件 `snapshot_download("mlx-community/S3TokenizerV2")`，**不钉 revision**。[mlx-community/S3TokenizerV2](https://huggingface.co/mlx-community/S3TokenizerV2) 的 `cardData.license` 是**空的**，没有 LICENSE 文件，`base_model` 是 [FunAudioLLM/CosyVoice2-0.5B](https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B)（`apache-2.0`），卡上写着是 mlx-audio-plus 转换的。voxx 要登记它，就得在 `voxx install` 时一起钉住这个仓库，并且决定按上游 Apache-2.0 记它的许可证。
- **水印**：官方卡写着“Every audio file generated by Chatterbox includes … Perth … Watermarker”。这是官方包的行为，MIT 许可证没有要求加水印。mlx-audio 源码里搜不到 `perth`（GitHub code search 0 条），mlx 生成的音频没有水印。
- **内置音色**（上一份调研标为未核实）：官方 torch 包里 `generate(text)` 不给参考音频也能念，用的是仓库里的 `conds.pt`，只有这一个默认声音，没有具名音色表。mlx 仓库没有 `conds.safetensors`，源码在既没有 `ref_audio` 也没有 conds 时直接 `raise ValueError`，所以 **mlx 版只能克隆**。默认声音的性别**未核实**。
- **结论**：许可证没问题，**能登记**；前提是安装时把 S3TokenizerV2 一起钉住。

### 3.3 MOSS-TTS-Nano-100M

- **许可证**：[OpenMOSS-Team/MOSS-TTS-Nano-100M](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M) 的 `cardData.license` 是 `apache-2.0`，HEAD `44502f80dbf9743528fa921cc544d662c685ebec`，最后提交 2026-04-13，之后**没有任何变化**，237,808,621 B，仍然**没有** LICENSE 文件。卡上“License”一节仍然写着“If you are reading this before that file is published, please treat the repository as **not yet licensed for redistribution**”。mlx 仓库 [mlx-community/MOSS-TTS-Nano-100M](https://huggingface.co/mlx-community/MOSS-TTS-Nano-100M) 是 `apache-2.0`，没有 LICENSE 文件，README 是空的。
- **不一致的结论**：
  - GitHub [OpenMOSS/MOSS-TTS-Nano](https://github.com/OpenMOSS/MOSS-TTS-Nano) 的 README 里有**同一句话**，而 GitHub 的根目录 LICENSE（Apache-2.0）在仓库创建第二天就加上了（commit `c8cdc4e`，2026-04-11，“add lincense”）。HF 卡是从 GitHub README 复制过去的，这句话指的是 GitHub 的那个 LICENSE 文件，在 GitHub 上条件已经满足。
  - 发布方已经正面回答过：GitHub issue [#91 “Clarification on the license for MOSS-TTS-Nano model weights”](https://github.com/OpenMOSS/MOSS-TTS-Nano/issues/91) 问“Are the model weights released under the Apache License 2.0?”，仓库 COLLABORATOR alpacaking 在 2026-07-28 回复“Yes”，并指出 HF 元数据和 GitHub 都是 Apache-2.0，随后关闭为 completed。
  - 所以：**权重是 Apache-2.0，可以登记**。HF 卡上那句话是过时的模板文字。
- **加载时的第二个仓库**：mlx 仓库的 `config.json` 写着 `audio_tokenizer_pretrained_name_or_path: OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano`。源码（[moss_audio_tokenizer.py](https://github.com/Neywa-Labs/mlx-audio/blob/v0.6.4/mlx_audio/codec/models/moss_audio_tokenizer/moss_audio_tokenizer.py) 的 `_resolve_audio_tokenizer_dir`）在第一次克隆时 `snapshot_download` 这个仓库，**不钉 revision**。[OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano) 是 `apache-2.0`，HEAD `6aa02b01e445cc585582cf0ba480bc3ea6c8dd68`，按源码的 `allow_patterns` 算要下 87,976,790 B，没有 LICENSE 文件，卡上没有那句“not yet licensed”。voxx 要在安装时一起钉住它，并通过 `audio_tokenizer_source` 传本地路径。
- **内置音色**（上一份调研标为未核实）：只在 ONNX 仓库 [MOSS-TTS-Nano-100M-ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX) 的 `browser_poc_manifest.json` 里，共 18 个，是预先算好的参考音频码。英文女声有 Bella、Ava；英文男声有 Adam、Nathan，还有一个叫 **Trump**；日语 7 个女声名字是 Anon、Soyo、Mortis、Togawa 等，像是动画角色。这些都有肖像权和 IP 风险。**mlx 版不支持内置音色**：`voice_clone` 模式必须给 `ref_audio`，另一个 `continuation` 模式不指定声音。
- **结论**：许可证**能登记**；工程上要钉住第二个仓库。没有任何 TTS 质量指标，只能靠试听。

### 3.4 Audio8-TTS-Realistic-0.6B（现名 Audio8-TTS-Realistic-Air）

- **改名**：`Edge0/Audio8-TTS-Realistic-0.6b` 现在 307 重定向到 [Edge0/Audio8-TTS-Realistic-Air](https://huggingface.co/Edge0/Audio8-TTS-Realistic-Air)（2026-11-02 的提交“Align naming with Audio8-TTS-Realistic-Air”）。HEAD `23c305cc013fde378edb459f538317043c993a74`，2,565,567,307 B。mlx 卡说转换自 revision `925bbd4`，改名前后权重没变。
- **许可证**：原始仓库 `apache-2.0`，**带** LICENSE（Apache-2.0 全文）和 NOTICE（“The model architecture is inspired by the DualAR design used in Fish Audio S2 Pro.”），`base_model` 是 [Edge0/Audio8-TTS-Preview-0.6b](https://huggingface.co/Edge0/Audio8-TTS-Preview-0.6b)（也是 `apache-2.0`）。mlx 仓库 [mlx-community/Audio8-TTS-Realistic-0.6b-bf16](https://huggingface.co/mlx-community/Audio8-TTS-Realistic-0.6b-bf16) 是 `apache-2.0`，没有 LICENSE 文件。GitHub [Edge0-AI/Audio8_TTS](https://github.com/Edge0-AI/Audio8_TTS) 是 Apache-2.0。注意同系列的 0.1B 用的是自定义的 `audio8-community-license-v1.0`，不是 Apache。
- **语言模型部分不是从 Fish 派生的**：
  - 论文 [arXiv:2610.14776](https://arxiv.org/abs/2610.14776) §3.2：慢分支“based on a Qwen2.5 0.5B language model”。`config.json` 和这一致：宽 896、24 层、14 头、2 个 KV 头、FFN 4864、`attention_qkv_bias: true`，就是 Qwen2.5-0.5B 的形状。
  - Fish S2 Pro（[config.json](https://huggingface.co/fishaudio/s2-pro/blob/main/config.json)）是 `fish_qwen3_omni`，宽 2560、36 层，形状对不上，不可能从它初始化。
  - 论文 §4.1：SFT 数据是“cleaned Emilia and YODAS2 with a private collection”。
- **codec 是从 Fish 的 codec 派生的**（关键证据）：
  - 论文 §3.1 只说“A fixed audio tokenizer … Both the tokenizer and the decoder remain fixed throughout language-model training”，没说 codec 从哪来。
  - 结构：`modeling_arktts_codec.py` 的编码器（dim 64，步长 2/4/8/8，最后一级 4 层 transformer）、解码器（1536 通道，步长 8/8/4/2）、量化器（1 个 4096 语义码本 + 9 个 1024 残差码本，下采样 2×2，窗口 128）和 fish-speech 的 [`modded_dac_vq.yaml`](https://github.com/fishaudio/fish-speech/blob/main/fish_speech/configs/modded_dac_vq.yaml) 完全一样。只有 `post_module` 不同（Audio8 的 FFN 1216、8 个 KV 头；Fish 的是 3072、16 头）。
  - 权重：Audio8 的 `codec.pth`（1,349,857,559 B，sha256 `c310505a…`）和 [fishaudio/s2-pro](https://huggingface.co/fishaudio/s2-pro) 的 `codec.pth`（1,871,099,728 B，sha256 `74fc41c5…`，和 [fishaudio/drama-3](https://huggingface.co/fishaudio/drama-3) 的是同一个文件）整体不同。但按 zip 中央目录逐个比较张量：Audio8 的 535 个张量里有 **462 个的 CRC32 和字节数与 Fish 的完全相同**，覆盖 1,129,379,336 B，占 Audio8 codec 张量数据（1,349,715,464 B）的 84%。按模块分：编码器 156/156、解码器 119/119、`pre_module` 73/73、上下采样 44/44、语义和残差码本 70/70 全部相同；只有 `post_module` 的 73 个张量全部不同。Fish 那个 checkpoint 在 zip 里的目录名是 `modded_dac_msstftd_step_1380000`；Audio8 的是 `codec`。
  - tokenizer：`tokenizer.json`、`tokenizer_config.json`、`special_tokens_map.json` 三个文件的 git oid 和 fishaudio/s2-pro 的完全相同；`semantic_begin_id` 151678、`vocab_size` 155776 也和 S2 Pro 一致。
  - Preview-0.6b 的 `codec.pth` 和 Realistic-Air 的 sha256 相同，所以两代都一样。
  - 论文致谢里写着“The Fish Audio S2 implementations also underpin much of our training and inference code”。
- **Fish 许可证约束它吗：是**。
  - S2 Pro 仓库的 [LICENSE.md](https://huggingface.co/fishaudio/s2-pro/blob/main/LICENSE.md)（Fish Audio Research License）把“Derivative Work(s)”定义为包括“any modifications to a Model, and any other model created which is based on or derived from the Model”，并规定“Any use of the Fish Audio Materials or Derivative Works for a Commercial Purpose requires a separate written license agreement from Fish Audio”。
  - Fish 新的 [Community License v1.0](https://github.com/fishaudio/fish-speech/blob/main/LICENSE)（2026-10-13）明确把这个 codec 列为 Model，但只“solely for use with Fish Audio Drama 3 and its Derivative Works”，而且商用只限年营收低于 50 万美元，还要求显示“Built with Fish Audio”。
  - 两份协议下，Audio8 自带的 codec 都不是 Apache-2.0 能重新授权的东西。Edge0 的 NOTICE 只提了“architecture inspired”，没有声明 codec 权重来自 Fish。
- **其他**：
  - mlx-audio 早在 2026-07-30 就支持 Preview（commit `b734d1d`），上一份调研说“没有 mlx 支持”不准确。Realistic 要 0.6.4（[#1093](https://github.com/Neywa-Labs/mlx-audio/pull/1093)，2026-10-29 合并）。
  - 能力：克隆要参考音频加准确转写；不给参考音频时用“its own default voice”（[arktts README](https://github.com/Neywa-Labs/mlx-audio/tree/v0.6.4/mlx_audio/tts/models/arktts)），没有具名音色，没有 voice design。
  - 卡上的使用要求：“Obtain permission to clone a voice and disclose synthetic audio where appropriate.”
- **结论**：**不能登记**。阻碍是 codec 派生自 Fish S2 Pro 的 codec 权重，受 Fish 许可证约束，商用需要 Fish 另签协议。

### 3.5 Qwen3-TTS-12Hz-1.7B-VoiceDesign

- **许可证**：[Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign) 是 `apache-2.0`，HEAD `5ecdb67327fd37bb2e042aab12ff7391903235d3`（2026-01-29，没变），4,520,163,832 B，没有 LICENSE 文件。mlx 仓库 [mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit) 是 `apache-2.0`，没有 LICENSE 文件，卡上写着用 mlx-audio 0.3.0 转换。代码 [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) 是 Apache-2.0。模型卡没有许可证以外的限制文字。
- **mlx**：`config.json` 的 `tts_model_type` 是 `voice_design`，`generate()` 会转到 `generate_voice_design()`，把 `instruct` 当音色描述（[qwen3_tts.py](https://github.com/Neywa-Labs/mlx-audio/blob/v0.6.3/mlx_audio/tts/models/qwen3_tts/qwen3_tts.py) 第 1221 行），0.6.3 已经支持。
- **结论**：**能登记**。

---

## 4. mlx-audio

### 4.1 PR #1059（Ming 修复）

[#1059 “Ming-3.0: cap runaway decodes and cut the trailing hum”](https://github.com/Neywa-Labs/mlx-audio/pull/1059) 仍然是 **OPEN**，没有合并，不在任何 release 里，也不在 main 上。只有一个提交 `6de3388`，没有 review。最后一条评论是维护者 lucasnewman 在 2026-10-29 写的，他怀疑根因是 EOS 处理有 bug，希望不用启发式规则来修。之后没有其他合并的 PR 改 Ming 的代码（`bailingmm` 目录最后一次提交是 2026-10-25）。

### 4.2 最新版本和五个模型的支持

- PyPI 和 GitHub 最新都是 **0.6.4**（PyPI 上传于 2026-11-02，[release notes](https://github.com/Neywa-Labs/mlx-audio/releases/tag/v0.6.4)）。
- 0.6.3 和 0.6.4 的 `mlx_audio/tts/models` 都有 `dense`（Ming）、`chatterbox`（v2/v3）、`moss_tts_nano`、`arktts`（Audio8）、`qwen3_tts`（含 VoiceDesign）。区别只在 Audio8：Realistic 的支持（#1093）进的是 0.6.4。
- 所以四个能登记的候选**在 0.6.3 上都能跑**；唯一需要 0.6.4 的 Audio8 被许可证挡住了。

### 4.3 0.6.3 到 0.6.4 对 voxx 现有 Model 的影响

voxx 调用的 mlx-audio API 只有 `mlx_audio.tts.utils.load`、`mlx_audio.stt.utils.load`、各模型的 `generate()` 和 `mlx_audio.audio_io.read`（`src/voxx/engines/mlx_audio.py`、`src/voxx/audio.py`）。[v0.6.3…v0.6.4 的 compare](https://github.com/Neywa-Labs/mlx-audio/compare/v0.6.3...v0.6.4) 里和它们有关的改动：

- `qwen3_tts.py` +8 行（[#1096](https://github.com/Neywa-Labs/mlx-audio/pull/1096)）：只在 ICL **流式**生成时用参考码预热解码器。voxx 不用流式，没有影响。
- `mlx_audio/utils.py`：`apply_quantization` 多了一个 `model_load_quant_predicate` 钩子，加载时多跑 `replace_scaled_quantized_linears` 和 `prepare_modelopt_weights`（NVFP4 / ModelOpt 支持）。对 voxx 用的 mlx-community 8bit affine checkpoint 应该是空操作（读代码推断，**未实测**）。
- `voxcpm2`、`qwen3_asr`、`tts/utils.py`、`stt/utils.py`、`audio_io` 都没改。依赖列表完全相同（`mlx==0.32.4`、`transformers[chat-template]>=5.14.0` 等）。
- 没有发现破坏性变化。

0.6.4 之后 main 上还有一个和 voxx 直接相关的修复，**还没发版**：[#1117 “apply the speech-tokenizer decoder's sliding window”](https://github.com/Neywa-Labs/mlx-audio/pull/1117)（2026-11-03 合并）。PR 说 Qwen3-TTS 的 speech tokenizer 解码器忽略了 `sliding_window`（72 帧），超过 5.76 秒后看得比参考实现更远；修复后和 PyTorch 解码器的 relL2 从 0.25 降到 3e-6（**自报**）。这会改变 voxx 所有 Qwen3-TTS Model 念超过 5.76 秒的 Line 的输出。main 上还把 mlx 的依赖从 `==0.32.4` 放宽成了 `>=0.32.4`（#1128）。

### 4.4 建议

**现在留在 0.6.3，不为这次试听升级到 0.6.4。** 理由：四个能登记的候选 0.6.3 都支持；0.6.4 对 voxx 现有 Model 没有可见的行为变化；唯一需要 0.6.4 的 Audio8 不能登记。

**等下一个包含 #1117 的版本（应该是 0.6.5）发布后再升级**，升级时跑 `VOXX_TEST_REAL=1 uv run pytest tests/test_real_models.py`。如果试听要以 Qwen3-TTS 作基准，最好用修复后的版本重新生成基准样本，否则基准里长 Line 的音质会偏低。

---

## 5. 未核实

1. **Audio8 codec 的 `post_module`** 是重新训练的还是从 Fish 的微调来的。对结论没有影响，因为其余 84% 的张量和 Fish 的逐字节相同。
2. **mlx-community 的 Audio8 `codec.safetensors`** 是不是由同一个 codec 转换来的：只按大小（1,349,643,293 B）和 `base_model` 推断，没有逐张量比对。
3. **Emilia 数据集的许可证**：Audio8 的 SFT 用了 Emilia。[amphion/Emilia-Dataset](https://huggingface.co/datasets/amphion/Emilia-Dataset) 的 `cardData.license` 显示 `cc-by-4.0`，但 README 要登录才能看，原版 Emilia 部分是不是 NC **未核实**（OmniVoice 卡说受 Emilia 约束是 CC-BY-NC）。因为 codec 已经挡住了 Audio8，这一点不影响结论。
4. **mlx-community/S3TokenizerV2 的许可证**：仓库没写。按上游 CosyVoice2-0.5B 算是 Apache-2.0，但这是推断。
5. **Chatterbox 默认声音（`conds.pt`）** 的性别和风格。
6. **Ming mlx 仓库里 `campplus.safetensors`（CAM++）** 的许可证。
7. **0.6.4 的量化加载钩子**对 voxx 的 8bit checkpoint 是不是真的空操作：只读了代码。
8. **#1059 的走向**：维护者倾向于从 EOS 处理找根因，可能会换一个 PR 修。
