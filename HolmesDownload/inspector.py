
import requests
from bs4 import BeautifulSoup
import sys

def check_index():
    url = "http://www.bwsk.net/zt/k/kenandaoer/index.html"
    try:
        r = requests.get(url)
        r.encoding = 'big5'
        soup = BeautifulSoup(r.text, 'html.parser')
        
        links = soup.find_all('a')
        for link in links:
            href = link.get('href')
            text = link.get_text(strip=True)
            print(f"{text} -> {href}")
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_index()
