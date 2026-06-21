import glob
import os
import shutil

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchDriverException, WebDriverException

_CHROME_BINARY_CANDIDATES = [
    "/opt/google/chrome/chrome",
    "/opt/google/chrome/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]

_SNAP_WRAPPER_MARKER = "snap/bin/chromium.chromedriver"
_PROFILE_ENV = "DIGIKEY_CHROME_USER_DATA_DIR"
_PROFILE_DIR_ENV = "DIGIKEY_CHROME_PROFILE_DIRECTORY"
_DEFAULT_SCRAPER_PROFILE = os.path.expanduser("~/.local/share/digikey-scraper/chrome-profile")


def _find_chrome_binary() -> str | None:
    for path in _CHROME_BINARY_CANDIDATES:
        resolved = os.path.realpath(path)
        if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
            return resolved
    return None


def _system_chromedriver_is_snap() -> bool:
    cd = shutil.which("chromedriver")
    if not cd:
        return False
    try:
        with open(cd) as f:
            return _SNAP_WRAPPER_MARKER in f.read(512)
    except OSError:
        return False


def _find_cached_chromedriver() -> str | None:
    """Return a real ChromeDriver from Selenium Manager's download cache."""
    pattern = os.path.expanduser("~/.cache/selenium/chromedriver/linux64/*/chromedriver")
    candidates = sorted(glob.glob(pattern), reverse=True)
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _get_chrome_major_version() -> int | None:
    binary = _find_chrome_binary()
    if not binary:
        return None
    try:
        import subprocess

        out = subprocess.check_output([binary, "--version"], stderr=subprocess.DEVNULL, text=True)
        import re

        m = re.search(r"(\d+)\.", out)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def _chrome_profile_config() -> tuple[str | None, str | None]:
    user_data_dir = os.environ.get(_PROFILE_ENV, "").strip()
    profile_directory = os.environ.get(_PROFILE_DIR_ENV, "").strip()
    if not user_data_dir and os.path.isdir(_DEFAULT_SCRAPER_PROFILE):
        user_data_dir = _DEFAULT_SCRAPER_PROFILE
    return user_data_dir or None, profile_directory or None


def _apply_profile_options(options, user_data_dir: str | None, profile_directory: str | None) -> None:
    if user_data_dir:
        options.add_argument(f"--user-data-dir={os.path.expanduser(user_data_dir)}")
    if profile_directory:
        options.add_argument(f"--profile-directory={profile_directory}")


_CHROME_LOCK_FILES = (
    "DevToolsActivePort",
    "SingletonLock",
    "SingletonSocket",
    "SingletonCookie",
)


def _clear_profile_locks(user_data_dir: str | None) -> None:
    if not user_data_dir:
        return
    profile_path = os.path.expanduser(user_data_dir)
    for name in _CHROME_LOCK_FILES:
        lock = os.path.join(profile_path, name)
        try:
            os.remove(lock)
        except (FileNotFoundError, OSError):
            pass


def _patch_quit_for_display(driver, vd) -> None:
    if vd is None:
        return
    _orig = driver.quit
    def _quit():
        _orig()
        try:
            vd.stop()
        except Exception:
            pass
    driver.quit = _quit


def create_driver(headless: bool):  # returns uc.Chrome
    try:
        import undetected_chromedriver as uc
    except ImportError:
        uc = None

    _vd = None
    if headless:
        try:
            from pyvirtualdisplay import Display
            _vd = Display(visible=False, size=(1600, 1200))
            _vd.start()
            headless = False  # Chrome renders into virtual display instead of headless mode
        except Exception:
            pass  # fall back to off-screen positioning

    chrome_binary = _find_chrome_binary()
    version_main = _get_chrome_major_version()
    user_data_dir, profile_directory = _chrome_profile_config()
    _clear_profile_locks(user_data_dir)
    # Off-screen window trick only makes sense when reusing a Chrome profile
    # (stays stealthy while keeping session cookies). Without a profile, use --headless=new.
    hidden_visible = headless and user_data_dir is not None
    effective_headless = headless and not hidden_visible

    if uc is not None:
        opts = uc.ChromeOptions()
        if chrome_binary:
            opts.binary_location = chrome_binary
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1600,1200")
        opts.add_argument("--lang=en-US")
        opts.add_argument("--no-first-run")
        opts.add_argument("--no-default-browser-check")
        if profile_directory:
            opts.add_argument(f"--profile-directory={profile_directory}")
        if hidden_visible:
            opts.add_argument("--start-minimized")
            opts.add_argument("--window-position=-32000,-32000")
        if effective_headless:
            opts.add_argument("--headless=new")
            opts.add_argument("--remote-debugging-port=0")
        try:
            driver = uc.Chrome(
                options=opts,
                headless=effective_headless,
                user_data_dir=os.path.expanduser(user_data_dir) if user_data_dir else None,
                version_main=version_main,
                driver_executable_path=_find_cached_chromedriver() if _system_chromedriver_is_snap() else None,
            )
            _patch_quit_for_display(driver, _vd)
            return driver
        except Exception:
            pass  # fall through to standard selenium

    # Fallback: standard selenium
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    options = Options()
    options.page_load_strategy = "eager"
    if effective_headless:
        options.add_argument("--headless=new")
    if chrome_binary:
        options.binary_location = chrome_binary
    _apply_profile_options(options, user_data_dir, profile_directory)
    if hidden_visible:
        options.add_argument("--start-minimized")
        options.add_argument("--window-position=-32000,-32000")
    options.add_argument("--window-size=1600,1200")
    options.add_argument("--lang=en-US")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    if effective_headless:
        options.add_argument("--remote-debugging-port=0")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{version_main or 149}.0.0.0 Safari/537.36"
    )

    service: Service | None = None
    if _system_chromedriver_is_snap():
        cached = _find_cached_chromedriver()
        if cached:
            service = Service(executable_path=cached)

    try:
        driver = webdriver.Chrome(service=service, options=options) if service else webdriver.Chrome(options=options)
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )
        _patch_quit_for_display(driver, _vd)
        return driver
    except NoSuchDriverException as exc:
        raise RuntimeError(
            "Chrome WebDriver를 시작하지 못했습니다. Google Chrome 설치 여부와 "
            "ChromeDriver/Selenium Manager 사용 가능 여부를 확인하세요."
        ) from exc
    except WebDriverException as exc:
        raise RuntimeError(
            "Chrome 브라우저를 시작하지 못했습니다. Google Chrome 설치, ChromeDriver 호환성, "
            f"headless 실행 환경을 확인하세요. (binary={chrome_binary})\n원본: {exc}"
        ) from exc


def get_page_soup(driver) -> BeautifulSoup:
    return BeautifulSoup(driver.page_source, "html.parser")
