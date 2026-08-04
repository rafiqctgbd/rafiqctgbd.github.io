# mohammadrafiqulislam.com

Personal portfolio and app documentation site for **Mohammad Rafiqul Islam** —
Senior IT Manager and Android developer, Chittagong, Bangladesh.

Live at **[mohammadrafiqulislam.com](https://mohammadrafiqulislam.com)**, served
by GitHub Pages from this repository.

## Structure

```
index.html                          Portfolio home
apps/                               Android app pages
  medicine-health-reminder/         Medicine & Health Reminder
  nextcue/                          NextCue: Bill & Life Reminder
    index.html                        App landing page
    privacy-policy.html               Privacy policy (linked from Play Console)
    README.html                       README & Terms of Service
blog/                               Blog posts (English and Bengali)
resume/                             Résumé
assets/                             Icons, images, favicons
scripts/                            Maintenance scripts
sitemap.xml                         Search engine sitemap
```

Every page is a self-contained static HTML file with its own inline styles —
no build step, no framework, no dependencies. Editing a page and pushing is
the entire deploy process.

## Apps

| App | Package | Status |
|---|---|---|
| [Medicine & Health Reminder](https://mohammadrafiqulislam.com/apps/medicine-health-reminder/) | `com.rafiqctgbd.medicinehealth` | Published |
| [NextCue: Bill & Life Reminder](https://mohammadrafiqulislam.com/apps/nextcue/) | `com.rafiqctgbd.nextcue` | In testing |

Both are free, ad-free, and store data locally on the device by default, with
optional user-controlled Google Drive backup.

## Scripts

### `scripts/render_icon.py`

Regenerates every NextCue icon PNG from the Android project's adaptive-icon
vector XML, so the icons here can't drift out of sync with the ones the app
actually ships.

```bash
pip install cairosvg pillow
python3 scripts/render_icon.py --project ../NextCue
```

Outputs the rounded transparent web icons, the flat no-alpha Play Console
icon, and a background-free foreground variant. Run without arguments to use
pinned fallback geometry.

### `scripts/update_sitemap.py`

Refreshes `<lastmod>` dates in `sitemap.xml`. Run automatically by the
workflow in `.github/workflows/`. Note that it only updates entries that
already exist — new pages must be added to `sitemap.xml` by hand.

## License

This repository is **dual-licensed** — see [LICENSE](LICENSE) for full terms.

- **Code** (HTML, CSS, JavaScript, Python) — MIT License. Reuse of the layout
  and structure for your own site is welcome.
- **Brand assets and content** (the NextCue and Medicine & Health Reminder
  names and icons, feature graphics, screenshots, written page content, and
  personal material) — All rights reserved.

`render_icon.py` being public does not license the artwork it produces.
