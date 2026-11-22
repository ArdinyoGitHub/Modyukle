#!/usr/bin/env python3
"""Modyukle — graphical front end for modyukle.
Runs modyukle.py in the background; its questions show up as dialogs.
Default language: English. Turkish can be selected in Settings → Language."""
import html, json, os, re, subprocess, sys, time
from pathlib import Path

from PyQt6.QtCore import QProcess, QProcessEnvironment, QSettings, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QFont, QGuiApplication, QIcon, QTextCursor
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QFrame, QRadioButton, QScrollArea, QSizePolicy, QSplitter, QTabWidget, QToolBar, QVBoxLayout, QWidget,
)

DIZIN = Path(__file__).resolve().parent
sys.path.insert(0, str(DIZIN))
import modyukle  # noqa: E402  (jar_bilgisi için)

SOR_ISARETI = "\x1eSOR "
AYAR = QSettings("ardao", "modyukle-gui")
DILLER = [("en", "English"), ("tr", "Türkçe")]
DIL = AYAR.value("dil", "en")
if DIL not in dict(DILLER):
    DIL = "en"

# anahtar: (English, Türkçe)
S = {
    "title": ("Modyukle", "Modyukle"),
    "settings": ("Settings", "Ayarlar"),
    "settings_tip": ("Language and API keys (Ctrl+,)", "Dil ve API anahtarları (Ctrl+,)"),
    "jar_group": ("Jar file (you can drag && drop it here)", "Jar dosyası (sürükleyip bırakabilirsin)"),
    "src_group": ("Game and source", "Oyun ve kaynak"),
    "game": ("Game:", "Oyun:"),
    "src_ready": ("Ready .jar", "Hazır .jar"),
    "src_build": ("Build from workspace", "Çalışma alanından derle"),
    "ws_group": ("Mod workspace folder (contains gradlew)", "Mod çalışma alanı klasörü (gradlew içeren)"),
    "jar_group_built": ("Built jar (filled in after the build)", "Derlenen jar (derlemeden sonra dolar)"),
    "pick_ws": ("Pick a workspace folder that contains gradlew.", "gradlew içeren bir çalışma alanı klasörü seç."),
    "building": ("Building {} …", "Derleniyor: {} …"),
    "build_fail": ("Build failed (exit code {}).", "Derleme başarısız (çıkış kodu {})."),
    "build_nojar": ("Build finished but no jar was found in build/libs.", "Derleme bitti ama build/libs içinde jar bulunamadı."),
    "build_ok": ("Build finished: {}", "Derleme bitti: {}"),
    "up_name": ("Upload file name:", "Yüklenecek dosya adı:"),
    "up_name_ph": ("empty = keep the jar's own name", "boş = jar'ın kendi adı"),
    "tag_label": ("GitHub tag:", "GitHub etiketi:"),
    "tag_ph": ("empty = v<version>", "boş = v<sürüm>"),
    "browse": ("Browse…", "Gözat…"),
    "refresh_tip": ("Refresh the list of jars in the home folder", "Ev dizinindeki jar listesini yenile"),
    "no_jar": ("No jar selected.", "Jar seçilmedi."),
    "no_file": ("File not found.", "Dosya yok."),
    "bad_jar": ("Could not read this jar (not a NeoForge/Forge mod?).", "Bu jar okunamadı (NeoForge/Forge modu değil mi?)."),
    "read_fail": ("Could not read: {}", "Okunamadı: {}"),
    "deps": ("requires: {}", "gerekli: {}"),
    "none": ("none", "yok"),
    "server_only": ("server only", "yalnızca sunucu"),
    "project_group": ("Project", "Proje"),
    "project_name": ("Project name:", "Proje adı:"),
    "registered": ("Registered on: {}", "Kayıtlı: {}"),
    "no_platform_yet": ("no platform yet", "henüz hiçbir platform"),
    "new_project": ("New project — will be created on first upload.", "Yeni proje — ilk yüklemede oluşturulacak."),
    "platforms": ("Platforms", "Platformlar"),
    "options": ("Options", "Seçenekler"),
    "dry_run": ("Dry run (don't really upload)", "Prova (gerçekten yükleme)"),
    "auto_review": ("Submit drafts for review without asking", "Taslaksa sormadan incelemeye gönder"),
    "tab_changelog": ("Changelog", "Değişiklik notu"),
    "tab_props": ("ayarlar.properties", "ayarlar.properties"),
    "tab_desc": ("Page description", "Sayfa açıklaması"),
    "ph_changelog": ("Changes in this version (if empty, '<name> <version>' is used).",
                     "Bu sürümdeki değişiklikler (boşsa '<ad> <sürüm>' yazılır)."),
    "ph_props": ("This file is created automatically on the first upload.", "Proje ilk yüklemede bu dosya otomatik oluşturulur."),
    "ph_desc": ("Modrinth page description (only used when the project is first created).\n"
                "Format: a 'Short description: ...' line, then a '---' line, then the body.",
                "Modrinth sayfa açıklaması (yalnızca proje ilk oluşturulurken kullanılır).\n"
                "Biçim: 'Short description: ...' satırı, sonra '---' satırı, sonra gövde."),
    "save_files": ("Save files", "Dosyaları kaydet"),
    "clear_out": ("Clear output", "Çıktıyı temizle"),
    "stop": ("Stop", "Durdur"),
    "nexus_page": ("Update Nexus page", "Nexus sayfasını güncelle"),
    "nexus_page_tip": ("Converts the 'Page description' tab (Markdown) to Nexus BBCode and sends the short + full description "
                       "to the mod's Nexus page. With 'Dry run' checked it only shows a preview.",
                       "'Sayfa açıklaması' sekmesini (Markdown) Nexus BBCode'una çevirip kısa + tam açıklamayı modun Nexus "
                       "sayfasına gönderir. 'Prova' işaretliyse yalnızca önizleme gösterir."),
    "upload": ("Upload", "Yükle"),
    "run_dry": ("Run dry run", "Prova yap"),
    "saved": ("Saved: {}", "Kaydedildi: {}"),
    "no_changes": ("no changes", "değişiklik yok"),
    "pick_jar": ("Pick a valid jar file.", "Geçerli bir jar dosyası seç."),
    "empty_project": ("Project name is empty.", "Proje adı boş."),
    "pick_platform": ("Select at least one platform.", "En az bir platform seç."),
    "real_upload": ("Real upload", "Gerçek yükleme"),
    "real_upload_q": ("<b>{}</b><br>will <b>really</b> be uploaded to {}. Continue?",
                      "<b>{}</b><br>{} platformlarına <b>gerçekten</b> yüklenecek. Devam?"),
    "proc_fail": ("ERROR: could not start the process ({})", "HATA: süreç başlatılamadı ({})"),
    "asks": ("modyukle asks", "modyukle soruyor"),
    "empty_ans": ("(empty)", "(boş)"),
    "finished": ("— finished (exit code {}) —", "— işlem bitti (çıkış kodu {}) —"),
    "running_quit": ("An upload is running. Stop it and quit?", "Yükleme sürüyor. Durdurup çıkayım mı?"),
    "yes": ("Yes", "Evet"),
    "no": ("No", "Hayır"),
    # settings dialog
    "set_title": ("Settings", "Ayarlar"),
    "tab_general": ("General", "Genel"),
    "tab_api": ("API keys", "API anahtarları"),
    "language": ("Language", "Dil"),
    "language_lbl": ("Interface language:", "Arayüz dili:"),
    "language_note": ("Applied immediately. The output of the upload tool follows this language too.",
                      "Hemen uygulanır. Yükleme aracının çıktısı da bu dili izler."),
    "welcome": ("<b>Welcome!</b> To upload mods you need an API key for each platform. Enter what you have now; "
                "you can add the rest later from <i>Settings → API keys</i>.<br><br>",
                "<b>Hoş geldin!</b> Modları yükleyebilmek için platform anahtarlarına ihtiyaç var. "
                "İstediğini şimdi gir, kalanını sonra <i>Ayarlar → API anahtarları</i> bölümünden ekleyebilirsin.<br><br>"),
    "api_intro": ("Keys are stored on this computer as fish universal variables; the <code>modyukle</code> "
                  "command in the terminal uses the same keys. Fields left empty stay unchanged.",
                  "Anahtarlar bu bilgisayarda fish evrensel değişkeni olarak saklanır; terminaldeki "
                  "<code>modyukle</code> de aynı anahtarları kullanır. Boş bıraktığın alan değişmez."),
    "key": ("Key:", "Anahtar:"),
    "show": ("Show", "Göster"),
    "delete_key": ("Delete the saved key", "Kayıtlı anahtarı sil"),
    "where_to_get": ("Where to get it: ", "Nereden alınır: "),
    "mr_hint": ("(permissions: Create versions, Write projects, Read projects)", "(izinler: Create versions, Write projects, Read projects)"),
    "cf_hint": ("(the Upload API token is needed for uploading)", "(yükleme için Upload API token'ı gerekir)"),
    "nx_hint": ("(personal API key of the account that owns the mod page)", "(mod sayfasının sahibi hesabın kişisel API anahtarı)"),
    "saved_key": ("saved (…{})", "kayıtlı (…{})"),
    "saved_key_short": ("saved", "kayıtlı"),
    "not_set": ("not set", "girilmedi"),
    "gh_ok": ("Logged in: <b>{}</b> (no key needed, <code>gh</code> is used)",
              "Giriş yapılmış: <b>{}</b> (anahtar gerekmez, <code>gh</code> kullanılıyor)"),
    "gh_no_short": ("<span style='color:#d9a43a'>Not logged in to GitHub.</span>",
                    "<span style='color:#d9a43a'>GitHub'a giriş yapılmamış.</span>"),
    "gh_login": ("Log in to GitHub…", "GitHub'a giriş yap…"),
    "gh_logout": ("Log out", "Çıkış yap"),
    "gh_login_title": ("GitHub login", "GitHub girişi"),
    "gh_wait": ("Starting login…", "Giriş başlatılıyor…"),
    "gh_code_msg": ("Enter this one-time code on the GitHub page that just opened in your browser:",
                    "Tarayıcıda açılan GitHub sayfasına bu tek kullanımlık kodu gir:"),
    "gh_copy": ("Copy code", "Kodu kopyala"),
    "gh_open": ("Open GitHub page", "GitHub sayfasını aç"),
    "gh_ok_login": ("Logged in to GitHub.", "GitHub'a giriş yapıldı."),
    "gh_login_fail": ("Login failed or was cancelled.\n{}", "Giriş başarısız oldu ya da iptal edildi.\n{}"),
    "gh_missing": ("The <code>gh</code> command (GitHub CLI) was not found. Install it first.",
                   "<code>gh</code> komutu (GitHub CLI) bulunamadı. Önce onu kurmalısın."),
    "gh_logout_q": ("Log out of GitHub account <b>{}</b>?<br><br>This also logs out <code>gh</code> in the terminal "
                    "and other projects, because they share the same login.",
                    "<b>{}</b> GitHub hesabından çıkılsın mı?<br><br>Terminaldeki <code>gh</code> ve diğer projeler "
                    "aynı girişi kullandığı için onlar da çıkış yapmış olur."),
    "gh_logout_fail": ("Could not log out:\n{}", "Çıkış yapılamadı:\n{}"),
    "save": ("Save", "Kaydet"),
    "cancel": ("Cancel", "Vazgeç"),
    "not_now": ("Not now", "Şimdi değil"),
    "save_fail": ("Could not save: {}", "Kaydedilemedi: {}"),
    "fish_fail": ("fish command failed", "fish komutu başarısız"),
}


