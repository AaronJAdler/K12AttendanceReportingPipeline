"""Build the static dashboard, the ArcGIS map page and the private error reports.

Public output (``site/``) holds only suppressed aggregates. Student-level findings with
local IDs go to ``private/``, which is never deployed. Every page except the map is
plain HTML and CSS; the map page loads the ArcGIS Maps SDK and repeats its data in a
table so nothing depends on JavaScript.
"""

from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path

import duckdb

from k12att.constants import ACADEMIC_YEAR, DISTRICT_NAME, SUPPRESSED
from k12att.generate import SCHOOL_NAMES
from k12att.geo import MAP_CENTER, SCHOOL_POINTS
from k12att.rules import ALL_RULES
from k12att.strings import CATEGORY_LABELS, EN
from k12att.suppression import Cell, suppress

T = EN
ARCGIS_SDK = "https://js.arcgis.com/5.1/"
DIMENSIONS = {
    "TA": "total",
    **dict.fromkeys(("GM", "GF", "GX", "GZ"), "gender"),
    **dict.fromkeys(("RB", "RI", "RA", "RF", "RH", "RD", "RP", "RT", "RW"), "race"),
    **dict.fromkeys(("GRTKKN", "GR13", "GR46", "GR78", "GR912"), "grade_span"),
}
ORDER = list(DIMENSIONS)
# Rate bands used on the map and the school table. Each band also has a text label.
BANDS = (
    (0.0, 20.0, "Under 20%", "#1d8f7e"),
    (20.0, 25.0, "20-25%", "#c98a12"),
    (25.0, 101.0, "25% or more", "#d1495b"),
)

