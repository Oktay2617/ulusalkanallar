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

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
OUTPUT_FILENAME = "ulusal_kanallar.m3u8"

def find_best_stream(browser, channel_info):
    url = channel_info["url"]
    name = channel_info["name"]
    print(f"\n📡 {name} taranıyor... ({url})")

    # Adayları toplayacağımız havuz
    # Yapı: {'priority': puan, 'url': url, 'referer': referer}
    # Puanlama: DaionCDN = 100 puan, Diğerleri = 50 puan
    candidates = []
    
    context = browser.new_context(user_agent=USER_AGENT)
    page = context.new_page()

    def handle_response(response):
        try:
            req_url = response.url
            
            # Linkin içinde .m3u8 geçiyor mu?
            if ".m3u8" in req_url:
                
                # --- İSTENMEYENLERİ ELE ---
                if "securevideotoken" in req_url or "tmgrup.com.tr" in req_url: return # Token servisi
                if "ad_break" in req_url or "google" in req_url: return # Reklam
                if response.status != 200: return # Hatalı link
                
                # --- PUANLAMA SİSTEMİ ---
                priority = 0
                
                # 1. HEDEF: ATV için DAIONCDN (En Yüksek Puan)
                # Linkin içinde hem 'daioncdn' hem de 'atv.m3u8' geçmeli
                if "daioncdn" in req_url and "atv.m3u8" in req_url:
                    priority = 100
                    print(f"   🔥 [ALTIN] DAIONCDN Linki Yakalandı!")
                
                # 2. YEDEK: ERCDN (Düşük Puan)
                elif "ercdn" in req_url:
                    priority = 50
                    print(f"   ⚠️ [GÜMÜŞ] ERCDN Linki Yakalandı (Yedek)")
                
                # 3. GENEL: NOW TV vb.
                else:
                    priority = 70
                    print(f"   ✅ Standart Link Yakalandı")

                # Header bilgisini al
                referer = url
                try:
                    header_ref = response.request.header_value("referer")
                    if header_ref: referer = header_ref
                except: pass

                # Listeye ekle
                entry = {"url": req_url, "referer": referer, "priority": priority}
                candidates.append(entry)

        except Exception:
            pass

    page.on("response", handle_response)

    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        print("   ⏳ Yayın trafiği izleniyor (Maks 30sn)...")
        
        # Bekleme Döngüsü
        for i in range(30):
            page.wait_for_timeout(1000)
            
            # ERKEN ÇIKIŞ KONTROLLERİ
            # Eğer ATV tarıyorsak ve 100 puanlık (Daion) link bulduysak bekleme, çık.
            if name == "ATV":
                if any(c['priority'] == 100 for c in candidates):
                    print("   🚀 Hedef link (Daion) bulundu, döngü kırılıyor.")
                    break
            
            # NOW TV için standart m3u8 bulduysak 5. saniyeden sonra çıkabiliriz (hız için)
            if name == "NOW TV" and i > 5:
                 if any("playlist.m3u8" in c['url'] for c in candidates):
                    break

    except Exception as e:
        print(f"   ❌ Hata: {e}")

    page.close()
    context.close()

    # --- SEÇİM ZAMANI ---
    if not candidates:
        return None

    # Puanı en yüksek olanı, puanlar eşitse en son bulunanı (en güncel) seç
    # Python'da sort stable olduğu için, önce önceliğe göre sıralarız.
    candidates.sort(key=lambda x: x['priority'], reverse=True)
    
    best = candidates[0]
    return best

def main():
    print("🚀 Ulusal Kanal Tarayıcı (V6 - Hedef Odaklı) Başlatılıyor...")
    
    m3u_entries = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for channel in CHANNELS:
            best_candidate = find_best_stream(browser, channel)
            
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
                
                # URL'in bir kısmını gösterelim ki doğru mu emin olalım
                clean_url_log = stream_url.split('?')[0]
                if "daioncdn" in stream_url:
                    print(f"   🏆 KAZANAN LİNK: ...daioncdn... ({clean_url_log[-20:]})")
                else:
                    print(f"   💾 KAZANAN LİNK: ...{clean_url_log[-20:]}")
            else:
                print(f"   ⚠️ {channel['name']} için link bulunamadı.")

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
