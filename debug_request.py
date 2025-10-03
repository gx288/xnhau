import json
import requests
from bs4 import BeautifulSoup  # Optional, for basic parsing if needed
import os
import logging
import time
from datetime import datetime
import random

# Set up logging (detailed for debug)
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG to capture everything
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load config (minimal, fallback if no config.json)
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    DOMAIN = config['DOMAIN']
    HEADERS = config.get('HEADERS', {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://xnhau.sh/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
except Exception as e:
    logger.warning(f"Failed to load config.json: {str(e)}. Using defaults.")
    DOMAIN = "https://xnhau.sh/clip-sex-moi/"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://xnhau.sh/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

# List of free proxies (HTTP/HTTPS). You can add/remove or use paid proxies.
PROXIES_LIST = [
    '31.193.193.69:1488',
    '41.32.39.7:3128',
    '5.75.196.127:1080',
    '62.171.159.232:8888',
    '102.222.161.143:3128',
    '101.1.59.65:443',
    '27.65.98.229:12921',
    '117.7.195.193:11991',
    '36.50.53.219:11995',
    '52.67.251.34:80',
    '185.216.125.251:8888',
    '115.77.241.248:10001',
    '14.251.13.0:8080',
    '8.219.97.248:80',
    '34.160.134.22:3128',
    '67.43.236.18:3927',
    '157.250.203.234:8080',
    '45.14.224.247:80',
    '43.129.93.201:5000',
    '47.242.49.57:1122'
]

def make_request(url, proxy=None, retries=3, delay=1):
    """
    Make a single request with optional proxy, catch all errors, log everything.
    Returns (response, error_msg) or (None, error_msg) if fail.
    """
    proxies = None
    if proxy:
        proxies = {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }
        logger.info(f"Attempting request to {url} with proxy {proxy}")
    else:
        logger.info(f"Attempting request to {url} without proxy")

    logger.debug(f"Request headers: {HEADERS}")

    for attempt in range(retries):
        try:
            logger.info(f"  Attempt {attempt + 1}/{retries} (delay: {delay}s)")
            time.sleep(delay)  # Delay before each attempt

            response = requests.get(
                url,
                headers=HEADERS,
                proxies=proxies,
                timeout=20,  # Increased timeout
                allow_redirects=True,
                verify=True  # Verify SSL
            )

            logger.info(f"  Status code: {response.status_code}")
            logger.debug(f"  Response headers: {dict(response.headers)}")
            logger.debug(f"  Response content-length: {len(response.text)}")

            # Save full response to file
            with open('debug_response.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info("Saved full response to debug_response.html")

            # Check for common issues in response
            if 'cloudflare' in response.text.lower() or 'cf-ray' in response.headers:
                logger.warning("  Detected Cloudflare protection in response")
            if 'login' in response.text.lower() or 'authentication' in response.text.lower():
                logger.warning("  Detected login/authentication required")
            if 'captcha' in response.text.lower():
                logger.warning("  Detected CAPTCHA in response")

            # Parse lightly to check for items (optional)
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', class_='item ')
            logger.info(f"  Found {len(items)} items with class 'item '")

            return response, None

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"  HTTP Error (code: {http_err.response.status_code if hasattr(http_err, 'response') else 'Unknown'}): {str(http_err)}")
            if hasattr(http_err, 'response') and http_err.response is not None:
                logger.error(f"  Response body (first 1000 chars): {http_err.response.text[:1000]}")
                # Save error response
                with open('debug_error_response.html', 'w', encoding='utf-8') as f:
                    f.write(http_err.response.text)
                logger.info("Saved error response to debug_error_response.html")
            logger.debug(f"  Full exception: {http_err}")
            time.sleep(delay * 2)  # Exponential backoff

        except requests.exceptions.ProxyError as proxy_err:
            logger.error(f"  Proxy Error: {str(proxy_err)}. Proxy {proxy} may be invalid or blocked.")
            logger.debug(f"  Full exception: {proxy_err}")
            time.sleep(delay * 2)

        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"  Connection Error: {str(conn_err)}. Check network/DNS/IP.")
            logger.debug(f"  Full exception: {conn_err}")
            time.sleep(delay * 2)

        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"  Timeout Error: {str(timeout_err)}. Server slow or firewall.")
            logger.debug(f"  Full exception: {timeout_err}")
            time.sleep(delay * 2)

        except requests.exceptions.SSLError as ssl_err:
            logger.error(f"  SSL Error: {str(ssl_err)}. Certificate issue or MITM.")
            logger.debug(f"  Full exception: {ssl_err}")
            time.sleep(delay * 2)

        except requests.exceptions.RequestException as req_err:
            logger.error(f"  General Request Error: {str(req_err)}")
            logger.debug(f"  Full exception: {req_err}")
            time.sleep(delay * 2)

        except Exception as unexpected_err:
            logger.error(f"  Unexpected Error: {str(unexpected_err)}")
            logger.debug(f"  Full exception: {unexpected_err}")
            time.sleep(delay * 2)

    logger.error(f"All {retries} attempts failed for {url}")
    return None, "All retries failed"

def debug_single_page(page_num=1):
    """Debug a single page (e.g., page 1)."""
    url = DOMAIN if page_num == 1 else f"{DOMAIN}{page_num}/"
    
    logger.info(f"=== DEBUGGING PAGE {page_num}: {url} ===")
    logger.info(f"Environment: Python {os.sys.version}, OS: {os.name}, Working dir: {os.getcwd()}")
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Without proxy
    logger.info("--- Test 1: Without Proxy ---")
    response, error = make_request(url, proxy=None, retries=3, delay=1)
    if response:
        logger.info("SUCCESS without proxy!")
        # Basic parse
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else "No title"
        logger.info(f"  Page title: {title[:100]}...")
        return response
    else:
        logger.warning("FAILED without proxy. Trying with proxies...")

    # Test 2: With proxies (try up to 5 random proxies)
    logger.info("--- Test 2: With Random Proxies ---")
    random.shuffle(PROXIES_LIST)  # Shuffle for randomness
    for i, proxy in enumerate(PROXIES_LIST[:5]):  # Try first 5
        logger.info(f"Trying proxy {i+1}/5: {proxy}")
        response, error = make_request(url, proxy=proxy, retries=2, delay=2)
        if response:
            logger.info(f"SUCCESS with proxy {proxy}!")
            return response
        else:
            logger.warning(f"FAILED with proxy {proxy}")

    logger.error("All tests failed. Check debug.log and debug_response.html for details.")
    return None

if __name__ == '__main__':
    # Run debug for page 1 (change page_num if needed)
    success_response = debug_single_page(page_num=1)
    
    if success_response:
        logger.info("Debug successful! Request worked. Check debug_response.html for content.")
        # Optional: Count items
        soup = BeautifulSoup(success_response.text, 'html.parser')
        items = soup.find_all('div', class_='item ')
        logger.info(f"Total items found: {len(items)}")
    else:
        logger.error("Debug failed! Possible causes: Cloudflare, geo-block, rate limit, or invalid proxies.")
        logger.info("Next steps:")
        logger.info("1. Check debug.log for full errors and response snippets.")
        logger.info("2. Open debug_response.html or debug_error_response.html in browser.")
        logger.info("3. Try different User-Agent in config.json.")
        logger.info("4. Use Selenium for JavaScript/Cloudflare (see comments in code).")
        logger.info("5. Run on VPN/proxy from different country.")
