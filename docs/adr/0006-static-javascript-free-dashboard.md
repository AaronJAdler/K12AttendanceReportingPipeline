# 6. Static, JavaScript-free dashboard

Status: accepted

## Context
Public agencies must meet WCAG 2.1 AA. Interactive chart libraries are often hard to make accessible, and they need a server or a build step.

## Decision
Render static HTML. Charts are inline SVG with a title and description, labeled directly, and never use color alone to carry meaning. A data table with a caption and scoped header cells sits next to every chart. CI runs axe-core on every page and fails on any violation.

## Consequences
- There is no filtering or drill-down beyond links between pages.
- axe-core covers only part of WCAG, so a manual keyboard and screen-reader pass is still needed. It has not been done yet; the README tracks it.
