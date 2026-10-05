"""Speed limits, so text measuring does not become slow again (v0.6 was slow at start-up).

Limits are for a Raspberry Pi 4 drawing a block on a 9.7" screen (1200x825). A block with
``shrink: true`` may try three font sizes, so it gets three times the time.
"""

import time

import pytest

from epdlib import Layout, ScreenMode

from .conftest import column, text_block

LIMIT = 0.05  # seconds for one text block
TEXT = "The quick brown fox jumps over the lazy dog. "


def time_render(block, value, runs=5):
    page = Layout(column(block)).prepare(720, 660, ScreenMode.gray(16))
    page.render({block["name"]: "warm-up"})
    start = time.perf_counter()
    for i in range(runs):
        page.render({block["name"]: f"{i} {value}"})
    return (time.perf_counter() - start) / runs


@pytest.mark.parametrize("repeat", [1, 10, 50])
def test_text_block_speed(repeat):
    seconds = time_render(text_block("body", max_lines=6), TEXT * repeat)
    assert seconds < LIMIT, f"{seconds * 1000:.1f} ms"


@pytest.mark.parametrize("repeat", [1, 10, 50])
def test_shrinking_text_block_speed(repeat):
    seconds = time_render(text_block("body", max_lines=6, shrink=True), TEXT * repeat)
    assert seconds < 3 * LIMIT, f"{seconds * 1000:.1f} ms"


def test_prepare_measures_almost_nothing():
    layout = Layout(column(*[text_block(str(i), max_lines=2) for i in range(20)]))
    start = time.perf_counter()
    layout.prepare(1200, 825, ScreenMode.gray(16))
    assert time.perf_counter() - start < LIMIT
