"""Basic webapp for editing tensors."""

import os.path
import argparse
import shutil
import base64

import PIL
from flask import Flask, render_template, url_for, request
from tensor import TensorManager

from utils import HERE

STATIC = os.path.join(HERE, "static")

app = Flask(__name__)

AUDIT_LOG_FNAME = "audit.log"


def base64_from_fpath(fpath):
    """Return base64 string from fpath."""
    return base64.b64encode(open(fpath, "rb").read())


def write_audit_log():
    """Write the audit log to disk."""
    fpath = os.path.join(app.output_dir, AUDIT_LOG_FNAME)
    with open(fpath, "w") as fh:
        app.tensor_manager.write_audit_log(fh)


@app.route("/")
def index():
    tensors = [tensor_manager[i] for i in app.tensor_manager.identifiers]
    return render_template("template.html",
                           xdim=app.xdim,
                           ydim=app.ydim,
                           tensors=tensors,
                           cell_wall_image=app.wall_intensity,
                           marker_image=app.marker_intensity,
                           segmentation_image=app.segmentation)


@app.route("/inactivate_tensor/<int:tensor_id>", methods=["POST"])
def inactivate_tensor(tensor_id):
    if request.method == "POST":
        app.tensor_manager.inactivate_tensor(tensor_id)
        write_audit_log()
        app.logger.debug("Inactivated tensor {:d}".format(tensor_id))
        return "Inactivated tensor {:d}\n".format(tensor_id)


@app.route("/update_marker/<int:tensor_id>/<float:y>/<float:x>", methods=["POST"])
def update_marker(tensor_id, y, x):
    if request.method == "POST":
        app.tensor_manager.update_marker(tensor_id, (y, x))
        write_audit_log()
        app.logger.debug("Updated tensor {:d} marker to ({:.2f}, {:.2f})\n".format(tensor_id, y, x))
        return "Updated tensor {:d} marker to ({:.2f}, {:.2f})\n".format(tensor_id, y, x)


@app.route("/update_centroid/<int:tensor_id>/<float:y>/<float:x>", methods=["POST"])
def update_centroid(tensor_id, y, x):
    if request.method == "POST":
        app.tensor_manager.update_centroid(tensor_id, (y, x))
        write_audit_log()
        app.logger.debug("Updated tensor {:d} centroid to ({:.2f}, {:.2f})\n".format(tensor_id, y, x))
        return "Updated tensor {:d} centroid to ({:.2f}, {:.2f})\n".format(tensor_id, y, x)


@app.route("/undo", methods=["POST"])
def undo():
    if request.method == "POST":
        info =  "{}\n".format(app.tensor_manager.undo())
        write_audit_log()
        return info


@app.route("/redo", methods=["POST"])
def redo():
    if request.method == "POST":
        info =  "{}\n".format(app.tensor_manager.redo())
        write_audit_log()
        return info


@app.route("/audit_log")
def audit_log():
    return render_template("audit_log.html",
                           tensor_manager=app.tensor_manager)


@app.route("/csv", methods=["GET", "POST"])
def csv():
    return "\n".join(app.tensor_manager.csv)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", help="input directory")
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        parser.error("No such directory {}".format(args.input_dir))
    app.output_dir = args.input_dir

    for name in ["segmentation", "marker_intensity", "wall_intensity"]:
        fname = name + ".png"
        fpath = os.path.join(args.input_dir, fname)
        if not os.path.isfile(fpath):
            parser.error("No such file {}".format(fpath))
        setattr(app, name, base64_from_fpath(fpath))

    im_fpath = os.path.join(args.input_dir, fname)
    im = PIL.Image.open(im_fpath)
    xdim, ydim = im.size
    app.xdim = xdim
    app.ydim = ydim

    tensor_manager = TensorManager()

    fpath = os.path.join(args.input_dir, "raw_tensors.txt")
    if not os.path.isfile(fpath):
        parser.error("No such file {}".format(fpath))
    with open(fpath) as fh:
        tensor_manager.read_raw_tensors(fh)

    fpath = os.path.join(args.input_dir, AUDIT_LOG_FNAME)
    if os.path.isfile(fpath):
        with open(fpath) as fh:
            tensor_manager.apply_audit_log(fh)

    app.tensor_manager = tensor_manager

    app.run("0.0.0.0")
