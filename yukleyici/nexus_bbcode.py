"""Markdown (aciklamalar/*.txt) → Nexus Mods BBCode dönüştürücü. Yalnızca standart kütüphane."""
import re

# Nexus BBCode: [b] [i] [u] [s] [size=n] [url=..] [img] [list] [*] [quote] [code] [line] [font=..]
_BASLIK_BOYUT = {1: 5, 2: 4, 3: 3, 4: 3, 5: 3, 6: 3}


def _satir_ici(m):
    kodlar = []

    def sakla(g):
        kodlar.append(g.group(1))
        return f"\x00{len(kodlar) - 1}\x00"

    m = re.sub(r"`([^`]+)`", sakla, m)
    m = re.sub(r"!\[[^\]]*\]\(([^)\s]+)[^)]*\)", r"[img]\1[/img]", m)
    m = re.sub(r"\[([^\]]+)\]\(([^)\s]+)[^)]*\)", r"[url=\2]\1[/url]", m)
    m = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"[b]\1[/b]", m)
    m = re.sub(r"(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)", r"[b]\1[/b]", m)
    m = re.sub(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])", r"[i]\1[/i]", m)
    m = re.sub(r"(?<![\w])_(?=[^\s_])(.+?)(?<=[^\s_])_(?!\w)", r"[i]\1[/i]", m)
    m = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", r"[s]\1[/s]", m)
    return re.sub(r"\x00(\d+)\x00", lambda g: f"[font=Courier New]{kodlar[int(g.group(1))]}[/font]", m)


def md_bbcode(md):
    cikti, liste, kod = [], None, False

    def listeyi_kapat():
        nonlocal liste
        if liste:
            cikti.append("[/list]")
            liste = None

    for ln in md.splitlines():
        if ln.strip().startswith("```"):
            listeyi_kapat()
            cikti.append("[/code]" if kod else "[code]")
            kod = not kod
            continue
        if kod:
            cikti.append(ln)
            continue
        madde = re.match(r"^\s*[-*+]\s+(.*)", ln)
        sirali = re.match(r"^\s*\d+[.)]\s+(.*)", ln)
        if madde or sirali:
            tur = "ul" if madde else "ol"
            if liste != tur:
                listeyi_kapat()
                cikti.append("[list]" if tur == "ul" else "[list=1]")
                liste = tur
            cikti.append("[*]" + _satir_ici((madde or sirali).group(1)))
            continue
        listeyi_kapat()
        baslik = re.match(r"^(#{1,6})\s+(.*)", ln)
        if baslik:
            cikti.append(f"[size={_BASLIK_BOYUT[len(baslik.group(1))]}][b]{_satir_ici(baslik.group(2).strip())}[/b][/size]")
        elif re.fullmatch(r"\s*([-*_])\1{2,}\s*", ln):
            cikti.append("[line]")
        elif ln.startswith(">"):
            cikti.append("[quote]" + _satir_ici(ln.lstrip("> ").strip()) + "[/quote]")
        else:
            cikti.append(_satir_ici(ln))
    listeyi_kapat()
    if kod:
        cikti.append("[/code]")
    return "\n".join(cikti).strip()


if __name__ == "__main__":
    import sys
    print(md_bbcode(sys.stdin.read()))
