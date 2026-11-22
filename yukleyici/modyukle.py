#!/usr/bin/env python3
"""modyukle <platform> <proje> <jar> [--prova] [--incele] [--kaynak=<çalışma alanı>] [--dosya-adi=<ad.jar>] [--etiket=<tag>]

platform : modrinth | github | curseforge | nexus | hepsi   (virgülle birden fazla: modrinth,github)
proje    : proje adı, örn. ardinyos_biomes  (Modrinth slug'ı ve GitHub repo adı: ardinyos-biomes)
jar      : yüklenecek jar dosyası

modyukle sayfa <proje> [--prova] [--evet]
    aciklamalar/<proje>.txt (Markdown) dosyasını Nexus BBCode'una çevirip Nexus mod sayfasının kısa + tam açıklamasını
    günceller. --prova: yalnızca önizleme. --evet: onay sormadan gönder.

Proje yoksa oluşturur (Modrinth: taslak, GitHub: repo). Varsa yenisini oluşturmaz, sadece sürüm yükler.
CurseForge'da proje API ile oluşturulamaz: sitede açıp ID'sini bir kez girmen gerekir.
Nexus Mods: mod sayfasını sitede sen açarsın; sayfanın adresini (nexusmods.com/minecraft/mods/123) bir kez girersin,
  sonra dosya/sürüm yükleme Nexus v3 API ile yapılır (anahtar: NEXUS_TOKEN, https://www.nexusmods.com/settings/api-keys).
Bilgiler (ad, sürüm, MC sürümü, bağımlılıklar) jar'ın içindeki META-INF/*.mods.toml'dan okunur.

Modrinth'te yüklemeden sonra: sürümün ortamı (client/server) ayarlanır (ayarlar.properties → ortam=,
varsayılan client_and_server) ve proje taslaksa incelemeye göndermek istenip istenmediği sorulur.
--incele : sormadan incelemeye gönder.
--etiket=TAG : GitHub release etiketi (varsayılan: v<sürüm>).
--dosya-adi=AD : Platformlara yüklenecek jar dosyasının adı (varsayılan: jar'ın kendi adı).
--kaynak=DIR : GitHub'a jar'ın yanında çalışma alanının kaynak kodunu da gönderir.
Ortam değerleri: client_and_server, client_only, client_only_server_optional, server_only,
                 server_only_client_optional, singleplayer_only, dedicated_server_only, client_or_server
"""
import base64, hashlib, json, os, re, subprocess, sys, time, tomllib, urllib.request, urllib.error, uuid, zipfile
from pathlib import Path

DIZIN = Path(__file__).resolve().parent
UA = "ArdinyoGitHub/mod-yukleyici/1.0"
MR = "https://api.modrinth.com/v2"
PLATFORMLAR = ["modrinth", "github", "curseforge", "nexus"]
SISTEM_BAGIMLILIKLARI = {"neoforge", "forge", "minecraft", "java", "fabricloader", "fabric", "quilt_loader"}


DIL = os.environ.get("MODYUKLE_LANG", "tr")   # GUI "en" / "tr" iletir; terminalde varsayılan Türkçe


def t(tr, en):
    return en if DIL == "en" else tr


def evet(cevap):
    return cevap.strip().lower() in ("e", "evet", "y", "yes")


def hata(msg):
    print(f"{t('HATA', 'ERROR')}: {msg}", file=sys.stderr)
    sys.exit(1)


def sor(soru, varsayilan=""):
    if os.environ.get("MODYUKLE_GUI"):
        # GUI (modyukle_gui.py) bu satırı yakalayıp pencere açar, cevabı stdin'e tek satır yazar.
        print("\x1eSOR " + json.dumps({"soru": soru.strip(), "varsayilan": varsayilan}), flush=True)
        cevap = sys.stdin.readline().strip()
        return cevap or varsayilan
    try:
        cevap = input(f"{soru}{f' [{varsayilan}]' if varsayilan else ''}: ").strip()
    except EOFError:
        cevap = ""
    return cevap or varsayilan


# ---------- ayarlar.properties (basit, yorumları korur) ----------
def ayar_oku(yol):
    d = {}
    if yol.exists():
        for satir in yol.read_text("utf-8").splitlines():
            if "=" in satir and not satir.lstrip().startswith("#"):
                k, v = satir.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def ayar_yaz(yol, d):
    satirlar = yol.read_text("utf-8").splitlines() if yol.exists() else []
    kalan = dict(d)
    for i, s in enumerate(satirlar):
        if "=" in s and not s.lstrip().startswith("#"):
            k = s.split("=", 1)[0].strip()
            if k in kalan:
                satirlar[i] = f"{k}={kalan.pop(k)}"
    satirlar += [f"{k}={v}" for k, v in kalan.items()]
    yol.write_text("\n".join(satirlar) + "\n", "utf-8")


# ---------- jar bilgileri ----------
def jar_bilgisi(jar):
    with zipfile.ZipFile(jar) as z:
        adlar = [n for n in z.namelist() if re.fullmatch(r"META-INF/(neoforge\.)?mods\.toml", n)]
        if not adlar:
            hata(t(f"{jar} içinde META-INF/neoforge.mods.toml yok (NeoForge modu mu?)", f"No META-INF/neoforge.mods.toml in {jar} (is it a NeoForge mod?)"))
        yukleyici = "neoforge" if "neoforge" in adlar[0] else "forge"
        toml = tomllib.loads(z.read(adlar[0]).decode("utf-8"))
        manifest = z.read("META-INF/MANIFEST.MF").decode("utf-8", "ignore") if "META-INF/MANIFEST.MF" in z.namelist() else ""
    mod = toml["mods"][0]
    modid = mod["modId"]
    surum = mod.get("version", "")
    if "${" in surum or not surum:
        m = re.search(r"Implementation-Version:\s*(\S+)", manifest)
        surum = m.group(1) if m else hata(t("Jar'da sürüm bulunamadı", "No version found in the jar"))
    bag = toml.get("dependencies", {}).get(modid, [])
    mc = next((d.get("versionRange", "") for d in bag if d.get("modId") == "minecraft"), "")
    mc_surumleri = re.findall(r"\d+(?:\.\d+)+", mc)
    if not mc_surumleri:
        m = re.search(r"-(\d+(?:\.\d+)+)\.jar$", jar.name)
        mc_surumleri = [m.group(1)] if m else []
    if not mc_surumleri:
        hata(t("Minecraft sürümü jar'dan okunamadı", "Could not read the Minecraft version from the jar"))
    gerekli = [d["modId"] for d in bag
               if d.get("modId") not in SISTEM_BAGIMLILIKLARI
               and (d.get("type", "").lower() == "required" or d.get("mandatory") is True)]
    istege = [d["modId"] for d in bag
              if d.get("modId") not in SISTEM_BAGIMLILIKLARI and d.get("type", "").lower() == "optional"]
    yan = {d.get("side", "BOTH") for d in bag if d.get("modId") == "minecraft"}
    return {
        "modid": modid, "ad": mod.get("displayName", modid), "surum": surum,
        "aciklama": (mod.get("description") or "").strip(),
        "mc": mc_surumleri[0], "yukleyici": yukleyici,
        "gerekli": gerekli, "istege": istege, "sadece_sunucu": yan == {"SERVER"},
        "lisans": toml.get("license", ""),
    }


