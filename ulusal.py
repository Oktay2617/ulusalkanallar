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

# --- STRATEJİ DEĞİŞİKLİĞİ: IPHONE USER-AGENT ---
# Siteye kendimizi iPhone olarak tanıtıyoruz. 
# Bu genellikle 'daioncdn' sunucusunu tetikler.
IPHONE_USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"

OUTPUT_FILENAME = "ulusal_kanallar.m3u8"

def find_specific_stream(browser, channel_info):
    url = channel_info["url"]
    name = channel_info["name"]
    print(f"\n📡 {name} taranıyor (iPhone Modu)...")

    found_stream = None
    
    # iPhone boyutlarında ve kimliğinde bir sayfa aç
    context = browser.new_context(
        user_agent=IPHONE_USER_AGENT,
        viewport={"width": 390, "height": 844}, # iPhone 12/13/14 boyutları
        is_mobile=True,
        has_touch=True
    )
    page = context.new_page()

    def handle_response(response):
        nonlocal found_stream
        # Eğer zaten bulduysak işlem yapma
        if found_stream: return

        try:
            req_url = response.url
            
            # Link .m3u8 mi?
            if ".m3u8" in req_url:
                
                # --- YASAKLI LİSTESİ ---
                if "securevideotoken" in req_url: return
                if "ad_break" in req_url or "google" in req_url: return
                
                # --- ÖZEL FİLTRELER ---
                
                # ATV İÇİN KATI KURAL:
                # Sadece ve sadece 'daioncdn' kabul et. 'ercdn' gelirse görmezden gel.
                if name == "ATV":
                    if "daioncdn" in req_url:
                        print(f"   🔥 [HEDEF] ATV DaionCDN Yakalandı!")
                        
                        # Referer al
                        referer = url
                        try:
                            r = response.request.header_value("referer")
                            if r: referer = r
                        except: pass
                        
                        found_stream = {"url": req_url, "referer": referer}
                    else:
                        # ercdn gelirse loga yaz ama alma
                        if "ercdn" in req_url:
                            # Debug için yazdırıyoruz, ama found_stream'e atamıyoruz
                            pass 

                # NOW TV İÇİN KURAL:
                elif name == "NOW TV":
                    # Standart işleyiş
                    referer = url
                    try:
                        r = response.request.header_value("referer")
                        if r: referer = r
                    except: pass
                    found_stream = {"url": req_url, "referer": referer}
                    print(f"   ✅ NOW TV Linki: ...{req_url[-30:]}")

        except Exception:
            pass

    page.on("response", handle_response)

    try:
        # Sayfaya git
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        
        # ATV için biraz daha uzun, NOW için kısa bekleme
        wait_time = 35 if name == "ATV" else 20
        
        print(f"   ⏳ Yayın akışı izleniyor ({wait_time} sn)...")
        
        # Bekleme döngüsü
        for i in range(wait_time):
            page.wait_for_timeout(1000)
            
            # Eğer ATV ise ve DaionCDN bulduysak çık
            if name == "ATV" and found_stream:
                break
            
            # NOW TV ise hemen çık
            if name == "NOW TV" and found_stream:
                break
                
    except Exception as e:
        print(f"   ❌ Hata: {e}")

    page.close()
    context.close()
    return found_stream

def main():
    print("🚀 Ulusal Kanal Tarayıcı (V7 - iPhone & Strict Filter) Başlatılıyor...")
    
    m3u_entries = []

    with sync_playwright() as p:
        # Mobil emülasyonu için normal chromium başlatıyoruz, context ayarlarıyla mobile çevireceğiz
        browser = p.chromium.launch(headless=True)
        
        for channel in CHANNELS:
            result = find_specific_stream(browser, channel)
            
            if result:
                stream_url = result["url"]
                referer = result["referer"]
                
                entry_lines = [
                    f'#EXTINF:-1 tvg-name="{channel["name"]}" group-title="{channel["group"]}",{channel["name"]}',
                    f'#EXT-X-REFERER:{referer}',
                    f'#EXT-X-USER-AGENT:{IPHONE_USER_AGENT}', # User-Agent'ı iPhone olarak dosyaya da yazıyoruz
                    stream_url
                ]
                m3u_entries.append("\n".join(entry_lines))
                
                # Logda ne bulduğumuzu görelim
                clean_url = stream_url.split('?')[0]
                print(f"   💾 EKLENDİ: {clean_url[-40:]}")
            else:
                print(f"   ⚠️ {channel['name']} için istenen kriterde link bulunamadı.")

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
