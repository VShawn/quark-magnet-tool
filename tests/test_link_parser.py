from link_parser import extract_links, hash_of, filter_done, read_text

A40, B32 = "a" * 40, "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def test_extract_ignores_blank_and_noise():
    text = f"第一行\n\n{A40}不是磁力链\nmagnet:?xt=urn:btih:{A40}\n垃圾\n"
    links = extract_links(text)
    assert links == [f"magnet:?xt=urn:btih:{A40}"]


def test_extract_with_tr_params_and_surrounding_text():
    line = f"标题 magnet:?xt=urn:btih:{B32}&tr=udp%3A%2F%2Fxx 后缀"
    links = extract_links(line)
    assert len(links) == 1 and links[0].startswith(f"magnet:?xt=urn:btih:{B32}")


def test_dedup_case_insensitive_keeps_first():
    text = f"magnet:?xt=urn:btih:{'A'*40}\nmagnet:?xt=urn:btih:{'a'*40}"
    assert len(extract_links(text)) == 1


def test_invalid_ignored():
    assert extract_links("magnet:?xt=urn:sha1:abc\nhttp://x.com\nbtih:123") == []


def test_hash_of_lowercase():
    assert hash_of(f"magnet:?xt=urn:btih:{'A'*40}") == "a" * 40


def test_filter_done():
    links = [f"magnet:?xt=urn:btih:{A40}", f"magnet:?xt=urn:btih:{B32.lower()}"]
    rest = filter_done(links, {A40})
    assert rest == [f"magnet:?xt=urn:btih:{B32.lower()}"]


def test_read_text_gbk(tmp_path):
    p = tmp_path / "t.txt"
    p.write_bytes(f"magnet:?xt=urn:btih:{A40}".encode("gbk"))
    assert len(extract_links(read_text(str(p)))) == 1


def test_read_text_utf8_bom(tmp_path):
    p = tmp_path / "t.txt"
    p.write_bytes(f"﻿magnet:?xt=urn:btih:{A40}".encode("utf-8"))
    assert len(extract_links(read_text(str(p)))) == 1
