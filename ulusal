import time
from playwright.sync_api import sync_playwright

# ---------------- AYARLAR ----------------
NOWTV_URL = "https://www.nowtv.com.tr/canli-yayin"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
OUTPUT_FILENAME = "nowtv.m3u8"

def get_nowtv_stream():
    print(f"🚀 NOW TV Canlı Yayın Linki Aranıyor...")
    
    found_stream_url = None

    with sync_playwright() as p:
        # Tarayıcıyı başlat
        browser = p.chromium.launch(headless=True) # Headless=True arka planda çalışır
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        # --- AĞ DİNLEYİCİSİ (SNIFFER) ---
        # Sayfa yüklenirken yapılan her isteği kontrol eder
        def handle_request(request):
            nonlocal found_stream_url
            url = request.url
            
            # Eğer istek .m3u8 içeriyorsa ve henüz bulmadıysak
            if ".m3u8" in url and not found_stream_url:
                # Reklam linklerini veya gereksiz segmentleri elemek için basit filtreler
                if "playlist" in url or "master" in url or "index" in url:
                    print(f"✅ Canlı Yayın Linki Yakalandı!")
                    found_stream_url = url

        # Dinleyiciyi sayfaya ekle
        page.on("request", handle_request)

        try:
            print(f"🌐 Siteye gidiliyor: {NOWTV_URL}")
            page.goto(NOWTV_URL, timeout=40000, wait_until="domcontentloaded")
            
            # Video player'ın yüklenmesi ve isteğin atılması için bekle
            print("⏳ Player yükleniyor ve ağ istekleri dinleniyor (Lütfen bekleyin)...")
            
            # Maksimum 15 saniye boyunca linkin düşmesini bekle
            for _ in range(15):
                if found_stream_url:
                    break
                time.sleep(1)
            
        except Exception as e:
            print(f"❌ Hata oluştu: {e}")
        
        browser.close()

    return found_stream_url

def main():
    # Linki bul
    stream_url = get_nowtv_stream()

    if stream_url:
        print(f"\n🔗 Bulunan Link: {stream_url}")
        
        # Dosyaya kaydet
        content = [
            "#EXTM3U",
            f"#EXT-X-USER-AGENT:{USER_AGENT}",
            f"#EXT-X-REFERER:{NOWTV_URL}",
            f'#EXTINF:-1 tvg-name="NOW TV" group-title="Ulusal Kanallar",NOW TV',
            stream_url
        ]

        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        
        print(f"📂 Dosya oluşturuldu: {OUTPUT_FILENAME}")
        print("🎉 İşlem Tamamlandı!")
    else:
        print("\n❌ Maalesef canlı yayın linki yakalanamadı.")

if __name__ == "__main__":
    main()
