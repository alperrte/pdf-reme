<div align="center">

<img src="src/pdf_reme/resources/images/pdf-reme-logo.jpeg" alt="PDF-REME Logo" width="420">

PDF-REME

Read • Edit • Merge • Easily

Windows ve Linux için çevrimdışı, açık kaynak PDF ve belge yönetim aracı.

PDF belgelerinizi yerel olarak görüntüleyin, düzenleyin, birleştirin, bölün ve farklı dosya türlerinden PDF oluşturun — belgelerinizi üçüncü taraf servislere yüklemeden.

<br>









</div>

PDF-REME nedir?

PDF-REME, belge işlemlerini mümkün olduğunca kullanıcının kendi bilgisayarında gerçekleştirmek üzere geliştirilen ücretsiz ve açık kaynak bir masaüstü uygulamasıdır.

Temel amaç; PDF ve benzeri belgeleri işlemek için dosyaları web servislerine, bulut tabanlı dönüştürücülere veya üçüncü taraf yapay zekâ araçlarına yükleme ihtiyacını azaltan, sade ve güvenli bir yerel çalışma ortamı sunmaktır.

Local-first yaklaşım: Belgeler varsayılan olarak kullanıcının kendi bilgisayarında işlenir ve uygulama kütüphanesinde saklanır.

V1 hedefleri

Özellik

Durum

Yerel belge kütüphanesi

🚧 Geliştiriliyor

Güvenli dosya içe aktarma

✅ Hazır

SHA-256 ile kopya tespiti

✅ Hazır

PDF / görsel / OOXML doğrulama

✅ Hazır

SQLite + SQLAlchemy veri katmanı

✅ Hazır

Alembic migration altyapısı

✅ Hazır

Transaction / rollback yönetimi

✅ Hazır

Favoriler ve son kullanılanlar

⏳ Planlandı

Çöp kutusu ve geri yükleme

⏳ Planlandı

PDF görüntüleme

⏳ Planlandı

PDF birleştirme

⏳ Planlandı

PDF bölme

⏳ Planlandı

Sayfa sıralama / silme / döndürme / çoğaltma

⏳ Planlandı

Undo / Redo

⏳ Planlandı

JPG / PNG → PDF

⏳ Planlandı

DOC / DOCX → PDF

⏳ Planlandı

PPT / PPTX → PDF

⏳ Planlandı

Light / Dark tema

⏳ Planlandı

Windows / Linux paketleri

⏳ V1 sonunda

Proje şu anda aktif geliştirme aşamasındadır. Henüz son kullanıcıya yönelik kararlı V1 sürümü yayımlanmamıştır.

Güvenlik ve yerel çalışma yaklaşımı

PDF-REME geliştirilirken dosya güvenliği temel ürün ilkelerinden biri olarak ele alınır.

Kaynak dosya açık kullanıcı işlemi olmadan değiştirilmez.

İçe aktarılan belgelerin uygulama kontrollü bir kopyası oluşturulur.

Orijinal dosya yolu metadata olarak saklanır.

Aynı içeriğe sahip dosyalar SHA-256 özeti üzerinden tespit edilir.

Kopyalama işlemlerinde yarım dosya bırakmamak için geçici .part dosyaları kullanılır.

Veritabanı işlemleri transaction sınırları içerisinde yürütülür.

Hata durumunda rollback uygulanır ve yetim dosyalar temizlenir.

PDF ve görseller yalnızca uzantıya göre değil, mümkün olan yerlerde içerik açısından da doğrulanır.

DOCX ve PPTX dosyalarında temel OOXML paket yapısı kontrol edilir.

Desteklenen dosya türleri

İçe aktarma

PDF • DOC • DOCX • PPT • PPTX • JPG • JPEG • PNG

V1 dönüşüm hedefleri

JPG / JPEG / PNG → PDF

DOC / DOCX → PDF

PPT / PPTX → PDF

Excel (XLS, XLSX) dönüşümü V1 kapsamına dahil değildir.

Teknoloji yığını

Alan

Teknoloji

Programlama dili

Python

Masaüstü arayüz

PySide6 + Qt Widgets

Tema sistemi

QSS

PDF işlemleri

pypdf

PDF görüntüleme

PySide6 QtPdf

Görsel işlemleri

Pillow

Veritabanı

SQLite

ORM

SQLAlchemy

Migration

Alembic

Office → PDF

LibreOffice Runtime (V1 entegrasyonu planlandı)

Test

pytest + pytest-qt

Kod kalitesi

Ruff

Mimari

PDF-REME klasik web uygulaması gibi ayrı bir frontend/backend sunucusu kullanmaz. Masaüstü uygulaması içerisinde katmanlı bir mimari izlenir.

Presentation
    │
    ▼
Application / Use Cases
    │
    ▼
Domain
    ▲
    │
Infrastructure

Katmanlar

src/pdf_reme/
├── presentation/      # PySide6 ekranları ve UI bileşenleri
├── application/       # Use-case ve uygulama servisleri
├── domain/            # Modeller, kurallar ve repository arayüzleri
├── infrastructure/    # SQLite, filesystem, PDF ve dönüşüm adaptörleri
├── shared/            # Paths, config, logging, i18n ve tema altyapısı
└── resources/         # İkonlar, görseller, QSS ve çeviri kaynakları

