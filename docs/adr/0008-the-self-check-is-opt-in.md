# 听写自检默认不做，`--check` 才做

`narrate` 和 `voice design` 原先把每个 Line、每个 Design Take 都用 Qwen3-ASR 听写回来，算出 `transcript` 和 `error_rate`。这一步要把听写 Model 和念的 Model、对齐 Model 一起留在 worker 里：一次 `narrate` 峰值约 5.7 GB，16 GB 的 Mac 上和别的程序一起跑时会内存不足，每个 Line 还要多花一次听写的时间。而用户反正会自己听：机器听写只能说明念没念对字，说不出好不好听，听写本身也会听错（"Press send" 听成 "Press in"）。所以现在默认不听写，Line 和 Design Take 不带 `transcript` 和 `error_rate`，也不因为听写 Model 没装或这种语言没有听写 Model 而警告；传 `--check` 才照原样听写，缺听写 Model 时照 ADR 0006 降级为警告。

## Considered options

- **维持默认听写。** 否决：多占约 1 GB 内存和每个 Line 一次听写的时间，换来的是用户本来就要自己听的结论。
- **去掉听写自检。** 否决：用户不方便逐个听时（Line 很多、无人值守地重念），`error_rate` 仍然是 agent 找出念错的 Line 的唯一办法。

## Consequences

- skill 改为让用户听；用户要求检查、或不会逐个听时，agent 才传 `--check`。
- `voice add` 没给 `--ref-text` 时照旧用听写 Model 补参考录音的文字：那一步没有文字做不下去，和自检无关。
- 对齐 Model 照旧默认运行：`words` 是字幕要用的，不是检查。
