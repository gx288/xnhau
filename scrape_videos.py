import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import os
import logging
import time
from datetime import datetime
import socket
import random

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_all_methods.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load config
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    DOMAIN = config['DOMAIN']
    HEADERS = config.get('HEADERS', {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://xnhau.sh/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1'
    })
except Exception as e:
    logger.warning(f"Failed to load config.json: {str(e)}. Using defaults.")
    DOMAIN = "https://xnhau.sh/clip-sex-moi/"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://xnhau.sh/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1'
    }

# Proxy list (prioritize working proxy)
PROXIES_LIST = [
    '36.50.53.219:11995',  # Worked in previous debug
    '157.250.203.234:8080',
    '8.219.97.248:80',
    '45.14.224.247:80',
    '43.129.93.201:5000'
]

def check_dns(hostname):
    """Check DNS resolution."""
    try:
        ip = socket.gethostbyname(hostname)
        logger.info(f"DNS resolved for {hostname}: {ip}")
        return ip
    except socket.gaierror as e:
        logger.error(f"DNS resolution failed for {hostname}: {str(e)}")
        return None

def parse_response(response_text):
    """Parse response to check items and issues."""
    soup = BeautifulSoup(response_text, 'html.parser')
    items = soup.find_all('div', class_='item ')
    title = soup.title.string if soup.title else "No title"
    issues = []
    if 'cloudflare' in response_text.lower() or 'cf-ray' in response_text.lower():
        issues.append("Cloudflare protection")
    if 'login' in response_text.lower() or 'authentication' in response_text.lower():
        issues.append("Login/Authentication required")
    if 'captcha' in response_text.lower():
        issues.append("CAPTCHA")
    return items, title, issues

def save_response(response_text, method, status, timestamp):
    """Save response to file with clear naming."""
    if status == 'success':
        html_file = f"debug_response_success_{method}_{timestamp}.html"
    elif status.isdigit():
        html_file = f"debug_response_error_{method}_{status}_{timestamp}.html"
    else:
        html_file = f"debug_response_other_{method}_{status}_{timestamp}.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(response_text)
    logger.info(f"Saved {status.upper()} response to {html_file}")
    return html_file

