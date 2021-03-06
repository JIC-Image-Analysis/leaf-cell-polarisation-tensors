"""Module for creating, storing and editing tensors."""

import os
import os.path
import copy
import json
import logging

from utils import marker_cell_identifier


class Tensor(object):
    """Class for managing individual tensors."""

    def __init__(self, tensor_id, centroid, marker, creation_type):
        self._data = dict(tensor_id=tensor_id,
                          centroid=list(centroid),
                          marker=list(marker),
                          creation_type=creation_type,
                          active=True)

    def __eq__(self, other):
        return self._data == other._data

    def __repr__(self):
        prefix = "<Tensor("
        suffix = ")>"
        info = []
        for key in Tensor.keys():
            info.append("{}={}".format(key, self._data[key]))
        return prefix + ", ".join(info) + suffix

    @staticmethod
    def keys():
        return ["tensor_id", "centroid", "marker", "creation_type", "active"]

    @staticmethod
    def extended_keys():
        return ["tensor_id", "centroid_row", "centroid_col", "marker_row", "marker_col", "creation_type", "active"]

    @staticmethod
    def from_json(line):
        """Create Tensor from json string."""
        d = json.loads(line)
        tensor = Tensor(tensor_id=d["tensor_id"],
                        centroid=list(d["centroid"]),
                        marker=list(d["marker"]),
                        creation_type=d["creation_type"])
        tensor._data["active"] = d["active"]
        return tensor

    @staticmethod
    def csv_header():
        return ",".join(Tensor.extended_keys())

    @property
    def csv_line(self):
        return ",".join([str(getattr(self, k)) for k in Tensor.extended_keys()])

    @property
    def json(self):
        return json.dumps(self._data)

    @property
    def tensor_id(self):
        """Return the tensor identifier."""
        return self._data["tensor_id"]

    @property
    def centroid(self):
        """Return the cell centroid position."""
        return self._data["centroid"]

    @property
    def centroid_row(self):
        """Return the cell centroid row."""
        return self._data["centroid"][0]

    @property
    def centroid_col(self):
        """Return the cell centroid column."""
        return self._data["centroid"][1]

    @property
    def marker(self):
        """Return the membrane marker position."""
        return self._data["marker"]

    @property
    def marker_row(self):
        """Return the membrane marker row."""
        return self._data["marker"][0]

    @property
    def marker_col(self):
        """Return the membrane marker column."""
        return self._data["marker"][1]

    @property
    def creation_type(self):
        """Return the creation type (automated/manual)."""
        return self._data["creation_type"]

    @property
    def active(self):
        """Return the active status of the tensor (True/False)."""
        return self._data["active"]

    def update(self, name, value):
        """Update a property of the tensor.

        :returns: json string describing update
        """
        self._data[name] = value
        d = dict(tensor_id=self.tensor_id, action="update")
        d[name] = value
        logging.debug(json.dumps(d))
        return json.dumps(d)


class Command(object):
    """Command class to enable undo/redo functionality."""

    def __init__(self, do_method, undo_method, do_args, undo_args):
        self.do_method = do_method
        self.do_args = do_args
        self.undo_method = undo_method
        self.undo_args = undo_args
        self.audit_log = None

    def do(self):
        """Execute a command."""
        self.audit_log = self.do_method(*self.do_args)
        return self.audit_log

    def undo(self):
        """Reverse the effect of a command."""
        return self.undo_method(*self.undo_args)


