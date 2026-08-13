# monoidal-knot

`monoidal-knot` 是一个处于 pre-alpha 阶段的 Python 包，目标是对 braided monoidal / ribbon
category、R 矩阵和 framed braid closure 进行精确符号计算。

## Knot Atelier 前端

仓库中的 [`frontend`](frontend) 是一个独立的浏览器扭结图编辑器，支持平面 knot/link、
自由手绘转 Bézier、交叉点 over/under、colored braid word、项目 JSON 和 SVG 导出。它目前
不导入 Python 包，使用独立的 `knot-drawer/v1` schema；未来通过隔离的 adapter 接入
`BraidMorphism` 或 planar-tangle API。

当前已完成阶段 1 的类型化范畴 AST、阶段 2 的精确标量/Grassmann/矩阵基础层、阶段 3 的
紧凑 colored braid word、阶段 4 的 R 矩阵函子与精确求值器，以及阶段 5 的 homogeneous
R/trace 验证链和第一个完整 Jones 示例，并完成阶段 6 的教程及可复现实验 JSON。
现阶段可用的公共能力包括：

- 基础异常层级；
- 四态验证结果 `PASSED`、`FAILED`、`UNKNOWN`、`SKIPPED`；
- 已版本化的默认矩阵、tensor basis 和 braid word 约定；
- 多对象、unit、chosen pivotal dual 和规范化 tensor word；
- 任意 domain/codomain 的用户自定义 typed coupon；
- identity、compose、tensor、正负 colored braiding、cup、cap 和 twist；
- 构造时 domain/codomain 检查，以及不可变、可哈希的 AST。
- 普通交换符号与精确有理系数的 `ScalarExpr` 薄封装；
- 显式 `GrassmannAlgebra` 注册表、bitset 单项式、反交换和幂零运算；
- parity 检测、有限幂零逆元、整数幂和精确指数；
- 不可变 `ExactMatrix` 的加减、乘法、缩放、普通 Kronecker product、精确逆、迹和偶元素检查；
- 以整数 tuple 表示的 `BraidMorphism`，包括严格索引验证、identity、复合、inverse 和 writhe；
- 根据每一步实际颜色顺序把 braid word 展开为一般 `Morphism` AST；
- 检查顶部/底部颜色兼容性的 blackboard `FramedClosure` 抽象表示；
- 显式区分 `check_R` 与 quantum R 输入的 `RMatrixFunctor`；
- 通用 Morphism AST 和紧凑 braid word 的两条精确矩阵求值路径；
- 显式 ordinary trace、quantum trace、cup/cap/twist/coupon 映射和 `I -> I` 标量提取。
- R 尺寸、偶性、可逆性、braid-form 与 quantum-form Yang--Baxter 精确验证；
- enhanced Yang--Baxter trace 权重的交换性及正负 Markov 稳定化验证；
- 明确区分 `raw_evaluation` 与 `verified_invariant` 的闭合求值结果。

```python
from monoidal_knot import CategorySpec, CrossingSign

C = CategorySpec("experiment")
V = C.object("V")
W = C.object("W")

coupon = C.coupon("merge", V.tensor(W), V)
crossing = C.braiding(V, W, sign=CrossingSign.NEGATIVE)

assert crossing.dom == V.tensor(W)
assert crossing.cod == W.tensor(V)
assert C.identity(V.tensor(W)).then(coupon) == coupon
```

这里的相等是规范化后的**语法相等**，尚不自动应用 braid relation、snake identity 或
一般 string-diagram 重写。抽象态射 AST 不提供 `Add`、`Scale` 或标量态射；线性运算只在
符号矩阵层发生。

## Braid word 与 framed closure

```python
from monoidal_knot import BraidMorphism, CategorySpec

C = CategorySpec("braid-experiment")
V = C.object("V")

b = BraidMorphism(V.tensor_power(3), word=(1, -2, 1))
expanded = b.expand()
closure = b.close()

assert expanded.dom == b.dom
assert expanded.cod == b.cod
assert b.inverse().inverse() == b
assert closure.writhe == 1
```

