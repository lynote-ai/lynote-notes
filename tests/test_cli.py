from lynote_notes.cli import main


def run(capsys, *argv):
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_cli_add_list_note_ask_export(tmp_path, capsys, sample_file):
    ws = str(tmp_path / "ws")

    code, out, _ = run(capsys, "--workspace", ws, "add", str(sample_file))
    assert code == 0
    assert "Added src_" in out
    source_id = out.split()[1].rstrip(":")

    code, out, _ = run(capsys, "--workspace", ws, "list")
    assert code == 0
    assert source_id in out

    code, out, err = run(capsys, "--workspace", ws, "note", "--title", "Weekly reading")
    assert code == 0
    assert "# Weekly reading" in out
    assert "note id:" in err

    code, out, _ = run(capsys, "--workspace", ws, "ask", "What license is the project under?")
    assert code == 0
    assert "MIT" in out

    code, out, _ = run(capsys, "--workspace", ws, "list", "--notes")
    assert code == 0
    assert "Weekly reading" in out


def test_cli_export_unknown_note(tmp_path, capsys):
    code, _, err = run(capsys, "--workspace", str(tmp_path / "ws"), "export", "--note", "nope")
    assert code == 1
    assert "Note not found" in err


def test_cli_export_writes_file(tmp_path, capsys, sample_file):
    ws = str(tmp_path / "ws")
    run(capsys, "--workspace", ws, "add", str(sample_file))
    _, _, err = run(capsys, "--workspace", ws, "note", "--title", "Cards")
    note_id = err.strip().split("note id: ")[1].rstrip(")")

    out_path = tmp_path / "cards.tsv"
    code, out, _ = run(
        capsys, "--workspace", ws, "export", "--note", note_id, "--format", "anki", "--out", str(out_path)
    )
    assert code == 0
    assert "Wrote" in out
    content = out_path.read_text(encoding="utf-8")
    assert content.startswith("#separator:tab")
