"""A simple web crawler to scrape links from a website.

Example command line usage:

  python3 crawler.py --root_url=http://www.joanorr.com

Flags:

  --num_workers: Number of worker tasks to run.
    (an integer, default: '5')
  --root_url: The site root url, e.g. http://www.joanorr.com/index.html
"""

from absl import app, flags
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Callable, List, Set
from urllib.parse import urldefrag, urljoin, urlparse

MONITOR_SLEEP_MS = 250
DEFAULT_NUM_WORKERS = 5

FLAGS = flags.FLAGS
flags.DEFINE_string('root_url', None,
                    'The site root url, e.g. http://www.joanorr.com/index.html')
flags.DEFINE_integer('num_workers', DEFAULT_NUM_WORKERS,
                     'Number of worker tasks to run.')

flags.mark_flag_as_required('root_url')


async def set_up_tasks(
        root_url: str, num_workers: int,
        output_page_and_links_function: Callable[[str, Set[str]], str]) -> None:
    # An async queue to hold the page links for processing by worker tasks.
    queue = asyncio.Queue()
    # A set to dedup page links.
    enqueued = set()
    queue.put_nowait(root_url)
    enqueued.add(root_url)

    async with aiohttp.ClientSession() as session:
        workers = [Worker(queue, enqueued, session,
                          output_page_and_links_function)
                   for _ in range(num_workers)]
        for worker in workers:
            worker.start()
        all_tasks = [worker.task for worker in workers] + [monitor(workers),]
        await asyncio.gather(*all_tasks)


class Worker:
    """A worker which extracts link URLs from the pages on the queue."""
    STATE_UNSPECIFIED = 0
    STATE_AWAITING_PAGE_GET = 1
    STATE_AWAITINMG_QUEUE = 2

    def __init__(self, queue: asyncio.Queue, enqueued: Set[str],
                 session: aiohttp.ClientSession,
                 output_page_and_links_function: Callable[[str, Set[str]], str]
                 ) -> None:
        self.__state = self.STATE_UNSPECIFIED
        self.__queue = queue
        self.__enqueued = enqueued
        self.__session = session
        self.__output_page_and_links = output_page_and_links_function

    @property
    def state(self) -> int:
        return self.__state

    @property
    def task(self) -> asyncio.Task:
        return self.__task

    def start(self) -> None:
        self.__task = asyncio.create_task(self.run())

    def stop(self) -> None:
        self.__task.cancel()

    async def run(self) -> None:
        while True:
            await self.process_queue_item()

    async def process_queue_item(self) -> None:
        self.__state = self.STATE_AWAITINMG_QUEUE
        url = await self.__queue.get()

        self.__state = self.STATE_AWAITING_PAGE_GET
        links_set = await get_page_links(
            self.__session, url)
        self.__output_page_and_links(url, links_set)

        self.__state = self.STATE_UNSPECIFIED
        for link in sorted(links_set):
            if link not in self.__enqueued:
                self.__queue.put_nowait(link)
                self.__enqueued.add(link)
        self.__queue.task_done()


async def get_page_links(session: aiohttp.ClientSession, url: str) -> Set[str]:
    async with session.get(url) as response:
        if not response.headers['content-type'].startswith('text/html'):
            return set()

        html = await response.text()
        links_set = extract_links_from_page(url, html)
        return links_set


def extract_links_from_page(page_url: str, html: str) -> Set[str]:
    site_name = urlparse(page_url).netloc
    page_soup = BeautifulSoup(html, 'html.parser')
    href_list = [a['href']
                 for a in page_soup.find_all('a') if a.has_attr('href')]
    links_set = set()
    for link_url in href_list:
        parsed_url = urlparse(link_url)
        if (parsed_url.scheme in ['', 'http', 'https'] and
                parsed_url.netloc in ['', site_name]):
            links_set.add(resolve_link_url(page_url, page_soup, link_url))
    return links_set


def resolve_link_url(page_url: str, page_soup: BeautifulSoup,
                     link_url: str) -> str:
    base_tag = page_soup.find('base')
    base_url = base_tag['href'] if base_tag else page_url
    resolved_link_url = urljoin(base_url, link_url)
    defragged_link_url = urldefrag(resolved_link_url).url
    return defragged_link_url


def print_page_and_links(page_url: str, links_set: Set[str]) -> None:
    if links_set:
        print(f'Links found on {page_url}')
        for link_url in links_set:
            print(f'  {link_url}')
        print()
    else:
        print(f'No links found on {page_url}')
        print()


async def monitor(workers: List[Worker]) -> None:
    """A monitor task which stops the crawl when no more links are available."""
    while True:
        # Note, monitor must yield first in order to give the workers a chance
        # to get their first url off the queue.
        await asyncio.sleep(MONITOR_SLEEP_MS / 1000)

        if all([worker.state is Worker.STATE_AWAITINMG_QUEUE
                for worker in workers]):
            break

    for worker in workers:
        worker.stop()


def main(unused_argv: List[str]):
    try:
        asyncio.run(set_up_tasks(FLAGS.root_url, FLAGS.num_workers,
                                 print_page_and_links))
    except asyncio.CancelledError:
        print('Done')


if __name__ == '__main__':
    app.run(main)
