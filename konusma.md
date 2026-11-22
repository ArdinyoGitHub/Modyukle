# Planlama Konuşması — Özet Kaydı (13 Kasım 2026)

**1. Soru:** Modları CurseForge, Modrinth ve Nexus'a ayrı ayrı yüklemek zaman alıyor, otomasyon yolu var mı?

**Cevap:** Var. Seçenekler: GitHub Actions (`mc-publish`), Gradle eklentileri (Minotaur, CurseGradle, ModPublisher) veya kendi betiğin. Nexus'un yükleme API'si/GitHub Action'ı yeni çıktı, durumu kontrol edilmeli.

---

**2. Soru:** Nexus yerine GitHub olsun, Nexus'a belki elle yüklerim. Şu an kısıtlı ağdayım, planlamayı yapalım.

**Cevap:** Hedef: CurseForge + Modrinth + GitHub Releases. Aşamalar: kararlar → tokenlar → repo düzeni → yükleme ayarı → alpha sürümle test → Nexus elle.

---

**3. Soru:** NeoForge ve Gradle kullanıyorum. Minecraft'a yeni sürüm geldikçe güncellemeleri yeni sürümde yapıyorum.

**Cevap:** `mc-publish` 2023'ten beri güncellenmemiş ve yeni MC sürüm formatını (26.1 gibi) desteklediği belirsiz. Bu yüzden aktif bakımlı **Mod Publish Plugin** seçildi. MC sürümü `gradle.properties`'teki `minecraft_version`'dan okunduğu için yeni sürüme geçince yükleme ayarı değişmez. Önce GitHub Actions iş akışı yazıldı (tag kontrolü, Java sürümü tespiti, changelog çıkarma) → `ileride-github-actions/publish.yml`.

---

**4. Soru:** Bunlar neden önemli? Mod sadece bir .jar. Galiba GitHub'da derlenmemiş hali olduğu için iş karışıyor.

**Cevap:** Doğru. Karmaşıklığın çoğu (Java tespiti, tag kontrolü, changelog'u dosyadan çekme, iş akışı) jar'ı GitHub'ın boş sunucusunda kaynaktan derlemekten geliyordu. Yüklemenin kendisi için gereken sadece sitelerin istediği bilgiler (MC sürümü, yükleyici, sürüm türü, changelog) ve tokenlar. **Karar:** Yerel yükleme — kendi bilgisayarında `./gradlew build publishMods`. Gerekirse ileride Actions'a geçilir, Gradle bloğu aynen kalır.

---

**5. Soru:** Yerel kullanıma göre son halini yaz.

**Cevap:** `publishMods.gradle` dosyası. `-PdryRun` ile prova modu eklendi. Tokenlar fish universal değişkenleri olarak tanımlanacak. Adımlar `README.md`'de.

---

Kaynaklar:
- https://modmuss50.github.io/mod-publish-plugin/
- https://plugins.gradle.org/plugin/me.modmuss50.mod-publish-plugin
- https://github.com/Kir-Antipov/mc-publish/releases
