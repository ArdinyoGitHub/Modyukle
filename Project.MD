# mcmodplan (mod yayınlama otomasyonu)

## Proje ne hakkında
MCreator ile yapılan modları tek komutla CurseForge + Modrinth + GitHub Releases'e yüklemek. Nexus elle kalıyor. MCreator `build.gradle`'ı ezdiği için sistem modun dışında, bağımsız bir Gradle projesi (`mod-publish-plugin` 2.2.1) olarak duruyor.

## Katedilen yol
- 2026-11-13: plan ve `yukleyici/` kuruldu. fish komutu `modyukle <platform> <proje> <jar> [--prova] [--incele]`; `modyukle.py` jar içindeki `neoforge.mods.toml`'dan metadata okur, yoksa Modrinth taslağı ve GitHub reposu oluşturur, CF Project ID'sini sorar.
- Ayarlar: `yukleyici/modlar/<modid>/ayarlar.properties` + `changelog.txt`; sayfa açıklamaları `aciklamalar/<proje>.txt`.
- İlk gerçek yükleme: Ardinyo's Biomes 2.0.1 → Modrinth taslağı `fWoDggyV`.
- 2026-11-15: Modrinth sürüm ortamı (`ortam=`) PATCH ile ayarlanıyor, taslak projeyi incelemeye gönderme (`--incele`) eklendi.
- 2026-11-22: GUI eklendi — `yukleyici/modyukle_gui.py` (PyQt6), menüde "Modyukle" (`~/.local/share/applications/modyukle.desktop`). modyukle.py'yi QProcess ile çalıştırır; `MODYUKLE_GUI=1` iken `sor()` soruyu `\x1eSOR {json}` satırı olarak basar, GUI pencere açıp cevabı stdin'e yazar. Changelog / ayarlar.properties / aciklamalar düzenlenebilir; tokenlar ortamda yoksa fish'ten okunur. Değişiklik öncesi yedek: `modyukle.py.yedek`. Prova akışı GUI'den test edildi; gerçek yükleme GUI'den henüz denenmedi.
- 2026-11-22: GUI'ye API anahtarı penceresi eklendi (Ayarlar → API anahtarları, Ctrl+,): Modrinth/CurseForge anahtarları fish evrensel değişkenine yazılır (terminaldeki modyukle ile ortak), anahtar eksikse ilk açılışta bir kez sorulur (QSettings `api_soruldu`). Prova modu artık ayarlar.properties'i bitince eski hâline döndürüyor (eskiden sahte CF id kalıyordu).
- 2026-11-22: GUI çok dilli: varsayılan İngilizce, Ayarlar (üstte belirgin ⚙ düğmesi, Ctrl+,) → Genel → Dil'den Türkçe seçilebilir (QSettings `dil`). Metinler `modyukle_gui.py` içindeki `S` sözlüğünde (en, tr). `modyukle.py` mesajları `t(tr, en)` ile iki dilli; dil `MODYUKLE_LANG` ile gelir, terminalde varsayılan Türkçe. Ayarlar penceresinde Genel + API anahtarları sekmeleri.
- 2026-11-22: Ayarlar → API anahtarları: GitHub için "Log in" (gh auth login --web, tek kullanımlık kod penceresi, kod panoya kopyalanır + tarayıcıda açılır) ve "Log out" (gh auth logout, onay sorar) düğmeleri. Nexus Mods: resmî v3 Upload API (open beta) var; henüz eklenmedi — bkz. aşağıdaki not.
- 2026-11-22: Nexus Mods eklendi (4. platform, `modyukle nexus <proje> <jar>`): resmî v3 API (uploads → PUT presigned → finalise → mod-files/{id}/versions veya mod-files; ayrıca mods/{id}/changelogs). Sayfayı kullanıcı sitede açar, adresi bir kez girer (`nexus_oyun`, `nexus_mod`, `nexus_file_id` ayarlar.properties'e yazılır; sayfada tek dosya varsa otomatik seçilir, hiç yoksa ilk dosya oluşturulur). Anahtar: NEXUS_TOKEN (GUI Ayarlar'dan da girilir). >100 MiB çok parçalı yükleme desteklenmiyor. Sahte yerel sunucuyla test edildi; GERÇEK Nexus yüklemesi denenmedi. İsteğe bağlı ayarlar: nexus_dosya_adi, nexus_kategori (main/optional/miscellaneous), nexus_surum_guncelle, nexus_eskiyi_arsivle. NEXUS_API_BASE env ile test sunucusu verilebilir.
- 2026-11-22: Nexus sayfa açıklaması: `modyukle sayfa <proje> [--prova] [--evet]` aciklamalar/<proje>.txt'i (Markdown) `yukleyici/nexus_bbcode.py` ile BBCode'a çevirip PATCH /mods/{id} ile kısa+tam açıklamayı günceller (API sayfa AÇAMAZ; yalnızca summary+description değiştirilebilir). GUI'de "Update Nexus page" düğmesi (Prova işaretliyse önizleme). Sahte sunucuyla test edildi; mchol'un Nexus sayfası henüz açılmadı → `nexus_mod` ayarlanmadı.
- Kullanıcı sonradan ardoom, mchol, mcstray, the_artifacts projelerini de ekledi; ardoom/mchol/mcstray/biomes incelemede.
- 2026-11-22: GitHub repolarına (mchol, ardinyos-biomes, mcstray, ardinyos-dishes) aciklamalar/*.txt'ten üretilmiş tam README.md yazıldı ve pushlandı. ardoom/the_artifacts'ın GitHub repoları henüz yok. mchol README'sinde 26.1.2 (release) / kaynak 26.3 farkı not düşüldü.

- 2026-11-22: Araç adı "Modyukle" (EN/TR aynı). Git deposu ~/Projects/mcmodplan, GitHub: ArdinyoGitHub/Modyukle (private).

## En son nerede kaldık (2026-11-22)
- Sıradaki: kullanıcı mchol Nexus sayfasını sitede açınca `modyukle sayfa mchol --prova` ile önizle, sonra gerçek gönder; ardından `modyukle nexus mchol <jar> --prova` ile dosya yüklemeyi dene. Nexus tarafı hiç gerçek hesapla denenmedi.
- GUI hazır; kullanıcının ekranda deneyip geri bildirim vermesi bekleniyor (gerçek yükleme GUI'den denenmedi).
- İnceleme gönderme yolu canlıda henüz denenmedi.
- `ardinyos_dishes`: GitHub repo açıldı, CF id 533099 (doğrulanmadı), hiçbir şey yüklenmedi.
- Modrinth PAT'inde USER_READ yok, `/v2/user` 401 verir (token geçerli).
- Tokenlar fish evrensel değişkenlerinde (CF + Modrinth); GitHub token `gh auth token` (ArdinyoGitHub).
- Ayrıntılı hafıza notu: `mod-publishing`.


### GUI: oyun + kaynak türü (2026-11-22)
- Üstte "Game and source" kutusu: Oyun açılırı (şimdilik yalnızca Minecraft, ileride başka oyun eklenebilir) + iki kaynak türü: **Hazır .jar** veya **Çalışma alanından derle**.
- Derle modunda MCreator çalışma alanı klasörü seçilir (içinde gradlew olmalı); GUI `sh gradlew build` çalıştırır, build/libs içindeki en yeni jar'ı (sources/javadoc/slim/dev hariç) alıp yükleme akışına sürer. Sahte gradlew ile test edildi, gerçek derleme denenmedi.
- Derle modunda GUI `--kaynak=<çalışma alanı>` bayrağını da gönderir: modyukle, GitHub sürümünden önce kaynağı (build/, .gradle/, run/, .mcreator/, *.jar hariç; gradle-wrapper.jar dahil) repoya commit'leyip main'e iter, release etiketi o commit'e gider. Prova'da sadece dosya sayısını yazar. Yerel bare repo ile test edildi, gerçek GitHub'da denenmedi.
- Yüklenecek jar adı ayarlanabilir: GUI'de "Upload file name" alanı → `--dosya-adi=AD` (jar geçici klasöre o adla kopyalanıp tüm platformlara öyle gider; boş = orijinal ad; .jar otomatik eklenir).
- (2026-11-22) GitHub repoları incelendi: kaynak kod hiçbirinde yoktu (repo yalnızca README ile açılıyordu). ardinyos-dishes release'i yoktu → yüklendi. Kaynaklar `modyukle kaynak <proje> <çalışma alanı> [--haric=klasor]` komutuyla gönderildi (mchol, mcstray [stray-walled-city hariç], ardinyos-biomes). Kaynak gönderimi artık MCreator/, bin/, .settings, build/, run/ vb. hariç tutar ve 200 MB üstünü reddeder. mchol'a yanlışlıkla giren MCreator/ klasörü ayrı commit'le silindi (geçmişte kaldı). mcstray release dosya adı modid-1.0.jar, mchol release dosya adı 2.2.0 ama etiket v1.0.0 (tutarsız).
- GitHub etiketi seçilebilir: GUI'de "GitHub tag" alanı / `--etiket=TAG` (boş = v<sürüm>). mchol release dosyası mchol-1.0.0-neoforge-26.1.2.jar olarak yeniden adlandırıldı; mcstray: mcstray-1.0.0-neoforge-26.1.2.jar.
