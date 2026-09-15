<div align="center">
  <img src="src/pdf_reme/resources/images/pdf-reme-logo.jpeg" alt="PDF-REME logosu" width="210" />

  <h1>📄 PDF-REME</h1>
  <h3>Read • Edit • Merge • Easily</h3>

  <p>
    <strong>Windows ve Linux için çevrimdışı, açık kaynak PDF ve belge yönetim aracı.</strong>
  </p>

  <p>
    Belgelerinizi görüntüleyin, düzenleyin, birleştirin, bölün ve dönüştürün.<br>
    <strong>Dosyalarınız cihazınızdan ayrılmaz.</strong>
  </p>

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white" alt="PySide6" />
  <img src="https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Tests-253%20Passing-success" alt="253 test başarılı" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-5A5A5A" alt="Windows ve Linux" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache--2.0-blue" alt="Apache 2.0 lisansı" /></a>
  <img src="https://img.shields.io/badge/Status-Active%20Development-orange" alt="Aktif geliştirme" />
</p>

<br>

<img src="src/pdf_reme/resources/images/1.png" alt="PDF-REME ana ekran konsepti" width="100%" />
</div>

---

## 📌 PDF-REME Nedir?

**PDF-REME**, PDF ve belge işlemlerini mümkün olduğunca kullanıcının kendi bilgisayarında gerçekleştirmek üzere geliştirilen ücretsiz ve açık kaynak bir masaüstü uygulamasıdır.

Temel hedef; PDF ve benzeri belgeleri işlemek için web tabanlı araçlara, bulut servislerine veya üçüncü taraf dönüştürücülere dosya yükleme ihtiyacını azaltan, sade ve güvenli bir **local-first** çalışma alanı sunmaktır.

> **Local-first:** Belgeleriniz varsayılan olarak cihazınızda kalır ve işlemler yerel olarak gerçekleştirilir.

### ✨ Öne çıkanlar

| 🔒 Gizlilik | 🧰 Güçlü PDF araçları | 🗃️ Yerel kütüphane | 🧪 Güvenilir altyapı |
|---|---|---|---|
| Dosyalar üçüncü taraf servislere yüklenmez. | PDF araçları, sıkıştırma ve belge dönüşümleri bir arada. | Belgeler, favoriler ve çöp kutusu cihazınızda yönetilir. | Katmanlı mimari ve **253 başarılı test**. |

---

## 🎯 Ürün Vizyonu

<div align="center">
<img src="src/pdf_reme/resources/images/2.png" alt="PDF-REME Ana Sayfa Konsepti" width="100%" />
</div>

> Yukarıdaki görsel, PDF-REME için hazırlanan **arayüz konseptidir**. PySide6 tabanlı gerçek arayüz geliştirme sürecinde bu tasarım dili referans alınacaktır.

PDF-REME; günlük belge işlemlerini tek bir yerel masaüstü uygulamasında, sade bir arayüz ve güvenli dosya yönetimiyle sunmayı hedefler. Ürün yaklaşımının temelini dört ilke oluşturur:

- **Yerel çalışma:** Belgeler varsayılan olarak cihazda kalır.
- **Kaynak dosyayı koruma:** İşlemler yeni çıktılar üretir; orijinal dosyanın üzerine yazılmaz.
- **Tek çalışma alanı:** PDF araçları, görsel dönüşümleri ve belge kütüphanesi birlikte çalışır.
- **Sade deneyim:** Teknik ayrıntıları kullanıcıdan uzak tutan, Türkçe öncelikli bir arayüz hedeflenir.

---

## 📚 Kütüphane Konsepti

<div align="center">
<img src="src/pdf_reme/resources/images/3.png" alt="PDF-REME Kütüphane Konsepti" width="100%" />
</div>

PDF-REME kütüphanesi, içe aktarılan ve uygulama tarafından oluşturulan belgeleri tek bir yerden yönetmeyi hedefler.

Mevcut backend altyapısında:

- **Yüklenenler** ve **Oluşturulanlar** ayrımı yapılabilir,
- favori belgeler takip edilebilir,
- son kullanılan belgeler `last_opened_at` üzerinden sıralanabilir,
- belgeler çöp kutusuna taşınabilir ve geri yüklenebilir,
- PDF araçları, sıkıştırma, görsel ve Office dönüşümlerinden üretilen dosyalar `generated` kütüphanesine kaydedilebilir,
- oluşturulan belgeler için SHA-256, dosya boyutu, sayfa sayısı ve üretim türü metadata olarak tutulabilir,
- fiziksel dosyalar dosya sisteminde, metadata bilgileri SQLite üzerinde tutulur.

