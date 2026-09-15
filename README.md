<div align="center">

<img src="src/pdf_reme/resources/images/pdf-reme-logo.jpeg" alt="PDF-REME Logo" width="260" />

<br><br>

<img src="src/pdf_reme/resources/images/1.png" alt="PDF-REME Hero" width="100%" />

# PDF-REME

### Read • Edit • Merge • Easily

**Windows ve Linux için çevrimdışı, açık kaynak PDF ve belge yönetim aracı.**

Belgelerinizi görüntüleyin, düzenleyin, birleştirin, bölün ve dönüştürün —  
**dosyalarınızı üçüncü taraf servislere yüklemeden, kendi bilgisayarınızda.**

<p>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/UI-PySide6-41CD52?logo=qt&logoColor=white" />
  <img src="https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/Tests-191%20Passing-success" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-5A5A5A" />
  <img src="https://img.shields.io/badge/License-Apache--2.0-blue" />
  <img src="https://img.shields.io/badge/Status-Active%20Development-orange" />
</p>

</div>

---

## PDF-REME Nedir?

**PDF-REME**, PDF ve belge işlemlerini mümkün olduğunca kullanıcının kendi bilgisayarında gerçekleştirmek üzere geliştirilen ücretsiz ve açık kaynak bir masaüstü uygulamasıdır.

Temel hedef; PDF ve benzeri belgeleri işlemek için web tabanlı araçlara, bulut servislerine veya üçüncü taraf dönüştürücülere dosya yükleme ihtiyacını azaltan, sade ve güvenli bir **local-first** çalışma alanı sunmaktır.

> **Local-first:** Belgeleriniz varsayılan olarak cihazınızda kalır ve işlemler yerel olarak gerçekleştirilir.

---

## Ürün Vizyonu

<div align="center">

<img src="src/pdf_reme/resources/images/2.png" alt="PDF-REME Ana Sayfa Konsepti" width="100%" />

</div>

> Yukarıdaki görsel, PDF-REME için hazırlanan **arayüz konseptidir**. PySide6 tabanlı gerçek arayüz geliştirme sürecinde bu tasarım dili referans alınacaktır.

PDF-REME V1 ile hedeflenen deneyim:

- PDF dosyalarını görüntüleme
- PDF birleştirme ve bölme
- Sayfa sıralama, silme, döndürme ve çoğaltma
- İki sayfanın yerini değiştirme
- Başka PDF'den sayfa ekleme
- Seçili sayfaları yeni PDF olarak dışa aktarma
- JPG / JPEG / PNG → PDF
- DOC / DOCX → PDF
- PPT / PPTX → PDF
- Yerel belge kütüphanesi
- Favoriler ve son kullanılanlar
- Çöp kutusu ve geri yükleme
- Undo / Redo
- Türkçe öncelikli, i18n'e hazır yapı
- İlerleyen aşamalar için tema altyapısı

> Excel (`XLS`, `XLSX`) dönüşümü V1 kapsamına dahil değildir.

---

## Kütüphane Konsepti

<div align="center">

<img src="src/pdf_reme/resources/images/3.png" alt="PDF-REME Kütüphane Konsepti" width="100%" />

</div>

PDF-REME kütüphanesi, içe aktarılan ve uygulama tarafından oluşturulan belgeleri tek bir yerden yönetmeyi hedefler.

Mevcut backend altyapısında:

- **Yüklenenler** ve **Oluşturulanlar** ayrımı yapılabilir,
- favori belgeler takip edilebilir,
- son kullanılan belgeler `last_opened_at` üzerinden sıralanabilir,
- belgeler çöp kutusuna taşınabilir ve geri yüklenebilir,
- Merge, Split ve sayfa düzenleme işlemlerinden üretilen dosyalar `generated` kütüphanesine kaydedilebilir,
- oluşturulan belgeler için SHA-256, dosya boyutu, sayfa sayısı ve üretim türü metadata olarak tutulabilir,
- fiziksel dosyalar dosya sisteminde, metadata bilgileri SQLite üzerinde tutulur.

Planlanan kullanıcı arayüzü yapısı:

- **Yüklenenler**
- **Oluşturulanlar**
- Favoriler
- Son kullanılanlar
- Arama ve filtreleme
- Dosya türüne göre ayrım
- Çöp kutusu
- Yerel metadata yönetimi

---

## PDF Düzenleyici Konsepti

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

Planlanan devam özellikleri:

- [ ] Save / Save As kullanıcı akışı
- [ ] PySide6 arayüzünde drag & drop sayfa sıralama

