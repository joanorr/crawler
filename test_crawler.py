"""Tests for the web crawler."""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import crawler
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, Mock


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


@pytest.fixture
async def mock_asyncio_gather():
    return 'foo'


@pytest.mark.asyncio
@patch('asyncio.gather', new_callable=AsyncMock)
@patch('crawler.monitor')
@patch('crawler.Worker')
async def test_worker(MockWorker, mock_monitor, mock_asyncio_gather):
    root_url = 'http://www.example.com/'
    num_workers = 3

    await crawler.set_up_tasks(root_url, num_workers,
                               crawler.print_page_and_links)

    # The right number of Workers have been created
    assert MockWorker.call_count == num_workers

    # The monitor has been started and passed the workers
    assert mock_monitor.call_count == 1
    mock_monitor_args = mock_monitor.call_args.args
    assert len(mock_monitor_args) == 1
    assert len(mock_monitor_args[0]) == num_workers
    assert "name='Worker()'" in repr(mock_monitor_args[0][0])
    assert "name='Worker()'" in repr(mock_monitor_args[0][1])
    assert "name='Worker()'" in repr(mock_monitor_args[0][2])

    # The worker tasks have been gathered
    assert mock_asyncio_gather.call_count == 1
    mock_asyncio_gather_args = mock_asyncio_gather.call_args.args
    assert len(mock_asyncio_gather_args) == 4
    assert "name='Worker().task'" in repr(mock_asyncio_gather_args[0])
    assert "name='Worker().task'" in repr(mock_asyncio_gather_args[1])
    assert "name='Worker().task'" in repr(mock_asyncio_gather_args[2])


@patch.object(crawler.Worker, 'run')
@patch('asyncio.create_task')
@patch('aiohttp.ClientSession')
@patch('asyncio.Queue')
def test_worker_starts_task(MockQueue, MockClientSession, mock_create_task,
                            mock_crawler_worker_run):
    queue = MockQueue()
    enqueued = set()
    session = MockClientSession()
    worker = crawler.Worker(queue, enqueued, session,
                            crawler.print_page_and_links)

    mock_create_task.assert_not_called()
    mock_crawler_worker_run.assert_not_called()
    worker.start()

    mock_create_task.assert_called_once()
    mock_crawler_worker_run.assert_called_once()


@patch.object(crawler.Worker, 'run')
@patch('asyncio.create_task')
@patch('aiohttp.ClientSession')
@patch('asyncio.Queue')
def test_worker_stops_task(MockQueue, MockClientSession, mock_create_task,
                           mock_crawler_worker_run):
    queue = MockQueue()
    enqueued = set()
    session = MockClientSession()
    worker = crawler.Worker(queue, enqueued, session,
                            crawler.print_page_and_links)
    worker.start()

    mock_create_task().cancel.assert_not_called()
    worker.stop()

    mock_create_task().cancel.assert_called_once()


@pytest.mark.asyncio
@patch('crawler.get_page_links')
@patch('aiohttp.ClientSession')
@patch('asyncio.Queue')
async def test_worker_processes_queue(MockQueue, MockClientSession,
                                      mock_get_page_links):
    session = MockClientSession()
    queue = MockQueue()
    queue.get = AsyncMock(return_value='index.html')
    enqueued = set(['index.html'])
    mock_get_page_links.return_value = set(['foo.html', 'bar.html'])

    worker = crawler.Worker(queue, enqueued, session,
                            crawler.print_page_and_links)

    await worker.process_queue_item()

    assert enqueued == set(['index.html', 'foo.html', 'bar.html'])
    assert queue.put_nowait.call_count == 2
    assert queue.put_nowait.call_args_list[0].args[0] == 'bar.html'
    assert queue.put_nowait.call_args_list[1].args[0] == 'foo.html'


@pytest.mark.asyncio
@patch('crawler.get_page_links')
@patch('aiohttp.ClientSession')
@patch('asyncio.Queue')
async def test_worker_processes_queue_and_dedups(MockQueue, MockClientSession,
                                                 mock_get_page_links):
    session = MockClientSession()
    queue = MockQueue()
    queue.get = AsyncMock(return_value='index.html')
    enqueued = set(['index.html'])
    mock_get_page_links.return_value = set(['foo.html', 'bar.html', 'foo.html'])

    worker = crawler.Worker(queue, enqueued, session,
                            crawler.print_page_and_links)

    await worker.process_queue_item()

    # foo.html appears twice but is only added once
    assert enqueued == set(['index.html', 'foo.html', 'bar.html'])
    assert queue.put_nowait.call_count == 2
    assert queue.put_nowait.call_args_list[0].args[0] == 'bar.html'
    assert queue.put_nowait.call_args_list[1].args[0] == 'foo.html'


@pytest.mark.asyncio
@patch('crawler.get_page_links')
@patch('aiohttp.ClientSession')
@patch('asyncio.Queue')
async def test_worker_processes_queue_does_not_revist(
        MockQueue, MockClientSession, mock_get_page_links):
    session = MockClientSession()
    queue = MockQueue()
    queue.get = AsyncMock(return_value='index.html')
    enqueued = set(['index.html'])
    mock_get_page_links.return_value = set([
        'index.html', 'foo.html', 'bar.html'])

    worker = crawler.Worker(queue, enqueued, session,
                            crawler.print_page_and_links)

    await worker.process_queue_item()

    assert enqueued == set(['index.html', 'foo.html', 'bar.html'])
    assert queue.put_nowait.call_count == 2
    assert queue.put_nowait.call_args_list[0].args[0] == 'bar.html'
    assert queue.put_nowait.call_args_list[1].args[0] == 'foo.html'
