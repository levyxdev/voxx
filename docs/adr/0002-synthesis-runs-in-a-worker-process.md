# 合成在独立的 worker 进程里运行

CLI 不在自己的进程里加载模型，而是启动一个 worker 进程，用 JSON-RPC over stdio 通信，一份旁白念完 worker 就退出。这样 mlx 爆显存或崩溃时只会死掉 worker，CLI 仍能给 agent 返回结构化的错误；模型占用的几个 GB 内存随 worker 退出归还；CLI 自己不 import mlx，`voxx models`、`voxx schema` 这类命令能立刻返回。以后接入 PyTorch 系的引擎或加常驻模式，都沿用同一个协议。

## Considered options

- **单进程、延迟 import。** 否决：代码最少，但崩溃时 agent 拿不到 JSON 错误，协议也要到以后再补。
- **每个引擎一个独立 venv。** 推迟：只有当两个引擎要求同一个依赖的不同版本时才需要（例如官方 CosyVoice 和 Qwen3-TTS 包各自锁定的 `transformers` 版本冲突）。v0.1 的模型都通过 mlx-audio 运行，worker 就是同一个包里的 `python -m voxx.worker`。
