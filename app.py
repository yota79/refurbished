import streamlit as st
import subprocess
import json
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Apple Refurbed Search", layout="wide")
st.title("🔍 Apple Refurbed Multi-Store Search")

st.sidebar.header("Search Filters")

store_options = ['it', 'de', 'at', 'fr', 'es', 'nl', 'ie', 'uk', 'be', 'ch', 'se', 'dk', 'fi', 'pl', 'pt']
selected_stores = st.sidebar.multiselect("Select European Stores", store_options, default=['it', 'de', 'at'])
query = st.sidebar.text_input("What are you looking for?", value="macs")
min_saving = st.sidebar.number_input("Minimum savings (€)", min_value=0, value=300, step=50)

# Nuovo filtro per il quantitativo di RAM
ram_filter_options = ['All', '8 GB', '16 GB', '18 GB', '24 GB', '32 GB', '36 GB', '48 GB', '64 GB', '96 GB', '128 GB']
min_ram_selected = st.sidebar.selectbox("Minimum RAM Required", ram_filter_options, index=0)

def fetch_specs_from_url(url):
    ram = "N/A"
    storage = "N/A"
    
    if not url:
        return ram, storage
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=4)
        if response.status_code != 200:
            return ram, storage
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        important_text = " ".join([
            soup.title.get_text() if soup.title else "",
            " ".join([meta.get('content', '') for meta in soup.find_all('meta')]),
            soup.find('body').get_text() if soup.find('body') else ""
        ])
        
        text_clean = important_text.upper().replace('‑', '-').replace(' ', ' ').strip()
        
        # 1. Parsing mirato per le schede tecniche degli store Apple (es. "MEMORIA. 16GB DI MEMORIA UNIFICATA" o "SSD DA 256GB")
        tech_ram = re.search(r'(?:MEMORIA\.)\s*(\d+)\s*(?:GB|GO)', text_clean)
        if tech_ram:
            ram = f"{tech_ram.group(1)} GB"
            
        tech_storage = re.search(r'(?:ARCHIVIAZIONE\.|SSD\s+DA)\s*(\d+)\s*(?:GB|GO|TB|TO)', text_clean)
        if tech_storage:
            unit = "TB" if "TB" in tech_storage.group(0) or "TO" in tech_storage.group(0) else "GB"
            storage = f"{tech_storage.group(1)} {unit}"

        # 2. Pattern espliciti classici (se il parsing mirato fallisce)
        if ram == "N/A":
            ram_patterns = [
                r'(\d+)\s*(?:GB|GO)\s*(?:DI\s+MEMORIA|MEMORIA|UNIFIED|RAM|ZWISCHENSPEICHER|MÉMOIRE)',
                r'(?:MEMORIA\s+UNIFICATA|UNIFIED\s+MEMORY|ARBEITSSPEICHER|MÉMOIRE\s+UNIFIÉE)\s*(?:DA|VON|DE)?\s*(\d+)\s*(?:GB|GO)'
            ]
            for pattern in ram_patterns:
                match = re.search(pattern, text_clean)
                if match:
                    ram = f"{match.group(1)} GB"
                    break
                    
        if storage == "N/A":
            storage_patterns = [
                r'(\d+)\s*(?:GB|GO|TB|TO)\s*(?:SSD|UNITÀ\s+FLASH|FLASH|SPEICHER|STOCKAGE|DISCO|KAPACITET)',
                r'(?:SSD|UNITÀ\s+FLASH|FLASH-SPEICHER|STOCKAGE\s+SSD)\s*(?:DA|VON|DE)?\s*(\d+)\s*(?:GB|GO|TB|TO)'
            ]
            for pattern in storage_patterns:
                match = re.search(pattern, text_clean)
                if match:
                    unit = "TB" if "TB" in match.group(0) or "TO" in match.group(0) else "GB"
                    storage = f"{match.group(1)} {unit}"
                    break

        # 3. Fallback sequenziale avanzato per liste puntate (es. iMac M4)
        if ram == "N/A" or storage == "N/A":
            all_memories = re.findall(r'\b(\d+)\s*(GB|GO|TB|TO)\b', text_clean)
            
            valid_specs = []
            for num_str, unit in all_memories:
                num = int(num_str)
                if num in [8, 16, 18, 24, 32, 36, 48, 64, 96, 128, 256, 512, 1, 2, 4, 8]:
                    valid_specs.append((num, unit))
            
            if valid_specs:
                tb_specs = [spec for spec in valid_specs if spec[1] in ['TB', 'TO']]
                gb_specs = [spec for spec in valid_specs if spec[1] in ['GB', 'GO']]
                
                if tb_specs and ram == "N/A":
                    storage = f"{tb_specs[0][0]} TB"
                    if gb_specs:
                        ram = f"{gb_specs[0][0]} GB"
                elif len(gb_specs) >= 2:
                    if ram == "N/A":
                        ram = f"{gb_specs[0][0]} GB"
                    if storage == "N/A":
                        storage = f"{gb_specs[1][0]} GB"
                elif len(gb_specs) == 1 and ram == "N/A":
                    ram = f"{gb_specs[0][0]} GB"

    except:
        pass
        
    return ram, storage

