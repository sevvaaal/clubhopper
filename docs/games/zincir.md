# Zincir

**Durum:** Prototip hazır (`site/chain.html`).

## Oyun
- Bir başlangıç ve bir hedef oyuncu verilir. Oyuncu, ortak takım-sezonlar üzerinden takım arkadaşından takım arkadaşına geçerek hedefe ulaşmaya çalışır.
  - Örnek: Icardi → Galatasaray 23/24 → Muslera.
- **Hamle:** Önce mevcut oyuncunun takım-sezonlarından biri seçilir, sonra o kadrodan bir oyuncu. Hamleler tamamen tıklanarak yapılır.
- Geri al ve Pes et düğmeleri var. Oyun bitince en kısa zincir gösterilir.

## Veri
- `game.json` içindeki takım-sezonlar kullanılır.
- Bir oyuncu, ligde ya da Avrupa kupalarında en az 1 dakika oynadığı takım-sezona sayılır.
- Kaynak maç kadrolarıdır.

## Bulmaca üretimi
- Başlangıç ve hedef, en çok dakika almış ilk 250 oyuncudan seçilir.
- En kısa yol en az 3 adım olmalı; BFS ile kontrol edilir.
- Günlük bulmaca tarih seed'iyle üretilir, herkese aynı çıkar.

## Yapılacaklar
- [ ] **Zorluk seviyeleri:** kolay, orta ve zor. Yol uzunluğuna ve oyuncuların tanınırlığına göre belirlenir.
- [ ] **Puanlama:** adım sayısı ile en kısa yol karşılaştırılır. Seri (streak) bilgisi localStorage'da tutulur.
- [ ] **Uzun kadrolar:** kadroda arama ve mevkiye göre gruplama.
- [ ] **Paylaşım:** emoji özetiyle sonuç paylaşma.
- [ ] **Günlük bulmacalar:** yayından önce sabitlenir (`daily/{yıl}.json`), veri güncellense de değişmez.
- [ ] **Veri boyutu:** `game.json` 6,6 MB; yayında bölünmesi gerekiyor.
