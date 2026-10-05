import json

import pytest

from epdlib import Layout, LayoutError
from epdlib.spec import MAX_DEPTH, MAX_JSON_BYTES, MAX_PIXELS

from .conftest import column, row, text_block


def test_minimal_layout():
    layout = Layout(column(text_block("a"), text_block("b")))
    assert list(layout.blocks) == ["a", "b"]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([], "must be a dictionary"),
        ({"name": "a", "type": "text"}, "top level must be a 'row' or a 'column'"),
        ({"row": [], "column": []}, "both 'row' and 'column'"),
        (column(), "at least one item"),
        (column({"type": "text"}), "needs a 'name'"),
        (column(text_block("a"), text_block("a")), "used twice"),
        (column({"name": "a", "type": "txt"}), "'type' must be one of"),
        (column(text_block("a", sise=1)), "unknown key 'sise' (did you mean 'size'?)"),
        (column(text_block("a", size=1, pixels=10)), "both 'size' and 'pixels'"),
        (column(text_block("a", size=0)), "'size' must be a number above 0"),
        (column(text_block("a", size=True)), "'size' must be a number above 0"),
        (column(text_block("a", pixels=-1)), "'pixels' must be a whole number"),
        (column(text_block("a", padding=2)), "share of the screen from 0 to 1"),
        (column(text_block("a", padding={"px": 2})), "unknown key 'px'"),
        (column(text_block("a", max_lines=0)), "'max_lines' must be a whole number"),
        (column(text_block("a", align="middle")), "'align' must be one of"),
        (column(text_block("a", fill="blurple")), "not a colour name"),
        (column(text_block("a", shrink="yes")), "'shrink' must be true or false"),
        (column(text_block("a", font_size=0)), "'font_size' must be more than 0"),
        (column({"name": "s", "type": "shape", "shape": "star"}), "'shape' must be one of"),
    ],
)
def test_errors_name_the_problem(data, message):
    with pytest.raises(LayoutError, match=None) as err:
        Layout(data)
    assert message in str(err.value)


def test_error_names_the_block():
    with pytest.raises(LayoutError, match="block 'body': unknown key 'colour'"):
        Layout(column(text_block("title"), row(text_block("body", colour="red"))))


def nested(levels):
    data = text_block("deep")
    for _ in range(levels):
        data = column(data)
    return data


def test_nesting_limit():
    Layout(nested(MAX_DEPTH))  # 10 levels of rows and columns are allowed
    with pytest.raises(LayoutError, match="nested deeper"):
        Layout(nested(MAX_DEPTH + 1))


@pytest.mark.parametrize(
    "options",
    [
        {"pixels": MAX_PIXELS + 1},
        {"border": {"pixels": MAX_PIXELS + 1}},
        {"font_size": {"pixels": MAX_PIXELS + 1}},
    ],
)
def test_pixel_limit(options):
    Layout(column(text_block("a", **{k: _at_limit(v) for k, v in options.items()})))
    with pytest.raises(LayoutError, match="whole number from"):
        Layout(column(text_block("a", **options)))


def _at_limit(value):
    return {"pixels": MAX_PIXELS} if isinstance(value, dict) else MAX_PIXELS


def test_json_round_trip(tmp_path):
    path = tmp_path / "layout.json"
    path.write_text(json.dumps(column(text_block("a", size=2), text_block("b"))))
    layout = Layout.from_json(path, asset_dirs=[tmp_path])
    assert list(layout.blocks) == ["a", "b"]


def test_json_bad_syntax(tmp_path):
    path = tmp_path / "layout.json"
    path.write_text("{column: }")
    with pytest.raises(LayoutError, match="not valid JSON"):
        Layout.from_json(path, asset_dirs=[tmp_path])


def test_json_too_large(tmp_path):
    path = tmp_path / "layout.json"
    path.write_text(" " * (MAX_JSON_BYTES + 1))
    with pytest.raises(LayoutError, match="larger than"):
        Layout.from_json(path, asset_dirs=[tmp_path])


@pytest.mark.parametrize("bad", ["../../etc/passwd", "/etc/passwd", "fonts/../../x.ttf"])
@pytest.mark.parametrize("key", ["font", "image"])
def test_json_paths_must_stay_in_allowed_folders(tmp_path, bad, key):
    allowed = tmp_path / "assets"
    allowed.mkdir()
    block = {"name": "a", "type": "text" if key == "font" else "image", key: bad}
    path = tmp_path / "layout.json"
    path.write_text(json.dumps(column(block)))
    with pytest.raises(LayoutError, match="outside the allowed folders"):
        Layout.from_json(path, asset_dirs=[allowed])


def test_json_link_out_of_folder_is_refused(tmp_path):
    allowed = tmp_path / "assets"
    allowed.mkdir()
    (tmp_path / "secret.ttf").write_bytes(b"")
    (allowed / "link.ttf").symlink_to(tmp_path / "secret.ttf")
    with pytest.raises(LayoutError, match="outside the allowed folders"):
        Layout(column(text_block("a", font="link.ttf")), asset_dirs=[allowed])


@pytest.mark.parametrize("bad", [".", "missing.ttf", "a\x00b"])
def test_json_paths_must_be_files(tmp_path, bad):
    with pytest.raises(LayoutError, match="not a file|not a valid path"):
        Layout(column(text_block("a", font=bad)), asset_dirs=[tmp_path])


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("[" * 100_000, "nested too deeply"),
        ("1" * 5000, "not valid JSON"),
        (b"\xff\xfe", "not valid JSON"),
    ],
)
def test_odd_json_gives_layout_error(tmp_path, content, message):
    path = tmp_path / "layout.json"
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content)
    with pytest.raises(LayoutError, match=message):
        Layout.from_json(path, asset_dirs=[tmp_path])


def test_json_size_limit_does_not_trust_file_size(tmp_path):
    """A pipe reports size 0; reading must still stop at the limit."""
    import os
    import threading

    fifo = tmp_path / "pipe.json"
    os.mkfifo(fifo)

    def writer():
        with open(fifo, "w") as f:
            try:
                f.write(" " * (MAX_JSON_BYTES + 10))
            except BrokenPipeError:
                pass

    thread = threading.Thread(target=writer)
    thread.start()
    with pytest.raises(LayoutError, match="larger than"):
        Layout.from_json(fifo, asset_dirs=[tmp_path])
    thread.join(timeout=5)


def test_json_paths_inside_allowed_folder_are_found(tmp_path):
    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "a.ttf").write_bytes(b"")
    path = tmp_path / "layout.json"
    path.write_text(json.dumps(column(text_block("a", font="fonts/a.ttf"))))
    layout = Layout.from_json(path, asset_dirs=[tmp_path])
    assert layout.blocks["a"].options["font"] == str(tmp_path / "fonts" / "a.ttf")
