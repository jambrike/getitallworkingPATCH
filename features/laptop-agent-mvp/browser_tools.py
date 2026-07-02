from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus, urlparse

from playwright.sync_api import Browser, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from safety import safe_output_path


BLOCK_BROWSER_PROMPTS_SCRIPT = """
(() => {
  if ("Notification" in window) {
    try {
      Object.defineProperty(Notification, "permission", { get: () => "denied" });
      Notification.requestPermission = () => Promise.resolve("denied");
    } catch (_error) {}
  }

  if (navigator.permissions && navigator.permissions.query) {
    const originalQuery = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = (parameters) => {
      if (parameters && parameters.name === "notifications") {
        return Promise.resolve({ state: "denied", onchange: null });
      }
      return originalQuery(parameters);
    };
  }
})();
"""


class BrowserSession:
    def __init__(self) -> None:
        self._playwright = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    def __enter__(self) -> "BrowserSession":
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-notifications",
                "--disable-infobars",
                "--disable-features=PermissionPromptPersistence,AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
        )
        self.page = self.browser.new_page()
        self._prepare_page(self.page)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.browser:
            self.browser.close()
        if self._playwright:
            self._playwright.stop()

    def require_page(self) -> Page:
        if self.page is None:
            raise RuntimeError("Browser page is not available.")
        return self.page

    def _prepare_page(self, page: Page) -> None:
        page.add_init_script(BLOCK_BROWSER_PROMPTS_SCRIPT)
        page.on("dialog", lambda dialog: dialog.dismiss())

    def current_url(self) -> str:
        page = self.require_page()
        return page.url

    def open_url(self, url: str) -> str:
        page = self.require_page()
        page.goto(normalize_url(url), wait_until="domcontentloaded", timeout=30_000)
        return f"Opened {page.url}"

    def search_web(self, query: str) -> str:
        url = f"https://duckduckgo.com/?q={quote_plus(query)}"
        return self.open_url(url)

    def get_page_text(self, limit: int = 6000) -> str:
        page = self.require_page()
        try:
            text = page.locator("body").inner_text(timeout=5_000)
        except Exception:
            return ""
        return text[:limit]

    def click_text(self, text: str) -> str:
        page = self.require_page()
        locator = page.get_by_text(text, exact=False).first
        locator.click(timeout=10_000)
        page.wait_for_load_state("domcontentloaded", timeout=10_000)
        return f"Clicked text matching: {text}"

    def type_text(self, selector: str, text: str) -> str:
        page = self.require_page()
        page.fill(selector, text, timeout=10_000)
        return f"Typed into {selector}"

    def press_key(self, key: str) -> str:
        page = self.require_page()
        page.keyboard.press(key)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except PlaywrightTimeoutError:
            pass
        return f"Pressed {key}"


def save_output_file(outputs_dir: Path, filename: str | None, content: str) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    path = safe_output_path(outputs_dir, filename)
    path.write_text(content, encoding="utf-8")
    return path


def normalize_url(url: str) -> str:
    cleaned = str(url or "").strip()
    if not cleaned:
        raise ValueError("URL cannot be empty.")

    parsed = urlparse(cleaned)
    if not parsed.scheme:
        cleaned = f"https://{cleaned}"

    return cleaned
