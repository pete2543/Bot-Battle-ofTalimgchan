"""
Database setup and utilities
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """สร้าง connection กับ PostgreSQL"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_database():
    """สร้างตาราง products ถ้ายังไม่มี"""
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

def load_products():
    """โหลดรายการสินค้าจาก Database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT id, url, name, active FROM products ORDER BY id")
    products = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(p) for p in products]

def add_product(url, name):
    """เพิ่มสินค้าใหม่"""
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

def delete_product(product_id):
    """ลบสินค้า"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
    
    conn.commit()
    cur.close()
    conn.close()

def toggle_product(product_id):
    """เปิด/ปิดการเช็คสินค้า"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute(
        "UPDATE products SET active = NOT active, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (product_id,)
    )
    
    conn.commit()
    cur.close()
    conn.close()
