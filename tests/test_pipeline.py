# -*- coding: utf-8 -*-
"""เทสต์กลไก pipeline — ตัวที่ระบบในอนาคตจะเสียบเข้ามา"""

import pytest

from imbine import (Cancelled, CancelToken, Pipeline, PipelineContext,
                    Progress, ProgressEvent, StitchConfig, Step,
                    build_default_pipeline)


class RecordingStep(Step):
    """ขั้นตอนหลอกที่จดว่าตัวเองถูกเรียก"""

    def __init__(self, name, log, enabled=True):
        self.name = name
        self._log = log
        self._enabled = enabled

    def is_enabled(self, ctx):
        return self._enabled

    def run(self, ctx):
        self._log.append(self.name)


def make_ctx(**kwargs):
    return PipelineContext(config=StitchConfig(), **kwargs)


class TestCancelToken:

    def test_เริ่มต้นยังไม่ถูกยกเลิก(self):
        token = CancelToken()
        assert token.cancelled is False
        token.check()  # ต้องไม่โยน

    def test_เมื่อยกเลิกแล้ว_check_ต้องโยน(self):
        token = CancelToken()
        token.cancel()
        assert token.cancelled is True
        with pytest.raises(Cancelled):
            token.check()

    def test_reset_ใช้ซ้ำได้(self):
        token = CancelToken()
        token.cancel()
        token.reset()
        token.check()


class TestProgress:

    def test_ไม่มี_callback_ก็เรียกได้ไม่พัง(self):
        p = Progress()
        p.begin_step("a", 1, 2)
        p.report(1, 1)

    def test_ส่ง_event_ที่มีข้อมูลขั้นตอนครบ(self):
        events = []
        p = Progress(events.append)
        p.begin_step("load", 2, 5)
        p.report(3, 10, "a.jpg")
        last = events[-1]
        assert (last.step, last.step_index, last.step_total) == ("load", 2, 5)
        assert (last.done, last.total, last.message) == (3, 10, "a.jpg")

    def test_begin_step_ยิง_event_ทันที(self):
        events = []
        Progress(events.append).begin_step("load", 1, 3)
        assert len(events) == 1
        assert events[0].done == 0


class TestProgressEvent:

    def test_fraction(self):
        assert ProgressEvent("s", 1, 4, 3, 4).fraction == 0.75

    def test_fraction_ไม่หารด้วยศูนย์(self):
        assert ProgressEvent("s", 1, 4, 0, 0).fraction == 0.0

    def test_overall_รวมความคืบหน้าข้ามขั้น(self):
        # ขั้นที่ 3 จาก 4 ทำไปครึ่งหนึ่ง -> (2 + 0.5) / 4
        assert ProgressEvent("s", 3, 4, 1, 2).overall == 0.625

    def test_overall_ไม่หารด้วยศูนย์(self):
        assert ProgressEvent("s", 0, 0, 0, 0).overall == 0.0


class TestPipelineOrder:

    def test_รันตามลำดับ(self):
        log = []
        Pipeline([RecordingStep("a", log), RecordingStep("b", log),
                  RecordingStep("c", log)]).run(make_ctx())
        assert log == ["a", "b", "c"]

    def test_ขั้นที่ปิดอยู่ถูกข้าม(self):
        log = []
        Pipeline([RecordingStep("a", log),
                  RecordingStep("b", log, enabled=False),
                  RecordingStep("c", log)]).run(make_ctx())
        assert log == ["a", "c"]

    def test_ขั้นที่ปิดไม่ถูกนับในตัวเลขความคืบหน้า(self):
        # ผู้ใช้ต้องไม่เห็น "ขั้นที่ 3 จาก 3" ทั้งที่ยังเหลืออีกขั้น
        events = []
        log = []
        ctx = make_ctx(progress=Progress(events.append))
        Pipeline([RecordingStep("a", log),
                  RecordingStep("b", log, enabled=False),
                  RecordingStep("c", log)]).run(ctx)
        assert {e.step_total for e in events} == {2}

    def test_คืน_ctx_ตัวเดิม(self):
        ctx = make_ctx()
        assert Pipeline([]).run(ctx) is ctx


class TestPipelineEditing:
    """เมธอดกลุ่มนี้คือเหตุผลที่รื้อมาเป็น pipeline ตั้งแต่แรก"""

    def _pipe(self, log):
        return Pipeline([RecordingStep("load", log),
                         RecordingStep("stitch", log),
                         RecordingStep("save", log)])

    def test_แทรกก่อนขั้นที่ระบุ(self):
        log = []
        pipe = self._pipe(log)
        pipe.insert_before("save", RecordingStep("watermark", log))
        pipe.run(make_ctx())
        assert log == ["load", "stitch", "watermark", "save"]

    def test_แทรกหลังขั้นที่ระบุ(self):
        log = []
        pipe = self._pipe(log)
        pipe.insert_after("load", RecordingStep("upscale", log))
        pipe.run(make_ctx())
        assert log == ["load", "upscale", "stitch", "save"]

    def test_แทนที่ขั้นเดิม(self):
        log = []
        pipe = self._pipe(log)
        pipe.replace("stitch", RecordingStep("stitch-ใหม่", log))
        pipe.run(make_ctx())
        assert log == ["load", "stitch-ใหม่", "save"]

    def test_ถอดขั้นออก(self):
        log = []
        pipe = self._pipe(log)
        pipe.remove("save")
        pipe.run(make_ctx())
        assert log == ["load", "stitch"]

    def test_ต่อสายได้(self):
        log = []
        pipe = self._pipe(log)
        assert pipe.insert_after("load", RecordingStep("x", log)) is pipe

    def test_ชื่อขั้นที่ไม่มีต้องโยน_KeyError_พร้อมบอกว่ามีอะไรบ้าง(self):
        pipe = self._pipe([])
        with pytest.raises(KeyError) as exc:
            pipe.insert_before("ไม่มีขั้นนี้", RecordingStep("x", []))
        assert "load" in str(exc.value)

    def test_step_names(self):
        assert self._pipe([]).step_names() == ["load", "stitch", "save"]


class TestPipelineCancel:

    def test_ยกเลิกก่อนเริ่มแล้วไม่มีขั้นไหนถูกรัน(self):
        log = []
        token = CancelToken()
        token.cancel()
        with pytest.raises(Cancelled):
            Pipeline([RecordingStep("a", log)]).run(make_ctx(cancel=token))
        assert log == []

    def test_ยกเลิกกลางทางแล้วขั้นที่เหลือไม่ถูกรัน(self):
        log = []
        token = CancelToken()

        class CancellingStep(Step):
            name = "ตัวยกเลิก"

            def run(self, ctx):
                log.append(self.name)
                ctx.cancel.cancel()

        with pytest.raises(Cancelled):
            Pipeline([CancellingStep(),
                      RecordingStep("ไม่ควรถูกเรียก", log)]).run(
                          make_ctx(cancel=token))
        assert log == ["ตัวยกเลิก"]


class TestDefaultPipeline:

    def test_ลำดับขั้นมาตรฐาน(self):
        assert build_default_pipeline().step_names() == [
            "load", "uniform", "split", "stitch", "save"]

    def test_ปิดการบันทึกได้สำหรับ_preview(self):
        assert "save" not in build_default_pipeline(save=False).step_names()

    def test_uniform_ปิดตาม_config(self, folder_of_images):
        ctx = make_ctx()
        ctx.config = StitchConfig(uniform=False)
        uniform = build_default_pipeline().steps[1]
        assert uniform.is_enabled(ctx) is False
