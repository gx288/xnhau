import requests
from bs4 import BeautifulSoup

# URL and headers
url = "https://xnhau.sh/clip-sex-moi/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://xnhau.sh/",
}

# Proxy configuration
proxy_host = "42.96.12.24"
proxy_port = "49005"
proxy_user = "user49005"
proxy_pass = "2lsBkRUegO"
proxies = {
    "http": f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}",
    "https": f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
}

try:
    # Make request with proxy
    print(f"Trying proxy: {proxy_host}:{proxy_port}")
    response = requests.get(url, headers=headers, proxies=proxies, timeout=10, allow_redirects=True)
    print(f"Status code: {response.status_code}")
    print(f"Redirect history: {[r.url for r in response.history]}")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Print HTML
    print("\n=== HTML from soup ===")
    print(soup.prettify())
    
    # Save to file
    with open("response.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())
    print("\nSaved HTML to response.html")
    
    # Check items
    items = soup.find_all("div", class_="item ")
    print(f"\nFound {len(items)} items with class 'item '")
    
except Exception as e:
    print(f"Error: {str(e)}")