> V1 kapsamında PDF içindeki mevcut metin ve nesnelerin Word benzeri biçimde düzenlenmesi hedeflenmemektedir.

---

## Güvenli İçe Aktarma Akışı

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

## Çöp Kutusu ve Güvenli Silme Akışı

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

## PDF Birleştirme (Merge)

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

## PDF Sayfa Ayırma ve Bölme (Split)

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

## Sayfa Düzenleme Backend'i

PDF-REME'nin sayfa tabanlı düzenleme altyapısındaki temel backend işlemleri ve Undo / Redo geçmişi tamamlanmıştır.

### Sayfa sıralama

`reorder_pages()` verilen yeni sırayı birebir uygular.

```text
1 2 3 4 5
↓
5 1 3 2 4
```

Yeni sıranın belgedeki tüm sayfaları tam olarak bir kez içermesi zorunludur. Eksik veya tekrar eden sıralamalar reddedilir.

### İki sayfanın yerini değiştirme

`swap_pages()` yalnızca belirtilen iki sayfanın yerini değiştirir ve mevcut `reorder_pages()` altyapısını tekrar kullanır.

```text
2 ↔ 5

1 2 3 4 5
↓
1 5 3 4 2
```

### Sayfa silme

`delete_pages()` seçilen sayfaları yeni PDF çıktısından kaldırır.

```text
Sil: 2,4

1 2 3 4 5
↓
1 3 5
```

Tüm sayfaların aynı işlemde silinmesine izin verilmez.

### Sayfa döndürme

`rotate_pages()` seçilen sayfaları 90 derecenin katlarıyla döndürür. Negatif açılar desteklenir ve çıktıdaki dönüş açısı normalize edilir.

### Sayfa çoğaltma

`duplicate_pages()` seçilen her sayfanın bir kopyasını orijinal sayfanın hemen arkasına ekler.

### Başka PDF'den sayfa ekleme

`insert_pages()` başka bir PDF'den seçilen sayfaları, seçim sırasını koruyarak belgenin başına veya belirtilen sayfanın arkasına ekler.

### Boş sayfa ekleme

`insert_blank_page()` referans sayfanın boyutlarını kullanarak belgenin başına veya belirtilen sayfanın arkasına boş bir sayfa ekler.

### Undo / Redo geçmişi

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

İlk script reorder, swap ve delete işlemlerini; Gün 11 script'i ise rotate, duplicate, başka PDF'den sayfa ekleme, boş sayfa ekleme ve Undo / Redo geçmişini gerçek PDF'lerle doğrular. Her iki akışta da kaynak dosyaların değişmediği ve generated DB kayıtlarının oluştuğu kontrol edilir.

---

## Aktif Geliştirme

<div align="center">

<img src="src/pdf_reme/resources/images/6.png" alt="PDF-REME Aktif Geliştirme" width="100%" />

</div>

PDF-REME şu anda aktif olarak geliştirilmektedir.

Backend-first yaklaşımıyla önce çekirdek iş akışları ve güvenli veri yönetimi tamamlanmakta, ardından Stitch ile hazırlanan tasarım dili PySide6 arayüzüne uygulanacaktır.

**Gün 11 tamamlandı:** Sayfa döndürme, çoğaltma, başka PDF'den sayfa ekleme, boş sayfa ekleme ve Undo / Redo geçmişi backend'e eklendi.

### Güncel checkpoint

```text
191 passed
0 failed
```

Şu anda tamamlanan temel altyapılar:

- [x] SQLite + SQLAlchemy veri katmanı
- [x] Repository pattern
- [x] Alembic migration altyapısı
- [x] Transaction / rollback yönetimi
- [x] SHA-256 hesaplama
- [x] Duplicate detection
- [x] PDF ve görsel doğrulama
- [x] DOCX / PPTX temel OOXML doğrulama
- [x] Güvenli kütüphane kopyalama
- [x] Gerçek PDF import akışı
- [x] Metadata veritabanı kaydı
- [x] Kütüphane servisleri
- [x] Yüklenenler / Oluşturulanlar ayrımı
- [x] Favoriler
- [x] Son kullanılan belgeler
- [x] Çöp kutusuna taşıma
- [x] Geri yükleme
- [x] Kalıcı silme
- [x] Çöp kutusunu toplu temizleme
- [x] 30 günlük çöp kutusu retention kontrolü
- [x] Gerçek dosya ile trash / restore / permanent delete testi
- [x] PDF Merge backend'i
- [x] PDF Merge generated kütüphane entegrasyonu
- [x] PDF Split / seçili sayfa çıkarma
- [x] İkiye / dörde / N parçaya bölme
- [x] Özel sayfa grupları
- [x] Sayfa reorder
- [x] Sayfa swap
- [x] Sayfa delete
- [x] Sayfa rotate
- [x] Sayfa duplicate
- [x] Başka PDF'den sayfa ekleme
- [x] Boş sayfa ekleme
- [x] Undo / Redo işlem geçmişi
- [x] Merge / Split / Page Edit gerçek dosya testleri
- [x] Otomatik unit + integration testleri

