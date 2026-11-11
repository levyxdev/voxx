# Open-weight TTS model survey (2026-10)

## 1. Scope

Question: which open-weight TTS model should voxx v0.1 (Apple Silicon Macs only, for agents only, voicing narration for CueTake screen-recorded demos) use by default, which for cloning, and which to add later; and what to use for Chinese and English word-level forced alignment. Hard requirements: the weight license allows commercial use; both Simplified Chinese and English reach publishable quality; zero-shot cloning from a reference recording. Nice to have: built-in voices; speed and emotion controlled by instruct text or parameters.

Surveyed on 2026-10-29. All licenses were read from `cardData.license` in the Hugging Face API (`curl -s https://huggingface.co/api/models/<repo>`), the model card text and the GitHub repo's license field; mlx-audio support was read from upstream source, cloned at commit `8c244a1` (2026-10-28, v0.6.3, [Blaizzy/mlx-audio](https://github.com/Blaizzy/mlx-audio)).

Labels:
- **Self-reported**: numbers a project reports in its own model card, README or paper.
- **Third-party**: numbers measured by another project or leaderboard. Note: many "third-party" tables copy each other's numbers (the Qwen3-TTS rows in FireRedTTS3's and dots.tts's tables are identical to VoxCPM's, for example), so they do not count as independent reproduction.
- **Unverified**: no primary source found.

Seed-TTS-eval's CER/WER measures intelligibility, and SIM measures speaker similarity. Neither measures naturalness. The only things that compare naturalness are two arenas, and both **test English only** (see §3.11).

---

## 2. Comparison table (candidates that pass or nearly pass the hard requirements)

Seed-TTS-eval numbers are zh CER / en WER (%, lower is better); SIM is zh / en. Self-reported unless stated otherwise.

| Model | Weight license / code license | Seed zh CER / en WER | SIM zh / en | Cloning | Built-in voices | Speed / emotion control | Runs on Mac | Size |
|---|---|---|---|---|---|---|---|---|
| **Qwen3-TTS-12Hz-1.7B** (Base / CustomVoice / VoiceDesign) | Apache-2.0 / Apache-2.0 | 0.77 / 1.24 (Base, self-reported); 1.22 / 1.23 (measured by VoxCPM); 1.33 / 1.50 (measured by MOSS) | the self-reported Seed table gives no SIM; 77.0 / 71.7 (measured by VoxCPM) | Base: reference audio + transcript (ICL), or reference audio alone (x-vector, lower quality) | CustomVoice: 9 (5 Chinese, 2 English, both male) | CustomVoice and VoiceDesign take instruct; **no speed parameter** | mlx-audio upstream ✅, bf16/4/5/6/8bit | original 4.5 GB; mlx 8-bit 3.1 GB |
| **Qwen3-TTS-12Hz-0.6B** (Base / CustomVoice) | Apache-2.0 / Apache-2.0 | 0.92 / 1.32 (self-reported); 1.23 / 1.68 (measured by MOSS) | 76.4 / 70.4 (measured by MOSS) | as above | as above (9) | CustomVoice takes instruct | mlx-audio upstream ✅, bf16/4/5/6/8bit | original 2.5 GB; mlx 8-bit 2.0 GB |
| **VoxCPM2** (2B) | Apache-2.0 / Apache-2.0 | 0.97 / 1.84 | 79.5 / 75.3 | reference audio alone; reference audio + transcript works best; instruct can be layered on cloning | none (Voice Design only) | instruct text ("(description)text") controls emotion and speed | mlx-audio upstream ✅, bf16/8bit/4bit; also llama.cpp-omni GGUF and torch MPS | original 4.96 GB; mlx 8-bit 3.23 GB |
| **Ming-3.0-tts-0.5B** (new, 2026-10) | MIT / MIT | 0.80 / 1.58 | 75.8 / 69.1 | reference audio + transcript (`seed` task); emotion and speed tasks take reference audio only | 100+ Chinese, 3 to 5 English (US_Emma, UK_George, UK_Charlotte and others) | **explicit parameters**: speed (slow/medium/fast), 7 emotions, pitch, volume; also free instruct and 14 paralinguistic tags | mlx-audio upstream ✅ (since v0.6.0, merged 2026-10-19, still very new); mlx bf16/8bit | original 3.0 GB; mlx 8-bit 1.62 GB |
| **Fun-CosyVoice3-0.5B-2512** (RL version) | Apache-2.0 / Apache-2.0 | 0.81 / 1.68 | 77.4 / 69.5 | reference audio + transcript (zero_shot), or reference audio alone (cross_lingual) | none | instruct2 preset phrases (fast, slow, happy, sad, angry, dialects and so on) | ⚠️ **not** in upstream mlx-audio, PR #861 still unmerged; only the mlx-audio-plus fork supports it | original repo 9.75 GB (with both the base and RL LLMs); mlx 8-bit 1.41 GB (fork format) |
| **FireRedTTS3-Base** (2026-08) | Apache-2.0 / Apache-2.0 | 1.01 / 1.64 | 80.9 / 77.2 | reference audio + transcript (may be empty) | none (the Instruct model has Voice Design) | the Instruct model edits speed, pitch and volume (0.5–2.0×) | ❌ not in mlx-audio; community GGUF only | 8.48 GB per checkpoint (fp32, about 2B, estimated from file size) |
| **dots.tts-soar** (2B, 2026-06) | Apache-2.0 / Apache-2.0 | 0.94 / 1.30 | 81.0 / 77.1 | reference audio + transcript | none | none seen | ❌ upstream PRs #844/#845 both closed; community mlx conversion only | 5.16 GB |
| **MOSS-TTS-Nano-100M** | Apache-2.0 / Apache-2.0 | no TTS metrics published | not published | reference audio alone | yes (the ONNX version says "built-in voices"; list unverified) | none seen | mlx-audio upstream ✅; ONNX runs on CPU alone | 0.24 GB |
| **Chatterbox Multilingual V3** (0.5B) | MIT / MIT | not published | not published | reference audio alone | unverified (the official examples all require reference audio) | `exaggeration` controls emotion intensity, `cfg_weight` pacing | mlx-audio upstream ✅ (v2/v3); official torch supports `mps` | mlx v3 2.71 GB |

