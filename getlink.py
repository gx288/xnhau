import json
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import time
import pandas as pd
import os
from urllib.parse import urljoin
import logging
import re
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load config
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except Exception as e:
    logger.error(f"Failed to load config.json: {str(e)}")
    raise

DOMAIN = config['DOMAIN']
NUM_THREADS = config['NUM_THREADS']
LIMIT_PAGES_NO_NEW = config['LIMIT_PAGES_NO_NEW']
DETAIL_DELAY = config['DETAIL_DELAY']
DATA_TXT = config['DATA_TXT']
TEMP_CSV = config['TEMP_CSV']
FORCE_ALL_PAGES = config.get('FORCE_ALL_PAGES', False)
GOOGLE_SHEETS_ENABLED = config.get('GOOGLE_SHEETS_ENABLED', True)
SCOPE = config.get('SCOPE', [])
CREDENTIALS_FILE = config.get('CREDENTIALS_FILE', 'credentials.json')
SHEET_ID = config.get('SHEET_ID', '')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://xnhau.sh/'
}

all_video_data = []
new_items = 0
updated_items = 0
stop_scraping = False
total_pages_scraped = 0
total_items = 0


def convert_views(views_str):
    """Convert views string to integer."""
    views_str = views_str.lower().replace(',', '')
    try:
        if 'k' in views_str:
            return int(float(views_str.replace('k', '')) * 1000)
        elif 'm' in views_str:
            return int(float(views_str.replace('m', '')) * 1000000)
        return int(views_str)
    except:
        return 0