CSS = """
:root {
  --ink: #14213d; --muted: #4a5568; --bg: #f2f5fb; --card: #ffffff;
  --navy: #0b2545; --blue: #13497a; --teal: #1d8f7e; --line: #d8dfeb;
  --radius: 16px; --shadow: 0 10px 30px rgba(11, 37, 69, .10), 0 2px 6px rgba(11, 37, 69, .06);
}
* { box-sizing: border-box; }
body { margin: 0; font-family: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
       color: var(--ink); background: var(--bg); line-height: 1.55; }
a { color: #0b4f8a; }
a:focus-visible, summary:focus-visible { outline: 3px solid #f4a261; outline-offset: 3px;
       border-radius: 6px; }
.skip { position: absolute; left: -9999px; }
.skip:focus { left: 1rem; top: 1rem; background: #fff; color: var(--ink); padding: .6rem 1rem;
       border-radius: 8px; z-index: 10; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
       overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
.wrap { max-width: 72rem; margin: 0 auto; padding: 0 1.25rem; }

.hero { color: #fff; padding: 1.25rem 0 4.5rem; position: relative; overflow: hidden;
  background:
    radial-gradient(60rem 30rem at 85% -10%, rgba(29, 143, 126, .55), transparent 60%),
    radial-gradient(40rem 25rem at 0% 120%, rgba(244, 162, 97, .35), transparent 60%),
    linear-gradient(135deg, #0b2545 0%, #13497a 55%, #134074 100%); }
.hero a { color: #fff; }
.topbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: 1rem; }
.brand { display: flex; align-items: center; gap: .65rem; font-weight: 700;
  letter-spacing: .01em; }
.logo { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center;
  background: linear-gradient(135deg, #f4a261, #e76f51); color: #0b2545; font-weight: 800; }
nav ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: .5rem; }
nav a { display: inline-block; padding: .45rem .95rem; border-radius: 999px; text-decoration: none;
  background: rgba(255, 255, 255, .10); border: 1px solid rgba(255, 255, 255, .25); }
nav a:hover { background: rgba(255, 255, 255, .22); }
nav a[aria-current="page"] { background: #fff; color: var(--navy); font-weight: 700; }
.eyebrow { text-transform: uppercase; letter-spacing: .14em; font-size: .8rem; font-weight: 700;
  color: #ffd8b5; margin: 2.25rem 0 .25rem; }
.hero h1 { font-size: clamp(2rem, 4.5vw, 3.2rem); line-height: 1.1; margin: 0 0 .75rem;
  letter-spacing: -.02em; }
.hero .lead { font-size: 1.15rem; max-width: 46rem; margin: 0; color: #e8eef8; }
.pill-synth { display: inline-block; margin-top: 1.25rem; padding: .4rem .85rem; border-radius: 999px;
  background: #fff4d6; color: #5c3d00; font-size: .9rem; font-weight: 600; }

main { margin-top: -3rem; position: relative; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 1rem; }
.kpi { background: var(--card); border-radius: var(--radius); box-shadow: var(--shadow);
  padding: 1.1rem 1.25rem; border-top: 5px solid var(--accent, var(--teal)); }
.kpi .label { color: var(--muted); font-size: .9rem; font-weight: 600; margin: 0; }
.kpi .value { font-size: 2.1rem; font-weight: 800; letter-spacing: -.02em; margin: .15rem 0 0; }
.kpi .sub { color: var(--muted); font-size: .88rem; margin: .15rem 0 0; }

.card { background: var(--card); border-radius: var(--radius); box-shadow: var(--shadow);
  padding: 1.4rem 1.5rem; margin: 1.5rem 0; }
.card h2 { margin: 0 0 .25rem; font-size: 1.35rem; letter-spacing: -.01em; }
.card { overflow-x: auto; }
.card .hint { color: var(--muted); margin: 0 0 1rem; font-size: .95rem; }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(30rem, 1fr)); gap: 1.5rem; }
.grid2 > .card { margin: 0; }
@media (max-width: 40rem) { .grid2 { grid-template-columns: 1fr; } }

table { width: 100%; border-collapse: separate; border-spacing: 0; margin: .5rem 0 0;
  font-size: .95rem; }
th, td { padding: .55rem .75rem; text-align: left; border-bottom: 1px solid var(--line); }
thead th { background: #eef2f9; color: #24324d; font-weight: 700; font-size: .85rem;
  text-transform: uppercase; letter-spacing: .04em; }
thead th:first-child { border-top-left-radius: 10px; }
thead th:last-child { border-top-right-radius: 10px; }
tbody tr:nth-child(even) { background: #f8fafd; }
tbody tr:hover { background: #eef6f4; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.ratecell { display: flex; align-items: center; justify-content: flex-end; gap: .6rem; }
.meter { width: 7rem; height: .55rem; border-radius: 999px; background: #e6ebf3; overflow: hidden; }
.meter > span { display: block; height: 100%; border-radius: 999px; }
.tag { display: inline-block; white-space: nowrap; padding: .1rem .55rem; border-radius: 999px; font-size: .78rem;
  font-weight: 700; background: #eef2f9; color: #24324d; }

.status { display: inline-flex; align-items: center; gap: .35rem; padding: .25rem .7rem;
  border-radius: 999px; font-weight: 700; font-size: .88rem; }
.status.ok { background: #e3f6ea; color: #14532d; }
.status.bad { background: #fde8e8; color: #8a1c1c; }
.callout { display: flex; gap: 1rem; align-items: flex-start; border-left: 6px solid #d1495b; }
.callout.ok { border-left-color: var(--teal); }
.timeline { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: 1rem;
  list-style: none; padding: 0; margin: 0; }
.timeline li { border: 1px solid var(--line); border-radius: 12px; padding: 1rem; background: #fbfcfe; }
.timeline .date { font-weight: 800; font-size: 1.1rem; margin: 0 0 .35rem; }
.timeline p { margin: .35rem 0 0; color: var(--muted); }
details { border: 1px solid var(--line); border-radius: 12px; padding: .75rem 1rem; margin: .75rem 0;
  background: #fbfcfe; }
summary { cursor: pointer; font-weight: 700; }

svg.chart text { font-family: inherit; font-size: 13px; fill: #14213d; }
svg.chart .val { font-weight: 700; }
arcgis-map { display: block; height: 34rem; border-radius: 12px; overflow: hidden;
  border: 1px solid var(--line); }
.legend { display: flex; flex-wrap: wrap; gap: 1rem; margin: .75rem 0 0; padding: 0;
  list-style: none; color: var(--muted); font-size: .92rem; }
.legend span { display: inline-block; width: .9rem; height: .9rem; border-radius: 50%;
  vertical-align: -2px; margin-right: .35rem; }

footer { background: var(--navy); color: #d7e1f0; margin-top: 3rem; padding: 2rem 0; font-size: .92rem; }
footer p { margin: .4rem 0; max-width: 52rem; }
footer a { color: #ffd8b5; }
"""


def _nav(active: str) -> str:
    items = (
        ("index.html", T["nav_overview"]),
        ("map.html", "School map"),
        ("readiness.html", T["nav_readiness"]),
    )
    current = ' aria-current="page"'
    links = "".join(
        f'<li><a href="{href}"{current if href == active else ""}>{label}</a></li>'
        for href, label in items
    )
    return f'<nav aria-label="Main"><ul>{links}</ul></nav>'


