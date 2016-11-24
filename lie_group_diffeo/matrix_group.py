import odl
import numpy as np
import scipy as sp
from lie_group import LieGroup, LieGroupElement, LieAlgebra, LieAlgebraElement
from action import LieAction


__all__ = ('GLn', 'SOn', 'MatrixVectorAction', 'MatrixImageAction')


class MatrixGroup(LieGroup):
    def __init__(self, size):
        self.size = size

    def element(self, array=None):
        """Create element from ``array``."""
        if array is None:
            return self.identity
        else:
            return self.element_type(self, array)

    @property
    def identity(self):
        return self.element(np.eye(self.size))

    def __eq__(self, other):
        return ((isinstance(self, type(other)) or
                 isinstance(other, type(self))) and
                self.size == other.size)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.size)


class MatrixGroupElement(LieGroupElement):
    def __init__(self, lie_group, arr):
        LieGroupElement.__init__(self, lie_group)
        self.arr = np.asarray(arr, dtype=float)

    def compose(self, other):
        return self.lie_group.element(self.arr.dot(other.arr))

    def __repr__(self):
        return '{!r}.element({!r})'.format(self.lie_group, self.arr)


class MatrixAlgebra(LieAlgebra):
    def __init__(self, lie_group):
        LieAlgebra.__init__(self, lie_group=lie_group)

    def project(self, array):
        """Project array on the algebra."""
        raise NotImplementedError('abstract method')

    @property
    def size(self):
        return self.lie_group.size

    def _lincomb(self, a, x1, b, x2, out):
        out.arr[:] = a * x1.arr + b * x2.arr

    def _inner(self, x1, x2):
        """Frobenious inner product."""
        return np.trace(x1.arr.T.dot(x2.arr))

    def one(self):
        return self.element(np.eye(self.size))

    def zero(self):
        return self.element(np.zeros([self.size, self.size]))

    def element(self, array=None):
        if array is None:
            return self.zero()
        else:
            return self.element_type(self, self.project(array))

    def exp(self, el):
        """Exponential map via matrix exponential."""
        return self.lie_group.element(sp.linalg.expm(el.arr))

    def __eq__(self, other):
        return (isinstance(other, MatrixAlgebra) and
                self.lie_group == other.lie_group)


class MatrixAlgebraElement(LieAlgebraElement):
    def __init__(self, lie_group, arr):
        LieAlgebraElement.__init__(self, lie_group)
        self.arr = np.asarray(arr, dtype=float)

    def __repr__(self):
        return '{!r}.element({!r})'.format(self.space, self.arr)


class GLn(MatrixGroup):
    @property
    def associated_algebra(self):
        return GLnAlgebra(self)

    @property
    def element_type(self):
        return GLnElement


class GLnElement(MatrixGroupElement):
    pass


class GLnAlgebra(MatrixAlgebra):
    @property
    def element_type(self):
        return GLnAlgebraElement

    def project(self, array):
        """Project array on the algebra."""
        return array


class GLnAlgebraElement(MatrixAlgebraElement):
    pass


class SOn(MatrixGroup):
    @property
    def associated_algebra(self):
        return SOnAlgebra(self)

    @property
    def element_type(self):
        return SOnElement


class SOnElement(MatrixGroupElement):
    pass


class SOnAlgebra(MatrixAlgebra):
    @property
    def element_type(self):
        return SOnAlgebraElement

    def project(self, array):
        return array - array.T


class SOnAlgebraElement(MatrixAlgebraElement):
    pass


class MatrixVectorAction(LieAction):
    """Action by matrix vector product."""

    def __init__(self, lie_group, domain):
        LieAction.__init__(self, lie_group, domain)
        assert lie_group.size == domain.size

    def action(self, lie_grp_element):
        return odl.MatVecOperator(lie_grp_element.arr,
                                  self.domain, self.domain)

    def inf_action(self, lie_grp_element):
        return odl.MatVecOperator(lie_grp_element.arr,
                                  self.domain, self.domain)

    def inf_action_adj(self, v, m):
        return self.lie_group.associated_algebra.element(np.outer(m, v))


class MatrixImageAction(LieAction):
    """Action on image via coordinate transformation."""

    def __init__(self, lie_group, domain, gradient=None):
        LieAction.__init__(self, lie_group, domain)
        assert lie_group.size == domain.ndim
        if gradient is None:
            self.gradient = odl.Gradient(self.domain)
        else:
            self.gradient = gradient

    def action(self, lie_grp_element):
        pts = self.domain.points()
        deformed_pts = lie_grp_element.arr.dot(pts.T) - pts.T
        deformed_pts = self.domain.tangent_bundle.element(deformed_pts)
        return odl.deform.LinDeformFixedDisp(deformed_pts)

    def inf_action(self, lie_grp_element):
        pts = self.domain.points()
        deformed_pts = lie_grp_element.arr.dot(pts.T) - pts.T
        deformed_pts = self.domain.tangent_bundle.element(deformed_pts)
        pointwise_inner = odl.PointwiseInner(self.gradient.range, deformed_pts)
        return pointwise_inner * self.gradient

    def inf_action_adj(self, v, m):
        size = self.lie_group.size
        pts = self.domain.tangent_bundle.element(self.domain.points().T)
        gradv = self.gradient(v)
        result = np.zeros([size, size])
        for i in range(size):
            for j in range(size):
                result[i, j] = m.inner(gradv[i] * pts[j])

        return self.lie_group.associated_algebra.element(result)
