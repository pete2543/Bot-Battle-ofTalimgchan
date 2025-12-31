"""
Discord Bot สำหรับเช็คสต็อกสินค้าและแจ้งเตือน
รองรับการ deploy บน Railway + Web Dashboard
"""
import discord
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import random
import re
import json
import os
from dotenv import load_dotenv

# โหลด environment variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

# ไฟล์เก็บข้อมูลสินค้า
PRODUCTS_FILE = "data/products.json"


intents = discord.Intents.default()
client = discord.Client(intents=intents)

headers = {
    "User-Agent": "Mozilla/5.0 (StockChecker)"
}

# การตั้งค่าจาก environment variables หรือใช้ค่า default
ALERT_COUNT = int(os.getenv("ALERT_COUNT", "10"))  # แจ้งเตือนกี่ครั้ง
ALERT_INTERVAL = int(os.getenv("ALERT_INTERVAL", "10"))  # ห่างกันครั้งละกี่วินาที
CHECK_INTERVAL_MIN = int(os.getenv("CHECK_INTERVAL_MIN", "600"))
CHECK_INTERVAL_MAX = int(os.getenv("CHECK_INTERVAL_MAX", "900"))
CHECK_INTERVAL = [CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX]  # สลับเช็คทุกกี่วินาที

# เก็บสถานะสินค้าแต่ละตัว
product_states = {}

def load_products():
    """โหลดรายการสินค้าจากไฟล์"""
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    # ถ้าไม่มีไฟล์ ให้สร้างค่า default จาก env
    default_url = os.getenv("PRODUCT_URL", "https://www.toylaxy.com/th/product/1227227/product-1227227?category_id=137697")
    return [{'id': 1, 'url': default_url, 'name': 'สินค้าเริ่มต้น', 'active': True}]


async def get_product_info(url):
    """ดึงข้อมูลสินค้า"""
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, timeout=15) as r:
            html = await r.text()

    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text()

    # ดึงชื่อสินค้า
    title = soup.find("meta", property="og:title")
    name = title["content"] if title else "Toylaxy Product"

    # เช็คใน JSON data (stock_txt field)
    in_stock = True  # default เป็นมีของ


    # หา JSON data ที่มี stock_txt
    json_pattern = r'"stock_txt"\s*:\s*"([^"]+)"'
    matches = re.findall(json_pattern, html, re.IGNORECASE)
    if matches:
        stock_txt = matches[0].lower()
        # ถ้า stock_txt เป็น "sold out" หรือ "หมด" = หมดสต็อก
        if "sold out" in stock_txt or "หมด" in stock_txt:
            in_stock = False
    else:
        # ถ้าไม่เจอ JSON ให้เช็คแบบเดิม
        page_text_without_title = page_text.replace(name, "")
        in_stock = not ("SOLD OUT" in page_text_without_title or "sold out" in page_text_without_title.lower() or 
                        "PRE-ORDER" in page_text_without_title or "pre-order" in page_text_without_title.lower() or 
                        "สินค้าหมด" in page_text_without_title)

    image = soup.find("meta", property="og:image")
    image_url = image["content"] if image else None

    return in_stock, name, image_url


async def send_alert(channel, name, image_url, alert_number, url):
    """ส่งข้อความแจ้งเตือน"""
    embed = discord.Embed(
        title="🚨 สินค้ามีของแล้ว!",
        description=f"**{name}**\n[👉 คลิกเพื่อไปหน้าเว็บ]({url})",
        color=0x2ecc71  # สีเขียว
    )
    if image_url:
        embed.set_image(url=image_url)
    embed.set_footer(text=f"แจ้งเตือนครั้งที่ {alert_number}/{ALERT_COUNT}")

    await channel.send(embed=embed)


async def send_multiple_alerts(channel, name, image_url, url):
    """ส่งแจ้งเตือนหลายครั้ง"""
    print(f"🔔 เริ่มแจ้งเตือน {ALERT_COUNT} ครั้ง สำหรับ: {name}")
    for i in range(1, ALERT_COUNT + 1):
        await send_alert(channel, name, image_url, i, url)
        print(f"✅ ส่งแจ้งเตือนครั้งที่ {i}/{ALERT_COUNT}")
        if i < ALERT_COUNT:
            await asyncio.sleep(ALERT_INTERVAL)
    print(f"✅ แจ้งเตือนครบ {ALERT_COUNT} ครั้งแล้ว")


