"""
Web Dashboard สำหรับจัดการ URL สินค้าที่ต้องการเช็ค
"""
from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os

app = Flask(__name__)

# ไฟล์เก็บข้อมูล products
PRODUCTS_FILE = "data/products.json"

def load_products():
    """โหลดรายการสินค้าจากไฟล์"""
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_products(products):
    """บันทึกรายการสินค้าลงไฟล์"""
    os.makedirs(os.path.dirname(PRODUCTS_FILE), exist_ok=True)
    with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    """หน้าแรก - แสดงรายการสินค้าทั้งหมด"""
    products = load_products()
    return render_template('index.html', products=products)

@app.route('/add', methods=['POST'])
def add_product():
    """เพิ่มสินค้าใหม่"""
    url = request.form.get('url', '').strip()
    name = request.form.get('name', '').strip()
    
    if url:
        products = load_products()
        product_id = max([p.get('id', 0) for p in products], default=0) + 1
        products.append({
            'id': product_id,
            'url': url,
            'name': name or f"สินค้า #{product_id}",
            'active': True
        })
        save_products(products)
    
    return redirect(url_for('index'))

@app.route('/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    """ลบสินค้า"""
    products = load_products()
    products = [p for p in products if p['id'] != product_id]
    save_products(products)
    return redirect(url_for('index'))

@app.route('/toggle/<int:product_id>', methods=['POST'])
def toggle_product(product_id):
    """เปิด/ปิดการเช็คสินค้า"""
    products = load_products()
    for p in products:
        if p['id'] == product_id:
            p['active'] = not p.get('active', True)
            break
    save_products(products)
    return redirect(url_for('index'))

@app.route('/api/products')
def api_products():
    """API สำหรับ Bot ดึงข้อมูลสินค้า"""
    products = load_products()
    active_products = [p for p in products if p.get('active', True)]
    return jsonify(active_products)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
