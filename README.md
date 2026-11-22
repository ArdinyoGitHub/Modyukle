# Modyukle — Minecraft mod uploader

Upload a Minecraft mod to all of these platforms with a single command (or a small GUI):

- **Modrinth**
- **CurseForge**
- **GitHub Releases**
- **Nexus Mods**

Built for MCreator workspaces, but works with any mod jar. It lives outside the mod's own project because MCreator overwrites `build.gradle`; uploading is done by a standalone Gradle project using [mod-publish-plugin](https://modmuss50.github.io/mod-publish-plugin/) 2.2.1.

## Repository layout
- `yukleyici/` — the tool itself ("yükleyici" = uploader): `modyukle.py` (CLI), `modyukle_gui.py` (PyQt6 GUI, English/Turkish), `nexus_bbcode.py` (Markdown → BBCode for Nexus pages) and the Gradle upload engine.
- `yukleyici/modlar/<mod>/` — per-mod settings (`ayarlar.properties` = settings) and `changelog.txt`.
- `aciklamalar/` — page descriptions per mod (`<mod>.txt`: first line = short summary, text after `---` = full page). Used when creating new Modrinth projects, GitHub READMEs and Nexus pages.
- `publishMods.gradle` — snippet for hand-written (non-MCreator) Gradle projects.
- `ileride-github-actions/publish.yml` — optional GitHub Actions workflow, currently unused.

## Usage
```
modyukle <platform> <project> <jar> [--prova] [--incele]

modyukle hepsi ardinyos_biomes ~/Downloads/ardinyos_biomes-2.0.2-neoforge-26.1.2.jar
modyukle modrinth,github new_mod ~/new_mod-1.0.0-neoforge-26.1.2.jar --prova
```
- **platform:** `modrinth`, `github`, `curseforge`, `nexus`, `hepsi` (= all) or a comma-separated list.
- **project:** project name (`ardinyos_biomes` → Modrinth slug / GitHub repo `ardinyos-biomes`).
- **jar:** the exported mod file. Name, version, Minecraft version and dependencies are read from the jar's `neoforge.mods.toml`.
- `--prova` (dry run): creates and uploads nothing, only shows what would happen. Running `modyukle` with no arguments prints help and the known projects.
- `--incele` (review): submit a draft Modrinth project for review without asking.
- Other flags: `--kaynak=<workspace>` (commit the mod source to the GitHub repo before the release), `--dosya-adi=<name.jar>` (upload under a different file name), `--etiket=<tag>` (GitHub tag, default `v<version>`).
- Other commands: `modyukle readme <project>` (write the GitHub README + repo description from `aciklamalar/<project>.txt`; also done automatically on every GitHub upload, hand-edited READMEs are left alone unless `--evet`), `modyukle sayfa <project>` (update the Nexus page description), `modyukle kaynak <project> <workspace>` (push source code to GitHub only).

**If the project doesn't exist yet**, it is created: a draft on Modrinth (asks for description/category/license) and a repo on GitHub.
**If it exists**, only the new version is uploaded; a platform where that version already exists is skipped.
**After a Modrinth upload**, the version's environment is set from `ayarlar.properties → ortam=` (default `client_and_server`; the plugin uses the v2 API, which would leave it `unknown`). Drafts can be submitted for review.
**CurseForge** projects can't be created through the API: create it on the site and enter the Project ID when asked.
**Nexus Mods** uses the official v3 upload API; you open the mod page on the site once and enter its address, the rest is stored in `ayarlar.properties`. Files over 100 MiB are not supported yet.

Project IDs are stored in `yukleyici/modlar/<project>/ayarlar.properties` (created on first run).

## GUI
`python3 yukleyici/modyukle_gui.py` — pick a game and a source (ready `.jar` or build from a workspace), choose platforms, edit changelog / settings / descriptions, and run (with dry-run option). Settings (⚙, Ctrl+,) hold the language (English default, Turkish available), API keys and GitHub login/logout.

## Tokens (once)
| Variable | Where to get it | Permissions |
|---|---|---|
| `CURSEFORGE_TOKEN` | curseforge.com → Account → API Tokens | – |
| `MODRINTH_TOKEN` | modrinth.com → Settings → PATs | Create projects, Create versions, Write projects |
| `NEXUS_TOKEN` | Nexus Mods → API access | – |
| GitHub | `gh auth login` is enough | – |

```fish
set -Ux CURSEFORGE_TOKEN ...
set -Ux MODRINTH_TOKEN ...
```

## For every release
1. Bump the version in MCreator (Workspace settings; `1.0.1-alpha`, `-beta` for pre-releases).
2. MCreator → **File → Export mod**.
3. Write the changes into `yukleyici/modlar/<project>/changelog.txt` (archived as `changelog-<version>.txt` after upload).
4. `modyukle hepsi <project> <jar>`

> The same version can't be uploaded twice (the sites reject it) — bump it in MCreator first.
> Without "Read user data" on the Modrinth PAT some test calls return a misleading 401; uploading doesn't need it.
> Note: CLI flags and the folder names (`yukleyici`, `modlar`, `aciklamalar`) are Turkish for historical reasons; messages and the GUI are bilingual.