---

## 🧩 PDF Düzenleyici Konsepti

<div align="center">
<img src="src/pdf_reme/resources/images/4.png" alt="PDF-REME PDF Düzenleyici Konsepti" width="100%" />
</div>

V1 düzenleyici; tam metin düzenleme yerine **sayfa tabanlı PDF işlemlerine** odaklanır.

Backend'de şu işlemler tamamlanmıştır:

- [x] Sayfaları istenilen sıraya göre yeniden sıralama
- [x] İki sayfanın yerini değiştirme
- [x] Seçilen sayfaları silme
- [x] Seçilen sayfaları döndürme
- [x] Seçilen sayfaları çoğaltma
- [x] Başka PDF'den seçili sayfaları ekleme
- [x] Boş sayfa ekleme
- [x] Seçili sayfaları yeni PDF olarak dışa aktarma
- [x] Undo / Redo işlem geçmişi
- [x] Kaynak PDF'yi değiştirmeden yeni çıktı üretme
- [x] Çıktıları `generated` kütüphanesine kaydetme

> V1 kapsamında PDF içindeki mevcut metin ve nesnelerin Word benzeri biçimde düzenlenmesi hedeflenmemektedir.

---

## 🛡️ Güvenli İçe Aktarma Akışı

<div align="center">
<img src="src/pdf_reme/resources/images/5.png" alt="PDF-REME Güvenli İçe Aktarma Akışı" width="100%" />
</div>

PDF-REME'nin mevcut backend altyapısında gerçek bir dosya şu kontrollü akıştan geçirilebilir:

```text
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
```

Bu yapı sayesinde:

- kaynak dosya korunur,
- aynı içeriğe sahip dosyalar SHA-256 üzerinden tespit edilir,
- mevcut dosyanın üzerine yanlışlıkla yazılmaz,
- yarım kalan `.part` dosyaları temizlenir,
- veritabanı hatasında rollback uygulanır,
- veritabanında karşılığı olmayan yetim kopyalar bırakılmaz.

---

## 🗑️ Çöp Kutusu ve Güvenli Silme Akışı

PDF-REME'nin mevcut backend altyapısında kütüphanedeki bir belge doğrudan kalıcı olarak silinmek yerine uygulamanın fiziksel çöp kutusuna taşınabilir.

```text
Kütüphane Belgesi
    ↓
TrashService.move_to_trash()
    ↓
Documents/PDF-REME/trash/
    ↓
status = trashed
trashed_from_path = önceki kütüphane yolu
deleted_at = silinme zamanı
```

Çöp kutusu altyapısında şu davranışlar uygulanmıştır:

- belgeyi fiziksel olarak `trash/` klasörüne taşıma,
- önceki kütüphane konumunu `trashed_from_path` ile saklama,
- belgeyi eski konumuna geri yükleme,
- restore sırasında aynı isimli dosyanın üzerine yazmama,
- çöp kutusundaki belgeleri listeleme,
- tek belgeyi kalıcı silme,
- çöp kutusunun tamamını temizleme,
- yalnızca PDF-REME `trash/` klasörü içindeki dosyalara kalıcı silme izni verme,
- kullanıcı dosyayı Explorer üzerinden elle silmiş olsa bile ilgili DB kaydını temizleyebilme,
- 30 günlük saklama süresini kontrol ederek süresi dolan kayıtları temizleme.

> `cleanup_expired()` ile 30 günlük backend kontrolü hazırdır. Bu kontrolün uygulama başlangıç akışına otomatik bağlanması PySide6 uygulama shell'i / frontend entegrasyonu sırasında yapılacaktır.

Gerçek dosya doğrulamasında aşağıdaki akış başarıyla test edilmiştir:

```text
Kütüphane
    ↓
Çöp Kutusu
    ↓
Geri Yükleme
    ↓
Çöp Kutusu
    ↓
Kalıcı Silme
```

---

## 🔗 PDF Birleştirme (Merge)

PDF-REME backend'inde birden fazla PDF dosyasını kullanıcının verdiği sırayı koruyarak tek bir yeni PDF dosyasında birleştiren altyapı tamamlanmıştır.

