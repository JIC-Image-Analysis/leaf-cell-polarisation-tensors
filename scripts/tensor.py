"""Module for creating, storing and editing tensors."""


class Tensor(object):
    """Class for managing individual tensors."""

    def __init__(self, identifier, centroid, marker, creation_type):
        self.identifier = identifier
        self.centroid = centroid
        self.marker = marker
        self.creation_type = creation_type
        self.active = True

    def activate(self):
        """Mark a tensor as active."""
        self.active = True

    def inactivate(self):
        """Mark a tensor as inactive."""
        self.active = False

    def update_centroid(self, new_position):
        """Move position of a centroid."""
        self.centroid = new_position

    def update_marker(self, new_position):
        """Move position of a marker."""
        self.marker = new_position


class Command(object):
    """Command class to enable undo/redo functionality."""

    def __init__(self, do_method, undo_method, do_args=None, undo_args=None):
        self.do_method = do_method
        self.do_args = do_args
        self.undo_method = undo_method
        self.undo_args = undo_args

    def do(self):
        """Execute a command."""
        if self.do_args is None:
            self.do_method()
        else:
            self.do_method(*self.do_args)

    def undo(self):
        """Reverse the effect of a command."""
        if self.undo_args is None:
            self.undo_method()
        else:
            self.undo_method(*self.undo_args)


class TensorManager(dict):
    """Class for creating, storing and editing tensors."""

    def __init__(self):
        self.commands = []
        self.command_offset = 0

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
        # Command offset will be negative if we have already undone things.
        cmd_index = -1 + self.command_offset
        if len(self.commands) + cmd_index < 0:
            return None
        self.commands[cmd_index].undo()
        self.command_offset -= 1
        return self.command_offset

    def redo(self):
        """Redo the last action."""
        if self.command_offset >= 0:
            return None
        cmd_index = self.command_offset
        self.commands[cmd_index].do()
        self.command_offset += 1
        return self.command_offset

    def create_tensor(self, identifier, centroid, marker, method="automated"):
        """Create a tensor and store it.

        Not for manual editing.
        """
        self[identifier] = Tensor(identifier, centroid, marker, method)

    def _destroy_tensor(self, identifier):
        """Never call this directly."""
        del self[identifier]

    def add_tensor(self, centroid, marker):
        """Add a tensor manually.

        For manual editing with undo.
        """
        identifier = max(self.identifiers) + 1
        cmd = Command(do_method=self.create_tensor,
                      undo_method=self._destroy_tensor,
                      do_args=[identifier, centroid, marker, "manual"],
                      undo_args=[identifier])
        self.run_command(cmd)
        return identifier

    def inactivate_tensor(self, identifier):
        """Mark a tensor as inactive."""
        tensor = self[identifier]
        cmd = Command(tensor.inactivate, tensor.activate)
        self.run_command(cmd)

    def update_centroid(self, identifier, new_position):
        """Update the position of a centroid."""
        tensor = self[identifier]
        prev_position = tensor.centroid
        cmd = Command(do_method=tensor.update_centroid,
                      undo_method=tensor.update_centroid,
                      do_args=[new_position],
                      undo_args=[prev_position])
        self.run_command(cmd)

    def update_marker(self, identifier, new_position):
        """Update the position of a marker."""
        tensor = self[identifier]
        prev_position = tensor.marker
        cmd = Command(do_method=tensor.update_marker,
                      undo_method=tensor.update_marker,
                      do_args=[new_position],
                      undo_args=[prev_position])
        self.run_command(cmd)


def test_overall_api():

    # Test the creation of a tensor.
    tensor_manager = TensorManager()
    tensor_manager.create_tensor(1, (0, 0), (3, 5))
    tensor1 = tensor_manager[1]
    assert isinstance(tensor1, Tensor)
    assert tensor1.identifier == 1
    assert tensor1.centroid == (0, 0)
    assert tensor1.marker == (3, 5)
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
    assert tensor1.centroid == (1, 10)
    tensor_manager.undo()
    assert tensor1.centroid == (0, 0)
    tensor_manager.redo()
    assert tensor1.centroid == (1, 10)

    # Test update_marker and undo/redo.
    tensor_manager.update_marker(1, (100, 8))
    assert tensor1.marker == (100, 8)
    tensor_manager.undo()
    assert tensor1.marker == (3, 5)
    tensor_manager.redo()
    assert tensor1.marker == (100, 8)

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
    assert tensor.centroid == (3, 4)
    assert tensor.marker == (5, 6)
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
    assert tensor1.marker == (3, 5)
    assert tensor_manager[2].centroid == (2, 8)
    tensor_manager.update_centroid(2, (1, 1))
    assert tensor_manager[2].centroid == (1, 1)
    assert len(tensor_manager.commands) == 3
    assert tensor_manager.command_offset == 0
