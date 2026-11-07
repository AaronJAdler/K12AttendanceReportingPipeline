"""Build the static, JavaScript-free dashboard and the private error reports.

Public output (``site/``) holds only suppressed aggregates. Student-level findings with
local IDs go to ``private/``, which is never deployed.
"""

from __future__ import annotations

import csv
from html import escape
from pathlib import Path

import duckdb

from k12att.constants import ACADEMIC_YEAR, SUPPRESSED
from k12att.generate import SCHOOL_NAMES
from k12att.rules import ALL_RULES
from k12att.strings import CATEGORY_LABELS, EN
from k12att.suppression import Cell, suppress

T = EN
DIMENSIONS = {
    "TA": "total",
    **dict.fromkeys(("GM", "GF", "GX", "GZ"), "gender"),
    **dict.fromkeys(("RB", "RI", "RA", "RF", "RH", "RD", "RP", "RT", "RW"), "race"),
    **dict.fromkeys(("GRTKKN", "GR13", "GR46", "GR78", "GR912"), "grade_span"),
}
ORDER = list(DIMENSIONS)

CSS = """
:root { color-scheme: light; }
body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0;
       color: #1a1a1a; background: #ffffff; line-height: 1.5; }
.skip { position: absolute; left: -9999px; }
.skip:focus { left: 1rem; top: 1rem; background: #ffffff; padding: .5rem; z-index: 1; }
header, main, footer { max-width: 60rem; margin: 0 auto; padding: 0 1rem; }
header { border-bottom: 1px solid #6b6b6b; }
nav ul { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 1rem; }
a { color: #0b4f8a; }
a:focus-visible, summary:focus-visible { outline: 3px solid #b34700; outline-offset: 2px; }
.banner { background: #fff4d6; border: 1px solid #8a6100; padding: .5rem .75rem; }
table { border-collapse: collapse; margin: .5rem 0 1.5rem; min-width: 60%; }
caption { text-align: left; font-weight: 600; padding: .25rem 0; }
th, td { border: 1px solid #6b6b6b; padding: .3rem .6rem; text-align: left; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.note { font-size: .95rem; color: #333333; }
svg text { font-family: inherit; font-size: 13px; fill: #1a1a1a; }
"""


def _page(title: str, body: str) -> str:
    nav = (
        f'<nav aria-label="Main"><ul><li><a href="index.html">{T["nav_overview"]}</a></li>'
        f'<li><a href="readiness.html">{T["nav_readiness"]}</a></li></ul></nav>'
    )
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)} | {T['site_title']}</title>\n<style>{CSS}</style>\n</head>\n"
        '<body>\n<a class="skip" href="#main">Skip to main content</a>\n'
        f"<header><p><strong>{T['site_title']}</strong></p>{nav}</header>\n"
        f'<main id="main">\n<p class="banner" role="note">{T["synthetic_banner"]}</p>\n'
        f"{body}\n</main>\n"
        f'<footer><p class="note">{T["definition_note"]}</p>'
        f'<p class="note">{T["suppression_note"]}</p></footer>\n</body>\n</html>\n'
    )


def _fmt(c: Cell) -> tuple[str, str, str]:
    if c.suppressed:
        return SUPPRESSED, SUPPRESSED, SUPPRESSED
    rate = c.rate_pct
    return f"{c.eligible:,}", f"{c.chronic:,}", "" if rate is None else f"{rate:.1f}"


def _table(caption: str, cells: list[Cell], label_header: str) -> str:
    rows = "".join(
        f'<tr><th scope="row">{escape(CATEGORY_LABELS.get(c.category, c.category))}</th>'
        + "".join(f'<td class="num">{v}</td>' for v in _fmt(c))
        + "</tr>"
        for c in cells
    )
    return (
        f"<table><caption>{escape(caption)}</caption><thead><tr>"
        f'<th scope="col">{label_header}</th><th scope="col" class="num">{T["col_eligible"]}</th>'
        f'<th scope="col" class="num">{T["col_chronic"]}</th>'
        f'<th scope="col" class="num">{T["col_rate"]}</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
    )