class TensorManager(dict):
    """Class for creating, storing and editing tensors."""

    def __init__(self):
        self.commands = []
        self.command_offset = 0

    def __eq__(self, other):
        if len(self) != len(other):
            return False
        for key, value in self.items():
            if key not in other:
                return False
            if not value == other[key]:
                return False
        return True

    @property
    def identifiers(self):
        """Return sorted list of identifiers."""
        ids = self.keys()
        return sorted(ids)

    @property
    def audit_log(self):
        """Return list of commands excluding undone ones."""
        num_commands = len(self.commands) + self.command_offset
        return [self.commands[i] for i in range(num_commands)]

    @property
    def csv(self):
        """Return list of csv lines."""
        lines = []
        lines.append(Tensor.csv_header())
        for tensor_id in self.identifiers:
            tensor = self[tensor_id]
            lines.append(tensor.csv_line)
        return lines

    def run_command(self, cmd):
        """Add command to command list and run it."""
        # Clip future if running a new command.
        if self.command_offset != 0:
            self.commands = self.commands[:self.command_offset]
            self.command_offset = 0

        # Add the command to the history and run it.
        self.commands.append(cmd)
        self.commands[-1].do()

    def undo(self):
        """Undo the last action."""
        logging.debug("Undoing...")
        # Command offset will be negative if we have already undone things.
        cmd_index = -1 + self.command_offset
        # Basic checking to ensure that there is something to undo.
        if len(self.commands) + cmd_index < 0:
            logging.debug("Nothing to undo...")
            return None

        info = self.commands[cmd_index].undo()
        self.command_offset -= 1
        return info

    def redo(self):
        """Redo the last action."""
        logging.debug("Redoing...")
        # Basic checking to ensure that there is something to redo.
        if self.command_offset >= 0:
            logging.debug("Nothing to redo...")
            return None
        cmd_index = self.command_offset
        info = self.commands[cmd_index].do()
        self.command_offset += 1
        return info

    def create_tensor(self, tensor_id, centroid, marker,
                      creation_type="automated"):
        """Create a tensor and store it.

        Not for manual editing.
        """
        self[tensor_id] = Tensor(tensor_id, centroid, marker, creation_type)
        d = copy.deepcopy(self[tensor_id]._data)
        d["action"] = "create"
        logging.debug(json.dumps(d))
        return json.dumps(d)

    def _delete_tensor(self, tensor_id):
        """Never call this directly."""
        d = dict(tensor_id=tensor_id, action="delete")
        del self[tensor_id]
        logging.debug(json.dumps(d))

    def add_tensor(self, centroid, marker):
        """Add a tensor manually.

        For manual editing with undo.
        """
        tensor_id = max(self.identifiers) + 1
        cmd = Command(do_method=self.create_tensor,
                      undo_method=self._delete_tensor,
                      do_args=[tensor_id, centroid, marker, "manual"],
                      undo_args=[tensor_id])
        self.run_command(cmd)
        return cmd.audit_log

    def inactivate_tensor(self, tensor_id):
        """Mark a tensor as inactive."""
        tensor = self[tensor_id]
        cmd = Command(do_method=tensor.update,
                      undo_method=tensor.update,
                      do_args=["active", False],
                      undo_args=["active", True])
        self.run_command(cmd)
        return cmd.audit_log

    def update_centroid(self, tensor_id, new_position):
        """Update the position of a centroid."""
        tensor = self[tensor_id]
        prev_position = tensor.centroid
        cmd = Command(do_method=tensor.update,
                      undo_method=tensor.update,
                      do_args=["centroid", list(new_position)],
                      undo_args=["centroid", prev_position])
        self.run_command(cmd)
        return cmd.audit_log

    def update_marker(self, tensor_id, new_position):
        """Update the position of a marker."""
        tensor = self[tensor_id]
        prev_position = tensor.marker
        cmd = Command(do_method=tensor.update,
                      undo_method=tensor.update,
                      do_args=["marker", list(new_position)],
                      undo_args=["marker", prev_position])
        self.run_command(cmd)
        return cmd.audit_log

    def read_raw_tensors(self, fh):
        """Read in raw tensors from file."""
        for line in fh:
            tensor = Tensor.from_json(line)
            self[tensor.tensor_id] = tensor

    def write_raw_tensors(self, fh):
        """Write out raw tensors to file."""
        for tensor_id in self.identifiers:
            tensor = self[tensor_id]
            if tensor.creation_type == "automated":
                fh.write("{}\n".format(tensor.json))

    def write_audit_log(self, fh):
        """Write out an audit log."""
        for cmd in self.audit_log:
            fh.write("{}\n".format(cmd.audit_log))

    def apply_json(self, line):
        """Apply a line of json."""
        d = json.loads(line)
        action = d.pop("action")
        if action == "update":
            tensor_id = d.pop("tensor_id")
            for key, value in d.items():
                self[tensor_id]._data[key] = value
        elif action == "create":
            tensor_id = d["tensor_id"]
            self[tensor_id] = Tensor.from_json(json.dumps(d))
        else:
            raise(RuntimeError)

    def apply_audit_log(self, fh):
        """Apply an audit log."""
        for json_line in fh:
            self.apply_json(json_line)


def get_tensors(cells, markers):
    """Return TensorManager instance."""
    tensor_manager = TensorManager()
    for tensor_id, marker_id in enumerate(markers.identifiers):
        m_region = markers.region_by_identifier(marker_id)
        marker_position = m_region.convex_hull.centroid
        cell_id = marker_cell_identifier(m_region, cells)
        if cell_id == 0:
            logging.debug("Skipping tensor from cell_id 0")
            continue
        c_region = cells.region_by_identifier(cell_id)
        centroid = c_region.centroid
        tensor_manager.create_tensor(tensor_id, centroid, marker_position)
    return tensor_manager


