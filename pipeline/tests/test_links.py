"""Link check for every published surface.

Offline (pytest): every internal anchor on index.html, methodology.html and
README.md resolves to an element id or heading on the page it points at, and
every relative file link points at a file that exists in the repository.

Manual (network): the external URLs - the GitHub tag and commit pages, the
Bank of England source documents, the methodology page's cited news
releases - are listed and checked with their status codes when run as

    python -m pipeline.tests.test_links --external

which pytest never does: the suite makes no live network calls. Record the
output in DECISIONS.md when a pass depends on it (2026-09-02).
"""
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[2]
SURFACES = ("index.html", "methodology.html", "episodes.html", "README.md")


def _strip_scripts(raw: str) -> str:
    raw = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.S)
    return re.sub(r"<style\b.*?</style>", " ", raw, flags=re.S)


def hrefs(surface: str) -> list[str]:
    raw = (ROOT / surface).read_text()
    if surface.endswith(".md"):
        found = re.findall(r"\]\(([^)\s]+)\)", raw) + re.findall(r"<(https?://[^>]+)>", raw)
    else:
        found = re.findall(r'href="([^"]+)"', _strip_scripts(raw))
        found += re.findall(r'content="(https?://[^"]+)"', raw)
    return [h for h in found if not h.startswith(("data:", "mailto:"))]


def github_slug(heading: str) -> str:
    """GitHub's heading-anchor rule: lowercase, drop punctuation, spaces to hyphens."""
    s = re.sub(r"[`*]", "", heading).strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s", "-", s)


def test_github_slug_preserves_underscores_in_source_names():
    assert github_slug("market_probs: two-state ±25bp assumption") == "market_probs-two-state-25bp-assumption"


def anchors(target: str) -> set[str]:
    raw = (ROOT / target).read_text()
    if target.endswith(".md"):
        return {github_slug(h) for h in re.findall(r"^#{1,6}\s+(.*)$", raw, flags=re.M)}
    return set(re.findall(r'\sid="([^"$]+)"', raw))


def split(href: str) -> tuple[str, str | None]:
    path, _, frag = href.partition("#")
    return path, (frag or None)


@pytest.mark.parametrize("surface", SURFACES)
def test_internal_anchors_resolve(surface):
    for href in hrefs(surface):
        if href.startswith(("http://", "https://")):
            continue
        path, frag = split(href)
        target = surface if not path else path
        assert (ROOT / target).exists(), f"{surface} links to {href!r} but {target} does not exist"
        if frag:
            assert frag in anchors(target), (
                f"{surface} links to {href!r} but {target} has no anchor {frag!r}"
            )


@pytest.mark.parametrize("surface", SURFACES)
def test_relative_file_links_exist(surface):
    for href in hrefs(surface):
        if href.startswith(("http://", "https://", "#")):
            continue
        path, _ = split(href)
        assert (ROOT / path).exists(), f"{surface} links to {href!r} but {path} is not in the repository"


def external_urls() -> list[str]:
    seen: list[str] = []
    for surface in SURFACES:
        for href in hrefs(surface):
            if href.startswith(("http://", "https://")) and href not in seen:
                seen.append(href)
    return seen


def test_the_tag_and_source_document_are_linked():
    """The two links a sceptical reader needs most: the lock tag and the Bank's
    own copy of the latest minutes."""
    import json

    from pipeline.site_figures import AUTHOR, prediction_file

    tag = Path(prediction_file()).stem
    urls = external_urls()
    assert f"{AUTHOR['repo']}/releases/tag/{tag}" in urls
    latest = json.loads((ROOT / "data/index.json").read_text())["documents"][-1]["source_url"]
    assert latest in urls


@pytest.mark.parametrize("surface", SURFACES)
def test_repository_source_links_resolve_locally(surface):
    """Code and log citations must point at real files and existing headings."""
    from pipeline.site_figures import AUTHOR

    prefix = f"{AUTHOR['repo']}/blob/main/"
    for href in hrefs(surface):
        if not href.startswith(prefix):
            continue
        target = urlsplit(href[len(prefix):])
        path = unquote(target.path)
        assert (ROOT / path).is_file(), f"{surface}: missing source file in {href}"
        if target.fragment:
            assert unquote(target.fragment) in anchors(path), (
                f"{surface}: missing source heading in {href}"
            )


