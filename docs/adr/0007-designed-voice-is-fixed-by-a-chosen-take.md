# 设计音色先挑定一段音频，再由克隆模式照着念

VoxCPM2 这类模型能凭一段文字描述生成声音，但每生成一次都是一个新的人：同一个描述，换一句话或换一个 seed，声音就变了。一条旁白有十几句，必须是同一个人，所以设计音色分两步：先用描述生成几个 Design Take，它们念同一段试读稿，由用户试听挑一个；挑中的那个存成 Designed Voice 的参考录音，以后每句都由克隆模式照着它念。代价是多了一步试听挑选。

## Considered options

- **每句都带着描述直接生成。** 否决：句与句之间声音不同，`--line` 重念一句也可能变声。

## Consequences

- `narrate` 不用为 Designed Voice 另开一条路：它和 Cloned Voice 一样由克隆 Model 念，默认是第一个克隆 Model，`voice add --model` 和 `narrate --model` 照常可以换。
- Designed Voice 跟不跟随 `style`，和 Cloned Voice 一样由念它的克隆 Model 决定，不另立规则。
