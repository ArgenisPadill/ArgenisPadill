from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README_ES = ROOT / "README.md"
README_EN = ROOT / "README.en.md"

REQUIRED_FILES = [
    README_ES,
    README_EN,
    ROOT / "assets/header-es.svg",
    ROOT / "assets/header-en.svg",
    ROOT / "assets/header-es-light.svg",
    ROOT / "assets/header-en-light.svg",
    ROOT / "assets/language-es.svg",
    ROOT / "assets/language-en.svg",
    ROOT / "assets/language-es-light.svg",
    ROOT / "assets/language-en-light.svg",
    ROOT / "assets/activity-es.svg",
    ROOT / "assets/activity-en.svg",
    ROOT / "assets/activity-es-light.svg",
    ROOT / "assets/activity-en-light.svg",
]

REQUIRED_ES_SECTIONS = [
    "## Sobre mí",
    "## Áreas clave",
    "## Forma de trabajo",
    "## Proyectos destacados",
    "## Stack técnico",
    "## Actividad",
]

REQUIRED_EN_SECTIONS = [
    "## About me",
    "## Key areas",
    "## How I work",
    "## Featured projects",
    "## Technical stack",
    "## Activity",
]

FEATURED_REPOS = [
    "https://github.com/ArgenisPadill/SineOS",
    "https://github.com/ArgenisPadill/VisualizacionDeDatosConRyShiny",
    "https://github.com/ArgenisPadill/EstadisticaMultiVariable",
]

errors: list[str] = []
warnings: list[str] = []

def fail(message: str) -> None:
    errors.append(message)

def warn(message: str) -> None:
    warnings.append(message)

for path in REQUIRED_FILES:
    if not path.exists():
        fail(f"Missing required file: {path.relative_to(ROOT)}")

if errors:
    for item in errors:
        print(f"ERROR: {item}")
    sys.exit(1)

es = README_ES.read_text(encoding="utf-8")
en = README_EN.read_text(encoding="utf-8")

for label, content, sections in (
    ("README.md", es, REQUIRED_ES_SECTIONS),
    ("README.en.md", en, REQUIRED_EN_SECTIONS),
):
    if len(content.encode("utf-8")) > 400_000:
        fail(f"{label} is approaching GitHub's README rendering limit.")

    visible_content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    if "<sub>" in visible_content.lower():
        fail(f"{label} contains visible <sub>, which reduces body-text readability.")

    for section in sections:
        if section not in content:
            fail(f"{label} is missing section: {section}")

    if content.count("<picture>") != content.count("</picture>"):
        fail(f"{label} has unbalanced <picture> tags.")

    if content.count("<details>") != content.count("</details>"):
        fail(f"{label} has unbalanced <details> tags.")

    for img_tag in re.findall(r"<img\b[^>]*>", content, flags=re.IGNORECASE):
        if not re.search(r'\balt="[^"]+"', img_tag, flags=re.IGNORECASE):
            fail(f"{label} has an image without useful alt text: {img_tag[:100]}")

    for local_ref in re.findall(r'(?:src|srcset)="(\./[^"]+)"', content):
        path = ROOT / local_ref.removeprefix("./")
        if not path.exists():
            fail(f"{label} references missing local asset: {local_ref}")

    ids = re.findall(r'<a\s+id="([^"]+)"', content)
    if len(ids) != len(set(ids)):
        fail(f"{label} contains duplicate explicit anchor IDs.")

for repo_url in FEATURED_REPOS:
    if repo_url not in es or repo_url not in en:
        fail(f"Featured repository is not represented in both languages: {repo_url}")

if "METRICS_ES:START" not in es or "METRICS_ES:END" not in es:
    fail("Spanish metrics markers are missing.")
if "METRICS_EN:START" not in en or "METRICS_EN:END" not in en:
    fail("English metrics markers are missing.")

# Ensure adaptive assets are paired.
asset_names = {p.name for p in (ROOT / "assets").glob("*.svg")}
for dark in [name for name in asset_names if "-light" not in name]:
    light = dark.removesuffix(".svg") + "-light.svg"
    if dark.startswith(("header-", "language-", "activity-")) and light not in asset_names:
        fail(f"Adaptive asset missing light variant: {light}")

# Motion accessibility: animated hero/switch SVGs should respect reduced motion.
for path in [
    ROOT / "assets/header-es.svg",
    ROOT / "assets/header-en.svg",
    ROOT / "assets/header-es-light.svg",
    ROOT / "assets/header-en-light.svg",
    ROOT / "assets/language-es.svg",
    ROOT / "assets/language-en.svg",
    ROOT / "assets/language-es-light.svg",
    ROOT / "assets/language-en-light.svg",
]:
    content = path.read_text(encoding="utf-8")
    if "animation:" in content and "prefers-reduced-motion" not in content:
        fail(f"Animated asset does not respect reduced motion: {path.relative_to(ROOT)}")

# Guard against stale asset names that previously caused maintenance ambiguity.
for label, content in (("README.md", es), ("README.en.md", en)):
    if './assets/header.svg' in content or './assets/activity.svg' in content:
        fail(f"{label} references a deprecated shared asset.")

# UX heuristic: preserve native text for core profile content.
for label, content in (("README.md", es), ("README.en.md", en)):
    if content.count("<table") > 0:
        warn(f"{label} contains tables; verify they remain readable on narrow screens.")

if warnings:
    print("\nWarnings:")
    for item in warnings:
        print(f"WARNING: {item}")

if errors:
    print("\nProfile quality checks failed:")
    for item in errors:
        print(f"ERROR: {item}")
    sys.exit(1)

print("Profile quality checks passed.")
print(f"Validated {len(REQUIRED_FILES)} required files, bilingual structure, adaptive assets, accessibility, and local references.")
