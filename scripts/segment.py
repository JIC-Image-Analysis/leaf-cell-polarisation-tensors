"""Segment leaf into individual cells."""

import os.path
import argparse
import warnings

import numpy as np

from jicbioimage.core.image import MicroscopyCollection
from jicbioimage.core.transform import transformation
from jicbioimage.core.io import (
    FileBackend,
    DataManager,
    _md5_hexdigest_from_file,
    AutoWrite,
)

from jicbioimage.transform import (
    max_intensity_projection,
    remove_small_objects,
)

HERE = os.path.dirname(os.path.realpath(__file__))

# Suppress spurious scikit-image warnings.
warnings.filterwarnings("ignore", module="skimage.io._io")


def get_microscopy_collection(input_file):
    """Return microscopy collection from input file."""
    data_dir = os.path.abspath(os.path.join(HERE, "..", "data"))
    if not os.path.isdir(data_dir):
        raise(OSError("Data directory does not exist: {}".format(data_dir)))
    backend_dir = os.path.join(data_dir, 'unpacked')
    file_backend = FileBackend(backend_dir)
    data_manager = DataManager(file_backend)
    data_manager.load(input_file)

    md5_hex = _md5_hexdigest_from_file(input_file)
    manifest_path = os.path.join(backend_dir, md5_hex, "manifest.json")

    microscopy_collection = MicroscopyCollection()
    microscopy_collection.parse_manifest(manifest_path)
    return microscopy_collection


@transformation
def threshold_mean(image):
    """Return image thresholded using the mean."""
    return image > np.mean(image)


@transformation
def threshold_percentile(image, percentile):
    """Return image thresholded using the mean."""
    return image > np.percentile(image, percentile)


@transformation
def threshold_abs(image, threshold):
    """Return image thresholded using the mean."""
    return image > threshold


@transformation
def identity(image):
    return image


def segment_zslice(image):
    """Segment a zslice."""
    tmp_autowrite = AutoWrite.on
    AutoWrite.on = False
    image = identity(image)
    image = threshold_abs(image, 100)
    image = remove_small_objects(image, min_size=500)
    AutoWrite.on = tmp_autowrite
    return image


def preprocess_zstack(zstack_proxy_iterator, cutoff):
    """Select the pixels where the signal is."""
    raw = []
    zstack = []
    for i, proxy_image in enumerate(zstack_proxy_iterator):
        image = proxy_image.image
        segmented = segment_zslice(image)
        with open("z{:03d}.png".format(i), "wb") as fh:
            fh.write(segmented.png())
        with open("raw_z{:03d}.png".format(i), "wb") as fh:
            fh.write(image.png())
        raw.append(image)
        zstack.append(segmented)
    return np.dstack(raw), np.dstack(zstack)


def segment(zstack_proxy_iterator):
    """Return a segmented image."""
    raw, processed = preprocess_zstack(zstack_proxy_iterator, 90)
    image = max_intensity_projection(raw)
    image = max_intensity_projection(processed)

    return image


def main():
    """Run the analysis on an indivudual image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="Path to input tiff file")
    args = parser.parse_args()
    if not os.path.isfile(args.input_file):
        parser.error("No such file: {}".format(args.input_file))

    microscopy_collection = get_microscopy_collection(args.input_file)

    zstack_proxy_iterator = microscopy_collection.zstack_proxy_iterator(c=1)
    segment(zstack_proxy_iterator)

if __name__ == "__main__":
    main()
