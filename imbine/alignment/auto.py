"""Pluggable automatic alignment backends.

The UI depends only on :class:`AutoAlignmentBackend`; importing this module
never imports OpenCV. This makes auto-alignment genuinely optional.
"""

from abc import ABC, abstractmethod

from .models import Transform


class AutoAlignError(RuntimeError):
    pass


class BackendUnavailable(AutoAlignError):
    """Raised with an actionable message when no implementation is installed."""


class AutoAlignmentBackend(ABC):
    name = "unnamed"

    @abstractmethod
    def align(self, source, reference, cancel=None):
        """Return a source-to-reference :class:`Transform`."""


class OpenCVBackend(AutoAlignmentBackend):
    """ORB feature matching implementation; OpenCV is imported on first use."""

    name = "opencv"

    def align(self, source, reference, cancel=None):
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise BackendUnavailable(
                "OpenCV auto-alignment is not installed. "
                "Install imbine[auto] or choose another backend.") from exc
        _check_cancel(cancel)
        source = np.asarray(source)
        reference = np.asarray(reference)
        gray_source = cv2.cvtColor(source, cv2.COLOR_RGB2GRAY) if source.ndim == 3 else source
        gray_reference = cv2.cvtColor(reference, cv2.COLOR_RGB2GRAY) if reference.ndim == 3 else reference
        detector = cv2.ORB_create(nfeatures=3000)
        key_source, desc_source = detector.detectAndCompute(gray_source, None)
        _check_cancel(cancel)
        key_reference, desc_reference = detector.detectAndCompute(gray_reference, None)
        if desc_source is None or desc_reference is None:
            raise AutoAlignError("Not enough image features for auto-alignment")
        matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(
            desc_source, desc_reference)
        matches = sorted(matches, key=lambda match: match.distance)[:500]
        if len(matches) < 3:
            raise AutoAlignError("Not enough matching features for auto-alignment")
        _check_cancel(cancel)
        source_points = np.float32([key_source[m.queryIdx].pt for m in matches])
        reference_points = np.float32([key_reference[m.trainIdx].pt for m in matches])
        matrix, _ = cv2.estimateAffinePartial2D(
            source_points, reference_points, method=cv2.RANSAC)
        if matrix is None:
            raise AutoAlignError("OpenCV could not estimate an alignment transform")
        _check_cancel(cancel)
        return Transform(((float(matrix[0, 0]), float(matrix[0, 1]), float(matrix[0, 2])),
                          (float(matrix[1, 0]), float(matrix[1, 1]), float(matrix[1, 2])),
                          (0.0, 0.0, 1.0)), "similarity")


_BACKENDS = {"opencv": OpenCVBackend}


def register_backend(name, factory):
    """Register a backend factory (also useful for application plugins/tests)."""
    _BACKENDS[str(name)] = factory


def available_backends():
    """Return installed backend names without importing optional libraries."""
    result = []
    for name in _BACKENDS:
        if name != "opencv":
            result.append(name)
            continue
        try:
            import importlib.util
            if importlib.util.find_spec("cv2") is not None:
                result.append(name)
        except (ImportError, ValueError):
            pass
    return tuple(result)


def get_backend(name=None):
    if name is None:
        installed = available_backends()
        if not installed:
            raise BackendUnavailable(
                "No auto-alignment backend is available. Install imbine[auto] "
                "(OpenCV) or align manually with control points.")
        name = installed[0]
    try:
        factory = _BACKENDS[name]
    except KeyError as exc:
        raise BackendUnavailable("Unknown auto-alignment backend: %s" % name) from exc
    return factory() if isinstance(factory, type) or callable(factory) else factory


def align_automatically(source, reference, backend=None, cancel=None):
    _check_cancel(cancel)
    implementation = get_backend(backend) if isinstance(backend, str) or backend is None else backend
    result = implementation.align(source, reference, cancel=cancel)
    _check_cancel(cancel)
    if not isinstance(result, Transform):
        raise AutoAlignError("auto-alignment backend returned an invalid result")
    return result


def _check_cancel(cancel):
    if cancel is None:
        return
    if hasattr(cancel, "check"):
        cancel.check()
    elif callable(cancel) and cancel():
        raise AutoAlignError("Auto-alignment cancelled")
    elif getattr(cancel, "cancelled", False):
        raise AutoAlignError("Auto-alignment cancelled")
