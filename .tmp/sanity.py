import sys, types
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
pkg = types.ModuleType("searchpin"); pkg.__path__ = [str(ROOT / "searchpin")]
sys.modules["searchpin"] = pkg

from searchpin import config
from searchpin.backends import build_backends

print("default engines:", len(build_backends("test")))
config.ENABLE_GOOGLE = True
for b in build_backends("solid state battery 量产", page=1):
    host, path, parse_fn, follow, port, lang, tag = b
    engine = "_".join(tag.split("_")[:-1]) if "_pg" in tag else tag
    print(f"  {host:<16} engine={engine:<10} follow={follow} lang={lang}")
    print(f"    path={path[:110]}")

# news vertical + freshness
g_news = [b for b in build_backends("AI", topic="news", freshness_suffix="&tbs=qdr:d") if b[0] == "www.google.com"][0]
print("news+freshness:", g_news[1])
