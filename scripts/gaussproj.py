import os
import argparse

import numpy as np
import scipy.ndimage as nd

from jicbioimage.core.image import Image

from jicbioimage.core.io import FileBackend
from jicbioimage.core.io import DataManager

HERE = os.path.dirname(__file__)
UNPACK = os.path.join(HERE, '..', 'data', 'unpack')
OUTPUT = os.path.join(HERE, '..', 'output')

def collection_from_filename(stack_filename):
    file_backend = FileBackend(UNPACK)
    data_manager = DataManager(file_backend)
    microscopy_collection = data_manager.load(stack_filename)

    return microscopy_collection

def generate_surface_from_stack(stack, sd=(10, 10, 10), surface_blur_sd=5):
    """Return a 2D image encoding a height map, generated from the input stack.
    The image is generated by first blurring the stack, then taking the z index
    of the brightest point for each X, Y location. The resultant surface is
    then smoothed with a gaussian filter.

    sd: standard deviation in each direction
    surface_blur_sd: standard deviation of smoothing applied to 2D surface."""


    smoothed_stack = nd.gaussian_filter(stack, sd)
    raw_surface = np.argmax(smoothed_stack, 2)
    smoothed_surface = nd.gaussian_filter(raw_surface, surface_blur_sd)

    return smoothed_surface

def projection_from_stack_and_surface(stack, surface, z_below=1, z_above=1):
    """Return a 2D projection of a 3D stack. The projection is obtained by
    using the elements of the 2D array surface as the Z index for each 
    point in the plane."""

    projection = np.zeros(surface.shape, dtype=np.uint8)

    xdim, ydim, zdim = stack.shape
    for x in range(xdim):
        for y in range(ydim):
            z_index = surface[x, y]
            z_min = max(0, z_index-z_below)
            z_max = min(zdim-1, z_index+z_above)
            value = np.mean(stack[x, y, z_min:z_max])
            projection[x, y] = value

    return projection.view(Image)

def save_image(filename, image):
    """Save the given image to a file."""

    with open(filename, 'wb') as f:
        f.write(image.png())

def generate_projections_from_microscope_image(input_file, cell_wall_file, 
                                                protein_file):
    """Generate and save projections generated from a stack loaded from the
    input microscopy file. These use a surface extracted from channel 2
    (assumed to be the cell wall channel) which is then used to determine
    projections of that channel, as well as the protein channel (assumed to
    be channel 0)."""

    cell_wall_channel = 2
    protein_channel = 0
    collection = collection_from_filename(input_file)

    cell_wall_stack = collection.zstack_array(s=0, c=cell_wall_channel)
    protein_stack = collection.zstack_array(s=0, c=protein_channel)

    surface = generate_surface_from_stack(cell_wall_stack)

    cell_wall_projection = projection_from_stack_and_surface(cell_wall_stack, 
                                                             surface, 5, 5)
    protein_projection = projection_from_stack_and_surface(protein_stack,
                                                            surface, 5, 5)


    save_image(cell_wall_file, cell_wall_projection)
    save_image(protein_file, protein_projection)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help="Input microscope file.")
    parser.add_argument('cell_wall_filename', help="Filename to use for output cell wall projection image.")
    parser.add_argument('protein_filename', help="Filename ot use for output protein channel projection image.")

    args = parser.parse_args()

    generate_projections_from_microscope_image(args.input_file, 
                                               args.cell_wall_filename,
                                               args.protein_filename)

if __name__ == "__main__":
    main()
