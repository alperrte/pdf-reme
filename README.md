<div align="center">

<img src="src/pdf_reme/resources/images/pdf-reme-logo.jpeg" alt="PDF-REME Logo" width="260" />

<br><br>

<img src="assets/1.png" alt="PDF-REME Hero" width="100%" />

PDF-REME

Read • Edit • Merge • Easily

Windows ve Linux için çevrimdışı, açık kaynak PDF ve belge yönetim aracı.

Belgelerinizi görüntüleyin, düzenleyin, birleştirin, bölün ve dönüştürün —
dosyalarınızı üçüncü taraf servislere yüklemeden, kendi bilgisayarınızda.

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white" />
  <img src="https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/Tests-53%20Passing-success" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-5A5A5A" />
  <img src="https://img.shields.io/badge/License-Apache--2.0-blue" />
  <img src="https://img.shields.io/badge/Status-Active%20Development-orange" />
</p>

</div>

PDF-REME Nedir?

PDF-REME, PDF ve belge işlemlerini mümkün olduğunca kullanıcının kendi bilgisayarında gerçekleştirmek üzere geliştirilen ücretsiz ve açık kaynak bir masaüstü uygulamasıdır.

Temel hedef; PDF ve benzeri belgeleri işlemek için web tabanlı araçlara, bulut servislerine veya üçüncü taraf dönüştürücülere dosya yükleme ihtiyacını azaltan, sade ve güvenli bir local-first çalışma alanı sunmaktır.

Local-first: Belgeleriniz varsayılan olarak cihazınızda kalır ve işlemler yerel olarak gerçekleştirilir.

Ürün Vizyonu

<div align="center">

<img src="assets/2.png" alt="PDF-REME Ana Sayfa Konsepti" width="100%" />

</div>

Yukarıdaki görsel, PDF-REME için hazırlanan arayüz konseptidir. PySide6 tabanlı gerçek arayüz geliştirme sürecinde bu tasarım dili referans alınacaktır.

PDF-REME V1 ile hedeflenen deneyim:

PDF dosyalarını görüntüleme

PDF birleştirme ve bölme

Sayfa sıralama, silme, döndürme ve çoğaltma

Başka PDF'den sayfa ekleme

JPG / JPEG / PNG → PDF

DOC / DOCX → PDF

PPT / PPTX → PDF

Yerel belge kütüphanesi

Favoriler ve son kullanılanlar

Çöp kutusu ve geri yükleme

Undo / Redo

Light / Dark tema altyapısı

Türkçe / İngilizce i18n altyapısı

Excel (XLS, XLSX) dönüşümü V1 kapsamına dahil değildir.

Kütüphane Konsepti

<div align="center">

<img src="assets/3.png" alt="PDF-REME Kütüphane Konsepti" width="100%" />

</div>

PDF-REME kütüphanesi, içe aktarılan ve uygulama tarafından oluşturulan belgeleri tek bir yerden yönetmeyi hedefler.

Planlanan yapı:

Yüklenenler

Oluşturulanlar

Favoriler

Son kullanılanlar

Arama ve filtreleme

Dosya türüne göre ayrım

Çöp kutusu

Yerel metadata yönetimi

PDF Düzenleyici Konsepti

<div align="center">

<img src="assets/4.png" alt="PDF-REME PDF Düzenleyici Konsepti" width="100%" />

</div>

V1 düzenleyici; tam metin düzenleme yerine sayfa tabanlı PDF işlemlerine odaklanır.

Planlanan işlemler:

Sayfaları sürükle-bırak ile sıralama

Sayfa silme

Sayfa döndürme

Sayfa çoğaltma

Başka PDF'den sayfa ekleme

Seçili sayfaları dışa aktarma

Undo / Redo

Save / Save As

Güvenli İçe Aktarma Akışı

<div align="center">

<img src="assets/5.png" alt="PDF-REME Güvenli İçe Aktarma Akışı" width="100%" />

</div>

PDF-REME'nin mevcut backend altyapısında gerçek bir dosya şu kontrollü akıştan geçirilebilir:

Dosya Seç
    ↓
Dosya Doğrulama
    ↓
SHA-256 Hesaplama
    ↓
Kopya Kontrolü
    ↓
Güvenli Yerel Kopyalama
    ↓
Document Metadata Kaydı
    ↓
SQLite COMMIT / ROLLBACK

Bu yapı sayesinde:

kaynak dosya korunur,

aynı içeriğe sahip dosyalar SHA-256 üzerinden tespit edilir,

mevcut dosyanın üzerine yanlışlıkla yazılmaz,

yarım kalan .part dosyaları temizlenir,

veritabanı hatasında rollback uygulanır,

veritabanında karşılığı olmayan yetim kopyalar bırakılmaz.

Aktif Geliştirme

<div align="center">

<img src="assets/6.png" alt="PDF-REME Aktif Geliştirme" width="100%" />

</div>

PDF-REME şu anda aktif olarak geliştirilmektedir.

Backend-first yaklaşımıyla önce çekirdek iş akışları ve güvenli veri yönetimi tamamlanmakta, ardından Stitch ile hazırlanan tasarım dili PySide6 arayüzüne uygulanacaktır.

Güncel checkpoint

53 passed

Şu anda tamamlanan temel altyapılar:

SQLite + SQLAlchemy veri katmanı

Repository pattern

Alembic migration altyapısı

Transaction / rollback yönetimi

SHA-256 hesaplama

Duplicate detection

PDF ve görsel doğrulama

DOCX / PPTX temel OOXML doğrulama