```text
PDF 3
PDF 1
PDF 2
   ↓
PdfMergeService
   ↓
3 → 1 → 2 sırasını koruyan yeni PDF
   ↓
library/generated/
   ↓
Document metadata kaydı
```

Mevcut Merge davranışları:

- en az iki PDF zorunluluğu,
- verilen dosya sırasının aynen korunması,
- kaynak PDF'lerin değiştirilmemesi,
- PDF olmayan veya bulunamayan girdilerin reddedilmesi,
- şifreli PDF'lerin kontrollü olarak reddedilmesi,
- çıktı dosyasının kaynak PDF'lerden birinin üzerine yazılmasının engellenmesi,
- aynı isimli generated çıktılarda benzersiz dosya adı oluşturulması,
- generated klasörü dışına yazmayı engelleyen dosya adı / path kontrolü,
- hata durumunda yarım çıktı dosyasının temizlenmesi,
- DB kayıt hatasında oluşturulan fiziksel çıktının temizlenmesi,
- SHA-256, dosya boyutu ve sayfa sayısının metadata olarak kaydedilmesi,
- `generation_type = "merge"` ile üretilen belgenin işaretlenmesi.

Gerçek dosya testi:

```bash
python scripts/manual_merge_test.py
```

---

## ✂️ PDF Sayfa Ayırma ve Bölme (Split)

PDF-REME backend'inde kullanıcı tarafından seçilen sayfalardan yeni PDF üretme ve bir PDF'yi birden fazla parçaya bölme altyapısı tamamlanmıştır.

Sayfa seçim ifadesi örneği:

```text
2,5,8-12,37
```

şuna dönüştürülebilir:

```text
2, 5, 8, 9, 10, 11, 12, 37
```

`PageSelectionParser` şu hatalı durumları kontrollü biçimde reddeder:

- boş ifade,
- 0 veya negatif sayfa numarası,
- belge sınırını aşan sayfa numarası,
- ters aralık (`8-5`),
- geçersiz metin,
- geçersiz aralık biçimi.

Tekrarlanan sayfa numaraları sıralama korunarak tekilleştirilir.

Split altyapısında:

- seçilen sayfalardan tek yeni PDF oluşturma,
- PDF'yi iki parçaya bölme,
- PDF'yi dört parçaya bölme,
- PDF'yi istenilen sayıda parçaya bölme,
- özel sayfa gruplarından ayrı PDF'ler oluşturma,
- eşit olmayan bölmelerde hiçbir sayfayı kaybetmeme,
- kaynak PDF'yi değiştirmeme,
- her çıktıyı `generated` kütüphanesine ayrı Document kaydı olarak ekleme,
- her çıktı için SHA-256 / dosya boyutu / sayfa sayısı hesaplama,
- aynı isimli çıktıların üzerine yazmama,
- path kontrolü,
- hata durumunda daha önce oluşturulmuş yarım çıktıları temizleme

davranışları uygulanmıştır.

Örneğin 10 sayfalık bir PDF dört parçaya bölündüğünde:

```text
3 + 3 + 2 + 2 = 10 sayfa
```

şeklinde dağıtılır ve hiçbir sayfa kaybolmaz.

Kullanılan generation type değerleri:

```text
split_extract
split_parts
split_groups
```

Gerçek dosya testi:

```bash
python scripts/manual_split_test.py
```

---

## 🛠️ Sayfa Düzenleme Backend'i

PDF-REME'nin sayfa tabanlı düzenleme altyapısındaki temel backend işlemleri ve Undo / Redo geçmişi tamamlanmıştır.

### ↕️ Sayfa sıralama

`reorder_pages()` verilen yeni sırayı birebir uygular.

```text
1 2 3 4 5
↓
5 1 3 2 4
```

Yeni sıranın belgedeki tüm sayfaları tam olarak bir kez içermesi zorunludur. Eksik veya tekrar eden sıralamalar reddedilir.

### 🔄 İki sayfanın yerini değiştirme

`swap_pages()` yalnızca belirtilen iki sayfanın yerini değiştirir ve mevcut `reorder_pages()` altyapısını tekrar kullanır.

```text
2 ↔ 5
1 2 3 4 5
↓
1 5 3 4 2
```

### 🗑️ Sayfa silme

`delete_pages()` seçilen sayfaları yeni PDF çıktısından kaldırır.

```text
Sil: 2,4
1 2 3 4 5
↓
1 3 5
```

