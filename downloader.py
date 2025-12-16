#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin
import sys
import re
import opencc

def download_image(url, folder, min_size_kb=25):
    """
    Download an image from the given URL and save it to the specified folder.
    Skip images smaller than min_size_kb and those that already exist.
    """
    try:
        img_filename = url.split("/")[-1]
        img_path = os.path.join(folder, img_filename)

        # Skip download if the image already exists
        if os.path.exists(img_path):
            print(f"Image already exists: {url}")
            return

        img_response = requests.get(url, stream=True)
        img_size_kb = int(img_response.headers.get('content-length', 0)) / 1024

        if img_size_kb >= min_size_kb:
            print(f"Downloading image: {url}")
            with open(img_path, 'wb') as f:
                for chunk in img_response.iter_content(1024):
                    f.write(chunk)
        else:
            print(f"Skipping small image ({img_size_kb:.2f} KB): {url}")
    except Exception as e:
        print(f"Failed to download image {url}: {e}")


def get_page_title(soup):
    """
    Extract the title of the page from the HTML and convert it to traditional Chinese.
    First, try to get the <title> tag content, then fall back to the first <h1> tag.
    If neither is found, return "Untitled".
    """
    converter = opencc.OpenCC('s2t.json')  # Simplified to Traditional converter
    
    title_tag = soup.find('title')
    if title_tag:
        return converter.convert(title_tag.string.strip())
    h1_tag = soup.find('h1')
    if h1_tag:
        return converter.convert(h1_tag.string.strip())
    return "Untitled"

def get_next_url(soup, current_url):
    """
    Find the URL of the next page by looking for a link with the text "下一页" (Next Page).
    Return None if no such link is found.
    Handles both standard hrefs and javascript:ContentPageHref pagination.
    """
    next_link = soup.find('a', string='下一页')
    if next_link and 'href' in next_link.attrs:
        href = next_link['href']
        
        # Handle JavaScript pagination
        if href.startswith('javascript:ContentPageHref'):
            try:
                # Extract the URL template from the function call
                # Expected format ends with: , 'template');
                match = re.search(r",\s*'([^']*)'\);?$", href)
                if match:
                    url_template = match.group(1)
                    
                    # Determine current page number from current_url
                    page_match = re.search(r"_(\d+)\.html$", current_url)
                    if page_match:
                        current_page = int(page_match.group(1))
                    else:
                        # Assuming start page is page 1
                        current_page = 1
                    
                    next_page = current_page + 1
                    
                    # Generate next URL
                    if '[page]' in url_template:
                        next_relative = url_template.replace('[page]', str(next_page))
                        return urljoin(current_url, next_relative)
            except Exception as e:
                print(f"Warning: Failed to parse Javascript link: {e}")
                return None
                
        else:
            return urljoin(current_url, href)
    return None

def download_images(start_url, min_size_kb=25):
    """
    Main function to download images from a series of web pages.
    Start from the given URL, download images, then move to the next page until no more pages are found.
    """
    print(f"Requesting initial page: {start_url}")
    response = requests.get(start_url)
    if response.status_code != 200:
        print(f"Failed to retrieve {start_url}: {response.status_code}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    title = get_page_title(soup)
    output_folder = re.sub(r'[^\w\-_\. ]', '_', title)  # Sanitize folder name
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder, exist_ok=True)
    
    print(f"Output folder: {output_folder}")

    url = start_url

    while True:
        print(f"Processing page: {url}")
        
        # Find all image tags on the current page
        images = soup.find_all('img')

        # Download each image found
        for img in images:
            img_src = img.get('src')
            if img_src:
                img_url = urljoin(url, img_src)
                if img_url.startswith('http'):
                    download_image(img_url, output_folder, min_size_kb)

        # Find the URL of the next page
        next_url = get_next_url(soup, url)
        if not next_url:
            print(f"No more pages found. Stopping at: {url}")
            break

        url = next_url
        print(f"Next URL: {url}")
        
        # Request the next page
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to retrieve {url}: {response.status_code}")
            break
        
        soup = BeautifulSoup(response.content, 'html.parser')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python downloader.py [START_URL] [MIN_SIZE_KB]")
        sys.exit(1)

    start_url = sys.argv[1]
    min_size_kb = 25
    
    if len(sys.argv) > 2:
        try:
            min_size_kb = float(sys.argv[2])
        except ValueError:
            print("Error: MIN_SIZE_KB must be a number")
            sys.exit(1)
            
    download_images(start_url, min_size_kb)

"""
This script downloads images from a series of web pages, starting from a given URL.
It performs the following steps:
1. Starts from the provided URL.
2. Extracts the page title to create a folder for storing images.
3. Finds and downloads all images on the current page.
4. Looks for a "Next Page" link (text: "下一页") to navigate to the next page.
5. Repeats steps 3-4 until no more "Next Page" links are found.

The script skips images smaller than 50KB and those that have already been downloaded.
It handles relative URLs for both images and "Next Page" links.

Usage: python downloader.py [START_URL]
Example: python downloader.py https://example.com/gallery/page1.html
"""
