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

# User-Agent güncellemesi
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
OUTPUT_FILENAME = "ulusal_kanallar.m3u8"

def find_stream_candidates(browser, channel_info):
    url = channel_info["url"]
    name = channel_info["name"]
    print(f"\n📡 {name} taranıyor... ({url})")

    candidates = []
    
    # Her kanal için tertemiz bir sayfa ve context açıyoruz
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()

    def handle_response(response):
        try:
            # Yanıt türü ve URL kontrolü
            content_type = response.headers.get("content-type", "").lower()
            req_url = response.url

            # M3U8 veya MPEGURL yakala
            if "mpegurl" in content_type or ".m3u8" in req_url:
                
                # --- FİLTRELER ---
                # Token ve reklamları engelle
                if "securevideotoken" in req_url or "tmgrup.com.tr" in req_url:
                    return 
                if "ad_break" in req_url or "google" in req_url or "doubleclick" in req_url:
                    return
                if response.status != 200:
                    return
                
                # Çapraz karışmayı önlemek için basit kontrol (Opsiyonel)
                # ATV ararken linkte 'nowtv' varsa şüpheli olabilir ama bazen ortak CDN kullanırlar.
                # Şimdilik bunu kapatıyorum, her şeyi yakalasın.

                # Header bilgisini güvenli al
                referer = url
                try:
                    header_ref = response.request.header_value("referer")
                    if header_ref:
                        referer = header_ref
                except:
                    pass

                entry = {"url": req_url, "referer": referer}
                
                # Aynı linki tekrar ekleme
                if entry not in candidates:
                    candidates.append(entry)
                    print(f"   ✅ Aday Link Havuza Eklendi: ...{req_url[-40:]}")

        except Exception:
            pass

    page.on("response", handle_response)

    try:
        # Timeout süresini artırdık (60sn)
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        print("   ⏳ Yayın izleniyor (Bekleniyor)...")
        
        # --- KRİTİK DÜZELTME ---
        # time.sleep() YERİNE wait_for_timeout() KULLANIYORUZ
        # Bu, tarayıcı event loop'unun çalışmaya devam etmesini sağlar.
        
        # Toplam 20 saniye bekle
        for _ in range(20):
            page.wait_for_timeout(1000) # 1 saniye bekle (Active Wait)
            
            # Eğer DaionCDN (ATV için en iyisi) bulduysak erken çık
            if name == "ATV" and any("daioncdn" in c["url"] for c in candidates):
                print("   🔥 ATV (Daion) bulundu, erken çıkılıyor.")
                break
            
            # NOW TV için playlist.m3u8 bulduysak erken çık
            if name == "NOW TV" and any("playlist.m3u8" in c["url"] for c in candidates):
                print("   🔥 NOW TV bulundu, erken çıkılıyor.")
                break
            
    except Exception as e:
        print(f"   ❌ Tarama hatası: {e}")

    page.close()
    context.close()
    
    # --- EN İYİ LİNKİ SEÇME ---
    if not candidates:
        return None

    # ATV için DaionCDN önceliği
    if name == "ATV":
        for c in candidates:
            if "daioncdn" in c["url"]:
                return c
                
    # Diğer durumlarda veya NOW TV için son bulunanı (en güncel) al
    # Genellikle m3u8 zincirinin en son halkası en doğru olandır.
    return candidates[-1]

def main():
    print("🚀 Ulusal Kanal Tarayıcı (V5 - Sync Fix) Başlatılıyor...")
    
    m3u_entries = []

    with sync_playwright() as p:
        # Headless=True (Arka plan modu)
        browser = p.chromium.launch(headless=True)
        
        for channel in CHANNELS:
            best_candidate = find_stream_candidates(browser, channel)
            
            if best_candidate:
                stream_url = best_candidate["url"]
                referer = best_candidate["referer"]
                
                # M3U Formatı
                entry_lines = [
                    f'#EXTINF:-1 tvg-name="{channel["name"]}" group-title="{channel["group"]}",{channel["name"]}',
                    f'#EXT-X-REFERER:{referer}',
                    f'#EXT-X-USER-AGENT:{USER_AGENT}',
                    stream_url
                ]
                m3u_entries.append("\n".join(entry_lines))
                print(f"   💾 LİSTEYE EKLENDİ: {channel['name']}")
            else:
                print(f"   ⚠️ {channel['name']} için uygun link yakalanamadı.")

        browser.close()

    # Dosya Yazma
    if m3u_entries:
        header = "#EXTM3U"
        full_content = header + "\n" + "\n".join(m3u_entries)
        
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        print(f"\n📂 Dosya Başarıyla Oluşturuldu: {OUTPUT_FILENAME}")
    else:
        print("\n❌ Hiçbir kanal bulunamadı.")

if __name__ == "__main__":
    main()
