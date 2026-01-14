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

def find_stream_candidates(browser, channel_info):
    url = channel_info["url"]
    name = channel_info["name"]
    print(f"\n📡 {name} taranıyor... ({url})")

    # Bulunan tüm potansiyel linkleri buraya atacağız
    candidates = []
    
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()

    def handle_response(response):
        try:
            # 1. MIME Type Kontrolü (Kesin Çözüm)
            content_type = response.headers.get("content-type", "").lower()
            req_url = response.url

            # Eğer yanıt bir m3u8 dosyası ise
            if "mpegurl" in content_type or ".m3u8" in req_url:
                
                # --- FİLTRELER ---
                # ATV Token servisini engelle
                if "securevideotoken" in req_url or "tmgrup.com.tr" in req_url:
                    return 
                # Reklamları engelle
                if "ad_break" in req_url or "google" in req_url or "doubleclick" in req_url:
                    return
                # Başarısız istekleri engelle
                if response.status != 200:
                    return

                # --- HEADER ALMA (GÜVENLİ YÖNTEM) ---
                referer = url # Varsayılan olarak site adresi
                try:
                    # Header'ı almayı dene, alamazsan site adresini kullan
                    header_ref = response.request.header_value("referer")
                    if header_ref:
                        referer = header_ref
                except:
                    pass

                # Listeye ekle
                entry = {"url": req_url, "referer": referer}
                candidates.append(entry)
                
                # Kullanıcıya bilgi ver (Sadece URL'in sonunu göster)
                short_url = req_url.split('?')[0][-30:]
                print(f"   ✅ Aday Link Bulundu: ...{short_url}")

        except Exception:
            pass

    page.on("response", handle_response)

    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        print("   ⏳ Yayın izleniyor (15 sn)...")
        
        # Linklerin havuza düşmesi için bekle
        # DaionCDN gelse bile biraz bekleyelim ki diğer alternatifler de düşsün
        for _ in range(15):
            time.sleep(1)
            # Eğer halihazırda DaionCDN bulduysak çok beklemeye gerek yok, erken çık
            has_daion = any("daioncdn" in c["url"] for c in candidates)
            if has_daion:
                print("   🔥 En iyi kaynak (Daion) tespit edildi, erken çıkılıyor.")
                break
            
    except Exception as e:
        print(f"   ❌ Tarama hatası: {e}")

    page.close()
    
    # --- EN İYİ LİNKİ SEÇME ---
    if not candidates:
        return None

    # 1. Öncelik: İçinde 'daioncdn' geçen link (ATV için)
    for c in candidates:
        if "daioncdn" in c["url"]:
            return c
            
    # 2. Öncelik: Herhangi bir geçerli link (NOW TV için)
    # Genellikle son bulunan link en güncel olandır, o yüzden listeyi ters çevirip bakabiliriz
    return candidates[-1]

def main():
    print("🚀 Ulusal Kanal Tarayıcı (V4 - Liste Modu) Başlatılıyor...")
    
    m3u_entries = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for channel in CHANNELS:
            best_candidate = find_stream_candidates(browser, channel)
            
            if best_candidate:
                stream_url = best_candidate["url"]
                referer = best_candidate["referer"]
                
                entry_lines = [
                    f'#EXTINF:-1 tvg-name="{channel["name"]}" group-title="{channel["group"]}",{channel["name"]}',
                    f'#EXT-X-REFERER:{referer}',
                    f'#EXT-X-USER-AGENT:{USER_AGENT}',
                    stream_url
                ]
                m3u_entries.append("\n".join(entry_lines))
                print(f"   💾 KAYDEDİLDİ: {channel['name']}")
            else:
                print(f"   ⚠️ {channel['name']} için uygun link yakalanamadı.")

        browser.close()

    if m3u_entries:
        header = "#EXTM3U"
        full_content = header + "\n" + "\n".join(m3u_entries)
        
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        print(f"\n📂 Dosya Oluşturuldu: {OUTPUT_FILENAME}")
    else:
        print("\n❌ Hiçbir kanal bulunamadı.")

if __name__ == "__main__":
    main()
