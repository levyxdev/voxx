# 旁白文件是 voxx 唯一的输入输出契约

voxx 一次调用合成一整份旁白：读入 `{ language, lines: [{ id, text }] }`，为每个 Line 写出一个音频文件，再写回补全了 `audio` 和 `words` 的同一份旁白文件。这个格式和 CueTake 的 Narration（levyxdev/cuetake#7）一致，agent 可以直接把 voxx 的输出交给 `cuetake record --narration`，两个工具之间只靠文件交接，不互相调用，也没有常驻服务。格式由 voxx 自己定义，代码里不依赖 CueTake。

## Considered options

- **每句一次 CLI 调用。** 否决：每次都要重新加载几 GB 的模型，十几句的旁白要多花几分钟。
- **常驻服务（HTTP 或 `serve --stdio`）。** v0.1 不做：调用方都是 agent，一份旁白一次调用已经只加载一次模型，常驻进程带来的生命周期管理不值得。
- **对外暴露 `align`、`transcribe`、`batch` 等原子命令。** 否决：强制对齐、语音识别和批量合成都只是合成一份旁白的内部步骤。

## Consequences

- 改变旁白文件的字段要同时考虑 CueTake，属于跨仓库的变更。
- 单句重配也走同一个文件：指定 Line id 后只重新生成这些 Line，其他 Line 的音频不动。
- 一个 Line 永远由模型一次连续念完，不在 Line 内部拼接音频，保证听起来像人在说话。