Tüm sayfaların aynı işlemde silinmesine izin verilmez.

### 🔃 Sayfa döndürme

`rotate_pages()` seçilen sayfaları 90 derecenin katlarıyla döndürür. Negatif açılar desteklenir ve çıktıdaki dönüş açısı normalize edilir.

### 📑 Sayfa çoğaltma

`duplicate_pages()` seçilen her sayfanın bir kopyasını orijinal sayfanın hemen arkasına ekler.

### ➕ Başka PDF'den sayfa ekleme

`insert_pages()` başka bir PDF'den seçilen sayfaları, seçim sırasını koruyarak belgenin başına veya belirtilen sayfanın arkasına ekler.

### 📃 Boş sayfa ekleme

`insert_blank_page()` referans sayfanın boyutlarını kullanarak belgenin başına veya belirtilen sayfanın arkasına boş bir sayfa ekler.

### ↩️ Undo / Redo geçmişi

`PageEditHistory` ilk dosyayı ve üretilen düzenleme çıktılarını durum geçmişinde tutar. Geri alma sonrasında yeni bir işlem yapılırsa artık geçerli olmayan redo zinciri temizlenir.

Tüm PDF düzenleme işlemlerinde:

- kaynak PDF korunur,
- çıktı `library/generated/` altında yeni bir PDF olarak oluşturulur,
- aynı isimli mevcut çıktının üzerine yazılmaz,
- path traversal niteliğindeki dosya adları reddedilir,
- SHA-256 / dosya boyutu / sayfa sayısı metadata olarak saklanır,
- DB kayıt hatasında fiziksel çıktı temizlenir.

Kullanılan generation type değerleri:

```text
page_reorder
page_swap
page_delete
page_rotate
page_duplicate
page_insert
page_blank_insert
```

Gerçek dosya testi:

```bash
python scripts/manual_page_edit_test.py
python scripts/manual_page_edit_test2.py
```

İlk script reorder, swap ve delete işlemlerini; ikinci script ise rotate, duplicate, başka PDF'den sayfa ekleme, boş sayfa ekleme ve Undo / Redo geçmişini gerçek PDF'lerle doğrular. Her iki akışta da kaynak dosyaların değişmediği ve generated DB kayıtlarının oluştuğu kontrol edilir.

---

## 🖼️ Görsel Dönüşümleri

Gün 12 ile iki yönlü görsel dönüşüm altyapısı tamamlandı.

### JPG / JPEG / PNG → PDF

- Bir veya birden fazla görseli verilen sırayı koruyarak tek PDF'e dönüştürme
- RGB, RGBA ve şeffaf PNG desteği
- Kaynak görselleri değiştirmeden yeni çıktı üretme
- Çıktıyı `generation_type = "images_to_pdf"` ile kütüphaneye kaydetme

### PDF → JPG

- PDF'in tamamını veya seçilen sayfalarını JPG olarak dışa aktarma
- Seçilen sayfa sırasını koruma
- DPI ve JPEG kalite ayarları
- Her görseli `generation_type = "pdf_to_jpg"` ile ayrı belge olarak kaydetme
- Hata durumunda yarım çıktıları temizleme

Gerçek dosya testi:

```bash
python scripts/manual_image_conversion_test.py
```

---

## 📄 Office → PDF Dönüşümü

Gün 13 ile Word, PowerPoint ve Excel belgelerini PDF'e dönüştüren backend akışı tamamlandı.

- `DOC` / `DOCX` → PDF
- `PPT` / `PPTX` → PDF
- `XLS` / `XLSX` → PDF
- LibreOffice'i headless modda ve izole geçici profille çalıştırma
- Kurulu veya yapılandırılmış LibreOffice Runtime'ı otomatik bulma
- Üretilen PDF'in boyutunu, geçerliliğini ve sayfa sayısını doğrulama
- Kaynak belgeyi değiştirmeden benzersiz çıktı oluşturma
- Çıktıyı `word_to_pdf`, `powerpoint_to_pdf` veya `excel_to_pdf` türüyle kütüphaneye kaydetme
- Dönüşüm, zaman aşımı veya DB hatasında yarım çıktıyı temizleme

Gerçek dosya testi üç örnek Office belgesiyle çalıştırılabilir:

```bash
python scripts/manual_office_to_pdf_test.py "test.docx" "test.pptx" "test.xlsx"
```

