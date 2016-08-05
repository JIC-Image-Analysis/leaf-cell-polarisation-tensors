"""Utility functions."""

import os.path
import logging

from jicbioimage.core.image import MicroscopyCollection
from jicbioimage.core.io import (
    FileBackend,
    DataManager,
    _md5_hexdigest_from_file,
)

HERE = os.path.dirname(os.path.realpath(__file__))


def get_data_manager():
    """Return a data manager."""
    data_dir = os.path.abspath(os.path.join(HERE, "..", "data"))
    if not os.path.isdir(data_dir):
        raise(OSError("Data directory does not exist: {}".format(data_dir)))
    backend_dir = os.path.join(data_dir, 'unpacked')
    file_backend = FileBackend(backend_dir)
    return DataManager(file_backend), backend_dir


def get_microscopy_collection_from_tiff(input_file):
    """Return microscopy collection from tiff file."""
    data_manager, backend_dir = get_data_manager()
    data_manager.load(input_file)

    md5_hex = _md5_hexdigest_from_file(input_file)
    manifest_path = os.path.join(backend_dir, md5_hex, "manifest.json")

    microscopy_collection = MicroscopyCollection()
    microscopy_collection.parse_manifest(manifest_path)
    return microscopy_collection


def get_microscopy_collection_from_org(input_file):
    """Return microscopy collection from microscopy file."""
    data_manager, _ = get_data_manager()
    return data_manager.load(input_file)


def get_microscopy_collection(input_file):
    name, ext = os.path.splitext(input_file)
    ext = ext.lower()
    if ext == '.tif' or ext == '.tiff':
        logging.debug("reading in a tif file")
        return get_microscopy_collection_from_tiff(input_file)
    else:
        logging.debug("reading in a microscopy file")
        return get_microscopy_collection_from_org(input_file)