def T(anahtar, *a):
    metin = S[anahtar][0 if DIL == "en" else 1]
    return metin.format(*a) if a else metin


TOKENLAR = [
    ("MODRINTH_TOKEN", "Modrinth", '<a href="https://modrinth.com/settings/pats">modrinth.com/settings/pats</a>', "mr_hint"),
    ("CURSEFORGE_TOKEN", "CurseForge", '<a href="https://console.curseforge.com/#/api-keys">console.curseforge.com → API keys</a>', "cf_hint"),
    ("NEXUS_TOKEN", "Nexus Mods", '<a href="https://www.nexusmods.com/settings/api-keys">nexusmods.com/settings/api-keys</a>', "nx_hint"),
]
PLATFORMLAR = [("modrinth", "Modrinth"), ("github", "GitHub"), ("curseforge", "CurseForge"), ("nexus", "Nexus Mods")]


def proje_adi(ad):
    return re.sub(r"[^a-z0-9_]+", "_", ad.lower().replace("-", "_")).strip("_")


def evet_hayir_kutusu(parent, baslik, metin, varsayilan_evet=False):
    k = QMessageBox(QMessageBox.Icon.Question, baslik, metin,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, parent)
    k.button(QMessageBox.StandardButton.Yes).setText(T("yes"))
    k.button(QMessageBox.StandardButton.No).setText(T("no"))
    k.setDefaultButton(QMessageBox.StandardButton.Yes if varsayilan_evet else QMessageBox.StandardButton.No)
    return k.exec() == QMessageBox.StandardButton.Yes


