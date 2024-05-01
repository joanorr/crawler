"""Tests for the web crawler."""

from bs4 import BeautifulSoup
import crawler
import pytest


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


class TestExtractLinksFromPage:
    """Test suite for the extract_links_from_page function."""

    PAGE_URL = 'https://www.joanorr.com/foo/bar.html'

    def test_includes_links_to_current_site(self):
        html = """
          <a href="baz.html">Link 1</a>
          <a href="/breeze.html">Link 2</a>
          <a href="http://www.joanorr.com/blouse.html">Link 2</a>
        """
        expected_result = set([
            'http://www.joanorr.com/blouse.html',
            'https://www.joanorr.com/foo/baz.html',
            'https://www.joanorr.com/breeze.html',
        ])

        actual_result = crawler.extract_links_from_page(self.PAGE_URL, html)

        assert actual_result == expected_result

    def test_does_not_inlcude_links_to_other_sites(self):
        html = """
          <a href="baz.html">Link 1</a>
          <a href="https://www.example.com/blue.html">Link 2</a>
        """
        expected_result = set([
            'https://www.joanorr.com/foo/baz.html',
        ])

        actual_result = crawler.extract_links_from_page(self.PAGE_URL, html)

        assert actual_result == expected_result

    def test_does_not_inlcude_links_which_are_not_http_or_https(self):
        html = """
          <a href="baz.html">Link 1</a>
          <a href="mailto:someone@www.joanorr.com">Link 2</a>
        """
        expected_result = set([
            'https://www.joanorr.com/foo/baz.html',
        ])

        actual_result = crawler.extract_links_from_page(self.PAGE_URL, html)

        assert actual_result == expected_result

    def test_ignores_anchors_without_href_attributes(self):
        html = """
          <a href="baz.html">Link 1</a>
          <a name="target">Link 2</a>
        """
        expected_result = set([
            'https://www.joanorr.com/foo/baz.html',
        ])

        actual_result = crawler.extract_links_from_page(self.PAGE_URL, html)

        assert actual_result == expected_result