def _page(
    title: str,
    active: str,
    eyebrow: str,
    heading: str,
    lead: str,
    body: str,
    head_extra: str = "",
    tail_extra: str = "",
) -> str:
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 '
        "viewBox=%220 0 32 32%22%3E%3Crect width=%2232%22 height=%2232%22 rx=%228%22 "
        'fill=%22%23e76f51%22/%3E%3C/svg%3E">\n'
        f"<title>{escape(title)} | {T['site_title']}</title>\n<style>{CSS}</style>\n"
        f"{head_extra}</head>\n<body>\n"
        '<a class="skip" href="#main">Skip to main content</a>\n'
        '<header class="hero"><div class="wrap">'
        '<div class="topbar"><div class="brand"><span class="logo" aria-hidden="true">R</span>'
        f"<span>{T['site_title']}</span></div>{_nav(active)}</div>"
        f'<p class="eyebrow">{escape(eyebrow)}</p><h1>{escape(heading)}</h1>'
        f'<p class="lead">{lead}</p>'
        f'<p class="pill-synth" role="note">{T["synthetic_banner"]}</p>'
        "</div></header>\n"
        f'<main id="main" class="wrap">\n{body}\n</main>\n'
        '<footer><div class="wrap">'
        f"<p>{T['definition_note']}</p><p>{T['suppression_note']}</p>"
        '<p>Source code and verification notes: <a href="https://github.com/AaronJAdler/'
        'K12AttendanceReportingPipeline">github.com/AaronJAdler/K12AttendanceReportingPipeline</a>'
        "</p></div></footer>\n"
        f"{tail_extra}</body>\n</html>\n"
    )


def _band(rate: float) -> tuple[str, str]:
    for lo, hi, label, color in BANDS:
        if lo <= rate < hi:
            return label, color
    return BANDS[-1][2], BANDS[-1][3]


def _kpi(label: str, value: str, sub: str = "", accent: str = "#1d8f7e") -> str:
    sub_html = f'<p class="sub">{sub}</p>' if sub else ""
    return (
        f'<div class="kpi" style="--accent:{accent}"><p class="label">{label}</p>'
        f'<p class="value">{value}</p>{sub_html}</div>'
    )


def _fmt(c: Cell) -> tuple[str, str, str]:
    if c.suppressed:
        return SUPPRESSED, SUPPRESSED, SUPPRESSED
    rate = c.rate_pct
    return f"{c.eligible:,}", f"{c.chronic:,}", "" if rate is None else f"{rate:.1f}"


def _rate_cell(c: Cell) -> str:
    if c.suppressed or c.rate_pct is None:
        return f'<td class="num">{SUPPRESSED}</td>'
    _, color = _band(c.rate_pct)
    width = min(100.0, c.rate_pct * 2.5)
    return (
        f'<td class="num"><div class="ratecell"><span class="meter" aria-hidden="true">'
        f'<span style="width:{width:.0f}%;background:{color}"></span></span>'
        f"{c.rate_pct:.1f}</div></td>"
    )


def _table(caption: str, cells: list[Cell], label_header: str) -> str:
    rows = "".join(
        f'<tr><th scope="row">{escape(CATEGORY_LABELS.get(c.category, c.category))}</th>'
        f'<td class="num">{_fmt(c)[0]}</td><td class="num">{_fmt(c)[1]}</td>{_rate_cell(c)}</tr>'
        for c in cells
    )
    return (
        f'<table><caption class="sr-only">{escape(caption)}</caption><thead><tr>'
        f'<th scope="col">{label_header}</th><th scope="col" class="num">{T["col_eligible"]}</th>'
        f'<th scope="col" class="num">{T["col_chronic"]}</th>'
        f'<th scope="col" class="num">{T["col_rate"]}</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
    )


