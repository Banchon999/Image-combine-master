from imbine.ui.document import StitchDocument


def test_document_add_move_remove_and_visible_paths(tmp_path):
    paths = [str(tmp_path / name) for name in ("one.png", "two.png", "three.png")]
    document = StitchDocument()
    document.add_paths(paths)
    assert [layer.name for layer in document.layers] == ["one.png", "two.png", "three.png"]

    document.move(2, 0)
    document.layers[1].visible = False
    assert document.paths == [paths[2], paths[1]]
    assert document.remove(1).path == paths[0]


def test_layer_transform_defaults_are_independent(tmp_path):
    document = StitchDocument()
    first, second = document.add_paths([tmp_path / "a.png", tmp_path / "b.png"])
    first.rotation = 45
    first.offset_x = 20
    assert second.rotation == 0
    assert second.offset_x == 0