> Office dönüşümü için sistemde erişilebilir veya uygulama tarafından yapılandırılmış bir LibreOffice Runtime gerekir.

---

## 🗜️ PDF Sıkıştırma

Gün 14 ile kaynak belgeyi koruyan PDF sıkıştırma backend'i tamamlandı.

| Profil | Yaklaşım |
|---|---|
| `light` | PDF yapısını ve görsel kalitesini mümkün olduğunca koruyan hafif optimizasyon |
| `balanced` | Dosya boyutu ile görsel kalite arasında dengeli optimizasyon |
| `strong` | Daha agresif görsel optimizasyonu ve gerektiğinde adaptif raster fallback |

Sıkıştırma akışında:

- PDF akışları ve uygun görseller `pikepdf` ile optimize edilir,
- çıktı geçerliliği ve sayfa sayısının değişmediği doğrulanır,
- şifreli veya geçersiz kaynaklar kontrollü biçimde reddedilir,
- sıkıştırılmış çıktı daha büyükse kaynak belge güvenli fallback olarak kopyalanır,
- orijinal ve yeni boyut ile kazanılan alan ve oran raporlanır,
- çıktı `pdf_compress_light`, `pdf_compress_balanced` veya `pdf_compress_strong` türüyle kütüphaneye kaydedilir,
- hata durumunda geçici ve yarım çıktılar temizlenir.

Gerçek dosya testi:

```bash
python scripts/manual_pdf_compression_test.py "C:\Test\test.pdf"
```

---

## 🚧 Aktif Geliştirme

<div align="center">
<img src="src/pdf_reme/resources/images/6.png" alt="PDF-REME Aktif Geliştirme" width="100%" />
</div>

PDF-REME şu anda aktif olarak geliştirilmektedir.

Backend-first yaklaşımla çekirdek iş akışları ve güvenli veri yönetimi geliştirilmektedir.

**Gün 14 tamamlandı:** Hafif, dengeli ve güçlü PDF sıkıştırma profilleri backend'e eklendi.

### ✅ Güncel checkpoint

```text
253 passed
0 failed
```

Şu anda tamamlanan temel altyapılar:

- [x] SQLite, repository ve migration altyapısı
- [x] Güvenli içe aktarma, doğrulama ve duplicate detection
- [x] Yerel kütüphane, favoriler, son kullanılanlar ve çöp kutusu
- [x] PDF birleştirme ve bölme
- [x] Sayfa tabanlı PDF düzenleme ve Undo / Redo geçmişi
- [x] JPG / JPEG / PNG → PDF
- [x] PDF → JPG
- [x] Word / PowerPoint / Excel → PDF
- [x] PDF sıkıştırma ve boyut kazanımı raporlama
- [x] Otomatik ve gerçek dosya testleri

---

## 🔐 Güvenlik ve Yerel Çalışma Yaklaşımı

PDF-REME geliştirilirken belge güvenliği temel ürün ilkelerinden biridir.

- Kaynak belge otomatik olarak değiştirilmez.
- Uygulama kendi kontrollü kopyası veya yeni generated çıktısı üzerinde çalışır.
- Orijinal dosya yolu metadata olarak saklanır.
- Fiziksel belgeler SQLite içine BLOB olarak gömülmez.
- Aynı dosyanın tekrar eklenmesi SHA-256 ile tespit edilir.
- Başarısız kopyalamalarda geçici dosyalar temizlenir.
- Veritabanı işlemleri transaction sınırlarında yürütülür.
- Hata halinde rollback uygulanır.
- DB kayıt hatalarında yeni oluşturulmuş generated çıktılar temizlenebilir.
- Çıktı dosyalarının kaynak PDF'nin üzerine yazılması engellenir.
- Generated dosya adlarında klasör yolu / path traversal girişleri reddedilir.
- Aynı isimli generated çıktıların üzerine yazılmaz; benzersiz isim üretilir.
- Çöp kutusuna taşınan belgenin önceki uygulama yolu ayrıca saklanır.
- Kalıcı silme yalnızca PDF-REME'nin kendi `trash/` alanıyla sınırlandırılır.
- Restore işleminde aynı isimli dosyanın üzerine yazılmaz.
- Çöp kutusundaki fiziksel dosyalar kullanıcı tarafından Dosya Gezgini üzerinden erişilebilir durumdadır.
- Log kayıtlarında belge içeriğinin tutulmaması hedeflenir.
- Temel işlevlerin internet bağlantısı olmadan çalışması hedeflenir.

