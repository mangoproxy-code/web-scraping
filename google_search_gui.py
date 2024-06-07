import requests
from bs4 import BeautifulSoup
import random
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from config import PROXY_URL
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    # Add more User-Agent strings if needed
]

def fetch_page(query, start):
    headers = {
        'User-Agent': random.choice(user_agents)
    }
    proxies = {
        'http': PROXY_URL,
        'https': PROXY_URL,
    }
    
    url = f'https://www.google.com/search?q={query}&start={start}'
    
    for _ in range(3):  # Retry up to 3 times
        try:
            response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                print(f'Rate limit exceeded at start={start}. Retrying...')
                time.sleep(random.uniform(10, 20))
        except requests.exceptions.SSLError as e:
            print(f'SSLError for start={start}: {e}. Retrying...')
            time.sleep(random.uniform(5, 10))
        except requests.exceptions.RequestException as e:
            print(f'RequestException for start={start}: {e}. Retrying...')
            time.sleep(random.uniform(5, 10))
    return None

def parse_results(html):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for g in soup.find_all('div', class_='tF2Cxc'):
        title = g.find('h3').text if g.find('h3') else 'No title'
        link = g.find('a')['href'] if g.find('a') else 'No link'
        description = 'No description'
        
        # Try multiple ways to find the description
        description_element = g.find('span', class_='aCOpRe') or \
                             g.find('div', class_='IsZvec') or \
                             g.find('div', class_='VwiC3b yXK7lf lVm3ye r025kc hJNv6b Hdw6tb') or \
                             g.find('div', class_='VwiC3b yXK7lf MUxGbd yDYNvb lyLwlc') or \
                             g.find('div', class_='VwiC3b MUxGbd yDYNvb lyLwlc')
                             
        if description_element:
            description = description_element.text
        
        results.append({
            'title': title,
            'link': link,
            'description': description
        })
    return results

def google_search(query, num_results):
    results = []
    start = 0
    
    while len(results) < num_results:
        num_pages = (num_results - len(results) + 9) // 10  # Calculate the remaining pages needed
        
        with ThreadPoolExecutor(max_workers=5) as executor:  # Reduce the number of threads
            future_to_start = {executor.submit(fetch_page, query, start + i * 10): start + i * 10 for i in range(num_pages)}
            
            for future in as_completed(future_to_start):
                start_page = future_to_start[future]
                html = future.result()
                if html:
                    page_results = parse_results(html)
                    results.extend(page_results)
                    if len(results) >= num_results:
                        break
                else:
                    print(f'Failed to retrieve results for start={start_page}. Retrying...')
        
        start += num_pages * 10  # Move to the next set of pages if needed
    
    return results[:num_results]

def save_to_csv(data, query, num_results):
    sanitized_query = re.sub(r'\W+', '_', query)  # Replace non-alphanumeric characters with underscores
    filename = f"results/results-{sanitized_query}-{num_results}.csv"
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)

def search_and_save():
    query = query_entry.get()
    num_results = int(num_results_entry.get())
    results = google_search(query, num_results)
    if results:
        save_to_csv(results, query, num_results)
        messagebox.showinfo("Success", f"Results saved to results/results-{re.sub(r'\W+', '_', query)}-{num_results}.csv")
    else:
        messagebox.showerror("Error", "No results found or an error occurred.")

# GUI setup
root = tk.Tk()
root.title("Google Search Scraper")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

query_label = ttk.Label(frame, text="Search Query:")
query_label.grid(row=0, column=0, sticky=tk.W)
query_entry = ttk.Entry(frame, width=50)
query_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))

num_results_label = ttk.Label(frame, text="Number of Results:")
num_results_label.grid(row=1, column=0, sticky=tk.W)
num_results_entry = ttk.Entry(frame, width=10)
num_results_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))

search_button = ttk.Button(frame, text="Search and Save", command=search_and_save)
search_button.grid(row=2, column=0, columnspan=2)

# Make the GUI responsive
for child in frame.winfo_children():
    child.grid_configure(padx=5, pady=5)

root.mainloop()
