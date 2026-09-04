from __future__ import annotations

from datetime import date
import base64
import json
from pathlib import Path
import re
import shutil

try:
    from scripts.hub_sessions import create_hub_session
    from scripts.template_catalog import public_template_catalog
except ImportError:
    from hub_sessions import create_hub_session
    from template_catalog import public_template_catalog


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "dist" / "vercel"


def build() -> None:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    editors_dir = OUTPUT / "editors"
    editors_dir.mkdir(parents=True)

    catalog = public_template_catalog()
    for template in catalog:
        session = create_hub_session(template["id"], editors_dir)
        target = editors_dir / f'{template["id"]}.html'
        session.path.replace(target)
        html = target.read_text(encoding="utf-8")
        for font_name in ("Advercase-Regular.otf", "Advercase-Bold.otf"):
            font_data = base64.b64encode(
                (ROOT / "assets" / "fonts" / font_name).read_bytes()
            ).decode("ascii")
            html = html.replace(
                f"/assets/fonts/{font_name}",
                f"data:font/otf;base64,{font_data}",
            )
        html = re.sub(
            r'window\.MATHEUSAO_PECA_PATH\s*=\s*"[^"]*";',
            'window.MATHEUSAO_PECA_PATH = "";',
            html,
        )
        web_runtime = """
<script>
  window.CARROSSEL_WEB_DEPLOY = true;
  window.returnToHub = function () {
    if (!window.confirm('Descartar esta criação e voltar aos modelos?')) return;
    if (typeof clearHubSessionStorage === 'function') clearHubSessionStorage();
    window.location.replace('/');
  };
</script>
"""
        html = html.replace("</body>", web_runtime + "</body>", 1)
        target.write_text(html, encoding="utf-8")

    hub = (ROOT / "templates" / "hub.html").read_text(encoding="utf-8")
    catalog_json = json.dumps(catalog, ensure_ascii=False).replace("</", "<\\/")
    hub = hub.replace("{{TEMPLATES_JSON}}", catalog_json)
    hub = re.sub(
        r"    async function createCarousel\(templateId, button\) \{.*?\n    \}\n\n    renderTemplates\(\);",
        """    function createCarousel(templateId, button) {
      button.disabled = true;
      setStatus('Abrindo seu editor…');
      window.location.assign('/editors/' + encodeURIComponent(templateId) + '.html');
    }

    renderTemplates();""",
        hub,
        flags=re.DOTALL,
    )
    runtime = "<script>window.CARROSSEL_CSRF=''; window.CARROSSEL_WEB_DEPLOY=true;</script>"
    hub = hub.replace("</head>", runtime + "</head>", 1)
    (OUTPUT / "index.html").write_text(hub, encoding="utf-8")

    # The image-generation helper belongs to the local Python API. Keeping a
    # harmless browser stub avoids a 404 without sending user content anywhere.
    (editors_dir / "image-gen-client.js").write_text(
        "window.MATHEUSAO_IMAGE_GEN_AVAILABLE = false;\n", encoding="utf-8"
    )

    print(f"Vercel static bundle generated at {OUTPUT} ({date.today().isoformat()})")


if __name__ == "__main__":
    build()
