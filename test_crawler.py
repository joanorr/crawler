"""Tests for the web crawler."""

from bs4 import BeautifulSoup
import crawler


class TestResolveLinkUrl:
    """Test suite for the resolve_link_url function."""

    def test_resolves_absolute_url(self):
        page_url = 'http://www.joanorr.com/baz/boz.html'
        page_soup = BeautifulSoup('<a href="{url}"></a>', 'html.parser')
        link_url = 'http://www.joanorr.com/foo/bar.html'

        assert (crawler.resolve_link_url(page_url, page_soup, link_url) ==
                'http://www.joanorr.com/foo/bar.html')

    def test_resolves_absolute_path_url(self):
        page_url = 'http://www.joanorr.com/baz/boz.html'
        page_soup = BeautifulSoup('<a href="{url}"></a>', 'html.parser')
        link_url = '/foo/bar.html'

        assert (crawler.resolve_link_url(page_url, page_soup, link_url) ==
                'http://www.joanorr.com/foo/bar.html')

    def test_resolves_relative_path_url_no_base_tag(self):
        page_url = 'http://www.joanorr.com/baz/boz.html'
        page_soup = BeautifulSoup('<a href="{url}"></a>', 'html.parser')
        link_url = 'foo/bar.html'

        assert (crawler.resolve_link_url(page_url, page_soup, link_url) ==
                'http://www.joanorr.com/baz/foo/bar.html')

    def test_resolves_relative_path_url_with_base_tag(self):
        base_url = 'http://www.joanorr.com/new_base/index.html'
        page_url = 'http://www.joanorr.com/baz/boz.html'
        page_soup = BeautifulSoup(
            '<base href="{base_url}"><a href="{url}"></a>', 'html.parser')
        link_url = 'http://www.joanorr.com/new_base/foo/bar.html'

        assert (crawler.resolve_link_url(page_url, page_soup, link_url) ==
                'http://www.joanorr.com/new_base/foo/bar.html')

    def test_discards_url_fragment(self):
        page_url = 'http://www.joanorr.com/baz/boz.html'
        page_soup = BeautifulSoup('<a href="{url}"></a>', 'html.parser')
        link_url = 'http://www.joanorr.com/foo/bar.html#tab=5'

        assert (crawler.resolve_link_url(page_url, page_soup, link_url) ==
                'http://www.joanorr.com/foo/bar.html')