# ---------- API anahtarları (fish evrensel değişkenleri) ----------
def anahtar_oku(ad):
    """Önce ortam, yoksa fish evrensel değişkeni (terminaldeki modyukle de aynı yerden okur)."""
    deger = os.environ.get(ad)
    if deger:
        return deger
    try:
        return subprocess.run(["fish", "-c", f"echo -n ${ad}"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return ""


def anahtar_yaz(ad, deger):
    """fish evrensel değişkeni olarak saklar (boş = sil). Değer komut satırına değil argv'ye gider."""
    if deger:
        cmd = ["fish", "-c", "set -Ux $argv[1] $argv[2]", ad, deger]
    else:
        cmd = ["fish", "-c", "set -e -U $argv[1]; set -e $argv[1]; true", ad]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or T("fish_fail"))
    if deger:
        os.environ[ad] = deger
    else:
        os.environ.pop(ad, None)


def tokenlari_tamamla(env):
    for ad, _, _, _ in TOKENLAR:
        if not env.contains(ad):
            deger = anahtar_oku(ad)
            if deger:
                env.insert(ad, deger)


def maske(deger):
    return T("saved_key", deger[-4:]) if len(deger) > 8 else (T("saved_key_short") if deger else T("not_set"))


class GhGirisPenceresi(QDialog):
    """`gh auth login --web` çalıştırır; tek kullanımlık kodu gösterir, GitHub sayfasını tarayıcıda açar."""
    URL = "https://github.com/login/device"

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(T("gh_login_title"))
        self.setMinimumWidth(460)
        self.cikti = ""
        v = QVBoxLayout(self)
        self.mesaj = QLabel(T("gh_wait"))
        self.mesaj.setWordWrap(True)
        v.addWidget(self.mesaj)
        self.kod = QLabel("")
        self.kod.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.kod.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.kod.setStyleSheet("font-size:26pt;font-weight:700;letter-spacing:3px;padding:10px;")
        self.kod.setMinimumHeight(80)
        v.addWidget(self.kod)
        sat = QHBoxLayout()
        self.kopyala = QPushButton(T("gh_copy"))
        self.kopyala.setEnabled(False)
        self.kopyala.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.kod.text()))
        self.ac = QPushButton(T("gh_open"))
        self.ac.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.URL)))
        iptal = QPushButton(T("cancel"))
        iptal.clicked.connect(self.reject)
        sat.addWidget(self.kopyala)
        sat.addWidget(self.ac)
        sat.addStretch()
        sat.addWidget(iptal)
        v.addLayout(sat)

        self.p = QProcess(self)
        self.p.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.p.readyReadStandardOutput.connect(self.okunan)
        self.p.finished.connect(self.bitti)
        self.p.errorOccurred.connect(self.hata)
        self.p.start("gh", ["auth", "login", "-h", "github.com", "-p", "https", "--web", "--skip-ssh-key"])
        self.p.closeWriteChannel()

    def okunan(self):
        self.cikti += bytes(self.p.readAllStandardOutput()).decode("utf-8", "replace")
        m = re.search(r"\b([A-Z0-9]{4}-[A-Z0-9]{4})\b", self.cikti)
        if m and not self.kod.text():
            self.kod.setText(m.group(1))
            self.mesaj.setText(T("gh_code_msg"))
            self.kopyala.setEnabled(True)
            QGuiApplication.clipboard().setText(m.group(1))
            QDesktopServices.openUrl(QUrl(self.URL))

    def bitti(self, kod, _d):
        if kod == 0:
            self.accept()
        else:
            QMessageBox.warning(self, T("gh_login_title"), T("gh_login_fail", self.cikti.strip()[-300:]))
            self.reject()

    def hata(self, h):
        if h == QProcess.ProcessError.FailedToStart:
            QMessageBox.warning(self, T("gh_login_title"), T("gh_missing"))
            self.reject()

    def reject(self):
        if self.p.state() != QProcess.ProcessState.NotRunning:
            self.p.finished.disconnect(self.bitti)
            self.p.kill()
            self.p.waitForFinished(2000)
        super().reject()


