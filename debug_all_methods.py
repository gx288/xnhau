import requests
from bs4 import BeautifulSoup

# URL and headers
url = "https://xnhau.sh/clip-sex-moi/"


try:
    # Make request
    response = requests.get(url, timeout=10, allow_redirects=True)
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