def convert_relative_time(relative_time):
    """Convert relative time to approximate datetime."""
    now = datetime.now()
    relative_time = relative_time.lower().strip()
    if 'phút trước' in relative_time:
        minutes = int(re.search(r'\d+', relative_time).group())
        return (now - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
    elif 'giờ trước' in relative_time:
        hours = int(re.search(r'\d+', relative_time).group())
        return (now - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    elif 'ngày trước' in relative_time:
        days = int(re.search(r'\d+', relative_time).group())
        return (now - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    elif 'tháng trước' in relative_time:
        months = int(re.search(r'\d+', relative_time).group())
        return (now - timedelta(days=months * 30)).strftime('%Y-%m-%d %H:%M:%S')  # Approximate
    elif 'năm trước' in relative_time:
        years = int(re.search(r'\d+', relative_time).group())
        return (now - timedelta(days=years * 365)).strftime('%Y-%m-%d %H:%M:%S')  # Approximate
    else:
        return relative_time  # Fallback if format unknown


def scrape_page(page_num, retries=3):
    """Scrape data from a single page."""
    global total_pages_scraped, stop_scraping, total_items
    for attempt in range(retries):
        try:
            url = DOMAIN if page_num == 1 else f"{DOMAIN}{page_num}/"
            logger.info(f"Scraping URL: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            if page_num == 1:
                with open('page1.html', 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logger.info("Saved HTML of page 1 to page1.html")

            soup = BeautifulSoup(response.text, 'html.parser')

            if "Không tìm thấy gì" in soup.text:
                stop_scraping = True
                logger.info(f"Stop: 'Không tìm thấy gì' on page {page_num}")
                return []

            # Flexible selector: try 'div.item ' first, fallback to article or regex
            items = soup.find_all('div', class_='item ')
            if not items:
                items = soup.find_all('article') or soup.find_all('div', class_=re.compile(r'(video|item|post)'))

            if not items:
                logger.info(f"No items found on page {page_num}")
                if page_num > 1:
                    stop_scraping = True
                return []

            page_data = []
            for item in items:
                try:
                    a = item.find('a')
                    if not a:
                        continue

                    link = urljoin(DOMAIN, a.get('href', ''))
                    title = a.get('title', '') or a.text.strip()

                    id_match = re.search(r'/video/(\d+)/', link)
                    post_id = id_match.group(1) if id_match else None
                    if not post_id:
                        continue

                    img = item.find('img', class_='thumb') or item.find('img')
                    # Prioritize data-webp or data-src, fallback to src if not placeholder
                    thumbnail = img.get('data-webp', '') or img.get('data-src', '') or img.get('src', '')
                    if thumbnail.startswith('data:image/'):
                        thumbnail = ''  # Ignore placeholder
                    thumbnail = urljoin(DOMAIN, thumbnail) if thumbnail else ''

                    preview = img.get('data-preview', '') if img and 'data-preview' in img.attrs else ''
                    preview = urljoin(DOMAIN, preview) if preview else ''

                    duration_elem = item.find('div', class_='duration') or item.find('span', class_='duration')
                    duration = duration_elem.text.strip() if duration_elem else ''

                    rating_div = item.find('div', class_='rating')
                    rating = 0
                    rating_type = ''
                    if rating_div:
                        rating_type = 'positive' if 'positive' in rating_div.get('class',
                                                                                 []) else 'negative' if 'negative' in rating_div.get(
                            'class', []) else ''
                        circle = rating_div.find('circle', class_='e-c-progress')
                        if circle:
                            style = circle.get('style', '')
                            array_match = re.search(r'stroke-dasharray:\s*([\d.]+)px', style)
                            offset_match = re.search(r'stroke-dashoffset:([\d.]+)px', style)
                            if array_match and offset_match:
                                array = float(array_match.group(1))
                                offset = float(offset_match.group(1))
                                if array > 0:
                                    rating = round(((array - offset) / array) * 100)

                    added_elem = item.find('div', class_='added')
                    relative_added = added_elem.find('em').text.strip() if added_elem and added_elem.find('em') else ''
                    added = convert_relative_time(relative_added)

                    views_elem = item.find('div', class_='views') or item.find('span', class_='views')
                    views_str = views_elem.text.strip() if views_elem else '0'
                    views = convert_views(views_str)

                    video_data = {
                        'page': page_num,
                        'id': post_id,
                        'title': title,
                        'link': link,
                        'thumbnail': thumbnail,
                        'preview': preview,
                        'duration': duration,
                        'rating': rating,
                        'rating_type': rating_type,
                        'added': added,
                        'views': views
                    }
                    page_data.append(video_data)

                except Exception as e:
                    logger.error(f"Error parsing item on page {page_num}: {str(e)}")
                    continue

            total_pages_scraped += 1
            total_items += len(page_data)
            if len(page_data) != 29:
                logger.warning(f"Anomalous page {page_num}: Found {len(page_data)} items (expected 29)")
            else:
                logger.info(f"Page {page_num}: Found 29 items")
            return page_data

        except requests.exceptions.HTTPError as http_err:
            if '404' in str(http_err) and page_num > 1:
                stop_scraping = True
                logger.info(f"Stop: 404 error on page {page_num}")
                return []
            logger.error(f"HTTP error on page {page_num}, attempt {attempt + 1}: {str(http_err)}")
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request error on page {page_num}, attempt {attempt + 1}: {str(req_err)}")
        time.sleep(2 ** attempt)
    return []


def load_existing_data():
    """Load existing data from data.txt."""
    if os.path.exists(DATA_TXT):
        try:
            with open(DATA_TXT, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_data(data):
    """Save data to data.txt and optionally Google Sheets."""
    try:
        sorted_data = sorted(data, key=lambda x: (x['page'], -int(x['id'])))
        with open(DATA_TXT, 'w', encoding='utf-8') as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=2)

        df = pd.DataFrame(sorted_data)
        if not df.empty:
            df['id'] = pd.to_numeric(df['id'], errors='coerce')
            df = df.sort_values(by=['page', 'id'], ascending=[True, False])
            df.to_csv(TEMP_CSV, index=False, encoding='utf-8')

            if GOOGLE_SHEETS_ENABLED and os.path.exists(CREDENTIALS_FILE):
                try:
                    from google.oauth2.service_account import Credentials
                    import gspread
                    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
                    client = gspread.authorize(creds)
                    sheet = client.open_by_key(SHEET_ID).sheet1
                    sheet.clear()
                    sheet.update([df.columns.values.tolist()] + df.values.tolist())
                    logger.info("Updated Google Sheets successfully")
                except Exception as e:
                    logger.error(f"Error updating Google Sheets: {str(e)}")
            else:
                logger.info("Skipped Google Sheets update: credentials.json not found or disabled")

    except Exception as e:
        logger.error(f"Error saving data: {str(e)}")


def main():
    """Main function."""
    global all_video_data, stop_scraping, new_items, updated_items, total_items
    logger.info("Starting scraper")
    existing_data = load_existing_data()
    existing_dict = {item['id']: item for item in existing_data}
    max_pages = 10000
    batch_size = 50

    logger.info(
        f"Config: NUM_THREADS={NUM_THREADS}, LIMIT_PAGES_NO_NEW={LIMIT_PAGES_NO_NEW}, FORCE_ALL_PAGES={FORCE_ALL_PAGES}")
    logger.info("Scraping page 1")
    all_video_data = []
    stop_scraping = False
    page1_data = scrape_page(1)
    all_video_data.extend(page1_data)

    has_new_posts = any(item['id'] not in existing_dict for item in page1_data)
    pages_to_scrape = max_pages if FORCE_ALL_PAGES or has_new_posts else LIMIT_PAGES_NO_NEW
    logger.info(
        f"Mode: {'Scraping all pages' if FORCE_ALL_PAGES or has_new_posts else f'Scraping first {LIMIT_PAGES_NO_NEW} pages'} (Total: {pages_to_scrape} pages)")

    new_items += sum(1 for item in page1_data if item['id'] not in existing_dict)
    updated_items += sum(1 for item in page1_data if item['id'] in existing_dict)

    page_num = 2
    while page_num <= pages_to_scrape and not stop_scraping:
        start_page = page_num
        end_page = min(page_num + batch_size - 1, pages_to_scrape)
        logger.info(
            f"Processing batch from page {start_page} to {end_page} (Progress: {total_pages_scraped}/{pages_to_scrape} pages, {total_items} items so far)")

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = [executor.submit(scrape_page, i) for i in range(start_page, end_page + 1)]
            for future in futures:
                page_data = future.result()
                all_video_data.extend(page_data)
                new_items += sum(1 for item in page_data if item['id'] not in existing_dict)
                updated_items += sum(1 for item in page_data if item['id'] in existing_dict)

        logger.info(
            f"Batch complete: {start_page} to {end_page}, {total_pages_scraped} pages scraped, {total_items} items collected")
        page_num += batch_size

    logger.info(
        f"Scraping complete: {total_pages_scraped} pages scraped, {total_items} items collected, {new_items} new items, {updated_items} updated items")

    for item in all_video_data:
        existing_dict[item['id']] = item
    unique_data = list(existing_dict.values())
    save_data(unique_data)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Main function error: {str(e)}")