"""Tests for search backend parsers — uses static HTML snippets, no network."""

from searchpin.backends import (
    build_backends,
    make_baidu_parser,
    make_bing_parser,
    make_cn_bing_path,
    make_google_news_path,
    make_google_parser,
    make_google_path,
    make_sogou_parser,
    make_www_bing_path,
    prep_query,
)


class TestPrepQuery:
    def test_english_unchanged(self):
        assert prep_query("hello world") == "hello world"

    def test_chinese_no_spaces_removed(self):
        """CJK spaces between Chinese chars should be removed."""
        # Chinese chars on both sides → space removed
        assert prep_query("你好 世界") == "你好世界"

    def test_mixed_cjk_english(self):
        """Space on either side of CJK is removed — both English→CJK and CJK→CJK."""
        result = prep_query("Python 编程 语言")
        # Regex: \s+(?=CJK) removes "Python " (space before CJK)
        #        (?<=CJK)\s+ removes "程 语" (space after CJK)
        assert result == "Python编程语言"


class TestBingPaths:
    def test_cn_bing_path(self):
        path = make_cn_bing_path("test query", freshness_suffix="&tbs=qdr:d")
        assert path.startswith("/search?q=")
        # URL-encoded space is %20, not +
        assert "test%20query" in path.lower()
        assert "qdr" in path  # freshness filter present

    def test_www_bing_path(self):
        path = make_www_bing_path("test query")
        assert "setmkt=en-US" in path
        assert path.startswith("/search?q=")


class TestGooglePaths:
    def test_general_path(self):
        path = make_google_path("test query", extra="&start=0", freshness_suffix="&tbs=qdr:w")
        assert path.startswith("/search?q=test%20query")
        assert "udm=14" in path  # lightweight no-JS layout
        assert "num=15" in path
        assert "hl=en-US" in path
        assert "start=0" in path
        assert "qdr:w" in path

    def test_news_path(self):
        path = make_google_news_path("breaking news")
        assert path.startswith("/search?q=breaking%20news")
        assert "tbm=nws" in path


class TestBuildBackends:
    def test_general_build(self):
        backends = build_backends("test", page=0)
        assert len(backends) == 5  # baidu, sogou, bing_cn, bing_intl, google
        hosts = {b[0] for b in backends}
        assert hosts == {
            "www.baidu.com",
            "www.sogou.com",
            "cn.bing.com",
            "www.bing.com",
            "www.google.com",
        }

    def test_google_included(self):
        """Google is always part of the parallel batch."""
        backends = build_backends("test", page=0)
        google = [b for b in backends if b[0] == "www.google.com"]
        assert len(google) == 1
        host, path, parse_fn, follow, port, lang, tag = google[0]
        assert "/search?q=" in path
        assert callable(parse_fn)
        assert follow is True
        assert port == 443
        assert tag == "google_pg0"

    def test_news_build(self):
        backends = build_backends("breaking news", page=0, topic="news")
        for host, path, *_ in backends:
            if "bing" in host:
                assert "/news/search" in path

    def test_google_news_vertical(self):
        """topic=news routes Google to its tbm=nws vertical."""
        backends = build_backends("breaking news", page=0, topic="news")
        google_paths = [b[1] for b in backends if b[0] == "www.google.com"]
        assert len(google_paths) == 1
        assert "tbm=nws" in google_paths[0]

    def test_pagination(self):
        backends_p0 = build_backends("test", page=0)
        backends_p1 = build_backends("test", page=1)
        # Page 1 paths should differ from page 0
        p0_paths = [b[1] for b in backends_p0 if "bing" in b[0]]
        p1_paths = [b[1] for b in backends_p1 if "bing" in b[0]]
        assert p0_paths != p1_paths

    def test_google_pagination_start_offset(self):
        """Google paginates via &start=<page*10>."""
        p0 = [b[1] for b in build_backends("test", page=0) if b[0] == "www.google.com"][0]
        p1 = [b[1] for b in build_backends("test", page=1) if b[0] == "www.google.com"][0]
        assert "start=0" in p0
        assert "start=10" in p1


