import os
import sqlite3
import json
from openai import OpenAI

DB_NAME = "bloodygreen_voc.db"

# Sample new reviews in Spanish that we want to analyze programmatically
NEW_REVIEWS_TO_PROCESS = [
    {
        "customer_name": "Antonia Ruiz",
        "model_name": "High Waist Ultra Abundante",
        "rating": 5,
        "review_text_es": "Es la mejor compra de mi vida. Tengo flujo ultra abundante y siempre andaba con miedo de mancharme. Estos calzones me cambiaron la vida, los usé por 10 horas seguidas y cero fugas. Además la tela de bambú es súper suave."
    },
    {
        "customer_name": "Constanza M.",
        "model_name": "Bikini Moderado",
        "rating": 3,
        "review_text_es": "El calzón absorbe bien y no tiene olores, pero las costuras de la pretina molestan un poco después de usarlo todo el día. Quizás una talla más grande habría sido más cómoda, la horma es algo ajustada."
    },
    {
        "customer_name": "Daniela Gomez",
        "model_name": "Colaless Liviano",
        "rating": 2,
        "review_text_es": "La tela de algodón orgánico es rica, pero el colaless se me pasó muy rápido en el primer día. Sé que es para flujo liviano, pero esperaba que aguantara más. La atención al cliente me ayudó a elegir otro modelo pero fue lenta la respuesta."
    }
]

def analyze_review_with_openai(review_text_es):
    """
    Uses OpenAI to:
    1. Translate the review to English.
    2. Extract structured aspects (Sizing, Absorbency, Comfort, Durability, Customer Service) 
       and their sentiment (Positive, Neutral, Negative) + a short note.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Warning: OPENAI_API_KEY not found. Cannot process review via API.")
        return None, []
        
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
    You are an expert data analyst working for the D2C brand Bloody Green (period underwear).
    Analyze this Spanish customer review:
    
    "{review_text_es}"
    
    Perform the following tasks:
    1. Translate the review text into natural, professional English.
    2. Extract granular aspects: Absorbency, Sizing, Comfort, Durability, or Customer Service.
       For each aspect mentioned, classify the sentiment as: "Positive", "Neutral", or "Negative".
       Provide a short English note explaining why.
    
    Your output must be strict JSON in the following format:
    {{
      "translation": "English translation here",
      "aspects": [
        {{"aspect_name": "Absorbency", "sentiment": "Positive", "notes": "No leaks after 10 hours"}},
        {{"aspect_name": "Comfort", "sentiment": "Positive", "notes": "Bamboo fabric is super soft"}}
      ]
    }}
    Do not output markdown code blocks or any other explanation, only raw JSON.
    """
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        response_text = completion.choices[0].message.content.strip()
        
        # Clean potential markdown wrapping
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()
            
        data = json.loads(response_text)
        return data.get("translation"), data.get("aspects", [])
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None, []

def run_analysis_pipeline():
    # Make sure DB is initialized
    import mock_reviews
    mock_reviews.init_db()
    mock_reviews.populate_mock_data()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("Running Bloody Green VoC analysis pipeline...")
    
    for item in NEW_REVIEWS_TO_PROCESS:
        customer_name = item["customer_name"]
        model_name = item["model_name"]
        rating = item["rating"]
        review_text_es = item["review_text_es"]
        
        # Check if review already processed
        cursor.execute("SELECT COUNT(*) FROM reviews WHERE review_text_es = ?", (review_text_es,))
        if cursor.fetchone()[0] > 0:
            print(f"Review from {customer_name} already processed. Skipping.")
            continue
            
        # Get product_id
        cursor.execute("SELECT id FROM products WHERE model_name = ?", (model_name,))
        result = cursor.fetchone()
        if not result:
            print(f"Product model '{model_name}' not found. Skipping.")
            continue
        product_id = result[0]
        
        print(f"\nAnalyzing review from {customer_name} ({model_name})...")
        
        # Call API
        translation, aspects = analyze_review_with_openai(review_text_es)
        
        if not translation:
            print("API query failed or returned empty. Make sure your OPENAI_API_KEY is configured.")
            continue
            
        # Insert review
        today = datetime.date.today().strftime("%Y-%m-%d")
        cursor.execute("""
        INSERT INTO reviews (product_id, customer_name, rating, review_text_es, review_text_en, submitted_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (product_id, customer_name, rating, review_text_es, translation, today))
        review_id = cursor.lastrowid
        
        # Insert aspects
        for asp in aspects:
            cursor.execute("""
            INSERT INTO aspects (review_id, aspect_name, sentiment, notes)
            VALUES (?, ?, ?, ?)
            """, (review_id, asp["aspect_name"], asp["sentiment"], asp["notes"]))
            
        conn.commit()
        print(f"Successfully processed review and stored {len(aspects)} aspects.")
        
    conn.close()
    print("\nPipeline execution complete.")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it in your terminal:")
        print("export OPENAI_API_KEY='your-key-here'")
    else:
        run_analysis_pipeline()