生成元使用 1-based index，并按 tuple 顺序从上到下执行；第一版不支持字符串 braid 语法。
`FramedClosure` 只记录 blackboard-framed closure 结构，不自动进行 writhe 修正。求值时必须
显式提供 `QuantumTrace`；程序不会把 ordinary trace 静默当作 categorical closure，也不会因
求值得到一个标量就声称 Yang--Baxter 方程或扭结不变量条件已经验证。

## R 矩阵函子与精确求值

```python
from monoidal_knot import (
    BraidMorphism,
    CategorySpec,
    ExactMatrix,
    QuantumTrace,
    RMatrixFunctor,
    RMatrixSpec,
    Symbol,
)

C = CategorySpec("r-matrix-experiment")
V = C.object("V")
q = Symbol("q")

# check_R is the tensor-factor swap on a two-dimensional V.
check_R = ExactMatrix([
    [1, 0, 0, 0],
    [0, 0, 1, 0],
    [0, 1, 0, 0],
    [0, 0, 0, 1],
])

model = RMatrixFunctor(
    source=C,
    object_map={V: 2},
    r_matrices={(V, V): RMatrixSpec(check_R, convention="check")},
    trace_data=QuantumTrace(weights={V: ExactMatrix([[q, 0], [0, 1]])}),
)

b = BraidMorphism(V.tensor_power(3), word=(1, -2, 1))
assert model.evaluate_braid(b) == model.evaluate(b.expand())

raw_matrix = model.evaluate_braid(b)
raw_framed_value = model.close(b.close())
```

若输入的是满足 quantum Yang--Baxter 约定的 `R`，使用 `convention="quantum"`；函子按
`check_R = P @ R` 和已固定的 tensor basis 顺序进行转换。负 colored crossing `(A, B)` 按
AST 类型约定使用 `check_R[(B, A)].inverse()`。

阶段 4 的构造器检查维数、矩阵形状和偶性，求值保持 `ScalarExpr`/`ExactMatrix` 的精确符号
形式。`model.close(...)` 仍只返回 raw framed value；阶段 5 新增的 `model.verify()` 和
`model.evaluate_invariant(...)` 才执行完整验证。若任何必需检查失败或缺失，后者的
`normalized_value` 为 `None`，分类保持 `raw_evaluation`。

如果实验只关心 Yang--Baxter 方程，不需要不变量证书，可以使用轻量入口：

```python
ybe_report = model.verify_yang_baxter()       # 单生成对象时自动选择
ybe_report = model.verify_yang_baxter(V)      # 多生成对象时显式选择 homogeneous R(V,V)

assert ybe_report.verified
```

该入口只精确检查 braid-form YBE，以及由 `R = P @ check_R` 得到的 quantum-form YBE。
它不要求 R 可逆，也不要求 trace、Markov 参数或 framing normalization。因而通过只表示
“所选 homogeneous R 满足 YBE”，不表示它给出了 braid-group 表示或扭结不变量。需要后一
结论时仍须使用 `model.verify()`；需要归一化闭合值时使用 `model.evaluate_invariant(...)`。

## 完整 Jones 示例

[examples/jones_r_matrix.py](examples/jones_r_matrix.py) 使用二维 homogeneous `check_R`：

```text
check_R = [[q, 0, 0, 0],
           [0, 0, 1, 0],
           [0, 1, q-q^-1, 0],
           [0, 0, 0, q]]
mu = diag(q, q^-1)
```

显式 Markov 参数为 `alpha=q^2`、`beta=1`，总缩放为 `(q+q^-1)^-1`。对 `n` 股闭辫
`b`，writhe 为 `w`，示例返回

```text
V(b-hat) = (q+q^-1)^-1 q^(-2w) Tr(mu^tensor-n rho(b)).
```

因此 unknot 为 `1`，二分支 unlink 为 `q+q^-1`，正 Hopf link 为 `q^-1+q^-5`；右手
trefoil（闭合 `sigma_1^3`）为 `q^-2+q^-6-q^-8`。令 `t=q^-2`，后者就是
`t+t^3-t^4`。这些等式由测试直接以精确符号形式核对；示例运行命令：

```powershell
.venv\Scripts\python examples\jones_r_matrix.py
```

