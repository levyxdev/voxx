# Licenses and upstream checks for the audition candidates (2026-11)

## 1. Scope

Question: step 1 of [levyxdev/voxx#25](https://github.com/levyxdev/voxx/issues/25). Can the five candidates (Ming-3.0-tts-0.5B, Chatterbox Multilingual V3, MOSS-TTS-Nano-100M, Audio8-TTS-Realistic-0.6B, Qwen3-TTS-12Hz-1.7B-VoiceDesign) be registered under ADR 0003, and should mlx-audio be upgraded? Background is in [tts-models-2026-10.md](tts-models-2026-10.md); this report holds only what was re-checked and what is new.

Checked on 2026-11-06. Method:
- Licenses, HEAD shas and file lists read from the HF API (`https://huggingface.co/api/models/<repo>` and `.../tree/main?recursive=true`). Sizes are the sum of all file sizes in the tree API (`lfs.size` for LFS files).
- GitHub licenses read from `license.spdx_id` of `gh api repos/<owner>/<repo>`.
- mlx-audio read from upstream source and release notes. The repo has been renamed to [Neywa-Labs/mlx-audio](https://github.com/Neywa-Labs/mlx-audio); the old address Blaizzy/mlx-audio redirects (commit `e083358`, 2026-11-03).
- No weights were downloaded. The Audio8 codec comparison read only the zip central directories and `data.pkl` of two `codec.pth` files over HTTP Range (about 1.2 MB of metadata in all: tensor names, each tensor's CRC32 and byte count); no tensor data was read and no pickle was deserialized.

Labels follow the previous survey: **self-reported**, **third-party**, **unverified**.

---

## 2. Summary

| Model | Weight license (original / mlx) | LICENSE file (original / mlx / GitHub) | mlx repo voxx would pin · HEAD · size | Registrable? | Blockers and notes |
|---|---|---|---|---|---|
| Ming-3.0-tts-0.5B | MIT / MIT | none / yes (MIT) / yes (MIT) | `mlx-community/Ming-3.0-tts-0.5B-8bit` · `d0d1da6f627e4b3f20cc2db6ba4aee86d45343ad` · 1,617,181,518 B (1.62 GB) | **Yes** | Fix PR #1059 still unmerged; mlx does not extract CAM++ |
| Chatterbox Multilingual V3 | MIT / MIT | none / none / yes (MIT) | `mlx-community/chatterbox-multilingual-v3` · `03565773edd72e949572557597af8063bb49a18a` · 2,713,107,406 B (2.71 GB); at load it also fetches `mlx-community/S3TokenizerV2` · `e0c9886f0e1c35ae85b1f27277416fb19fc72bec` · 494,869,110 B | **Yes**, but S3TokenizerV2 must be pinned and installed with it | The S3TokenizerV2 repo states no license (upstream CosyVoice2-0.5B is Apache-2.0); the mlx version requires reference audio; no Perth watermark |
| MOSS-TTS-Nano-100M | Apache-2.0 / Apache-2.0 | none / none / yes (Apache-2.0) | `mlx-community/MOSS-TTS-Nano-100M` · `229a9c51bb0ffff6fd0dbe53b5bf0c441e438a79` · 285,462,910 B (0.29 GB); at load it also fetches `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano` · `6aa02b01e445cc585582cf0ba480bc3ea6c8dd68` · 87,976,790 B | **Yes**, but the audio tokenizer must be pinned and installed with it | The "do not redistribute" line on the HF card is stale; the publisher confirmed on GitHub that the weights are Apache-2.0; no TTS quality metrics; the mlx version can only clone |
| Audio8-TTS-Realistic-0.6B (now Realistic-Air) | Apache-2.0 / Apache-2.0 | yes (Apache-2.0 + NOTICE) / none / yes (Apache-2.0) | `mlx-community/Audio8-TTS-Realistic-0.6b-bf16` · `f2addfde1a6196399bf23330dfd66c47b2fe10ea` · 2,565,175,187 B (2.57 GB) | **No** | 462 of the 535 tensors in its bundled codec are byte-identical to Fish Audio S2 Pro's codec, so it is bound by the Fish license (commercial use needs a separate agreement); it also needs mlx-audio 0.6.4 |
| Qwen3-TTS-12Hz-1.7B-VoiceDesign | Apache-2.0 / Apache-2.0 | none / none / yes (Apache-2.0) | `mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit` · `f90d617701d9f7f4ca499291e0b57f2b3c2fd2ee` · 3,080,140,867 B (3.08 GB) | **Yes** | Nothing new; mlx-audio 0.6.3 already supports it |

The "LICENSE file" column: of the five original repos only Audio8 carries a LICENSE file; the rest declare it only in `cardData.license`. voxx no longer distributes weights and only downloads them from HF on the user's command, so a missing LICENSE file is not a blocker in itself; `cardData.license` plus the GitHub LICENSE is what counts, as for the six Models already in the registry.

---

## 3. Model by model

### 3.1 Ming-3.0-tts-0.5B

- **License**: the original repo [inclusionAI/Ming-3.0-tts-0.5B](https://huggingface.co/inclusionAI/Ming-3.0-tts-0.5B) has `cardData.license` `mit`, HEAD `7247f4c94a5b2e987404ed28a5cfec41b1a4ca61` (2026-10-27, unchanged), 3,004,401,795 B, **no** LICENSE file; the model card ends with a link to the GitHub LICENSE. The mlx repo [mlx-community/Ming-3.0-tts-0.5B-8bit](https://huggingface.co/mlx-community/Ming-3.0-tts-0.5B-8bit) is `mit`, with `base_model` pointing at the original repo, and **does** carry a LICENSE file (MIT, "Copyright (c) 2025 inclusionAI"). The code [inclusionAI/Ming-3.0-tts](https://github.com/inclusionAI/Ming-3.0-tts) is MIT.
- **Other restrictions on the card**: the "Usage Disclaimer" says cloning and the built-in character voices are "provided for research and legitimate creative use", that real people must not be impersonated without consent, and that synthetic audio must be labelled where it could be mistaken for a real recording. It is a usage statement, not a license term: no "research only" and no watermark requirement.
- **IP voices**: the voice table includes Kangxi, Tang Seng, Peppa and others; they are not blocked on integration (user's decision, 2026-11-06).
- **CAM++ in the mlx repo**: the 8-bit repo carries `campplus.safetensors` (27,699,096 B), but mlx-audio's [dense README](https://github.com/Neywa-Labs/mlx-audio/tree/main/mlx_audio/tts/models/dense) still says "Automatic CAM++ speaker embedding extraction is not implemented"; `spk_emb=` can only be passed by hand. The license of the CAM++ weights themselves is **unverified**.
- **Upstream fix**: see §4.1; #1059 is still unmerged. Nothing changed Ming's code between 0.6.3 and 0.6.4 (the compare has no `dense` or `bailingmm` changes).
- **Verdict**: the license is fine, **registrable**. Quality risks (runaway decoding, a trailing hum) are left to the audition.

### 3.2 Chatterbox Multilingual V3

- **License**: V3 has no repo of its own; the weights `t3_mtl23ls_v3.safetensors` and `s3gen_v3.safetensors` sit in [ResembleAI/chatterbox](https://huggingface.co/ResembleAI/chatterbox), whose `cardData.license` is `mit`, HEAD `5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18` (2026-06-10), 13,866,212,931 B for the whole repo (v1/v2/v3 included), **no** LICENSE file. The mlx repo [mlx-community/chatterbox-multilingual-v3](https://huggingface.co/mlx-community/chatterbox-multilingual-v3) is `mit` with no LICENSE file; its card says it was converted from ResembleAI/chatterbox with mlx-audio 0.4.7. The code [resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox) is MIT ("Copyright (c) 2025 Resemble AI").
- **A second repo at load**: the mlx card says it "requires the S3Tokenizer weights from mlx-community/S3TokenizerV2, which will be downloaded automatically". The source ([chatterbox.py](https://github.com/Neywa-Labs/mlx-audio/blob/v0.6.4/mlx_audio/tts/models/chatterbox/chatterbox.py) from line 586) calls `snapshot_download("mlx-community/S3TokenizerV2")` unconditionally at load, **with no revision pinned**. [mlx-community/S3TokenizerV2](https://huggingface.co/mlx-community/S3TokenizerV2) has an **empty** `cardData.license` and no LICENSE file; its `base_model` is [FunAudioLLM/CosyVoice2-0.5B](https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B) (`apache-2.0`), and its card says mlx-audio-plus converted it. To register it, voxx must pin this repo at `voxx install` too, and decide to record its license as upstream's Apache-2.0.
- **Watermark**: the official card says "Every audio file generated by Chatterbox includes … Perth … Watermarker". That is the official package's behaviour; the MIT license does not require a watermark. `perth` does not appear in mlx-audio's source (GitHub code search: 0 hits), so mlx-generated audio carries no watermark.
- **Built-in voices** (marked unverified in the previous survey): in the official torch package `generate(text)` reads without reference audio, using the repo's `conds.pt`: one default voice only, no table of named voices. The mlx repo has no `conds.safetensors`, and the source raises `ValueError` when there is neither `ref_audio` nor conds, so **the mlx version can only clone**. The default voice's gender is **unverified**.
- **Verdict**: the license is fine, **registrable**, provided S3TokenizerV2 is pinned and installed with it.

### 3.3 MOSS-TTS-Nano-100M

- **License**: [OpenMOSS-Team/MOSS-TTS-Nano-100M](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M) has `cardData.license` `apache-2.0`, HEAD `44502f80dbf9743528fa921cc544d662c685ebec`, last commit 2026-04-13 with **no change since**, 237,808,621 B, and still **no** LICENSE file. The card's "License" section still says "If you are reading this before that file is published, please treat the repository as **not yet licensed for redistribution**". The mlx repo [mlx-community/MOSS-TTS-Nano-100M](https://huggingface.co/mlx-community/MOSS-TTS-Nano-100M) is `apache-2.0` with no LICENSE file and an empty README.
- **Resolving the inconsistency**:
  - The README of GitHub [OpenMOSS/MOSS-TTS-Nano](https://github.com/OpenMOSS/MOSS-TTS-Nano) carries **the same sentence**, and GitHub's root LICENSE (Apache-2.0) was added the day after the repo was created (commit `c8cdc4e`, 2026-04-11, "add lincense"). The HF card was copied from the GitHub README, and the sentence refers to that GitHub LICENSE file, so on GitHub the condition is already met.
  - The publisher has answered directly: GitHub issue [#91 "Clarification on the license for MOSS-TTS-Nano model weights"](https://github.com/OpenMOSS/MOSS-TTS-Nano/issues/91) asked "Are the model weights released under the Apache License 2.0?"; repo COLLABORATOR alpacaking replied "Yes" on 2026-07-28, pointing out that both the HF metadata and GitHub say Apache-2.0, and closed it as completed.
  - So: **the weights are Apache-2.0 and can be registered**. The sentence on the HF card is stale template text.
- **A second repo at load**: the mlx repo's `config.json` says `audio_tokenizer_pretrained_name_or_path: OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano`. The source (`_resolve_audio_tokenizer_dir` in [moss_audio_tokenizer.py](https://github.com/Neywa-Labs/mlx-audio/blob/v0.6.4/mlx_audio/codec/models/moss_audio_tokenizer/moss_audio_tokenizer.py)) calls `snapshot_download` on this repo at the first clone, **with no revision pinned**. [OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano](https://huggingface.co/OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano) is `apache-2.0`, HEAD `6aa02b01e445cc585582cf0ba480bc3ea6c8dd68`, 87,976,790 B to download by the source's `allow_patterns`, no LICENSE file, and its card lacks the "not yet licensed" sentence. voxx must pin it at install and pass a local path through `audio_tokenizer_source`.
- **Built-in voices** (marked unverified in the previous survey): they exist only in `browser_poc_manifest.json` of the ONNX repo [MOSS-TTS-Nano-100M-ONNX](https://huggingface.co/OpenMOSS-Team/MOSS-TTS-Nano-100M-ONNX): 18 in all, as precomputed reference audio codes. English female voices include Bella and Ava; English male voices include Adam, Nathan, and one called **Trump**; the 7 Japanese female voices are named Anon, Soyo, Mortis, Togawa and so on, which look like anime characters. All carry likeness and IP risk. **The mlx version does not support built-in voices**: `voice_clone` mode requires `ref_audio`, and the other mode, `continuation`, specifies no voice.
- **Verdict**: the license is **registrable**; engineering-wise the second repo must be pinned. There are no TTS quality metrics at all, so only the audition can judge it.

### 3.4 Audio8-TTS-Realistic-0.6B (now Audio8-TTS-Realistic-Air)

- **Rename**: `Edge0/Audio8-TTS-Realistic-0.6b` now 307-redirects to [Edge0/Audio8-TTS-Realistic-Air](https://huggingface.co/Edge0/Audio8-TTS-Realistic-Air) (commit "Align naming with Audio8-TTS-Realistic-Air", 2026-11-02). HEAD `23c305cc013fde378edb459f538317043c993a74`, 2,565,567,307 B. The mlx card says it was converted from revision `925bbd4`; the weights did not change with the rename.
- **License**: the original repo is `apache-2.0` and **does** carry a LICENSE (the full Apache-2.0 text) and a NOTICE ("The model architecture is inspired by the DualAR design used in Fish Audio S2 Pro."); its `base_model` is [Edge0/Audio8-TTS-Preview-0.6b](https://huggingface.co/Edge0/Audio8-TTS-Preview-0.6b) (also `apache-2.0`). The mlx repo [mlx-community/Audio8-TTS-Realistic-0.6b-bf16](https://huggingface.co/mlx-community/Audio8-TTS-Realistic-0.6b-bf16) is `apache-2.0` with no LICENSE file. GitHub [Edge0-AI/Audio8_TTS](https://github.com/Edge0-AI/Audio8_TTS) is Apache-2.0. Note that the 0.1B of the same series uses a custom `audio8-community-license-v1.0`, not Apache.
- **The language model is not derived from Fish**:
  - Paper [arXiv:2610.14776](https://arxiv.org/abs/2610.14776) §3.2: the slow branch is "based on a Qwen2.5 0.5B language model". `config.json` agrees: width 896, 24 layers, 14 heads, 2 KV heads, FFN 4864, `attention_qkv_bias: true`, exactly the shape of Qwen2.5-0.5B.
  - Fish S2 Pro ([config.json](https://huggingface.co/fishaudio/s2-pro/blob/main/config.json)) is `fish_qwen3_omni`, width 2560, 36 layers; the shapes do not match, so it cannot have been initialized from it.
  - Paper §4.1: the SFT data is "cleaned Emilia and YODAS2 with a private collection".
- **The codec is derived from Fish's codec** (the key evidence):
  - Paper §3.1 says only "A fixed audio tokenizer … Both the tokenizer and the decoder remain fixed throughout language-model training", without saying where the codec comes from.
  - Structure: the encoder (dim 64, strides 2/4/8/8, a 4-layer transformer at the last stage), decoder (1536 channels, strides 8/8/4/2) and quantizer (1 semantic codebook of 4096 + 9 residual codebooks of 1024, 2×2 downsampling, window 128) in `modeling_arktts_codec.py` are identical to fish-speech's [`modded_dac_vq.yaml`](https://github.com/fishaudio/fish-speech/blob/main/fish_speech/configs/modded_dac_vq.yaml). Only `post_module` differs (Audio8's FFN is 1216 with 8 KV heads; Fish's is 3072 with 16 heads).
  - Weights: Audio8's `codec.pth` (1,349,857,559 B, sha256 `c310505a…`) differs as a whole from [fishaudio/s2-pro](https://huggingface.co/fishaudio/s2-pro)'s `codec.pth` (1,871,099,728 B, sha256 `74fc41c5…`, the same file as [fishaudio/drama-3](https://huggingface.co/fishaudio/drama-3)'s). But comparing tensor by tensor through the zip central directories, **462 of Audio8's 535 tensors have exactly the same CRC32 and byte count as Fish's**, covering 1,129,379,336 B, 84% of Audio8's codec tensor data (1,349,715,464 B). By module: encoder 156/156, decoder 119/119, `pre_module` 73/73, up- and downsampling 44/44, semantic and residual codebooks 70/70 are all identical; only the 73 tensors of `post_module` all differ. Fish's checkpoint directory inside the zip is named `modded_dac_msstftd_step_1380000`; Audio8's is `codec`.
  - Tokenizer: the git oids of `tokenizer.json`, `tokenizer_config.json` and `special_tokens_map.json` are identical to fishaudio/s2-pro's; `semantic_begin_id` 151678 and `vocab_size` 155776 also match S2 Pro.
  - Preview-0.6b's `codec.pth` has the same sha256 as Realistic-Air's, so both generations share it.
  - The paper's acknowledgements say "The Fish Audio S2 implementations also underpin much of our training and inference code".
- **Does the Fish license bind it: yes**.
  - The S2 Pro repo's [LICENSE.md](https://huggingface.co/fishaudio/s2-pro/blob/main/LICENSE.md) (Fish Audio Research License) defines "Derivative Work(s)" as including "any modifications to a Model, and any other model created which is based on or derived from the Model", and provides that "Any use of the Fish Audio Materials or Derivative Works for a Commercial Purpose requires a separate written license agreement from Fish Audio".
  - Fish's new [Community License v1.0](https://github.com/fishaudio/fish-speech/blob/main/LICENSE) (2026-10-13) explicitly lists this codec as a Model, but only "solely for use with Fish Audio Drama 3 and its Derivative Works"; commercial use is limited to annual revenue under USD 500,000 and requires showing "Built with Fish Audio".
  - Under either agreement, the codec Audio8 bundles is not something Apache-2.0 can relicense. Edge0's NOTICE mentions only "architecture inspired" and does not state that the codec weights come from Fish.
- **Other**:
  - mlx-audio has supported Preview since 2026-07-30 (commit `b734d1d`), so the previous survey's "no mlx support" was inaccurate. Realistic needs 0.6.4 ([#1093](https://github.com/Neywa-Labs/mlx-audio/pull/1093), merged 2026-10-29).
  - Capabilities: cloning needs reference audio plus an accurate transcript; without reference audio it uses "its own default voice" ([arktts README](https://github.com/Neywa-Labs/mlx-audio/tree/v0.6.4/mlx_audio/tts/models/arktts)); no named voices, no voice design.
  - The card's usage requirement: "Obtain permission to clone a voice and disclose synthetic audio where appropriate."
- **Verdict**: **not registrable**. The blocker is that the codec derives from Fish S2 Pro's codec weights and is bound by the Fish license; commercial use needs a separate agreement with Fish.

### 3.5 Qwen3-TTS-12Hz-1.7B-VoiceDesign

- **License**: [Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign) is `apache-2.0`, HEAD `5ecdb67327fd37bb2e042aab12ff7391903235d3` (2026-01-29, unchanged), 4,520,163,832 B, no LICENSE file. The mlx repo [mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit) is `apache-2.0` with no LICENSE file; its card says it was converted with mlx-audio 0.3.0. The code [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) is Apache-2.0. The model card has no restrictions beyond the license.
- **mlx**: `config.json`'s `tts_model_type` is `voice_design`, so `generate()` hands off to `generate_voice_design()`, taking `instruct` as the voice description ([qwen3_tts.py](https://github.com/Neywa-Labs/mlx-audio/blob/v0.6.3/mlx_audio/tts/models/qwen3_tts/qwen3_tts.py) line 1221); 0.6.3 already supports it.
- **Verdict**: **registrable**.

---

## 4. mlx-audio

### 4.1 PR #1059 (the Ming fix)

[#1059 "Ming-3.0: cap runaway decodes and cut the trailing hum"](https://github.com/Neywa-Labs/mlx-audio/pull/1059) is still **OPEN**: not merged, in no release, not on main. It has a single commit, `6de3388`, and no review. The last comment is from maintainer lucasnewman on 2026-10-29, who suspects the root cause is a bug in EOS handling and would rather not fix it with heuristics. No merged PR has changed Ming's code since (the last commit to the `bailingmm` directory is from 2026-10-25).

### 4.2 Latest version and support for the five Models

- The latest on both PyPI and GitHub is **0.6.4** (uploaded to PyPI on 2026-11-02, [release notes](https://github.com/Neywa-Labs/mlx-audio/releases/tag/v0.6.4)).
- Both 0.6.3 and 0.6.4 have `dense` (Ming), `chatterbox` (v2/v3), `moss_tts_nano`, `arktts` (Audio8) and `qwen3_tts` (VoiceDesign included) under `mlx_audio/tts/models`. The only difference is Audio8: Realistic support (#1093) went into 0.6.4.
- So the four registrable candidates **all run on 0.6.3**; Audio8, the only one that needs 0.6.4, is blocked by its license.

### 4.3 What 0.6.3 to 0.6.4 does to voxx's existing Models

The only mlx-audio APIs voxx calls are `mlx_audio.tts.utils.load`, `mlx_audio.stt.utils.load`, each model's `generate()` and `mlx_audio.audio_io.read` (`src/voxx/engines/mlx_audio.py`, `src/voxx/audio.py`). The changes in the [v0.6.3…v0.6.4 compare](https://github.com/Neywa-Labs/mlx-audio/compare/v0.6.3...v0.6.4) that touch them:

- `qwen3_tts.py` +8 lines ([#1096](https://github.com/Neywa-Labs/mlx-audio/pull/1096)): warms the decoder up with the reference codes only in ICL **streaming** generation. voxx does not stream, so no effect.
- `mlx_audio/utils.py`: `apply_quantization` gains a `model_load_quant_predicate` hook, and loading also runs `replace_scaled_quantized_linears` and `prepare_modelopt_weights` (NVFP4 / ModelOpt support). For the mlx-community 8-bit affine checkpoints voxx uses this should be a no-op (inferred from the code, **not measured**).
- `voxcpm2`, `qwen3_asr`, `tts/utils.py`, `stt/utils.py` and `audio_io` are unchanged. The dependency lists are identical (`mlx==0.32.4`, `transformers[chat-template]>=5.14.0` and so on).
- No breaking changes found.

After 0.6.4, main has one more fix that bears directly on voxx and is **not released yet**: [#1117 "apply the speech-tokenizer decoder's sliding window"](https://github.com/Neywa-Labs/mlx-audio/pull/1117) (merged 2026-11-03). The PR says Qwen3-TTS's speech tokenizer decoder ignored `sliding_window` (72 frames), so past 5.76 seconds it looked further than the reference implementation; after the fix, relL2 against the PyTorch decoder drops from 0.25 to 3e-6 (**self-reported**). This changes the output of every voxx Qwen3-TTS Model for Lines longer than 5.76 seconds. main also relaxed the mlx dependency from `==0.32.4` to `>=0.32.4` (#1128).

### 4.4 Recommendation

**Stay on 0.6.3 for now; do not upgrade to 0.6.4 for this audition.** Reasons: 0.6.3 supports all four registrable candidates; 0.6.4 brings no visible behaviour change to voxx's existing Models; and Audio8, the only one that needs 0.6.4, cannot be registered.

**Upgrade once the next release containing #1117 (probably 0.6.5) is out**, running `VOXX_TEST_REAL=1 uv run pytest tests/test_real_models.py` when upgrading. If the audition uses Qwen3-TTS as the baseline, regenerate the baseline samples with the fixed version, or the baseline's long Lines will sound worse than they should.

---

## 5. Unverified

1. **The Audio8 codec's `post_module`**: retrained, or fine-tuned from Fish's. It does not affect the verdict, since the other 84% of the tensors are byte-identical to Fish's.
2. **Whether mlx-community's Audio8 `codec.safetensors`** was converted from the same codec: inferred only from its size (1,349,643,293 B) and `base_model`, without a tensor-by-tensor comparison.
3. **The Emilia dataset's license**: Audio8's SFT used Emilia. [amphion/Emilia-Dataset](https://huggingface.co/datasets/amphion/Emilia-Dataset) shows `cardData.license` `cc-by-4.0`, but the README needs a login, so whether the original Emilia part is NC is **unverified** (the OmniVoice card says Emilia binds it to CC-BY-NC). Since the codec already blocks Audio8, this does not affect the verdict.
4. **The license of mlx-community/S3TokenizerV2**: the repo states none. Apache-2.0 by upstream CosyVoice2-0.5B, but that is an inference.
5. **The gender and style of Chatterbox's default voice (`conds.pt`)**.
6. **The license of `campplus.safetensors` (CAM++) in Ming's mlx repo**.
7. **Whether 0.6.4's quantized loading hook** really is a no-op for voxx's 8-bit checkpoints: only the code was read.
8. **Where #1059 goes**: the maintainer leans towards finding the root cause in EOS handling, and the fix may come in another PR.