def bar_chart(chart_id: str, title: str, cells: list[Cell]) -> str:
    """Horizontal bars with direct value labels; no meaning is carried by color alone."""
    row_h, label_w, bar_w = 28, 230, 360
    height = row_h * len(cells) + 10
    parts = []
    for i, c in enumerate(cells):
        y = 5 + i * row_h
        label = escape(CATEGORY_LABELS.get(c.category, c.category))
        parts.append(f'<text x="0" y="{y + 18}">{label}</text>')
        if c.suppressed or c.rate_pct is None:
            parts.append(f'<text x="{label_w}" y="{y + 18}">{SUPPRESSED} hidden</text>')
            continue
        w = min(float(bar_w), max(1.0, bar_w * c.rate_pct / 50.0))
        parts.append(
            f'<rect x="{label_w}" y="{y + 4}" width="{w:.1f}" height="18" fill="#1f5f99"/>'
            f'<text x="{label_w + w + 6:.1f}" y="{y + 18}">{c.rate_pct:.1f}%</text>'
        )
    return (
        f'<svg role="img" aria-labelledby="{chart_id}-t {chart_id}-d" width="100%" '
        f'viewBox="0 0 {label_w + bar_w + 70} {height}" preserveAspectRatio="xMinYMin meet">'
        f'<title id="{chart_id}-t">{escape(title)}</title>'
        f'<desc id="{chart_id}-d">{T["chart_desc_prefix"]} Scale 0 to 50 percent.</desc>'
        + "".join(parts)
        + "</svg>"
    )


def _cells(con: duckdb.DuckDBPyConnection) -> list[Cell]:
    rows = con.execute(
        "select coalesce(school_code, 'district'), reporting_category, "
        "eligible_enrollment, chronic_count from mart_chronic_absenteeism"
    ).fetchall()
    cells = [Cell(e, DIMENSIONS[cat], cat, int(n), int(k)) for e, cat, n, k in rows]
    return suppress(cells)


def _section(entity: str, cells: list[Cell], prefix: str) -> str:
    mine = sorted((c for c in cells if c.entity == entity), key=lambda c: ORDER.index(c.category))
    out = []
    for dim, key in (("grade_span", "by_grade_span"), ("gender", "by_gender"), ("race", "by_race")):
        group = [c for c in mine if c.dimension == dim]
        if not group:
            continue
        out.append(f"<h2>{T[key]}</h2>")
        out.append(bar_chart(f"{prefix}-{dim}", T[key], group))
        out.append(_table(T[key], group, T["col_category"]))
    return "\n".join(out)


def _readiness(con: duckdb.DuckDBPyConnection, current: str) -> str:
    batches = con.execute(
        "select batch_id, status, coalesce(reason, '') from batches order by batch_id desc"
    ).fetchall()
    latest, status, reason = batches[0]
    counts = con.execute(
        "select batch_id, count(*) filter (where severity='Fatal'), "
        "count(*) filter (where severity='Warning') from validation_results group by 1"
    ).fetchall()
    by_batch = {b: (int(f), int(w)) for b, f, w in counts}

    if status == "accepted":
        lead = T["readiness_lead_ok"].format(batch=latest, fatal=by_batch.get(latest, (0, 0))[0])
    else:
        lead = T["readiness_lead_rejected"].format(batch=latest, reason=reason, current=current)

    hist_rows = "".join(
        f'<tr><th scope="row">{b}</th><td>{s}</td>'
        f'<td class="num">{by_batch.get(b, (0, 0))[0]:,}</td>'
        f'<td class="num">{by_batch.get(b, (0, 0))[1]:,}</td></tr>'
        for b, s, _ in batches
    )
    history = (
        f"<h2>{T['history_heading']}</h2><table><caption>{T['history_heading']}</caption>"
        f'<thead><tr><th scope="col">{T["col_batch"]}</th><th scope="col">{T["col_status"]}</th>'
        f'<th scope="col" class="num">{T["col_fatal"]}</th>'
        f'<th scope="col" class="num">{T["col_warning"]}</th></tr></thead>'
        f"<tbody>{hist_rows}</tbody></table>"
    )

    sections = [f"<h1>{T['readiness_heading']}</h1><p>{escape(lead)}</p>", history]
    for b, _, _ in batches:
        school_rows = con.execute(
            "select school_code, count(*) filter (where severity='Fatal'), "
            "count(*) filter (where severity='Warning') from validation_results "
            "where batch_id = ? group by 1 order by 2 desc, 1",
            [b],
        ).fetchall()
        rule_rows = dict(
            con.execute(
                "select rule_id, count(*) from validation_results where batch_id = ? group by 1",
                [b],
            ).fetchall()
        )
        cap = T["findings_heading"].format(batch=b)
        body = "".join(
            f'<tr><th scope="row">{escape(SCHOOL_NAMES.get(s, s))}</th>'
            f'<td class="num">{f:,}</td><td class="num">{w:,}</td></tr>'
            for s, f, w in school_rows
        )
        rcap = T["rules_heading"].format(batch=b)
        rbody = "".join(
            f'<tr><th scope="row">{r.rule_id}</th><td>{r.severity}</td>'
            f"<td>{escape(r.description)}</td>"
            f'<td class="num">{int(rule_rows.get(r.rule_id, 0)):,}</td></tr>'
            for r in ALL_RULES
        )
        sections.append(
            f"<details{' open' if b == latest else ''}><summary>Batch {b}</summary>"
            f"<table><caption>{cap}</caption><thead><tr>"
            f'<th scope="col">{T["col_school"]}</th>'
            f'<th scope="col" class="num">{T["col_fatal"]}</th>'
            f'<th scope="col" class="num">{T["col_warning"]}</th></tr></thead>'
            f"<tbody>{body}</tbody></table>"
            f"<table><caption>{rcap}</caption><thead><tr>"
            f'<th scope="col">{T["col_rule"]}</th><th scope="col">{T["col_severity"]}</th>'
            f'<th scope="col">{T["col_description"]}</th>'
            f'<th scope="col" class="num">{T["col_count"]}</th></tr></thead>'
            f"<tbody>{rbody}</tbody></table></details>"
        )
    return _page(T["readiness_heading"], "\n".join(sections))


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


