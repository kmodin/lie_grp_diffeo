"""Definitions of abstract actions with Lie groups."""

# Imports for common Python 2/3 codebase
from __future__ import print_function, division, absolute_import
from future import standard_library
standard_library.install_aliases()

import odl
from numbers import Integral


__all__ = ('LieAction', 'ProductSpaceAction', 'IdentityAction')


class LieAction(object):

    """Action of a lie group on some set."""

    def __init__(self, lie_group, domain):
        self.lie_group = lie_group
        self.domain = domain

    def action(self, lie_grp_element):
        """Return the action, an odl.Operator associated with lie_grp_element.
        """
        raise NotImplementedError('abstract method')

    def inf_action(self, lie_grp_element):
        """Return the infinitesimal action, an odl.Operator associated with
        ``lie_grp_element``.
        """
        raise NotImplementedError('abstract method')

    def momentum_map(self, v, m):
        """The momentum map corresponding to the infinitesimal action.
        Returns a `lie_group.associated_algebra` object associated with 
        base point ``v`` and momentum ``m``.
        """
        raise NotImplementedError('abstract method')


class ProductSpaceAction(LieAction):

    """Action on a product space as defined by several "sub-actions"."""

    def __init__(self, *actions):

        # Allow ProductSpaceAction(action, 3) style syntax.
        if (len(actions) == 2 and
                isinstance(actions[0], LieAction) and
                isinstance(actions[1], Integral)):
            actions = [actions[0]] * actions[1]

        self.lie_group = actions[0].lie_group
        self.domain = odl.ProductSpace(*[ac.domain for ac in actions])
        self.actions = actions
        assert all(ac.lie_group == actions[0].lie_group for ac in actions)

    def action(self, lie_grp_element):
        assert lie_grp_element in self.lie_group
        subops = [ac.action(lie_grp_element) for ac in self.actions]
        return odl.DiagonalOperator(*subops)

    def inf_action(self, lie_alg_element):
        assert lie_alg_element in self.lie_group.associated_algebra
        subops = [ac.inf_action(lie_alg_element) for ac in self.actions]
        return odl.DiagonalOperator(*subops)

    def momentum_map(self, v, m):
        assert v in self.domain
        assert m in self.domain
        return sum((ac.momentum_map(vi, mi)
                    for ac, vi, mi in zip(self.actions, v, m)),
                   self.lie_group.associated_algebra.zero())


def IdentityAction(LieAction):

    """The action that maps any element to itself."""

    def action(self, lie_grp_element):
        assert lie_grp_element in self.lie_group
        return odl.IdentityOperator(self.domain)

    def inf_action(self, lie_alg_element):
        assert lie_alg_element in self.lie_group.associated_algebra
        return odl.ZeroOperator(self.domain)

    def momentum_map(self, v, m):
        assert v in self.domain
        assert m in self.domain
        return self.lie_group.associated_algebra.zero()
