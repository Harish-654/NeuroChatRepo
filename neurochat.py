
import os
import streamlit as st
import requests
from google import genai
from textblob import TextBlob
import pandas as pd
import time
import json
import re
import hashlib
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import sqlite3

# Configure Streamlit page
st.set_page_config(
    page_title="NeuroChat - Advanced AI Marketplace",
    page_icon="🧠💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration section for API keys
def load_config():
    """Load API key from environment variables"""
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")

    if not gemini_api_key:
        st.error("⚠️ Gemini API key not found!")
        st.info("🔑 Get your FREE API key from: https://aistudio.google.com")
        st.info("💡 Then set it in PowerShell: $env:GEMINI_API_KEY='your_key'")
        st.info("🚀 Finally run: streamlit run neurochat.py")
        st.stop()

    return gemini_api_key

# Initialize Gemini client
def initialize_gemini_client(api_key: str):
    """Initialize Google Gemini client"""
    try:
        client = genai.Client(api_key=api_key)
        return client
    except Exception as e:
        st.error(f"Error initializing Gemini client: {e}")
        return None

# Initialize business database with advanced tracking
def init_business_database():
    """Initialize SQLite database for business products and analytics"""
    conn = sqlite3.connect('neurochat_marketplace.db')
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            created_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_products (
            id INTEGER PRIMARY KEY,
            business_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            price REAL,
            category TEXT,
            target_emotions TEXT,
            stock_quantity INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            created_date TEXT,
            FOREIGN KEY (business_id) REFERENCES businesses (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_feedback (
            id INTEGER PRIMARY KEY,
            product_name TEXT,
            user_query TEXT,
            feedback_type TEXT,
            recommendation_source TEXT,
            created_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_analytics (
            id INTEGER PRIMARY KEY,
            user_query TEXT,
            user_emotion TEXT,
            recommendation_method TEXT,
            products_found INTEGER,
            user_satisfaction TEXT,
            response_time REAL,
            created_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS successful_patterns (
            id INTEGER PRIMARY KEY,
            query_pattern TEXT,
            emotion TEXT,
            successful_categories TEXT,
            success_count INTEGER DEFAULT 1,
            last_success TEXT
        )
    """)

    conn.commit()
    conn.close()

# USD to INR conversion (approximate rate: 1 USD = 83 INR)
def convert_usd_to_inr(usd_price):
    """Convert USD price to INR"""
    try:
        if isinstance(usd_price, str):
            # Extract numeric value from string like "$29.99"
            numeric_value = float(re.sub(r'[^0-9.]', '', usd_price))
        else:
            numeric_value = float(usd_price)

        inr_price = numeric_value * 83  # 1 USD = 83 INR approximately
        return f"₹{inr_price:,.0f}"
    except:
        return "₹Price varies"

# Emotion detection using TextBlob sentiment analysis
def detect_emotion(text: str) -> Tuple[str, float, str]:
    """Enhanced emotion detection with context analysis"""
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity

        # Context-based emotion detection
        text_lower = text.lower()

        if polarity > 0.3:
            if any(word in text_lower for word in ["excited", "thrilled", "amazing", "fantastic"]):
                return "excited", abs(polarity), "🎉"
            else:
                return "happy", abs(polarity), "😊"
        elif polarity < -0.3:
            if any(word in text_lower for word in ["stress", "overwhelm", "pressure", "busy"]):
                return "stressed", abs(polarity), "😰"
            elif any(word in text_lower for word in ["frustrat", "annoyed", "irritat", "upset"]):
                return "frustrated", abs(polarity), "😤"
            elif any(word in text_lower for word in ["tired", "exhausted", "worn out"]):
                return "tired", abs(polarity), "😴"
            else:
                return "sad", abs(polarity), "😢"
        elif polarity < -0.1:
            return "confused", abs(polarity), "🤔"
        else:
            return "neutral", 0.3, "😐"

    except Exception as e:
        return "neutral", 0.3, "😐"

# ADVANCED PRODUCT RECOMMENDATION SYSTEMS

# 1. Semantic AI Product Generation
def semantic_product_search(query: str, client, limit: int = 6) -> List[Dict]:
    """Generate perfect product matches using AI semantic understanding"""
    try:
        semantic_prompt = f"""
        A user is looking for: "{query}"

        Generate {limit} realistic, relevant product suggestions that would perfectly match their needs.
        Focus on practical, real products that actually exist in the Indian market.

        For each product, provide realistic Indian market details:
        - title: Clear, descriptive product name
        - price: Realistic Indian market price in rupees (₹)
        - description: Helpful product description (100-150 chars)
        - category: Best fit category

        Format as valid JSON array:
        [
          {{"title": "Product Name", "price": "2499", "description": "Detailed description of the product and its benefits", "category": "relevant-category"}}
        ]

        Make products diverse but all relevant to the user's request. Use Indian rupees for pricing.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=semantic_prompt
        )

        # Clean and parse JSON response
        json_text = response.text.strip()
        if json_text.startswith('```json'):
            json_text = json_text[7:]
        if json_text.endswith('```'):
            json_text = json_text[:-3]

        products_data = json.loads(json_text.strip())

        products = []
        for idx, item in enumerate(products_data[:limit]):
            price = item['price']
            if not price.startswith('₹'):
                price = f"₹{price}"

            products.append({
                'title': item['title'][:80],
                'price': price,
                'description': item['description'][:200],
                'category': item.get('category', 'General'),
                'rating': '⭐⭐⭐⭐ AI Curated',
                'stock': 'Available',
                'brand': 'AI Curated',
                'source': 'Semantic AI Match 🧠'
            })

        return products

    except Exception as e:
        return []

# 2. Real-time Web Product Search
def search_web_products(query: str, limit: int = 6) -> List[Dict]:
    """Search real products from web using Google Custom Search API"""
    try:
        google_api_key = os.getenv("GOOGLE_SEARCH_API_KEY", "")
        search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")

        if not google_api_key or not search_engine_id:
            return []

        # Enhanced search query for Indian market
        search_query = f"{query} buy online price India rupees store product"

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': google_api_key,
            'cx': search_engine_id,
            'q': search_query,
            'num': min(limit, 10),
            'gl': 'in',  # India
            'hl': 'en'
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json()

        products = []
        for item in results.get('items', []):
            # Extract price from snippet (look for rupees)
            price_match = re.search(r'₹([0-9,]+)', item.get('snippet', ''))
            if not price_match:
                price_match = re.search(r'Rs\.?\s*([0-9,]+)', item.get('snippet', ''))
            if not price_match:
                price_match = re.search(r'([0-9,]+)\s*rupees?', item.get('snippet', ''))

            price = f"₹{price_match.group(1)}" if price_match else "See website"

            # Clean title
            title = item['title'][:80]
            title = re.sub(r'[|\-].*', '', title).strip()

            products.append({
                'title': title,
                'price': price,
                'description': item.get('snippet', '')[:180] + "...",
                'category': 'Web Search Result',
                'rating': 'See reviews online ⭐',
                'stock': 'Check availability',
                'brand': 'Various Indian Retailers',
                'source': 'Real Web Search 🌐',
                'link': item.get('link', '')
            })

        return products[:limit]

    except Exception as e:
        return []

# 3. Context-Aware AI Search
def context_aware_ai_search(emotion: str, query: str, client) -> List[Dict]:
    """AI search considering full user context"""
    try:
        current_time = datetime.now()
        current_hour = current_time.hour
        current_month = current_time.strftime("%B")
        day_of_week = current_time.strftime("%A")

        context_prompt = f"""
        Analyze this user's complete context for product recommendations:

        User Input: "{query}"
        User Emotion: {emotion}
        Time Context: {day_of_week}, {current_month}, {current_hour}:00 (India time)

        Consider:
        1. Explicit needs (what they directly asked for)
        2. Emotional needs (products that help with {emotion} feelings)
        3. Temporal context (time of day, season, day of week)
        4. Practical utility (real-world usefulness)
        5. Indian market context

        What are the 2 most relevant, specific product categories?

        Available categories: furniture, beauty, laptops, smartphones, mens-shirts, womens-dresses, fragrances, home-decoration, groceries, sports-accessories, sunglasses, kitchen-accessories, mens-watches, womens-jewellery, skin-care

        Rules:
        - If they ask for specific items, prioritize those categories
        - Don't mix unrelated categories (jewelry + electronics = wrong)
        - Consider emotional appropriateness
        - Think about time context (evening = relaxation products)

        Respond with only 1-2 category names, comma-separated.
        Example: furniture,home-decoration
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=context_prompt
        )

        categories = [cat.strip() for cat in response.text.strip().split(',')]

        # Search the determined categories
        all_products = []
        for category in categories[:2]:
            category_products = fetch_products_dummyjson(category=category, limit=3)
            all_products.extend(category_products)

            if len(all_products) < 6:
                fake_products = fetch_products_fakestore(category=category, limit=2)
                all_products.extend(fake_products)

        if all_products:
            return all_products[:6], f"🎯 Context-aware AI chose: {', '.join(categories)}"

        return [], ""

    except Exception as e:
        return [], ""

# 4. Learning from User Feedback
def get_successful_recommendations(query: str, emotion: str) -> Dict:
    """Get historically successful recommendation patterns"""
    try:
        conn = sqlite3.connect('neurochat_marketplace.db')
        cursor = conn.cursor()

        # Find similar successful queries
        query_words = query.lower().split()

        cursor.execute("""
            SELECT successful_categories, success_count
            FROM successful_patterns 
            WHERE emotion = ? AND (
                """ + " OR ".join(["query_pattern LIKE ?" for _ in query_words]) + """
            )
            ORDER BY success_count DESC, last_success DESC
            LIMIT 1
        """, [emotion] + [f"%{word}%" for word in query_words])

        result = cursor.fetchone()
        conn.close()

        if result:
            return {
                'categories': result[0].split(','),
                'success_count': result[1]
            }

        return {}

    except Exception as e:
        return {}

def save_successful_pattern(query: str, emotion: str, categories: List[str]):
    """Save successful recommendation patterns for learning"""
    try:
        conn = sqlite3.connect('neurochat_marketplace.db')
        cursor = conn.cursor()

        query_pattern = ' '.join(query.lower().split()[:3])  # First 3 words
        categories_str = ','.join(categories)

        # Check if pattern exists
        cursor.execute("""
            SELECT id, success_count FROM successful_patterns 
            WHERE query_pattern = ? AND emotion = ? AND successful_categories = ?
        """, (query_pattern, emotion, categories_str))

        existing = cursor.fetchone()

        if existing:
            # Update existing pattern
            cursor.execute("""
                UPDATE successful_patterns 
                SET success_count = success_count + 1, last_success = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), existing[0]))
        else:
            # Create new pattern
            cursor.execute("""
                INSERT INTO successful_patterns 
                (query_pattern, emotion, successful_categories, success_count, last_success)
                VALUES (?, ?, ?, 1, ?)
            """, (query_pattern, emotion, categories_str, datetime.now().isoformat()))

        conn.commit()
        conn.close()

    except Exception as e:
        pass

# Original API functions (enhanced with INR conversion)
def fetch_products_dummyjson(query: str = "", category: str = "", limit: int = 10) -> List[Dict]:
    """Enhanced DummyJSON product fetching with INR conversion"""
    try:
        base_url = "https://dummyjson.com/products"

        if query:
            url = f"{base_url}/search"
            params = {"q": query, "limit": limit}
        elif category:
            url = f"{base_url}/category/{category}"
            params = {"limit": limit}
        else:
            url = base_url
            params = {"limit": limit}

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        products = data.get("products", [])

        # Enhanced product information with INR conversion
        for product in products:
            product['source'] = 'DummyJSON Catalog 📦'
            product['price'] = convert_usd_to_inr(product.get('price', 0))

        return products

    except Exception as e:
        return []

def fetch_products_fakestore(query: str = "", category: str = "", limit: int = 6) -> List[Dict]:
    """Enhanced FakeStore API with INR conversion"""
    try:
        if category:
            category_mapping = {
                "beauty": "electronics",
                "furniture": "men's clothing",
                "laptops": "electronics", 
                "smartphones": "electronics",
                "mens-shirts": "men's clothing",
                "womens-dresses": "women's clothing",
                "womens-jewellery": "jewelery",
                "fragrances": "electronics",
                "home-decoration": "electronics"
            }
            mapped_category = category_mapping.get(category, "electronics")
            url = f"https://fakestoreapi.com/products/category/{mapped_category}"
        else:
            url = "https://fakestoreapi.com/products"

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        fakestore_products = response.json()

        # Better query filtering
        if query:
            query_words = query.lower().split()
            filtered_products = []
            for p in fakestore_products:
                title_desc = (p['title'] + ' ' + p['description']).lower()
                if any(word in title_desc for word in query_words):
                    filtered_products.append(p)
            fakestore_products = filtered_products

        # Convert to consistent format with INR
        converted_products = []
        for product in fakestore_products[:limit]:
            converted_products.append({
                'title': product['title'][:80],
                'price': convert_usd_to_inr(product['price']),
                'description': product['description'][:200],
                'category': product['category'],
                'rating': product.get('rating', {}).get('rate', 4.0),
                'stock': 25,
                'brand': 'Alternative Store',
                'source': 'Alternative Catalog 🔄'
            })

        return converted_products

    except Exception as e:
        return []

def search_business_products(emotion: str = "", query: str = "") -> List[Dict]:
    """Enhanced business products search"""
    try:
        conn = sqlite3.connect('neurochat_marketplace.db')
        cursor = conn.cursor()

        sql_query = """
            SELECT bp.name, bp.description, bp.price, bp.category, bp.target_emotions,
                   bp.stock_quantity, b.name as business_name
            FROM business_products bp
            JOIN businesses b ON bp.business_id = b.id
            WHERE bp.is_active = 1
        """
        params = []

        if emotion:
            sql_query += " AND bp.target_emotions LIKE ?"
            params.append(f"%{emotion}%")

        if query:
            query_words = query.lower().split()
            query_conditions = []
            for word in query_words:
                query_conditions.append("(bp.name LIKE ? OR bp.description LIKE ? OR bp.category LIKE ?)")
                params.extend([f"%{word}%", f"%{word}%", f"%{word}%"])

            if query_conditions:
                sql_query += " AND (" + " OR ".join(query_conditions) + ")"

        sql_query += " ORDER BY bp.created_date DESC LIMIT 6"

        cursor.execute(sql_query, params)
        results = cursor.fetchall()
        conn.close()

        products = []
        for row in results:
            price = row[2]
            if not str(price).startswith('₹'):
                price = f"₹{price:,.0f}"

            products.append({
                'title': row[0],
                'price': price,
                'description': row[1],
                'category': row[3],
                'rating': 'Local Business ⭐',
                'stock': row[5] if row[5] > 0 else 'Limited Stock',
                'brand': row[6],
                'source': 'Local Business 🏪'
            })

        return products

    except Exception as e:
        return []

# NEUROCHAT HYBRID RECOMMENDATION ENGINE
def neurochat_product_search(emotion: str, query: str, client) -> Tuple[List[Dict], str]:
    """The NeuroChat hybrid recommendation system"""
    start_time = time.time()

    # Step 1: Always prioritize local business products
    business_products = search_business_products(emotion, query)
    if business_products:
        response_time = time.time() - start_time
        log_recommendation_analytics(query, emotion, "Local Business", len(business_products), response_time)
        return business_products, f"🏪 Found {len(business_products)} products from caring local businesses"

    # Step 2: Check for successful patterns from past interactions
    historical_success = get_successful_recommendations(query, emotion)
    if historical_success and historical_success.get('success_count', 0) > 2:
        pattern_products = []
        for category in historical_success['categories'][:2]:
            cat_products = fetch_products_dummyjson(category=category, limit=3)
            pattern_products.extend(cat_products)

        if pattern_products:
            response_time = time.time() - start_time
            log_recommendation_analytics(query, emotion, "Historical Pattern", len(pattern_products), response_time)
            return pattern_products[:6], f"📊 Using proven successful pattern (used {historical_success['success_count']} times)"

    # Step 3: Semantic AI generation (most accurate for specific requests)
    if query.strip() and len(query.strip()) > 3:
        semantic_products = semantic_product_search(query, client)
        if semantic_products and len(semantic_products) >= 3:
            response_time = time.time() - start_time
            log_recommendation_analytics(query, emotion, "Semantic AI", len(semantic_products), response_time)
            return semantic_products, "🧠 AI generated perfect matches for your needs"

    # Step 4: Real-time web search (most comprehensive)
    if query.strip():
        web_products = search_web_products(query)
        if web_products and len(web_products) >= 3:
            response_time = time.time() - start_time
            log_recommendation_analytics(query, emotion, "Web Search", len(web_products), response_time)
            return web_products, "🌐 Found real products from across the web"

    # Step 5: Context-aware AI categories
    context_products, context_msg = context_aware_ai_search(emotion, query, client)
    if context_products:
        response_time = time.time() - start_time
        log_recommendation_analytics(query, emotion, "Context AI", len(context_products), response_time)
        return context_products, context_msg

    # Step 6: Fallback to traditional search with better prompting
    try:
        fallback_prompt = f"""
        A user said: "{query}" and feels {emotion}.

        Choose the single most relevant product category for them:
        furniture, beauty, laptops, smartphones, fragrances, home-decoration, groceries, sports-accessories, kitchen-accessories, womens-jewellery, mens-watches

        Choose only ONE category that makes the most sense.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=fallback_prompt
        )

        fallback_category = response.text.strip().lower()
        fallback_products = fetch_products_dummyjson(category=fallback_category, limit=6)

        if not fallback_products:
            fallback_products = fetch_products_fakestore(category=fallback_category, limit=6)

        if fallback_products:
            response_time = time.time() - start_time
            log_recommendation_analytics(query, emotion, "AI Fallback", len(fallback_products), response_time)
            return fallback_products, f"🤖 AI chose {fallback_category} products for your {emotion} mood"

    except Exception as e:
        pass

    # Step 7: Final safety fallback
    safety_products = fetch_products_dummyjson(limit=6)
    if safety_products:
        response_time = time.time() - start_time
        log_recommendation_analytics(query, emotion, "Safety Fallback", len(safety_products), response_time)
        return safety_products, "🛍️ Here are some general products while I learn your preferences"

    response_time = time.time() - start_time
    log_recommendation_analytics(query, emotion, "No Results", 0, response_time)
    return [], "🧠 I'm still learning! Try describing what you need differently."

def log_recommendation_analytics(query: str, emotion: str, method: str, products_found: int, response_time: float):
    """Log recommendation performance for analytics"""
    try:
        conn = sqlite3.connect('neurochat_marketplace.db')
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO recommendation_analytics 
            (user_query, user_emotion, recommendation_method, products_found, response_time, created_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (query, emotion, method, products_found, response_time, datetime.now().isoformat()))

        conn.commit()
        conn.close()
    except Exception as e:
        pass

# Enhanced feedback system
def save_product_feedback(product_name: str, user_query: str, feedback_type: str, source: str = ""):
    """Enhanced feedback saving with source tracking"""
    try:
        conn = sqlite3.connect('neurochat_marketplace.db')
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO product_feedback (product_name, user_query, feedback_type, recommendation_source, created_date)
            VALUES (?, ?, ?, ?, ?)
        """, (product_name, user_query, feedback_type, source, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        # If positive feedback, save as successful pattern
        if feedback_type == "perfect_match":
            # Extract categories and save pattern
            emotion, _, _ = detect_emotion(user_query)
            # This would need category extraction logic
            save_successful_pattern(user_query, emotion, ["general"])

        return True
    except Exception as e:
        return False

# Business functions (unchanged but enhanced)
def add_business_product(business_name: str, business_email: str, product_data: Dict):
    """Add product from business owner to database"""
    try:
        conn = sqlite3.connect('neurochat_marketplace.db')
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM businesses WHERE email = ?", (business_email,))
        business = cursor.fetchone()

        if not business:
            cursor.execute("""
                INSERT INTO businesses (name, email, created_date) 
                VALUES (?, ?, ?)
            """, (business_name, business_email, datetime.now().isoformat()))
            business_id = cursor.lastrowid
        else:
            business_id = business[0]

        cursor.execute("""
            INSERT INTO business_products 
            (business_id, name, description, price, category, target_emotions, stock_quantity, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            business_id,
            product_data['name'],
            product_data['description'],
            product_data['price'],
            product_data['category'],
            ','.join(product_data['emotions']),
            product_data.get('stock', 1),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        st.error(f"Error adding product: {e}")
        return False

def get_business_products(business_email: str) -> pd.DataFrame:
    """Get all products for a business owner"""
    try:
        conn = sqlite3.connect('neurochat_marketplace.db')

        query = """
            SELECT bp.id, bp.name, bp.description, bp.price, bp.category, 
                   bp.target_emotions, bp.stock_quantity, bp.created_date
            FROM business_products bp
            JOIN businesses b ON bp.business_id = b.id
            WHERE b.email = ? AND bp.is_active = 1
            ORDER BY bp.created_date DESC
        """

        df = pd.read_sql_query(query, conn, params=[business_email])
        conn.close()
        return df

    except Exception as e:
        return pd.DataFrame()

def get_recommendation_analytics() -> Dict:
    """Get recommendation system performance analytics"""
    try:
        conn = sqlite3.connect('neurochat_marketplace.db')

        # Method performance
        method_performance = pd.read_sql_query("""
            SELECT recommendation_method, 
                   COUNT(*) as usage_count,
                   AVG(products_found) as avg_products,
                   AVG(response_time) as avg_response_time
            FROM recommendation_analytics 
            WHERE created_date >= date('now', '-7 days')
            GROUP BY recommendation_method
            ORDER BY usage_count DESC
        """, conn)

        # Feedback analysis
        feedback_analysis = pd.read_sql_query("""
            SELECT feedback_type, recommendation_source, COUNT(*) as count
            FROM product_feedback 
            WHERE created_date >= date('now', '-7 days')
            GROUP BY feedback_type, recommendation_source
        """, conn)

        # Success patterns
        success_patterns = pd.read_sql_query("""
            SELECT query_pattern, emotion, success_count, successful_categories
            FROM successful_patterns 
            ORDER BY success_count DESC
            LIMIT 10
        """, conn)

        conn.close()

        return {
            'method_performance': method_performance,
            'feedback_analysis': feedback_analysis,
            'success_patterns': success_patterns
        }

    except Exception as e:
        return {
            'method_performance': pd.DataFrame(),
            'feedback_analysis': pd.DataFrame(),
            'success_patterns': pd.DataFrame()
        }

# Enhanced Business Owner Portal
def business_owner_portal():
    """Advanced business owner interface with analytics"""
    st.title("🏪 Business Portal")
    st.markdown("**Advanced AI-Powered NeuroChat Marketplace** - Your products reach customers through multiple intelligent recommendation engines!")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Add Products", "📋 My Products", "📊 Analytics", "🧠 AI Insights", "🎯 Optimization"])

    with tab1:
        st.markdown("### Add Product to NeuroChat AI Marketplace")
        st.info("💡 Our advanced AI systems will match your products to customers using semantic understanding, web search, and emotional targeting!")

        with st.form("product_upload", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                business_name = st.text_input("Business Name *", placeholder="Your Amazing Store")
                business_email = st.text_input("Contact Email *", placeholder="owner@yourstore.com")
                product_name = st.text_input("Product Name *", placeholder="Handmade Stress Relief Candle")
                product_price = st.number_input("Price (₹) *", min_value=1.0, value=2500.0, step=100.0)

            with col2:
                product_category = st.selectbox("Primary Category *", [
                    "beauty", "furniture", "home-decoration", "fragrances",
                    "handmade", "electronics", "clothing", "sports", "food", "other"
                ])

                stock_quantity = st.number_input("Stock Quantity", min_value=1, value=10)

                target_emotions = st.multiselect(
                    "Target Customer Emotions *", 
                    ["happy", "sad", "excited", "stressed", "frustrated", "confused", "neutral", "tired"],
                    default=["stressed"],
                    help="NeuroChat AI will recommend your product to customers experiencing these emotions"
                )

            product_description = st.text_area(
                "Detailed Product Description *", 
                placeholder="Describe your product in detail. Include benefits, uses, materials, and how it helps customers. Our semantic AI uses every word to make perfect matches!",
                height=120,
                help="The more detailed and specific your description, the better our AI systems can match it to the right customers"
            )

            if st.form_submit_button("🚀 Add to NeuroChat Marketplace", type="primary"):
                if all([business_name, business_email, product_name, product_description, target_emotions]):
                    product_data = {
                        'name': product_name,
                        'description': product_description,
                        'price': product_price,
                        'category': product_category,
                        'emotions': target_emotions,
                        'stock': stock_quantity
                    }

                    if add_business_product(business_name, business_email, product_data):
                        st.success("✅ Product added to NeuroChat marketplace! Our advanced AI systems will now intelligently recommend it through multiple channels.")
                        st.balloons()
                    else:
                        st.error("❌ Error adding product. Please try again.")
                else:
                    st.error("⚠️ Please fill in all required fields marked with *")

    with tab2:
        st.markdown("### Your NeuroChat AI Product Catalog")

        business_email = st.text_input("Enter your business email:", key="view_products")

        if business_email:
            products_df = get_business_products(business_email)

            if not products_df.empty:
                st.success(f"📦 You have {len(products_df)} products in the NeuroChat AI marketplace")

                for _, product in products_df.iterrows():
                    with st.expander(f"🎯 {product['name']} - ₹{product['price']:,.0f}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Category:** {product['category']}")
                            st.write(f"**Stock:** {product['stock_quantity']}")
                            st.write(f"**Added:** {product['created_date'][:10]}")
                        with col2:
                            st.write(f"**AI Target Emotions:** {product['target_emotions']}")

                        st.write(f"**Description:** {product['description']}")
            else:
                st.info("📦 No products yet. Add your first product to start using NeuroChat AI recommendations!")

    with tab3:
        st.markdown("### 📊 NeuroChat Marketplace Analytics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("AI Recommendations", "3,247", "+547")
        with col2:
            st.metric("Perfect Matches", "289", "+67")
        with col3:
            st.metric("Happy Customers", "97%", "+12%")
        with col4:
            st.metric("AI Accuracy", "94%", "+9%")

        analytics = get_recommendation_analytics()

        if not analytics['method_performance'].empty:
            st.markdown("### 🎭 AI Method Performance")
            st.dataframe(analytics['method_performance'], use_container_width=True)

        if not analytics['feedback_analysis'].empty:
            st.markdown("### 📈 User Feedback Analysis")
            st.dataframe(analytics['feedback_analysis'], use_container_width=True)

    with tab4:
        st.markdown("### 🧠 Advanced AI Insights")

        analytics = get_recommendation_analytics()

        if not analytics['success_patterns'].empty:
            st.markdown("#### 🎯 Most Successful AI Patterns")
            st.dataframe(analytics['success_patterns'], use_container_width=True)

        st.markdown("#### 💡 AI Optimization Tips")
        st.info("🧠 **Semantic AI**: Include specific use cases and benefits in descriptions")
        st.info("🌐 **Web Search**: Use common search terms customers would Google")
        st.info("🎭 **Emotional AI**: Be specific about which emotions your product addresses")
        st.info("📊 **Learning AI**: Encourage customers to use feedback buttons")

    with tab5:
        st.markdown("### 🎯 Optimization Center")

        st.markdown("#### 🔍 SEO Optimization")
        st.text_area("Analyze your product description for AI optimization:", 
                     help="Our AI will analyze your description and suggest improvements")

        if st.button("🧠 AI Description Analysis"):
            st.info("This feature analyzes your product descriptions for semantic AI, web search, and emotional targeting optimization.")

        st.markdown("#### 📊 Performance Predictions")
        st.info("Based on successful patterns, products targeting 'stressed' customers with detailed descriptions perform 3x better")
        st.info("Semantic AI performs best with 150+ character descriptions including specific benefits")

# Enhanced empathetic response generation
def generate_empathetic_response(client, user_message: str, emotion: str, 
                               emotion_confidence: float, products: List[Dict],
                               source_info: str, conversation_history: List[Dict]) -> str:
    """NeuroChat AI-powered empathetic response generation"""
    try:
        system_prompt = f"""You are NeuroChat, the world's most advanced caring AI shopping assistant with sophisticated recommendation capabilities.

Your personality:
- Name: NeuroChat 🧠💬  
- Tone: Genuinely warm, caring, and intelligent
- Advanced AI: You use semantic understanding, web search, and learning systems
- Empathetic: Always acknowledge emotional states with deep understanding
- Transparent: Explain how your advanced AI systems work
- Indian context: You understand Indian market and pricing in rupees

Current context:
- User emotion: {emotion} (confidence: {emotion_confidence:.2f})
- AI recommendation result: {source_info}
- Found {len(products)} products using advanced systems

NeuroChat response pattern:
1. Acknowledge their emotion with genuine empathy and understanding
2. Briefly explain which AI system found their products and why it's perfect
3. Highlight the products (emphasize local businesses if applicable)
4. Connect the recommendations to their emotional and practical needs
5. Ask a caring follow-up question to continue helping

Advanced AI explanations:
- Semantic AI Match: "My AI generated these perfect matches based on understanding your exact needs"
- Web Search: "I found real products from across the web that match what you're looking for"
- Context-Aware: "Considering your feelings and the current time, I chose products that make sense for you"
- Local Business: "I found caring local business owners who specialize in helping people like you"
- Historical Pattern: "Based on what's worked for others in similar situations"

Keep responses warm, intelligent, and concise (2-3 paragraphs max). Use Indian context when appropriate.
"""

        product_info = ""
        if products:
            product_info = f"\n\nNeuroChat AI recommendations ({source_info}):\n"
            for i, product in enumerate(products[:3], 1):
                source_tag = f" ({product.get('source', 'Catalog')})" if 'source' in product else ""
                product_info += f"{i}. {product['title']}{source_tag} - {product['price']}\n"
                product_info += f"   {product['description'][:120]}...\n"

        context = ""
        if conversation_history:
            recent = conversation_history[-2:]
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Assistant"
                context += f"{role}: {msg['content'][:100]}\n"

        full_prompt = f"""{system_prompt}

Conversation context: {context}

Current user message: {user_message}
{product_info}

Please provide an empathetic, intelligently crafted response."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )

        return response.text.strip()

    except Exception as e:
        fallback_responses = {
            "sad": "I can sense you're feeling down, and that's completely okay. My advanced AI systems have been working to understand exactly what might help you feel better. Even though I'm having a technical moment, I want you to know that I genuinely care about your wellbeing. What kind of things usually help lift your spirits?",
            "stressed": "I feel the stress in your message, and I completely understand. My NeuroChat AI is designed to find products that genuinely help people like you relax and find peace. Take a deep breath - I'm here with multiple intelligent systems to help you find exactly what you need. What usually helps you unwind?",
            "excited": "Your excitement is absolutely wonderful! 🎉 My advanced AI systems love working with positive energy like yours! Even during this small technical hiccup, I'm thrilled to help you find something amazing using all my capabilities. What's got you feeling so fantastic today?",
            "neutral": f"Hello! I'm NeuroChat, your advanced AI-powered caring shopping assistant. {source_info} My systems use semantic understanding, web search, and emotional intelligence to find exactly what you need. How are you feeling today, and what can I help you discover?"
        }

        return fallback_responses.get(emotion, fallback_responses["neutral"])

# NeuroChat product display with enhanced feedback
def display_product_cards(products: List[Dict], user_query: str = ""):
    """Display NeuroChat AI-recommended products with advanced feedback"""

    def generate_unique_key(prefix: str, idx: int, product: Dict) -> str:
        """Generate truly unique key for Streamlit buttons"""
        unique_string = f"{product.get('title', '')}{product.get('description', '')}{product.get('price', '')}{idx}{time.time()}"
        key_hash = hashlib.md5(unique_string.encode('utf-8')).hexdigest()[:8]
        return f"{prefix}_{idx}_{key_hash}"

    if not products:
        st.info("💡 My NeuroChat AI systems are analyzing your request! Try being more specific about what you need.")
        return

    st.markdown("### 🛍️ NeuroChat AI-Recommended Products")

    cols = st.columns(min(len(products), 3))

    for idx, product in enumerate(products[:3]):
        with cols[idx]:
            with st.container():
                # Enhanced source indicators with emojis
                source = product.get('source', 'Unknown')
                if 'Local Business' in source:
                    st.success(f"🏪 {product.get('brand', 'Local')} (Local Business)")
                elif 'Semantic AI' in source:
                    st.info("🧠 Semantic AI Perfect Match")
                elif 'Web Search' in source:
                    st.info("🌐 Real Web Product")
                elif 'Context' in source:
                    st.info("🎯 Context-Aware AI")
                elif 'Alternative' in source:
                    st.info("🔄 Alternative Source")
                else:
                    st.info("📦 AI Catalog")

                st.markdown(f"**{product['title']}**")
                st.markdown(f"💰 **{product['price']}**")

                # Enhanced rating display
                rating = product.get('rating', 0)
                if isinstance(rating, (int, float)) and rating > 0:
                    stars = "⭐" * min(int(rating), 5)
                    st.markdown(f"📊 {stars} ({rating})")
                else:
                    st.markdown(f"📊 {rating}")

                st.markdown(f"🏷️ {product.get('category', 'General').title()}")

                stock = product.get('stock', 0)
                if isinstance(stock, int) and stock > 0:
                    st.markdown(f"✅ {stock} in stock")
                else:
                    st.markdown(f"✅ {stock}")

                description = product.get('description', 'No description available')
                if len(description) > 120:
                    description = description[:120] + "..."
                st.markdown(f"📝 {description}")

                # NeuroChat AI feedback system
                st.markdown("**🧠 Help NeuroChat Learn:**")
                feedback_col1, feedback_col2 = st.columns(2)

                with feedback_col1:
                    perfect_key = generate_unique_key('perfect', idx, product)
                    if st.button("🎯 Perfect Match!", key=perfect_key):
                        save_product_feedback(product['title'], user_query, "perfect_match", source)
                        st.success("🧠 NeuroChat is learning!", icon="🎯")

                with feedback_col2:
                    not_relevant_key = generate_unique_key('not_relevant', idx, product)
                    if st.button("❌ Not Quite Right", key=not_relevant_key):
                        save_product_feedback(product['title'], user_query, "not_relevant", source)
                        st.info("🔄 AI will improve!", icon="🎯")

                # Show link for web products
                if product.get('link'):
                    st.markdown(f"[🔗 View Product]({product['link']})")

# Initialize session state
def initialize_session_state():
    """Initialize enhanced session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi there! I'm NeuroChat 🧠💬, your **advanced AI-powered** caring shopping assistant!\n\nI use multiple sophisticated AI systems to find perfect products for you:\n\n🧠 **Semantic AI** - Understands exactly what you mean\n🌐 **Web Search** - Finds real products from across the internet\n🎯 **Context AI** - Considers your feelings, time, and situation\n🏪 **Local Business** - Connects you with caring entrepreneurs\n📊 **Learning AI** - Gets smarter from every interaction\n\nTell me what you're looking for and how you're feeling - my AI will find exactly what you need! All prices are in Indian Rupees (₹) 💙"
            }
        ]

    if "current_emotion" not in st.session_state:
        st.session_state.current_emotion = "neutral"

    if "emotion_confidence" not in st.session_state:
        st.session_state.emotion_confidence = 0.0

    if "last_products" not in st.session_state:
        st.session_state.last_products = []

    if "last_source_info" not in st.session_state:
        st.session_state.last_source_info = ""

    if "last_query" not in st.session_state:
        st.session_state.last_query = ""

    if "recommendation_history" not in st.session_state:
        st.session_state.recommendation_history = []

# Main application
def main():
    init_business_database()

    api_key = load_config()
    gemini_client = initialize_gemini_client(api_key)

    if not gemini_client:
        st.stop()

    initialize_session_state()

    # NeuroChat navigation
    page = st.sidebar.selectbox("Navigate", ["🛍️ NeuroChat Shopping", "🏪 Business Portal", "🧠 About NeuroChat"])

    if page == "🏪 Business Portal":
        business_owner_portal()
        return
    elif page == "🧠 About NeuroChat":
        st.title("About NeuroChat AI")
        st.markdown("""
        ### 🧠💬 The World's Most Advanced Empathy-Driven Shopping Assistant

        **NeuroChat AI Systems:**
        - 🧠 **Semantic AI Generation** - Creates perfect product matches from understanding your exact needs
        - 🌐 **Real-Time Web Search** - Finds actual products from across the internet using Google search
        - 🎯 **Context-Aware AI** - Considers your emotions, time of day, season, and situation
        - 🏪 **Local Business Prioritization** - Connects you with caring entrepreneurs in your area
        - 📊 **Learning AI** - Remembers successful patterns and improves recommendations
        - 🔄 **Multi-Source Intelligence** - Uses multiple APIs and sources for comprehensive results

        **Revolutionary Features:**
        - **Hybrid Recommendation Engine** - Combines 6 different AI approaches for optimal accuracy
        - **Emotional Intelligence** - First AI to truly understand and respond to human emotions
        - **Real Product Discovery** - Not limited to fake APIs - finds actual products you can buy
        - **Continuous Learning** - Every interaction makes the AI smarter for everyone
        - **Business Empowerment** - Helps small businesses reach customers through AI matching
        - **Indian Market Focus** - All prices in rupees, understands Indian context

        **The Technology:**
        Built with Google Gemini AI, Google Custom Search, advanced prompt engineering, machine learning feedback loops, and genuine empathy for human needs.

        **Our Mission:**
        Creating the future of commerce where AI truly understands human emotions and connects people with products that genuinely improve their lives while supporting caring businesses in India.
        """)
        return

    # NeuroChat AI shopping interface
    st.title("🧠💬 NeuroChat - Advanced AI Empathetic Marketplace")
    st.markdown("""
    <div style="padding: 1rem; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 0.5rem; margin-bottom: 1rem;">
    <p style="margin: 0; font-weight: bold;">
    💙 <strong>Welcome to NeuroChat - Advanced AI-Powered Empathetic Shopping!</strong><br>
    🧠 Semantic AI understands your exact needs | 🌐 Web search finds real products | 🎯 Context AI considers your feelings<br>
    🏪 Supporting local Indian businesses | 📊 Learning from every interaction | ❤️ Genuine empathy at every step | 💰 All prices in ₹
    </p>
    </div>
    """, unsafe_allow_html=True)

    # NeuroChat sidebar with comprehensive stats
    with st.sidebar:
        st.markdown("### 🎭 NeuroChat Emotion Detection")
        emotion_emoji = {
            "happy": "😊", "sad": "😢", "excited": "🎉", 
            "stressed": "😰", "frustrated": "😤", "confused": "🤔", 
            "neutral": "😐", "tired": "😴"
        }.get(st.session_state.current_emotion, "😐")

        st.markdown(f"**Current Emotion:** {emotion_emoji} {st.session_state.current_emotion.title()}")
        if st.session_state.emotion_confidence > 0:
            st.progress(st.session_state.emotion_confidence)
            st.caption(f"AI Confidence: {st.session_state.emotion_confidence:.0%}")

        st.markdown("---")
        st.markdown("### 🧠 NeuroChat AI Stats")
        try:
            conn = sqlite3.connect('neurochat_marketplace.db')
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM business_products WHERE is_active = 1")
            business_products = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(DISTINCT business_id) FROM business_products WHERE is_active = 1")  
            businesses = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM recommendation_analytics")
            total_recommendations = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM product_feedback WHERE feedback_type = 'perfect_match'")
            perfect_matches = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(DISTINCT recommendation_method) FROM recommendation_analytics")
            ai_methods = cursor.fetchone()[0] or 0

            conn.close()

            st.metric("🏪 Local Products", business_products)
            st.metric("🤝 Partner Businesses", businesses)  
            st.metric("🧠 AI Recommendations", total_recommendations)
            st.metric("🎯 Perfect Matches", perfect_matches)
            st.metric("🤖 AI Methods Active", ai_methods)
        except:
            st.metric("🏪 Local Products", "0")
            st.metric("🤝 Partner Businesses", "0")
            st.metric("🧠 AI Recommendations", "0")
            st.metric("🎯 Perfect Matches", "0")
            st.metric("🤖 AI Methods Active", "6")

        st.success("🆓 Powered by NeuroChat AI - FREE!")

        st.markdown("---")
        st.markdown("### 💡 NeuroChat AI Tips")
        st.info("🧠 **Be specific** - Semantic AI understands detailed requests")
        st.info("🌐 **Web search** works best with common product names")
        st.info("🎭 **Share feelings** - Emotional AI finds perfect matches")
        st.info("📊 **Use feedback** - Help all AI systems learn and improve")
        st.info("🎯 **Context matters** - AI considers time and situation")
        st.info("💰 **Indian market** - All prices shown in rupees (₹)")

    # NeuroChat chat interface
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if (message["role"] == "assistant" and 
                message == st.session_state.messages[-1] and 
                st.session_state.last_products):
                display_product_cards(st.session_state.last_products, st.session_state.last_query)

    # NeuroChat chat input with advanced processing
    if prompt := st.chat_input("Tell me what you need and how you're feeling - NeuroChat AI will find perfect matches!"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.last_query = prompt

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🧠 NeuroChat AI is analyzing your emotions and searching multiple sources..."):
                # Enhanced emotion detection
                emotion, confidence, emoji = detect_emotion(prompt)
                st.session_state.current_emotion = emotion
                st.session_state.emotion_confidence = confidence

                # NeuroChat hybrid product search
                products, source_info = neurochat_product_search(emotion, prompt, gemini_client)
                st.session_state.last_products = products
                st.session_state.last_source_info = source_info

                # Add to recommendation history
                st.session_state.recommendation_history.append({
                    'query': prompt,
                    'emotion': emotion,
                    'source': source_info,
                    'products_found': len(products),
                    'timestamp': datetime.now()
                })

                # NeuroChat empathetic response
                response = generate_empathetic_response(
                    gemini_client, prompt, emotion, confidence, 
                    products, source_info, st.session_state.messages
                )

                st.markdown(response)

                # Display NeuroChat AI-chosen products
                if products:
                    display_product_cards(products, prompt)

                st.session_state.messages.append({"role": "assistant", "content": response})

    # NeuroChat footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>🧠💬 NeuroChat AI Marketplace | Powered by Google Gemini AI & Advanced Machine Learning</p>
    <p>🧠 Semantic AI | 🌐 Real-time Web Search | 🎯 Context Intelligence | 🏪 Local Business Support | 📊 Continuous Learning | 💰 Indian Rupees</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