Güvenli kütüphane kopyalama

Gerçek PDF import akışı

Metadata veritabanı kaydı

Otomatik unit + integration testleri

Güvenlik ve Yerel Çalışma Yaklaşımı

PDF-REME geliştirilirken belge güvenliği temel ürün ilkelerinden biridir.

Kaynak belge otomatik olarak değiştirilmez.

Uygulama kendi kontrollü kopyası üzerinde çalışır.

Orijinal dosya yolu metadata olarak saklanır.

Fiziksel belgeler SQLite içine BLOB olarak gömülmez.

Aynı dosyanın tekrar eklenmesi SHA-256 ile tespit edilir.

Başarısız kopyalamalarda geçici dosyalar temizlenir.

Veritabanı işlemleri transaction sınırlarında yürütülür.

Hata halinde rollback uygulanır.

Log kayıtlarında belge içeriğinin tutulmaması hedeflenir.

Temel işlevlerin internet bağlantısı olmadan çalışması hedeflenir.

Desteklenen Dosya Türleri

İçe aktarma

PDF • DOC • DOCX • PPT • PPTX • JPG • JPEG • PNG

V1 dönüşüm hedefleri

JPG / JPEG / PNG → PDF

DOC / DOCX → PDF

PPT / PPTX → PDF

Teknoloji Yığını

Alan

Teknoloji

Programlama dili

Python

Masaüstü UI

PySide6 + Qt Widgets

Stil

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

LibreOffice Runtime (planlanan entegrasyon)

Test

pytest + pytest-qt

Kod kalitesi

Ruff

Lisans

Apache License 2.0

Mimari

PDF-REME klasik bir web uygulaması gibi ayrı frontend/backend sunucuları kullanmaz.
Masaüstü uygulaması içerisinde katmanlı bir yapı izlenir.

src/pdf_reme/
├── presentation/      # PySide6 ekranları ve UI bileşenleri
├── application/       # Use-case ve application servisleri
├── domain/            # Domain modelleri ve repository arayüzleri
├── infrastructure/    # SQLite, filesystem, PDF ve conversion adaptörleri
├── shared/            # Paths, config, logging, i18n, theme
└── resources/         # İkonlar, görseller, stiller ve çeviriler

Temel amaç, UI katmanının SQLAlchemy, dosya sistemi veya PDF motoru gibi altyapı detaylarına doğrudan bağımlı olmamasıdır.

Testler

Tüm mevcut testleri çalıştırmak için:

python -m pytest -v

Güncel geliştirme checkpoint'i:

53 passed

Testlerde örnek olarak şu senaryolar doğrulanmaktadır:

başarılı repository işlemleri,

migration upgrade / downgrade,

commit / rollback,

kaynak dosyanın korunması,

büyük dosyaların parça parça hashlenmesi,

bozuk PDF ve görsel reddi,

sahte DOCX / PPTX reddi,

duplicate detection,

güvenli .part kopyalama,

veritabanı hatasında fiziksel dosya temizliği,

gerçek import akışı,

regresyon kontrolleri.

Geliştirme Ortamı

Repository'yi klonla

git clone https://github.com/alperrte/pdf-reme.git
cd pdf-reme

Sanal ortam oluştur

Windows:

python -m venv venv
.\venv\Scripts\Activate.ps1

Linux:

python3 -m venv venv
source venv/bin/activate

Bağımlılıkları yükle

python -m pip install -r requirements.txt

Veritabanını hazırla

alembic upgrade head

Testleri çalıştır

python -m pytest -v

Uygulamayı başlat

python start_app.py

Kullanıcı arayüzü halen aktif geliştirme aşamasındadır.

Yerel Veri Yapısı

Windows geliştirme ortamındaki güncel veri yapısı:

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

Yol Haritası

Backend / Core

Proje ve katmanlı mimari temeli

SQLite + SQLAlchemy

Repository altyapısı

Alembic migration

Transaction yönetimi

Dosya doğrulama

SHA-256 / duplicate detection

Güvenli import

Kütüphane servisleri

Favoriler / Son kullanılanlar

Çöp kutusu / Restore

PDF görüntüleme

Merge / Split

Sayfa işlemleri

Undo / Redo

Görsellerden PDF

Office → PDF

Autosave / Session recovery

Frontend

Görsel tasarım dili / konsept çalışmaları

PySide6 uygulama shell'i

Ana Sayfa

Kütüphane

PDF Düzenleyici

Dönüştürme ekranları

Light / Dark tema

Backend entegrasyonu

Release

Windows Setup

Windows Portable

Linux paketi

V1 Kapsamı Dışında

İlk sürümde yer alması planlanmayan başlıca özellikler:

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

Katkıda Bulunma

Katkıda bulunmak istersen:

Repository'yi fork et

Ayrı bir branch oluştur

Değişikliklerini geliştir

Testleri çalıştır

Pull Request aç

Proje halen V1 geliştirme sürecinde olduğu için mimari ve API'lerde değişiklikler olabilir.

Lisans

PDF-REME Apache License 2.0 altında lisanslanmıştır.

Detaylar için LICENSE dosyasını inceleyebilirsiniz.

Geliştirici

<div align="center">

Alper Temiz

Yazılım Mühendisliği Öğrencisi • Full-Stack Developer • AI/ML Engineer

PDF-REME — Read • Edit • Merge • Easily

<br>

Belgeleriniz cihazınızda. İşlemleriniz kontrolünüzde.

⭐ Projeyi faydalı bulursanız yıldız verebilirsiniz.

</div>