def test_overall_api():

    # Test the creation of a tensor.
    tensor_manager = TensorManager()
    tensor_manager.create_tensor(1, (0, 0), (3, 5))
    tensor1 = tensor_manager[1]
    assert isinstance(tensor1, Tensor)
    assert tensor1.tensor_id == 1
    assert tensor1.centroid == [0, 0]
    assert tensor1.marker == [3, 5]
    assert tensor1.creation_type == "automated"

    # Test inactivate tensor and undo/redo.
    assert tensor_manager.command_offset == 0
    assert tensor1.active is True
    tensor_manager.inactivate_tensor(1)
    assert tensor1.active is False
    tensor_manager.undo()
    assert tensor1.active is True

    # Test using undo when already nothing left to undo.
    assert tensor_manager.undo() is None

    assert tensor_manager.command_offset == -1
    tensor_manager.redo()
    assert tensor1.active is False
    assert tensor_manager.command_offset == 0

    # Test using redo when already at present.
    assert tensor_manager.redo() is None

    # Test update_centroid and undo/redo.
    tensor_manager.update_centroid(1, (1, 10))
    assert tensor1.centroid == [1, 10]
    tensor_manager.undo()
    assert tensor1.centroid == [0, 0]
    tensor_manager.redo()
    assert tensor1.centroid == [1, 10]

    # Test update_marker and undo/redo.
    tensor_manager.update_marker(1, (100, 8))
    assert tensor1.marker == [100, 8]
    tensor_manager.undo()
    assert tensor1.marker == [3, 5]
    tensor_manager.redo()
    assert tensor1.marker == [100, 8]

    # Test TensorManager.identifiers property.
    assert tensor_manager.identifiers == [1]
    tensor_manager.create_tensor(5, (4, 0), (7, 5))
    assert tensor_manager.identifiers == [1, 5]
    tensor_manager.create_tensor(2, (2, 8), (1, 6))
    assert tensor_manager.identifiers == [1, 2, 5]

    # Test add_tensor undo/redo.
    tensor_id = tensor_manager.add_tensor((3, 4), (5, 6))
    assert tensor_id == 6
    tensor = tensor_manager[tensor_id]
    assert tensor.tensor_id == tensor_id
    assert tensor.centroid == [3, 4]
    assert tensor.marker == [5, 6]
    assert tensor.creation_type == "manual"
    assert tensor_manager.identifiers == [1, 2, 5, 6]
    tensor_manager.undo()
    assert (6 in tensor_manager) is False
    assert tensor_manager.identifiers == [1, 2, 5]
    tensor_manager.redo()
    assert (6 in tensor_manager) is True
    assert tensor_manager.identifiers == [1, 2, 5, 6]

    # Test undo followed by new action and audit_log property.
    assert len(tensor_manager.commands) == 4
    assert len(tensor_manager.audit_log) == 4
    tensor_manager.undo()
    assert (6 in tensor_manager) is False
    tensor_manager.undo()
    assert len(tensor_manager.commands) == 4
    assert tensor_manager.command_offset == -2
    assert len(tensor_manager.audit_log) == 2
    assert tensor1.marker == [3, 5]
    assert tensor_manager[2].centroid == [2, 8]
    tensor_manager.update_centroid(2, (1, 1))
    assert tensor_manager[2].centroid == [1, 1]
    assert len(tensor_manager.commands) == 3
    assert tensor_manager.command_offset == 0

    # Manually create another tenor.
    tensor_id = tensor_manager.add_tensor((3, 4), (5, 6))

    # Test tensor json property and from_json static method.
    t1_copy = Tensor.from_json(tensor1.json)
    assert t1_copy == tensor1

    # Test writing of raw tensor data.
    raw_tensor_file = "test_raw_tensors.txt"
    with open(raw_tensor_file, "w") as fh:
        tensor_manager.write_raw_tensors(fh)
    assert os.path.isfile(raw_tensor_file)

    # Test writing of audit log.
    audit_file = "test_audit.log"
    with open(audit_file, "w") as fh:
        tensor_manager.write_audit_log(fh)
    assert os.path.isfile(audit_file)

    # Test recreation from an audit file.
    new_tensor_manager = TensorManager()
    with open(raw_tensor_file, "r") as fh:
        new_tensor_manager.read_raw_tensors(fh)
    with open(audit_file) as fh:
        new_tensor_manager.apply_audit_log(fh)
    assert tensor_manager == new_tensor_manager

    # Test csv functionality.
    assert Tensor.extended_keys() == ["tensor_id", "centroid_row", "centroid_col", "marker_row", "marker_col", "creation_type", "active"]
    assert Tensor.csv_header() == "tensor_id,centroid_row,centroid_col,marker_row,marker_col,creation_type,active"
    assert tensor1.csv_line == "1,1,10,3,5,automated,False"

    # Clean up.
    os.unlink(audit_file)
    os.unlink(raw_tensor_file)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_overall_api()