这里 raw trace 是 blackboard-framed evaluation；只有在 R、两种 YBE、trace 权重和正负
Markov 稳定化全部通过后，才应用 writhe/股数/总缩放并标记为 `verified_invariant`。当前完整
证书限于单对象 homogeneous R；一般多颜色系统仍保持 raw evaluation 状态。

## 精确 Grassmann 标量和矩阵

```python
from monoidal_knot import ExactMatrix, GrassmannAlgebra, Parity, Symbol

q = Symbol("q")
G = GrassmannAlgebra("experiment-scalars")
theta1, theta2 = G.symbols("theta1", "theta2")

assert theta1 * theta2 == -(theta2 * theta1)
assert theta1**2 == 0
assert (q + theta1 * theta2).parity is Parity.EVEN
assert (q + theta1).parity is Parity.MIXED
assert (1 + theta1 * theta2).inverse() == 1 - theta1 * theta2

matrix = ExactMatrix([[q, theta1 * theta2], [0, 1]])
matrix.require_even_entries(context="check_R")
assert matrix @ ExactMatrix.identity(2) == matrix
```

Grassmann 代数必须显式创建。不同 `GrassmannAlgebra` 实例不会因为 ID 或生成元同名而自动
合并。矩阵 tensor 当前使用普通 Kronecker product；graded basis 和 Koszul 符号留待未来
supercategory 扩展。

数学与表示约定见 [CONVENTIONS.md](CONVENTIONS.md)。后续实现以 [PLAN.md](PLAN.md) 为路线图。

## 自定义 R 与可复现实验

完整的入门程序见 [examples/custom_r_experiment.py](examples/custom_r_experiment.py)。它依次声明
范畴和对象、输入带明确 `check` convention 的 R 矩阵、设置 quantum trace、计算 framed
closure、检查完整验证报告，最后把 R、braid word、trace 数据、raw/normalized 值和每项验证
状态写入 `custom-r-experiment.json`：

```powershell
.venv\Scripts\python examples\custom_r_experiment.py
```

JSON 顶层包含 `schema="monoidal-knot"` 和整数 `version`。公共函数 `dumps`/`loads` 用于文本，
`save`/`load` 用于 UTF-8 文件；未知 schema 版本会被拒绝，而不会被静默误读。支持
`CategorySpec`、`ObjectExpr`、完整 `Morphism` AST、`BraidMorphism`、精确标量/矩阵、R/trace
配置和 `ExperimentRecord`。验证证据在实验记录中作为便于审计的显示文本保存；加载后的报告
保留 key、四态 status、summary、required 和 evidence 文本。

另外两个可直接运行的诊断教程是：

- [examples/grassmann_even_matrix.py](examples/grassmann_even_matrix.py)：构造含 `theta*eta` 的偶矩阵元并精确求逆；
- [examples/convention_diagnostics.py](examples/convention_diagnostics.py)：诊断非法标签，并展示把 `check_R` 错标成 quantum R 后的语义偏差。

`convention` 不能仅靠 YBE 是否通过来推断：错误解释后的矩阵仍可能满足 YBE。应先明确用户
输入是否已经包含 tensor-factor swap，再把单个 braid 生成元的求值与预期算子作精确比较。
若输入是 braid operator，应声明 `convention="check"`；未交换的 quantum R 才声明为
`"quantum"`。

## 环境要求

- Python 3.12 或更高版本；
- SymPy 1.14 或更高、2.0 以下版本。

## Windows PowerShell 开发环境

以下命令不需要激活虚拟环境，因此不会受到 PowerShell execution policy 的影响：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]"
```

## 验证命令

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check src tests
.venv\Scripts\python -m ruff format --check src tests
.venv\Scripts\python -m mypy src
.venv\Scripts\python -c "import monoidal_knot; print(monoidal_knot.__version__)"
```

这些命令验证包结构、阶段 0 约定、类型化 AST、符号代数、braid 结构、阶段 4 精确求值和
阶段 5 homogeneous invariant 证书。Jones 示例通过不代表任意用户 R、一般多颜色 YBE 系统
或一般范畴关系已经得到验证；每个模型都必须检查自己的 `ValidationReport`。
