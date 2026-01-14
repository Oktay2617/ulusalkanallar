import time
from playwright.sync_api import sync_playwright

# ---------------- AYARLAR ----------------
CHANNELS = [
    {
        "name": "NOW TV",
        "url": "https://www.nowtv.com.tr/canli-yayin",
        "group": "Ulusal Kanallar"
    },
    {
        "name": "ATV",
        "url": "https://www.atv.com.tr/canli-yayin",
        "group": "Ulusal Kanallar"
    }
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
OUTPUT_FILENAME = "ulusal_kanallar.m3u8"

def find_stream_by_response(browser, channel_info):
    url = channel_info["url"]
    name = channel_info["name"]
    print(f"\n📡 {name} aranıyor (MIME Type Analizi)... ({url})")

    found_data = {"url": None, "referer": None}
    
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()

    # --- YANIT DİNLEYİCİSİ (RESPONSE LISTENER) ---
    # Artık sadece isme değil, sunucunun "Bu bir yayındır" dediği yanıtlara bakıyoruz.
    def handle_response(response):
        nonlocal found_data
        
        # Eğer en iyi linki (daioncdn) zaten bulduysak diğerlerini boşver
        if found_data["url"] and "daioncdn" in found_data["url"]:
            return

        try:
            # Yanıtın türünü (Content-Type) kontrol et
            # Genellikle: application/vnd.apple.mpegurl veya application/x-mpegurl
            content_type = response.headers.get("content-type", "").lower()
            req_url = response.url

            if "mpegurl" in content_type or ".m3u8" in req_url:
                
                # --- FİLTRELER ---
                if "securevideotoken" in req_url or "tmgrup.com.tr" in req_url:
                    return # ATV token servisi, yayın değil.
                if "ad_break" in req_url or "google" in req_url or "doubleclick" in req_url:
                    return # Reklam
                if response.status != 200:
                    return # Hatalı veya engellenmiş yanıtları alma

                # --- 1. EN İYİ LİNK (ATV için DAION) ---
                if "daioncdn" in req_url:
                    print(f"   🔥 {name} İÇİN ORİJİNAL YAYIN (DAION) YAKALANDI!")
                    # Bu isteği yaparken kullanılan headerları al
                    headers = response.request.all_headers()
                    found_data["url"] = req_url
                    found_data["referer"] = headers.get("referer", url)
                    return

                # --- 2. STANDART LİNK ---
                if not found_data["url"]:
                    print(f"   ✅ {name} için geçerli yayın türü tespit edildi: {content_type}")
                    headers = response.request.all_headers()
                    found_data["url"] = req_url
                    found_data["referer"] = headers.get("referer", url)

        except Exception:
            pass

    # "request" yerine "response" dinliyoruz
    page.on("response", handle_response)

    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        print("   ⏳ Sayfa yüklendi, yayın paketleri bekleniyor...")
        
        # 25 saniye bekle
        for _ in range(25):
            if found_data["url"] and "daioncdn" in found_data["url"]:
                break
            time.sleep(1)
            
    except Exception as e:
        print(f"   ❌ Hata: {e}")

    page.close()
    return found_data

def main():
    print("🚀 Ulusal Kanal Tarayıcı (V3 - MIME Type) Başlatılıyor...")
    
    m3u_entries = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for channel in CHANNELS:
            result = find_stream_by_response(browser, channel)
            
            if result["url"]:
                stream_url = result["url"]
                referer = result["referer"]
                
                entry_lines = [
                    f'#EXTINF:-1 tvg-name="{channel["name"]}" group-title="{channel["group"]}",{channel["name"]}',
                    f'#EXT-X-REFERER:{referer}',
                    f'#EXT-X-USER-AGENT:{USER_AGENT}',
                    stream_url
                ]
                m3u_entries.append("\n".join(entry_lines))
                print(f"   💾 Eklendi: {stream_url[:50]}...")
            else:
                print(f"   ⚠️ {channel['name']} için yayın paketi bulunamadı.")

        browser.close()

    if m3u_entries:
        header = "#EXTM3U"
        full_content = header + "\n" + "\n".join(m3u_entries)
        
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        print(f"\n📂 Dosya Kaydedildi: {OUTPUT_FILENAME}")
    else:
        print("\n❌ Hiçbir kanal bulunamadı.")

if __name__ == "__main__":
    main()
