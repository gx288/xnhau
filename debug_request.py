import json
import requests
from bs4 import BeautifulSoup
import os
import logging
import time
from datetime import datetime
import socket

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_no_proxy.log', encoding='utf-8'),
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

def check_dns(hostname):
    """Check DNS resolution for the hostname."""
    try:
        ip = socket.gethostbyname(hostname)
        logger.info(f"DNS resolved for {hostname}: {ip}")
        return ip
    except socket.gaierror as e:
        logger.error(f"DNS resolution failed for {hostname}: {str(e)}")
        return None

def make_request(url, retries=3, delay=1):
    """Make a single request without proxy, catch all errors."""
    logger.info(f"Attempting request to {url} without proxy")
    logger.debug(f"Request headers: {HEADERS}")

    for attempt in range(retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{retries} (delay: {delay}s)")
            time.sleep(delay)

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=20,
                allow_redirects=True,
                verify=True
            )

            logger.info(f"Status code: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            logger.debug(f"Response content-length: {len(response.text)}")

            # Save response
            with open('debug_response.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info("Saved full response to debug_response.html")

            # Check for common issues
            if 'cloudflare' in response.text.lower() or 'cf-ray' in response.headers:
                logger.warning("Detected Cloudflare protection in response")
            if 'login' in response.text.lower() or 'authentication' in response.text.lower():
                logger.warning("Detected login/authentication required")
            if 'captcha' in response.text.lower():
                logger.warning("Detected CAPTCHA in response")

            # Parse to check items
            soup = BeautifulSoup(response.text, 'html.parser')
            items = soup.find_all('div', class_='item ')
            logger.info(f"Found {len(items)} items with class 'item '")
            title = soup.title.string if soup.title else "No title"
            logger.info(f"Page title: {title[:100]}...")

            return response, None

        except requests.exceptions.HTTPError as http_err:
            error_msg = f"HTTP Error (code: {http_err.response.status_code if hasattr(http_err, 'response') else 'Unknown'}): {str(http_err)}"
            logger.error(error_msg)
            if hasattr(http_err, 'response') and http_err.response is not None:
                logger.error(f"Response body (first 1000 chars): {http_err.response.text[:1000]}")
                with open('debug_error_response.html', 'w', encoding='utf-8') as f:
                    f.write(http_err.response.text)
                logger.info("Saved error response to debug_error_response.html")
            logger.debug(f"Full exception: {http_err}")
            time.sleep(delay * 2)

        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Connection Error: {str(conn_err)}. Check network/DNS/IP.")
            logger.debug(f"Full exception: {conn_err}")
            time.sleep(delay * 2)

        except requests.exceptions.Timeout as timeout_err:
            logger.error(f"Timeout Error: {str(timeout_err)}. Server slow or firewall.")
            logger.debug(f"Full exception: {timeout_err}")
            time.sleep(delay * 2)

        except requests.exceptions.SSLError as ssl_err:
            logger.error(f"SSL Error: {str(ssl_err)}. Certificate issue or MITM.")
            logger.debug(f"Full exception: {ssl_err}")
            time.sleep(delay * 2)

        except requests.exceptions.RequestException as req_err:
            logger.error(f"General Request Error: {str(req_err)}")
            logger.debug(f"Full exception: {req_err}")
            time.sleep(delay * 2)

        except Exception as unexpected_err:
            logger.error(f"Unexpected Error: {str(unexpected_err)}")
            logger.debug(f"Full exception: {unexpected_err}")
            time.sleep(delay * 2)

    error_msg = f"All {retries} attempts failed for {url}"
    logger.error(error_msg)
    return None, error_msg

def debug_single_page(page_num=1):
    """Debug a single page without proxy."""
    url = DOMAIN if page_num == 1 else f"{DOMAIN}{page_num}/"
    
    logger.info(f"=== DEBUGGING PAGE {page_num}: {url} ===")
    logger.info(f"Environment: Python {os.sys.version}, OS: {os.name}, Working dir: {os.getcwd()}")
    logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check DNS
    hostname = 'xnhau.sh'
    check_dns(hostname)
    
    # Make request
    logger.info("--- Test: Without Proxy ---")
    response, error = make_request(url, retries=3, delay=1)
    
    if response:
        logger.info("SUCCESS without proxy!")
        return response
    else:
        logger.error("FAILED without proxy.")
        logger.info("Next steps:")
        logger.info("1. Check debug_no_proxy.log for full errors and response snippets.")
        logger.info("2. Open debug_response.html or debug_error_response.html in browser.")
        logger.info("3. Try different User-Agent in config.json.")
        logger.info("4. Use Selenium for Cloudflare (requires 'pip install selenium webdriver-manager').")
        logger.info("5. Run with proxy or VPN from different country.")
        return None

if __name__ == '__main__':
    success_response = debug_single_page(page_num=1)
    
    if success_response:
        logger.info("Debug successful! Request worked. Check debug_response.html for content.")
        soup = BeautifulSoup(success_response.text, 'html.parser')
        items = soup.find_all('div', class_='item ')
        logger.info(f"Total items found: {len(items)}")
    else:
        logger.error("Debug failed! Likely Cloudflare or IP block.")
