import requests
from bs4 import BeautifulSoup
import json
import os
import re
from urllib.parse import urljoin
import time
import argparse
import sys

def get_soup(url):
    try:
        r = requests.get(url, timeout=10)
        r.encoding = 'big5'
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def clean_text(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)

def extract_content(soup):
    for script in soup(["script", "style"]):
        script.decompose()

    for br in soup.find_all("br"):
        br.replace_with("\n")
        
    for p in soup.find_all("p"):
        p.append("\n")
        
    text = soup.get_text()
    
    lines = text.split('\n')
    
    start_idx = 0
    end_idx = len(lines)
    
    # Heuristics to skip header
    for i, line in enumerate(lines[:50]):
        if "中文書庫" in line or "偵探小說" in line or "回目錄" in line:
            start_idx = i + 1
    
    # Heuristics to skip footer
    for i in range(len(lines) - 1, len(lines) - 50, -1):
        if i < start_idx: break
        if "上一頁" in line or "下一頁" in line or "回目錄" in line or "書香門第" in line:
            end_idx = i
            
    content = '\n'.join(lines[start_idx:end_idx])
    content = content.replace('　', ' ').strip()
    
    return content

def get_stories_list(base_url):
    soup = get_soup(base_url)
    if not soup:
        return []
    
    stories = []
    
    # Keywords to filter navigation links
    exclude_keywords = ["中文書庫", "偵探小說", "柯南道爾", "回首頁", "回目錄", "阿加莎", "克里斯蒂"]
    
    links = soup.find_all('a')
    for link in links:
        href = link.get('href')
        text = link.get_text(strip=True)
        
        if not href or not text:
            continue
            
        if href.startswith('..') or href.startswith('http'):
            continue
            
        if any(kw in text for kw in exclude_keywords):
            continue
            
        if href.startswith('javascript') or href.startswith('#'):
            continue

        full_url = urljoin(base_url, href)
        stories.append({'title': text, 'url': full_url})
             
    return stories

def process_short_story(title, url):
    print(f"Processing Short Story: {title}")
    soup = get_soup(url)
    if not soup:
        return None
    
    content = extract_content(soup)
    return {
        "title": title,
        "chapters": [
            {
                "title": title,
                "content": content
            }
        ]
    }

def process_novel(title, url):
    print(f"Processing Novel: {title}")
    soup = get_soup(url)
    if not soup:
        return None
        
    chapters = []
    links = soup.find_all('a')
    
    for link in links:
        href = link.get('href')
        text = link.get_text(strip=True)
        
        if not href: continue
        
        if href.startswith('..') or href.startswith('http') or href.startswith('javascript'):
            continue
            
        if "index" in href or "main" in href:
            continue
            
        chapter_url = urljoin(url, href)
        print(f"  Fetching Chapter: {text}")
        
        time.sleep(0.1)
        
        ch_soup = get_soup(chapter_url)
        if ch_soup:
            ch_content = extract_content(ch_soup)
            chapters.append({
                "title": text,
                "content": ch_content
            })
            
    return {
        "title": title,
        "chapters": chapters
    }

def main():
    parser = argparse.ArgumentParser(description='Download books from bwsk.net')
    parser.add_argument('folder_name', help='Name of the folder to save books to')
    parser.add_argument('url', help='URL of the index page')
    
    args = parser.parse_args()
    
    output_dir = args.folder_name
    base_url = args.url

    print(f"Downloading from {base_url} to {output_dir}")
    
    stories = get_stories_list(base_url)
    print(f"Found {len(stories)} stories.")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for story in stories:
        title = story['title']
        url = story['url']
        
        # Basic sanitization of filenames
        safe_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(os.sep, "_")
        filename = os.path.join(output_dir, f"{safe_title}.json")
        
        if os.path.exists(filename):
            print(f"Skipping {title}, already exists.")
            continue
            
        data = None
        # Heuristic: links ending in index.html (or variants) are novels (directories)
        # short stories are usually .htm or .html files
        if url.endswith('/') or 'index' in url.lower():
            data = process_novel(title, url)
        else:
            data = process_short_story(title, url)
            
        if data:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Saved {title}")
            
if __name__ == "__main__":
    main()
