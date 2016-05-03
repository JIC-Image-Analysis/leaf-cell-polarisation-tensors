"""Basic webapp for editing tensors."""

import os.path
import argparse
import shutil

import PIL
from flask import Flask, render_template, url_for, request
from tensor import TensorManager

from utils import HERE

STATIC = os.path.join(HERE, "static")

app = Flask(__name__)


@app.route("/")
def index():
    im_fpath = os.path.join(STATIC, app.segmentation)
    im = PIL.Image.open(im_fpath)
    xdim, ydim = im.size
    tensors = [tensor_manager[i] for i in app.tensor_manager.identifiers]
    return render_template("template.html",
                           xdim=xdim,
                           ydim=ydim,
                           tensors=tensors,
                           cell_wall_fname=url_for("static", filename=app.wall_intensity),
                           marker_fname=url_for("static", filename=app.marker_intensity),
                           segmentation_fname=url_for("static", filename=app.segmentation))


@app.route("/inactivate_tensor/<int:tensor_id>", methods=["POST"])
def inactivate_tensor(tensor_id):
    if request.method == "POST":
        app.tensor_manager.inactivate_tensor(tensor_id)
        app.logger.debug("Inactivated tensor {:d}".format(tensor_id))
        return "Inactivated tensor {:d}\n".format(tensor_id)


@app.route("/update_marker/<int:tensor_id>/<float:y>/<float:x>", methods=["POST"])
def update_marker(tensor_id, y, x):
    if request.method == "POST":
        app.tensor_manager.update_marker(tensor_id, (y, x))
        app.logger.debug("Updated tensor {:d} marker to ({:.2f}, {:.2f})\n".format(tensor_id, y, x))
        return "Updated tensor {:d} marker to ({:.2f}, {:.2f})\n".format(tensor_id, y, x)


@app.route("/update_centroid/<int:tensor_id>/<float:y>/<float:x>", methods=["POST"])
def update_centroid(tensor_id, y, x):
    if request.method == "POST":
        app.tensor_manager.update_centroid(tensor_id, (y, x))
        app.logger.debug("Updated tensor {:d} centroid to ({:.2f}, {:.2f})\n".format(tensor_id, y, x))
        return "Updated tensor {:d} centroid to ({:.2f}, {:.2f})\n".format(tensor_id, y, x)


@app.route("/undo", methods=["POST"])
def undo():
    if request.method == "POST":
        return "{}\n".format(app.tensor_manager.undo())


@app.route("/redo", methods=["POST"])
def redo():
    if request.method == "POST":
        return "{}\n".format(app.tensor_manager.redo())


@app.route("/audit_log")
def audit_log():
    return render_template("audit_log.html",
                           tensor_manager=app.tensor_manager)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", help="input directory")
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        parser.error("No such directory {}".format(args.input_dir))

    for name in ["segmentation", "marker_intensity", "wall_intensity"]:
        fname = name + ".png"
        fpath = os.path.join(args.input_dir, fname)
        if not os.path.isfile(fpath):
            parser.error("No such file {}".format(fpath))
        shutil.copy(fpath, STATIC)
        setattr(app, name, fname)

    tensor_manager = TensorManager()
    with open(os.path.join(args.input_dir, "raw_tensors.txt")) as fh:
        tensor_manager.read_raw_tensors(fh)
    app.tensor_manager = tensor_manager

    app.run(debug=True)
