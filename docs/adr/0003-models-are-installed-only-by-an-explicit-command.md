# 模型只通过显式的 install 命令下载

任何命令都不会自己下载模型。缺模型时，命令以「未安装」失败，并说明需要安装哪个模型、多大、什么许可证；agent 按 skill 的要求把这些告诉用户，用户同意后才运行 `voxx install <model>`。这和 CueTake 的 `install-browser` 是同一套规矩，agent 只需要学一次。

缺哪些模型才算失败，见 [ADR 0006](0006-only-the-model-that-reads-must-be-installed.md)：只有念所必需的模型，辅助模型缺失降级为警告。

## 额外仓库（2026-11-07 补充）

有的 Model 加载时还要别的仓库，比如 Chatterbox 要 `mlx-community/S3TokenizerV2`。注册表把它登记成 Model 的额外仓库，写上核实时的大小和许可证；`voxx install` 把它和 Model 一起下载，安装前告诉用户的大小算上它，并说明会连带下载哪些仓库。只有用户同意的 `voxx install` 会下载，这一条不变。额外仓库的文件缺一个，Model 就算没安装。

额外仓库**不钉版本**：`voxx install` 下载它当时的最新版，把实际下载的 revision 记进安装清单，大小和核实时不同也照样安装。原因是引擎按仓库名去拉它，不带 revision（Chatterbox 把仓库名写死在代码里），拿到的本来就是最新版；它只是 tokenizer 这类配套权重，许可证跟着上游。代价是两次安装可能装到不同的 revision，所以安装清单要记下实际装的是哪个。主仓库照旧钉住 revision，大小不符就拒绝安装。

额外仓库按 Hugging Face 缓存的目录结构放在 `$VOXX_HOME/hf-cache`，worker 把 `HF_HUB_CACHE` 指向这里，引擎离线时按仓库名就能找到它，也不会读到用户自己的 Hugging Face 缓存。

## Considered options

- **consent token 加专门的退出码（DESIGN.md 草案）。** 否决：CLI 验证不了真的有人同意，token 只是多了一层复杂度，起不到额外的保护作用。

## Consequences

- 注册表只登记权重许可证允许商用的模型，因为 voxx 的主要用途是给要发布的产品演示配音。
