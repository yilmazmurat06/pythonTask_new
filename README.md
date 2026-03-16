<div align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Flag_of_Interpol.svg/2560px-Flag_of_Interpol.svg.png" width="100"/>
  <h1>⭕ Interpol Red Notice Tracking System</h1>
  <p><i>Asenkron Veri Toplama ve Gerçek Zamanlı Takip Sistemi</i></p>
</div>

---

## 📌 Proje Hakkında
Bu proje, Interpol'ün uluslararası "Kırmızı Bülten (Red Notice)" veritabanını düzenli periyotlarla tarayan, elde ettiği arananlar listesini asenkron bir mesaj kuyruğu (Message Broker) üzerinden güvenle geçirerek yerel veri tabanına işleyen ve web üzerinden görselleştiren bir **Mikroservis (Microservices)** uygulamasıdır. 

Sistem dış etkenlere karşı dayanıklı, ölçeklenebilir ve **Docker** ile tamamen konteynerize edilmiş bir mimariyle tasarlanmıştır.

---

## 🏗️ Sistem Mimarisi ve Akış (Pipeline)

Sistemin kalbi birbirinden tamamen izole edilmiş fakat ağ üzerinden senkronize çalışan üç temel modülden oluşur:

### 1- Container A: Bot / Veri Toplayıcı (Scraper)
Görevi yalnızca Interpol sisteminden veri koparmaktır.
- Interpol'ün API'sine düzenli istekler gönderir. 
- Karşı tarafın güvenlik güvenlik cihazlarına (WAF/Cloudflare vb.) yakalanmamak için `curl_cffi` modülünü kullanır ve ağ üzerinde kendini "Google Chrome" tarayıcısıymış gibi gösterir (TLS Spoofing).
- Gelen ham veriyi filtreleyip sadece gerekli bilgileri paketler ve **RabbitMQ**'ya teslim eder. İşi bitince bir sonraki tarama süresine kadar beklemeye geçer.

### 2- RabbitMQ: Mesaj Kuyruğu (Message Broker)
**Container A** ile **Container B** arasındaki köprü görevini üstlenir. Scraper'ın çektiği yoğun verileri geçici belleğinde depolar ve yığın halde gelmesini engelleyerek alıcı taraf olan Web Sunucusuna verileri tek tek, güvenli bir şekilde sevk eder.

### 3- Container B: İşleyici ve Sunucu (Web Server & DB)
Verileri okuyan ve son kullanıcıya ulaştıran beynidir. İçerisinde iki farklı işleyici aynı anda asenkron olarak çalışır:
- **Queue Consumer (Arka Plan Dinleyicisi):** RabbitMQ kuyruğunu pür dikkat dinler. Yeni veri geldiğinde alır ve anında kalıcı **SQLite** veritabanına ekler. Eğer kişi zaten eşleşiyorsa üzerine yazar ve güncelleme sayısını artırır.
- **Flask Web Server:** Kullanıcılara modern bir arayüz (Dashboard) sunar. Tarayıcınızı sayfada açık bıraktığınızda arka plandaki JavaScript kodları, sayfayı yenilemenize gerek kalmadan saniyede bir Flask API'sine istek gönderir ve listeyi gerçek zamanlı (Real-time) olarak ekranınıza yansıtır.

---

## 💻 Kullanılan Teknolojiler
- **Python 3.x**
- **Docker Compose** *(Konteyner Yönetimi & Orkestrasyon)* 🐳
- **RabbitMQ** *(Mesaj Kuyruğu & AMQP Protokolü)* 🐇
- **Flask** *(Web Framework & REST API)* 🌶️
- **SQLite** *(İlişkisel ve Kalıcı Veritabanı)* 🗄️
- **curl_cffi** *(Güvenlik Duvarı Bypass ve Bot Gizleme)* 🥷 
- **HTML5, CSS3, Vanilla JS** *(Dinamik Ön-yüz Tasarımı)* 🎨

---

## 🚀 Hızlı Başlangıç & Kurulum

Sistemi çalıştırmak için bilgisayarınızda sadece **Docker Desktop**'ın kurulu olması yeterlidir.

1- Terminalinizi proje klasöründe açın ve projeyi inşa edip başlatın:
```bash
docker-compose up -d --build
```
> *(Bu işlem sistemin ihtiyaç duyduğu imajları indirecek ve üç ayrı servisi tek bir ağ içinde çalıştıracaktır.)*

2- Servisler `Healthy` (Sağlıklı) durumuna geldiğinde tarayıcınızdan aşağıdaki adreslere gidebilirsiniz:
* 🌐 **Canlı Web İzleme Paneli (Dashboard):** [http://localhost:8080](http://localhost:8080)
* ⚙️ **RabbitMQ Geliştirici Yönetim Ekranı:** [http://localhost:15672](http://localhost:15672)  *(Varsayılan kullanıcı/şifre: `guest` / `guest`)*

3- Sistemi tamamen durdurmak ve temizlemek için:
```bash
docker-compose down
```

---

## 📂 Dosya Hiyerarşisi

Sistem bileşenleri kofigürasyonlarına göre şu şekilde ayrılmıştır:

```text
├── docker-compose.yml       # Servis bağlarını, Volume'ları ve Ağları kuran Orkestratör dosya.
├── data/                    # Veritabanının konteyner kapansa dahi silinmemesi için (Volume) klasör.
│
├── container_a/             # 🕵️‍♂️ (SCRAPER SERVİSİ)
│   ├── scraper.py           # Interpol'den veri çeken ve kuyruğa yollayan bot yazılımı.
│   ├── config.py            # Botun ağ bağlatı ayarları ve tarama süresi konfigürasyonları.
│   ├── Dockerfile           # Servis A'nın yaratım adımları.
│   └── requirements.txt     # Botun kullanacağı python paketleri listesi.
│
└── container_b/             # 🖥️ (WEB VE VERİTABANI SERVİSİ)
    ├── web_server.py        # Kuyruktaki verileri karşılayan dinleyici ve Flask web sunucusu.
    ├── database.py          # SQLite veritabanı yönetim ve güncelleme kurallarının yazıldığı dosya.
    ├── config.py            # Servis B ağ, veritabanı yolları ve yayın portu (8080) ayarları.
    ├── Dockerfile           # Servis B'nin yaratım adımları.
    ├── requirements.txt     # Web sunucusu python paketleri.
    └── templates/           
        └── index.html       # Kullanıcının ekranda gördüğü Real-Time web arayüz tasarımı.
```

