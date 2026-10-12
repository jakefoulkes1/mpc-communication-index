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


def test_project_introduction_precedes_the_findings(page):
    intro = page.get_by_role("region", name="Does central bank communication help predict interest rates?")
    assert intro.is_visible()
    assert "I'm Jake Foulkes, an MPhil in Economics student at the University of Oxford." in intro.inner_text()
    assert "financial markets already expect" in intro.inner_text()
    assert "Every call is scored afterwards" in intro.inner_text()
    assert page.locator("#main > :first-child").get_attribute("id") == "about"
    assert intro.bounding_box()["y"] < page.locator("#summary").bounding_box()["y"]


def test_desktop_introduction_heading_uses_the_available_width(page):
    for width in [1280, 1366, 1440, 1920]:
        page.set_viewport_size({"width": width, "height": 900})
        assert page.locator("#about-h").evaluate("""el =>
            el.getBoundingClientRect().height <= parseFloat(getComputedStyle(el).lineHeight) + 1
        """), f"Introduction heading wraps unnecessarily at {width}px"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


@pytest.mark.parametrize("path", ["index.html", "methodology.html", "episodes.html"])
def test_page_and_footer_remain_contained_across_screen_sizes(page, site_url, path):
    page.goto(f"{site_url}/{path}", wait_until="networkidle")
    for width in [320, 390, 768, 1024, 1366, 1920, 2560]:
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        wrap = page.locator(".wrap").bounding_box()
        assert wrap["width"] <= 1200
        footer = page.locator("footer")
        notes = footer.locator("p").evaluate_all("""items => items.map(el => {
            const {x, y, width, height} = el.getBoundingClientRect();
            return {x, y, width, height};
        })""")
        author = footer.locator(".byline").bounding_box()
        if width > 760:
            assert author["x"] >= notes[0]["x"] + notes[0]["width"] + 20
            assert abs(author["y"] - notes[0]["y"]) <= 1
        else:
            assert abs(author["x"] - notes[0]["x"]) <= 1
            assert author["y"] >= notes[0]["y"] + notes[0]["height"]
        assert notes[-1]["y"] >= max(note["y"] + note["height"] for note in notes[:-1]) + 10
        if path != "index.html":
            reading = page.locator("#episodes-list" if path == "episodes.html" else ".section").first.bounding_box()
            contents = page.locator(".toc").bounding_box()
            assert reading["width"] <= 760
            assert abs(reading["x"] - contents["x"]) <= 1


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


def test_every_meeting_including_missing_vote_can_be_selected(page):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    for doc in load("index.json")["documents"]:
        page.locator("#meeting-select").select_option(doc["doc_id"])
        assert page.locator("#content").get_attribute("data-doc-id") == doc["doc_id"]
        assert page.locator("#score > span").first.inner_text() == f"{doc['abg_net_index']:.3f}"
        if doc["vote"] is None:
            assert "Not recorded" in page.locator("#meeting-facts").inner_text()
    assert not errors


@pytest.mark.parametrize("period", ["recent", "post"])
def test_filtered_overlays_stay_within_plot(page, period):
    page.locator("#period-select").select_option(period)
    for width in [1280, 390, 320]:
        page.set_viewport_size({"width": width, "height": 900})
        page.wait_for_timeout(250)
        geometry = page.locator("#chart").evaluate("""svg => {
          const bounds = svg.querySelector('#chart-plot-clip rect');
          const left = Number(bounds.getAttribute('x'));
          const right = left + Number(bounds.getAttribute('width'));
          const line = svg.querySelector('#layer-bankrate polyline');
          const xs = line.getAttribute('points').trim().split(/\\s+/).map(p => Number(p.split(',')[0]));
          return {left, right, xs, clipped: line.getAttribute('clip-path'),
            bandCount: svg.querySelectorAll('#layer-overlays rect').length};
        }""")
        assert all(geometry["left"] - 0.1 <= x <= geometry["right"] + 0.1 for x in geometry["xs"])
        assert geometry["clipped"] == "url(#chart-plot-clip)"
        assert geometry["bandCount"] == 0
        legend = page.locator("#chart-legend").inner_text()
        assert "Shaded band" not in legend and "Dashed rule" not in legend


def test_chart_describes_contemporaneous_not_following_decisions(page):
    description = page.locator("#chart-desc").text_content()
    assert "meetings announcing a hike" in description
    assert "followed by a hike" not in description
    page.locator("#toggle-decisions").uncheck()
    assert "Decision markers are hidden" in page.locator("#chart-desc").text_content()
    assert "Decision with these minutes" not in page.locator("#chart-legend").inner_text()


@pytest.mark.parametrize("target", ["index.html", "methodology.html", "episodes.html"])
def test_disclosures_remain_readable_when_theme_script_fails(page, site_url, target):
    page.route("**/site/theme.js", lambda route: route.abort())
    page.goto(f"{site_url}/{target}", wait_until="networkidle")
    for detail in page.locator("details").all():
        detail.evaluate("el => { el.open = false; }")
        detail.locator("summary").click()
        assert detail.locator(".disclosure-body").is_visible()


def test_archive_is_labelled_without_opening_more_detail(page):
    assert page.locator("#context-snapshot").is_visible()
    stamp = page.locator("#context-snapshot").inner_text()
    assert "Archived snapshot" in stamp and "not current pricing" in stamp
    assert "next" not in page.locator("#ois-h").text_content()


def test_hypothetical_example_matches_pipeline_scoring(page):
    from pipeline.predict.score_outcomes import brier_score

    assert page.locator("#how-it-works #scoring-lab").is_visible()
    for percent in [0, 20, 80, 100]:
        page.locator("#example-hold").fill(str(percent))
        for outcome in ["hold", "hike", "cut"]:
            page.locator(f'input[name="example-outcome"][value="{outcome}"]').check()
            probs = {"p_cut": 0, "p_hold": percent / 100, "p_hike": 1 - percent / 100}
            assert page.locator("#example-score").inner_text() == f"{brier_score(probs, outcome):.4f}"


@pytest.mark.parametrize("target", ["index.html", "methodology.html", "episodes.html"])
def test_shared_navigation_and_main_landmark(page, site_url, target):
    page.goto(f"{site_url}/{target}", wait_until="networkidle")
    assert page.locator("main#main").count() == 1
    current = page.get_by_role("navigation", name="Research pages").locator('[aria-current="page"]')
    assert current.get_attribute("href") == target
    assert page.locator('head link[href="site/dashboard.css"]').count() == 1
    if target == "methodology.html":
        assert page.locator("header .lede a").evaluate("el => getComputedStyle(el).color") == "rgb(255, 255, 255)"
