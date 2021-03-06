import lie_group_diffeo as lgd
import odl
import numpy as np

# linear interpolation has boundary problems.
space = odl.uniform_discr([-1, -1], [1, 1], [200, 200], interp='linear')

if 0:
    transform = odl.deform.LinDeformFixedDisp(
        space.tangent_bundle.element([lambda x: x[0] * 0.3 + x[1] * 0.2,
                                      lambda x: x[0] * 0.1 + x[1] * 0.3]))
else:
    theta = 0.3
    transform = odl.deform.LinDeformFixedDisp(
        space.tangent_bundle.element([lambda x: (np.cos(theta) - 1) * x[0] + np.sin(theta) * x[1],
                                      lambda x: -np.sin(theta) * x[0] + (np.cos(theta) - 1) * x[1]]))

# Make a parallel beam geometry with flat detector
angle_partition = odl.uniform_partition(0, np.pi, 10)
detector_partition = odl.uniform_partition(-2, 2, 300)
geometry = odl.tomo.Parallel2dGeometry(angle_partition, detector_partition)
ray_trafo = odl.tomo.RayTransform(space, geometry, impl='astra_cuda')

# Create template and target
template = odl.phantom.shepp_logan(space, modified=True)
target = transform(template)
data = ray_trafo(target)

# Define data matching functional
data_matching = odl.solvers.L2NormSquared(ray_trafo.range).translated(data)
data_matching = data_matching * ray_trafo  # compose from the right

# Define the lie group to use.
lie_grp_type = 'rigid'
if lie_grp_type == 'gln':
    lie_grp = lgd.GLn(space.ndim)
    deform_action = lgd.MatrixImageAction(lie_grp, space)
elif lie_grp_type == 'son':
    lie_grp = lgd.SOn(space.ndim)
    deform_action = lgd.MatrixImageAction(lie_grp, space)
elif lie_grp_type == 'sln':
    lie_grp = lgd.SLn(space.ndim)
    deform_action = lgd.MatrixImageAction(lie_grp, space)
elif lie_grp_type == 'affine':
    lie_grp = lgd.AffineGroup(space.ndim)
    deform_action = lgd.MatrixImageAffineAction(lie_grp, space)
elif lie_grp_type == 'rigid':
    lie_grp = lgd.EuclideanGroup(space.ndim)
    deform_action = lgd.MatrixImageAffineAction(lie_grp, space)
else:
    assert False

# Define what regularizer to use
regularizer = 'point'
if regularizer == 'image':
    # Create set of all points in space
    W = space.tangent_bundle
    w = W.element(space.points().T)

    # Create regularizing functional
    regularizer = 0.1 * odl.solvers.L2NormSquared(W).translated(w)

    # Create action
    regularizer_action = lgd.ProductSpaceAction(deform_action, W.size)
elif regularizer == 'point':
    W = odl.ProductSpace(odl.rn(space.ndim), 3)
    w = W.element([[0, 0],
                   [0, 1],
                   [1, 0]])

    # Create regularizing functional
    regularizer = 0.01 * odl.solvers.L2NormSquared(W).translated(w)

    # Create action
    if lie_grp_type == 'affine' or lie_grp_type == 'rigid':
        point_action = lgd.MatrixVectorAffineAction(lie_grp, W[0])
    else:
        point_action = lgd.MatrixVectorAction(lie_grp, W[0])
    regularizer_action = lgd.ProductSpaceAction(point_action, W.size)
elif regularizer == 'determinant':
    W = odl.rn(1)
    w = W.element([1])

    # Create regularizing functional
    regularizer = 0.2 * odl.solvers.L2NormSquared(W).translated(w)

    # Create action
    regularizer_action = lgd.MatrixDeterminantAction(lie_grp, W)
else:
    assert False

# Initial guess
g = lie_grp.identity

# Combine action and functional into single object.
action = lgd.ProductSpaceAction(deform_action, regularizer_action)
x = action.domain.element([template, w]).copy()
f = odl.solvers.SeparableSum(data_matching, regularizer)

# Show some results, reuse the plot
template.show('template')
target.show('target')

# Create callback that displays the current iterate and prints the function
# value
callback = odl.solvers.CallbackShow(lie_grp_type, display_step=10, indices=0)
callback &= odl.solvers.CallbackPrint(f)

# Solve via gradient flow
lgd.gradient_flow_solver(x, f, g, action,
                         niter=200, line_search=0.02, callback=callback)