def bar_chart(chart_id: str, title: str, cells: list[Cell]) -> str:
    """Horizontal gradient bars with direct value labels; color carries no meaning alone."""
    row_h, label_w, bar_w = 34, 230, 380
    rates = [c.rate_pct for c in cells if not c.suppressed and c.rate_pct is not None]
    top = max(10.0, ((max(rates) if rates else 10.0) * 1.2 // 10 + 1) * 10)
    height = row_h * len(cells) + 8
    parts = [
        f'<defs><linearGradient id="{chart_id}-g" x1="0" x2="1" y1="0" y2="0">'
        '<stop offset="0" stop-color="#13497a"/><stop offset="1" stop-color="#1d8f7e"/>'
        "</linearGradient></defs>"
    ]
    for i, c in enumerate(cells):
        y = 4 + i * row_h
        label = escape(CATEGORY_LABELS.get(c.category, c.category))
        parts.append(f'<text x="0" y="{y + 20}">{label}</text>')
        parts.append(
            f'<rect x="{label_w}" y="{y + 7}" width="{bar_w}" height="18" rx="9" fill="#e9eef6"/>'
        )
        if c.suppressed or c.rate_pct is None:
            parts.append(f'<text x="{label_w + 10}" y="{y + 21}">{SUPPRESSED} hidden</text>')
            continue
        w = min(float(bar_w), max(6.0, bar_w * c.rate_pct / top))
        parts.append(
            f'<rect x="{label_w}" y="{y + 7}" width="{w:.1f}" height="18" rx="9" '
            f'fill="url(#{chart_id}-g)"/>'
            f'<text class="val" x="{label_w + w + 8:.1f}" y="{y + 21}">{c.rate_pct:.1f}%</text>'
        )
    return (
        f'<svg class="chart" role="img" aria-labelledby="{chart_id}-t {chart_id}-d" width="100%" '
        f'viewBox="0 0 {label_w + bar_w + 70} {height}" preserveAspectRatio="xMinYMin meet">'
        f'<title id="{chart_id}-t">{escape(title)}</title>'
        f'<desc id="{chart_id}-d">{T["chart_desc_prefix"]} Scale 0 to {top:.0f} percent.</desc>'
        + "".join(parts)
        + "</svg>"
    )


def _cells(con: duckdb.DuckDBPyConnection) -> list[Cell]:
    rows = con.execute(
        "select coalesce(school_code, 'district'), reporting_category, "
        "eligible_enrollment, chronic_count from mart_chronic_absenteeism"
    ).fetchall()
    return suppress([Cell(e, DIMENSIONS[cat], cat, int(n), int(k)) for e, cat, n, k in rows])


def _sections(entity: str, cells: list[Cell], prefix: str) -> str:
    mine = sorted((c for c in cells if c.entity == entity), key=lambda c: ORDER.index(c.category))
    cards = []
    for dim, key in (("grade_span", "by_grade_span"), ("gender", "by_gender"), ("race", "by_race")):
        group = [c for c in mine if c.dimension == dim]
        if not group:
            continue
        cards.append(
            f'<section class="card" aria-labelledby="{prefix}-{dim}-h">'
            f'<h2 id="{prefix}-{dim}-h">{T[key]}</h2>'
            '<p class="hint">Share of eligible students who were chronically absent.</p>'
            + bar_chart(f"{prefix}-{dim}", T[key], group)
            + _table(T[key], group, T["col_category"])
            + "</section>"
        )
    return "".join(cards)


# ---------------------------------------------------------------- readiness helpers


def _batch_rejection(con: duckdb.DuckDBPyConnection, batch: str) -> list[tuple[str, int, int]]:
    """(school name, previous rows, current rows) for each school that tripped RB-BATCH-01."""
    prev_row = con.execute(
        "select max(batch_id) from batches where status = 'accepted' and batch_id < ?", [batch]
    ).fetchone()
    prev = prev_row[0] if prev_row else None
    schools = [
        r[0]
        for r in con.execute(
            "select school_code from validation_results where batch_id = ? and rule_id = 'RB-BATCH-01' "
            "order by 1",
            [batch],
        ).fetchall()
    ]
    out = []
    for s in schools:

        def n(b: str | None, school: str = s) -> int:
            row = con.execute(
                "select count(*) from senr where batch_id = ? and school_code = ?", [b, school]
            ).fetchone()
            return int(row[0]) if row else 0

        out.append((SCHOOL_NAMES.get(s, s), n(prev), n(batch)))
    return out


def _status_pill(status: str) -> str:
    if status == "accepted":
        return '<span class="status ok"><span aria-hidden="true">&#10003;</span> Accepted</span>'
    return '<span class="status bad"><span aria-hidden="true">&#10005;</span> Rejected</span>'


def _readiness(con: duckdb.DuckDBPyConnection, current: str) -> str:
    batches = con.execute("select batch_id, status from batches order by batch_id desc").fetchall()
    latest, status = batches[0]
    counts = {
        b: (int(f), int(w))
        for b, f, w in con.execute(
            "select batch_id, count(*) filter (where severity='Fatal'), "
            "count(*) filter (where severity='Warning') from validation_results group by 1"
        ).fetchall()
    }

    if status == "accepted":
        callout = (
            f'<section class="card callout ok"><div>{_status_pill(status)}'
            f"<h2>Batch {latest} was accepted</h2><p>It has "
            f"{counts.get(latest, (0, 0))[0]:,} Fatal findings.</p></div></section>"
        )
    else:
        moved = _batch_rejection(con, latest)
        why = "; ".join(
            f"{name} went from {p:,} to {c:,} enrollment rows ({(c - p) / p:+.0%})" if p else name
            for name, p, c in moved
        )
        callout = (
            f'<section class="card callout"><div>{_status_pill(status)}'
            f"<h2>Batch {latest} was rejected</h2>"
            f"<p>{escape(why)}. A change of more than 20% from the last accepted batch usually "
            f"means a partial extract, so the whole batch was held back.</p>"
            f"<p>Reports still use batch <strong>{current}</strong>.</p></div></section>"
        )

    kpis = (
        '<div class="kpis">'
        + "".join(
            [
                _kpi(
                    "Latest submission",
                    latest,
                    "Rejected" if status != "accepted" else "Accepted",
                    "#d1495b" if status != "accepted" else "#1d8f7e",
                ),
                _kpi("Reported batch", current, "Newest accepted submission", "#13497a"),
                _kpi(
                    "Fatal findings, first submission",
                    f"{counts.get(batches[-1][0], (0, 0))[0]:,}",
                    f"Batch {batches[-1][0]}",
                    "#f4a261",
                ),
                _kpi("Validation rules", str(len(ALL_RULES)), "Fatal and Warning", "#6c5ce7"),
            ]
        )
        + "</div>"
    )

    timeline = (
        '<ol class="timeline">'
        + "".join(
            f'<li><p class="date">{b}</p>{_status_pill(s)}'
            f"<p>{counts.get(b, (0, 0))[0]:,} Fatal &middot; {counts.get(b, (0, 0))[1]:,} Warnings</p></li>"
            for b, s in batches
        )
        + "</ol>"
    )
    history = (
        '<section class="card" aria-labelledby="hist-h">'
        f'<h2 id="hist-h">{T["history_heading"]}</h2>'
        '<p class="hint">Newest first. Rejected batches never reach the reports.</p>'
        f"{timeline}</section>"
    )

    detail_parts = []
    for b, _ in batches:
        school_rows = con.execute(
            "select school_code, count(*) filter (where severity='Fatal'), "
            "count(*) filter (where severity='Warning') from validation_results "
            "where batch_id = ? group by 1 order by 2 desc, 1",
            [b],
        ).fetchall()
        rule_counts = dict(
            con.execute(
                "select rule_id, count(*) from validation_results where batch_id = ? group by 1",
                [b],
            ).fetchall()
        )
        srows = "".join(
            f'<tr><th scope="row">{escape(SCHOOL_NAMES.get(s, s))}</th>'
            f'<td class="num">{f:,}</td><td class="num">{w:,}</td></tr>'
            for s, f, w in school_rows
        )
        rrows = "".join(
            f'<tr><th scope="row"><span class="tag">{r.rule_id}</span></th><td>{r.severity}</td>'
            f"<td>{escape(r.description)}</td>"
            f'<td class="num">{int(rule_counts.get(r.rule_id, 0)):,}</td></tr>'
            for r in ALL_RULES
        )
        detail_parts.append(
            f"<details{' open' if b == latest else ''}><summary>Batch {b} findings</summary>"
            f"<table><caption>{T['findings_heading'].format(batch=b)}</caption><thead><tr>"
            f'<th scope="col">{T["col_school"]}</th>'
            f'<th scope="col" class="num">{T["col_fatal"]}</th>'
            f'<th scope="col" class="num">{T["col_warning"]}</th></tr></thead>'
            f"<tbody>{srows}</tbody></table>"
            f"<table><caption>{T['rules_heading'].format(batch=b)}</caption><thead><tr>"
            f'<th scope="col">{T["col_rule"]}</th><th scope="col">{T["col_severity"]}</th>'
            f'<th scope="col">{T["col_description"]}</th>'
            f'<th scope="col" class="num">{T["col_count"]}</th></tr></thead>'
            f"<tbody>{rrows}</tbody></table></details>"
        )
    details = (
        '<section class="card" aria-labelledby="det-h"><h2 id="det-h">Findings by batch</h2>'
        '<p class="hint">Counts only. Student-level findings stay in the private error '
        "report.</p>" + "".join(detail_parts) + "</section>"
    )

    return _page(
        T["readiness_heading"],
        "readiness.html",
        "Data quality",
        T["readiness_heading"],
        "Every submission is validated before it can reach the reports.",
        kpis + callout + history + details,
    )


# ---------------------------------------------------------------- map


def _school_features(con: duckdb.DuckDBPyConnection, cells: list[Cell]) -> list[dict[str, object]]:
    latest_row = con.execute("select max(batch_id) from batches").fetchone()
    latest = latest_row[0] if latest_row else None
    fatal = dict(
        con.execute(
            "select school_code, count(*) from validation_results "
            "where batch_id = ? and severity = 'Fatal' group by 1",
            [latest],
        ).fetchall()
    )
    feats: list[dict[str, object]] = []
    for c in sorted(
        (c for c in cells if c.category == "TA" and c.entity != "district"), key=lambda c: c.entity
    ):
        lon, lat, level = SCHOOL_POINTS[c.entity]
        rate = c.rate_pct or 0.0
        feats.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "school_code": c.entity,
                    "name": SCHOOL_NAMES.get(c.entity, c.entity),
                    "level": level,
                    "eligible": c.eligible,
                    "chronic": c.chronic,
                    "rate_pct": rate,
                    "rate_band": _band(rate)[0],
                    "fatal_latest_batch": int(fatal.get(c.entity, 0)),
                    "page": f"school-{c.entity}.html",
                    "data": "synthetic",
                },
            }
        )
    return feats


