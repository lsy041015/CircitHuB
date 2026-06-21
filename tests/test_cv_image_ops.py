"""Tests for pure CV image ops (D2/D3) — synthetic images, no PDF/GUI."""

import unittest

import numpy as np

from digikey_scraper.infrastructure.cv.image_ops import (
    adaptive_block_size,
    apply_filter,
    deskew_image,
    samples_to_bgr,
    unsharp,
)


def _img(h=40, w=60):
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


class SamplesToBgrTests(unittest.TestCase):
    def test_rgb_3ch(self):
        h, w = 4, 5
        rgb = np.dstack(
            [
                np.full((h, w), 10, np.uint8),
                np.full((h, w), 20, np.uint8),
                np.full((h, w), 30, np.uint8),
            ]
        )
        out = samples_to_bgr(rgb.tobytes(), h, w, 3)
        self.assertEqual(out.shape, (h, w, 3))
        # RGB(10,20,30) -> BGR(30,20,10)
        self.assertEqual(tuple(int(v) for v in out[0, 0]), (30, 20, 10))

    def test_gray_1ch(self):
        h, w = 3, 3
        gray = np.full((h, w), 128, np.uint8)
        out = samples_to_bgr(gray.tobytes(), h, w, 1)
        self.assertEqual(out.shape, (h, w, 3))
        self.assertTrue((out == 128).all())

    def test_rgba_4ch(self):
        h, w = 2, 2
        rgba = np.dstack([np.full((h, w), c, np.uint8) for c in (10, 20, 30, 255)])
        out = samples_to_bgr(rgba.tobytes(), h, w, 4)
        self.assertEqual(out.shape, (h, w, 3))

    def test_unsupported_channels_raise(self):
        with self.assertRaises(ValueError):
            samples_to_bgr(b"\x00" * 6, 1, 2, 3 + 2)  # 5 channels


class FilterTests(unittest.TestCase):
    def test_original_is_identity(self):
        img = _img()
        self.assertTrue((apply_filter(img, "original") == img).all())

    def test_each_mode_preserves_shape_and_dtype(self):
        img = _img()
        for mode in ("contrast", "binarize", "denoise", "sharpen", "auto", "deskew"):
            out = apply_filter(img, mode)
            self.assertEqual(out.shape, img.shape, mode)
            self.assertEqual(out.dtype, np.uint8, mode)

    def test_unknown_mode_returns_input(self):
        img = _img()
        self.assertTrue((apply_filter(img, "nope") == img).all())

    def test_binarize_is_two_valued(self):
        out = apply_filter(_img(), "binarize")
        self.assertTrue(set(np.unique(out)).issubset({0, 255}))


class UnsharpTests(unittest.TestCase):
    def test_shape_preserved_and_uint8(self):
        out = unsharp(_img())
        self.assertEqual(out.shape, (40, 60, 3))
        self.assertEqual(out.dtype, np.uint8)


class DeskewTests(unittest.TestCase):
    def test_no_lines_returns_input(self):
        # flat gray image has no edges -> deskew is a no-op
        img = np.full((50, 50, 3), 200, np.uint8)
        self.assertTrue((deskew_image(img) == img).all())

    def test_rotated_text_image_runs(self):
        img = np.full((80, 120, 3), 255, np.uint8)
        img[30:34, 10:110] = 0  # a near-horizontal bar
        out = deskew_image(img)
        self.assertEqual(out.shape, img.shape)


class BlockSizeTests(unittest.TestCase):
    def test_odd_and_min(self):
        self.assertEqual(adaptive_block_size(30), 11)  # below min -> 11
        bs = adaptive_block_size(900)
        self.assertEqual(bs % 2, 1)
        self.assertGreaterEqual(bs, 11)


if __name__ == "__main__":
    unittest.main()
