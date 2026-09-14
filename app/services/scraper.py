"""Page fetching with requests + BeautifulSoup, falling back to Selenium for JS-heavy sites."""
import logging

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..config import settings

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def _fetch_with_requests(url: str) -> str:
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def _build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.page_load_strategy = "eager"
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def _fetch_with_selenium(url: str) -> str:
    driver = _build_driver()
    try:
        driver.set_page_load_timeout(settings.page_load_timeout)
        driver.get(url)
        WebDriverWait(driver, settings.page_wait_timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        return driver.page_source
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def fetch_page(url: str) -> str:
    """Fetch page HTML. Tries requests first, falls back to Selenium for JS-heavy sites."""
    html = _fetch_with_requests(url)

    soup = BeautifulSoup(html, "html.parser")
    has_headings = any(soup.find_all(tag) for tag in ["h1", "h2", "h3", "h4", "h5", "h6"])

    if has_headings:
        log.info("requests fetch succeeded for %s", url)
        return html

    log.info("No headings found with requests, falling back to Selenium for %s", url)
    return _fetch_with_selenium(url)
