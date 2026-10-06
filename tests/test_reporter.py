from reporter import setup_logging, load_done, append_done, format_summary
from orchestrator import LinkResult, SUCCESS, FAIL


def test_done_roundtrip(tmp_path):
    p = str(tmp_path / "d.txt")
    assert load_done(p) == set()
    append_done(p, "ABC")
    append_done(p, "abc")
    assert load_done(p) == {"abc"}


def test_format_summary_lists_failures():
    rs = [LinkResult(1, "l1", SUCCESS),
          LinkResult(2, "l2", FAIL, "弹窗超时未出现")]
    s = format_summary(rs)
    assert "成功 1 条" in s and "失败 1 条" in s and "弹窗超时" in s


def test_setup_logging_writes_file(tmp_path):
    logger = setup_logging(str(tmp_path / "a.log"))
    logger.info("hello")
    assert "hello" in (tmp_path / "a.log").read_text(encoding="utf-8")
