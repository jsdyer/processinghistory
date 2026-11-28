"""Build country comparisons from the same observed rows as the interactive archive."""
from collections import defaultdict
from datetime import date, timedelta
from html import escape
import re
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from collect import PROGRAMS
from search_metadata import add_search_metadata

CHECKER = 'https://www.canada.ca/en/immigration-refugees-citizenship/services/application/check-processing-times.html'
NUMERIC = re.compile(r'(\d+) (day|week)s?', re.IGNORECASE)
SHORT = {'visitor-outside-canada': 'Visitor visa', 'supervisa': 'Super visa',
         'study': 'Study permit', 'work': 'Work permit'}


def days(label):
    match = NUMERIC.fullmatch(label or '')
    if match:
        return int(match[1]) * (7 if match[2].lower() == 'week' else 1)
    return None


def link(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def editions(rows):
    """Choose the last observation of each dated IRCC edition, including corrections."""
    by_date = {row['issued']: row for row in rows if row['issued']}
    return [by_date[key] for key in sorted(by_date)]


def four_weeks_before(latest, timeline):
    if not latest['issued']:
        return None
    target = date.fromisoformat(latest['issued']) - timedelta(weeks=4)
    earliest = target - timedelta(weeks=2)
    return next((row for row in reversed(timeline)
                 if earliest <= date.fromisoformat(row['issued']) <= target), None)


def difference(current_label, previous_label):
    current, previous = days(current_label), days(previous_label)
    if current is None or previous is None:
        return None
    delta = current - previous
    if delta == 0:
        return 'The two editions give the same duration.'
    # Preserve IRCC's original units in the table and compare week-only series in weeks.
    unit = 'day'
    if 'week' in current_label.lower() and 'week' in previous_label.lower():
        delta //= 7
        unit = 'week'
    if abs(delta) != 1:
        unit += 's'
    return f'The latest estimate is {abs(delta)} {unit} {"longer" if delta > 0 else "shorter"}.'


def page(stage, tool, path, title, description, body, discoverable=True):
    dest = stage / path
    dest.mkdir(parents=True, exist_ok=True)
    base = '../' * len(path.rstrip('/').split('/'))
    view = dict(tool, url=tool['url'] + path, title=title, description=description)
    official_project = tool['source'].rstrip('/') == 'https://github.com/jsdyer/' + tool['id'] and tool['id'] != 'coolcode-tool-template'
    metrics = '<script defer src="/assets/tool-metrics.js" referrerpolicy="no-referrer"></script>' if official_project else ''
    report = link('https://coolcode.ca/report/?tool=' + tool['id'], 'Report an issue') if official_project else ''
    robots = '' if discoverable else '<meta name="robots" content="noindex,follow">'
    doc = f'''<!doctype html><html lang="en-CA"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · CoolCode</title><meta name="description" content="{escape(description, quote=True)}">
{robots}<link rel="stylesheet" href="{base}style.css">{metrics}
</head><body data-tool-id="{escape(tool['id'],quote=True)}"><a class="skip" href="#main">Skip to results</a>
<header>{link(base, 'IRCC Processing Time History')}{link('https://coolcode.ca/', 'CoolCode.ca')}</header>
<main id="main">{body}</main><footer>{link(CHECKER, 'IRCC’s current processing times')}
{link(base, 'Compare individual application histories')}{report}</footer></body></html>'''
    (dest / 'index.html').write_text(add_search_metadata(doc, view, category='ReferenceApplication'), encoding='utf-8')


def program_card(program, code, rows, timeline):
    latest = rows[-1]
    current = latest['label']
    label = current or ('No row in this capture' if current is None else 'No estimate supplied')
    previous = four_weeks_before(latest, timeline)
    body = [f'<section class="surface" id="{program}"><h2>{escape(PROGRAMS[program])}</h2>',
            f'<strong class="profile-estimate">{escape(label)}</strong>',
            f'<p>IRCC edition {escape(latest["issued"] or "unavailable")} · observed {escape(latest["observed"][:10])} UTC.</p>']
    if previous:
        was = previous['label'] or 'No published estimate'
        summary = difference(current, was)
        body.append(f'<p>On {escape(previous["issued"])} the published value was <strong>{escape(was)}</strong>. '
                    + (escape(summary) if summary else 'A numerical change requires a duration in both editions.') + '</p>')
    elif days(current) is not None:
        body.append('<p>The archive has no dated edition four to six weeks earlier for this comparison.</p>')
    if days(current) is None:
        numbered = next((r for r in reversed(timeline) if days(r['label']) is not None), None)
        if numbered:
            body.append(f'<p>The last dated estimate retained for this application was {escape(numbered["label"])} '
                        f'in the {escape(numbered["issued"])} edition.</p>')
    sample = {r['issued']: r for r in timeline[-3:]}
    if previous:
        sample[previous['issued']] = previous
    if sample:
        entries = ''.join(f'<tr><td>{escape(d)}</td><td>{escape(sample[d]["label"] or "No published estimate")}</td>'
                          f'<td>{link(sample[d]["evidence"], "Source copy observed " + sample[d]["observed"][:10])}</td></tr>'
                          for d in sorted(sample, reverse=True))
        body.append('<details><summary>Published editions and evidence</summary><div class="scroll"><table>'
                    '<thead><tr><th>IRCC edition</th><th>Published value</th><th>Evidence</th></tr></thead>'
                    f'<tbody>{entries}</tbody></table></div></details>')
    url = '../../?' + urlencode({'program': program, 'country': code})
    body.append(f'<nav>{link(url, "Explore the full " + SHORT[program].lower() + " timeline")} '
                f'{link("../../series/" + program + "/" + code + ".csv", "Download observations (CSV)")}</nav></section>')
    return ''.join(body)


def build_country(stage, tool, code, name, histories, checked):
    if not re.fullmatch('[A-Z]{2}', code):
        raise ValueError('Invalid country code for a profile')
    timelines = {k: editions(rows) for k, rows in histories.items()}
    # Once meaningful history exists, a temporary withdrawal keeps the URL usable.
    historic = sum(sum(days(r['label']) is not None for r in series) >= 2
                   for series in timelines.values())
    if historic < 2:
        return None
    current = {k: rows[-1] for k, rows in histories.items()}
    active = sum(days(row['label']) is not None for row in current.values())
    path = 'records/' + code.lower() + '/'
    title = 'Canada visa and permit processing times for applications from ' + name
    reported = [(SHORT[k], row['label']) for k, row in current.items() if days(row['label']) is not None]
    observed = max(row['observed'] for row in current.values())[:10]
    excerpt = '. '.join(f'{k} {v}' for k, v in reported[:2])
    description = (f'IRCC processing estimates for {name} observed {observed}. {excerpt}. Compare dated editions and source records.'
                   if reported else f'Historical IRCC visa and permit estimates for applications from {name}, with dated editions and source records.')
    title_html = escape(title)
    summary = ''.join(f'<li>{link("#" + program, SHORT[program])}<strong>{escape(row["label"] or "No published estimate")}</strong></li>'
                      for program, row in current.items())
    body = (f'<p>{link("../", "Browse by country or territory")}</p><h1>{title_html}</h1>'
            '<p class="lead">Choose the application you plan to submit. Each figure is IRCC’s published estimate '
            f'for someone applying from {escape(name)}.</p><ul class="profile-summary">{summary}</ul>'
            f'<p>Latest retained observation <strong>{observed} UTC</strong>. Source last checked {escape(checked[:10])} UTC. '
            'An individual application can take longer. Check the '
            f'{link(CHECKER, "official IRCC tool for current estimates and special measures")} before making plans.</p>'
            '<p>The comparisons use the nearest saved edition on or before four weeks earlier, within a two-week window. '
            'Each comparison shows both dates. A change between editions describes what IRCC published for that group.</p>'
            + ''.join(program_card(k, code, histories[k], timelines[k]) for k in PROGRAMS))
    page(stage, tool, path, title, description, body, discoverable=active >= 2)
    return {'code': code, 'name': name, 'path': path, 'active': active}


def directory(stage, tool, profiles, checked):
    listed = sorted((p for p in profiles if p['active'] >= 2), key=lambda p: p['name'].casefold())
    if not listed:
        raise ValueError('No comparable published country estimates')
    groups = defaultdict(list)
    for p in listed:
        groups[p['name'][0].upper()].append(p)
    jumps = ' '.join(link('#group-' + str(i), letter) for i, letter in enumerate(groups))
    sections = []
    for i, (letter, group) in enumerate(groups.items()):
        entries = ''.join('<li>' + link(p['code'].lower() + '/', p['name']) + '</li>' for p in group)
        sections.append(f'<section id="group-{i}"><h2>{escape(letter)}</h2><ul class="country-list">{entries}</ul></section>')
    title = 'Canada visa and permit processing times by country of application'
    description = ('Compare current published IRCC estimates with recent editions for visitor visas, super visas, '
                   'study permits and work permits. Select the country you are applying from.')
    body = (f'<h1>{title}</h1><p class="lead">{escape(description)}</p>'
            f'<p>{len(listed)} countries and territories have at least two application types with a published duration '
            f'in the latest capture. Source checked {escape(checked[:10])} UTC. For other locations or a single series, '
            f'{link("../", "search the full IRCC history archive")}.</p><nav aria-label="Jump to a letter">{jumps}</nav>'
            + ''.join(sections))
    page(stage, tool, 'records/', title, description, body)
    if tool['source'].rstrip('/') != 'https://github.com/jsdyer/' + tool['id'] or tool['id'] == 'coolcode-tool-template':
        return
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    urlset = ET.Element('urlset', xmlns=ns)
    for path in ['records/', *(p['path'] for p in listed)]:
        ET.SubElement(ET.SubElement(urlset, 'url'), 'loc').text = 'https://coolcode.ca' + tool['url'] + path
    ET.ElementTree(urlset).write(stage / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
