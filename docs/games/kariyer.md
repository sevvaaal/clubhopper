# Kariyer yolu

**Durum:** Prototip hazır (`site/career.html`).

## Oyun
- Oyuncunun kulüpleri, en eskiden yeniye sırayla gösterilir.
  - Her satırda sezon aralığı, kulüp logosu ve maç sayısı bulunur.
  - Kariyerdeki boşluklar "… başka bir lig" olarak işaretlenir.
- Oyuncu adı yazılarak tahmin edilir; arama kutusu öneri listesi gösterir.
- Toplam **6 tahmin** hakkı var. Her yanlış tahminde bir ipucu daha açılır, sırasıyla:
  1. mevki
  2. uyruk
  3. doğum yılı
  4. baş harfler
  5. fotoğraf

## Veri
- Kariyer, `game.json`'daki takım-sezonlardan çıkarılır. Aynı kulüpte arka arkaya oynanan sezonlar tek satırda birleşir.
- Mevki, oyuncunun maç kadrolarında en sık göründüğü yerdir (`matches.json` → `positions`). Yaklaşık 18 bin oyuncu için mevki var.
- **Havuz:** en az 3 farklı kulüpte oynamış oyunculardan, dakikası en yüksek 1500 kişi.

## Bilinen sınırlar
- Kapsam yalnızca 6 lig, Şampiyonlar Ligi ve Avrupa Ligi. 2010 öncesi ve başka ligler (Hollanda, Portekiz, Suudi Arabistan…) görünmez, bu yüzden bazı kariyerler eksik kalır.
- Kiralıkla gidip dönen oyuncuda aynı kulüp iki ayrı satırda görünür; bu doğru davranış.

## Yapılacaklar
- [ ] **Eksik kariyerler:** API'nin `/transfers` verisiyle doldurulabilir. Yalnızca kulüp adı gösterilir, maç sayısı olmaz. 700 kulübün transferleri zaten indirildi.
- [ ] **Tahmin geri bildirimi:** her yanlış tahminde yaşın büyük ya da küçük olduğu, uyruğun aynı olup olmadığı gösterilir (Wordle tarzı).
- [ ] **Zorluk:** az kulüp ve ünlü oyuncu kolay; çok kulüp ve az tanınan oyuncu zor.
- [ ] **Kulüp sayısı:** 1–2 kulüplü oyuncular havuza alınmaz, çünkü cevap çok belirsiz kalır.
