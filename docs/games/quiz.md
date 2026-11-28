# Maç quiz'i

**Durum:** Canlı anlatım sürümü hazır (`site/quiz.html`, 28 Kasım).

## Oyun
- "Bu hangi maç?" diye sorulur ve 4 seçenek verilir. Turnuva ve sezon baştan görünür.
- Maç **canlı yazılı anlatım** gibi akar:
  - saat ilerler
  - her olay dakikası gelince harf harf yazılır
  - skor tabelası olaylarla birlikte güncellenir
- Olaylar dakika sırasıyla gelir:
  - goller, asistler, penaltı golleri, kendi kalesine goller
  - kaçan penaltılar
  - sarı ve kırmızı kartlar (sebebiyle, ikinci sarı ayrıca belirtilir)
  - oyuncu değişiklikleri
  - VAR kararları
  - başlama düdüğü, devre arası, uzatmalar ve maç sonu
- Maç bitince sırasıyla şunlar gelir:
  1. penaltı atışlarının sonucu (varsa)
  2. istatistikler (topla oynama, şut, isabetli şut, korner)
  3. tur, tarih ve stat
  4. teknik direktörler
- Oyuncu istediği an şık seçebilir. Doğru cevapta anlatımın kalanı hemen açılır.
- "Duraklat" ve "Hızlandır" düğmeleri var. Hareketi azalt ayarı açıksa yazılar animasyonsuz gelir.
- **Puan:** 5'ten başlar. Şu durumlarda 1 puan düşer:
  - 30. dakika geldiğinde
  - 60. dakika geldiğinde
  - maç bittiğinde
  - her yanlış şıkta

  3 yanlış cevapta ya da puan 0'a düşünce oyun biter.

## Veri
- Kaynak `matches.json`'daki önemli maçlardır (`pipeline/build_matches.py`). Her maçta artık bütün olaylar ve 4 istatistik var. Dosya 4,1 MB, gzip ile ~660 KB.
- Olay biçimi: `[dakika, uzatma, taraf, oyuncu, tür, diğer oyuncu, not]`.
  - **Oyuncu:** oyunda bilinen oyuncuysa id, değilse adı.
  - **Diğer oyuncu:** gollerde asist yapan, değişiklikte oyuna giren. Değişiklikte "oyuncu" alanı çıkan oyuncudur.
  - **Not:** kart sebebi.
  - **Kendi kalesine gol:** taraf, golün yazıldığı takımdır. Ham veriyle karşılaştırınca 859 maçın 858'inde skor tuttu.
- API ikinci sarıyı ayrı göndermiyor, düz kırmızı kart olarak gönderiyor. Site bunu aynı oyuncunun daha önce sarı görmesinden anlıyor.
- Penaltı atışlarının tek tek vuruşları alınmaz, yalnızca sonucu gösterilir.
- Havuz: en az 6 olayı olan maçlar (3328 maç).
- **Şıklar:** her seferinde aynı turnuva ve sezondan seçilir, mümkünse cevapla ortak bir kulüp içerir. Aynı iki kulübün başka bir maçı şık olarak gelmez.

## Bilinen sınırlar
- Teknik direktör adı eski maçlarda çoğunlukla yok.
- 3375 maçın 877'sinde istatistik yok.
- Tur adları API'den geldiği gibi İngilizce ("Regular Season - 15").
- Oyunda olmayan oyuncuların adı API'deki hâliyle uzun yazılabiliyor ("Robin van Persie" ile "A. Valencia" yan yana).
- VAR penaltı kararlarında hangi takımın lehine olduğu kesin bilinmediği için taraf yazılmıyor.

## Yapılacaklar
- [ ] **Şıksız mod:** iki takım da arama kutusundan seçilir. Daha zor olur.
- [ ] **Başka soru tipleri:**
  - skoru tahmin et
  - golü kim attı
  - bu maçta hangi oyuncu oynamadı
- [ ] **Tur adlarını çevir:** Türkçe ve İngilizce, "15. hafta", "Çeyrek final" gibi.
- [ ] **Puanlama:** günlük skor ve seri.
