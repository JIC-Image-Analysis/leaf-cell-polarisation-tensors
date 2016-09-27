import argparse

import numpy as np
import scipy.ndimage as nd
import PIL.Image

from jicbioimage.core.image import Image

from utils import get_microscopy_collection


def generate_surface_from_stack(stack):
    def _pre_blur(stack, sd):
        ydim, xdim, zdim = stack.shape
        pad_val = 5
        padding = pad_val * 2
        padded_stack = np.zeros((ydim + padding, xdim + padding, zdim + padding),
                                dtype=stack.dtype)
        start = pad_val
        end_add = pad_val
        padded_stack[start:ydim+end_add,
                     start:xdim+end_add,
                     start:zdim+end_add] = stack
        smoothed_stack = nd.gaussian_filter(padded_stack, sd)
        cropped_stack = smoothed_stack[start:ydim+end_add,
                                       start:xdim+end_add,
                                       start:zdim+end_add]
        return cropped_stack

    def _post_blur(surface, sd):
        return nd.gaussian_filter(surface, sd)

    # Turn pre blurring on/off by commenting out the line below.
    stack = _pre_blur(stack, (10, 10, 10))

    # Choose either one of the two methods below to generate the surface.
#   surface = percentile_surface_from_stack(stack, percentile=95, surface_blur_sd=10)
    surface = max_surface_from_stack(stack)

    # Turn post blurring on/off by commenting out the line below.
    surface = _post_blur(surface, (5, 5))

    return surface

def percentile_surface_from_stack(stack, percentile, surface_blur_sd):
    ydim, xdim, zdim = stack.shape
    cutoff = np.percentile(stack, percentile, axis=2)
    surface = np.zeros((ydim, xdim), dtype=np.uint8)
    for zi in range(zdim):
        mask = stack[:, :, zi] > cutoff
        not_done = surface == 0
        mask = mask * not_done
        surface[mask] = zi

    return surface


def max_surface_from_stack(stack):
    """Return a 2D image encoding a height map, generated from the input stack.
    The image is generated by first blurring the stack, then taking the z index
    of the brightest point for each X, Y location. The resultant surface is
    then smoothed with a gaussian filter.

    sd: standard deviation in each direction
    surface_blur_sd: standard deviation of smoothing applied to 2D surface."""
    ydim, xdim, zdim = stack.shape
    raw_surface = np.argmax(stack, 2)

    # There are two situations in which the raw surface could have a value
    # of zero. The maximum value could have been located in the first
    # z-slice (correct). The z-column contained only zeros (incorrect).
    # In the latter case we want the value of the raw surface to be at
    # the bottom of the projection (zdim - 1).
    positions_to_move_to_bottom = np.logical_and(raw_surface == 0,
                                                 stack[:, :, 0] == 0)
    raw_surface[positions_to_move_to_bottom] = zdim - 1
    return raw_surface


def projection_from_stack_and_surface(stack, surface, z_above=1, z_below=5, proj_method=np.mean):
    """Return a 2D projection of a 3D stack. The projection is obtained by
    using the elements of the 2D array surface as the Z index for each
    point in the plane."""

    projection = np.zeros(surface.shape, dtype=np.uint8)

    xdim, ydim, zdim = stack.shape
    for x in range(xdim):
        for y in range(ydim):
            z_index = surface[x, y]
            z_min = min(zdim - 1, max(0, z_index-z_above))
            z_max = max(1, min(zdim, z_index+z_below))
            value = proj_method(stack[x, y, z_min:z_max])
            projection[x, y] = value

    return projection.view(Image)


def save_image(filename, image):
    """Save the given image to a file."""

    with open(filename, 'wb') as f:
        f.write(image.png())


def generate_projections_from_microscope_image(input_file,
                                               wall_channel,
                                               marker_channel):
    """Generate and save projections generated from a stack loaded from the
    input microscopy file. These use a surface extracted from channel 2
    (assumed to be the cell wall channel) which is then used to determine
    projections of that channel, as well as the marker channel (assumed to
    be channel 0)."""

    collection = get_microscopy_collection(input_file)

    wall_stack = collection.zstack_array(s=0, c=wall_channel)
    marker_stack = collection.zstack_array(s=0, c=marker_channel)

    surface = generate_surface_from_stack(wall_stack)

    cell_wall_projection = projection_from_stack_and_surface(wall_stack,
                                                             surface,
                                                             proj_method=np.mean)
    marker_max_projection = projection_from_stack_and_surface(marker_stack,
                                                          surface,
                                                          proj_method=np.max)
    marker_mean_projection = projection_from_stack_and_surface(marker_stack,
                                                          surface,
                                                          proj_method=np.mean)

    save_image("wall.png", cell_wall_projection)
    save_image("marker_max.png", marker_max_projection)
    save_image("marker_mean.png", marker_mean_projection)
    pil_im = PIL.Image.fromarray(surface.astype(np.uint8))
    pil_im.save('surface.png')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help="Input microscope file.")
    parser.add_argument("-w", "--wall-channel",
                        default=1, type=int,
                        help="Wall channel (zero indexed)")
    parser.add_argument("-m", "--marker-channel",
                        default=0, type=int,
                        help="Marker channel (zero indexed)")

    args = parser.parse_args()

    generate_projections_from_microscope_image(args.input_file,
                                               args.wall_channel,
                                               args.marker_channel)


if __name__ == "__main__":
    main()
