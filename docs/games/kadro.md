# Kadroyu tamamla

**Durum:** Prototip hazır (`site/lineup.html`).

## Oyun
- Bir maçın skoru, turnuvası, turu ve tarihi verilir. Sorulan: takımlardan biri bu maça hangi 11'le çıktı?
- Saha üzerinde 11 boş yer bulunur. Her yerde forma numarası yazar.
- Oyuncu adı yazılır:
  - Kadrodaysa yerine oturur.
  - Kadroda değilse yanlış sayısı artar.
- Bir yere tıklamak o oyuncunun uyruğunu ve baş harflerini gösterir; ipucu sayısına eklenir.
- 11 oyuncunun hepsi bulunursa oyun kazanılır. Pes et düğmesi kadronun tamamını gösterir.

## Veri
Kaynak `pipeline/build_matches.py`, çıktısı `site/data/matches.json` (2,7 MB). Seçilen 3375 "önemli maç":
- Her ligin en çok Avrupa kupası oynamış 6 kulübünün kendi aralarındaki lig maçları
- Şampiyonlar Ligi son 16 ve sonrası
- Avrupa Ligi çeyrek final ve sonrası
- Türk kulüplerinin gruplardan itibaren bütün Avrupa maçları

Dizilişin kaynağı maça göre değişir:
- **2016 ve sonrası:** API'nin saha ızgarası (grid) kullanılır, gerçek diziliş görünür.
- **Daha eski maçlar:** ızgara yok. Oyuncular kaleci, defans, orta saha ve forvet sırasıyla dizilir. Mevki maçtan alınır, yoksa oyuncunun her zamanki mevkisi kullanılır.

## Bilinen sınırlar
- Eski maçlarda mevki bilgisi olmadığı için diziliş bazen gerçeğe uymaz (örneğin 2-7-1).
- Konyaspor gibi Avrupa'ya sık giden orta sıra kulüpler "büyük" listesine girebiliyor.

## Yapılacaklar
- [ ] **Yanlış hakkı:** sınırsız yerine en fazla 5.
- [ ] **Zorluk:** final ve derbi kolay; eski ve az bilinen maçlar zor.
- [ ] **Büyük kulüp listesi:** algoritma yerine elle düzenlenebilir.
- [ ] **Yedekler:** isteğe bağlı olarak oyuna girenler de sorulabilir.
- [ ] **Puanlama:** bulunan oyuncu sayısı, yanlışlar ve ipuçlarından hesaplanır.
