# 只有念所必需的 Model 没装才失败，辅助 Model 没装降级为警告

ADR 0003 说缺模型时命令以「未安装」失败。`narrate` 原先把它用到一个 Line 用到的每个 Model 上：念的 Model、对齐 Model 和听写 Model 缺一个，整次运行就以退出码 3 失败。但三者地位不同：念的 Model 产出音频，没有它什么都做不了；对齐 Model 只产出 `words`，听写 Model 只产出 `transcript` 和 `error_rate` 这份质量报告，缺了它们音频照样能用。所以现在只有念的 Model 没装才以 `model_not_installed` 失败；对齐或听写 Model 没装时，每个 Line 照常念，只是不带相应字段，各带一条 `aligner_not_installed` 或 `checker_not_installed` 警告，details 给出那个 Model 的 id、大小、许可证和安装命令。这样用户只装一个 TTS Model 也能用 voxx，agent 仍然拿到足够的信息去问用户要不要补装。

## Considered options

- **维持全部必需。** 否决：第一次用 voxx 要先下三个 Model，其中两个对很多用途（不需要字幕、自己会听）只是锦上添花。
- **辅助 Model 缺失时只在结果顶层报一次。** 否决：警告和缺的字段都在 Line 上，agent 逐个 Line 判断时不必再回头看别处；`--line` 重念的 Line 也自然带上自己的警告。

## Consequences

- 警告 code 和「这种语言没有 Model」的 `not_aligned`/`not_checked` 分开：后者装什么都补不上，前者装一个 Model 再 `--line` 重念就能补上。
- 规则只看这一步能不能做下去。`voice add` 没给参考录音文字时要靠听写 Model 补文字，那一步没有它做不下去，所以那里听写 Model 仍是必需的。
