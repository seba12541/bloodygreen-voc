import urllib.request
import json
import re
import sqlite3
import datetime
import time

DB_NAME = "bloodygreen_voc.db"

# NLP keywords for aspect extraction (Spanish)
ASPECT_KEYWORDS = {
    "Sizing": ["talla", "chico", "chica", "grande", "horma", "aprieta", "ajustado", "ajusta", "pequeño", "medida", "medidas", "tabla"],
    "Absorbency": ["absorbe", "absorcion", "absorción", "fuga", "fugas", "pasa", "paso", "pasó", "gotas", "gotea", "seco", "humedo", "humedad", "aguantar", "aguanta", "proteccion", "protección", "traspaso", "traspasó"],
    "Comfort": ["comodo", "cómodo", "comodidad", "suave", "tela", "algodon", "algodón", "bambu", "bambú", "molesta", "molesto", "pica", "grueso"],
    "Durability": ["lavado", "lavar", "costura", "costuras", "lavadas", "calidad", "rompe", "rompio", "rompió", "durabilidad", "durar", "duró"],
    "Customer Service": ["atencion", "atención", "cliente", "cambio", "cambiar", "envio", "envío", "despacho", "lento", "lenta", "rapido", "rápido", "amable"]
}

def extract_aspects(text, rating):
    text_lower = text.lower()
    aspects = []
    
    for aspect, keywords in ASPECT_KEYWORDS.items():
        matched = False
        for kw in keywords:
            if kw in text_lower:
                matched = True
                break
        
        if matched:
            # Determine sentiment based on rating and context keywords
            if rating >= 4:
                sentiment = "Positive"
                # Exception: Sizing issues often present even with 4 stars
                if aspect == "Sizing" and any(k in text_lower for k in ["chico", "aprieta", "ajustado"]):
                    sentiment = "Negative"
            elif rating <= 2:
                sentiment = "Negative"
            else:
                sentiment = "Neutral"
                
            # Generate a brief explanation note
            note = f"Extracted via keyword matching. Rating: {rating} stars."
            aspects.append({
                "aspect_name": aspect,
                "sentiment": sentiment,
                "notes": note
            })
            
    # Default aspect if no keywords match
    if not aspects:
        aspects.append({
            "aspect_name": "General Feedback",
            "sentiment": "Positive" if rating >= 4 else ("Negative" if rating <= 2 else "Neutral"),
            "notes": "General rating feedback."
        })
        
    return aspects

def run_scraper():
    import mock_reviews
    mock_reviews.init_db()
    
    print("Fetching product handles from bloodygreen.cl...")
    products_url = "https://bloodygreen.cl/products.json?limit=100"
    req = urllib.request.Request(
        products_url,
        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    )

    try:
        with urllib.request.urlopen(req) as response:
            products_data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching products.json: {e}")
        return

    products_list = products_data.get("products", [])
    print(f"Found {len(products_list)} products.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Store products
    for p in products_list:
        model_name = p["title"]
        # Determine a mock absorbency category based on title keywords
        title_lower = model_name.lower()
        if "ultra" in title_lower or "abundante" in title_lower:
            abs_level = "Ultra Abundante (5-7 toallitas)"
        elif "intenso" in title_lower:
            abs_level = "Intenso (3-5 toallitas)"
        elif "moderado" in title_lower or "sport" in title_lower:
            abs_level = "Moderado (2-3 toallitas)"
        elif "liviano" in title_lower or "colaless" in title_lower:
            abs_level = "Liviano (1-2 toallitas)"
        else:
            abs_level = "Standard"
            
        cursor.execute("INSERT OR IGNORE INTO products (model_name, absorbency_level) VALUES (?, ?)", (model_name, abs_level))
    conn.commit()

    # Get product mapping
    cursor.execute("SELECT id, model_name FROM products")
    product_map = {name: id for id, name in cursor.fetchall()}

    now_str = datetime.date.today().strftime("%Y-%m-%d")
    total_reviews_inserted = 0

    print("\nStarting review scraping and classification...")
    for p in products_list:
        handle = p["handle"]
        model_name = p["title"]
        product_id = product_map.get(model_name)
        
        if not product_id:
            continue

        url = f"https://bloodygreen.cl/products/{handle}"
        product_req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        )
        
        try:
            with urllib.request.urlopen(product_req) as response:
                html = response.read().decode('utf-8')
            
            # Fetch Loox inline reviews from HTML
            # HTML format: <div class="review"><div class="name">Name</div><div class="review_text">Text</div></div>
            reviews = re.findall(
                r'<div class="review"><div class="name">([^<]*)</div><div class="review_text">([^<]*)</div></div>', 
                html
            )
            
            if not reviews:
                # Fallback regex
                reviews = re.findall(r'<div class="review">.*?<div class="name">([^<]*)</div>.*?<div class="review_text">([^<]*)</div>', html, re.DOTALL)
            
            if reviews:
                print(f"Scraped {len(reviews)} reviews for '{model_name}'")
                
                # Check for product overall rating as reference, or default to 5
                # Loox elements contain rating details, e.g. data-rating="4.8" or data-raters="45"
                rating_match = re.search(r'data-rating="([0-9\.]+)"', html)
                overall_rating = float(rating_match.group(1)) if rating_match else 5.0
                rating_int = int(round(overall_rating))
                
                for name, text in reviews:
                    name = name.strip()
                    text = text.strip()
                    
                    if not text:
                        continue
                        
                    # Skip duplicate reviews
                    cursor.execute("SELECT COUNT(*) FROM reviews WHERE review_text_es = ?", (text,))
                    if cursor.fetchone()[0] > 0:
                        continue
                        
                    # We approximate rating: if customer review text has negative words, we give it a 3, else overall_rating
                    cust_rating = rating_int
                    text_lower = text.lower()
                    if any(w in text_lower for w in ["malo", "mala", "fuga", "pasa", "aprieta", "rompio", "lento"]):
                        cust_rating = max(3, rating_int - 2)
                    
                    # Insert review (using Spanish text, and simple translated placeholder for English)
                    cursor.execute("""
                    INSERT INTO reviews (product_id, customer_name, rating, review_text_es, review_text_en, submitted_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (product_id, name, cust_rating, text, "[Translation not run - Spanish version available]", now_str))
                    review_id = cursor.lastrowid
                    
                    # Extract aspects and insert
                    aspects = extract_aspects(text, cust_rating)
                    for asp in aspects:
                        cursor.execute("""
                        INSERT INTO aspects (review_id, aspect_name, sentiment, notes)
                        VALUES (?, ?, ?, ?)
                        """, (review_id, asp["aspect_name"], asp["sentiment"], asp["notes"]))
                        
                    total_reviews_inserted += 1
                conn.commit()
        except Exception as e:
            print(f"Error scraping '{model_name}' ({handle}): {e}")
            
        # Polite delay to prevent Shopify/Cloudflare rate-limiting (HTTP 429)
        time.sleep(2.0)

    conn.close()
    print(f"\nScraping finished. Populated database with {total_reviews_inserted} real customer reviews.")

if __name__ == "__main__":
    run_scraper()
