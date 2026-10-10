"""The dashboard displays published observations without changing evaluation."""
import json
from pathlib import Path

import pytest

from pipeline.tests.test_static_js_parity import site_url  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def page(site_url):
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        try:
            browser = runtime.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.goto(site_url, wait_until="networkidle")
        yield page
        context.close()
        browser.close()


def load(name):
    return json.loads((ROOT / "data" / name).read_text())


def test_meeting_selection_uses_the_selected_observation_and_following_decision(page):
    documents = load("index.json")["documents"]
    first = documents[0]
    page.locator("#meeting-select").select_option(first["doc_id"])
    assert page.locator("#score > span").first.inner_text() == f"{first['abg_net_index']:.3f}"
    facts = page.locator("#meeting-facts").inner_text()
    assert f"{first['abg_hawk']} hawkish / {first['abg_dove']} dovish" in facts
    assert first["vote"].replace("-", "\u2013") in facts
    assert "Decision that followed" in facts
    page.locator("#meeting-select").select_option(documents[-1]["doc_id"])
    assert "Not yet observed" in page.locator("#meeting-facts").inner_text()


def test_period_filter_preserves_evaluation_scores_and_overlay_choices(page):
    table = page.locator("#ladder-tbody").inner_text()
    page.locator("#toggle-bankrate").uncheck()
    page.locator("#toggle-decisions").uncheck()
    page.locator("#period-select").select_option("post")
    start = load("inference_v1.json")["fragility_check_subsample"]["start_date"]
    expected = [doc["doc_id"] for doc in load("index.json")["documents"] if doc["published"] >= start]
    options = page.locator("#meeting-select option").evaluate_all("items => items.map(item => item.value)")
    assert set(options) == set(expected)
    assert page.locator("#ladder-tbody").inner_text() == table
    assert not page.locator("#layer-bankrate").is_visible()
    assert not page.locator("#layer-decisions").is_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_function("document.querySelector('#chart').viewBox.baseVal.width < 460")
    assert not page.locator("#layer-bankrate").is_visible()
    assert not page.locator("#layer-decisions").is_visible()
    assert page.locator("[data-inspector-marker]").count() == 1


def test_metric_switches_and_selected_models_use_published_scores(page):
    scores = load("ladder_v1.json")["headline_scores_scheduled_only"]
    for metric, field in [("brier", "mean_brier"), ("log", "mean_log_score"), ("skill", "skill_vs_l1")]:
        page.locator(f"[data-metric='{metric}']").click()
        for model in ["L2", "L3", "L4"]:
            row = page.locator(f".model-bar[data-model='{model}']")
            expected = f"{scores[model][field]:.4f}".replace("-", "\u2212")
            assert row.locator(".model-bar-value").inner_text() == expected
            row.click()
            assert page.locator(".insight-value").inner_text() == expected
    page.locator("#show-baseline").check()
    assert page.locator(".model-bar[data-model='L0'] .model-bar-value").inner_text() == "\u2014"


def test_method_tabs_work_with_keyboard(page):
    language = page.get_by_role("tab", name="Language", exact=True)
    language.focus()
    language.press("ArrowRight")
    assert page.get_by_role("tab", name="Market", exact=True).get_attribute("aria-selected") == "true"
    assert page.locator("#method-panel-market").is_visible()
    assert not page.locator("#method-panel-language").is_visible()


def test_mobile_tooltip_stays_inside_the_plot(page):
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_function("document.querySelector('#chart').viewBox.baseVal.width < 460")
    chart = page.locator("#chart")
    bounds = chart.bounding_box()
    chart.click(position={"x": bounds["width"] - 20, "y": 100})
    chart.hover(position={"x": bounds["width"] - 22, "y": 100})
    page.locator("#chart-tip").wait_for(state="visible")
    tip = page.locator("#chart-tip").bounding_box()
    bounds = chart.bounding_box()
    assert tip["x"] >= bounds["x"]
    assert tip["x"] + tip["width"] <= bounds["x"] + bounds["width"]


def test_failed_fetch_keeps_the_published_table_and_reading(page, site_url):
    page.route("**/data/index.json", lambda route: route.abort())
    page.route("**/data/ladder_v1.json", lambda route: route.abort())
    page.goto(site_url, wait_until="networkidle")
    assert not page.locator("#explorer-toolbar").is_visible()
    assert not page.locator("#comparison-tool").is_visible()
    page.get_by_text("All scores and sample counts", exact=True).click()
    assert page.locator("#ladder-tbody").is_visible()
    assert page.locator("#ladder-tbody tr").count() == 5
    assert page.locator("#score").is_visible()
