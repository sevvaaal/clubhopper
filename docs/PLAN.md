# Clubhopper — Proje Planı

Son güncelleme: 27 Kasım 2026. Bu belge kararları ve yol haritasını tek yerde tutar; karar değiştikçe güncellenir.

## 1. Kararlar (netleşti)

| Konu | Karar |
|---|---|
| İlk oyun | **Zincir**: oyuncudan oyuncuya, ortak takım-sezonlar üzerinden (Icardi → Galatasaray 23/24 → Muslera). Hamleler tıklanarak seçilir. Diğer üç oyun sonra. |
| Oyun modu | **Günlük bulmaca** (herkese aynı) **+ serbest mod** (sınırsız rastgele). |
| Dil | **TR + EN**, varsayılan Türkçe. |
| Kapsam | Süper Lig + büyük 5 lig, milli takım yok. Sezonlar veri geldikçe açılır, diğerleri "yakında". |
| Ekstra turnuvalar | Pro ayında **Şampiyonlar Ligi** ve **Avrupa Ligi** de çekilir. Türkiye Kupası, 1. Lig, Eredivisie ve Portekiz yok. |
| Kadro eşiği | Oyuncu, ligde ya da Avrupa kupalarında **en az 1 dakika** oynadığı takım-sezona aittir. Kaynak maç kadroları (ilk 11, oyuna girenler). Şampiyonlar Ligi ve Avrupa Ligi ayrı düğüm değil, kulübün o sezonuna eklenir. |
| Altyapı | **Statik site**: önceden üretilmiş JSON + tarayıcıda graf. Sunucu ve veritabanı yok. |
| Pro plan | **Alındı: 26 Kasım 2026, bitiş 26 Aralık 2026 17:13 (TR).** Günde 7500 istek. Hatırlatmalar 21 ve 25 Aralık 10:00'da. |
| Sezonlar (Pro) | Büyük 5 lig 2010/11–2025/26, Süper Lig ve Şampiyonlar Ligi 2011/12–2025/26, Avrupa Ligi 2014/15–2025/26 (API bunlardan eskisini vermiyor). Devam eden 2026/27 şimdilik yok. Hepsinde kadro, ilk 11 ve maç olayları var. |
| Görseller | Takım logosu ve oyuncu fotoğrafı küçültülüp kendi sitemizden sunulur. Yoksa baş harf avatarı kullanılır. Hakkında sayfasında kaynak/telif notu olur. |
| Tasarım | Logo hazır (taslak B). Site tasarımına henüz başlanmayacak. |

## 2. Mimari

```
API-Football ──collect.py──▶ data/raw/       (ham yanıtlar, gitignore, bir kez çekilir)
                               │
                         build.py (yeni)
                               ▼
                         data/build/         (oyunun okuduğu küçük, temiz JSON)
                               │
                         images.py (yeni)
                               ▼
                         site/public/img/    (64 px logo, 96 px foto, webp)
                               │
                            site/ (statik)   ──▶ Render Static Site (render.yaml)
```

Pipeline üç ayrı adımdan oluşur ve her biri tekrar çalıştırılabilir:

1. **collect**: API'den ham veriyi indirir. Kaldığı yerden devam eder. `--plan free|pro` ile limitler değişir.
2. **build**: Ham veriyi oyun verisine çevirir. API'ye hiç istek atmaz, istediğimiz kadar yeniden çalıştırabiliriz.
3. **images**: Logo ve fotoğrafları indirir, küçültür, yerelde saklar.

### Oyun verisi (data/build/) taslağı

- `teams.json`: id, ad, kısa ad, ülke, logo yolu
- `players.json`: id, ad, kısa ad, uyruk, doğum yılı, foto yolu
- `seasons/{lig}-{yıl}.json`: o lig-sezondaki takımlar ve her takımın oyuncu id'leri. Yalnızca en az 1 maça çıkanlar alınır; maç ve dakika sayısı da tutulur (zorluk/ünlülük için).
- `index.json`: hangi lig-sezonlar açık, hangileri "yakında"
- `daily/{yıl}.json`: önceden üretilmiş günlük bulmacalar (başlangıç, hedef, en kısa yol uzunluğu)

Kabaca hesap: tam kapsamda ~2000 takım-sezon, ~25 bin oyuncu, ~60 bin oyuncu-takım bağı var. Sıkıştırılmış hâli birkaç MB eder, statik site için sorun değil. Gerekirse sezon dosyaları tembel (lazy) yüklenir.