def method_requests_no_proxy(url, retries=3, delay=1):
    """Method 1: Requests without proxy."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Method 1: Requests without proxy to {url}")
    logger.debug(f"Request headers: {HEADERS}")
    session = requests.Session()  # For cookies persistence

    for attempt in range(retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{retries} (delay: {delay}s)")
            time.sleep(delay)
            response = session.get(url, headers=HEADERS, timeout=20, allow_redirects=True, verify=True)
            logger.info(f"Status code: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response content-length: {len(response.text)}")

            html_file = save_response(response.text, 'requests_no_proxy', str(response.status_code), timestamp)
            items, title, issues = parse_response(response.text)
            logger.info(f"Found {len(items)} items with class 'item '")
            logger.info(f"Page title: {title[:100]}...")
            for issue in issues:
                logger.warning(f"Detected issue: {issue}")

            return response, len(items), html_file

        except requests.exceptions.HTTPError as http_err:
            error_msg = f"HTTP Error (code: {http_err.response.status_code if hasattr(http_err, 'response') else 'Unknown'}): {str(http_err)}"
            logger.error(error_msg)
            if hasattr(http_err, 'response'):
                logger.error(f"Response body (first 1000 chars): {http_err.response.text[:1000]}")
                html_file = save_response(http_err.response.text, 'requests_no_proxy', str(http_err.response.status_code), timestamp)
            logger.debug(f"Full exception: {http_err}")
            time.sleep(delay * 2)

        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection Error: {str(conn_err)}")
            html_file = save_response(str(conn_err), 'requests_no_proxy', 'connection', timestamp)
            logger.debug(f"Full exception: {conn_err}")
            time.sleep(delay * 2)

        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout Error: {str(timeout_err)}")
            html_file = save_response(str(timeout_err), 'requests_no_proxy', 'timeout', timestamp)
            logger.debug(f"Full exception: {timeout_err}")
            time.sleep(delay * 2)

        except requests.exceptions.SSLError as ssl_err:
            logger.error(f"SSL Error: {str(ssl_err)}")
            html_file = save_response(str(ssl_err), 'requests_no_proxy', 'ssl', timestamp)
            logger.debug(f"Full exception: {ssl_err}")
            time.sleep(delay * 2)

        except requests.exceptions.RequestException as req_err:
            logger.error(f"General Request Error: {str(req_err)}")
            html_file = save_response(str(req_err), 'requests_no_proxy', 'request', timestamp)
            logger.debug(f"Full exception: {req_err}")
            time.sleep(delay * 2)

    logger.error(f"All {retries} attempts failed for {url}")
    return None, 0, None

def method_requests_proxy(url, retries=2, delay=2):
    """Method 2: Requests with proxy."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Method 2: Requests with proxy to {url}")
    random.shuffle(PROXIES_LIST)

    for proxy in PROXIES_LIST[:3]:  # Try up to 3 proxies
        proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        logger.info(f"Trying proxy: {proxy}")
        session = requests.Session()

        for attempt in range(retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{retries} (delay: {delay}s)")
                time.sleep(delay)
                response = session.get(url, headers=HEADERS, proxies=proxies, timeout=20, allow_redirects=True, verify=True)
                logger.info(f"Status code: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response content-length: {len(response.text)}")

                html_file = save_response(response.text, 'requests_proxy', str(response.status_code), timestamp)
                items, title, issues = parse_response(response.text)
                logger.info(f"Found {len(items)} items with class 'item '")
                logger.info(f"Page title: {title[:100]}...")
                for issue in issues:
                    logger.warning(f"Detected issue: {issue}")

                return response, len(items), html_file

            except requests.exceptions.ProxyError as proxy_err:
                logger.error(f"Proxy Error: {str(proxy_err)}. Proxy {proxy} may be invalid.")
                html_file = save_response(str(proxy_err), 'requests_proxy', 'proxy', timestamp)
                logger.debug(f"Full exception: {proxy_err}")
                break  # Skip to next proxy
            except requests.exceptions.HTTPError as http_err:
                error_msg = f"HTTP Error (code: {http_err.response.status_code if hasattr(http_err, 'response') else 'Unknown'}): {str(http_err)}"
                logger.error(error_msg)
                if hasattr(http_err, 'response'):
                    logger.error(f"Response body (first 1000 chars): {http_err.response.text[:1000]}")
                    html_file = save_response(http_err.response.text, 'requests_proxy', str(http_err.response.status_code), timestamp)
                logger.debug(f"Full exception: {http_err}")
                time.sleep(delay * 2)
            except requests.exceptions.RequestException as req_err:
                logger.error(f"Request Error: {str(req_err)}")
                html_file = save_response(str(req_err), 'requests_proxy', 'request', timestamp)
                logger.debug(f"Full exception: {req_err}")
                time.sleep(delay * 2)

    logger.error(f"All proxies failed for {url}")
    return None, 0, None

def method_selenium_no_proxy(url, retries=2, delay=5):
    """Method 3: Selenium without proxy."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Method 3: Selenium without proxy to {url}")

    for attempt in range(retries):
        driver = None
        try:
            logger.info(f"Attempt {attempt + 1}/{retries} (delay: {delay}s)")
            time.sleep(delay)

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(f"--user-agent={HEADERS['User-Agent']}")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            driver = webdriver.Chrome(service=webdriver.chrome.service.Service(ChromeDriverManager().install()), options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            driver.get(url)
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(5)  # Wait for JS

            page_source = driver.page_source
            html_file = save_response(page_source, 'selenium_no_proxy', 'success', timestamp)
            items, title, issues = parse_response(page_source)
            logger.info(f"Found {len(items)} items with class 'item '")
            logger.info(f"Page title: {title[:100]}...")
            for issue in issues:
                logger.warning(f"Detected issue: {issue}")

            return page_source, len(items), html_file

        except (TimeoutException, WebDriverException) as e:
            logger.error(f"Selenium Error: {str(e)}")
            html_file = save_response(str(e), 'selenium_no_proxy', 'selenium', timestamp)
            logger.debug(f"Full exception: {e}")
            time.sleep(delay * 2)
        except Exception as e:
            logger.error(f"Unexpected Error: {str(e)}")
            html_file = save_response(str(e), 'selenium_no_proxy', 'unexpected', timestamp)
            logger.debug(f"Full exception: {e}")
            time.sleep(delay * 2)
        finally:
            if driver:
                driver.quit()

    logger.error(f"All {retries} attempts failed for {url}")
    return None, 0, None

def method_selenium_proxy(url, retries=2, delay=5):
    """Method 4: Selenium with proxy."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Method 4: Selenium with proxy to {url}")
    random.shuffle(PROXIES_LIST)

    for proxy in PROXIES_LIST[:3]:
        logger.info(f"Trying proxy: {proxy}")
        for attempt in range(retries):
            driver = None
            try:
                logger.info(f"Attempt {attempt + 1}/{retries} (delay: {delay}s)")
                time.sleep(delay)

                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument(f"--user-agent={HEADERS['User-Agent']}")
                chrome_options.add_argument(f"--proxy-server=http://{proxy}")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)

                driver = webdriver.Chrome(service=webdriver.chrome.service.Service(ChromeDriverManager().install()), options=chrome_options)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                driver.get(url)
                wait = WebDriverWait(driver, 30)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(5)

                page_source = driver.page_source
                html_file = save_response(page_source, 'selenium_proxy', 'success', timestamp)
                items, title, issues = parse_response(page_source)
                logger.info(f"Found {len(items)} items with class 'item '")
                logger.info(f"Page title: {title[:100]}...")
                for issue in issues:
                    logger.warning(f"Detected issue: {issue}")

                return page_source, len(items), html_file

            except (TimeoutException, WebDriverException) as e:
                logger.error(f"Selenium Error: {str(e)}")
                html_file = save_response(str(e), 'selenium_proxy', 'selenium', timestamp)
                logger.debug(f"Full exception: {e}")
                time.sleep(delay * 2)
            except Exception as e:
                logger.error(f"Unexpected Error: {str(e)}")
                html_file = save_response(str(e), 'selenium_proxy', 'unexpected', timestamp)
                logger.debug(f"Full exception: {e}")
            finally:
                if driver:
                    driver.quit()

    logger.error(f"All proxies failed for {url}")
    return None, 0, None

