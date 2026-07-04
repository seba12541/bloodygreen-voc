import sqlite3
import datetime

DB_NAME = "bloodygreen_voc.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name TEXT UNIQUE,
        absorbency_level TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        customer_name TEXT,
        rating INTEGER,
        review_text_es TEXT,
        review_text_en TEXT,
        submitted_date TEXT,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aspects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id INTEGER,
        aspect_name TEXT, -- Sizing, Absorbency, Comfort, Durability, Customer Service
        sentiment TEXT,   -- Positive, Neutral, Negative
        notes TEXT,
        FOREIGN KEY (review_id) REFERENCES reviews(id)
    )
    """)
    
    conn.commit()
    conn.close()

def populate_mock_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Insert products
    products = [
        ("Bikini Intenso", "Intenso (3-5 toallitas)"),
        ("High Waist Ultra Abundante", "Ultra Abundante (5-7 toallitas)"),
        ("Colaless Liviano", "Liviano (1-2 toallitas)"),
        ("Short Intenso", "Intenso (3-5 toallitas)"),
        ("Bikini Moderado", "Moderado (2-3 toallitas)"),
        ("High Waist Moderado", "Moderado (2-3 toallitas)")
    ]
    cursor.executemany("INSERT OR IGNORE INTO products (model_name, absorbency_level) VALUES (?, ?)", products)
    conn.commit()
    
    # Get product IDs
    cursor.execute("SELECT id, model_name FROM products")
    product_map = {name: id for id, name in cursor.fetchall()}
    
    now = (datetime.date.today() - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    
    # Insert Reviews and pre-extracted aspects (simulating the output of analyzer.py)
    
    # Review 1
    p_id = product_map["Bikini Intenso"]
    cursor.execute("""
    INSERT INTO reviews (product_id, customer_name, rating, review_text_es, review_text_en, submitted_date)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (p_id, "Camila Espinoza", 4, 
          "Me encantó el Bikini Intenso, absorbe súper bien y no se pasa nada de flujo. Lo único es que la talla corre un poco chica, sugiero pedir una talla más.",
          "I loved the Bikini Intenso, it absorbs super well and no flow leaks at all. The only thing is that the size runs a bit small, I suggest ordering one size up.",
          now))
    r_id = cursor.lastrowid
    cursor.executemany("INSERT INTO aspects (review_id, aspect_name, sentiment, notes) VALUES (?, ?, ?, ?)", [
        (r_id, "Absorbency", "Positive", "Absorbs super well, no leaks"),
        (r_id, "Sizing", "Negative", "Size runs a bit small, suggest ordering size up")
    ])
    
    # Review 2
    p_id = product_map["High Waist Ultra Abundante"]
    cursor.execute("""
    INSERT INTO reviews (product_id, customer_name, rating, review_text_es, review_text_en, submitted_date)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (p_id, "Francisca Torres", 5, 
          "El modelo High Waist Ultra Abundante es increíble para las noches. Súper cómodo, la tela de algodón orgánico se siente muy suave. Soportó mi flujo más pesado sin problemas.",
          "The High Waist Ultra Abundante model is incredible for nights. Super comfortable, the organic cotton fabric feels very soft. It handled my heaviest flow without problems.",
          now))
    r_id = cursor.lastrowid
    cursor.executemany("INSERT INTO aspects (review_id, aspect_name, sentiment, notes) VALUES (?, ?, ?, ?)", [
        (r_id, "Absorbency", "Positive", "Handled heaviest flow without issues"),
        (r_id, "Comfort", "Positive", "Super comfortable, organic cotton fabric feels soft")
    ])

    # Review 3
    p_id = product_map["Colaless Liviano"]
    cursor.execute("""
    INSERT INTO reviews (product_id, customer_name, rating, review_text_es, review_text_en, submitted_date)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (p_id, "Valentina Paz", 5, 
          "Compré el Colaless y es perfecto para los últimos días del ciclo. Muy discreto y cómodo, no se nota nada bajo la ropa. Sin fugas.",
          "I bought the Colaless and it is perfect for the last days of the cycle. Very discreet and comfortable, it doesn't show at all under clothes. No leaks.",
          now))
    r_id = cursor.lastrowid
    cursor.executemany("INSERT INTO aspects (review_id, aspect_name, sentiment, notes) VALUES (?, ?, ?, ?)", [
        (r_id, "Comfort", "Positive", "Discreet and comfortable, doesn't show"),
        (r_id, "Absorbency", "Positive", "No leaks")
    ])

    # Review 4
    p_id = product_map["Short Intenso"]
    cursor.execute("""
    INSERT INTO reviews (product_id, customer_name, rating, review_text_es, review_text_en, submitted_date)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (p_id, "Javiera Silva", 3, 
          "El Short Intenso es muy cómodo pero después de 5 lavadas la costura de los bordes se empezó a soltar un poco. Cumple con absorber pero la durabilidad podría ser mejor.",
          "The Short Intenso is very comfortable but after 5 washes the stitching on the edges started to come loose. It absorbs well but the durability could be better.",
          now))
    r_id = cursor.lastrowid
    cursor.executemany("INSERT INTO aspects (review_id, aspect_name, sentiment, notes) VALUES (?, ?, ?, ?)", [
        (r_id, "Comfort", "Positive", "Very comfortable"),
        (r_id, "Absorbency", "Positive", "Absorbs well"),
        (r_id, "Durability", "Negative", "Stitching came loose after 5 washes, needs better durability")
    ])

    # Review 5
    p_id = product_map["Bikini Moderado"]
    cursor.execute("""
    INSERT INTO reviews (product_id, customer_name, rating, review_text_es, review_text_en, submitted_date)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (p_id, "María José", 3, 
          "La talla del Bikini me quedó gigante, tuve que pedir un cambio. El servicio de atención al cliente fue rápido y amable para gestionar el envío. En absorción todo bien.",
          "The size of the Bikini was huge on me, I had to request an exchange. Customer service was fast and friendly in handling the shipping. Absorbency was all good.",
          now))
    r_id = cursor.lastrowid
    cursor.executemany("INSERT INTO aspects (review_id, aspect_name, sentiment, notes) VALUES (?, ?, ?, ?)", [
        (r_id, "Sizing", "Negative", "Size was too large, had to exchange"),
        (r_id, "Customer Service", "Positive", "Fast and friendly exchange management"),
        (r_id, "Absorbency", "Positive", "All good")
    ])

    # Review 6
    p_id = product_map["Bikini Intenso"]
    cursor.execute("""
    INSERT INTO reviews (product_id, customer_name, rating, review_text_es, review_text_en, submitted_date)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (p_id, "Isidora R.", 4, 
          "Al principio dudaba de que funcionara, pero resistió todo mi día de oficina sin problemas. Es un poco grueso pero te acostumbras rápido.",
          "At first I doubted it would work, but it held up through my whole office day without issues. It is a bit thick but you get used to it quickly.",
          now))
    r_id = cursor.lastrowid
    cursor.executemany("INSERT INTO aspects (review_id, aspect_name, sentiment, notes) VALUES (?, ?, ?, ?)", [
        (r_id, "Absorbency", "Positive", "Held up through office day without issues"),
        (r_id, "Comfort", "Neutral", "A bit thick but easy to get used to")
    ])

    # Review 7
    p_id = product_map["High Waist Moderado"]
    cursor.execute("""
    INSERT INTO reviews (product_id, customer_name, rating, review_text_es, review_text_en, submitted_date)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (p_id, "Sofía Balmaceda", 2, 
          "El modelo High Waist Moderado se me pasó a las 2 horas. Creo que para flujo moderado le falta más protección impermeable en la parte trasera. Una lástima.",
          "The High Waist Moderado model leaked after 2 hours. I think for moderate flow it lacks more waterproof protection in the back. A pity.",
          now))
    r_id = cursor.lastrowid
    cursor.executemany("INSERT INTO aspects (review_id, aspect_name, sentiment, notes) VALUES (?, ?, ?, ?)", [
        (r_id, "Absorbency", "Negative", "Leaked after 2 hours, lacks waterproof protection in the back")
    ])

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    populate_mock_data()
    print("Bloody Green database initialized and populated.")