MAP_SCRIPT = """
<script type="module">
const GeoJSONLayer = await $arcgis.import("@arcgis/core/layers/GeoJSONLayer.js");
const band = (min, max, color, label) => ({
  minValue: min, maxValue: max, label,
  symbol: { type: "simple-marker", color, outline: { color: "#ffffff", width: 2 } }
});
const layer = new GeoJSONLayer({
  url: "schools.geojson",
  title: "Chronic absenteeism by school (synthetic)",
  copyright: "Synthetic data; invented locations",
  renderer: {
    type: "class-breaks",
    field: "rate_pct",
    legendOptions: { title: "Chronically absent (% of eligible)" },
    classBreakInfos: [
      band(0, 19.999, "__C0__", "Under 20%"),
      band(20, 24.999, "__C1__", "20-25%"),
      band(25, 100, "__C2__", "25% or more")
    ],
    visualVariables: [{
      type: "size", field: "eligible",
      stops: [{ value: 900, size: 22 }, { value: 1400, size: 44 }],
      legendOptions: { title: "Eligible students" }
    }]
  },
  labelingInfo: [{
    labelExpressionInfo: { expression: "$feature.name + TextFormatting.NewLine + Text($feature.rate_pct, '#.0') + '%'" },
    labelPlacement: "above-center",
    symbol: { type: "text", color: "#14213d", haloColor: "#ffffff", haloSize: 2,
              font: { size: 11, weight: "bold" } }
  }],
  popupTemplate: {
    title: "{name}",
    content: [{
      type: "fields",
      fieldInfos: [
        { fieldName: "level", label: "Level" },
        { fieldName: "rate_pct", label: "Chronically absent (%)", format: { places: 1 } },
        { fieldName: "chronic", label: "Chronically absent students", format: { digitSeparator: true } },
        { fieldName: "eligible", label: "Eligible students", format: { digitSeparator: true } },
        { fieldName: "fatal_latest_batch", label: "Fatal findings, latest batch" }
      ]
    }, {
      type: "text",
      text: "<a href='{page}'>Open the {name} page</a>"
    }]
  }
});
const mapEl = document.querySelector("arcgis-map");
await mapEl.viewOnReady();
mapEl.map.add(layer);
</script>
"""