class TestParsers:
    """Parser tests with minimal valid HTML snippets."""

    def test_baidu_parser_handles_empty(self):
        parser = make_baidu_parser()
        results = parser("<html></html>")
        assert isinstance(results, list)
        assert len(results) == 0

    def test_sogou_parser_handles_empty(self):
        parser = make_sogou_parser()
        results = parser("<html></html>")
        assert isinstance(results, list)
        assert len(results) == 0

    def test_bing_parser_handles_empty(self):
        parser = make_bing_parser("cn.bing.com")
        results = parser("<html></html>")
        assert isinstance(results, list)
        assert len(results) == 0

    def test_bing_parser_b_algo(self):
        """Bing parser should extract results from b_algo blocks."""
        parser = make_bing_parser("cn.bing.com")
        html = """<html><body>
        <li class="b_algo"><h2><a href="https://example.com/article">
        Article Title</a></h2>
        <p class="b_lineclamp">This is a search result snippet.</p>
        </li>
        </body></html>"""
        results = parser(html)
        assert len(results) >= 1
        assert results[0]["title"] == "Article Title"
        assert results[0]["url"] == "https://example.com/article"
        assert "snippet" in results[0]["snippet"]

    def test_bing_parser_fallback_filters_bing_links(self):
        """Fallback parser (no b_algo blocks) filters bing self-referencing links."""
        parser = make_bing_parser("cn.bing.com")
        # No b_algo blocks → triggers fallback generic <a> extraction
        html = """<html><body>
        <a href="https://example.com/page">Real Result Title Text</a>
        <a href="https://cn.bing.com/something">Bing Self Link Here</a>
        <a href="https://other-site.com/thing">Another Real One</a>
        </body></html>"""
        results = parser(html)
        urls = [r["url"] for r in results]
        assert "https://cn.bing.com/something" not in urls
        assert len(results) >= 2  # got the two real links

    def test_google_parser_handles_empty(self):
        parser = make_google_parser()
        results = parser("<html></html>")
        assert isinstance(results, list)
        assert len(results) == 0

    def test_google_parser_anchor_wrapped_h3(self):
        """Google parser extracts anchor-wrapped h3 titles with VwiC3b snippets."""
        parser = make_google_parser()
        html = """<html><body>
        <div class="g">
          <a href="https://example.org/article"><h3 class="abc">Example Article Title</h3></a>
          <div class="VwiC3b">This is the snippet text for the example article.</div>
        </div>
        </body></html>"""
        results = parser(html)
        assert len(results) == 1
        assert results[0]["title"] == "Example Article Title"
        assert results[0]["url"] == "https://example.org/article"
        assert "snippet text" in results[0]["snippet"]

    def test_google_parser_unwraps_url_redirect(self):
        """/url?q=REAL redirect links resolve to their real target."""
        parser = make_google_parser()
        html = """<html><body>
        <div class="g">
          <a href="/url?q=https://real-site.com/page&amp;sa=U"><h3>Redirected Result Title</h3></a>
          <div class="VwiC3b">Snippet for the redirected result goes here.</div>
        </div>
        </body></html>"""
        results = parser(html)
        assert len(results) == 1
        assert results[0]["url"] == "https://real-site.com/page"

    def test_google_parser_filters_self_links(self):
        """google.com / gstatic self-referencing links are excluded."""
        parser = make_google_parser()
        # No h3-in-anchor blocks → triggers fallback generic extraction
        html = """<html><body>
        <a href="https://www.google.com/search?q=other">Google Self Link Here</a>
        <a href="https://fonts.gstatic.com/x">Gstatic Self Link</a>
        <a href="https://example.net/real">Real Result Title Text</a>
        </body></html>"""
        results = parser(html)
        urls = [r["url"] for r in results]
        assert all("google.com" not in u and "gstatic.com" not in u for u in urls)
        assert "https://example.net/real" in urls

    def test_google_parser_dedupes(self):
        parser = make_google_parser()
        html = """<html><body>
        <a href="https://same.com/a"><h3>First Title Here</h3></a>
        <a href="https://same.com/a"><h3>Duplicate Title Here</h3></a>
        </body></html>"""
        results = parser(html)
        assert len(results) == 1