class AyarPenceresi(QDialog):
    def __init__(self, parent, ilk=False):
        super().__init__(parent)
        self.secilen_dil = DIL
        self.setWindowTitle(T("set_title"))
        self.setMinimumSize(660, 640)
        v = QVBoxLayout(self)
        self.sekmeler = QTabWidget()
        v.addWidget(self.sekmeler)

        # --- General ---
        genel = QWidget()
        gl = QVBoxLayout(genel)
        dil_kutu = QGroupBox(T("language"))
        df = QFormLayout(dil_kutu)
        self.dil = QComboBox()
        for kod, ad in DILLER:
            self.dil.addItem(ad, kod)
        self.dil.setCurrentIndex(self.dil.findData(DIL))
        df.addRow(T("language_lbl"), self.dil)
        not_ = QLabel(T("language_note"))
        not_.setWordWrap(True)
        df.addRow("", not_)
        gl.addWidget(dil_kutu)
        gl.addStretch()
        self.sekmeler.addTab(genel, T("tab_general"))

        # --- API keys ---
        api = QWidget()
        al = QVBoxLayout(api)
        giris = QLabel((T("welcome") if ilk else "") + T("api_intro"))
        giris.setWordWrap(True)
        al.addWidget(giris)
        self.alanlar, self.silinecek = {}, {}
        for ad, gorunen, baglanti, ipucu in TOKENLAR:
            kutu = QGroupBox(gorunen)
            f = QFormLayout(kutu)
            mevcut = anahtar_oku(ad)
            e = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
            e.setPlaceholderText(maske(mevcut))
            goster = QCheckBox(T("show"))
            goster.toggled.connect(lambda a, e=e: e.setEchoMode(
                QLineEdit.EchoMode.Normal if a else QLineEdit.EchoMode.Password))
            sat = QHBoxLayout()
            sat.addWidget(e, 1)
            sat.addWidget(goster)
            f.addRow(T("key"), sat)
            if mevcut:
                sil = QCheckBox(T("delete_key"))
                self.silinecek[ad] = sil
                f.addRow("", sil)
            yardim = QLabel(T("where_to_get") + baglanti + " " + T(ipucu))
            yardim.setOpenExternalLinks(True)
            yardim.setWordWrap(True)
            f.addRow("", yardim)
            self.alanlar[ad] = e
            al.addWidget(kutu)
        gh = QGroupBox("GitHub")
        ghl = QVBoxLayout(gh)
        self.gh_durum = QLabel()
        self.gh_durum.setWordWrap(True)
        ghl.addWidget(self.gh_durum)
        gsat = QHBoxLayout()
        self.gh_giris = QPushButton(T("gh_login"))
        self.gh_giris.clicked.connect(self.gh_giris_yap)
        self.gh_cikis = QPushButton(T("gh_logout"))
        self.gh_cikis.clicked.connect(self.gh_cikis_yap)
        gsat.addWidget(self.gh_giris)
        gsat.addWidget(self.gh_cikis)
        gsat.addStretch()
        ghl.addLayout(gsat)
        self.gh_login_adi = ""
        al.addWidget(gh)
        al.addStretch()
        self.gh_yenile()
        kaydir = QScrollArea()
        kaydir.setWidgetResizable(True)
        kaydir.setFrameShape(QFrame.Shape.NoFrame)
        kaydir.setWidget(api)
        self.sekmeler.addTab(kaydir, T("tab_api"))
        if ilk:
            self.sekmeler.setCurrentIndex(1)

        d = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        d.button(QDialogButtonBox.StandardButton.Save).setText(T("save"))
        d.button(QDialogButtonBox.StandardButton.Cancel).setText(T("not_now") if ilk else T("cancel"))
        d.accepted.connect(self.kaydet)
        d.rejected.connect(self.reject)
        v.addWidget(d)

    def gh_yenile(self):
        self.gh_login_adi = ""
        try:
            r = subprocess.run(["gh", "api", "user", "-q", ".login"], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                self.gh_login_adi = r.stdout.strip()
        except FileNotFoundError:
            self.gh_durum.setText(T("gh_missing"))
            self.gh_giris.setVisible(False)
            self.gh_cikis.setVisible(False)
            return
        except Exception:
            pass
        if self.gh_login_adi:
            self.gh_durum.setText(T("gh_ok", html.escape(self.gh_login_adi)))
        else:
            self.gh_durum.setText(T("gh_no_short"))
        self.gh_giris.setVisible(not self.gh_login_adi)
        self.gh_cikis.setVisible(bool(self.gh_login_adi))

    def gh_giris_yap(self):
        if GhGirisPenceresi(self).exec() == QDialog.DialogCode.Accepted:
            QMessageBox.information(self, T("gh_login_title"), T("gh_ok_login"))
        self.gh_yenile()

    def gh_cikis_yap(self):
        if not evet_hayir_kutusu(self, T("gh_logout"), T("gh_logout_q", html.escape(self.gh_login_adi))):
            return
        cmd = ["gh", "auth", "logout", "-h", "github.com"] + (["-u", self.gh_login_adi] if self.gh_login_adi else [])
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            QMessageBox.warning(self, T("gh_logout"), T("gh_logout_fail", (r.stderr or r.stdout).strip()))
        self.gh_yenile()

    def kaydet(self):
        try:
            for ad, e in self.alanlar.items():
                yeni = e.text().strip()
                if yeni:
                    anahtar_yaz(ad, yeni)
                elif ad in self.silinecek and self.silinecek[ad].isChecked():
                    anahtar_yaz(ad, "")
        except Exception as ex:
            return QMessageBox.critical(self, T("set_title"), T("save_fail", ex))
        self.secilen_dil = self.dil.currentData()
        self.accept()


class Pencere(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon.fromTheme("cloud-upload", QIcon.fromTheme("document-send")))
        self.resize(1000, 780)
        self.setAcceptDrops(True)
        self.surec = None
        self.tampon = ""
        self.yuklu_proje = None

        # --- üst araç çubuğu: Ayarlar belirgin ---
        arac = QToolBar()
        arac.setMovable(False)
        arac.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        arac.setStyleSheet("QToolBar{spacing:6px;padding:4px;} QToolButton{font-weight:600;font-size:11pt;padding:6px 16px;border:1px solid palette(mid);border-radius:5px;}QToolButton:hover{background:palette(midlight);}")
        bosluk = QWidget()
        bosluk.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        arac.addWidget(bosluk)
        self.ayar_eylem = QAction("", self)
        self.ayar_eylem.setShortcut("Ctrl+,")
        self.ayar_eylem.triggered.connect(lambda: self.ayarlari_ac())
        arac.addAction(self.ayar_eylem)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, arac)

        merkez = QWidget()
        self.setCentralWidget(merkez)
        ana = QVBoxLayout(merkez)

        # --- oyun + kaynak türü ---
        self.kaynak_kutu = QGroupBox()
        kl = QHBoxLayout(self.kaynak_kutu)
        self.oyun_etiket = QLabel()
        self.oyun = QComboBox()
        self.oyun.addItem("Minecraft")  # ileride başka oyunlar eklenebilir
        self.r_hazir = QRadioButton()
        self.r_derle = QRadioButton()
        (self.r_derle if AYAR.value("kaynak", "hazir") == "derle" else self.r_hazir).setChecked(True)
        self.r_hazir.toggled.connect(self.kaynak_degisti)
        kl.addWidget(self.oyun_etiket)
        kl.addWidget(self.oyun)
        kl.addSpacing(24)
        kl.addWidget(self.r_hazir)
        kl.addWidget(self.r_derle)
        kl.addStretch()
        ana.addWidget(self.kaynak_kutu)

        self.ws_kutu = QGroupBox()
        wl = QHBoxLayout(self.ws_kutu)
        self.ws = QComboBox(editable=True)
        self.ws.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.ws.addItems([x for x in str(AYAR.value("calisma_alanlari", "")).split("\n") if x])
        self.ws_gozat = QPushButton(QIcon.fromTheme("folder-open"), "")
        self.ws_gozat.clicked.connect(self.ws_sec)
        wl.addWidget(self.ws, 1)
        wl.addWidget(self.ws_gozat)
        ana.addWidget(self.ws_kutu)
        self.derleme = None
        self.d_tampon = ""
        self._derlendi = False

        # --- jar ---
        self.jar_kutu = QGroupBox()
        jl = QVBoxLayout(self.jar_kutu)
        satir = QHBoxLayout()
        self.jar = QComboBox(editable=True)
        self.jar.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.jar.currentTextChanged.connect(self.jar_degisti)
        self.gozat = QPushButton(QIcon.fromTheme("document-open"), "")
        self.gozat.clicked.connect(self.jar_sec)
        self.yenile = QPushButton(QIcon.fromTheme("view-refresh"), "")
        self.yenile.clicked.connect(self.jarlari_listele)
        satir.addWidget(self.jar, 1)
        satir.addWidget(self.yenile)
        satir.addWidget(self.gozat)
        jl.addLayout(satir)
        self.jar_bilgi = QLabel("—")
        self.jar_bilgi.setTextFormat(Qt.TextFormat.RichText)
        self.jar_bilgi.setWordWrap(True)
        jl.addWidget(self.jar_bilgi)
        ad_satir = QHBoxLayout()
        self.ad_etiket = QLabel()
        self.yukleme_adi = QLineEdit()
        ad_satir.addWidget(self.ad_etiket)
        ad_satir.addWidget(self.yukleme_adi, 1)
        self.etiket_etiket = QLabel()
        self.etiket = QLineEdit()
        self.etiket.setMaximumWidth(180)
        ad_satir.addWidget(self.etiket_etiket)
        ad_satir.addWidget(self.etiket)
        jl.addLayout(ad_satir)
        ana.addWidget(self.jar_kutu)

        # --- proje + platform + seçenekler ---
        ust = QHBoxLayout()
        self.proje_kutu = QGroupBox()
        pf = QFormLayout(self.proje_kutu)
        self.proje = QComboBox(editable=True)
        self.proje.addItems(self.kayitli_projeler())
        self.proje.setCurrentText("")
        self.proje.currentTextChanged.connect(self.proje_degisti)
        self.proje_etiket = QLabel()
        pf.addRow(self.proje_etiket, self.proje)
        self.proje_durum = QLabel("")
        pf.addRow("", self.proje_durum)
        ust.addWidget(self.proje_kutu, 2)

        self.plat_kutu = QGroupBox()
        plv = QVBoxLayout(self.plat_kutu)
        self.platform_kutulari = {}
        secili = AYAR.value("platformlar", "modrinth,github")
        for kod, ad in PLATFORMLAR:
            k = QCheckBox(ad)
            k.setChecked(kod in secili.split(","))
            plv.addWidget(k)
            self.platform_kutulari[kod] = k
        ust.addWidget(self.plat_kutu, 1)

        self.sec_kutu = QGroupBox()
        sv = QVBoxLayout(self.sec_kutu)
        self.prova = QCheckBox()
        self.prova.setChecked(AYAR.value("prova", "true") == "true")
        self.incele = QCheckBox()
        self.incele.setChecked(AYAR.value("incele", "false") == "true")
        sv.addWidget(self.prova)
        sv.addWidget(self.incele)
        sv.addStretch()
        ust.addWidget(self.sec_kutu, 1)
        ana.addLayout(ust)

        # --- sekmeler + çıktı ---
        bolucu = QSplitter(Qt.Orientation.Vertical)
        self.sekmeler = QTabWidget()
        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.changelog = QPlainTextEdit()
        self.ayar_metni = QPlainTextEdit()
        self.ayar_metni.setFont(mono)
        self.aciklama = QPlainTextEdit()
        for w in (self.changelog, self.ayar_metni, self.aciklama):
            self.sekmeler.addTab(w, "")
        bolucu.addWidget(self.sekmeler)

        self.cikti = QPlainTextEdit(readOnly=True)
        self.cikti.setFont(mono)
        self.cikti.setMaximumBlockCount(5000)
        bolucu.addWidget(self.cikti)
        bolucu.setSizes([260, 360])
        ana.addWidget(bolucu, 1)

        # --- düğmeler ---
        alt = QHBoxLayout()
        self.kaydet_dugme = QPushButton(QIcon.fromTheme("document-save"), "")
        self.kaydet_dugme.clicked.connect(lambda: self.dosyalari_kaydet(bildir=True))
        self.temizle = QPushButton(QIcon.fromTheme("edit-clear"), "")
        self.temizle.clicked.connect(self.cikti.clear)
        self.durdur = QPushButton(QIcon.fromTheme("process-stop"), "")
        self.durdur.setEnabled(False)
        self.durdur.clicked.connect(self.surec_durdur)
        self.sayfa_dugme = QPushButton(QIcon.fromTheme("document-edit"), "")
        self.sayfa_dugme.clicked.connect(self.sayfa_guncelle)
        self.calistir = QPushButton(QIcon.fromTheme("cloud-upload", QIcon.fromTheme("go-up")), "")
        self.calistir.setDefault(True)
        self.calistir.setMinimumWidth(140)
        self.calistir.clicked.connect(self.baslat)
        self.prova.toggled.connect(self.dugme_metni)
        alt.addWidget(self.kaydet_dugme)
        alt.addWidget(self.temizle)
        alt.addWidget(self.sayfa_dugme)
        alt.addStretch()
        alt.addWidget(self.durdur)
        alt.addWidget(self.calistir)
        ana.addLayout(alt)

        self.jarlari_listele()
        self.dil_uygula()
        self.kaynak_degisti()
        QTimer.singleShot(0, self.ilk_acilis)

    # ---------- dil ----------
    def dil_uygula(self):
        self.setWindowTitle(T("title"))
        self.ayar_eylem.setText("⚙  " + T("settings"))
        self.ayar_eylem.setToolTip(T("settings_tip"))
        self.kaynak_kutu.setTitle(T("src_group"))
        self.oyun_etiket.setText(T("game"))
        self.r_hazir.setText(T("src_ready"))
        self.r_derle.setText(T("src_build"))
        self.ws_kutu.setTitle(T("ws_group"))
        self.ws_gozat.setText(T("browse"))
        self.kaynak_degisti()
        self.ad_etiket.setText(T("up_name"))
        self.yukleme_adi.setPlaceholderText(T("up_name_ph"))
        self.etiket_etiket.setText(T("tag_label"))
        self.etiket.setPlaceholderText(T("tag_ph"))
        self.gozat.setText(T("browse"))
        self.yenile.setToolTip(T("refresh_tip"))
        self.proje_kutu.setTitle(T("project_group"))
        self.proje_etiket.setText(T("project_name"))
        self.plat_kutu.setTitle(T("platforms"))
        self.sec_kutu.setTitle(T("options"))
        self.prova.setText(T("dry_run"))
        self.incele.setText(T("auto_review"))
        for i, k in enumerate(("tab_changelog", "tab_props", "tab_desc")):
            self.sekmeler.setTabText(i, T(k))
        self.changelog.setPlaceholderText(T("ph_changelog"))
        self.ayar_metni.setPlaceholderText(T("ph_props"))
        self.aciklama.setPlaceholderText(T("ph_desc"))
        self.kaydet_dugme.setText(T("save_files"))
        self.temizle.setText(T("clear_out"))
        self.durdur.setText(T("stop"))
        self.sayfa_dugme.setText(T("nexus_page"))
        self.sayfa_dugme.setToolTip(T("nexus_page_tip"))
        self.dugme_metni()
        self.jar_degisti(self.jar.currentText(), proje_ata=False)
        self.proje_durumu_yaz()

    def dil_degistir(self, kod):
        global DIL
        if kod and kod != DIL:
            DIL = kod
            AYAR.setValue("dil", kod)
            self.dil_uygula()

    def ayarlari_ac(self, ilk=False):
        d = AyarPenceresi(self, ilk=ilk)
        if d.exec() == QDialog.DialogCode.Accepted:
            self.dil_degistir(d.secilen_dil)

    def ilk_acilis(self):
        """Anahtarlar eksikse ilk açılışta bir kez sor; sonrası Ayarlar düğmesinden."""
        if AYAR.value("api_soruldu", "false") == "true":
            return
        if any(not anahtar_oku(ad) for ad, _, _, _ in TOKENLAR):
            AYAR.setValue("api_soruldu", "true")
            self.ayarlari_ac(ilk=True)

    # ---------- yardımcılar ----------
    def kayitli_projeler(self):
        return sorted(p.name for p in (DIZIN / "modlar").iterdir() if p.is_dir() and p.name != "ornek")

    def proje_dizini(self):
        ad = proje_adi(self.proje.currentText())
        return (DIZIN / "modlar" / ad) if ad else None

    def aciklama_yolu(self):
        ad = proje_adi(self.proje.currentText())
        return (DIZIN.parent / "aciklamalar" / f"{ad}.txt") if ad else None

    def dugme_metni(self):
        self.calistir.setText(T("run_dry") if self.prova.isChecked() else T("upload"))

    def yaz(self, metin, renk=None):
        if renk is None:
            if metin.startswith(("HATA", "ERROR")) or "FAILED" in metin:
                renk = "#e05252"
            elif "UYARI" in metin or "WARNING" in metin:
                renk = "#d9a43a"
            elif metin.startswith(("===", "Bitti", "Done")):
                renk = "#4caf7a"
        e = html.escape(metin).replace(" ", "&nbsp;") or "&nbsp;"
        self.cikti.appendHtml(f'<span style="color:{renk}">{e}</span>' if renk else e)
        self.cikti.moveCursor(QTextCursor.MoveOperation.End)

    # ---------- kaynak (hazır jar / derleme) ----------
    def kaynak_degisti(self, *_):
        derle = self.r_derle.isChecked()
        self.ws_kutu.setVisible(derle)
        self.jar_kutu.setTitle(T("jar_group_built") if derle else T("jar_group"))
        self.yenile.setVisible(not derle)
        AYAR.setValue("kaynak", "derle" if derle else "hazir")

    def ws_sec(self):
        yol = QFileDialog.getExistingDirectory(self, T("ws_group"), self.ws.currentText() or str(Path.home()))
        if yol:
            self.ws.setCurrentText(yol)

    def derle(self):
        ws = Path(self.ws.currentText().strip()).expanduser()
        if not (ws / "gradlew").is_file():
            return QMessageBox.warning(self, T("title"), T("pick_ws"))
        yollar = [self.ws.itemText(i) for i in range(self.ws.count())]
        if str(ws) not in yollar:
            self.ws.addItem(str(ws))
            yollar.append(str(ws))
        AYAR.setValue("calisma_alanlari", "\n".join(yollar))
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        self.d_tampon = ""
        self.derleme = QProcess(self)
        self.derleme.setProcessEnvironment(env)
        self.derleme.setWorkingDirectory(str(ws))
        self.derleme.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.derleme.readyReadStandardOutput.connect(self.derleme_okunan)
        self.derleme.finished.connect(lambda kod, _d: self.derleme_bitti(kod, ws))
        self.derleme.errorOccurred.connect(lambda h: self.yaz(T("proc_fail", h)))
        self.yaz(T("building", ws), "#7aa2d9")
        self.kilitle(True)
        self.derleme.start("sh", [str(ws / "gradlew"), "build", "--console=plain"])

    def derleme_okunan(self):
        self.d_tampon += bytes(self.derleme.readAllStandardOutput()).decode("utf-8", "replace")
        while "\n" in self.d_tampon:
            satir, self.d_tampon = self.d_tampon.split("\n", 1)
            self.yaz(satir.rstrip("\r"))

    def derleme_bitti(self, kod, ws):
        if self.d_tampon.strip():
            self.yaz(self.d_tampon.rstrip())
        self.d_tampon = ""
        self.derleme = None
        self.kilitle(False)
        if kod != 0:
            return self.yaz(T("build_fail", kod), "#e05252")
        jarlar = [j for j in (ws / "build" / "libs").glob("*.jar")
                  if not re.search(r"-(sources|javadoc|slim|dev)\.jar$", j.name)]
        if not jarlar:
            return self.yaz(T("build_nojar"), "#e05252")
        jar = max(jarlar, key=lambda j: j.stat().st_mtime)
        self.yaz(T("build_ok", jar.name), "#4caf7a")
        self.jar.setCurrentText(str(jar))
        self._derlendi = True
        self.baslat()

    # ---------- jar ----------
    def jarlari_listele(self):
        simdiki = self.jar.currentText()
        jarlar = sorted(Path.home().glob("*.jar"), key=lambda p: p.stat().st_mtime, reverse=True)
        self.jar.blockSignals(True)
        self.jar.clear()
        self.jar.addItems([str(j) for j in jarlar])
        self.jar.setCurrentText(simdiki if simdiki else (str(jarlar[0]) if jarlar else ""))
        self.jar.blockSignals(False)
        self.jar_degisti(self.jar.currentText())

    def jar_sec(self):
        yol, _ = QFileDialog.getOpenFileName(self, T("jar_group"), str(Path.home()), "Jar (*.jar)")
        if yol:
            self.jar.setCurrentText(yol)

    def jar_degisti(self, metin, proje_ata=True):
        jar = Path(metin.strip()).expanduser()
        kirmizi = "<span style='color:#e05252'>{}</span>"
        if not jar.is_file():
            self.jar_bilgi.setText(f"<i>{T('no_jar')}</i>" if not metin.strip() else kirmizi.format(T("no_file")))
            return
        try:
            b = modyukle.jar_bilgisi(jar)
        except SystemExit:
            self.jar_bilgi.setText(kirmizi.format(T("bad_jar")))
            return
        except Exception as e:
            self.jar_bilgi.setText(kirmizi.format(html.escape(T("read_fail", e))))
            return
        bag = ", ".join(b["gerekli"]) or T("none")
        self.jar_bilgi.setText(
            f"<b>{html.escape(b['ad'])}</b> {html.escape(b['surum'])} &nbsp;·&nbsp; modId <code>{b['modid']}</code>"
            f" &nbsp;·&nbsp; {b['yukleyici']} {b['mc']} &nbsp;·&nbsp; {html.escape(T('deps', bag))}"
            + (f" &nbsp;·&nbsp; {T('server_only')}" if b["sadece_sunucu"] else ""))
        if proje_ata:
            self.proje.setCurrentText(b["modid"])

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.toLocalFile().endswith(".jar") for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            if u.toLocalFile().endswith(".jar"):
                self.jar.setCurrentText(u.toLocalFile())
                break

    # ---------- proje dosyaları ----------
    def proje_durumu_yaz(self):
        d = self.proje_dizini()
        if not d:
            self.proje_durum.setText("")
        elif d.exists():
            a = modyukle.ayar_oku(d / "ayarlar.properties")
            kayit = [ad for anahtar, ad in (("modrinth_id", "Modrinth"), ("github_repo", "GitHub"),
                                            ("curseforge_id", "CurseForge")) if a.get(anahtar)]
            self.proje_durum.setText(T("registered", ", ".join(kayit) or T("no_platform_yet")))
        else:
            self.proje_durum.setText(f"<span style='color:#d9a43a'>{T('new_project')}</span>")

    def proje_degisti(self, _metin=None):
        if self.yuklu_proje and self.yuklu_proje != self.proje_dizini():
            self.dosyalari_kaydet()
        d = self.proje_dizini()
        self.yuklu_proje = d
        self.proje_durumu_yaz()
        if not d:
            for w in (self.changelog, self.ayar_metni, self.aciklama):
                w.setPlainText("")
            return
        oku = lambda p: p.read_text("utf-8") if p and p.exists() else ""
        self.changelog.setPlainText(oku(d / "changelog.txt"))
        self.ayar_metni.setPlainText(oku(d / "ayarlar.properties"))
        self.aciklama.setPlainText(oku(self.aciklama_yolu()))
        for w in (self.changelog, self.ayar_metni, self.aciklama):
            w.document().setModified(False)

    def dosyalari_kaydet(self, bildir=False):
        d = self.yuklu_proje
        if not d:
            return
        kaydedilen = []
        for w, yol in ((self.changelog, d / "changelog.txt"), (self.ayar_metni, d / "ayarlar.properties"),
                       (self.aciklama, DIZIN.parent / "aciklamalar" / f"{d.name}.txt")):
            if not w.document().isModified():
                continue
            yol.parent.mkdir(parents=True, exist_ok=True)
            metin = w.toPlainText()
            yol.write_text(metin + ("\n" if metin and not metin.endswith("\n") else ""), "utf-8")
            w.document().setModified(False)
            kaydedilen.append(yol.name)
        if bildir:
            self.yaz(T("saved", ", ".join(kaydedilen) or T("no_changes")), "#7aa2d9")

    # ---------- çalıştırma ----------
    def baslat(self):
        derlendi, self._derlendi = self._derlendi, False
        if self.r_derle.isChecked() and not derlendi:
            if not [k for k, w in self.platform_kutulari.items() if w.isChecked()]:
                return QMessageBox.warning(self, T("title"), T("pick_platform"))
            return self.derle()
        jar = Path(self.jar.currentText().strip()).expanduser()
        proje = proje_adi(self.proje.currentText())
        platformlar = [k for k, w in self.platform_kutulari.items() if w.isChecked()]
        if not jar.is_file():
            return QMessageBox.warning(self, T("title"), T("pick_jar"))
        if not proje:
            return QMessageBox.warning(self, T("title"), T("empty_project"))
        if not platformlar:
            return QMessageBox.warning(self, T("title"), T("pick_platform"))
        prova = self.prova.isChecked()
        if not prova:
            ad = ", ".join(a for k, a in PLATFORMLAR if k in platformlar)
            if not evet_hayir_kutusu(self, T("real_upload"), T("real_upload_q", jar.name, ad)):
                return
        self.dosyalari_kaydet()
        AYAR.setValue("platformlar", ",".join(platformlar))
        AYAR.setValue("prova", "true" if prova else "false")
        AYAR.setValue("incele", "true" if self.incele.isChecked() else "false")

        args = [str(DIZIN / "modyukle.py"), ",".join(platformlar), proje, str(jar)]
        if prova:
            args.append("--prova")
        if self.incele.isChecked():
            args.append("--incele")
        if self.etiket.text().strip():
            args.append("--etiket=" + self.etiket.text().strip())
        if self.yukleme_adi.text().strip():
            args.append("--dosya-adi=" + self.yukleme_adi.text().strip())
        if self.r_derle.isChecked():
            args.append("--kaynak=" + str(Path(self.ws.currentText().strip()).expanduser()))

        self.surec_baslat(args)

    def surec_baslat(self, args):
        env = QProcessEnvironment.systemEnvironment()
        env.insert("MODYUKLE_GUI", "1")
        env.insert("MODYUKLE_LANG", DIL)
        env.insert("PYTHONUNBUFFERED", "1")
        tokenlari_tamamla(env)

        self.tampon = ""
        self.surec = QProcess(self)
        self.surec.setProcessEnvironment(env)
        self.surec.setWorkingDirectory(str(DIZIN))
        self.surec.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.surec.readyReadStandardOutput.connect(self.okunan)
        self.surec.finished.connect(self.bitti)
        self.surec.errorOccurred.connect(lambda h: self.yaz(T("proc_fail", h)))
        self.yaz(f"$ modyukle {' '.join(args[1:])}", "#888888")
        self.kilitle(True)
        self.surec.start(sys.executable, args)

    def sayfa_guncelle(self):
        proje = proje_adi(self.proje.currentText())
        if not proje:
            return QMessageBox.warning(self, T("title"), T("empty_project"))
        self.dosyalari_kaydet()
        args = [str(DIZIN / "modyukle.py"), "sayfa", proje]
        if self.prova.isChecked():
            args.append("--prova")
        self.surec_baslat(args)

    def okunan(self):
        self.tampon += bytes(self.surec.readAllStandardOutput()).decode("utf-8", "replace")
        while "\n" in self.tampon:
            satir, self.tampon = self.tampon.split("\n", 1)
            satir = satir.rstrip("\r")
            if satir.startswith(SOR_ISARETI):
                self.soru_sor(json.loads(satir[len(SOR_ISARETI):]))
            else:
                self.yaz(satir)

    def soru_sor(self, s):
        soru, vars_ = s["soru"], s.get("varsayilan", "")
        m = re.search(r"\((e/h|y/n)\)", soru)
        if m:
            temiz = soru.replace(m.group(0), "").strip()
            cevap = "e" if evet_hayir_kutusu(self, T("asks"), temiz, vars_ in ("e", "y")) else "h"
        else:
            giris = QInputDialog(self)
            giris.setWindowTitle(T("asks"))
            giris.setLabelText(soru)
            giris.setTextValue(vars_)
            giris.setOkButtonText("OK")
            giris.setCancelButtonText(T("cancel"))
            cevap = giris.textValue() if giris.exec() else ""
        self.yaz(f"{soru} → {cevap or T('empty_ans')}", "#7aa2d9")
        if self.surec:
            self.surec.write((cevap.replace("\n", " ") + "\n").encode("utf-8"))

    def bitti(self, kod, _durum):
        if self.tampon.strip():
            self.yaz(self.tampon.rstrip())
        self.tampon = ""
        self.yaz(T("finished", kod), "#4caf7a" if kod == 0 else "#e05252")
        self.surec = None
        self.kilitle(False)
        # modyukle ayarlar.properties ve changelog'u değiştirmiş olabilir
        self.yuklu_proje = None
        self.proje.blockSignals(True)
        mevcut = self.proje.currentText()
        self.proje.clear()
        self.proje.addItems(self.kayitli_projeler())
        self.proje.setCurrentText(mevcut)
        self.proje.blockSignals(False)
        self.proje_degisti()

    def surec_durdur(self):
        if self.surec:
            self.surec.kill()
        if self.derleme:
            self.derleme.kill()

    def kilitle(self, calisiyor):
        self.calistir.setEnabled(not calisiyor)
        self.sayfa_dugme.setEnabled(not calisiyor)
        self.durdur.setEnabled(calisiyor)
        for w in (self.oyun, self.r_hazir, self.r_derle, self.ws, self.ws_gozat, self.jar, self.yukleme_adi, self.etiket, self.proje, self.prova, self.incele, self.changelog, self.ayar_metni, self.aciklama,
                  *self.platform_kutulari.values()):
            w.setEnabled(not calisiyor)

    def closeEvent(self, e):
        if (self.surec or self.derleme) and not evet_hayir_kutusu(self, T("title"), T("running_quit")):
            return e.ignore()
        self.surec_durdur()
        self.dosyalari_kaydet()
        e.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Modyukle")
    app.setDesktopFileName("modyukle")
    p = Pencere()
    p.show()
    sys.exit(app.exec())
