import pytest
from PIL import Image

from imbine import (ImageValidationError, available_export_formats,
                    inspect_image, load_image, run_stitch, save_image)
from imbine.formats import encoder_available


def test_alpha_is_preserved_until_png_export(tmp_path):
    source = tmp_path / "alpha.png"
    output = tmp_path / "result.png"
    Image.new("RGBA", (4, 4), (200, 20, 10, 77)).save(source)
    result = run_stitch([str(source)]).results[0]
    assert result.mode == "RGBA"
    assert result.getpixel((0, 0))[3] == 77
    save_image(result, output, "PNG")
    with Image.open(output) as reopened:
        assert reopened.getpixel((0, 0))[3] == 77


def test_exif_orientation_is_applied(tmp_path):
    source = tmp_path / "turned.jpg"
    image = Image.new("RGB", (3, 7))
    exif = image.getexif()
    exif[274] = 6
    image.save(source, exif=exif)
    loaded = load_image(source)[0]
    assert loaded.size == (7, 3)
    assert loaded.getexif().get(274) is None


def test_icc_profile_propagates_through_stitch_and_png(tmp_path):
    source = tmp_path / "profile.png"
    output = tmp_path / "out.png"
    profile = b"test ICC payload"
    Image.new("RGB", (4, 4)).save(source, icc_profile=profile)
    result = run_stitch([str(source)]).results[0]
    assert result.info["icc_profile"] == profile
    save_image(result, output, "PNG")
    with Image.open(output) as reopened:
        assert reopened.info["icc_profile"] == profile


def test_content_wins_over_mismatched_extension(tmp_path):
    source = tmp_path / "actually_png.jpg"
    Image.new("RGB", (2, 2)).save(source, "PNG")
    assert inspect_image(source) == "PNG"


def test_multiframe_policy(tmp_path):
    source = tmp_path / "animated.gif"
    frames = [Image.new("RGB", (2, 2), color) for color in ("red", "blue")]
    frames[0].save(source, save_all=True, append_images=frames[1:])
    assert len(load_image(source, "first")) == 1
    assert len(load_image(source, "all")) == 2
    with pytest.raises(ImageValidationError):
        load_image(source, "error")


def test_unavailable_encoder_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr("imbine.output.encoder_available", lambda fmt: False)
    with pytest.raises(ValueError, match="encoder"):
        save_image(Image.new("RGB", (1, 1)), tmp_path / "x.png", "PNG")


def test_runtime_format_list_only_contains_encoders():
    assert all(encoder_available(fmt) for fmt in available_export_formats())