---

## Güvenlik ve Yerel Çalışma Yaklaşımı

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

## Desteklenen Dosya Türleri

### İçe aktarma

`PDF` • `DOC` • `DOCX` • `PPT` • `PPTX` • `JPG` • `JPEG` • `PNG`

### Mevcut PDF işlemleri

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

### V1 dönüşüm hedefleri

- JPG / JPEG / PNG → PDF
- DOC / DOCX → PDF
- PPT / PPTX → PDF

---

## Teknoloji Yığını

| Alan | Teknoloji |
|---|---|
| Programlama dili | Python 3.10+ |
| Masaüstü UI | PySide6 + Qt Widgets |
| Stil | QSS |
| PDF işlemleri | pypdf |
| PDF görüntüleme | PySide6 QtPdf |
| Görsel işlemleri | Pillow |
| Veritabanı | SQLite |
| ORM | SQLAlchemy |
| Migration | Alembic |
| Office → PDF | LibreOffice Runtime *(planlanan entegrasyon)* |
| Test | pytest + pytest-qt |
| Kod kalitesi | Ruff |
| Lisans | Apache License 2.0 |

---

## Mimari

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

---

## Testler

Tüm mevcut testleri çalıştırmak için:

```bash
python -m pytest -v
```

Güncel geliştirme checkpoint'i:

```text
191 passed
0 failed
```

Testlerde örnek olarak şu senaryolar doğrulanmaktadır:

- başarılı repository işlemleri,
- migration upgrade / downgrade,
- commit / rollback,
- kaynak dosyanın korunması,
- büyük dosyaların parça parça hashlenmesi,
- bozuk PDF ve görsel reddi,
- sahte DOCX / PPTX reddi,
- duplicate detection,
- güvenli `.part` kopyalama,
- veritabanı hatasında fiziksel dosya temizliği,
- gerçek import akışı,
- yüklenen / oluşturulan belge ayrımı,
- favori açma / kapama,
- son kullanılan belgelerin sıralanması,
- dosyanın fiziksel çöp kutusuna taşınması,
- çöp kutusundan geri yükleme,
- restore sırasında isim çakışmasının güvenli çözülmesi,
- çöp kutusu dışındaki dosyaların kalıcı silinmesinin engellenmesi,
- fiziksel dosya daha önce elle silinmişse DB kaydının temizlenmesi,
- çöp kutusunun toplu temizlenmesi,
- 29 günlük kaydın korunması,
- tam 30 günlük ve daha eski kayıtların temizleme kapsamına alınması,
- Alembic migration upgrade / downgrade regresyonu,
- Merge işleminde kullanıcı sırasının korunması,
- Merge işleminde kaynak PDF'lerin değişmemesi,
- Merge hata durumunda yarım çıktının temizlenmesi,
- Split sayfa seçim ifadelerinin doğru ayrıştırılması,
- Split işleminde seçili sayfaların doğru sırada çıkarılması,
- iki / dört / N parçaya bölmede hiçbir sayfanın kaybolmaması,
- özel sayfa gruplarının ayrı çıktılar oluşturması,
- reorder işleminde tüm sayfaların tam bir kez bulunması,
- swap işleminde yalnızca seçilen iki sayfanın yer değiştirmesi,
- delete işleminde seçilen sayfaların kaldırılması,
- bütün sayfaların silinmesinin engellenmesi,
- yalnızca seçilen sayfaların 90° katlarıyla döndürülmesi,
- seçilen sayfaların doğru konumlarda çoğaltılması,
- başka bir PDF'den seçilen sayfaların istenen sırayla eklenmesi,
- belgenin başına veya belirtilen konuma boş sayfa eklenmesi,
- Undo / Redo durum geçişleri ve yeni işlemde redo zincirinin temizlenmesi,
- generated dosyalarda aynı isim çakışmasının güvenli çözülmesi,
- generated dosya adlarında path traversal girişlerinin reddedilmesi,
- generated DB kayıt hatasında fiziksel çıktının temizlenmesi,
- gerçek Merge / Split / Page Edit akışları,
- genel regresyon kontrolleri.

### Manuel gerçek dosya testleri

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

---

## Geliştirme Ortamı

### Repository'yi klonla

