# monoidal-knot

`monoidal-knot` 是一个处于 pre-alpha 阶段的 Python 包，目标是对 braided monoidal / ribbon
category、R 矩阵和 framed braid closure 进行精确符号计算。

当前已完成阶段 1 的类型化范畴 AST 和阶段 2 的精确标量/Grassmann/矩阵基础层，尚未实现
紧凑 braid word、R 矩阵函子或矩阵求值器。
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
- 不可变 `ExactMatrix` 的加减、乘法、缩放、普通 Kronecker product 和偶元素检查。

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

这些命令验证包结构、阶段 0 约定、阶段 1 类型化 AST 和阶段 2 符号代数，不代表任何
R 矩阵、范畴关系或扭结不变量已经得到验证。
