"""
Discord Bot สำหรับเช็คสต็อกสินค้าและแจ้งเตือน
รองรับการ deploy บน Railway
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
URL = os.getenv("PRODUCT_URL", "https://www.toylaxy.com/th/product/1227227/product-1227227?category_id=137697")


intents = discord.Intents.default()
client = discord.Client(intents=intents)

headers = {
    "User-Agent": "Mozilla/5.0 (StockChecker)"
}

# การตั้งค่าจาก environment variables หรือใช้ค่า default
ALERT_COUNT = int(os.getenv("ALERT_COUNT", "10"))  # แจ้งเตือนกี่ครั้ง
ALERT_INTERVAL = int(os.getenv("ALERT_INTERVAL", "10"))  # ห่างกันครั้งละกี่วินาที
CHECK_INTERVAL_MIN = int(os.getenv("CHECK_INTERVAL_MIN", "30"))
CHECK_INTERVAL_MAX = int(os.getenv("CHECK_INTERVAL_MAX", "60"))
CHECK_INTERVAL = [CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX]  # สลับเช็คทุกกี่วินาที


async def get_product_info():
    """ดึงข้อมูลสินค้า"""
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(URL, timeout=15) as r:
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


async def send_alert(channel, name, image_url, alert_number):
    """ส่งข้อความแจ้งเตือน"""
    embed = discord.Embed(
        title="🚨 สินค้ามีของแล้ว!",
        description=f"**{name}**\n[👉 คลิกเพื่อไปหน้าเว็บ]({URL})",
        color=0x2ecc71  # สีเขียว
    )
    if image_url:
        embed.set_image(url=image_url)
    embed.set_footer(text=f"🧪 ทดสอบระบบ | แจ้งเตือนครั้งที่ {alert_number}/{ALERT_COUNT}")

    await channel.send(embed=embed)


async def send_multiple_alerts(channel, name, image_url):
    """ส่งแจ้งเตือน 20 ครั้ง ห่างกันครั้งละ 10 วินาที"""
    print(f"🔔 เริ่มแจ้งเตือน {ALERT_COUNT} ครั้ง...")
    for i in range(1, ALERT_COUNT + 1):
        await send_alert(channel, name, image_url, i)
        print(f"✅ ส่งแจ้งเตือนครั้งที่ {i}/{ALERT_COUNT}")
        if i < ALERT_COUNT:  # ไม่ต้องรอหลังจากครั้งสุดท้าย
            await asyncio.sleep(ALERT_INTERVAL)
    print(f"✅ แจ้งเตือนครบ {ALERT_COUNT} ครั้งแล้ว")


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
        print("\n" + "=" * 50)
        print("📋 การตั้งค่า (TEST MODE):")
        print(f"  ✔ แจ้งเตือน {ALERT_COUNT} ครั้ง (เฉพาะตอนมีของ)")
        print(f"  ✔ ห่างกันครั้งละ {ALERT_INTERVAL} วินาที")
        print(f"  ✔ สลับเช็คทุก {CHECK_INTERVAL[0]} / {CHECK_INTERVAL[1]} วินาที")
        print(f"  ✔ แจ้งใหม่ได้อีกถ้าสินค้าหมดแล้วกลับมาอีกครั้ง")
        print("=" * 50)
        print("⚠️  กด Ctrl+C เพื่อหยุดการทำงาน\n")

        last_in_stock = False
        check_count = 0

        # เช็คสถานะเริ่มต้น
        in_stock, name, image_url = await get_product_info()
        print(f"📊 สถานะเริ่มต้น: {'✅ มีของ' if in_stock else '❌ หมดสต็อก'}")
        
        # ถ้าสินค้ามีของตั้งแต่เริ่มต้น ให้แจ้งเตือนทันที
        if in_stock:
            print("🎉 สินค้ามีของตั้งแต่เริ่มต้น! เริ่มแจ้งเตือน...")
            await send_multiple_alerts(channel, name, image_url)
            last_in_stock = True
        else:
            last_in_stock = False
        print()

        # Loop เช็คสต็อก
        while True:
            try:
                check_count += 1
                print(f"[#{check_count}] 🔍 กำลังเช็คสต็อกสินค้า...")
                in_stock, name, image_url = await get_product_info()

                # ถ้าหมดสต็อก - ไม่ส่งข้อความใดๆ
                if not in_stock:
                    if last_in_stock:  # เปลี่ยนจากมีของเป็นหมด
                        print("📉 สินค้าหมดสต็อก - รอให้มีของเข้ามาอีกครั้ง")
                    last_in_stock = False
                    print(f"📊 สถานะ: ❌ หมดสต็อก (ไม่ส่งข้อความใน Discord)")
                    # ไม่มี await channel.send() ที่นี่ - ไม่ส่งข้อความ
                # มีของเข้าใหม่ (เปลี่ยนจากหมดเป็นมีของ) - แจ้งเตือนเฉพาะตอนนี้เท่านั้น
                elif in_stock and not last_in_stock:
                    print("🎉 พบสินค้ามีของเข้ามา! เริ่มแจ้งเตือน...")
                    await send_multiple_alerts(channel, name, image_url)
                    last_in_stock = True
                elif in_stock and last_in_stock:
                    print("✅ สินค้ายังมีของอยู่ (ไม่แจ้งเตือนซ้ำ)")
                    # ไม่มี await channel.send() ที่นี่ - ไม่ส่งข้อความ

            except Exception as e:
                print(f"❌ เกิดข้อผิดพลาดในการเช็ค: {e}")
                import traceback
                traceback.print_exc()

            # สลับเช็คตามช่วงเวลาที่กำหนด
            wait_time = random.choice(CHECK_INTERVAL)
            print(f"⏱️  จะเช็คอีกครั้งใน {wait_time} วินาที...\n")
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