```bash
git clone https://github.com/alperrte/pdf-reme.git
cd pdf-reme
```

### Sanal ortam oluştur

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

### Bağımlılıkları yükle

```bash
python -m pip install -r requirements.txt
```

### Veritabanını hazırla

```bash
alembic upgrade head
```

### Testleri çalıştır

```bash
python -m pytest -v
```

### Uygulamayı başlat

```bash
python start_app.py
```

> Kullanıcı arayüzü halen aktif geliştirme aşamasındadır.

---

## Yerel Veri Yapısı

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

Merge, Split ve Page Edit sonucunda oluşturulan yeni PDF'ler:

```text
Documents/PDF-REME/library/generated/
```

altında tutulur.

---

## Yol Haritası

### Backend / Core

- [x] Proje ve katmanlı mimari temeli
- [x] SQLite + SQLAlchemy
- [x] Repository altyapısı
- [x] Alembic migration
- [x] Transaction yönetimi
- [x] Dosya doğrulama
- [x] SHA-256 / duplicate detection
- [x] Güvenli import
- [x] Kütüphane servisleri
- [x] Favoriler / Son kullanılanlar
- [x] Çöp kutusu / Restore
- [x] Kalıcı silme / Çöp kutusunu temizleme
- [x] 30 günlük çöp kutusu retention kontrolü
- [x] PDF Merge
- [x] PDF Split
- [x] Seçili sayfaları dışa aktarma
- [x] Sayfa yeniden sıralama
- [x] İki sayfanın yerini değiştirme
- [x] Sayfa silme
- [x] Sayfa döndürme
- [x] Sayfa çoğaltma
- [x] Başka PDF'den sayfa ekleme
- [x] Boş sayfa ekleme
- [x] Undo / Redo
- [ ] Görsellerden PDF
- [ ] Office → PDF
- [ ] Autosave / Session recovery
- [ ] Startup maintenance / 30 günlük trash cleanup bağlantısı
- [ ] Backend final E2E / kapanış

### Frontend

- [x] Görsel tasarım dili / konsept çalışmaları
- [ ] Stitch ile final ekran tasarımları
- [ ] PySide6 uygulama shell'i
- [ ] Ana Sayfa
- [ ] Kütüphane
- [ ] Çöp Kutusu
- [ ] PDF Viewer
- [ ] Merge ekranı
- [ ] Split ekranı
- [ ] PDF Düzenleyici
- [ ] Dönüştürme ekranları
- [ ] Tema altyapısı
- [ ] Backend entegrasyonu

### Release

- [ ] Windows Setup
- [ ] Windows Portable
- [ ] Linux paketi
- [ ] Final README / ekran görüntüleri
- [ ] GitHub Release

---

## Sıradaki Geliştirme Aşamaları

Backend'in ana omurgası tamamlanmış durumdadır. Sonraki geliştirme sırası genel olarak:

```text
JPG / PNG → PDF
        ↓
Word / PowerPoint → PDF
        ↓
Autosave / Recovery / Logging / Startup bakım işleri
        ↓
Backend final E2E ve regresyon
        ↓
Stitch UI tasarımı
        ↓
PySide6 frontend
        ↓
Backend entegrasyonu
        ↓
Paketleme ve Release
```

---

## V1 Kapsamı Dışında

İlk sürümde yer alması planlanmayan başlıca özellikler:

- PDF içindeki mevcut metin ve nesneleri Word benzeri düzenleme
- OCR
- Excel → PDF
- Elektronik imza
- Gelişmiş anotasyon
- Form düzenleme
- Bulut senkronizasyonu
- Kullanıcı hesabı
- Mobil uygulama
- macOS paketleme
- Otomatik güncelleme

---

## Katkıda Bulunma

Katkıda bulunmak istersen:

1. Repository'yi fork et
2. Ayrı bir branch oluştur
3. Değişikliklerini geliştir
4. Testleri çalıştır
5. Pull Request aç

Proje halen V1 geliştirme sürecinde olduğu için mimari ve API'lerde değişiklikler olabilir.

---

## Lisans

PDF-REME **Apache License 2.0** altında lisanslanmıştır.

Detaylar için [`LICENSE`](LICENSE) dosyasını inceleyebilirsiniz.

---

## Geliştirici

<div align="center">

### Alper Temiz

**Yazılım Mühendisliği Öğrencisi • Full-Stack Developer • AI/ML Engineer**

PDF-REME — Read • Edit • Merge • Easily

<br>

**Belgeleriniz cihazınızda. İşlemleriniz kontrolünüzde.**

⭐ Projeyi faydalı bulursanız yıldız verebilirsiniz.

</div>
