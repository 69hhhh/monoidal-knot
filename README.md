# monoidal-knot

`monoidal-knot` 是一个处于 pre-alpha 阶段的 Python 包，目标是对 braided monoidal / ribbon
category、R 矩阵和 framed braid closure 进行精确符号计算。

当前只完成项目骨架与基础约定，尚未实现对象、态射、braid 或矩阵求值。现阶段可用的公共类型只有：

- 基础异常层级；
- 四态验证结果 `PASSED`、`FAILED`、`UNKNOWN`、`SKIPPED`；
- 已版本化的默认矩阵、tensor basis 和 braid word 约定。

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

这些命令只验证包结构、类型和阶段 0 的约定，不代表任何 R 矩阵或扭结不变量已经得到验证。
