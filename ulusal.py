import time
from playwright.sync_api import sync_playwright

# ---------------- AYARLAR ----------------
# Aranacak kanalların listesi
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

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
OUTPUT_FILENAME = "ulusal_kanallar.m3u8"

def find_m3u8_link(browser, channel_info):
    """
    Verilen kanalın sayfasına gider ve .m3u8 isteğini yakalar.
    """
    url = channel_info["url"]
    name = channel_info["name"]
    print(f"\n📡 {name} aranıyor... ({url})")

    found_url = None
    
    # Yeni bir sayfa aç
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()

    # --- AĞ DİNLEYİCİSİ ---
    def handle_request(request):
        nonlocal found_url
        req_url = request.url
        
        # .m3u8 içeren ve henüz bulmadığımız linki yakala
        if ".m3u8" in req_url and not found_url:
            # Filtreleme: Genellikle ana yayın 'master', 'index' veya 'playlist' içerir.
            # ATV bazen 'trkvz' sunucularından gelir, NOW TV farklıdır.
            # En güvenli yöntem ilk anlamlı m3u8'i almaktır.
            
            # Gereksiz segment dosyalarını ele (ts, key vs değil m3u8 bakıyoruz zaten)
            if "ad_break" not in req_url: # Reklam aralarını elemek için basit bir kontrol eklenebilir
                print(f"   ✅ {name} Linki Yakalandı!")
                found_url = req_url

    page.on("request", handle_request)

    try:
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
        
        # Linkin ağa düşmesi için bekle (Maksimum 20 saniye)
        print("   ⏳ Yayın yükleniyor, bekleniyor...")
        for _ in range(20):
            if found_url:
                break
            time.sleep(1)
            
    except Exception as e:
        print(f"   ❌ Hata: {e}")

    page.close()
    return found_url

def main():
    print("🚀 Ulusal Kanal Tarayıcı Başlatılıyor...")
    
    m3u_entries = []

    with sync_playwright() as p:
        # Tarayıcıyı bir kere başlat, tüm kanallar için kullan
        browser = p.chromium.launch(headless=True)
        
        for channel in CHANNELS:
            stream_url = find_m3u8_link(browser, channel)
            
            if stream_url:
                # M3U formatına ekle
                entry = f'#EXTINF:-1 tvg-name="{channel["name"]}" group-title="{channel["group"]}",{channel["name"]}\n{stream_url}'
                m3u_entries.append(entry)
            else:
                print(f"   ⚠️ {channel['name']} için link bulunamadı.")

        browser.close()

    # Dosyayı Kaydet
    if m3u_entries:
        header = [
            "#EXTM3U",
            f"#EXT-X-USER-AGENT:{USER_AGENT}",
            # Referer her kanal için farklı olabilir, genelde boş bırakmak veya ana domaini vermek çalışır.
            # Şimdilik genel bir referer verelim veya boş geçelim.
        ]
        
        full_content = "\n".join(header) + "\n" + "\n".join(m3u_entries)
        
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        print(f"\n📂 Dosya Kaydedildi: {OUTPUT_FILENAME}")
        print(f"📊 Toplam {len(m3u_entries)}/{len(CHANNELS)} kanal bulundu.")
    else:
        print("\n❌ Hiçbir kanal bulunamadı.")

if __name__ == "__main__":
    main()
