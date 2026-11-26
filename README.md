# IRCC Processing Time History

[Explore published estimates](https://coolcode.ca/processinghistory/) for visitor visas, super visas, study permits and work permits by country.

<!-- coolcode:guide -->
Choose the country applying from and one of four IRCC country-based programs. The first result shows the latest retained value and IRCC source edition. Review earlier observations with source links, download the selected history as CSV, or subscribe to its RSS change feed. A point is an observed estimate, never an individual completion date.
<!-- /coolcode:guide -->

## Sources and coverage

IRCC's [processing-time form](https://www.canada.ca/en/immigration-refugees-citizenship/services/application/check-processing-times.html) loads the [official country estimate feed](https://www.canada.ca/content/dam/ircc/documents/json/data-ptime-en.json) and separate files for other services. The archive here covers the four temporary resident country series from the first file. Source edition dates are preserved per program. Collection dates, source hashes, and provenance accompany every observation. A missing source date, absent series and the publisher's own unavailable status are distinct. The trend displays observed points with gaps. Historical weeks are converted to days only for the chart.

The collector runs daily at 13:43 UTC. Last-good data stays published if validation or build fails. Identical data need no additional snapshot. `web/data/index.json` gives collection time, edition, number of retained captures and series count; `web/data/history/YYYY-MM.json` contains normalized captures with exact source strings in each snapshot's dictionary. The latest direct capture links to the mutable upstream URL; see its SHA-256 in the CSV and the retained version in this repository.

Older observations come from two sources: original files from the [Wayback CDX](https://web.archive.org/cdx/search/cdx?url=www.canada.ca/content/dam/ircc/documents/json/data-ptime-en.json&output=json&filter=statuscode:200&collapse=digest) index and the independently preserved [IRCC JSON copies](https://github.com/suhaibmujahid/cic-processing-times/blob/main/.github/workflows/flat.yml) that link to individual commits. For the latter, the collector commit time serves as the observed time. These points are distinct from CoolCode’s own direct fetches. Missing observations are never inferred.

## Expand or customize

Add a named scenario in `web/examples.json` using a supported program slug and country code. It will have its own static, preselected result and canonical URL. Every retained country is also selectable from any page. For new programs verify source schema, methodology and country coverage before adding them to `PROGRAMS` in the collector. To import older supported records, download timestamped original Wayback JSON files named with their 14-digit capture timestamps and clone the cited mirror. Run `python3 scripts/backfill.py MIRROR_CHECKOUT WAYBACK_DIR` followed by `python3 scripts/collect.py`.

Run `node --test tests/*.test.mjs`, `python3 -m unittest discover -s tests`, `python3 scripts/build.py` and, with Playwright Chromium installed, `python3 tests/browser_smoke.py`. Push to main to deploy. Scheduled or manual Actions runs add dated observations. No key, case number or login is used. The shared CoolCode counter receives only the tool ID.