def _map_page(features: list[dict[str, object]]) -> str:
    script = MAP_SCRIPT
    for i, (_, _, _, color) in enumerate(BANDS):
        script = script.replace(f"__C{i}__", color)
    legend = (
        '<ul class="legend" aria-label="Map colors">'
        + "".join(
            f'<li><span style="background:{color}" aria-hidden="true"></span>{label}</li>'
            for _, _, label, color in BANDS
        )
        + "<li>Circle size: eligible students</li></ul>"
    )
    row_list = []
    for f in features:
        p = f["properties"]
        assert isinstance(p, dict)
        row_list.append(
            f'<tr><th scope="row"><a href="{p["page"]}">{escape(str(p["name"]))}</a></th>'
            f'<td>{p["level"]}</td><td class="num">{int(str(p["eligible"])):,}</td>'
            f'<td class="num">{float(str(p["rate_pct"])):.1f}</td><td>{p["rate_band"]}</td>'
            f'<td class="num">{p["fatal_latest_batch"]}</td></tr>'
        )
    rows = "".join(row_list)
    body = (
        '<section class="card" aria-labelledby="map-h"><h2 id="map-h">Where chronic absenteeism '
        'is highest</h2><p class="hint">Select a circle for details. The school locations are '
        "invented and do not match any real school.</p>"
        f'<arcgis-map basemap="osm" center="{MAP_CENTER[0]},{MAP_CENTER[1]}" zoom="12" '
        'aria-label="Map of the eight fictional schools, colored by chronic absenteeism rate">'
        '<arcgis-zoom slot="top-left"></arcgis-zoom><arcgis-home slot="top-left"></arcgis-home>'
        '<arcgis-popup slot="popup"></arcgis-popup></arcgis-map>'
        f"{legend}"
        '<p class="hint">Map built with the ArcGIS Maps SDK for JavaScript 5.1 on an '
        'OpenStreetMap basemap. <a href="schools.geojson" download>Download the points as GeoJSON'
        "</a> to add them to ArcGIS Online or any GIS.</p></section>"
        '<section class="card" aria-labelledby="mt-h"><h2 id="mt-h">The same data as a table</h2>'
        '<table><caption class="sr-only">Schools on the map</caption><thead><tr>'
        '<th scope="col">School</th><th scope="col">Level</th>'
        '<th scope="col" class="num">Eligible students</th><th scope="col" class="num">Rate (%)</th>'
        '<th scope="col">Rate band</th><th scope="col" class="num">Fatal findings, latest batch</th>'
        f"</tr></thead><tbody>{rows}</tbody></table></section>"
    )
    head = f'<script type="module" src="{ARCGIS_SDK}"></script>\n'
    return _page(
        "School map",
        "map.html",
        "ArcGIS map",
        "School map",
        "Chronic absenteeism by school, mapped. Circle size shows enrollment; color "
        "and the label show the rate.",
        body,
        head_extra=head,
        tail_extra=script,
    )


