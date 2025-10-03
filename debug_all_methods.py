import json
import requests
from bs4 import BeautifulSoup
from undetected_chromedriver import Chrome, ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
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
        logging.FileHandler('debug_referer_google.log', encoding='utf-8'),
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
        'Referer': 'https://www.google.com/',  # Simulate coming from Google
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1'
    })
except Exception as e:
    logger.warning(f"Failed to load config.json: {str(e)}. Using defaults.")
    DOMAIN = "https://xnhau.sh/clip-sex-moi/"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1'
    }

# Proxy list (prioritize working proxy)
PROXIES_LIST = [
    '36.50.53.219:11995',  # Worked previously
    '157.250.203.234:8080',
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
    """Method 1: Requests without proxy, Referer Google."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Method 1: Requests without proxy, Referer Google to {url}")
    logger.debug(f"Request headers: {HEADERS}")
    session = requests.Session()

    # Simulate Google search visit
    try:
        session.get('https://www.google.com/', headers=HEADERS, timeout=10)
        logger.info("Simulated visit to Google for cookies")
    except Exception as e:
        logger.warning(f"Failed to visit Google: {str(e)}")

    for attempt in range(retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{retries} (delay: {delay}s)")
            time.sleep(delay)
            response = session.get(url, headers=HEADERS, timeout=20, allow_redirects=True, verify=True)
            logger.info(f"Status code: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response content-length: {len(response.text)}")

            html_file = save_response(response.text, 'requests_no_proxy_referer_google', str(response.status_code), timestamp)
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
                html_file = save_response(http_err.response.text, 'requests_no_proxy_referer_google', str(http_err.response.status_code), timestamp)
            logger.debug(f"Full exception: {http_err}")
            time.sleep(delay * 2)

        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request Error: {str(req_err)}")
            html_file = save_response(str(req_err), 'requests_no_proxy_referer_google', 'request', timestamp)
            logger.debug(f"Full exception: {req_err}")
            time.sleep(delay * 2)

    logger.error(f"All {retries} attempts failed for {url}")
    return None, 0, None

def method_requests_proxy(url, retries=2, delay=2):
    """Method 2: Requests with proxy, Referer Google."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Method 2: Requests with proxy, Referer Google to {url}")
    random.shuffle(PROXIES_LIST)

    for proxy in PROXIES_LIST:
        proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
        logger.info(f"Trying proxy: {proxy}")
        session = requests.Session()

        # Simulate Google visit
        try:
            session.get('https://www.google.com/', headers=HEADERS, proxies=proxies, timeout=10)
            logger.info("Simulated visit to Google for cookies")
        except Exception as e:
            logger.warning(f"Failed to visit Google with proxy {proxy}: {str(e)}")

        for attempt in range(retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{retries} (delay: {delay}s)")
                time.sleep(delay)
                response = session.get(url, headers=HEADERS, proxies=proxies, timeout=20, allow_redirects=True, verify=True)
                logger.info(f"Status code: {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response content-length: {len(response.text)}")

                html_file = save_response(response.text, 'requests_proxy_referer_google', str(response.status_code), timestamp)
                items, title, issues = parse_response(response.text)
                logger.info(f"Found {len(items)} items with class 'item '")
                logger.info(f"Page title: {title[:100]}...")
                for issue in issues:
                    logger.warning(f"Detected issue: {issue}")

                return response, len(items), html_file

            except requests.exceptions.ProxyError as proxy_err:
                logger.error(f"Proxy Error: {str(proxy_err)}. Proxy {proxy} may be invalid.")
                html_file = save_response(str(proxy_err), 'requests_proxy_referer_google', 'proxy', timestamp)
                logger.debug(f"Full exception: {proxy_err}")
                break
            except requests.exceptions.RequestException as req_err:
                logger.error(f"Request Error: {str(req_err)}")
                html_file = save_response(str(req_err), 'requests_proxy_referer_google', 'request', timestamp)
                logger.debug(f"Full exception: {req_err}")
                time.sleep(delay * 2)

    logger.error(f"All proxies failed for {url}")
    return None, 0, None

def method_selenium_no_proxy(url, retries=2, delay=5):
    """Method 3: Selenium without proxy, Referer Google."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Method 3: Selenium without proxy, Referer Google to {url}")

    for attempt in range(retries):
        driver = None
        try:
            logger.info(f"Attempt {attempt + 1}/{retries} (delay: {delay}s)")
            time.sleep(delay)

            chrome_options = ChromeOptions()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(f"--user-agent={HEADERS['User-Agent']}")
            chrome_options.add_argument(f"--referer={HEADERS['Referer']}")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            driver = Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Simulate Google visit
            driver.get('https://www.google.com/')
            time.sleep(2)
            logger.info("Simulated visit to Google for cookies")

            driver.get(url)
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(5)

            page_source = driver.page_source
            html_file = save_response(page_source, 'selenium_no_proxy_referer_google', 'success', timestamp)
            items, title, issues = parse_response(page_source)
            logger.info(f"Found {len(items)} items with class 'item '")
            logger.info(f"Page title: {title[:100]}...")
            for issue in issues:
                logger.warning(f"Detected issue: {issue}")

            return page_source, len(items), html_file

        except (TimeoutException, WebDriverException) as e:
            logger.error(f"Selenium Error: {str(e)}")
            html_file = save_response(str(e), 'selenium_no_proxy_referer_google', 'selenium', timestamp)
            logger.debug(f"Full exception: {e}")
            time.sleep(delay * 2)
        except Exception as e:
            logger.error(f"Unexpected Error: {str(e)}")
            html_file = save_response(str(e), 'selenium_no_proxy_referer_google', 'unexpected', timestamp)
            logger.debug(f"Full exception: {e}")
        finally:
            if driver:
                driver.quit()

    logger.error(f"All {retries} attempts failed for {url}")
    return None, 0, None

def method_selenium_proxy(url, retries=2, delay=5):
    """Method 4: Selenium with proxy, Referer Google."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Method 4: Selenium with proxy, Referer Google to {url}")
    random.shuffle(PROXIES_LIST)

    for proxy in PROXIES_LIST:
        logger.info(f"Trying proxy: {proxy}")
        for attempt in range(retries):
            driver = None
            try:
                logger.info(f"Attempt {attempt + 1}/{retries} (delay: {delay}s)")
                time.sleep(delay)

                chrome_options = ChromeOptions()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument(f"--user-agent={HEADERS['User-Agent']}")
                chrome_options.add_argument(f"--proxy-server=http://{proxy}")
                chrome_options.add_argument(f"--referer={HEADERS['Referer']}")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)

                driver = Chrome(options=chrome_options)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                # Simulate Google visit
                driver.get('https://www.google.com/')
                time.sleep(2)
                logger.info("Simulated visit to Google for cookies")

                driver.get(url)
                wait = WebDriverWait(driver, 30)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(5)

                page_source = driver.page_source
                html_file = save_response(page_source, 'selenium_proxy_referer_google', 'success', timestamp)
                items, title, issues = parse_response(page_source)
                logger.info(f"Found {len(items)} items with class 'item '")
                logger.info(f"Page title: {title[:100]}...")
                for issue in issues:
                    logger.warning(f"Detected issue: {issue}")

                return page_source, len(items), html_file

            except (TimeoutException, WebDriverException) as e:
                logger.error(f"Selenium Error: {str(e)}")
                html_file = save_response(str(e), 'selenium_proxy_referer_google', 'selenium', timestamp)
                logger.debug(f"Full exception: {e}")
                time.sleep(delay * 2)
            except Exception as e:
                logger.error(f"Unexpected Error: {str(e)}")
                html_file = save_response(str(e), 'selenium_proxy_referer_google', 'unexpected', timestamp)
                logger.debug(f"Full exception: {e}")
            finally:
                if driver:
                    driver.quit()

    logger.error(f"All proxies failed for {url}")
    return None, 0, None

