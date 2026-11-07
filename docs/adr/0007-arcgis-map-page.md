# 7. ArcGIS map page as the one JavaScript page

Status: accepted. Narrows ADR 6.

## Context
A map shows where rates are highest faster than a table does. The public-sector GIS teams this project is aimed at mostly use Esri ArcGIS.

## Decision
Add `map.html`. It uses the ArcGIS Maps SDK for JavaScript 5.1 from Esri's CDN and loads `schools.geojson` into a `GeoJSONLayer`. Each school is a circle: its size shows eligible students, and its color band and text label show the rate. Popups link to the school pages. The basemap is OpenStreetMap ("osm") because Esri's own basemaps need an ArcGIS account or API key.

Every other page stays free of JavaScript. The map page repeats its data in a table, so nothing depends on the script loading. `schools.geojson` is published so the points can be added to ArcGIS Online.

## Consequences
- The school locations are invented. They sit in farmland west of Sacramento so the basemap has something real to draw on. The page and the GeoJSON say they are not real schools.
- The page depends on js.arcgis.com and OpenStreetMap tiles being available. CI's axe-core check runs on this page with the SDK loaded.
