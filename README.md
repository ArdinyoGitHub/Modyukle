# Modyukle — Minecraft Mod Otomatik Yükleme Aracı

**Hedef:** Modu tek komutla CurseForge + Modrinth + GitHub Releases'e yüklemek. Nexus elle.
**Yöntem:** Mod Publish Plugin (`me.modmuss50.mod-publish-plugin` 2.2.1).
**Tarih:** 13 Kasım 2026

## Dosyalar
- `yukleyici/` — **asıl kullanılan.** `modyukle.py` (fish: `modyukle`) + Gradle yükleme motoru
- `publishMods.gradle` — elle yazılmış (MCreator olmayan) Gradle projeleri için `build.gradle` bloğu
- `ileride-github-actions/publish.yml` — opsiyonel, şu an kullanılmıyor
- `aciklamalar/` — her modun sayfa açıklaması (`<proje>.txt`: ilk satır kısa açıklama, `---` sonrası sayfa metni). modyukle yeni Modrinth projesi oluştururken bunu kullanır.
- `konusma.md` — planlama konuşmasının kaydı

## Kullanım
```
modyukle <platform> <proje> <jar> [--prova] [--incele]

modyukle hepsi ardinyos_biomes ~/İndirilenler/ardinyos_biomes-2.0.2-neoforge-26.1.2.jar
modyukle modrinth,github yeni_mod ~/yeni_mod-1.0.0-neoforge-26.1.2.jar --prova
```
- **platform:** `modrinth`, `github`, `curseforge`, `hepsi` ya da virgülle birkaçı
- **proje:** proje adı (`ardinyos_biomes` → Modrinth slug'ı ve GitHub repo adı `ardinyos-biomes`)
- **jar:** MCreator'ın export ettiği dosya. Ad, sürüm, MC sürümü ve bağımlılıklar jar'ın içinden okunur.
- `--prova`: hiçbir şey oluşturmaz/yüklemez, ne yapılacağını gösterir. `modyukle` tek başına yardımı ve kayıtlı projeleri gösterir.

**Proje yoksa** oluşturur: Modrinth'te taslak (açıklama/kategori/lisans sorar), GitHub'da repo.
**Proje varsa** yenisini oluşturmaz, sadece sürümü yükler. O sürüm zaten yüklüyse o platformu atlar.
**Modrinth sonrası:** sürümün ortamı (Environment) `ayarlar.properties → ortam=` değerine göre ayarlanır (varsayılan `client_and_server`; eklenti v2 API kullandığı için aksi halde `unknown` kalıyordu). Proje taslaksa "incelemeye göndereyim mi?" diye sorar; `--incele` sormadan gönderir.
Modrinth'te aynı adlı başkasının projesi varsa sahibini gösterip sorar.
**CurseForge** projesi API ile oluşturulamaz: sitede açıp ilk seferde sorulan Project ID'yi gir.

Proje ID'leri `yukleyici/modlar/<proje>/ayarlar.properties` içinde saklanır (ilk çalıştırmada otomatik oluşur).

## Tokenlar (bir kez)
| Değişken | Nereden | İzin |
|---|---|---|
| `CURSEFORGE_TOKEN` | curseforge.com → Account → API Tokens | – |
| `MODRINTH_TOKEN` | modrinth.com → Settings → PATs | Create projects, Create versions, Write projects |
| GitHub | `gh auth login` yeterli | – |

```fish
set -Ux CURSEFORGE_TOKEN ...
set -Ux MODRINTH_TOKEN ...
```

## Her sürümde
1. MCreator → Workspace settings → **sürümü artır** (alpha için `1.0.1-alpha`, beta için `-beta`).
2. MCreator → **File → Export mod**.
3. `yukleyici/modlar/<proje>/changelog.txt`'ye değişiklikleri yaz (yükleme sonrası `changelog-<sürüm>.txt` olarak arşivlenir ve boşaltılır).
4. `modyukle hepsi <proje> <jar>`
5. Nexus: elle.

> Aynı sürümü iki kez yükleyemezsin (siteler reddeder) — önce MCreator'da sürümü artır.
> Modrinth PAT'ında "Read user data" yoksa bazı testler yanıltıcı 401 verir; yükleme için gerekmez.
> 13 Kasım 2026: Ardinyo's Biomes 2.0.1 Modrinth (taslak) + GitHub'a yüklendi.
