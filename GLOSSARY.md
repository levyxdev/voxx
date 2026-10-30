# voxx

voxx 是只给 agent 用的本地语音工具：把 agent 写好的旁白逐句念出来，交回音频和词级时间戳。术语与 CueTake 共用的部分保持同名。

## Language

### 旁白

**Narration（旁白）**:
一组同一种语言、按顺序排列的 Line，是 voxx 一次合成的输入，也是它交回的清单。
_Avoid_: script, 文案文件, 口播稿

**Line（句子）**:
旁白中有唯一 id 的一段文字，一次连续念完，对应一个音频文件。
_Avoid_: segment, 段落, sentence

**Word Timing（词级时间戳）**:
Line 的音频里每个词（中文为字）开始和结束的时刻，相对该 Line 音频的起点。
_Avoid_: alignment, 时间轴, 时间

### 音色

**Voice（音色）**:
念一个 Line 时用的声音身份，要么是 Preset Voice，要么是 Cloned Voice。
_Avoid_: speaker, 声音, 角色

**Preset Voice（预设音色）**:
模型自带、按名字选用的音色。
_Avoid_: built-in speaker, 内置声音

**Cloned Voice（克隆音色）**:
从一段参考录音得到的音色。
_Avoid_: custom voice, 声音档案

**Reference Recording（参考录音）**:
用来得到 Cloned Voice 的那段真人录音。
_Avoid_: prompt audio, ref, 样本

### 模型

**Model（模型）**:
voxx 注册表里登记的一个可下载的 TTS、对齐或听写模型，固定到一个上游版本，带有已核实的权重许可证。
_Avoid_: checkpoint, 权重

**Capability（能力）**:
一个 Model 能做的事：念 Preset Voice（preset_voice）、克隆（clone）、对齐（align）或听写（transcribe）。
_Avoid_: feature, task, 功能

**Engine（引擎）**:
实际加载并运行 Model 的推理库，一个 Engine 可以运行多个 Model。
_Avoid_: backend, runtime, 框架
