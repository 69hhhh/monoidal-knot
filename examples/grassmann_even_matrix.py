"""An R-shaped matrix whose entries are even Grassmann expressions."""

from monoidal_knot import ExactMatrix, GrassmannAlgebra

algebra = GrassmannAlgebra("tutorial")
theta, eta = algebra.symbols("theta", "eta")
matrix = ExactMatrix([[1 + theta * eta, 0], [0, 1 - theta * eta]])
matrix.require_even_entries(context="tutorial matrix")
print(matrix)
print(f"inverse={matrix.inverse()}")