# ---------- Modrinth ----------
def mr_istek(yol, yontem="GET", veri=None, basliklar=None, yetkili=True, api=MR):
    h = {"User-Agent": UA, **(basliklar or {})}
    if yetkili and os.environ.get("MODRINTH_TOKEN"):
        h["Authorization"] = os.environ["MODRINTH_TOKEN"]
    req = urllib.request.Request(api + yol, data=veri, method=yontem, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        govde = e.read()
        try:
            return e.code, json.loads(govde)
        except Exception:
            return e.code, {"error": govde.decode("utf-8", "ignore")}


def mr_slug_var_mi(slug):
    kod, _ = mr_istek(f"/project/{slug}", yetkili=False)
    return kod == 200


def mr_proje_hazirla(proje, slug, bilgi, ayar, prova=False):
    if ayar.get("modrinth_id"):
        print(t(f"  Modrinth: proje zaten kayıtlı ({ayar['modrinth_id']}), yenisi oluşturulmayacak.", f"  Modrinth: project already registered ({ayar['modrinth_id']}), not creating a new one."))
        return ayar["modrinth_id"]
    kod, p = mr_istek(f"/project/{slug}")
    if kod == 200:
        _, uyeler = mr_istek(f"/project/{p['id']}/members", yetkili=False)
        sahipler = ", ".join(u["user"]["username"] for u in (uyeler or []))
        print(t(f"  Modrinth'te '{slug}' zaten var: {p['title']} (sahibi: {sahipler})", f"  '{slug}' already exists on Modrinth: {p['title']} (owner: {sahipler})"))
        if not evet(sor(t("  Bu senin projen mi? Ona yükleyeyim mi? (e/h)", "  Is this your project? Upload to it? (y/n)"), t("h", "n"))):
            hata(t("Başka bir proje adı seç.", "Choose a different project name."))
        return p["id"]
    if prova:
        print(t(f"  (prova) Modrinth'te '{slug}' yok, gerçek çalıştırmada taslak proje oluşturulacak.", f"  (dry run) '{slug}' not on Modrinth; a draft project will be created on a real run."))
        return ""
    if not os.environ.get("MODRINTH_TOKEN"):
        hata(t("MODRINTH_TOKEN tanımlı değil", "MODRINTH_TOKEN is not set"))
    print(t(f"  Modrinth'te '{slug}' yok, taslak proje oluşturulacak.", f"  '{slug}' not on Modrinth, creating a draft project."))
    kisa, govde_metni = "", ""
    aciklama_dosyasi = DIZIN.parent / "aciklamalar" / f"{proje}.txt"
    if aciklama_dosyasi.exists():
        metin = aciklama_dosyasi.read_text("utf-8")
        ust, _, govde_metni = metin.partition("\n---\n")
        kisa = ust.replace("Short description:", "").strip()
        print(t(f"  Sayfa açıklaması {aciklama_dosyasi.name} dosyasından alınacak.", f"  Page description will be taken from {aciklama_dosyasi.name}."))
    aciklama = sor(t("  Kısa açıklama", "  Short description"), kisa or bilgi["aciklama"][:200] or f"{bilgi['ad']} - Minecraft {bilgi['yukleyici']} mod")
    kategoriler = sor(t("  Kategoriler, virgülle (worldgen, adventure, decoration, food, magic, technology, utility...)", "  Categories, comma-separated (worldgen, adventure, decoration, food, magic, technology, utility...)"), "adventure")
    lisans = sor(t("  Lisans (SPDX, örn. MIT; boş = All Rights Reserved)", "  License (SPDX, e.g. MIT; empty = All Rights Reserved)"), "LicenseRef-All-Rights-Reserved")
    veri = {
        "slug": slug, "title": bilgi["ad"], "description": aciklama,
        "categories": [k.strip() for k in kategoriler.split(",") if k.strip()], "additional_categories": [],
        "client_side": "optional" if bilgi["sadece_sunucu"] else "required", "server_side": "required",
        "body": govde_metni.strip() or f"# {bilgi['ad']}\n\n{aciklama}\n", "project_type": "mod", "initial_versions": [],
        "is_draft": True, "license_id": lisans,
        "issues_url": None, "source_url": None, "wiki_url": None, "discord_url": None, "donation_urls": [],
    }
    sinir = uuid.uuid4().hex
    govde = (f"--{sinir}\r\nContent-Disposition: form-data; name=\"data\"\r\nContent-Type: application/json\r\n\r\n"
             f"{json.dumps(veri)}\r\n--{sinir}--\r\n").encode()
    kod, cevap = mr_istek("/project", "POST", govde, {"Content-Type": f"multipart/form-data; boundary={sinir}"})
    if kod not in (200, 201):
        if "slug" in json.dumps(cevap).lower():
            hata(t(f"'{slug}' adresi Modrinth'te alınmış (belki senin taslağın?). Taslaksa ID'sini "
                   f"modlar/{proje}/ayarlar.properties içine modrinth_id= olarak yaz. Cevap: {cevap}",
                   f"'{slug}' is taken on Modrinth (maybe your own draft?). If it is, put its ID into "
                   f"modlar/{proje}/ayarlar.properties as modrinth_id=. Response: {cevap}"))
        hata(t(f"Modrinth projesi oluşturulamadı ({kod}): {cevap}", f"Could not create the Modrinth project ({kod}): {cevap}"))
    print(t(f"  Oluşturuldu: https://modrinth.com/mod/{slug}  (taslak — sitede simge ekle ve 'Submit for review' de)", f"  Created: https://modrinth.com/mod/{slug}  (draft — add an icon on the site and click 'Submit for review')"))
    return cevap["id"]


def mr_surum_var_mi(proje_id, surum):
    kod, surumler = mr_istek(f"/project/{proje_id}/version")
    return kod == 200 and any(v["version_number"] == surum for v in surumler)


MR3 = "https://api.modrinth.com/v3"


def mr_ortam_ayarla(proje_id, surum, ortam):
    """Yükleme eklentisi v2 kullandığı için sürümün 'environment' alanı 'unknown' kalıyor; v3 ile düzelt."""
    kod, surumler = mr_istek(f"/project/{proje_id}/version", api=MR3)
    v = next((v for v in (surumler or []) if v.get("version_number") == surum), None) if kod == 200 else None
    if not v:
        print(t(f"  UYARI: Modrinth'te {surum} sürümü bulunamadı, ortam ayarlanamadı.", f"  WARNING: version {surum} not found on Modrinth, could not set the environment."))
        return
    if v.get("environment") == ortam:
        print(t(f"  Modrinth ortamı: {ortam} (zaten ayarlı)", f"  Modrinth environment: {ortam} (already set)"))
        return
    kod, cevap = mr_istek(f"/version/{v['id']}", "PATCH", json.dumps({"environment": ortam}).encode(),
                          {"Content-Type": "application/json"}, api=MR3)
    if kod in (200, 204):
        print(t(f"  Modrinth ortamı ayarlandı: {ortam}", f"  Modrinth environment set: {ortam}"))
    else:
        print(t(f"  UYARI: ortam ayarlanamadı ({kod}): {cevap}  — ayarlar.properties → ortam= değerini kontrol et.", f"  WARNING: could not set the environment ({kod}): {cevap}  — check ortam= in ayarlar.properties."))


def mr_incelemeye_gonder(proje_id, otomatik):
    kod, p = mr_istek(f"/project/{proje_id}")
    if kod != 200:
        return
    durum = p.get("status")
    if durum != "draft":
        aciklama = {"processing": t("incelemede", "in review"), "approved": t("yayında", "published"),
                    "rejected": t("reddedildi", "rejected"), "withheld": t("geri tutuldu", "withheld"),
                    "unlisted": t("liste dışı", "unlisted")}.get(durum, durum)
        print(t(f"  Modrinth proje durumu: {aciklama}", f"  Modrinth project status: {aciklama}"))
        return
    eksik = []
    if not p.get("icon_url"):
        eksik.append(t("simge", "icon"))
    if len(p.get("body") or "") < 100:
        eksik.append(t("sayfa açıklaması", "page description"))
    if eksik:
        print(t(f"  Not: projede eksik var ({', '.join(eksik)}). Modrinth incelemesinde sorun çıkarabilir.", f"  Note: the project is missing: {', '.join(eksik)}. This may cause problems in Modrinth review."))
    if not otomatik and not evet(sor(t("  Proje taslak. İncelemeye göndereyim mi? (e/h)", "  The project is a draft. Submit it for review? (y/n)"), t("h", "n"))):
        print(t(f"  Gönderilmedi. Sonra: https://modrinth.com/project/{proje_id} → Submit for review", f"  Not submitted. Later: https://modrinth.com/project/{proje_id} → Submit for review"))
        return
    kod, cevap = mr_istek(f"/project/{proje_id}", "PATCH", json.dumps({"status": "processing"}).encode(),
                          {"Content-Type": "application/json"})
    if kod in (200, 204):
        print(t("  Modrinth: proje incelemeye gönderildi.", "  Modrinth: project submitted for review."))
    else:
        print(t(f"  UYARI: incelemeye gönderilemedi ({kod}): {cevap}", f"  WARNING: could not submit for review ({kod}): {cevap}"))


def mr_bagimliliklari_dogrula(modidler):
    gecerli = []
    for m in modidler:
        if mr_slug_var_mi(m) or mr_slug_var_mi(m.replace("_", "-")):
            gecerli.append(m if mr_slug_var_mi(m) else m.replace("_", "-"))
        else:
            print(t(f"  UYARI: bağımlılık '{m}' Modrinth'te bulunamadı, eklenmedi "
                    f"(doğru slug'ı ayarlar.properties → gerekli= içine yazabilirsin).",
                    f"  WARNING: dependency '{m}' not found on Modrinth, not added "
                    f"(you can put the correct slug into gerekli= in ayarlar.properties)."))
    return gecerli


# ---------- GitHub ----------
def gh(*args, sessiz=True):
    return subprocess.run(["gh", *args], capture_output=sessiz, text=True)


KAYNAK_ATLA_DIZIN = {".git", "build", ".gradle", "run", "runs", "out", ".idea", ".vscode", ".mcreator", "__pycache__", "node_modules", "logs", "MCreator", "bin", ".settings"}
KAYNAK_TOPLAM_SINIRI = 200 * 1024 * 1024
KAYNAK_HARIC = set()  # --haric=klasor1,klasor2 (üst düzey klasör adları)


def kaynak_dosyalari(kok):
    """Kaynak koddan GitHub'a gidecek dosyalar (derleme çıktıları ve cache hariç)."""
    for yol in sorted(kok.rglob("*")):
        goreli = yol.relative_to(kok)
        if not yol.is_file() or yol.is_symlink() or KAYNAK_ATLA_DIZIN & set(goreli.parts[:-1]) or goreli.parts[0] in KAYNAK_HARIC:
            continue
        if yol.suffix in (".jar", ".class", ".log") and goreli.as_posix() != "gradle/wrapper/gradle-wrapper.jar":
            continue
        if yol.stat().st_size > 50 * 1024 * 1024:
            continue
        yield goreli


def gh_kaynak_yukle(repo, kaynak, surum, dal, prova, mesaj=None):
    """Çalışma alanının kaynak kodunu repoya commit'leyip iter (release etiketi bu commit'e gider)."""
    import shutil, tempfile
    dosyalar = list(kaynak_dosyalari(kaynak))
    if not dosyalar:
        print(t(f"  UYARI: {kaynak} içinde yüklenecek kaynak dosyası bulunamadı.", f"  WARNING: no source files to upload in {kaynak}."))
        return
    toplam = sum((kaynak / g).stat().st_size for g in dosyalar)
    if toplam > KAYNAK_TOPLAM_SINIRI:
        boyut = {}
        for g in dosyalar:
            boyut[g.parts[0]] = boyut.get(g.parts[0], 0) + (kaynak / g).stat().st_size
        buyuk = ", ".join(f"{k} ({v // 2**20} MB)" for k, v in sorted(boyut.items(), key=lambda x: -x[1])[:3])
        return print(t(f"  UYARI: kaynak {toplam // 2**20} MB, çok büyük; yüklenmedi. En büyükler: {buyuk}. --haric=klasor ile hariç tutabilirsin.",
                       f"  WARNING: source is {toplam // 2**20} MB, too large; not uploaded. Largest: {buyuk}. Use --haric=folder to exclude."))
    if prova:
        print(t(f"  (prova) GitHub: {kaynak} içindeki {len(dosyalar)} kaynak dosyası {repo} reposuna gönderilecek.",
                f"  (dry run) GitHub: {len(dosyalar)} source files from {kaynak} would be pushed to {repo}."))
        return
    gecici = Path(tempfile.mkdtemp(prefix="modyukle-kaynak-"))
    try:
        klon = gecici / "repo"
        r = gh("repo", "clone", repo, str(klon), "--", "--depth", "1")
        if r.returncode != 0:
            return print(t(f"  UYARI: repo klonlanamadı, kaynak kod yüklenmedi: {r.stderr.strip()}",
                           f"  WARNING: could not clone the repo, source not uploaded: {r.stderr.strip()}"))
        for g in dosyalar:
            hedef = klon / g
            hedef.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(kaynak / g, hedef)
        login = gh("api", "user", "-q", ".login").stdout.strip() or "modyukle"
        git = ["git", "-C", str(klon), "-c", f"user.name={login}", "-c", f"user.email={login}@users.noreply.github.com",
               "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]
        subprocess.run([*git, "add", "-A"], capture_output=True, text=True)
        if not subprocess.run([*git, "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
            return print(t("  GitHub: kaynak kod zaten güncel.", "  GitHub: source code already up to date."))
        c = subprocess.run([*git, "commit", "-m", mesaj or f"Source for v{surum}"], capture_output=True, text=True)
        if c.returncode != 0:
            return print(t(f"  UYARI: commit başarısız: {c.stderr.strip() or c.stdout.strip()}", f"  WARNING: commit failed: {c.stderr.strip() or c.stdout.strip()}"))
        pu = subprocess.run([*git, "push", "origin", f"HEAD:{dal}"], capture_output=True, text=True)
        if pu.returncode != 0:
            return print(t(f"  UYARI: push başarısız, kaynak kod yüklenmedi: {pu.stderr.strip()}", f"  WARNING: push failed, source not uploaded: {pu.stderr.strip()}"))
        print(t(f"  GitHub: {len(dosyalar)} kaynak dosyası {repo}/{dal} dalına gönderildi.", f"  GitHub: pushed {len(dosyalar)} source files to {repo}/{dal}."))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def gh_proje_hazirla(slug, bilgi, ayar, prova=False):
    if ayar.get("github_repo"):
        print(t(f"  GitHub: repo zaten kayıtlı ({ayar['github_repo']}), yenisi oluşturulmayacak.", f"  GitHub: repo already registered ({ayar['github_repo']}), not creating a new one."))
        return ayar["github_repo"]
    r = gh("api", "user", "-q", ".login")
    if r.returncode != 0:
        hata(t("gh ile giriş yapılmamış: gh auth login", "Not logged in with gh: run gh auth login"))
    repo = f"{r.stdout.strip()}/{slug}"
    if gh("repo", "view", repo).returncode == 0:
        print(t(f"  GitHub: {repo} zaten var, yenisi oluşturulmayacak.", f"  GitHub: {repo} already exists, not creating a new one."))
        return repo
    if prova:
        print(t(f"  (prova) GitHub: {repo} yok, gerçek çalıştırmada oluşturulacak.", f"  (dry run) GitHub: {repo} does not exist; it will be created on a real run."))
        return ""
    print(t(f"  GitHub: {repo} yok, oluşturuluyor...", f"  GitHub: {repo} does not exist, creating..."))
    r = gh("repo", "create", repo, "--public", "--add-readme",
           "--description", f"{bilgi['ad']} - Minecraft {bilgi['yukleyici']} mod")
    if r.returncode != 0:
        hata(t(f"GitHub reposu oluşturulamadı: {r.stderr}", f"Could not create the GitHub repo: {r.stderr}"))
    print(t(f"  Oluşturuldu: https://github.com/{repo}", f"  Created: https://github.com/{repo}"))
    return repo


# ---------- Nexus Mods (v3 API) ----------
NX = os.environ.get("NEXUS_API_BASE", "https://api.nexusmods.com/v3")
NX_TEK_PARCA_SINIRI = 100 * 1024 * 1024   # bundan büyük dosyalar çok parçalı yükleme ister (desteklenmiyor)


def nx_istek(yol, yontem="GET", veri=None):
    h = {"User-Agent": UA, "apikey": os.environ.get("NEXUS_TOKEN", ""), "Accept": "application/json"}
    govde = None
    if veri is not None:
        govde = json.dumps(veri).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(NX + yol, data=govde, method=yontem, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            ham = r.read()
            return r.status, (json.loads(ham) if ham else None)
    except urllib.error.HTTPError as e:
        ham = e.read()
        try:
            return e.code, json.loads(ham)
        except Exception:
            return e.code, {"error": ham.decode("utf-8", "ignore")[:500]}


def nx_veri(kod, cevap, ne):
    if kod not in (200, 201):
        hata(t(f"Nexus: {ne} başarısız ({kod}): {json.dumps(cevap, ensure_ascii=False)[:500]}",
               f"Nexus: {ne} failed ({kod}): {json.dumps(cevap, ensure_ascii=False)[:500]}"))
    return (cevap or {}).get("data", cevap)


def nx_temiz_ad(ad):
    return re.sub(r"[^a-zA-Z0-9 _'().-]", "", ad).strip()[:50] or "Mod"


def nx_temiz_surum(v):
    return re.sub(r"[^a-zA-Z0-9.-]", "-", v)[:50]


def nx_adres_sor(ayar):
    """Mod sayfası adresini sorar ve ayar'a yazar. Boş bırakılırsa False."""
    print(t("  Nexus'ta mod sayfasını sitede oluştur (API sayfa açamaz), sonra adresini gir.",
            "  Create the mod page on Nexus first (the API cannot create pages), then enter its address."))
    giris = sor(t("  Nexus mod sayfası adresi, örn. nexusmods.com/minecraft/mods/123 (boş = Nexus'u atla)",
                  "  Nexus mod page address, e.g. nexusmods.com/minecraft/mods/123 (empty = skip Nexus)"))
    if not giris:
        print(t("  Nexus atlandı.", "  Nexus skipped."))
        return False
    m = re.search(r"nexusmods\.com/([^/\s]+)/mods/(\d+)", giris)
    if m:
        ayar["nexus_oyun"], ayar["nexus_mod"] = m.group(1), m.group(2)
    elif giris.isdigit():
        ayar["nexus_oyun"], ayar["nexus_mod"] = ayar.get("nexus_oyun", "minecraft"), giris
    else:
        hata(t("Nexus adresi anlaşılamadı. Örnek: https://www.nexusmods.com/minecraft/mods/123",
               "Could not understand the Nexus address. Example: https://www.nexusmods.com/minecraft/mods/123"))
    return True


def nx_hazirla(ayar, tum):
    """Mod sayfasını (oyun + numara) çözer, yüklenecek dosyayı (file id) belirler. None = Nexus'u atla."""
    if not os.environ.get("NEXUS_TOKEN"):
        if tum:
            print(t("  Nexus: NEXUS_TOKEN tanımlı değil, atlanıyor.", "  Nexus: NEXUS_TOKEN is not set, skipping."))
            return None
        hata(t("NEXUS_TOKEN tanımlı değil (https://www.nexusmods.com/settings/api-keys)",
               "NEXUS_TOKEN is not set (https://www.nexusmods.com/settings/api-keys)"))
    if not ayar.get("nexus_mod") and not nx_adres_sor(ayar):
        return None
    oyun = ayar.setdefault("nexus_oyun", "minecraft")
    kod, c = nx_istek(f"/games/{oyun}/mods/{ayar['nexus_mod']}")
    mod_uid = str(nx_veri(kod, c, t("mod sayfası sorgusu", "mod page lookup")).get("id", ""))
    if not mod_uid:
        hata(t("Nexus: mod kimliği alınamadı.", "Nexus: could not get the mod ID."))
    dosya_id = ayar.get("nexus_file_id", "")
    if not dosya_id:
        kod, c = nx_istek(f"/mods/{mod_uid}/files")
        dosyalar = nx_veri(kod, c, t("dosya listesi", "file list")).get("mod_files", [])
        if len(dosyalar) == 1:
            dosya_id = str(dosyalar[0]["id"])
            print(t(f"  Nexus: sayfadaki tek dosya seçildi: {dosyalar[0].get('name')} ({dosya_id})",
                    f"  Nexus: the only file on the page was selected: {dosyalar[0].get('name')} ({dosya_id})"))
        elif len(dosyalar) > 1:
            liste = "; ".join(f"{i + 1}) {d.get('name')}" for i, d in enumerate(dosyalar))
            sec = sor(t(f"  Nexus'ta birden çok dosya var: {liste}. Hangisine yeni sürüm yüklensin? (numara)",
                        f"  Several files on Nexus: {liste}. Which one gets the new version? (number)"), "1")
            try:
                dosya_id = str(dosyalar[int(sec) - 1]["id"])
            except (ValueError, IndexError):
                hata(t("Geçersiz seçim.", "Invalid choice."))
        else:
            print(t("  Nexus: sayfada henüz dosya yok, ilk dosya oluşturulacak.",
                    "  Nexus: the page has no files yet, the first file will be created."))
    ayar["nexus_file_id"] = dosya_id
    return {"oyun": oyun, "mod_uid": mod_uid, "dosya_id": dosya_id}


def nx_yukle(plan, jar, bilgi, changelog_metni, ayar, prova):
    """Yüklenirse True, atlanırsa False döner."""
    surum = nx_temiz_surum(bilgi["surum"])
    dosya_id = plan["dosya_id"]
    if dosya_id:
        kod, c = nx_istek(f"/mod-files/{dosya_id}/versions")
        if kod == 200 and any(v.get("version") == surum for v in (nx_veri(kod, c, "versions") or {}).get("versions", [])):
            print(t(f"  Nexus: {surum} zaten yüklü, atlanıyor.", f"  Nexus: {surum} already uploaded, skipping."))
            return False
    boyut = jar.stat().st_size
    if boyut > NX_TEK_PARCA_SINIRI:
        hata(t(f"Nexus: dosya {boyut // 1048576} MiB; 100 MiB üstü çok parçalı yükleme gerekir, bu araç henüz desteklemiyor.",
               f"Nexus: the file is {boyut // 1048576} MiB; files over 100 MiB need multipart upload, which this tool does not support yet."))
    ad = nx_temiz_ad(ayar.get("nexus_dosya_adi") or bilgi["ad"])
    kategori = ayar.get("nexus_kategori", "main")
    aciklama = (changelog_metni.strip().splitlines() or [""])[0][:255]
    if prova:
        islem = t("yeni sürüm", "new version") if dosya_id else t("ilk dosya", "first file")
        print(t(f"  (prova) Nexus: '{ad}' {surum} ({islem}, kategori {kategori}) yüklenecek; oyun {plan['oyun']}, mod {ayar['nexus_mod']}.",
                f"  (dry run) Nexus: would upload '{ad}' {surum} ({islem}, category {kategori}); game {plan['oyun']}, mod {ayar['nexus_mod']}."))
        return True
    veri = jar.read_bytes()
    md5 = hashlib.md5(veri)
    print(t(f"  Nexus: yükleniyor ({boyut // 1024} KiB)...", f"  Nexus: uploading ({boyut // 1024} KiB)..."))
    kod, c = nx_istek("/uploads", "POST", {"size_bytes": boyut, "filename": jar.name, "md5": md5.hexdigest()})
    yukleme = nx_veri(kod, c, t("yükleme oturumu", "upload session"))
    put = urllib.request.Request(yukleme["presigned_url"], data=veri, method="PUT", headers={
        "Content-Disposition": f'attachment; filename="{jar.name}"',
        "Content-MD5": base64.b64encode(md5.digest()).decode(), "Content-Type": "application/octet-stream"})
    try:
        urllib.request.urlopen(put, timeout=600).read()
    except urllib.error.HTTPError as e:
        hata(t(f"Nexus: dosya gönderilemedi ({e.code}): {e.read().decode('utf-8', 'ignore')[:300]}",
               f"Nexus: could not send the file ({e.code}): {e.read().decode('utf-8', 'ignore')[:300]}"))
    kod, c = nx_istek(f"/uploads/{yukleme['id']}/finalise", "POST")
    nx_veri(kod, c, t("yüklemeyi kapatma", "finalise"))
    for _ in range(60):
        kod, c = nx_istek(f"/uploads/{yukleme['id']}")
        if nx_veri(kod, c, t("yükleme durumu", "upload status")).get("state") == "available":
            break
        time.sleep(2)
    else:
        hata(t("Nexus: yükleme 2 dakikada hazır olmadı.", "Nexus: the upload was not ready after 2 minutes."))
    govde = {"upload_id": yukleme["id"], "name": ad, "version": surum, "file_category": kategori}
    if aciklama:
        govde["description"] = aciklama
    govde["update_mod_version"] = ayar.get("nexus_surum_guncelle", "true") == "true"
    if dosya_id:
        govde["archive_existing_file"] = ayar.get("nexus_eskiyi_arsivle", "false") == "true"
        kod, c = nx_istek(f"/mod-files/{dosya_id}/versions", "POST", govde)
        sonuc = nx_veri(kod, c, t("sürüm oluşturma", "version creation"))
    else:
        govde["mod_id"] = plan["mod_uid"]
        if kategori == "main":
            govde["primary_mod_manager_download"] = True
        kod, c = nx_istek("/mod-files", "POST", govde)
        sonuc = nx_veri(kod, c, t("dosya oluşturma", "file creation"))
        ayar["nexus_file_id"] = str((sonuc.get("file") or sonuc).get("id", ""))
    print(t(f"  Nexus: {surum} yüklendi.", f"  Nexus: {surum} uploaded."))
    if changelog_metni.strip():
        kod, c = nx_istek(f"/mods/{plan['mod_uid']}/changelogs", "POST",
                          {"version": surum, "changelog": changelog_metni.strip()[:65535]})
        if kod in (200, 201):
            print(t("  Nexus: değişiklik notu eklendi.", "  Nexus: changelog added."))
        else:
            print(t(f"  UYARI: Nexus değişiklik notu eklenemedi ({kod}): {json.dumps(c, ensure_ascii=False)[:300]}",
                    f"  WARNING: could not add the Nexus changelog ({kod}): {json.dumps(c, ensure_ascii=False)[:300]}"))
    return True



def nexus_sayfa(proje, kabul_edildi, prova):
    """aciklamalar/<proje>.txt (Markdown) → Nexus BBCode; mod sayfasının kısa ve tam açıklamasını günceller."""
    from nexus_bbcode import md_bbcode
    if not os.environ.get("NEXUS_TOKEN"):
        hata(t("NEXUS_TOKEN tanımlı değil (https://www.nexusmods.com/settings/api-keys)",
               "NEXUS_TOKEN is not set (https://www.nexusmods.com/settings/api-keys)"))
    dosya = DIZIN.parent / "aciklamalar" / f"{proje}.txt"
    if not dosya.exists():
        hata(t(f"Açıklama dosyası yok: {dosya}", f"Description file not found: {dosya}"))
    ust, _, govde = dosya.read_text("utf-8").partition("\n---\n")
    kisa = re.sub(r"\s+", " ", ust.replace("Short description:", "")).strip()
    bb = md_bbcode(govde.strip())
    if not kisa or not bb:
        hata(t("Açıklama dosyasında kısa açıklama ya da gövde boş.", "The short description or body in the description file is empty."))
    mod_dizini = DIZIN / "modlar" / proje
    ayar_yolu = mod_dizini / "ayarlar.properties"
    ayar = ayar_oku(ayar_yolu)
    if not ayar.get("nexus_mod"):
        if not nx_adres_sor(ayar):
            return
        if not prova:
            mod_dizini.mkdir(parents=True, exist_ok=True)
            if not ayar_yolu.exists():
                ayar_yolu.write_text("# modyukle tarafından oluşturuldu.\n", "utf-8")
            ayar_yaz(ayar_yolu, ayar)
    oyun = ayar.get("nexus_oyun", "minecraft")
    kod, c = nx_istek(f"/games/{oyun}/mods/{ayar['nexus_mod']}")
    mod_uid = str(nx_veri(kod, c, t("mod sayfası sorgusu", "mod page lookup")).get("id", ""))
    if not mod_uid:
        hata(t("Nexus: mod kimliği alınamadı.", "Nexus: could not get the mod ID."))
    print(t(f"=== Nexus sayfası: {oyun}/mods/{ayar['nexus_mod']} ← aciklamalar/{proje}.txt",
            f"=== Nexus page: {oyun}/mods/{ayar['nexus_mod']} ← aciklamalar/{proje}.txt"))
    print(t("  Kısa açıklama:", "  Short description:"), kisa)
    print(t("  Tam açıklama (BBCode):", "  Full description (BBCode):"))
    for satir in bb.splitlines():
        print("    " + satir)
    if prova:
        print(t("  (prova) Gönderilmedi.", "  (dry run) Not sent."))
        return
    if not kabul_edildi and not evet(sor(t("  Bu metin Nexus sayfasına gönderilsin mi? (e/h)", "  Send this text to the Nexus page? (y/n)"), t("h", "n"))):
        print(t("  Gönderilmedi.", "  Not sent."))
        return
    kod, c = nx_istek(f"/mods/{mod_uid}", "PATCH", {"summary": kisa, "description": bb})
    if kod not in (200, 204):
        hata(t(f"Nexus: sayfa güncellenemedi ({kod}): {json.dumps(c, ensure_ascii=False)[:500]}",
               f"Nexus: could not update the page ({kod}): {json.dumps(c, ensure_ascii=False)[:500]}"))
    print(t("  Nexus: sayfa açıklaması güncellendi.", "  Nexus: page description updated."))


def _main():
    sys.stdout.reconfigure(line_buffering=True)
    bayraklar = {"--prova", "--incele", "--evet"}
    kaynak_dizin = next((Path(a.split("=", 1)[1]).expanduser() for a in sys.argv[1:] if a.startswith("--kaynak=")), None)
    yukleme_adi = next((a.split("=", 1)[1].strip() for a in sys.argv[1:] if a.startswith("--dosya-adi=")), "")
    KAYNAK_HARIC.update(x for a in sys.argv[1:] if a.startswith("--haric=") for x in a.split("=", 1)[1].split(",") if x)
    etiket = next((a.split("=", 1)[1].strip() for a in sys.argv[1:] if a.startswith("--etiket=")), "")
    if etiket and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}", etiket):
        hata(t(f"Geçersiz etiket: {etiket!r} (harf, rakam, . _ - / kullan)", f"Invalid tag: {etiket!r} (use letters, digits, . _ - /)"))
    argv = [a for a in sys.argv[1:] if a not in bayraklar and not a.startswith(("--kaynak=", "--dosya-adi=", "--haric=", "--etiket="))]
    if argv[:1] == ["kaynak"]:
        if len(argv) != 3:
            hata(t("Kullanım: modyukle kaynak <proje> <çalışma alanı> [--prova]", "Usage: modyukle kaynak <project> <workspace> [--prova]"))
        proje = re.sub(r"[^a-z0-9_]+", "_", argv[1].lower().replace("-", "_")).strip("_")
        ayar = ayar_oku(DIZIN / "modlar" / proje / "ayarlar.properties")
        if not ayar.get("github_repo"):
            hata(t(f"{proje} için kayıtlı GitHub reposu yok.", f"No GitHub repo registered for {proje}."))
        ws = Path(argv[2]).expanduser().resolve()
        if not ws.is_dir():
            hata(t(f"Klasör yok: {ws}", f"Folder not found: {ws}"))
        return gh_kaynak_yukle(ayar["github_repo"], ws, "?", ayar.get("github_dal", "main"), "--prova" in sys.argv[1:], mesaj="Update source code")
    if argv[:1] == ["sayfa"]:
        if len(argv) != 2:
            hata(t("Kullanım: modyukle sayfa <proje> [--prova] [--evet]", "Usage: modyukle sayfa <project> [--prova] [--evet]"))
        proje = re.sub(r"[^a-z0-9_]+", "_", argv[1].lower().replace("-", "_")).strip("_")
        return nexus_sayfa(proje, "--evet" in sys.argv[1:], "--prova" in sys.argv[1:])
    prova = "--prova" in sys.argv[1:]
    incele = "--incele" in sys.argv[1:]
    if len(argv) != 3:
        print(__doc__)
        mevcut = sorted(p.name for p in (DIZIN / "modlar").iterdir() if p.is_dir() and p.name != "ornek")
        print(t("Kayıtlı projeler:", "Registered projects:"), ", ".join(mevcut) or t("yok", "none"))
        sys.exit(1)
    platform_arg, proje_arg, jar_arg = argv
    platformlar = PLATFORMLAR if platform_arg == "hepsi" else [p.strip() for p in platform_arg.lower().split(",")]
    for p in platformlar:
        if p not in PLATFORMLAR:
            hata(t(f"Bilinmeyen platform: {p}  (modrinth, github, curseforge, nexus, hepsi)", f"Unknown platform: {p}  (modrinth, github, curseforge, nexus, hepsi)"))
    jar = Path(jar_arg).expanduser().resolve()
    if not jar.is_file():
        hata(t(f"Dosya yok: {jar}", f"File not found: {jar}"))

    proje = re.sub(r"[^a-z0-9_]+", "_", proje_arg.lower().replace("-", "_")).strip("_")
    slug = proje.replace("_", "-")
    bilgi = jar_bilgisi(jar)
    if yukleme_adi:
        import shutil, tempfile
        yukleme_adi = Path(yukleme_adi).name
        if not yukleme_adi.lower().endswith(".jar"):
            yukleme_adi += ".jar"
        if yukleme_adi != jar.name:
            klasor = Path(tempfile.mkdtemp(prefix="modyukle-ad-"))
            GECICI_DIZINLER.append(klasor)
            shutil.copy2(jar, klasor / yukleme_adi)
            jar = klasor / yukleme_adi
            print(t(f"  Yüklenecek dosya adı: {yukleme_adi}", f"  Upload file name: {yukleme_adi}"))
    print(f"=== {bilgi['ad']} {bilgi['surum']} | {bilgi['yukleyici']} {bilgi['mc']} | proje: {proje}")
    if bilgi["modid"] != proje:
        print(t(f"  Not: jar'daki modId '{bilgi['modid']}', proje adı '{proje}'.", f"  Note: modId in the jar is '{bilgi['modid']}', project name is '{proje}'."))

    mod_dizini = DIZIN / "modlar" / proje
    ayar_yolu = mod_dizini / "ayarlar.properties"
    ayar = ayar_oku(ayar_yolu)

    gorevler = []
    mr_id = ""
    if "modrinth" in platformlar:
        mr_id = mr_proje_hazirla(proje, slug, bilgi, ayar, prova)
        if mr_id:
            ayar["modrinth_id"] = mr_id
            ayar.setdefault("ortam", "server_only" if bilgi["sadece_sunucu"] else "client_and_server")
            if "gerekli" not in ayar:
                ayar["gerekli"] = ",".join(mr_bagimliliklari_dogrula(bilgi["gerekli"]))
                ayar["istege_bagli"] = ",".join(mr_bagimliliklari_dogrula(bilgi["istege"]))
            if mr_surum_var_mi(mr_id, bilgi["surum"]):
                print(t(f"  Modrinth: {bilgi['surum']} zaten yüklü, atlanıyor.", f"  Modrinth: {bilgi['surum']} already uploaded, skipping."))
            else:
                gorevler.append("publishModrinth")
    if "github" in platformlar:
        repo = gh_proje_hazirla(slug, bilgi, ayar, prova)
        if repo:
            ayar["github_repo"] = repo
            ayar.setdefault("github_dal", "main")
            etiket_adi = etiket or f"v{bilgi['surum']}"
            if gh("release", "view", etiket_adi, "-R", repo).returncode == 0:
                print(t(f"  GitHub: {etiket_adi} zaten yüklü, atlanıyor.", f"  GitHub: {etiket_adi} already uploaded, skipping."))
            else:
                if kaynak_dizin:
                    gh_kaynak_yukle(repo, kaynak_dizin, bilgi["surum"], ayar["github_dal"], prova)
                gorevler.append("publishGithub")
    if "curseforge" in platformlar:
        if not os.environ.get("CURSEFORGE_TOKEN"):
            hata(t("CURSEFORGE_TOKEN tanımlı değil", "CURSEFORGE_TOKEN is not set"))
        if not ayar.get("curseforge_id"):
            print(t("  CurseForge'da proje API ile oluşturulamaz. Sitede oluştur (curseforge.com → Create Project),",
                    "  CurseForge projects cannot be created via the API. Create it on the site (curseforge.com → Create Project),"))
            cf = sor(t("  sonra Project ID'yi gir (boş = CurseForge'u atla)", "  then enter the Project ID (empty = skip CurseForge)"))
            if cf:
                ayar["curseforge_id"] = cf
                ayar["gerekli_curseforge"] = sor(t("  CurseForge'daki gerekli bağımlılık slug'ları, virgülle", "  Required dependency slugs on CurseForge, comma-separated"),
                                                 ",".join(bilgi["gerekli"]))
        else:
            print(t(f"  CurseForge: proje zaten kayıtlı ({ayar['curseforge_id']}), yenisi oluşturulmayacak.", f"  CurseForge: project already registered ({ayar['curseforge_id']}), not creating a new one."))
        if ayar.get("curseforge_id"):
            gorevler.append("publishCurseforge")
        else:
            print(t("  CurseForge atlandı.", "  CurseForge skipped."))

    nexus_plani = None
    if "nexus" in platformlar:
        nexus_plani = nx_hazirla(ayar, platform_arg == "hepsi")

    if not prova or ayar_yolu.exists():
        mod_dizini.mkdir(parents=True, exist_ok=True)
        if not ayar_yolu.exists():
            ayar_yolu.write_text("# modyukle tarafından oluşturuldu. Boş bırakılan platforma yüklenmez.\n", "utf-8")
        ayar_yaz(ayar_yolu, ayar)
    changelog = mod_dizini / "changelog.txt"

    def changelog_metni():
        return changelog.read_text("utf-8") if changelog.exists() else ""

    def nexus_calistir():
        if not nexus_plani:
            return False
        yapildi = nx_yukle(nexus_plani, jar, bilgi, changelog_metni(), ayar, prova)
        if yapildi and not prova:
            ayar_yaz(ayar_yolu, ayar)   # yeni file id kaydedilsin
        return yapildi

    def changelog_arsivle():
        if changelog.exists() and changelog.read_text("utf-8").strip():
            arsiv = mod_dizini / f"changelog-{bilgi['surum']}.txt"
            changelog.rename(arsiv)
            changelog.write_text("", "utf-8")
            print(t(f"  Değişiklik notu {arsiv.name} olarak arşivlendi, changelog.txt bir sonraki sürüm için boşaltıldı.", f"  Changelog archived as {arsiv.name}; changelog.txt emptied for the next version."))

    if not gorevler:
        if nexus_calistir():
            if not prova:
                changelog_arsivle()
        else:
            print(t("Yüklenecek yeni sürüm yok.", "No new version to upload."))
        if mr_id and not prova:
            mr_ortam_ayarla(mr_id, bilgi["surum"], ayar["ortam"])
            mr_incelemeye_gonder(mr_id, incele)
        return

    if not changelog.exists() or not changelog.read_text("utf-8").strip():
        print(t(f"  Not: {changelog} boş, değişiklik notu olarak '{bilgi['ad']} {bilgi['surum']}' yazılacak.", f"  Note: {changelog} is empty, '{bilgi['ad']} {bilgi['surum']}' will be used as the changelog."))

    komut = [str(DIZIN / "gradlew"), "-p", str(DIZIN), "--console=plain", *gorevler,
             f"-Pmod={proje}", f"-Pjar={jar}", *([f"-Petiket={etiket}"] if etiket else []), f"-Pad={bilgi['ad']}", f"-Psurum={bilgi['surum']}",
             f"-Pmc={bilgi['mc']}", f"-Pyukleyici_turu={bilgi['yukleyici']}",
             f"-Psadece_sunucu={'true' if bilgi['sadece_sunucu'] else 'false'}"]
    komut.append("-PdryRun" if prova else "-q")
    print((t("PROVA: ", "DRY RUN: ") if prova else t("Yükleniyor: ", "Uploading: ")) + ", ".join(g.removeprefix("publish") for g in gorevler))
    r = subprocess.run(komut)
    if r.returncode != 0:
        hata(t("Yükleme başarısız (yukarıdaki çıktıya bak).", "Upload failed (see the output above)."))
    nexus_calistir()
    if not prova:
        changelog_arsivle()
        if mr_id:
            mr_ortam_ayarla(mr_id, bilgi["surum"], ayar["ortam"])
            mr_incelemeye_gonder(mr_id, incele)
        print(t("Bitti.", "Done."))


GECICI_DIZINLER = []


def main():
    """--prova: Gradle'ın dry-run'ı ayarlar.properties'i okuduğu için dosya geçici yazılır, bitince eski hâline döner."""
    yedek = {}
    if "--prova" in sys.argv[1:]:
        for yol in (DIZIN / "modlar").glob("*/ayarlar.properties"):
            yedek[yol] = yol.read_text("utf-8")
        onceden_var = {d for d in (DIZIN / "modlar").iterdir() if d.is_dir()}
    try:
        _main()
    finally:
        import shutil
        for d in GECICI_DIZINLER:
            shutil.rmtree(d, ignore_errors=True)
        if yedek or "--prova" in sys.argv[1:]:
            for yol, metin in yedek.items():
                yol.write_text(metin, "utf-8")
            for d in (DIZIN / "modlar").iterdir():  # prova sırasında yeni açılan proje klasörünü sil
                if d.is_dir() and d not in onceden_var and not any(d.iterdir()) :
                    d.rmdir()


if __name__ == "__main__":
    main()
