# -*- coding: utf-8 -*-
"""Runtime image codec capabilities exposed by the Pillow backend."""

from dataclasses import dataclass

from PIL import Image, features


@dataclass(frozen=True)
class FormatCapabilities:
    name: str
    extensions: tuple
    alpha: bool = False
    animation: bool = False
    quality: bool = False
    lossless: bool = False
    icc_profile: bool = False
    exif: bool = False
    maximum_dimensions: tuple = None
    streaming: bool = False


# ``None`` means Pillow/the file format does not publish a fixed pixel limit.
FORMAT_REGISTRY = {
    "JPEG": FormatCapabilities("JPEG", (".jpg", ".jpeg"), quality=True,
                               icc_profile=True, exif=True,
                               maximum_dimensions=(65535, 65535), streaming=True),
    "PNG": FormatCapabilities("PNG", (".png",), alpha=True, animation=True,
                              lossless=True, icc_profile=True, exif=True,
                              maximum_dimensions=(2 ** 31 - 1, 2 ** 31 - 1),
                              streaming=True),
    "WEBP": FormatCapabilities("WEBP", (".webp",), alpha=True, animation=True,
                               quality=True, lossless=True, icc_profile=True,
                               exif=True, maximum_dimensions=(16383, 16383)),
    "TIFF": FormatCapabilities("TIFF", (".tif", ".tiff"), alpha=True,
                               animation=True, lossless=True, icc_profile=True,
                               exif=True, streaming=True),
    "BMP": FormatCapabilities("BMP", (".bmp",), alpha=True, lossless=True),
    "GIF": FormatCapabilities("GIF", (".gif",), alpha=True, animation=True,
                              lossless=True, maximum_dimensions=(65535, 65535),
                              streaming=True),
}

ALIASES = {"JPG": "JPEG", "TIF": "TIFF"}


def canonical_format(fmt):
    value = str(fmt).upper()
    return ALIASES.get(value, value)


def refresh_pillow_formats():
    """Initialise Pillow plugins before inspecting the decoder/encoder maps."""
    Image.init()


def decoder_available(fmt):
    refresh_pillow_formats()
    return canonical_format(fmt) in Image.OPEN


def encoder_available(fmt):
    refresh_pillow_formats()
    name = canonical_format(fmt)
    if name == "WEBP" and not features.check("webp"):
        return False
    return name in Image.SAVE


def available_export_formats(candidates=None):
    """Return only formats which the running Pillow can actually encode."""
    candidates = candidates or FORMAT_REGISTRY
    return tuple(name for name in candidates if encoder_available(name))


def capabilities(fmt):
    return FORMAT_REGISTRY.get(canonical_format(fmt))


def extensions_for_decoders():
    refresh_pillow_formats()
    extensions = set()
    for name, spec in FORMAT_REGISTRY.items():
        if decoder_available(name):
            extensions.update(spec.extensions)
    return tuple(sorted(extensions))