def debug_all_methods(page_num=1):
    """Test all methods to scrape page."""
    url = DOMAIN if page_num == 1 else f"{DOMAIN}{page_num}/"
    logger.info(f"=== DEBUGGING PAGE {page_num}: {url} ===")
    logger.info(f"Environment: Python {os.sys.version}, OS: {os.name}, Working dir: {os.getcwd()}")
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check DNS
    check_dns('xnhau.sh')

    # Method 1: Requests without proxy
    logger.info("--- Method 1: Requests without proxy ---")
    response, item_count, html_file = method_requests_no_proxy(url)
    if item_count > 0:
        logger.info(f"SUCCESS with Method 1! Found {item_count} items. HTML: {html_file}")
        return response, item_count, html_file

    # Method 2: Requests with proxy
    logger.info("--- Method 2: Requests with proxy ---")
    response, item_count, html_file = method_requests_proxy(url)
    if item_count > 0:
        logger.info(f"SUCCESS with Method 2! Found {item_count} items. HTML: {html_file}")
        return response, item_count, html_file

    # Method 3: Selenium without proxy
    logger.info("--- Method 3: Selenium without proxy ---")
    response, item_count, html_file = method_selenium_no_proxy(url)
    if item_count > 0:
        logger.info(f"SUCCESS with Method 3! Found {item_count} items. HTML: {html_file}")
        return response, item_count, html_file

    # Method 4: Selenium with proxy
    logger.info("--- Method 4: Selenium with proxy ---")
    response, item_count, html_file = method_selenium_proxy(url)
    if item_count > 0:
        logger.info(f"SUCCESS with Method 4! Found {item_count} items. HTML: {html_file}")
        return response, item_count, html_file

    logger.error("All methods failed! No items found.")
    logger.info("Next steps:")
    logger.info("1. Check debug_all_methods.log for errors and response snippets.")
    logger.info("2. Open HTML files (debug_response_*.html) in browser.")
    logger.info("3. Try paid proxies (Bright Data, Smartproxy).")
    logger.info("4. Use undetected-chromedriver for Selenium.")
    logger.info("5. Run with VPN from different country.")
    return None, 0, None

if __name__ == '__main__':
    response, item_count, html_file = debug_all_methods(page_num=1)
    if item_count > 0:
        logger.info(f"Debug successful! Found {item_count} items in {html_file}")
    else:
        logger.error("Debug failed! Likely Cloudflare or IP block.")
