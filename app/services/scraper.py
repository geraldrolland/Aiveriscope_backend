"""Headless Chrome page fetching via Selenium.

A single driver is created on first use and reused across requests (guarded
by a lock). If a request fails, the driver is torn down and recreated on the
next request, so browser processes cannot leak.
"""
import threading

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..config import settings

_lock = threading.Lock()
_driver: webdriver.Chrome | None = None


def _build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.page_load_strategy = "eager"
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def get_driver() -> webdriver.Chrome:
    global _driver
    with _lock:
        if _driver is not None:
            try:
                _driver.current_url
                return _driver
            except Exception:
                try:
                    _driver.quit()
                except Exception:
                    pass
                _driver = None
        _driver = _build_driver()
        return _driver


def fetch_page(url: str) -> str:
    """Load a URL in headless Chrome and return the rendered page source."""
    driver = get_driver()
    try:
        driver.set_page_load_timeout(settings.page_load_timeout)
        driver.get(url)
        WebDriverWait(driver, settings.page_wait_timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        return driver.page_source
    except Exception:
        close_driver()
        raise


def close_driver() -> None:
    global _driver
    with _lock:
        if _driver is not None:
            try:
                _driver.quit()
            except Exception:
                pass
            _driver = None