---

## 📁 Desteklenen Dosya Türleri

### 📥 İçe aktarma

`PDF` • `DOC` • `DOCX` • `PPT` • `PPTX` • `JPG` • `JPEG` • `PNG`

### 🧰 Mevcut işlemler

- PDF Merge
- PDF Split
- Seçili sayfaları dışa aktarma
- Sayfa sıralama
- Sayfa yer değiştirme
- Sayfa silme
- Sayfa döndürme
- Sayfa çoğaltma
- Başka PDF'den sayfa ekleme
- Boş sayfa ekleme
- Undo / Redo işlem geçmişi
- JPG / JPEG / PNG → PDF
- PDF → JPG
- DOC / DOCX → PDF
- PPT / PPTX → PDF
- XLS / XLSX → PDF
- Hafif / dengeli / güçlü PDF sıkıştırma

---

## 🧱 Teknoloji Yığını

| Alan | Teknoloji |
|---|---|
| Programlama dili | Python 3.10+ |
| Masaüstü UI | PySide6 + Qt Widgets |
| Stil | QSS |
| PDF işlemleri | pypdf |
| PDF sıkıştırma | pikepdf + Pillow + QtPdf |
| PDF görüntüleme | PySide6 QtPdf |
| Görsel işlemleri | Pillow |
| Office → PDF | LibreOffice Runtime |
| Veritabanı | SQLite |
| ORM | SQLAlchemy |
| Migration | Alembic |
| Test | pytest + pytest-qt |
| Kod kalitesi | Ruff |
| Lisans | Apache License 2.0 |

---

## 🏗️ Mimari

PDF-REME klasik bir web uygulaması gibi ayrı frontend/backend sunucuları kullanmaz.

Masaüstü uygulaması içerisinde katmanlı bir yapı izlenir.

```text
src/pdf_reme/
├── presentation/      # PySide6 ekranları ve UI bileşenleri
├── application/       # Use-case ve application servisleri
├── domain/            # Domain modelleri ve repository arayüzleri
├── infrastructure/    # SQLite, filesystem, PDF ve conversion adaptörleri
├── shared/            # Paths, config, logging, i18n, theme
└── resources/         # İkonlar, görseller, stiller ve çeviriler
```

Temel amaç, UI katmanının SQLAlchemy, dosya sistemi veya PDF motoru gibi altyapı detaylarına doğrudan bağımlı olmamasıdır.

Örnek akışlar:

```text
Presentation (ileride PySide6)
        ↓
Application Service / Use Case
        ↓
Repository + Infrastructure Service
        ↓
SQLite + Dosya Sistemi + pypdf
```

Merge örneği:

```text
Presentation
    ↓
MergePdfsUseCase
    ↓
PdfMergeService + DocumentRepository
    ↓
pypdf + generated/ + SQLite
```

Page Edit örneği:

```text
Presentation
    ↓
EditPdfPagesUseCase
    ↓
PdfPageEditService + DocumentRepository
    ↓
pypdf + generated/ + SQLite
```

Görsel dönüşüm örneği:

```text
Presentation
    ↓
ConvertImagesToPdfUseCase / ConvertPdfToImagesUseCase
    ↓
ImageToPdfService / PdfToImageService
    ↓
Pillow + QtPdf + generated/ + SQLite
```

Office dönüşüm örneği:

```text
Presentation
    ↓
ConvertOfficeToPdfUseCase
    ↓
OfficeToPdfService + DocumentRepository
    ↓
LibreOffice Runtime + generated/ + SQLite
```

PDF sıkıştırma örneği:

```text
Presentation
    ↓
CompressPdfUseCase
    ↓
PdfCompressionService + PdfCompressionEngine
    ↓
pikepdf + Pillow + QtPdf + generated/ + SQLite
```

---

## 🧪 Testler

Tüm mevcut testleri çalıştırmak için:

```bash
python -m pytest -v
```

Güncel geliştirme checkpoint'i:

```text
253 passed
0 failed
```

Test paketi başlıca şu alanları kapsar:

- veri katmanı, migration ve transaction davranışları,
- dosya doğrulama, güvenli import ve duplicate detection,
- kütüphane ve çöp kutusu işlemleri,
- Merge, Split ve sayfa düzenleme akışları,
- görsel sırasını ve şeffaflığı koruyan JPG / PNG → PDF dönüşümü,
- tüm sayfaları veya seçilen sayfaları PDF → JPG dönüştürme,
- DPI, kalite, geçersiz girdi ve şifreli PDF kontrolleri,
- Word, PowerPoint ve Excel belgelerinde doğru generation type üretimi,
- LibreOffice runtime keşfi, zaman aşımı ve geçersiz çıktı kontrolleri,
- üç PDF sıkıştırma profilinin geçerli çıktı üretmesi,
- sayfa sayısının korunması ve çıktının kaynaktan büyük olmaması,
- şifreli PDF, geçersiz profil ve path traversal kontrolleri,
- hata durumunda fiziksel çıktıların temizlenmesi,
- kaynak dosyaların değişmeden kalması ve genel regresyon kontrolleri.

### 🧑‍🔬 Manuel gerçek dosya testleri

Çöp kutusu:

```bash
python scripts/manual_trash_test.py
```

Merge:

```bash
python scripts/manual_merge_test.py
```

Split:

```bash
python scripts/manual_split_test.py
```

Sayfa düzenleme:

```bash
python scripts/manual_page_edit_test.py
python scripts/manual_page_edit_test2.py
```

Görsel dönüşümleri:

```bash
python scripts/manual_image_conversion_test.py
```

Office → PDF:

```bash
python scripts/manual_office_to_pdf_test.py "test.docx" "test.pptx" "test.xlsx"
```

PDF sıkıştırma:

```bash
python scripts/manual_pdf_compression_test.py "C:\Test\test.pdf"
```

---

## 💻 Geliştirme Ortamı

### 1️⃣ Repository'yi klonla

```bash
git clone https://github.com/alperrte/pdf-reme.git
cd pdf-reme
```

### 2️⃣ Sanal ortam oluştur

Windows:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Bağımlılıkları yükle

```bash
python -m pip install -r requirements.txt
```

### 4️⃣ Veritabanını hazırla

```bash
alembic upgrade head
```

### 5️⃣ Testleri çalıştır

```bash
python -m pytest -v
```

### 6️⃣ Uygulamayı başlat

```bash
python start_app.py
```

> Kullanıcı arayüzü halen aktif geliştirme aşamasındadır.

---

## 🗂️ Yerel Veri Yapısı

Windows geliştirme ortamındaki güncel veri yapısı:

```text
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
```

Çöp kutusundaki dosyalar fiziksel olarak:

```text
Documents/PDF-REME/trash/
```

altında tutulur ve uygulama dışından Dosya Gezgini ile de erişilebilir.

Merge, Split, Page Edit, sıkıştırma, görsel ve Office dönüşümleri sonucunda oluşturulan dosyalar:

```text
Documents/PDF-REME/library/generated/
```

altında tutulur.

---

## 🗺️ Yol Haritası

Güncel odak, tamamlanan çekirdek altyapıyı masaüstü deneyimine taşımak ve ilk kararlı sürüme hazırlamaktır.

- [x] Yerel veri, kütüphane ve güvenli dosya yönetimi
- [x] Temel PDF araçları ve sayfa düzenleme backend'i
- [x] PDF ↔ görsel ve Office → PDF dönüşüm altyapısı
- [x] PDF sıkıştırma altyapısı
- [ ] Masaüstü arayüzü ve backend entegrasyonu
- [ ] Dağıtım paketleri ve ilk kararlı sürüm

---

## 🤝 Katkıda Bulunma

Katkıda bulunmak istersen:

1. Repository'yi fork et
2. Ayrı bir branch oluştur
3. Değişikliklerini geliştir
4. Testleri çalıştır
5. Pull Request aç

Proje halen V1 geliştirme sürecinde olduğu için mimari ve API'lerde değişiklikler olabilir.

---

## 📜 Lisans

PDF-REME **Apache License 2.0** altında lisanslanmıştır.

Detaylar için [`LICENSE`]\(LICENSE) dosyasını inceleyebilirsiniz.

---

## 👨‍💻 Geliştirici

<div align="center">

### Alper Temiz

**Yazılım Mühendisliği Öğrencisi • Full-Stack Developer • AI/ML Engineer**

PDF-REME — Read • Edit • Merge • Easily

<br>

**Belgeleriniz cihazınızda. İşlemleriniz kontrolünüzde.**

⭐ Projeyi faydalı bulursanız yıldız verebilirsiniz.

</div>