def process_item(item):
    name_key = next((k for k in item.keys() if k.lower() in ['name', 'title']), None)
    product_name = item.get(name_key, "") if name_key else ""
    
    link_key = next((k for k in item.keys() if k.lower() in ['link', 'url']), 'url')
    product_url = item.get(link_key, "")
    
    ram, storage = fetch_specs_from_url(product_url)
    
    store_key = next((k for k in item.keys() if k.lower() == 'store'), 'store')
    price_key = next((k for k in item.keys() if k.lower() == 'price'), 'price')
    prev_price_key = next((k for k in item.keys() if k.lower() in ['previous price', 'previous_price']), 'previous_price')
    saving_key = next((k for k in item.keys() if k.lower() == 'saving'), 'saving')
    
    return {
        "Country": str(item.get(store_key, "??")).upper(),
        "RAM": ram,
        "Storage": storage,
        "Name": product_name,
        "Price": item.get(price_key),
        "Previous Price": item.get(prev_price_key),
        "Saving": item.get(saving_key),
        "Link": product_url
    }

if st.sidebar.button("Launch Search"):
    if not selected_stores or not query:
        st.error("Please select at least one store and enter a search query!")
    else:
        stores_str = ",".join(selected_stores)
        st.info(f"Searching for '{query}' in stores: {stores_str}...")
        
        cmd = ["rfrb", stores_str, query, f"--min-saving={min_saving}", "--format", "json"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            if data:
                st.info("🔄 Extracting deep technical specifications from Apple Stores... Please wait...")
                
                enriched_data = []
                with ThreadPoolExecutor(max_workers=10) as executor:
                    enriched_data = list(executor.map(process_item, data))
                
                # Applicazione del filtro RAM
                if min_ram_selected != 'All':
                    try:
                        min_ram_val = int(re.search(r'\d+', min_ram_selected).group())
                        filtered_data = []
                        for item in enriched_data:
                            if item["RAM"] != "N/A":
                                item_ram_val = int(re.search(r'\d+', item["RAM"]).group())
                                if item_ram_val >= min_ram_val:
                                    filtered_data.append(item)
                            else:
                                # Teniamo i N/A per sicurezza, oppure rimuovili se preferisci una pulizia totale
                                filtered_data.append(item)
                        enriched_data = filtered_data
                    except Exception as e:
                        pass
                
                if enriched_data:
                    st.success(f"Found {len(enriched_data)} products matching your filters!")
                    st.dataframe(enriched_data, use_container_width=True)
                else:
                    st.warning("No products match the selected RAM criteria.")
            else:
                st.warning("No products found with the selected filters.")
                
        except subprocess.CalledProcessError as e:
            st.error(f"Error during script execution: {e.stderr}")
        except Exception as e:
            st.error(f"Generic error: {str(e)}")