def publish(db_path: Path, site_dir: Path, private_dir: Path) -> list[Path]:
    con = duckdb.connect(str(db_path))
    try:
        current_row = con.execute("select batch_id from stg_current_batch").fetchone()
        current = str(current_row[0]) if current_row else "none"
        cells = _cells(con)
        site_dir.mkdir(parents=True, exist_ok=True)
        written = []

        total = next(c for c in cells if c.entity == "district" and c.category == "TA")
        rate = total.rate_pct or 0.0
        school_cells = sorted(
            (c for c in cells if c.category == "TA" and c.entity != "district"),
            key=lambda c: c.entity,
        )
        school_rows = "".join(
            f'<tr><th scope="row"><a href="school-{c.entity}.html">'
            f"{escape(SCHOOL_NAMES.get(c.entity, c.entity))}</a></th>"
            + "".join(f'<td class="num">{v}</td>' for v in _fmt(c))
            + "</tr>"
            for c in school_cells
        )
        reasons = con.execute(
            "select coalesce(school_code, 'district'), eligible_enrollment, avg_days_absent, "
            "excused_pct, unexcused_pct, oss_pct from mart_absence_by_reason order by 1"
        ).fetchall()
        reason_rows = "".join(
            f'<tr><th scope="row">{escape(SCHOOL_NAMES.get(e, "District total"))}</th>'
            + "".join(f'<td class="num">{v}</td>' for v in (avg, ex, un, oss))
            + "</tr>"
            for e, _, avg, ex, un, oss in reasons
        )
        body = "\n".join(
            [
                f"<h1>{T['overview_heading'].format(year=ACADEMIC_YEAR)}</h1>",
                "<p>"
                + T["overview_lead"].format(
                    rate=f"{rate:.1f}", count=f"{total.chronic:,}", eligible=f"{total.eligible:,}"
                )
                + "</p>",
                f'<p class="note">{T["batch_note"].format(batch=current)}</p>',
                f"<h2>{T['by_school']}</h2>",
                f"<table><caption>{T['by_school']}</caption><thead><tr>"
                f'<th scope="col">{T["col_school"]}</th>'
                f'<th scope="col" class="num">{T["col_eligible"]}</th>'
                f'<th scope="col" class="num">{T["col_chronic"]}</th>'
                f'<th scope="col" class="num">{T["col_rate"]}</th></tr></thead>'
                f"<tbody>{school_rows}</tbody></table>",
                _section("district", cells, "district"),
                f"<h2>{T['by_reason']}</h2>",
                f"<table><caption>{T['by_reason']}</caption><thead><tr>"
                f'<th scope="col">{T["col_school"]}</th>'
                f'<th scope="col" class="num">{T["col_avg_days"]}</th>'
                f'<th scope="col" class="num">{T["col_excused"]}</th>'
                f'<th scope="col" class="num">{T["col_unexcused"]}</th>'
                f'<th scope="col" class="num">{T["col_oss"]}</th></tr></thead>'
                f"<tbody>{reason_rows}</tbody></table>",
            ]
        )
        index = site_dir / "index.html"
        index.write_text(_page(T["nav_overview"], body), encoding="utf-8")
        written.append(index)

        for c in school_cells:
            name = SCHOOL_NAMES.get(c.entity, c.entity)
            lead = (
                "<p>"
                + (
                    f"{T['col_eligible']}: {_fmt(c)[0]}. {T['col_chronic']}: {_fmt(c)[1]} "
                    f"({_fmt(c)[2]}%)."
                )
                + "</p>"
            )
            page = _page(
                name,
                f"<h1>{escape(name)}</h1>{lead}" + _section(c.entity, cells, f"s{c.entity}"),
            )
            p = site_dir / f"school-{c.entity}.html"
            p.write_text(page, encoding="utf-8")
            written.append(p)

        r = site_dir / "readiness.html"
        r.write_text(_readiness(con, current), encoding="utf-8")
        written.append(r)
        write_error_reports(con, private_dir)
        return written
    finally:
        con.close()