async def check_single_product(channel, product):
    """เช็คสินค้า 1 ชิ้น"""
    product_id = product['id']
    product_url = product['url']
    product_name = product.get('name', f"สินค้า #{product_id}")
    
    try:
        print(f"🔍 กำลังเช็ค: {product_name}")
        in_stock, name, image_url = await get_product_info(product_url)
        
        # ดึงสถานะเก่าของสินค้านี้
        last_in_stock = product_states.get(product_id, False)
        
        # ถ้าหมดสต็อก
        if not in_stock:
            if last_in_stock:
                print(f"📉 {product_name}: สินค้าหมดสต็อก")
            product_states[product_id] = False
            print(f"  └─ สถานะ: ❌ หมดสต็อก")
        # มีของเข้าใหม่
        elif in_stock and not last_in_stock:
            print(f"🎉 {product_name}: พบสินค้ามีของเข้ามา!")
            await send_multiple_alerts(channel, name, image_url, product_url)
            product_states[product_id] = True
        elif in_stock and last_in_stock:
            print(f"  └─ สถานะ: ✅ ยังมีของอยู่")
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการเช็ค {product_name}: {e}")


@client.event
async def on_ready():
    print(f"✅ Bot เชื่อมต่อสำเร็จ!")
    print(f"📱 Bot name: {client.user}")
    print(f"🆔 Bot ID: {client.user.id}")
    
    # ตรวจสอบ environment variables
    if not TOKEN:
        print("❌ ไม่พบ DISCORD_TOKEN กรุณาตั้งค่า environment variable")
        await client.close()
        return
    
    if CHANNEL_ID == 0:
        print("❌ ไม่พบ CHANNEL_ID กรุณาตั้งค่า environment variable")
        await client.close()
        return

    try:
        channel = await client.fetch_channel(CHANNEL_ID)
        print(f"✅ พบ Channel: {channel.name}")
        print(f"🆔 Channel ID: {channel.id}")
        
        # โหลดรายการสินค้า
        products = load_products()
        print("\n" + "=" * 50)
        print("📋 การตั้งค่า:")
        print(f"  ✔ จำนวนสินค้าที่เช็ค: {len(products)} รายการ")
        print(f"  ✔ แจ้งเตือน {ALERT_COUNT} ครั้ง (เฉพาะตอนมีของ)")
        print(f"  ✔ ห่างกันครั้งละ {ALERT_INTERVAL} วินาที")
        print(f"  ✔ สลับเช็คทุก {CHECK_INTERVAL[0]}-{CHECK_INTERVAL[1]} วินาที")
        print("=" * 50)
        print("⚠️  กด Ctrl+C เพื่อหยุดการทำงาน\n")

        check_count = 0

        # เช็คสถานะเริ่มต้นทุกสินค้า
        print("📊 เช็คสถานะเริ่มต้น...")
        for product in products:
            if product.get('active', True):
                await check_single_product(channel, product)
                await asyncio.sleep(2)  # รอ 2 วิก่อนเช็คสินค้าถัดไป
        print()

        # Loop เช็คสต็อก
        while True:
            try:
                check_count += 1
                products = load_products()  # โหลดรายการใหม่ทุกครั้ง (เผื่อมีการเปลี่ยนแปลง)
                active_products = [p for p in products if p.get('active', True)]
                
                print(f"\n[รอบที่ #{check_count}] กำลังเช็ค {len(active_products)} รายการ...")
                print("-" * 50)
                
                for product in active_products:
                    await check_single_product(channel, product)
                    await asyncio.sleep(2)  # รอ 2 วิก่อนเช็คสินค้าถัดไป

            except Exception as e:
                print(f"❌ เกิดข้อผิดพลาดในการเช็ค: {e}")
                import traceback
                traceback.print_exc()

            # สลับเช็คตามช่วงเวลาที่กำหนด
            wait_time = random.choice(CHECK_INTERVAL)
            print(f"\n⏱️  จะเช็คอีกครั้งใน {wait_time} วินาที...\n")
            await asyncio.sleep(wait_time)

    except KeyboardInterrupt:
        print("\n\n⚠️  หยุดการทำงานโดยผู้ใช้")
        await client.close()
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()
        await client.close()


@client.event
async def on_error(event, *args, **kwargs):
    print(f"❌ เกิดข้อผิดพลาดใน event: {event}")


if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Discord Stock Checker Bot")
    print("=" * 50)
    
    # ตรวจสอบ environment variables ก่อนเริ่ม
    if not TOKEN:
        print("❌ Error: DISCORD_TOKEN ไม่ได้ถูกตั้งค่า")
        print("กรุณาตั้งค่า environment variable DISCORD_TOKEN")
        exit(1)
    
    if CHANNEL_ID == 0:
        print("❌ Error: CHANNEL_ID ไม่ได้ถูกตั้งค่า")
        print("กรุณาตั้งค่า environment variable CHANNEL_ID")
        exit(1)
    
    print(f"✅ Environment variables loaded")
    print(f"📍 Product URL: {URL}")
    print(f"🔔 Alert Count: {ALERT_COUNT}")
    print(f"⏱️  Check Interval: {CHECK_INTERVAL[0]}-{CHECK_INTERVAL[1]}s")
    print("=" * 50)
    
    try:
        client.run(TOKEN)
    except KeyboardInterrupt:
        print("\n⚠️  หยุดการทำงาน")
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()