# ---------------------------------------------------------------- error reports


def write_error_reports(con: duckdb.DuckDBPyConnection, out_dir: Path) -> list[Path]:
    """One CSV per batch, sorted the way a coordinator works them. Contains local IDs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for (batch,) in con.execute("select batch_id from batches order by 1").fetchall():
        rows = con.execute(
            """
            select v.school_code, v.severity, v.rule_id, v.record_type, v.line_no,
                   v.ssid, coalesce(e.local_id, i.local_id, s.local_id) as local_id, v.detail
            from validation_results v
            left join senr e on v.record_type = 'SENR' and e.batch_id = v.batch_id
                 and e.line_no = v.line_no
            left join sinf i on v.record_type = 'SINF' and i.batch_id = v.batch_id
                 and i.line_no = v.line_no
            left join stas s on v.record_type = 'STAS' and s.batch_id = v.batch_id
                 and s.line_no = v.line_no
            where v.batch_id = ?
            order by v.school_code, v.severity, v.rule_id, v.line_no
            """,
            [batch],
        ).fetchall()
        path = out_dir / f"error_report_{batch}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(
                [
                    "school_code",
                    "severity",
                    "rule_id",
                    "record_type",
                    "line_no",
                    "ssid",
                    "local_id",
                    "detail",
                ]
            )
            w.writerows(rows)
        paths.append(path)
    return paths


# ---------------------------------------------------------------- entry point


def publish(db_path: Path, site_dir: Path, private_dir: Path) -> list[Path]:
    con = duckdb.connect(str(db_path))
    try:
        current_row = con.execute("select batch_id from stg_current_batch").fetchone()
        current = str(current_row[0]) if current_row else "none"
        latest_row = con.execute(
            "select batch_id, status from batches order by batch_id desc limit 1"
        ).fetchone()
        cells = _cells(con)
        site_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []

        total = next(c for c in cells if c.entity == "district" and c.category == "TA")
        rate = total.rate_pct or 0.0
        school_cells = sorted(
            (c for c in cells if c.category == "TA" and c.entity != "district"),
            key=lambda c: -(c.rate_pct or 0),
        )
        worst = school_cells[0]

        kpis = (
            '<div class="kpis">'
            + "".join(
                [
                    _kpi("Chronically absent", f"{rate:.1f}%", "of eligible students", "#d1495b"),
                    _kpi(
                        "Students affected",
                        f"{total.chronic:,}",
                        f"of {total.eligible:,} eligible",
                        "#f4a261",
                    ),
                    _kpi(
                        "Highest school rate",
                        f"{worst.rate_pct or 0:.1f}%",
                        escape(SCHOOL_NAMES.get(worst.entity, worst.entity)),
                        "#6c5ce7",
                    ),
                    _kpi(
                        "Reported batch",
                        current,
                        "Latest submission rejected"
                        if latest_row and latest_row[1] != "accepted"
                        else "Latest submission",
                        "#13497a",
                    ),
                ]
            )
            + "</div>"
        )

        school_rows = "".join(
            f'<tr><th scope="row"><a href="school-{c.entity}.html">'
            f"{escape(SCHOOL_NAMES.get(c.entity, c.entity))}</a></th>"
            f'<td><span class="tag">{SCHOOL_POINTS[c.entity][2]}</span></td>'
            f'<td class="num">{_fmt(c)[0]}</td><td class="num">{_fmt(c)[1]}</td>{_rate_cell(c)}</tr>'
            for c in school_cells
        )
        schools = (
            '<section class="card" aria-labelledby="sch-h">'
            f'<h2 id="sch-h">{T["by_school"]}</h2>'
            '<p class="hint">Sorted by rate, highest first. Select a school for its breakdown, '
            'or see them on the <a href="map.html">map</a>.</p>'
            f'<table><caption class="sr-only">{T["by_school"]}</caption><thead><tr>'
            f'<th scope="col">{T["col_school"]}</th><th scope="col">Level</th>'
            f'<th scope="col" class="num">{T["col_eligible"]}</th>'
            f'<th scope="col" class="num">{T["col_chronic"]}</th>'
            f'<th scope="col" class="num">{T["col_rate"]}</th></tr></thead>'
            f"<tbody>{school_rows}</tbody></table></section>"
        )

        reasons = con.execute(
            "select coalesce(school_code, 'district'), avg_days_absent, excused_pct, "
            "unexcused_pct, oss_pct from mart_absence_by_reason "
            "order by school_code nulls last"
        ).fetchall()
        reason_rows = "".join(
            f'<tr><th scope="row">{escape(SCHOOL_NAMES.get(e, "District total"))}</th>'
            + "".join(f'<td class="num">{v}</td>' for v in (avg, ex, un, oss))
            + "</tr>"
            for e, avg, ex, un, oss in reasons
        )
        reason_card = (
            '<section class="card" aria-labelledby="rsn-h">'
            f'<h2 id="rsn-h">{T["by_reason"]}</h2>'
            '<p class="hint">Among eligible students. Shares are of all absence days.</p>'
            f'<table><caption class="sr-only">{T["by_reason"]}</caption><thead><tr>'
            f'<th scope="col">{T["col_school"]}</th>'
            f'<th scope="col" class="num">{T["col_avg_days"]}</th>'
            f'<th scope="col" class="num">{T["col_excused"]}</th>'
            f'<th scope="col" class="num">{T["col_unexcused"]}</th>'
            f'<th scope="col" class="num">{T["col_oss"]}</th></tr></thead>'
            f"<tbody>{reason_rows}</tbody></table></section>"
        )

        lead = T["overview_lead"].format(
            rate=f"{rate:.1f}", count=f"{total.chronic:,}", eligible=f"{total.eligible:,}"
        )
        body = kpis + schools + _sections("district", cells, "district") + reason_card
        index = site_dir / "index.html"
        index.write_text(
            _page(
                T["nav_overview"],
                "index.html",
                f"{DISTRICT_NAME} · {ACADEMIC_YEAR}",
                "Chronic absenteeism",
                lead,
                body,
            ),
            encoding="utf-8",
        )
        written.append(index)

        for c in school_cells:
            name = SCHOOL_NAMES.get(c.entity, c.entity)
            eligible, chronic, rate_s = _fmt(c)
            skpis = (
                '<div class="kpis">'
                + "".join(
                    [
                        _kpi("Chronically absent", f"{rate_s}%", "of eligible students", "#d1495b"),
                        _kpi("Students affected", chronic, f"of {eligible} eligible", "#f4a261"),
                        _kpi("District rate", f"{rate:.1f}%", "for comparison", "#13497a"),
                    ]
                )
                + "</div>"
            )
            page = _page(
                name,
                "",
                f"{SCHOOL_POINTS[c.entity][2]} school · {ACADEMIC_YEAR}",
                name,
                f"{rate_s}% of eligible students were chronically absent.",
                skpis + _sections(c.entity, cells, f"s{c.entity}"),
            )
            p = site_dir / f"school-{c.entity}.html"
            p.write_text(page, encoding="utf-8")
            written.append(p)

        r = site_dir / "readiness.html"
        r.write_text(_readiness(con, current), encoding="utf-8")
        written.append(r)

        features = _school_features(con, cells)
        (site_dir / "schools.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": features}, indent=2),
            encoding="utf-8",
        )
        m = site_dir / "map.html"
        m.write_text(_map_page(features), encoding="utf-8")
        written.append(m)

        write_error_reports(con, private_dir)
        return written
    finally:
        con.close()
