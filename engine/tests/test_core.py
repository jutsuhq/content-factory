from factory.core import digest, fresh, mark


def test_cache_key_follows_file_content(tmp_path):
    src, out = tmp_path / "a.txt", tmp_path / "b.txt"
    src.write_text("one")
    out.write_text("result")
    key = digest(src, "prompt")
    assert not fresh(out, key)
    mark(out, key)
    assert fresh(out, key)
    src.write_text("two")
    assert not fresh(out, digest(src, "prompt"))


def test_setup_names_what_it_can_install_when_asked_for_something_else():
    import pytest

    from factory import setup

    with pytest.raises(ValueError, match="installable: rife, depth, render, music, vosk"):
        setup.install("ffmpeg")
    assert {"vosk"} <= set(setup.INSTALLERS) and "vosk" not in setup.missing()
