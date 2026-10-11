"""Routine collection must not silently destroy or truncate the raw corpus."""
from types import SimpleNamespace

import pytest
import requests

from pipeline.scrape import era, minutes


def test_cached_pdf_text_is_preserved_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr(minutes, "ROOT", tmp_path)
    raw = tmp_path / "data/raw"
    raw.mkdir(parents=True)
    path = raw / "2019-12-minutes.txt"
    path.write_bytes(b"complete PDF-derived minutes")
    monkeypatch.setattr(minutes.requests, "get", lambda *a, **k: pytest.fail("must not fetch cached text"))
    assert minutes.scrape_month(2019, "december") == path
    assert path.read_bytes() == b"complete PDF-derived minutes"


def test_partial_html_cache_requires_inspection(tmp_path, monkeypatch):
    monkeypatch.setattr(minutes, "ROOT", tmp_path)
    raw = tmp_path / "data/raw/html"
    raw.mkdir(parents=True)
    (raw / "2019-12-minutes.html").write_text("partial")
    monkeypatch.setattr(minutes.requests, "get", lambda *a, **k: pytest.fail("must not fetch partial cache"))
    with pytest.raises(FileExistsError, match="incomplete cache"):
        minutes.scrape_month(2019, "december")


@pytest.mark.parametrize("status", [403, 429, 500])
def test_era_stops_on_non_404_http_failures(monkeypatch, status):
    def fail(*args):
        raise requests.HTTPError(response=SimpleNamespace(status_code=status))
    monkeypatch.setattr(era, "scrape_month", fail)
    with pytest.raises(requests.HTTPError):
        era.main()


def test_pdf_provenance_survives_a_later_fetch_failure(tmp_path, monkeypatch):
    import json
    from pipeline.scrape import backfill_pdf

    for month in [1, 2]:
        (tmp_path / f"2019-{month:02d}-minutes.txt").write_text("summary only")
    provenance = tmp_path / "source_kind.json"
    monkeypatch.setattr(backfill_pdf, "RAW", tmp_path)
    monkeypatch.setattr(backfill_pdf, "PDF_DIR", tmp_path / "pdf")
    monkeypatch.setattr(backfill_pdf, "SOURCE_KIND_PATH", provenance)
    monkeypatch.setattr(backfill_pdf.time, "sleep", lambda _: None)
    monkeypatch.setattr(backfill_pdf, "extract_pdf_text", lambda _: "Minutes " * 500)
    def fetch(url, **kwargs):
        if 'february' in url:
            raise requests.HTTPError(response=SimpleNamespace(status_code=503))
        return SimpleNamespace(content=b"fixture", raise_for_status=lambda: None)
    monkeypatch.setattr(backfill_pdf.requests, "get", fetch)
    with pytest.raises(requests.HTTPError):
        backfill_pdf.main()
    assert json.loads(provenance.read_text())["2019-01-minutes.txt"] == "pdf"
    assert (tmp_path / "2019-02-minutes.txt").read_text() == "summary only"
