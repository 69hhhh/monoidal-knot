# 数学与表示约定

本文档记录会影响矩阵、braid word 和未来序列化格式的稳定约定。当前约定版本为 `1`。

## 范畴边界

第一版面向 strict linear pivotal ribbon category：

- tensor object 使用扁平 tensor word；
- unit object 是空 tensor word；
- 结合子和 unitors 不进入 AST；
- 双对偶严格识别为原对象；
- braiding、cup、cap 和 twist 保留为显式结构态射；
- 第一版所有结构态射都是偶态射。

这里的 strict 是内部表示约定，不声称用户给出的具体范畴在数学上字面严格。

## 矩阵与复合

- 向量表示为列向量。
- 对 `f: A -> B`，矩阵 `M_f` 的形状为 `dim(B) x dim(A)`。
- `f.then(g)` 表示先执行 `f`、再执行 `g`，即 `g compose f`。
- 因而 `M_(g compose f) = M_g @ M_f`。

所有 API、测试和错误信息都使用上述顺序；不会根据 NumPy、SymPy 或绘图工具的习惯自动翻转。

## Tensor basis

对象因子和 basis 指标都从左向右排列，最右指标变化最快。若

```text
basis(A) = (a0, a1)
basis(B) = (b0, b1, b2)
```

则

```text
basis(A tensor B) = (
    a0 tensor b0,
    a0 tensor b1,
    a0 tensor b2,
    a1 tensor b0,
    a1 tensor b1,
    a1 tensor b2,
)
```

在此约定下，`M_(f tensor g) = kronecker_product(M_f, M_g)`。

## Braid word

- strands 从左向右编号；生成元使用 1-based index。
- braid 图从上向下读取。
- `word=(a1, ..., an)` 按 tuple 顺序依次执行对应 crossing。
- `b1.then(b2)` 表示把 `b2` 接在 `b1` 下方，底层 word 直接拼接。
- 第一版不为 braid 定义含义容易混淆的 `*` 运算符。

正生成元 `sigma_i` 是第 `i` 根线越过第 `i+1` 根线，并映射到作用于相邻 tensor
因子的 `check_R`。负生成元映射到 `check_R` 的逆。即：

```text
sigma_i       -> check_R
sigma_i^(-1)  -> check_R^(-1)
```

上述代数映射是正负 crossing 的最终权威定义；图形渲染必须服从它。

## Cup、cap 与 dual

为避免不同教材对 left/right dual 的命名差异，公开文档和错误信息必须同时给出态射类型。
名称中的 `dual_left` 或 `dual_right` 表示 dual factor 在 tensor word 中的位置：

```text
ev_dual_left(A):       dual(A) tensor A -> I
coev_dual_left(A):     I -> dual(A) tensor A

ev_dual_right(A):      A tensor dual(A) -> I
coev_dual_right(A):    I -> A tensor dual(A)
```

它们的矩阵形状和 basis 顺序继续服从本文档前面的统一约定。具体矩阵数据由函子显式提供。

## Framed closure

- 开 braid 的矩阵求值与 closure 是不同操作。
- closure 默认使用用户明确提供的 categorical/quantum trace 数据。
- 缺少 trace 数据时必须报错，不得静默退化成 ordinary matrix trace。
- closure 保留 blackboard framing，不自动进行 writhe 修正。
- twist 只在 AST 中显式出现或用户显式请求 framing correction 时应用。

实现与报告必须区分 raw matrix evaluation、categorical framed closure 和经过额外条件验证、
归一化后的 ambient-isotopy invariant。

## Jones 示例：阶段 5 决定

阶段 0 不固定 Jones 示例的变量名、变量替换或归一化公式。阶段 5 可以同时支持 `A`、`q`、
`t` 等表示，但每个示例必须显式记录：

- 使用的 R 矩阵与 trace 数据；
- crossing 和 framing 约定；
- 主变量及变量之间的替换关系；
- writhe 或其他归一化因子；
- unknot 的归一化值；
- 返回的是 raw framed value 还是已验证、已归一化的不变量。

新增变量表示不得静默改变既有序列化数据的含义。

