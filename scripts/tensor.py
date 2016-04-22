"""Module for creating, storing and editing tensors."""

import os
import os.path
import copy
import json
import logging
logging.basicConfig(level=logging.DEBUG)


class Tensor(object):
    """Class for managing individual tensors."""

    def __init__(self, identifier, centroid, marker, creation_type):
        self._data = dict(identifier=identifier,
                          centroid=list(centroid),
                          marker=list(marker),
                          creation_type=creation_type,
                          active=True)

    def __eq__(self, other):
        return self._data == other._data

    def __repr__(self):
        return "<Tensor({identifier:}, {centroid:}, {marker:}, {creation_type:}, {active:})>".format(**self._data)

    @staticmethod
    def from_json(line):
        """Create Tensor from json string."""
        d = json.loads(line)
        tensor =  Tensor(identifier=d["identifier"],
                         centroid=list(d["centroid"]),
                         marker=list(d["marker"]),
                         creation_type=d["creation_type"])
        tensor._data["active"] = d["active"]
        return tensor

    @property
    def identifier(self):
        """Return the tensor identifier."""
        return self._data["identifier"]

    @property
    def centroid(self):
        """Return the cell centroid position."""
        return self._data["centroid"]

    @property
    def marker(self):
        """Return the membrane marker position."""
        return self._data["marker"]

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
        d = dict(identifier=self.identifier, action="update")
        d[name] = value
        logging.info(json.dumps(d))
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


    def undo(self):
        """Reverse the effect of a command."""
        self.undo_method(*self.undo_args)


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

        self.commands[cmd_index].undo()
        self.command_offset -= 1
        return self.command_offset

    def redo(self):
        """Redo the last action."""
        logging.debug("Redoing...")
        # Basic checking to ensure that there is something to redo.
        if self.command_offset >= 0:
            logging.debug("Nothing to redo...")
            return None
        cmd_index = self.command_offset
        self.commands[cmd_index].do()
        self.command_offset += 1
        return self.command_offset

    def create_tensor(self, identifier, centroid, marker, creation_type="automated"):
        """Create a tensor and store it.

        Not for manual editing.
        """
        self[identifier] = Tensor(identifier, centroid, marker, creation_type)
        d = copy.deepcopy(self[identifier]._data)
        d["action"] = "create"
        logging.info(json.dumps(d))
        return json.dumps(d)

    def _delete_tensor(self, identifier):
        """Never call this directly."""
        d = dict(identifier=identifier, action="delete")
        del self[identifier]
        logging.info(json.dumps(d))

    def add_tensor(self, centroid, marker):
        """Add a tensor manually.

        For manual editing with undo.
        """
        identifier = max(self.identifiers) + 1
        cmd = Command(do_method=self.create_tensor,
                      undo_method=self._delete_tensor,
                      do_args=[identifier, centroid, marker, "manual"],
                      undo_args=[identifier])
        self.run_command(cmd)
        return identifier

    def inactivate_tensor(self, identifier):
        """Mark a tensor as inactive."""
        tensor = self[identifier]
        cmd = Command(do_method=tensor.update,
                      undo_method=tensor.update,
                      do_args=["active", False],
                      undo_args=["active", True])
        self.run_command(cmd)

    def update_centroid(self, identifier, new_position):
        """Update the position of a centroid."""
        tensor = self[identifier]
        prev_position = tensor.centroid
        cmd = Command(do_method=tensor.update,
                      undo_method=tensor.update,
                      do_args=["centroid", list(new_position)],
                      undo_args=["centroid", prev_position])
        self.run_command(cmd)

    def update_marker(self, identifier, new_position):
        """Update the position of a marker."""
        tensor = self[identifier]
        prev_position = tensor.marker
        cmd = Command(do_method=tensor.update,
                      undo_method=tensor.update,
                      do_args=["marker", list(new_position)],
                      undo_args=["marker", prev_position])
        self.run_command(cmd)

    def write_audit_log(self, fh):
        """Write out an audit log."""
        for cmd in self.commands:
            fh.write("{}\n".format(cmd.audit_log))

    def apply_json(self, line):
        """Apply a line of json."""
        d = json.loads(line)
        action = d.pop("action")
        if action == "update":
            identifier = d.pop("identifier")
            for key, value in d.items():
                self[identifier]._data[key] = value
        elif action == "create":
            identifier = d["identifier"]
            self[identifier] = Tensor.from_json(json.dumps(d))
        else:
            raise(RuntimeError)


    def apply_audit_log(self, fh):
        """Apply an audit log."""
        for json_line in fh:
            self.apply_json(json_line)


def test_overall_api():

    # Test the creation of a tensor.
    tensor_manager = TensorManager()
    tensor_manager.create_tensor(1, (0, 0), (3, 5))
    tensor1 = tensor_manager[1]
    assert isinstance(tensor1, Tensor)
    assert tensor1.identifier == 1
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
    identifier = tensor_manager.add_tensor((3, 4), (5, 6))
    assert identifier == 6
    tensor = tensor_manager[identifier]
    assert tensor.identifier == identifier
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

    # Test undo followed by new action.
    assert len(tensor_manager.commands) == 4
    tensor_manager.undo()
    assert (6 in tensor_manager) is False
    tensor_manager.undo()
    assert len(tensor_manager.commands) == 4
    assert tensor_manager.command_offset == -2
    assert tensor1.marker == [3, 5]
    assert tensor_manager[2].centroid == [2, 8]
    tensor_manager.update_centroid(2, (1, 1))
    assert tensor_manager[2].centroid == [1, 1]
    assert len(tensor_manager.commands) == 3
    assert tensor_manager.command_offset == 0

    # Manually create another tenor.
    identifier = tensor_manager.add_tensor((3, 4), (5, 6))

    # Test creation of tensor using from_json static method.
    t1_copy = Tensor.from_json(json.dumps(tensor1._data))
    assert t1_copy == tensor1

    # Test writing of audit log.
    audit_file = "test_audit.log"
    with open(audit_file, "w") as fh:
        tensor_manager.write_audit_log(fh)
    assert os.path.isfile(audit_file)

    # Test recreation from an audit file.
    new_tensor_manager = TensorManager()
    new_tensor_manager.create_tensor(1, (0, 0), (3, 5))
    new_tensor_manager.create_tensor(5, (4, 0), (7, 5))
    new_tensor_manager.create_tensor(2, (2, 8), (1, 6))
    with open(audit_file) as fh:
        new_tensor_manager.apply_audit_log(fh)
    assert tensor_manager == new_tensor_manager

    # Clean up.
    os.unlink(audit_file)

if __name__ == "__main__":
    test_overall_api()
