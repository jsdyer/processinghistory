"""Check a published or locally built IRCC page against its own country-specific CSV and RSS."""
import csv
import io
import os
from urllib.parse import parse_qs, urlsplit
from xml.etree import ElementTree as ET

from playwright.sync_api import sync_playwright


def check_selection(page, base, program, country, check_exports=False):
    name = page.locator('#country option:checked').inner_text()
    page.wait_for_function(
        """([program,country]) => document.querySelector('#result').getAttribute('aria-busy') === 'false' &&
        document.querySelector('#retry').hidden && document.querySelector('#csv').href.endsWith('/'+program+'/'+country+'.csv')""",
        arg=[program, country])
    assert name in page.locator('h1').inner_text()
    assert page.locator('h1').inner_text() in page.title()
    assert name in page.locator('#lead').inner_text()
    assert name in page.locator('#context').inner_text()
    assert name in page.locator('#history-title').inner_text()
    assert name in page.locator('meta[name="description"]').get_attribute('content')
    assert name in page.locator('meta[property="og:title"]').get_attribute('content')
    assert page.locator('#records tr').count() == 12
    if check_exports:
        expected_path = f'{base}series/{program}/{country}'
        for selector, suffix in [('csv','.csv'),('rss','.rss')]:
            assert page.locator('#' + selector).get_attribute('href') == expected_path + suffix
        file = page.request.get(expected_path + '.csv')
        assert file.ok
        exported = list(csv.DictReader(io.StringIO(file.text())))
        assert all(r['application'] == program and r['country_code'] == country for r in exported)
        for ix, expected in enumerate(reversed(exported[-3:])):
            cols = page.locator('#records tr').nth(ix).locator('td')
            assert cols.nth(0).inner_text() == expected['observed_at_utc'][:10]
            assert cols.nth(2).inner_text() == expected['published_value']
            assert cols.nth(3).locator('a').get_attribute('href') == expected['evidence_url']
        assert page.locator('#estimate').inner_text() == exported[-1]['published_value']
        assert page.locator('svg circle').count() == sum(
            len(r['published_value'].split()) == 2 and r['published_value'].split()[0].isdigit()
            and r['published_value'].split()[1] in {'day','days','week','weeks'} for r in exported)
        feed = page.request.get(expected_path + '.rss')
        assert feed.ok
        channel = ET.fromstring(feed.body()).find('channel')
        assert name in channel.findtext('title')
        assert parse_qs(urlsplit(channel.findtext('link')).query) == {'program':[program], 'country':[country]}


def verify(page, base):
    visitor = 'visitor-outside-canada'
    india = base + 'visitor-visa-india/'
    page.goto(india)
    check_selection(page, base, visitor, 'IN', True)
    assert page.locator('link[rel="canonical"]').get_attribute('href') == 'https://coolcode.ca/processinghistory/visitor-visa-india/'
    assert page.url == india
    page.locator('#country').select_option('BR')
    check_selection(page, base, visitor, 'BR', True)
    brazil = page.locator('#share').get_attribute('href')
    assert brazil == page.url and 'India' not in page.title()
    assert parse_qs(urlsplit(brazil).query) == {'program':[visitor], 'country':['BR']}
    assert page.locator('link[rel="canonical"]').get_attribute('href') == 'https://coolcode.ca/processinghistory/'
    page.locator('#program').select_option('supervisa')
    check_selection(page, base, 'supervisa', 'BR', True)
    page.go_back()
    check_selection(page, base, visitor, 'BR')
    page.go_back()
    check_selection(page, base, visitor, 'IN')
    page.go_forward()
    check_selection(page, base, visitor, 'BR')
    page.reload()
    check_selection(page, base, visitor, 'BR', True)
    page.locator('#program').select_option('study')
    page.locator('#country').select_option('PH')
    check_selection(page, base, 'study', 'PH', True)
    assert page.url == base + 'study-permit-philippines/'
    assert page.locator('link[rel="canonical"]').get_attribute('href').endswith('/study-permit-philippines/')
    page.locator('#country').select_option('US')
    page.locator('#program').select_option('work')
    check_selection(page, base, 'work', 'US', True)
    assert page.url == base + 'work-permit-united-states/'
    assert page.get_by_role('link', name='Canada Visitor Visa Processing Time from India').get_attribute('href') == india
    page.goto(india + '?country=AU')
    check_selection(page, base, visitor, 'AU')
    # A temporarily unavailable country file must never leave another country's data on screen.
    page.route('**/series/JP.json', lambda route: route.fulfill(status=503,body='Unavailable'))
    page.locator('#country').select_option('JP')
    page.get_by_role('button',name='Retry this selection').wait_for()
    assert page.locator('#estimate').inner_text() == 'History unavailable'
    assert page.locator('#records tr, #plot circle').count() == 0
    assert 'Japan' in page.locator('h1').inner_text()
    page.unroute('**/series/JP.json')
    page.get_by_role('button',name='Retry this selection').click()
    check_selection(page, base, visitor, 'JP', True)
    page.goto(base)
    page.locator('#records tr:nth-child(10)').wait_for()
    assert page.locator('h1').inner_text() == 'IRCC Processing Time History'
    print('Verified country/program switching, table and chart against CSV, RSS, preset links, browser history, reload and recovery.')


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.environ.get('CHROME_BIN'))
        verify(browser.new_page(), 'https://coolcode.ca/processinghistory/')
        browser.close()