Near misses with weak spots (details in §3): Audio8-TTS-Realistic-0.6B (Apache-2.0, first on TTS Arena, but no mlx support and only two weeks old), MOSS-TTS v1.5 / Local-Transformer v1.5 (Apache-2.0, 4B to 8B, too large), GLM-TTS (MIT weights, no self-reported English metrics, no mlx support), Kokoro (Apache-2.0, **cannot clone**, Chinese voices all graded D).

---

## 3. Candidate by candidate

### 3.1 Qwen3-TTS (0.6B / 1.7B; Base, CustomVoice, VoiceDesign)

- **License**: all five checkpoints have `cardData.license` `apache-2.0` ([1.7B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base), [1.7B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice), [1.7B-VoiceDesign](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign), [0.6B-Base](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base), [0.6B-CustomVoice](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice)). The code repo [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) is Apache-2.0 too. Paper arXiv:2601.15621.
- **Objective metrics** ([GitHub README, evaluation section](https://github.com/QwenLM/Qwen3-TTS)):
  - Seed-TTS test-zh / test-en WER: 12Hz-1.7B-Base 0.77 / 1.24, 12Hz-0.6B-Base 0.92 / 1.32. **Self-reported**; the table has no SIM.
  - MiniMax multilingual test set, 12Hz-1.7B-Base: zh 0.928 / en 0.934, SIM 0.799 / 0.775; 12Hz-0.6B-Base: zh 1.145 / en 0.836, SIM 0.811 / 0.829. **Self-reported**.
  - Third-party: VoxCPM's table measures 1.7B at zh 1.22 / en 1.23, SIM 77.0 / 71.7, test-hard 6.76 ([VoxCPM README](https://github.com/OpenBMB/VoxCPM#-performance)); MOSS's table measures 1.7B at zh 1.33 / en 1.50, SIM 76.72 / 71.45, and 0.6B at 1.23 / 1.68 ([MOSS-TTS README](https://github.com/OpenMOSS/MOSS-TTS)). The three disagree on Chinese CER by nearly a factor of two, so the evaluation setup matters a lot.
  - InstructTTSEval-ZH (VoiceDesign): APS 85.2 / DSD 81.1 / RP 65.1. **Self-reported**.
- **Subjective metrics**: "Qwen3 TTS" on Artificial Analysis's Provider Voice board (2026-01) is at Elo 929±13, rank 88; "Qwen3 TTS Flash" at 941. **Third-party**. But that row lists an API price ($13.8/1M chars) and no HF link, so whether it measures the open-weight checkpoint is **unverified**. TTS Arena V2 does not list it. No MOS/CMOS found (**unverified**).
- **Cloning**: the Base model needs `ref_audio` + `ref_text` (ICL mode). With `x_vector_only_mode=True` it uses only the speaker embedding and needs no transcript, but the official README says "cloning quality may be reduced". It is advertised as "3-second rapid voice clone". In mlx-audio's implementation, ICL runs only when both `ref_audio` and `ref_text` are given; `ref_audio` alone takes the speaker-embedding path (around line 410 of `qwen3_tts.py`, inferred from the source). The Base model has no built-in voices, and passing `voice` raises an error.
- **Built-in voices** (CustomVoice, official README): Vivian (Chinese, young female), Serena (Chinese, gentle female), Uncle_Fu (Chinese, deep male), Dylan (Beijing-dialect male), Eric (Sichuan-dialect male), Ryan (English male), Aiden (American English male), Ono_Anna (Japanese female), Sohee (Korean female). **Only two voices are native English, and both are male**; an English female voice means a Chinese female voice speaking English, or designing one with VoiceDesign and turning it into a clone.
- **Speed and emotion**: CustomVoice and VoiceDesign are controlled by natural-language `instruct`, such as the official example "用特别愤怒的语气说" ("say it in a very angry tone"). No numeric speed parameter: mlx-audio's `speed` parameter is commented "not directly supported yet", and the README says "Sampling and voice/style instructions can still affect speaking rate". VoiceDesign exists only at 1.7B.
- **Mac**: full upstream mlx-audio support, including `generate_custom_voice` / `generate_voice_design`, batch generation and streaming. mlx-community has Base, CustomVoice and VoiceDesign in bf16 and 4/5/6/8bit. mlx-audio's README gives a batch benchmark for 6-bit 1.7B CustomVoice: 1.67× real time at batch 1, 84.8 ms to first chunk, 3.88 GB of memory. **Third-party** (measured by mlx-audio), but **the chip is not stated**. The official qwen-tts package's examples are all `cuda:0` and `mps` does not appear in its source, so torch MPS is **unverified**. There are community GGUFs (such as ggml-org/Qwen3-TTS-12Hz-1.7B-Base-GGUF); whether and how they work is **unverified**.
- **Size**: 1.7B CustomVoice original 4.52 GB, mlx 8-bit 3.08 GB; 0.6B CustomVoice mlx 8-bit 1.97 GB (HF tree API).
- **Watermark**: not mentioned in the README.
- **Maintenance**: last GitHub push 2026-03-17 ("fix finetuning bug"), last HF weight update 2026-01-29. No code updates for 7 months.

### 3.2 VoxCPM2 (2B)

- **License**: [openbmb/VoxCPM2](https://huggingface.co/openbmb/VoxCPM2) has `cardData.license` `apache-2.0`, and the model card says "free for commercial use". The code [OpenBMB/VoxCPM](https://github.com/OpenBMB/VoxCPM) is Apache-2.0 too.
- **Objective metrics** ([GitHub README](https://github.com/OpenBMB/VoxCPM#-performance), **self-reported**):
  - Seed-TTS-eval: test-zh CER 0.97 / SIM 79.5, test-en WER 1.84 / SIM 75.3, test-hard 8.13 / 75.3.
  - CV3-eval: zh 3.65, en 5.00, hard-zh 8.55, hard-en 8.48.
  - MiniMax multilingual: zh 1.136 / en 2.289, SIM 82.5 / 85.4.
  - InstructTTSEval: APS / DSD / RP of 85.2 / 71.5 / 60.8 for ZH and 84.2 / 83.2 / 71.4 for EN.
  - Third-party: Ming-3.0 re-measured German, Spanish, French, Korean and Japanese on a MiniMax subset, but not Chinese or English ([Ming-3.0 model card](https://huggingface.co/inclusionAI/Ming-3.0-tts-0.5B)).
- **Subjective metrics**: **not listed** on either Artificial Analysis board or TTS Arena V2. No MOS found (**unverified**).
- **Cloning**: three ways. ① `reference_wav_path` alone (no transcript needed); ② "Controllable Cloning": reference audio plus a style description, controlling emotion and speed; ③ "Ultimate Cloning": reference audio plus an accurate transcript, continued from, for the highest similarity. Reference audio is 16 kHz, output 48 kHz (model card). The model card says only "short clip" and **gives no concrete reference length**.
- **Built-in voices**: none. Voice Design can make a new voice from a text description alone, but the model card warns "results may vary between runs; generating 1–3 times is recommended".
- **Speed and emotion**: described in instruct text (gender, age, tone, emotion, speed). mlx-audio's implementation joins it as `({instruct}){text}`, which also works when cloning (confirmed at line 443 of `voxcpm2.py`).
- **Mac**:
  - Supported in upstream mlx-audio, with `mlx-community/VoxCPM2-bf16` (4.96 GB), `-8bit` (3.23 GB) and `-4bit` (2.30 GB); see [mlx-audio's voxcpm2 README](https://github.com/Blaizzy/mlx-audio/tree/main/mlx_audio/tts/models/voxcpm2).
  - The official `voxcpm` package picks a device automatically, in the order CUDA, MPS, CPU (`src/voxcpm/core.py`).
  - llama.cpp-omni has a GGUF, and the official README says "RTF ~1.76 (Q8_0) on Apple M4 Pro / Metal". **Self-reported**. Note that an RTF above 1 is slower than real time.
  - RTF about 0.30 on an RTX 4090 (self-reported). There is **no public data** on mlx RTF on M-series chips.
- **Size**: 2B, original 4.96 GB.
- **Watermark**: not mentioned in the README.
- **Maintenance**: latest release v2.0.3 (2026-05-11), last push 2026-10-08; active.

### 3.3 Ming-3.0-tts-0.5B (Ant Group's inclusionAI, 2026-10, **a strong new candidate**)

- **License**: [inclusionAI/Ming-3.0-tts-0.5B](https://huggingface.co/inclusionAI/Ming-3.0-tts-0.5B) has `cardData.license` `mit`, and the code [inclusionAI/Ming-3.0-tts](https://github.com/inclusionAI/Ming-3.0-tts) is MIT too. The MoE sibling [Ming-3.0-tts-tiny](https://huggingface.co/inclusionAI/Ming-3.0-tts-tiny) (7.9B total, 1.3B active) is MIT as well.
- **Objective metrics** (model card, **self-reported**; the card says "Each open-source model was evaluated using its recommended inference settings under a unified ASR-based WER/CER evaluation protocol"):
  - Seed-TTS: zh 0.800% / SIM 0.758, en 1.584% / SIM 0.691. tiny: zh 0.820 / 0.781, en 1.666 / 0.728.
  - Basic attribute control: speed accuracy 99.0%, volume 95.0%, pitch 86.0%.
  - CV3 emotion control: 72.33% on average.
  - InstructTTSEval-ZH (Voice Design): 72.29% on average.
  - Dialects: WSC-Eval-TTS-easy CER 2.27%.
  - The card's own "Limitations" admits: "Speaker similarity is weaker than content accuracy".
- **Subjective metrics** (**third-party**, Artificial Analysis, scraped 2026-10-29):
  - [Controlled Voice](https://artificialanalysis.ai/text-to-speech/leaderboard/controlled-voice): Elo 1068±15, rank 16 (confidence interval 13–23).
  - [Provider Voice](https://artificialanalysis.ai/text-to-speech/leaderboard/provider-voice): Elo 1187±13, rank 23, third among open-weight models, 3 voices tested.
  - Both roughly match the 1069 / 1188 Ming's own README cites. For comparison, on the Provider Voice board Kokoro is at 1062, Chatterbox at 1024, "Qwen3 TTS" at 929.
  - Both boards **test English only**. AA links the 0.5B HF page, but whether it actually tested 0.5B or tiny is **unverified**.
- **Cloning**: in the official task table, the `seed` / `multilingual` / `paralinguistic` tasks need reference audio and a transcript; the `basic` (speed, pitch, volume), `emotion` and `dialect` tasks need reference audio and **do not accept** a transcript. Upstream recommends `--use_spk_emb` (the CAM++ speaker embedding). The reference length is **not stated**. mlx-audio's limitation ([dense README](https://github.com/Blaizzy/mlx-audio/tree/main/mlx_audio/tts/models/dense)): "Automatic CAM++ speaker embedding extraction is not implemented. Cloning uses the supplied audio and transcript", so on mlx cloning takes a different path from the one upstream recommends, and similarity may fall below the self-reported numbers (**unverified**).
- **Built-in voices** ([voice catalog](https://github.com/inclusionAI/Ming-3.0-tts/blob/main/cookbooks/instruction_en.md#built-in-premium-voices)):
  - English: `US_Emma`, `UK_George`, `UK_Charlotte`. mlx-audio's README also lists `US_James` and `US_Stella`.
  - Chinese: 100+, such as 灵小柔, 灵楷, 灵卓然 (a male voice for news and documentaries) and 灵叙柔 (a female news voice); some have emotion variants (`_高兴` "happy" / `_悲伤` "sad" and so on).
  - ⚠️ The voice table also has film, TV and IP character voices: `康熙王朝_康熙` (Kangxi), `西游记_唐僧` (Tang Seng), `小猪佩奇_佩奇` (Peppa), `蜡笔小新_野原美伢` (Misae Nohara), `悟空` (Wukong) and others. These carry likeness and copyright risk; the user decided on 2026-11-06 not to block them on integration.
- **Speed and emotion**: the fullest set of controls. Explicit parameters for speed (慢速 / 中速 / 快速, slow / medium / fast), emotion (高兴, 悲伤, 愤怒, 恐惧, 厌恶, 惊讶, 中性: happy, sad, angry, fearful, disgusted, surprised, neutral), pitch and volume (低 / 中 / 高, low / medium / high) and dialect (Sichuan-Chongqing, Cantonese); plus FREEFORM free instruct and 14 paralinguistic tags (`[Laughter]`, `[Sigh]` and so on). In mlx, `ming3_instruction()` builds the JSON caption. Task modes **cannot be combined at will** (in upstream's words, "Capabilities use separate task modes, not arbitrary combinations").
- **Mac**:
  - Supported in upstream mlx-audio since v0.6.0 (PR #1048 merged 2026-10-20, #1047 merged 2026-10-19, followed by fixes such as #1054, #1062 and #1075).
  - One fix PR is **not merged**: [#1059 "Ming-3.0: cap runaway decodes and cut the trailing hum"](https://github.com/Blaizzy/mlx-audio/pull/1059).
  - The mlx README says "On an M4 Pro it runs at about real time and peaks at about 4.4 GB". **Third-party** (measured by mlx-audio).
  - Other limits of the mlx implementation: no text normalization (numbers must be written out as words); freeform and voice design top out around 30 seconds per call; an occasional long tail needs a retry with another seed.
  - mlx-community has `Ming-3.0-tts-0.5B-bf16` (3.00 GB) and `-8bit` (1.62 GB). The official inference code was tested only on NVIDIA H800/H20.
- **Size**: 0.5B (a Qwen2.5-0.5B backbone plus a DiT head), original 3.0 GB, 44.1 kHz output.
- **Watermark**: not mentioned.
- **Maintenance**: the GitHub repo was created only on 2026-10-19, last push 2026-10-27; HF weights last updated 2026-10-27. Very new.

### 3.4 Fun-CosyVoice3-0.5B-2512

- **License**: [FunAudioLLM/Fun-CosyVoice3-0.5B-2512](https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512) has `cardData.license` `apache-2.0`. The code repo FunAudioLLM/CosyVoice now **redirects to QwenAudio/CosyVoice** (the GitHub API returns `QwenAudio/CosyVoice`), also Apache-2.0. Paper arXiv:2505.17589.
- **Objective metrics** (model card, **self-reported**): on Seed-TTS, 0.5B-2512 is at zh 1.21 / SIM 78.0, en 2.24 / SIM 71.8, hard 6.71; the RL version at zh 0.81 / SIM 77.4, en 1.68 / SIM 69.5, hard 5.44. CV3-eval has numbers only for the 1.5B (not open). NVBench and emotion numbers are on the Ming card (third-party).
- **Subjective metrics**: neither arena lists it.
- **Cloning**: `inference_zero_shot(text, prompt_text, prompt_wav)` needs a transcript; `inference_cross_lingual(text, prompt_wav)` does not. mlx-audio-plus says `ref_audio` alone is the default mode, and adding `ref_text` gives "Better quality".
- **Built-in voices**: none.
- **Speed and emotion**: `inference_instruct2` with preset instruct phrases ([`cosyvoice/utils/common.py`](https://github.com/FunAudioLLM/CosyVoice/blob/main/cosyvoice/utils/common.py)), including "尽可能慢/快地语速" (as slow/fast as possible), happy, sad, angry, loud, quiet, 17 dialects, and fine-grained tags such as `[breath]`.
- **Mac**:
  - ⚠️ Upstream mlx-audio has no cosyvoice model directory. [PR #861](https://github.com/Blaizzy/mlx-audio/pull/861) is still OPEN (last updated 2026-10-27).
  - The `Fun-CosyVoice3-0.5B-2512-fp16/8bit/4bit` on mlx-community were converted with [mlx-audio-plus](https://github.com/DePasqualeOrg/mlx-audio-plus) 0.1.4; their model cards say `library_name: mlx-audio-plus`, and upstream mlx-audio cannot load them.
  - torch MPS is **unverified**. There is a community GGUF (cstr/cosyvoice3-0.5b-2512-GGUF).
- **Size**: 0.5B. The HF repo is 9.75 GB because it carries both `llm.pt` and `llm.rl.pt` at 2.0 GB each, plus onnx and pt copies of the flow.
- **Watermark**: not mentioned.
- **Maintenance**: last GitHub push 2026-05-25, last HF update 2026-02-03.

### 3.5 FireRedTTS3 (Xiaohongshu FireRed, 2026-08)

- **License**: [FireRedTeam/FireRedTTS3](https://huggingface.co/FireRedTeam/FireRedTTS3) is `apache-2.0`, and so is [GitHub](https://github.com/FireRedTeam/FireRedTTS3). Paper arXiv:2608.17492.
- **Objective metrics** (README, **self-reported**): on Seed-TTS, Base is at en 1.64 / 77.2, zh 1.01 / 80.9, hard 6.50 / 78.4; its SIM is the highest of the open models listed. MiniMax multilingual: zh 0.91 / SIM 84.2, en 2.12 / SIM 86.8.
- **Cloning**: `prompt_text` may be left empty. Upstream recommends reference audio in the target language.
- **Speed and emotion**: the Instruct model supports Voice Design, and also changing an existing recording's speed, pitch and volume by 0.5–2.0× (that is editing, not a synthesis parameter).
- **Mac**: mlx-audio has no model directory for it and no PR was found; only a community GGUF (cstr/fireredtts3-GGUF). Text normalization uses wetext by default (Chinese and English only); LLM normalization is an option, but it needs an external API such as DeepSeek, which voxx should not go near.
- **Size**: base and instruct are 8.48 GB each (config says `dtype: float32`, so about 2B, estimated), plus redae at 3.78 GB; 20.8 GB for the whole repo.
- **Maintenance**: last push 2026-09-08.

### 3.6 dots.tts (Xiaohongshu rednote-hilab, now under dots-studio, 2026-06)

- **License**: [dots-studio/dots.tts-soar](https://huggingface.co/dots-studio/dots.tts-soar), `-base` and `-mf` are all `apache-2.0`, and so is [studio-dots-ai/dots.tts](https://github.com/studio-dots-ai/dots.tts).
- **Objective metrics** (model card, **self-reported**): on Seed-TTS, soar is at en 1.30 / 77.1, zh 0.94 / 81.0, average SIM 79.2. Average SIM across MiniMax's 24 languages 83.9.
- **Cloning**: reference audio plus an accurate transcript (continuation). No built-in voices or instruct control seen.
- **Mac**: upstream mlx-audio's [#844](https://github.com/Blaizzy/mlx-audio/pull/844) and #845 were both closed unmerged; only a community conversion (smcleod/dots.tts-soar-mlx).
- **Size**: 2B (a Qwen2.5-1.5B backbone plus an AR flow-matching head), 5.16 GB, 48 kHz output.
- **Maintenance**: last GitHub push 2026-10-28; active.

### 3.7 MOSS-TTS-Nano-100M and MOSS-TTS v1.5

- **License**: [MOSS-TTS-Nano-100M](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M)'s `cardData` is `apache-2.0`, and so is [GitHub](https://github.com/OpenMOSS/MOSS-TTS-Nano). ⚠️ But the HF model card text still keeps one sentence: "If you are reading this before that file is published, please treat the repository as not yet licensed for redistribution", and the HF repo has **no LICENSE file** (checked with the tree API). By the GitHub LICENSE it is Apache-2.0, but the two disagree.
- **Metrics**: Nano has **no published TTS metrics**, only tokenizer reconstruction metrics. MOSS-TTS 1.0 self-reports on Seed-TTS: MossTTSDelay-8B en 1.84 / 70.86, zh 1.37 / 76.98; MossTTSLocal-1.7B en 1.93 / 73.28, zh 1.44 / 79.62. v1.5 gives no new Seed numbers.
- **Cloning and voices**: Nano is mainly clone mode; the ONNX version claims "built-in voices", list **unverified**. MOSS-TTS supports token-level duration control (`${token:N}`), valuable for "fit the narration into a fixed duration".
- **Mac**: Nano, MOSS-TTS 8B and Local-Transformer v1.5 are all in upstream mlx-audio (mlx-community has Local-Transformer-v1.5 in 4-bit at 2.62 GB and 8-bit). Nano has an ONNX CPU-only version, whose README says "on a MacBook Air M4, we observed smooth inference with only 1 CPU core", **self-reported**.
- **Size**: Nano 0.24 GB; MOSS-TTS v1.5 8B (17 GB); Local-Transformer v1.5 4B (9.1 GB).
- **Maintenance**: last push 2026-09-06.

### 3.8 Chatterbox / Chatterbox Multilingual V3 (Resemble AI)

- **License**: [ResembleAI/chatterbox](https://huggingface.co/ResembleAI/chatterbox) is `mit`, and the code [resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox) is MIT too. The Chinese-only pack [ResembleAI/Chatterbox-Multilingual-zh-cmn](https://huggingface.co/ResembleAI/Chatterbox-Multilingual-zh-cmn) is also `mit`.
- **Metrics**: no Chinese CER or any Seed-TTS numbers published (**unverified**). Subjective (**third-party**): Artificial Analysis Controlled Voice Elo 935±14, Provider Voice 1024±11 (listed as the original Chatterbox of 2025-05); TTS Arena V2 1467±20. All English only.
- **Cloning**: reference audio alone is enough. Multilingual V3 supports 23 languages, zh included.
- **Control**: `exaggeration` (emotion intensity), `cfg_weight`. The Turbo version has paralinguistic tags, but English only.
- **Mac**: upstream mlx-audio supports v2 and v3 (`mlx-community/chatterbox-multilingual-v3`, 2.71 GB). The official torch example says `device = "cuda"  # or "cpu" / "mps"`.
- **Watermark**: the official package embeds a [Perth](https://github.com/resemble-ai/perth) watermark. mlx-audio's source has **no** reference to perth or watermark, so audio generated through mlx most likely carries no watermark (inferred from the source).
- **Maintenance**: last push 2026-07-21.
- **Verdict**: license and Mac support are both fine, but there is no public data at all on its Chinese quality; it must be auditioned first.

### 3.9 Audio8-TTS-Realistic-0.6B (Edge0, 2026-10-14, new)

- **License**: [Edge0/Audio8-TTS-Realistic-0.6b](https://huggingface.co/Edge0/Audio8-TTS-Realistic-0.6b) is `apache-2.0`, and so is [GitHub](https://github.com/Edge0-AI/Audio8_TTS). The architecture is "DualAR … inspired by Fish Audio S2 Pro". Where the training data came from, and whether Fish's weights were used, is **unverified**. If it derives from Fish's weights, the Fish license binds it.
- **Metrics**: on Seed-TTS, en WER 1.464 / SIM 0.663, zh CER 1.029 / SIM 0.745, **self-reported**. First on [TTS Arena V2](https://tts-agi-tts-arena-v2.hf.space/leaderboard) at Elo 1668±52, but on only 215 votes, marked preliminary, **third-party**.
- **Mac**: no mlx support; upstream recommends a CUDA GPU. 0.6B plus a 44.1 kHz codec, 2.56 GB repo.
- **Verdict**: worth watching, but too new, with no Mac runtime, and its provenance needs checking.

### 3.10 Kokoro-82M (cannot clone; a fallback only)

- [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)'s weights and code are both Apache-2.0. It **does not support zero-shot cloning**, so it fails the hard requirements.
- In v1.0's [VOICES.md](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md) all 8 Chinese voices are graded D (self-reported). [v1.1-zh](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh) adds 100 Chinese speakers, also Apache-2.0, but the author writes that it is "not a strict upgrade" and it lost many English voices.
- Artificial Analysis Provider Voice Elo 1062±11, TTS Arena V2 1464±23, both third-party and English only.
- Supported in upstream mlx-audio (bf16 0.39 GB); Chinese needs `misaki[zh]`.

### 3.11 Arena summary (all **third-party**, scraped 2026-10-29)

- **Artificial Analysis** ([controlled-voice](https://artificialanalysis.ai/text-to-speech/leaderboard/controlled-voice): the language is stated as "English (US & UK)"; [provider-voice](https://artificialanalysis.ai/text-to-speech/leaderboard/provider-voice)):
  - The top five open-weight models on the Provider Voice board are Fish Audio Drama 3 Preview 1240, Breeze TTS 2 1228, **Ming-3.0-tts 1187**, Fish S2 Pro 1109 and Step Audio EditX 1099. The first, second and fourth are under non-commercial licenses.
  - The rest: Kokoro 1062, Higgs Audio V3 1039, Chatterbox 1024, VibeVoice 1.5B 955, "Qwen3 TTS" 929.
  - VoxCPM2 and CosyVoice3 are not listed.
- **TTS Arena V2** (data from the `https://tts-agi-tts-arena-v2.hf.space/api/leaderboard` JSON behind the page):
  - Open models: Audio8-TTS-Realistic-0.6B 1668 (preliminary), Chatterbox 1467, Kokoro v1.0 1464, Magpie Multilingual 1392.
  - Qwen3-TTS, VoxCPM2, CosyVoice3 and Ming-3.0 are **not listed**.
- Conclusion: **there is no third-party data at all on Chinese naturalness**. How Chinese sounds can only be judged by our own listening test.

---

## 4. Excluded

| Model | Reason | Source |
|---|---|---|
| IndexTTS2 / IndexTTS-2.5 | The weights use the **bilibili Model Use License Agreement** (2.5's `cardData.license_name` = `bilibili-model-license`; 2's HF repo has a `LICENSE.txt` and an empty `cardData`). The code [index-tts/index-tts](https://github.com/index-tts/index-tts) shows NOASSERTION as its GitHub license. **The license has not changed**. Note, though, that the agreement itself is "royalty-free", requiring a separate license only above 100 million monthly active users or RMB 1 billion in annual revenue; it can also be revoked for breach, is governed by Chinese law, and forbids using the output to improve other models. So it does not "forbid commercial use"; it is a non-standard custom agreement. By voxx's rule of taking only standard permissive licenses, it stays excluded. | [IndexTTS-2 LICENSE.txt](https://huggingface.co/IndexTeam/IndexTTS-2/blob/main/LICENSE.txt), [IndexTTS-2.5](https://huggingface.co/IndexTeam/IndexTTS-2.5) |
| IndexTTS-1.5 | ⚠️ HF's `cardData.license` says `apache-2.0`, but a GitHub commit on 2025-09-09 (#300) did "remove old license for v1.5" and switched to the bilibili agreement. The two contradict each other, and which one prevails is **unverified**, so it is excluded. | [IndexTTS-1.5](https://huggingface.co/IndexTeam/IndexTTS-1.5) |
| F5-TTS | Weights `cc-by-nc-4.0` (unchanged), code MIT | [SWivid/F5-TTS](https://huggingface.co/SWivid/F5-TTS) |
| Fish Audio S2 Pro | Weights under `fish-audio-research-license`; commercial use needs a separate written agreement (unchanged) | [fishaudio/s2-pro LICENSE.md](https://huggingface.co/fishaudio/s2-pro/blob/main/LICENSE.md) |
| Fish Audio Drama 3 (35B MoE) | ⚠️ The `LICENSE` file in the HF repo shows the **Fish Audio Community License** today (2026-10-29): limited commercial use under USD 500,000 in annual revenue, no hosted services. But `cardData.license_name` still says `fish-audio-research-license`; the two disagree. The model is also 81 GB, too large for a Mac. | [fishaudio/drama-3](https://huggingface.co/fishaudio/drama-3) |
| OmniVoice | Empty `cardData.license`; the model card says "The pre-trained model is licensed under the CC-BY-NC due to constraints from its training data (e.g., Emilia)" (unchanged). The code is Apache-2.0. | [k2-fsa/OmniVoice](https://huggingface.co/k2-fsa/OmniVoice) |
| ZipVoice | As above: trained on Emilia, so the weights are CC-BY-NC (unchanged) | [k2-fsa/ZipVoice](https://huggingface.co/k2-fsa/ZipVoice) |
| Higgs Audio v3 (4B) | `boson-higgs-tts-3-research-and-non-commercial-license`. It makes one exception for "digital creators"' creative content; not an open-source license. | [bosonai/higgs-tts-3-4b](https://huggingface.co/bosonai/higgs-tts-3-4b) |
| Higgs Audio v2 (3B) | Boson Higgs Audio 2 Community License: adapted from the Llama 3 license, needs a separate license above 100,000 annual active users, and requires attribution. Also a Chinese test-hard CER of 55.07 (measured by VoxCPM, third-party). | [higgs-audio-v2 LICENSE](https://huggingface.co/bosonai/higgs-audio-v2-generation-3B-base/blob/main/LICENSE) |
| Breeze TTS 2 | `breezeblue-research-and-non-commercial-license` | [BreezeBlue/Breeze-TTS-2](https://huggingface.co/BreezeBlue/Breeze-TTS-2) |
| Voxtral-4B-TTS (Mistral) | `cc-by-nc-4.0`, and zh is not among its languages | [mistralai/Voxtral-4B-TTS-2603](https://huggingface.co/mistralai/Voxtral-4B-TTS-2603) |
| Spark-TTS-0.5B | `cc-by-nc-sa-4.0` | [SparkAudio/Spark-TTS-0.5B](https://huggingface.co/SparkAudio/Spark-TTS-0.5B) |
| MegaTTS3 | Weights Apache-2.0, but upstream says "For security issues, we do not upload the parameters of WaveVAE encoder", so only pre-extracted latents work, and it **cannot clone arbitrary voices** | [bytedance/MegaTTS3](https://github.com/bytedance/MegaTTS3) |
| VibeVoice-1.5B / 7B | Weights MIT, but the model card says "limited to research purpose" and "We do not recommend using VibeVoice in commercial"; Microsoft removed the TTS code from the repo (2025-09-05); it carries an audible disclaimer and a watermark | [microsoft/VibeVoice-1.5B](https://huggingface.co/microsoft/VibeVoice-1.5B), [GitHub](https://github.com/microsoft/VibeVoice) |
| Step-Audio-EditX (3B) | The code is Apache-2.0, but the HF weights' `cardData.license` is empty, and the model card says only "The code … is licensed under Apache 2.0". **The weight license is unverified**. | [stepfun-ai/Step-Audio-EditX](https://huggingface.co/stepfun-ai/Step-Audio-EditX) |
| GLM-TTS (1.5B) | Weights MIT, code Apache-2.0: the license is fine. But the README says "Primarily supports Chinese, while also supporting English mixed text", there are no self-reported English metrics (en 1.91 measured by MOSS, third-party), no mlx support, and no pushes since 2026-04. Self-reported Seed zh 0.89 (RL version). | [zai-org/GLM-TTS](https://huggingface.co/zai-org/GLM-TTS), arXiv:2512.14291 |
| SoulX-Podcast-1.7B | Apache-2.0, but built mainly for podcast-style multi-speaker dialogue; no mlx support; no updates since 2025-12 | [Soul-AILab/SoulX-Podcast-1.7B](https://huggingface.co/Soul-AILab/SoulX-Podcast-1.7B) |
| MOSS-TTSD v1.0 | Apache-2.0, but an 8B multi-speaker dialogue model, a poor fit for single-voice narration | [OpenMOSS-Team/MOSS-TTSD-v1.0](https://huggingface.co/OpenMOSS-Team/MOSS-TTSD-v1.0) |
| Kimi-Audio-7B | MIT, but a 7B general audio model, not a dedicated cloning TTS | [moonshotai/Kimi-Audio-7B-Instruct](https://huggingface.co/moonshotai/Kimi-Audio-7B-Instruct) |
| MiniMax | No open-weight TTS from MiniMax found (HF has only MiniMax's video and text models, and third-party GGUF conversions of music models) | HF search |
| Magpie TTS Multilingual 357M (NVIDIA) | NVIDIA Open Model License, commercial use allowed, zh among its languages; but only 5 preset voices, and the zero-shot cloning version (Magpie TTS Zeroshot) is offered only through NIM. Whether the open version can clone is **unverified**. | [nvidia/magpie_tts_multilingual_357m](https://huggingface.co/nvidia/magpie_tts_multilingual_357m) |
| Kokoro | Cannot clone (see §3.10) | — |

---

## 5. Word-level forced alignment

voxx has to return `{text, start, end}` for each Line's audio.

### 5.1 Qwen3-ForcedAligner-0.6B (recommended)

- **License**: [Qwen/Qwen3-ForcedAligner-0.6B](https://huggingface.co/Qwen/Qwen3-ForcedAligner-0.6B) is `apache-2.0`, and the code [QwenLM/Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR) is Apache-2.0 too. Paper arXiv:2601.21337.
- **Languages and limits** (model card, self-reported): 11 languages (Chinese, English, Cantonese, French, German, Italian, Japanese, Korean, Portuguese, Russian, Spanish). "timestamp prediction for arbitrary units within up to 5 minutes of speech", so a single clip is at most 5 minutes. Non-autoregressive inference.
- **Accuracy** (Forced Alignment Benchmarks in the model card, AAS ms, lower is better, **self-reported**):

  | Test set | Language | Qwen3-ForcedAligner | NFA | WhisperX | Monotonic-Aligner |
  |---|---|---|---|---|---|
  | MFA-Labeled Raw | Chinese | 33.1 | 109.8 | – | 161.1 |
  | MFA-Labeled Raw | English | 37.5 | 107.5 | 92.1 | – |
  | Concat-300s | Chinese | 36.5 | 235.0 | – | 1742.4 |
  | Concat-300s | English | 58.6 | 226.7 | 227.2 | – |

  The competitors' numbers were also measured by Qwen; there is no independent reproduction.
- **Granularity**: Chinese aligns per **character**, not per word. In the mlx implementation, `tokenize_chinese_mixed` makes each CJK character one token, English splits on spaces, and Japanese is segmented with nagisa. For word-level times in Chinese, voxx would have to segment words itself (with jieba, say) and merge the character timestamps.
- **Time resolution**: the mlx config has `timestamp_segment_time: 80.0`, presumably 80 ms per step, **not verified in the official docs**.
- **Mac**: supported in upstream mlx-audio (`mlx_audio/stt/models/qwen3_asr/qwen3_forced_aligner.py`). mlx-community has bf16 (1.84 GB), 8-bit (1.28 GB) and 6/5/4-bit versions. The mlx implementation processes the whole clip at once with no chunking, which does not matter for voxx's Lines of a few to a few dozen seconds.
- **Companion**: Qwen3-ASR-0.6B (Apache-2.0, mlx 8-bit 1.01 GB) can fill in transcripts for cloning reference audio automatically.

### 5.2 Other commercially usable alignment options

| Option | Code license | Weight license | Chinese | Notes |
|---|---|---|---|---|
| torchaudio `MMS_FA` | BSD-2 | ❌ **CC-BY-NC 4.0** ([torchaudio docs](https://docs.pytorch.org/audio/stable/generated/torchaudio.pipelines.MMS_FA.html)) | yes (romanized first) | **Not commercially usable**. `facebook/mms-1b-all` is cc-by-nc-4.0 too. |
| WhisperX alignment (wav2vec2 CTC) | BSD-2-Clause ([m-bain/whisperX](https://github.com/m-bain/whisperX)) | en defaults to `WAV2VEC2_ASR_BASE_960H`, i.e. [facebook/wav2vec2-base-960h](https://huggingface.co/facebook/wav2vec2-base-960h), apache-2.0; zh defaults to [jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn), apache-2.0 | yes, per character | Source: `DEFAULT_ALIGN_MODELS_*` in [`alignment.py`](https://github.com/m-bain/whisperX/blob/main/whisperx/alignment.py). voxx already has the text and needs only the alignment step, not Whisper ASR; but it needs torch (CPU or MPS) and has no mlx version. Clearly less accurate than Qwen3-ForcedAligner (table above, self-reported by Qwen). |
| NeMo Forced Aligner (NFA) | Apache-2.0 (NeMo) | uses CTC models. zh: [nvidia/stt_zh_citrinet_1024_gamma_0_25](https://huggingface.co/nvidia/stt_zh_citrinet_1024_gamma_0_25), `cc-by-4.0`; en: for example [nvidia/parakeet-ctc-0.6b](https://huggingface.co/nvidia/parakeet-ctc-0.6b), `cc-by-4.0` | yes | CC-BY-4.0 allows commercial use but requires attribution. NeMo's dependencies are heavy; whether it installs cleanly on a Mac is **unverified**. |
| Timestamps from ASR in mlx-audio (Parakeet, Whisper and others) | MIT | depends on the model | depends on the model | These are recognized timestamps, not forced alignment against known text. Usable as a self-check, not as the main approach. |

**Recommendation**: v0.1 uses only Qwen3-ForcedAligner-0.6B (mlx 8-bit). If a fallback is needed later, take WhisperX's Apache-2.0 wav2vec2 models, run with torch. Stay away from MMS_FA.

---

## 6. Recommendations

### v0.1 default Model: Qwen3-TTS-12Hz CustomVoice (1.7B 8-bit as the main one, 0.6B 8-bit as the fast tier)

Reasons:
- Weights and code are both Apache-2.0.
- Upstream mlx-audio has supported it for 9 months; it is the first example in mlx-audio's README, with the widest range of checkpoint tiers (bf16, 4/5/6/8bit).
- Among the Models that run on a Mac, its self-reported Seed zh CER and en WER are the best.
- 9 built-in voices, usable directly as the agent's default voices; instruct controls emotion.
- The same family has Base (cloning) and VoiceDesign (design a voice, then turn it into a clone), matching DESIGN.md's design of "mapping tasks to checkpoints".

Known weak spots:
- The only native English voices are Ryan and Aiden, both male.
- No numeric speed parameter; speed is controllable only through instruct.
- The code has not been updated since 2026-03.
- "Qwen3 TTS" on Artificial Analysis has an Elo of only 929, though that row may be the API version, unverified.

**The strongest challenger is Ming-3.0-tts-0.5B**:
- MIT license; a third-party English arena Elo of 1187, the highest of all commercially usable open models.
- Explicit speed, emotion and pitch parameters, handy for fitting narration to a video's rhythm.
- English female voices (US_Emma, UK_Charlotte), 100+ Chinese voices; smaller (8-bit 1.62 GB).

Ming is not the v0.1 default because its mlx support was merged only 10 days ago and one fix PR (#1059) is still unmerged; mlx also lacks the CAM++ speaker embedding and text normalization. If the audition shows it clearly better, Ming can join the v0.1 registry as a second built-in-voice Model.

### First choice for cloning: VoxCPM2 (mlx 8-bit)

Reasons:
- Apache-2.0.
- Supported in upstream mlx-audio, with bf16/8bit/4bit.
- Among the Models that run on a Mac, the highest self-reported SIM (zh 79.5 / en 75.3, above the 77.0 / 71.7 VoxCPM itself measured for Qwen3-TTS-1.7B).
- Clones from reference audio alone, no transcript required; with a transcript it can do "Ultimate Cloning".
- Instruct can be layered on cloning to control emotion and speed. 48 kHz output.
- Actively maintained (pushes as recently as 2026-10).

Alternative: Qwen3-TTS-12Hz-1.7B-Base. It is in the same family as the default Model, so one less Model to install; ICL mode needs a transcript, which Qwen3-ASR can fill in automatically.

Weak spots: VoxCPM2's English WER of 1.84 is worse than Qwen3's 1.24 (both self-reported); llama.cpp's RTF on an M4 Pro is 1.76 (slower than real time), and the speed under mlx has to be measured ourselves.

### Add later

1. **Ming-3.0-tts-0.5B**: once mlx support settles (#1059 merged, CAM++ implemented), decide by the audition whether to make it the default.
2. **Fun-CosyVoice3-0.5B-2512**: once PR #861 is merged into upstream mlx-audio, without depending on the mlx-audio-plus fork (consistent with DESIGN.md's decision).
3. **FireRedTTS3 / dots.tts**: Apache-2.0 with the highest self-reported SIM (80.9 to 81.0), but upstream mlx-audio does not support them, so wait, or go through a v0.2 torch worker.
4. **MOSS-TTS-Nano**: a CPU fallback for getting sound out quickly without a GPU; MOSS-TTS's token-level duration control is worth another look when "synthesize to a duration" comes up.
5. **Audio8-TTS-Realistic-0.6B**: first on TTS Arena. Revisit once it has a Mac runtime and its training and derivation provenance is confirmed.
6. **Chatterbox Multilingual V3**: license and mlx support are fine, but it has no Chinese metrics at all; decide after an audition. Note that the mlx version has no Perth watermark.

### Questions the listening test still has to answer

- Naturalness: every third-party arena tests English only, so **there is no outside data at all on Chinese naturalness**. Blind-compare Qwen3-TTS 1.7B CustomVoice, Qwen3-TTS 0.6B CustomVoice, Ming-3.0-tts-0.5B (mlx) and VoxCPM2 (mlx 8-bit), plus CosyVoice3 (the fork version) if possible, on the same batch of CueTake-style Chinese and English narration (with mixed Chinese and English, numbers, product names and code terms).
- Cloning: with the same 5 to 15 seconds of the user's own recording, compare Chinese and English similarity and stability across VoxCPM2 (reference audio alone, and reference audio plus transcript), Qwen3-1.7B-Base (ICL and x-vector modes) and Ming-3.0 (mlx, without CAM++).
- Quantization loss: how 8-bit sounds against bf16 (no public comparison exists).
- Speed: measure each Model's RTF and peak memory on the target M-series machine. So far there is only mlx-audio's claim for Ming (about real time, 4.4 GB on an M4 Pro), Qwen3's 6-bit batch numbers (chip unknown), and VoxCPM2's RTF of 1.76 on llama.cpp.
- Alignment self-check: align the synthesized results with Qwen3-ForcedAligner and check whether Chinese per-character timestamps merged into words are usable; also count each Model's rate of dropped and added characters.

---

## 7. Open and unverified

1. **Qwen3-TTS's entry on Artificial Analysis** (Elo 929): whether it measures the open checkpoint or the Alibaba Cloud API, unverified.
2. **Whether AA tested Ming-3.0's 0.5B or tiny**, unverified (AA links the 0.5B).
3. **Ming-3.0's cloning similarity on mlx**: mlx has no CAM++ speaker embedding, so similarity may be below the self-reported 0.758 / 0.691; not measured.
4. **MOSS-TTS-Nano's HF model card** still says "treat the repository as not yet licensed", and the HF repo has no LICENSE file; GitHub says Apache-2.0. Which one voxx's registry goes by needs deciding.
5. **IndexTTS-1.5**: HF says Apache-2.0, GitHub has switched to the bilibili agreement; the two contradict each other.
6. **Fish Audio Drama 3**: the LICENSE file on HF (showing the Community License today, with a USD 500,000 revenue threshold) and the cardData (research license) disagree. Little impact on voxx, since the model is too large.
7. **Step-Audio-EditX's weight license**: not stated on HF.
8. **Audio8-TTS's training data and derivation provenance** (whether the Fish license binds it), unverified.
9. **Each Model's reference audio length requirement**: apart from Qwen3's "3 seconds" and GLM-TTS's "3–10 seconds", no Model gives a concrete number. voxx's "5–15 seconds of clean voice" guideline still needs confirming by measurement.
10. **Whether the official torch packages of Qwen3-TTS and CosyVoice3 run on MPS**, unverified. Only VoxCPM's source explicitly supports MPS.
11. **Qwen3-ForcedAligner's 80 ms time resolution**, inferred from the mlx config.
12. **Watermarks**: none of the READMEs of Qwen3-TTS, VoxCPM2, CosyVoice3, Ming-3.0, FireRedTTS3, dots.tts or MOSS mention a built-in watermark. Chatterbox's Perth watermark is not applied on the mlx path. Whether voxx should add its own watermark (such as AudioSeal, whose license needs checking separately) needs deciding.
13. **Qwen3-TTS's Chinese CER differs a lot across the MOSS, VoxCPM and Ming tables** (0.77 to 1.33), so evaluation setups differ widely; Seed-TTS numbers from different teams cannot be compared directly.
