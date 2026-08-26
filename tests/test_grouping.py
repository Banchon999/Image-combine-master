# -*- coding: utf-8 -*-
"""เทสต์การแบ่งภาพเป็นกลุ่ม"""

from imbine import split_into_groups


def sizes(groups):
    """จำนวนภาพในแต่ละกลุ่ม — ใช้เทียบง่ายกว่าเทียบ object ภาพ"""
    return [len(g) for g in groups]


class TestByPartsCount:

    def test_แบ่งลงตัว(self, img):
        images = [img(100, 50) for _ in range(9)]
        assert sizes(split_into_groups(images, parts_count=3)) == [3, 3, 3]

    def test_เศษถูกเกลี่ยใส่กลุ่มแรก(self, img):
        images = [img(100, 50) for _ in range(10)]
        assert sizes(split_into_groups(images, parts_count=3)) == [4, 3, 3]

    def test_ไฟล์เดียวได้ทุกภาพรวมกัน(self, img):
        images = [img(100, 50) for _ in range(7)]
        assert sizes(split_into_groups(images, parts_count=1)) == [7]

    def test_ขอมากกว่าจำนวนภาพได้เท่าจำนวนภาพ(self, img):
        images = [img(100, 50) for _ in range(3)]
        assert sizes(split_into_groups(images, parts_count=99)) == [1, 1, 1]

    def test_ไม่มีภาพหายไประหว่างแบ่ง(self, img):
        images = [img(100, 50) for _ in range(17)]
        groups = split_into_groups(images, parts_count=5)
        assert [im for g in groups for im in g] == images

    def test_ลิสต์ว่างได้กลุ่มว่าง(self):
        assert split_into_groups([], parts_count=3) == []


class TestByMaxSize:

    def test_แนวตั้งคิดจากความสูง(self, img):
        images = [img(100, 100) for _ in range(5)]
        assert sizes(split_into_groups(images, max_size=250,
                                       vertical=True)) == [2, 2, 1]

    def test_แนวนอนคิดจากความกว้าง(self, img):
        images = [img(100, 100) for _ in range(5)]
        assert sizes(split_into_groups(images, max_size=250,
                                       vertical=False)) == [2, 2, 1]

    def test_แนวตั้งกับแนวนอนให้ผลต่างกันเมื่อภาพไม่จัตุรัส(self, img):
        images = [img(50, 200) for _ in range(4)]
        # สูง 200 ต่อใบ -> ใส่ได้ใบเดียวต่อกลุ่ม
        assert sizes(split_into_groups(images, max_size=300,
                                       vertical=True)) == [1, 1, 1, 1]
        # กว้าง 50 ต่อใบ -> ใส่ได้ครบใน 6 ใบ
        assert sizes(split_into_groups(images, max_size=300,
                                       vertical=False)) == [4]

    def test_ภาพเดียวที่ใหญ่เกินยังได้อยู่กลุ่มตัวเอง(self, img):
        # ตัดกลางรูปไม่ได้ ดังนั้นกลุ่มนี้จะเกิน max_size อย่างเลี่ยงไม่ได้
        images = [img(100, 500) for _ in range(2)]
        assert sizes(split_into_groups(images, max_size=250)) == [1, 1]

    def test_max_size_มีสิทธิ์เหนือ_parts_count(self, img):
        images = [img(100, 100) for _ in range(5)]
        groups = split_into_groups(images, parts_count=1, max_size=250)
        assert sizes(groups) == [2, 2, 1]

    def test_max_size_ศูนย์คือไม่จำกัด(self, img):
        images = [img(100, 100) for _ in range(5)]
        assert sizes(split_into_groups(images, parts_count=2,
                                       max_size=0)) == [3, 2]

    def test_ทุกกลุ่มไม่เกินขนาดถ้าภาพเดี่ยวไม่เกิน(self, img):
        images = [img(100, 60) for _ in range(10)]
        for group in split_into_groups(images, max_size=250):
            assert sum(im.height for im in group) <= 250
