# monoidal-knot adapter boundary

这里故意不包含 Python 包调用。未来适配器应：

- 将 `BraidDocument.topObjects` 和 `word` 映射为 `BraidMorphism`；
- 保留显式 `blackboard` framing；
- 在 planar diagram 尚未经过辫化或包尚未支持 planar tangle 时拒绝伪转换；
- 通过可选 HTTP 客户端连接求值服务，不让编辑器核心依赖后端。