@pytest.mark.parametrize("surface,region", [
    ("index.html", "relatedwork"), ("methodology.html", "references"),
])
def test_bibliography_is_a_shared_list_of_direct_links(surface, region):
    from html.parser import HTMLParser

    from pipeline.build_fallbacks import RELATED_WORK, related_work_html

    raw = (ROOT / surface).read_text()
    block = re.search(
        rf"<!-- fallback:{region} -->\s*(.*?)\s*<!-- /fallback:{region} -->", raw, re.S
    ).group(1)
    assert block == related_work_html().strip()

    class References(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links = []
            self.in_link = False
            self.unlinked = []

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                self.in_link = True
                self.links.append(dict(attrs)["href"])

        def handle_endtag(self, tag):
            if tag == "a":
                self.in_link = False

        def handle_data(self, data):
            if data.strip() and not self.in_link:
                self.unlinked.append(data)

    references = References()
    references.feed(block)
    assert references.links == [entry["url"] for entry in RELATED_WORK]
    assert all(link.startswith("https://") for link in references.links)
    assert not references.unlinked


def test_inline_methodology_sources_are_links_not_parenthetical_notes():
    raw = (ROOT / "methodology.html").read_text()
    assert not re.search(r'<span\s+class="ref"', raw)
    assert re.search(r'<a\s+class="ref"\s+href="', raw)


def test_current_public_links_follow_the_repository_name():
    from pipeline.site_figures import AUTHOR

    assert AUTHOR["site"] == "https://jakefoulkes1.github.io/mpc-communication-index/"
    assert AUTHOR["repo"] == "https://github.com/jakefoulkes1/mpc-communication-index"
    for surface in (*SURFACES, "CITATION.cff", "LOCKDAY.md"):
        raw = (ROOT / surface).read_text()
        assert "https://jakefoulkes1.github.io/mpc-index/" not in raw, surface
        assert "https://github.com/jakefoulkes1/mpc-index" not in raw, surface
    for surface in SURFACES:
        if not surface.endswith(".html"):
            continue
        raw = (ROOT / surface).read_text()
        page = "" if surface == "index.html" else surface
        assert f'property="og:url" content="{AUTHOR["site"]}{page}"' in raw
        assert f'property="og:image" content="{AUTHOR["site"]}og-image.png"' in raw
        assert f'name="twitter:image" content="{AUTHOR["site"]}og-image.png"' in raw


# A publisher that refuses a scripted request has still been reached; a link
# that 404s has not. 403 and 429 are therefore reported and not counted as
# failures - both DOIs in the reference list redirect to a publisher that
# blocks non-browser agents, while resolving correctly at doi.org itself.
# See DECISIONS.md, 2026-09-02 (close-out).
REACHED_BUT_REFUSED = (403, 429)


def check_external() -> int:
    """Fetch every external URL and print its status. Network; manual only.

    Uses requests (already a project dependency) rather than urllib, because
    the macOS system Python ships without a CA bundle and fails every HTTPS
    verification; requests carries certifi.
    """
    import requests

    worst = 0
    for url in external_urls():
        note = ""
        try:
            code = requests.get(url, headers={"User-Agent": "mpc-index link check"}, timeout=20).status_code
            if code in REACHED_BUT_REFUSED:
                # Did the redirect happen at all? For a DOI, the registry's own
                # 302 is what says the identifier is live.
                first = requests.get(url, allow_redirects=False, timeout=20)
                if first.status_code in (301, 302, 303, 307, 308):
                    note = f"  (reached; publisher refused the robot, resolves to {first.headers.get('Location', '?')})"
                else:
                    note = "  (reached; refused the robot)"
        except Exception as e:  # noqa: BLE001 - report, don't raise
            code = f"error: {e}"
        print(f"{code}\t{url}{note}")
        if not isinstance(code, int) or (code >= 400 and code not in REACHED_BUT_REFUSED):
            worst = 1
    return worst


if __name__ == "__main__":
    if "--external" in sys.argv:
        sys.exit(check_external())
    print("\n".join(external_urls()))
