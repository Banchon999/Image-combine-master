import sys

import pytest

from imbine.alignment.auto import (AutoAlignmentBackend, BackendUnavailable,
                                   align_automatically, get_backend)
from imbine.alignment.manual import estimate_transform
from imbine.alignment.models import ImageLayer, Transform
from imbine.pipeline import CancelToken, Cancelled
from imbine.ui.qt.properties import AutoAlignController


def test_manual_transform_examples():
    translation = estimate_transform([((1, 2), (4, 6))], "translation")
    assert translation.map_point((10, 20)) == pytest.approx((13, 24))
    similarity = estimate_transform([((0, 0), (3, 4)), ((1, 0), (3, 6))],
                                    "similarity")
    assert similarity.map_point((0, 1)) == pytest.approx((1, 4))
    affine = estimate_transform([((0, 0), (2, 3)), ((1, 0), (4, 3)),
                                 ((0, 1), (3, 6))], "affine")
    assert affine.map_point((2, 2)) == pytest.approx((8, 9))


@pytest.mark.parametrize("pairs,kind", [([], "translation"),
    ([((0, 0), (0, 0)), ((0, 0), (1, 1))], "similarity"),
    ([((0, 0), (0, 0)), ((1, 0), (1, 0)), ((2, 0), (2, 0))], "affine")])
def test_invalid_control_points(pairs, kind):
    with pytest.raises(ValueError):
        estimate_transform(pairs, kind)


def test_cancelled_before_backend_runs():
    token = CancelToken()
    token.cancel()
    with pytest.raises(Cancelled):
        align_automatically(None, None, object(), token)


def test_missing_backend_has_actionable_fallback(monkeypatch):
    monkeypatch.setattr("imbine.alignment.auto.available_backends", lambda: ())
    with pytest.raises(BackendUnavailable, match=r"imbine\[auto\].*manually"):
        get_backend()


def test_controller_dispatches_transform_only_after_worker():
    expected = Transform.identity()

    class FakeBackend(AutoAlignmentBackend):
        def align(self, source, reference, cancel=None):
            cancel.check()
            return expected

    queued = []
    source, reference = ImageLayer(object()), ImageLayer(object())
    controller = AutoAlignController(queued.append)
    thread = controller.start(source, reference, FakeBackend())
    thread.join(2)
    assert source.transform == Transform.identity()
    assert len(queued) == 1
    queued.pop()()
    assert source.transform is expected
