"""UI-neutral document model used by the interactive Qt workspace."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class Layer:
    path: str
    name: str = ""
    rotation: float = 0.0
    scale: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    opacity: float = 1.0
    blend_mode: str = "Normal"
    visible: bool = True

    def __post_init__(self):
        self.path = str(self.path)
        if not self.name:
            self.name = Path(self.path).name


@dataclass
class StitchDocument:
    layers: List[Layer] = field(default_factory=list)
    orientation: str = "vertical"

    def add_paths(self, paths):
        added = [Layer(path) for path in paths]
        self.layers.extend(added)
        return added

    def remove(self, index):
        return self.layers.pop(index)

    def move(self, source, destination):
        if source == destination:
            return
        layer = self.layers.pop(source)
        self.layers.insert(destination, layer)

    @property
    def paths(self):
        return [layer.path for layer in self.layers if layer.visible]