def debug_all_methods(page_num=1):
    """Test all methods with Referer Google."""
    url = DOMAIN if page_num == 1 else f"{DOMAIN}{page_num}/"
    logger.info(f"=== DEBUGGING PAGE {page_num}: {url} ===")
    logger.info(f"Environment: Python {os.sys.version}, OS: {os.name}, Working dir: {os.getcwd()}")
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check DNS
    check_dns('xnhau.sh')

    # Method 1: Requests without proxy, Referer Google
    logger.info("--- Method 1: Requests without proxy, Referer Google ---")
    response, item_count, html_file = method_requests_no_proxy(url)
    if item_count > 0:
        logger.info(f"SUCCESS with Method 1! Found {item_count} items. HTML: {html_file}")
        return response, item_count, html_file

    # Method 2: Requests with proxy, Referer Google
    logger.info("--- Method 2: Requests with proxy, Referer Google ---")
    response, item_count, html_file = method_requests_proxy(url)
    if item_count > 0:
        logger.info(f"SUCCESS with Method 2! Found {item_count} items. HTML: {html_file}")
        return response, item_count, html_file

    # Method 3: Selenium without proxy, Referer Google
    logger.info("--- Method 3: Selenium without proxy, Referer Google ---")
    response, item_count, html_file = method_selenium_no_proxy(url)
    if item_count > 0:
        logger.info(f"SUCCESS with Method 3! Found {item_count} items. HTML: {html_file}")
        return response, item_count, html_file

    # Method 4: Selenium with proxy, Referer Google
    logger.info("--- Method 4: Selenium with proxy, Referer Google ---")
    response, item_count, html_file = method_selenium_proxy(url)
    if item_count > 0:
        logger.info(f"SUCCESS with Method 4! Found {item_count} items. HTML: {html_file}")
        return response, item_count, html_file

    logger.error("All methods failed! No items found.")
    logger.info("Next steps:")
    logger.info("1. Check debug_referer_google.log for errors and response snippets.")
    logger.info("2. Open HTML files (debug_response_*.html) in browser.")
    logger.info("3. Try paid proxies (Bright Data, Smartproxy).")
    logger.info("4. Extract cookies from local browser and add to requests.")
    logger.info("5. Run with VPN from different country.")
    return None, 0, None

if __name__ == '__main__':
    response, item_count, html_file = debug_all_methods(page_num=1)
    if item_count > 0:
        logger.info(f"Debug successful! Found {item_count} items in {html_file}")
    else:
        logger.error("Debug failed! Likely Cloudflare or IP block.")
