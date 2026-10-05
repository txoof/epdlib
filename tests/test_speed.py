"""Speed limits, so text measuring does not become slow again (v0.6 was slow at start-up).

The limits are for one large text block (720x660 pixels, about the body of a 9.7" screen)
on a Raspberry Pi 4. A block with ``shrink: true`` may try three font sizes, so it gets
three times the time. Each test takes the fastest of several runs, so a busy computer
does not make it fail.
"""

import time

import pytest

from epdlib import Layout, ScreenMode

from .conftest import column, text_block

LIMIT = 0.05  # seconds for one text block
TEXT = "The quick brown fox jumps over the lazy dog. "


def fastest_render(block, value, runs=7):
    page = Layout(column(block)).prepare(720, 660, ScreenMode.gray(16))
    page.render({block["name"]: TEXT * 50})  # warm-up: loads every font size it may use
    times = []
    for i in range(runs):
        start = time.perf_counter()
        page.render({block["name"]: f"{i} {value}"})
        times.append(time.perf_counter() - start)
    return min(times)


@pytest.mark.parametrize("repeat", [1, 10, 50])
def test_text_block_speed(repeat):
    seconds = fastest_render(text_block("body", max_lines=6), TEXT * repeat)
    assert seconds < LIMIT, f"{seconds * 1000:.1f} ms"


@pytest.mark.parametrize("repeat", [1, 10, 50])
def test_shrinking_text_block_speed(repeat):
    seconds = fastest_render(text_block("body", max_lines=6, shrink=True), TEXT * repeat)
    assert seconds < 3 * LIMIT, f"{seconds * 1000:.1f} ms"


def test_prepare_measures_almost_nothing():
    layout = Layout(column(*[text_block(str(i), max_lines=2) for i in range(20)]))
    layout.prepare(1000, 700, ScreenMode.gray(16))  # warm-up: loads fonts
    start = time.perf_counter()
    layout.prepare(1200, 825, ScreenMode.gray(16))
    assert time.perf_counter() - start < LIMIT