Amaç, UI katmanının SQLAlchemy veya PDF motoru gibi altyapı detaylarına doğrudan bağımlı olmamasıdır.

Şu anda çalışan backend akışı

Güncel geliştirme noktasında gerçek bir PDF dosyası aşağıdaki akıştan geçirilebilmektedir:

Dosya
  │
  ▼
Dosya doğrulama
  │
  ▼
SHA-256 hesaplama
  │
  ▼
Kopya kontrolü
  │
  ▼
Güvenli yerel kopyalama
  │
  ▼
Document metadata kaydı
  │
  ▼
SQLite / COMMIT

Hata oluşması halinde ilgili işlem rollback edilir ve tamamlanmamış kopyalar temizlenir.

Testler

Backend/core geliştirmeleri otomatik testlerle doğrulanmaktadır.

Güncel geliştirme checkpoint'i:

53 passed

Tüm testleri çalıştırmak için:

python -m pytest -v

Test yapısı:

tests/
├── unit/
├── integration/
├── gui/
└── fixtures/

Her backend özelliğinde mümkün olduğunca şu senaryolar kontrol edilir:

başarılı işlem,

geçersiz giriş,

hata / rollback,

kaynak dosyanın korunması,

fiziksel çıktının doğrulanması,

önceki özelliklere karşı regresyon.

Geliştirme ortamı

1. Repository'yi klonlayın

git clone https://github.com/alperrte/pdf-reme.git
cd pdf-reme

2. Sanal ortam oluşturun

Windows:

python -m venv venv
.\venv\Scripts\Activate.ps1

Linux:

python3 -m venv venv
source venv/bin/activate

3. Bağımlılıkları yükleyin

python -m pip install -r requirements.txt

4. Veritabanını hazırlayın

alembic upgrade head

5. Testleri çalıştırın

python -m pytest -v

6. Uygulamayı başlatın

python start_app.py

Frontend henüz aktif geliştirme aşamasındadır. Kullanıcı arayüzü V1 tamamlanmadan önce önemli ölçüde değişebilir.

Yerel veri yapısı

PDF-REME kullanıcı verilerini uygulamanın yerel veri alanında tutar.

Geliştirme sırasında Windows'taki mevcut yapı:

Documents/
└── PDF-REME/
    ├── database/
    │   └── pdf_reme.db
    ├── library/
    │   ├── imported/
    │   │   ├── pdf/
    │   │   ├── word/
    │   │   ├── powerpoint/
    │   │   └── images/
    │   └── generated/
    ├── thumbnails/
    ├── sessions/
    ├── autosave/
    ├── cache/
    ├── temp/
    ├── trash/
    ├── backups/
    └── logs/

PDF ve diğer belgeler SQLite içerisine BLOB olarak gömülmez. Fiziksel dosyalar dosya sisteminde tutulur; belge metadata bilgileri SQLite içerisinde saklanır.

Yol haritası

Backend / Core
├── ✅ Veri erişim ve repository altyapısı
├── ✅ Alembic migration
├── ✅ Transaction yönetimi
├── ✅ Dosya doğrulama
├── ✅ SHA-256 / duplicate detection
├── ✅ Güvenli import
├── 🚧 Kütüphane servisleri
├── ⏳ Favoriler / son kullanılanlar
├── ⏳ Çöp kutusu
├── ⏳ PDF merge / split
├── ⏳ Sayfa işlemleri
├── ⏳ Undo / Redo
├── ⏳ Görsellerden PDF
├── ⏳ Office → PDF
└── ⏳ Autosave / recovery

Frontend
├── ⏳ Stitch tasarım çalışmaları
├── ⏳ PySide6 uygulama shell'i
├── ⏳ Ana Sayfa
├── ⏳ Kütüphane
├── ⏳ PDF Düzenleyici
├── ⏳ Dönüşüm ekranları
└── ⏳ Backend entegrasyonu

Release
├── ⏳ Windows Setup
├── ⏳ Windows Portable
└── ⏳ Linux paketi

V1 kapsamı dışında

Aşağıdaki özellikler ilk sürümün kapsamına dahil değildir:

PDF içindeki mevcut metin ve nesneleri Word benzeri düzenleme

OCR

Excel → PDF

Elektronik imza

Gelişmiş anotasyon

Form düzenleme

Bulut senkronizasyonu

Kullanıcı hesabı

Mobil uygulama

macOS paketleme

Otomatik güncelleme

Katkıda bulunma

PDF-REME açık kaynak bir projedir. Proje V1 geliştirme sürecinde olduğu için mimari ve özellikler değişebilir.

Katkı yapmak isteyenler:

Repository'yi fork edebilir.

Ayrı bir branch üzerinde çalışabilir.

Değişiklikleri test edebilir.

Pull Request açabilir.

Yeni özellik önerilerinin V1 kapsamını, veri güvenliğini ve mevcut mimariyi bozmaması beklenir.

Lisans

Bu proje Apache License 2.0 altında lisanslanmıştır.

Detaylar için LICENSE dosyasını inceleyebilirsiniz.

Geliştirici

<div align="center">

Alper Temiz

Software Engineering Student • Full-Stack Developer • AI/ML Engineer

PDF-REME — Read • Edit • Merge • Easily

</div>

<div align="center">

Belgeleriniz cihazınızda. İşlemleriniz kontrolünüzde.

⭐ Projeyi faydalı bulursanız GitHub'da yıldız verebilirsiniz.

</div>