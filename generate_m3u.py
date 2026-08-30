import os
import re
import random
from KekikStream import KekikStream

CONFIG_FILE = "config.txt"
M3U_FILE = "rastgele_filmler.m3u"

def load_or_create_config(plugins_list):
    """Config dosyası yoksa oluşturur, varsa okur ve yeni eklentileri ekler."""
    config_data = {}
    
    if not os.path.exists(CONFIG_FILE):
        print(f"[!] {CONFIG_FILE} bulunamadı, mevcut tüm eklentiler 'aktif (1)' olarak oluşturuluyor...")
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            for plugin_name in plugins_list:
                f.write(f"{plugin_name}=1\n")
                config_data[plugin_name] = "1"
        return config_data

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                name, val = line.strip().split("=", 1)
                config_data[name.strip()] = val.strip()
                
    # KekikStream'e yeni eklenen bir eklenti varsa onu da config'e dahil et
    new_plugins = [p for p in plugins_list if p not in config_data]
    if new_plugins:
        with open(CONFIG_FILE, "a", encoding="utf-8") as f:
            for np in new_plugins:
                f.write(f"{np}=1\n")
                config_data[np] = "1"
                
    return config_data

def m3u_olustur():
    # KekikStream motorunu başlat
    ks = KekikStream()
    
    # KekikStream üzerindeki tüm eklenti isimlerini listele
    available_plugins = [p.name for p in ks.plugins]
    
    # Kullanıcının 0/1 tercihlerini config'den oku
    config = load_or_create_config(available_plugins)
    
    active_plugins = [name for name, status in config.items() if status == "1" and name in available_plugins]
    
    if not active_plugins:
        print("[!] Aktif hiçbir film sitesi seçilmemiş! config.txt dosyasını düzenleyin.")
        return

    print(f"[*] Aktif siteler taranıyor: {', '.join(active_plugins)}")
    film_havuzu = []

    # Tercih edilen sitelerden güncel içerikleri havuzda topla
    for plugin_name in active_plugins:
        try:
            plugin = ks.get_plugin(plugin_name)
            print(f" -> {plugin_name} içerikleri çekiliyor...")
            
            medya_listesi = plugin.get_main_page()
            if medya_listesi:
                for medya in medya_listesi:
                    # Dizi/Anime yerine sadece film olan içerikleri filtrele
                    if getattr(medya, 'is_movie', True): 
                        film_havuzu.append({'plugin': plugin, 'data': medya})
        except Exception as e:
            print(f" [Hata] {plugin_name} taranırken sorun oluştu: {e}")
            continue

    if not film_havuzu:
        print("[!] Sitelerden film içeriği çekilemedi. İşlem iptal edildi.")
        return

    # Havuzdan rastgele en fazla 50 film seç
    secilen_filmler = random.sample(film_havuzu, min(len(film_havuzu), 50))
    print(f"\n[*] {len(secilen_filmler)} adet rastgele film için linkler çözülüyor (Extractor)...")

    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        for item in secilen_filmler:
            plugin = item['plugin']
            medya = item['data']
            
            try:
                # Video oynatıcı (iframe/stream) linklerini çöz
                film_detay = plugin.load_item(medya)
                yayin_linkleri = plugin.load_links(film_detay)
                
                # Çözülen video linklerinden ilk m3u8 veya mp4 formatlı olanı yakala
                stream_url = None
                for link in yayin_linkleri:
                    if ".m3u8" in link.url or ".mp4" in link.url:
                        stream_url = link.url
                        break
                
                if stream_url:
                    # M3U formatına uygun başlık temizliği
                    cleaned_title = re.sub(r'[^\w\s\-\(\)]', '', medya.title)
                    logo_str = f' tvg-logo="{medya.poster}"' if hasattr(medya, 'poster') and medya.poster else ''
                    
                    f.write(f'#EXTINF:-1{logo_str} group-title="Rastgele Filmler",{cleaned_title}\n')
                    f.write(f"{stream_url}\n")
                    print(f" [Başarılı] {cleaned_title} ({plugin.name})")
            except:
                # Çözülemeyen link olursa sonraki filme geç
                continue

    print(f"\n[+] M3U Listesi başarıyla '{M3U_FILE}' adıyla güncellendi!")

if __name__ == "__main__":
    m3u_olustur()
