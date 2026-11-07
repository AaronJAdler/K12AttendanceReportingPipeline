"""Run axe-core (WCAG 2.0/2.1 A and AA rules) on every built page; exit 1 on any violation.

Usage: python scripts/check_a11y.py site [--chrome /usr/bin/google-chrome]
Needs ``npm ci`` (for axe-core) and a Chromium: ``playwright install chromium`` in CI.
Writes ``a11y-report.json`` next to the site directory. Automated checks cover only part
of WCAG; the manual keyboard and screen-reader pass is recorded in the README.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

AXE = Path(__file__).resolve().parents[1] / "node_modules" / "axe-core" / "axe.min.js"
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("site", type=Path)
    ap.add_argument("--chrome", default=None, help="path to a Chrome/Chromium binary")
    ap.add_argument("--screenshot", type=Path, default=None, help="save index.html screenshot")
    a = ap.parse_args()

    pages = sorted(a.site.glob("*.html"))
    report: dict[str, list[dict[str, object]]] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=a.chrome) if a.chrome else p.chromium.launch()
        page = browser.new_page()
        for html in pages:
            page.goto(html.resolve().as_uri())
            page.add_script_tag(path=str(AXE))
            result = page.evaluate(
                "tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", TAGS
            )
            report[html.name] = [
                {"id": v["id"], "impact": v["impact"], "nodes": len(v["nodes"]), "help": v["help"]}
                for v in result["violations"]
            ]
            print(
                f"{html.name}: {len(result['passes'])} rules passed, "
                f"{len(result['violations'])} violations"
            )
        if a.screenshot:
            page.goto((a.site / "index.html").resolve().as_uri())
            page.set_viewport_size({"width": 1100, "height": 900})
            page.screenshot(path=str(a.screenshot), full_page=True)
        browser.close()

    (a.site.parent / "a11y-report.json").write_text(json.dumps(report, indent=2))
    bad = {k: v for k, v in report.items() if v}
    for name, vs in bad.items():
        for v in vs:
            print(f"VIOLATION {name}: {v['id']} ({v['impact']}, {v['nodes']} nodes) {v['help']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
