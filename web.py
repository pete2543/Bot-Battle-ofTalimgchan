"""
Web Dashboard สำหรับจัดการ URL สินค้าที่ต้องการเช็ค
"""
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from database import init_database, load_products, add_product, delete_product, toggle_product

app = Flask(__name__)

# Initialize database on startup
try:
    init_database()
except Exception as e:
    print(f"⚠️  Warning: Could not initialize database: {e}")

@app.route('/')
def index():
    """หน้าแรก - แสดงรายการสินค้าทั้งหมด"""
    products = load_products()
    return render_template('index.html', products=products)

@app.route('/add', methods=['POST'])
def add_product_route():
    """เพิ่มสินค้าใหม่"""
    url = request.form.get('url', '').strip()
    name = request.form.get('name', '').strip()
    
    if url:
        if not name:
            name = f"สินค้า #{len(load_products()) + 1}"
        add_product(url, name)
    
    return redirect(url_for('index'))

@app.route('/delete/<int:product_id>', methods=['POST'])
def delete_product_route(product_id):
    """ลบสินค้า"""
    delete_product(product_id)
    return redirect(url_for('index'))

@app.route('/toggle/<int:product_id>', methods=['POST'])
def toggle_product_route(product_id):
    """เปิด/ปิดการเช็คสินค้า"""
    toggle_product(product_id)
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
