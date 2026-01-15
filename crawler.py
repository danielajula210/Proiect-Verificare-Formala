import requests
import time
import re

ZENODO_API = "https://zenodo.org/api/records"
PER_PAGE = 20 


KEYWORDS = [
    "functional correctness",
    "termination",
    "complexity bounds",
    "verification of neural networks",
    "quantified boolean formulae QBF evaluation",
]

def clean_text_for_markdown(text):
    if not text: return "N/A"
    text = re.sub(r'<[^>]+>', '', str(text))
    text = text.replace('\n', ' ').replace('\r', '').replace('|', '/')
    if len(text) > 300: return text[:297] + "..."
    return text

def search_zenodo(query, page=1):
    params = {
        "q": query,
        "size": PER_PAGE,
        "page": page,
        "sort": "mostrecent"
    }
    
    try:
        r = requests.get(ZENODO_API, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"!!! Error '{query}': {e}")
        return None

def extract_meta(item):
    md = item.get('metadata', {})
    stats = item.get('stats', {})
    
    title = clean_text_for_markdown(md.get('title', 'N/A'))
    
    resource_type = md.get('resource_type', {}).get('type', 'Unknown')
    
    creators = md.get('creators', [])
    authors = ", ".join([c.get('name') for c in creators[:3]])
    if len(creators) > 3: authors += " et al."
    
    url = item.get('links', {}).get('html', item.get('doi', ''))
    
    description = clean_text_for_markdown(md.get('description', ''))
    
    downloads = stats.get('downloads', 0)
    
    return {
        "title": title,
        "type": resource_type,
        "authors": authors,
        "date": md.get('publication_date', ''),
        "url": url,
        "desc": description,
        "downloads": downloads
    }

def main():
    found_items = {}
    
    print(f"--- Starting Broad Crawl on Zenodo ---")
    
    for kw in KEYWORDS:
        print(f"\n[*] Searching: '{kw}'...")
        
        for page in range(1, 3): 
            data = search_zenodo(kw, page)
            
            if not data:
                break
                
            hits = data.get('hits', {}).get('hits', [])
            total = data.get('hits', {}).get('total', 0)
            
            if page == 1:
                print(f"Zenodo reports {total} total results")
            
            if not hits:
                print("No results")
                break
                
            for h in hits:
                meta = extract_meta(h)
                
                if meta['type'] in ['poster', 'presentation', 'lesson']:
                    continue
                    
                if meta['url'] not in found_items:
                    found_items[meta['url']] = meta
                    print(f"Found [{meta['type']}]: {meta['title'][:50]}...")
            
            time.sleep(1) 
            
    filename = 'zenodo_tools_broad.md'
    print(f"\nWriting {len(found_items)} results in {filename}...")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# Verification Artifacts & Tools\n\n")
        f.write("| Type | Title | Authors | Date | Downloads | Link |\n")
        f.write("|------|-------|---------|------|-----------|------|\n")
        
        sorted_items = sorted(found_items.values(), key=lambda x: x['downloads'], reverse=True)
        
        for i in sorted_items:
            f.write(f"| {i['type']} | {i['title']} | {i['authors']} | {i['date']} | {i['downloads']} | [Link]({i['url']}) |\n")

    print("Done")

if __name__ == '__main__':
    main()