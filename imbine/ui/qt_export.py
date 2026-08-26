"""Small Qt-agnostic adapter for an export-format combo box.

No Qt binding is imported here: callers may pass a QComboBox from PySide or
PyQt, while headless users can still import the package.
"""

from ..formats import available_export_formats


def populate_export_formats(combo_box, candidates=("JPEG", "PNG", "WEBP", "TIFF")):
    """Replace combo entries with encoders available in this Pillow runtime."""
    formats = available_export_formats(candidates)
    combo_box.clear()
    combo_box.addItems(list(formats))
    return formats