## 3. Zincir oyunu — kurallar taslağı

- **Durak**: oyuncu. İki oyuncu, ikisinin de en az 1 maça çıktığı her takım-sezonla bağlıdır.
- Bir başlangıç ve bir hedef oyuncu verilir. İkisi de çok dakika almış, tanınan oyunculardan seçilir.
- **Hamle**: tamamen tıklayarak yapılır. Önce mevcut oyuncunun takım-sezonları buton olarak çıkar, birini seçince o kadronun oyuncuları çıkar, sonra biri seçilir.
- **Zorluk**: en kısa yolun uzunluğu (şimdilik en az 3 adım) ve oyuncuların tanınırlığı.
- **Günlük bulmaca**: tarih seed'iyle seçilir, herkes aynı bulmacayı görür.
- **Serbest mod**: rastgele çift seçilir; çözülebilir olduğu BFS ile garanti edilir.
- İlerleme ve seri (streak) bilgisi tarayıcıda (localStorage) tutulur, hesap sistemi yok.

## 4. Yol haritası

### Faz 1 — Ücretsiz veriyle Zincir (şimdi)
- [ ] `collect.py` ile 6 ligin 2022–2024 kadrolarını topla. Yaklaşık 6 × 3 × 40 = 720 istek, günde ~95 istekle ~8 gün sürer. Durum: Süper Lig 2024 tamam, 2023 yarım.
- [ ] Bundesliga ve Ligue 1 kapsama (coverage) kontrolü
- [ ] `build.py`: kadro verisinden takım-sezon grafı, "en az 1 maç" filtresi
- [ ] Zincir mantığı: BFS, çözülebilirlik, zorluk puanı, günlük bulmaca üretimi
- [ ] Site iskeleti: veri yükleme ve oyun akışı. Tasarım bu fazın sonunda ayrıca konuşulacak.
- [ ] TR/EN metin dosyaları
- [ ] Hakkında sayfası + veri/görsel telif notu

Not: Ücretsiz planda takım başına en fazla 3 sayfa (60 oyuncu) alınabiliyor. Bu kadro için genelde yeter; taşan takımlar build sırasında raporlanır.

### Faz 2 — Pro ayı (ilk oyun yayına hazır olunca)
- [ ] `collect.py --plan pro`: 2010–2025 sezonları; maç detayları `/fixtures?ids=` ile 20'şerli; `/players` için sayfa sınırı yok; hız ayarlanabilir (~100 istek/dk)
- [ ] `images.py`: logo (64 px) ve foto (96 px), webp formatında
- [ ] Tam kapsam: ~95 lig-sezon ≈ 5800 istek, ilk güne sığar
- [x] Tam çekim bitti (27 Kasım): 122 turnuva-sezon, ~41.500 maç, 700 kulübün transferleri; ~10.400 istek, 1,5 GB ham veri. Şampiyonlar Ligi ve Avrupa Ligi kulübün sezonuna eklendi.
- [ ] Ham veri yedeği: Pro bitince veri bizde kalır

### Faz 3 — Diğer oyunlar (prototipler hazır, 27 Kasım)
Her oyunun ayrıntılı planı `docs/games/` altında: [zincir](games/zincir.md), [kariyer](games/kariyer.md), [kadro](games/kadro.md), [quiz](games/quiz.md). Site ana sayfası oyun menüsü oldu; maç verisi `pipeline/build_matches.py` ile üretiliyor.
1. **Kariyer yolu**: takım-sezonlardan kariyer; eksik kısımlar ileride `/transfers` ile tamamlanabilir
2. **Kadroyu tamamla**: önemli maçların ilk 11'leri ve saha dizilişi
3. **Maç quiz'i**: ipuçlarından maçı bulma (gol dakikaları, golcüler, tur, stat)

## 5. Açık sorular

1. **Kariyer yolu kaynağı**: API-Football `/transfers` mı, Wikidata mı, ikisi birden mi? (Wikidata'daki Türk kulüp QID'leri ayrıca düzeltilmeli.)
2. **Alan adı**: Yayın yeri Render (statik site, 28 Kasım). Özel alan adı olacak mı?
3. **Sezon açılış sırası**: Faz 1'de 2022–2024 birlikte mi açılsın, yoksa önce sadece 2024 mü?
