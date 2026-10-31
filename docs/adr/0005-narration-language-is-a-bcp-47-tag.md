# 旁白的 language 是 BCP 47 标签，按原样和 Model 的语言比对

v0.1 的 spec 原来规定 `language` 用 ISO 639-1 两字母代码，但 Qwen3-ASR 支持的粤语（`yue`）和菲律宾语（`fil`）没有两字母代码，所以改用 BCP 47。BCP 47 包含 ISO 639-1，原来的 `zh`、`en` 照样有效，CueTake 也本来就把 `language` 当作语言标签处理（如 `zh-CN`）。标签只接受规范大小写（`zh-Hant-HK`，不接受 `zh-hant-hk`），并且必须和 Model 登记的某个语言完全一致，voxx 不做 `en-US` → `en` 这样的逐级回退。

## Considered options

- **按 RFC 4647 lookup 逐级回退。** 否决：`zh-HK` 会悄悄退成 `zh`，被当作普通话念出来；完全一致时 agent 会拿到 `unsupported_language` 和 Model 实际登记的语言列表，自己改成正确的标签。
- **不区分大小写。** 否决：只有一种写法时，比对和输出都不会出现歧义；大小写写错时，报错会给出规范写法。

## Consequences

- 一个 Model 能念 `en`，不代表它能念 `en-US`：注册表登记什么，旁白就得写什么。
- 自检也按完全一致来找能听写这种语言的 Model，所以 `en-GB` 的旁白不会交给只登记了 `en` 的 Model 听写，而是带 `not_checked` 警告。
