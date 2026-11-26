"""Exercise the built starter at a project subpath in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright
from selection_browser import verify

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / "browser-checks"
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / "dist", Path(temporary) / "example-tool")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=os.environ.get("CHROME_BIN"))
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/example-tool/")
                page.locator("#records tr:nth-child(10)").wait_for()
                page.locator("#country").select_option("US")
                page.locator("#program").select_option("work")
                page.wait_for_function("document.getElementById('csv').href.includes('/series/work/US.csv')")
                assert "United States" in page.locator("#context").inner_text()
                page.locator("#more").click()
                assert page.locator("#records tr").count() > 12
                page.get_by_role("link",name="Canada Study Permit Processing Time from the Philippines").click()
                assert page.locator("#program").input_value() == "study"
                assert page.locator("#country").input_value() == "PH"
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                verify(page, f"http://127.0.0.1:{server.server_port}/example-tool/")
                assert not errors, errors
                browser.close()
            print("Browser checks passed for root, preset and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
