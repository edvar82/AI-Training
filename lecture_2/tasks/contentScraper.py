from urllib.robotparser import RobotFileParser
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from openai import OpenAI
import urllib.parse
import html2text
import requests
import argparse
import time
import os
import re

load_dotenv()

client = OpenAI(api_key=os.getenv("api_key"))

class ContentScraper:
    def __init__(self, base_url, output_dir, delay=1.0):
        """Initialize the content scraper with base URL and output directory"""
        self.base_url = base_url
        self.domain = urllib.parse.urlparse(base_url).netloc
        self.output_dir = output_dir
        self.delay = delay
        self.visited_urls = set()
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.ignore_tables = False
        self.html_converter.body_width = 0
        
        self.robot_parser = RobotFileParser()
        self.robot_parser.set_url(urllib.parse.urljoin(self.base_url, "/robots.txt"))
        try:
            self.robot_parser.read()
        except Exception as e:
            print(f"Warning: Could not read robots.txt: {e}")
    
    def is_allowed_url(self, url):
        """Check if URL is allowed to be scraped based on robots.txt"""
        return self.robot_parser.can_fetch("*", url)
    
    def clean_url(self, url):
        """Clean URL by removing fragments and query params"""
        parsed = urllib.parse.urlparse(url)
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    
    def normalize_url(self, url, current_url=None):
        """Normalize URL to absolute URL"""
        if not url:
            return None
            
        if url.startswith(('mailto:', 'javascript:', 'tel:')):
            return None
            
        if current_url and not url.startswith(('http://', 'https://')):
            return urllib.parse.urljoin(current_url, url)
        
        return url
    
    def should_scrape_url(self, url):
        """Check if the URL should be scraped"""
        if not url:
            return False
            
        parsed = urllib.parse.urlparse(url)
        
        if parsed.netloc != self.domain:
            return False
            
        if parsed.path.endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf')):
            return False
            
        cleaned_url = self.clean_url(url)
        if cleaned_url in self.visited_urls:
            return False
            
        if not self.is_allowed_url(url):
            print(f"Skipping {url} (disallowed by robots.txt)")
            return False
            
        return True
    
    def extract_title(self, soup):
        """Extract the title from the page"""
        if soup.title:
            return soup.title.string
        
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
            
        return "Untitled Page"
    
    def extract_main_content(self, soup):
        """Extract the main content from the page"""
        main = soup.find('main')
        if main:
            return main
            
        article = soup.find('article')
        if article:
            return article
            
        content = soup.find('div', {'id': 'content'}) or soup.find('div', {'class': 'content'})
        if content:
            return content
            
        return soup.body
    
    def find_links(self, soup, current_url):
        """Find all links in the page that should be followed"""
        links = []
        for a_tag in soup.find_all('a', href=True):
            url = self.normalize_url(a_tag['href'], current_url)
            if url and self.should_scrape_url(url):
                links.append(url)
        return links
    
    def html_to_markdown(self, html_content):
        """Convert HTML to Markdown"""
        return self.html_converter.handle(str(html_content))
    
    def clean_markdown(self, markdown_content):
        """Clean up the markdown content"""
        response = client.chat.completions.create(
            model = "gpt-4o-mini",
            messages= [
                {
                    "role": "system", 
                    "content": "You are an expert at converting HTML documentation to clean, well-formatted Markdown. Your task is to take automatically converted Markdown text that may have formatting issues and clean it up to be more readable and better structured. Maintain all content and links, but fix formatting issues, improve headers structure, and make the document more readable. Do not add or remove substantive content. Return only the cleaned Markdown with no explanations or additional text."
                },
                {
                    "role": "user", 
                    "content": f"Clean and improve this automatically converted Markdown from a documentation page:\n\n{markdown_content}\n\n"
                }
            ],
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    def save_markdown(self, url, title, markdown_content):
        """Save markdown content to a file"""
        parsed_url = urllib.parse.urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        relative_dir = os.path.join(self.output_dir, *path_parts[:-1]) if path_parts else self.output_dir
        os.makedirs(relative_dir, exist_ok=True)
        
        if path_parts and path_parts[-1]:
            filename = path_parts[-1]
            if not filename.endswith('.md'):
                filename += '.md'
        else:
            filename = 'index.md'
            
        filepath = os.path.join(relative_dir, filename)
        
        content = f"# {title}\n\n{markdown_content}"
        
        with open(filepath, 'w', encoding='utf-8') as file:
            file.write(content)
            
        return filepath
    
    def scrape_page(self, url):
        """Scrape a single page and convert to markdown"""
        cleaned_url = self.clean_url(url)
        if cleaned_url in self.visited_urls:
            return None
            
        self.visited_urls.add(cleaned_url)
        
        print(f"Scraping: {url}")
        
        try:
            response = requests.get(url, headers={'User-Agent': 'Documentation Scraper - Educational Project'})
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = self.extract_title(soup)
            main_content = self.extract_main_content(soup)
            
            markdown = self.html_to_markdown(main_content)
            
            cleaned_markdown = self.clean_markdown(markdown)
            
            filepath = self.save_markdown(url, title, cleaned_markdown)
            print(f"Saved to: {filepath}")
            
            links = self.find_links(soup, url)
            
            return {
                'title': title,
                'url': url,
                'filepath': filepath,
                'links': links
            }
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
        
        finally:
            time.sleep(self.delay)
    
    def create_index(self, pages):
        """Create an index file with links to all scraped pages"""
        index_path = os.path.join(self.output_dir, "contentScraper.md")
        
        if not pages:
            return
            
        pages_by_path = {}
        for page in pages:
            if not page:
                continue
                
            path = os.path.dirname(page['filepath'])
            
            if path not in pages_by_path:
                pages_by_path[path] = []
                
            pages_by_path[path].append(page)
        
        with open(index_path, 'w', encoding='utf-8') as file:
            file.write("# Documentation Index\n\n")
            
            def build_index(group, level=0):
                result = ""
                for path, path_pages in sorted(group.items()):
                    if isinstance(path_pages, list):
                        for page in sorted(path_pages, key=lambda p: p['title']):
                            rel_path = os.path.relpath(page['filepath'], self.output_dir)
                            indent = "  " * level
                            result += f"{indent}- [{page['title']}]({rel_path})\n"
                    else:
                        path_name = os.path.basename(path)
                        result += f"{'  ' * level}- **{path_name}**\n"
                        result += build_index(path_pages, level + 1)
                        
                return result
                
            file.write(build_index(pages_by_path))
            
        print(f"Index created at {index_path}")
        return index_path
    
    def scrape_site(self):
        """Scrape the entire site starting from the base URL"""
        to_scrape = [self.base_url]
        scraped_pages = []
        
        while to_scrape:
            url = to_scrape.pop(0)
            result = self.scrape_page(url)
            
            if result:
                scraped_pages.append(result)
                
                for link in result['links']:
                    if link not in [page.get('url') for page in scraped_pages] and link not in to_scrape:
                        to_scrape.append(link)
        
        index_path = self.create_index(scraped_pages)
        
        return scraped_pages, index_path

def parse_args():
    parser = argparse.ArgumentParser(description='Scrape documentation website and convert to Markdown')
    parser.add_argument('--url', default='https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/', help='Base URL to start scraping')
    parser.add_argument('--output', default='./outputs/docs', help='Output directory for markdown files')
    parser.add_argument('--delay', type=float, default=1.5, help='Delay between requests in seconds')
    parser.add_argument('--max-pages', type=int, default=20, help='Maximum number of pages to scrape')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    lecture_dir = os.path.dirname(current_dir)
    
    # Use Flask-SQLAlchemy documentation
    flask_sqlalchemy_url = "https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/"
    output_dir = os.path.join(lecture_dir, "outputs", "docs")
    summary_path = os.path.join(lecture_dir, "outputs", "contentScraper.md")
    
    print(f"Starting scraping of Flask-SQLAlchemy documentation: {flask_sqlalchemy_url}")
    print(f"Output directory: {output_dir}")
    
    # Create scraper and run it
    scraper = ContentScraper(flask_sqlalchemy_url, output_dir, delay=args.delay)
    scraped_pages, index_path = scraper.scrape_site()
    
    # Create a detailed summary
    summary = f"""# Content Scraper Results

## Flask-SQLAlchemy Documentation Scraping

This file contains a summary of the web scraping operation performed by contentScraper.py.

## Statistics
- Base URL: {flask_sqlalchemy_url}
- Pages scraped: {len(scraped_pages)}
- Scraped on: {time.strftime("%Y-%m-%d %H:%M:%S")}

## Structure
The scraped content is organized in a directory structure that mirrors the website's URL paths.
Each page is converted to clean, well-formatted Markdown with proper headers and links.

## Scraped Pages
"""

    for page in scraped_pages:
        if page:
            rel_path = os.path.relpath(page['filepath'], output_dir)
            summary += f"- [{page['title']}]({rel_path})\n"
    
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, 'w', encoding='utf-8') as file:
        file.write(summary)
    
    print(f"Content scraper summary saved to {summary_path}")
    print(f"Documentation index saved to {index_path}")
    print(f"Total pages scraped: {len(scraped_pages)}")
