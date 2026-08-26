"""Small value objects shared by manual alignment, backends, and UIs."""

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence, Tuple

Point = Tuple[float, float]


@dataclass(frozen=True)
class Transform:
    """A homogeneous 3-by-3 transform mapping source to reference pixels."""

    matrix: Tuple[Tuple[float, float, float],
                  Tuple[float, float, float],
                  Tuple[float, float, float]]
    kind: str = "affine"

    @classmethod
    def identity(cls):
        return cls(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                    (0.0, 0.0, 1.0)), "translation")

    def map_point(self, point: Sequence[float]) -> Point:
        x, y = float(point[0]), float(point[1])
        m = self.matrix
        w = m[2][0] * x + m[2][1] * y + m[2][2]
        if abs(w) < 1e-15:
            raise ValueError("transform maps point to infinity")
        return ((m[0][0] * x + m[0][1] * y + m[0][2]) / w,
                (m[1][0] * x + m[1][1] * y + m[1][2]) / w)


@dataclass(frozen=True)
class ControlPointPair:
    source: Point
    reference: Point


@dataclass
class ImageLayer:
    """UI-neutral layer state; image may be a Pillow, Qt, or backend object."""

    image: Any
    name: str = ""
    transform: Transform = field(default_factory=Transform.identity)
    layer_id: Optional[str] = None
