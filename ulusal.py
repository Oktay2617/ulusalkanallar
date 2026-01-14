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

# ATV için User-Agent'ı biraz daha modern tutmakta fayda var
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
OUTPUT_FILENAME = "ulusal_kanallar.m3u8"

def find_m3u8_link(browser, channel_info):
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
        
        # Sadece .m3u8 içeren ve henüz bulmadığımız linklere bak
        if ".m3u8" in req_url and not found_url:
            
            # --- FİLTRELEME BÖLÜMÜ ---
            
            # 1. ATV İÇİN KRİTİK DÜZELTME:
            # securevideotoken linki gerçek yayın değil, yetkilendirme servisidir. Bunu atla.
            if "securevideotoken" in req_url or "tmgrup.com.tr" in req_url:
                print(f"   ⚠️ Token servisi atlandı (Bekleniyor)...")
                return

            # 2. Reklam ve Gereksiz Segment Filtreleri
            # Bazı sitelerde 'ad_break' veya 'google' kaynaklı m3u8'ler çıkabilir.
            if "ad_break" in req_url:
                return

            # 3. İdeal Link Bulundu
            # ATV için genellikle 'daioncdn' veya 'turkuvaz' domainleri asıl yayındır.
            # Ancak genel filtre (token hariç her şey) genellikle yeterlidir.
            print(f"   ✅ {name} Gerçek Yayın Linki Yakalandı!")
            found_url = req_url

    page.on("request", handle_request)

    try:
        # Sayfaya git
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        
        # Linkin ağa düşmesi için bekle
        # ATV player'ı bazen geç yükleniyor, süreyi biraz artırdık.
        print("   ⏳ Yayın yükleniyor, istekler dinleniyor...")
        
        # Maksimum 25 saniye bekle
        for _ in range(25):
            if found_url:
                break
            time.sleep(1)
            
    except Exception as e:
        print(f"   ❌ Hata: {e}")

    page.close()
    return found_url

def main():
    print("🚀 Ulusal Kanal Tarayıcı (ATV Fix) Başlatılıyor...")
    
    m3u_entries = []

    with sync_playwright() as p:
        # Tarayıcıyı başlat
        browser = p.chromium.launch(headless=True)
        
        for channel in CHANNELS:
            stream_url = find_m3u8_link(browser, channel)
            
            if stream_url:
                # M3U formatına ekle
                entry = f'#EXTINF:-1 tvg-name="{channel["name"]}" group-title="{channel["group"]}",{channel["name"]}\n{stream_url}'
                m3u_entries.append(entry)
            else:
                print(f"   ⚠️ {channel['name']} için geçerli link bulunamadı.")

        browser.close()

    # Dosyayı Kaydet
    if m3u_entries:
        header = [
            "#EXTM3U",
            f"#EXT-X-USER-AGENT:{USER_AGENT}",
            "#EXT-X-ALLOW-CACHE:NO"
        ]
        
        full_content = "\n".join(header) + "\n" + "\n".join(m3u_entries)
        
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        print(f"\n📂 Dosya Kaydedildi: {OUTPUT_FILENAME}")
        print(f"📊 Durum: {len(m3u_entries)}/{len(CHANNELS)} kanal aktif.")
    else:
        print("\n❌ Hiçbir kanal bulunamadı.")

if __name__ == "__main__":
    main()
