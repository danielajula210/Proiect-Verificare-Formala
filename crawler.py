import requests
import time
import re
import subprocess
import os
from datetime import datetime

ZENODO_API = "https://zenodo.org/api/records"
PER_PAGE = 20

WIKI_REPO_PATH = r"C:\Users\rares\Documents\master\VF\proiect\Proiect-Verificare-Formala\Proiect-Verificare-Formala.wiki"
MAIN_PAGE_FILENAME = 'Home.md'

CATEGORY_RULES = {
    "functional verification, program correctness": [
        "functional correctness", "correctness", "program verification", "verify", "model checking", "safety", "invariant generation"
    ],
    "proving (non-)termination": [
        "termination", "terminating", "liveness", "non-termination"
    ],
    "finding complexity bounds": [
        "complexity", "bounds", "resource analysis", "big-o", "cost analysis", "wcet"
    ],
    "verification of neural networks": [
        "neural network", "dnn", "cnn", "deep learning", "robustness", "adversarial"
    ],
    "QBF evaluation": [
        "qbf", "quantified boolean", "quantified", "boolean formula", "qbfeval"
    ]
}

def clean_text(text):
    if not text: return "-"
    text = re.sub(r'<[^>]+>', '', str(text))
    text = text.replace('\n', ' ').replace('\r', '').replace('|', '/')
    text = text.replace('[', '(').replace(']', ')')
    return text.strip()

def sanitize_filename(title):
    s = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    s = s.strip().replace(' ', '-')
    return s[:50]

def determine_status(pub_date_str):
    if not pub_date_str: return "unknown"
    try:
        pub_year = int(pub_date_str[:4])
        current_year = datetime.now().year
        if current_year - pub_year <= 5:
            return "maintained"
        else:
            return "legacy"
    except:
        return "unknown"

def guess_input_formats(description):
    formats = []
    text = description.lower()
    
    patterns = {
        " c ": "C", ".c": "C", "c-code": "C",
        "java": "Java", ".java": "Java", "jml": "JML",
        "haskell": "Haskell", ".hs": "Haskell",
        "python": "Python", ".py": "Python",
        "prolog": "Prolog",
        "llvm": "LLVM", "bitcode": "LLVM Bitcode",
        "smt": "SMT-LIB", ".smt2": "SMT-LIB",
        "boogie": "Boogie", ".bpl": "Boogie",
        "xml": "XML",
        "trs": "TRS", "rewrite system": "TRS",
        "cnf": "CNF",
        "automata": "Automata",
        "horn": "Horn Clauses"
    }
    
    for key, val in patterns.items():
        if key in text:
            formats.append(val)
            
    if not formats:
        return "-"
    return ", ".join(sorted(list(set(formats))))

def search_zenodo(query, page=1):
    params = {"q": query, "size": PER_PAGE, "page": page, "sort": "mostrecent"}
    try:
        r = requests.get(ZENODO_API, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Error {e}")
        return None

def extract_meta(item):
    md = item.get('metadata', {})
    stats = item.get('stats', {})
    
    title = clean_text(md.get('title', 'N/A'))
    
    url = item.get('links', {}).get('html')
    if not url:
        doi = item.get('doi')
        url = f"https://doi.org/{doi}" if doi else f"https://zenodo.org/records/{item.get('id')}"

    description = clean_text(md.get('description', ''))
    
    zenodo_keywords = md.get('keywords', [])
    full_text = (title + " " + description + " " + " ".join(zenodo_keywords)).lower()
    
    matched_categories = []
    for cat_name, triggers in CATEGORY_RULES.items():
        for trigger in triggers:
            if trigger.lower() in full_text:
                matched_categories.append(cat_name)
                break
    
    final_tags = ", ".join(matched_categories) if matched_categories else "-"
    status = determine_status(md.get('publication_date', ''))
    input_formats = guess_input_formats(description)

    return {
        "id": item.get('id'),
        "title": title,
        "authors": ", ".join([c.get('name') for c in md.get('creators', [])[:3]]),
        "date": md.get('publication_date', ''),
        "url": url,
        "description": description,
        "downloads": stats.get('downloads', 0),
        "tags": final_tags,
        "status": status,
        "input": input_formats
    }

def create_individual_page(tool):
    filename = sanitize_filename(tool['title']) + ".md"
    file_path = os.path.join(WIKI_REPO_PATH, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"# {tool['title']}\n\n")
        f.write(f"**Website:** [{tool['url']}]({tool['url']})\n\n")
        f.write(f"**Authors:** {tool['authors']}\n\n")
        f.write(f"**Status:** {tool['status']}\n\n")
        f.write(f"**Input formats:** {tool['input']}\n\n")
        f.write(f"**Used for:** {tool['tags']}\n\n")
        f.write(f"### Description\n{tool['description']}\n\n")
        f.write(f"\n---\n*Last updated: {tool['date']}*")
        
    return filename.replace('.md', '') 

def update_github_wiki():
    print(f"\n--- GITHUB WIKI AUTO-UPDATE ---")
    if not os.path.isdir(WIKI_REPO_PATH):
        print(f"!!! ERROR: Path '{WIKI_REPO_PATH}' not found.")
        return

    try:
        subprocess.run(["git", "add", "."], cwd=WIKI_REPO_PATH, check=True)
        message = f"Update Tools List: {time.strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", message], cwd=WIKI_REPO_PATH, check=False) 
        subprocess.run(["git", "push"], cwd=WIKI_REPO_PATH, check=True)
        print("SUCCESS!")
    except subprocess.CalledProcessError as e:
        print(f"GIT ERROR: {e}")

def main():
    found_items = {} 
    print(f"Starting crawl...")
    
    for cat_name, triggers in CATEGORY_RULES.items():
        search_term = triggers[0] 
        print(f"\n[*] Searching: '{cat_name}'")
        
        for page in range(1, 3): 
            data = search_zenodo(search_term, page)
            if not data or not data.get('hits', {}).get('hits'): break
                
            for h in data['hits']['hits']:
                meta = extract_meta(h)
                
                if h['metadata'].get('resource_type', {}).get('type') in ['poster', 'presentation', 'lesson']:
                    continue

                if meta['url'] not in found_items and meta['tags'] != "-":
                    found_items[meta['url']] = meta
                    print(f"    + Found: {meta['title'][:30]}...")
            time.sleep(1)

    sorted_items = sorted(found_items.values(), key=lambda x: x['downloads'], reverse=True)
    
    print(f"\nGenerating {len(sorted_items)} pages...")
    
    main_page_path = os.path.join(WIKI_REPO_PATH, MAIN_PAGE_FILENAME)
    os.makedirs(WIKI_REPO_PATH, exist_ok=True)
    
    with open(main_page_path, 'w', encoding='utf-8') as f:
        f.write(f"# List of Verification Tools\n\n")
        
        f.write("| Name | Website | Used for | Input formats | Status |\n")
        f.write("|------|---------|----------|---------------|--------|\n")
        
        for tool in sorted_items:
            page_link = create_individual_page(tool)
            # Aici am schimbat sintaxa de link pentru a nu strica tabelul
            row = f"| [{tool['title']}]({page_link}) | [link]({tool['url']}) | {tool['tags']} | {tool['input']} | {tool['status']} |\n"
            f.write(row)

    update_github_wiki()

if __name__ == '__main__':
    main()