"""
Database setup and utilities
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import time
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """สร้าง connection กับ PostgreSQL"""
    if not DATABASE_URL:
        raise Exception("DATABASE_URL is not set")
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️  Database connection failed (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"❌ Failed to connect to database after {max_retries} attempts")
                raise e

def init_database():
    """สร้างตาราง products ถ้ายังไม่มี"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                url TEXT NOT NULL,
                name TEXT NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        raise e

def load_products():
    """โหลดรายการสินค้าจาก Database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, url, name, active FROM products ORDER BY id")
        products = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return [dict(p) for p in products]
    except Exception as e:
        print(f"❌ Error loading products: {e}")
        return []

def add_product(url, name):
    """เพิ่มสินค้าใหม่"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO products (url, name, active) VALUES (%s, %s, TRUE) RETURNING id",
            (url, name)
        )
        product_id = cur.fetchone()['id']
        
        conn.commit()
        cur.close()
        conn.close()
        
        return product_id
    except Exception as e:
        print(f"❌ Error adding product: {e}")
        raise e

def delete_product(product_id):
    """ลบสินค้า"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error deleting product: {e}")
        raise e

def toggle_product(product_id):
    """เปิด/ปิดการเช็คสินค้า"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE products SET active = NOT active, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (product_id,)
        )
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error toggling product: {e}")
        raise e
