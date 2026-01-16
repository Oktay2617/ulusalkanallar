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

# iPhone User-Agent (HLS yayını tetiklemek için en iyisi)
USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
OUTPUT_FILENAME = "ulusal_kanallar.m3u8"

def find_best_stream(browser, channel_info):
    url = channel_info["url"]
    name = channel_info["name"]
    print(f"\n📡 {name} taranıyor... ({url})")

    candidates = []
    
    # iPhone Emülasyonu
    context = browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True
    )
    page = context.new_page()

    def handle_response(response):
        try:
            req_url = response.url
            
            # .m3u8 kontrolü
            if ".m3u8" in req_url:
                
                # --- ELEME LİSTESİ ---
                if "securevideotoken" in req_url or "tmgrup.com.tr" in req_url: return
                if "ad_break" in req_url or "google" in req_url: return
                if response.status != 200: return

                # --- PUANLAMA ---
                priority = 0
                
                # ATV için DAIONCDN (Altın)
                if name == "ATV" and "daioncdn" in req_url:
                    priority = 100
                
                # NOW TV için DAIONCDN (Altın)
                elif name == "NOW TV" and "daioncdn" in req_url:
                    priority = 100
                
                # Yedekler (Gümüş) - ercdn vb.
                else:
                    priority = 50

                # Header Bilgisi (Referer) - 403 hatasını önlemek için şart
                referer = url
                try:
                    r = response.request.header_value("referer")
                    if r: referer = r
                except: pass

                entry = {"url": req_url, "referer": referer, "priority": priority}
                
                # Listeye ekle (Tekrarı önle)
                if not any(c['url'] == req_url for c in candidates):
                    candidates.append(entry)
                    # Loglama
                    short_url = req_url.split('?')[0][-30:]
                    tag = "🔥 [HEDEF]" if priority == 100 else "✅ [YEDEK]"
                    print(f"   {tag} Link Bulundu: ...{short_url}")

        except Exception:
            pass

    page.on("response", handle_response)

    try:
        # Sayfaya git
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        
        # --- ETKİLEŞİM BÖLÜMÜ (Player'ı Uyandırma) ---
        # Sayfanın ortasına tıklayarak olası "Play" butonlarını tetikle
        try:
            page.mouse.click(195, 422) # Ekranın ortası
            print("   👆 Player etkileşimi yapıldı.")
        except: pass

        print("   ⏳ Yayın trafiği dinleniyor (Maks 25sn)...")
        
        # Bekleme ve Kontrol Döngüsü
        for i in range(25):
            page.wait_for_timeout(1000)
            
            # Eğer 100 puanlık (Daion) link bulduysak bekleme, çık.
            if any(c['priority'] == 100 for c in candidates):
                print("   🚀 Hedef kalite yakalandı, döngü kırılıyor.")
                break
            
            # Eğer en azından bir link (ercdn vb.) bulduysak ve süre 15sn'yi geçtiyse çık
            # (Daha fazla bekleyip vakit kaybetmeyelim)
            if i > 15 and candidates:
                print("   ⚠️ Hedef bulunamadı ama yedek var, devam ediliyor.")
                break

    except Exception as e:
        print(f"   ❌ Hata: {e}")

    page.close()
    context.close()

    # --- SEÇİM ---
    if not candidates:
        return None

    # Puana göre sırala (En yüksek puan en başa)
    candidates.sort(key=lambda x: x['priority'], reverse=True)
    
    # En iyisini seç
    return candidates[0]

def main():
    print("🚀 Ulusal Kanal Tarayıcı (V8 - Etkileşimli & Yedekli) Başlatılıyor...")
    
    m3u_entries = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for channel in CHANNELS:
            best = find_best_stream(browser, channel)
            
            if best:
                stream_url = best["url"]
                referer = best["referer"]
                
                entry_lines = [
                    f'#EXTINF:-1 tvg-name="{channel["name"]}" group-title="{channel["group"]}",{channel["name"]}',
                    f'#EXT-X-REFERER:{referer}',
                    f'#EXT-X-USER-AGENT:{USER_AGENT}',
                    stream_url
                ]
                m3u_entries.append("\n".join(entry_lines))
                
                clean_url = stream_url.split('?')[0]
                print(f"   💾 EKLENDİ ({channel['name']}): ...{clean_url[-40:]}")
            else:
                print(f"   ❌ {channel['name']} için hiçbir link bulunamadı.")

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
