# 模型只通过显式的 install 命令下载

任何命令都不会自己下载模型。缺模型时，命令以「未安装」失败，并说明需要安装哪个模型、多大、什么许可证；agent 按 skill 的要求把这些告诉用户，用户同意后才运行 `voxx install <model>`。这和 CueTake 的 `install-browser` 是同一套规矩，agent 只需要学一次。

## Considered options

- **consent token 加专门的退出码（DESIGN.md 草案）。** 否决：CLI 验证不了真的有人同意，token 只是多了一层复杂度，起不到额外的保护作用。

## Consequences

- 注册表只登记权重许可证允许商用的模型，因为 voxx 的主要用途是给要发布的产品演示配音。
