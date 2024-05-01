import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urldefrag, urljoin, urlparse

MONITOR_SLEEP_MS = 250
SITE_NAME = 'www.joanorr.com'
NUM_WORKERS = 5
SITE_ROOT_URL = '/'


async def main():
    enqueued = set()
    queue = asyncio.Queue()
    queue.put_nowait(SITE_ROOT_URL)
    enqueued.add(SITE_ROOT_URL)

    async with aiohttp.ClientSession(f'http://{SITE_NAME}') as session:
        workers = [Worker(queue, enqueued, session)
                   for _ in range(NUM_WORKERS)]
        for worker in workers:
            worker.start()
        all_tasks = [worker.task for worker in workers] + [monitor(workers),]
        await asyncio.gather(*all_tasks)


async def monitor(workers):
    while True:
        # Note, monitor must yield first in order to give the workers a chance to
        # get their first url off the queue.
        await asyncio.sleep(MONITOR_SLEEP_MS / 1000)

        if all([worker.state is Worker.STATE_AWAITINMG_QUEUE
                for worker in workers]):
            break

    for worker in workers:
        worker.stop()


class Worker(object):
    STATE_UNSPECIFIED = 0
    STATE_AWAITING_PAGE_GET = 1
    STATE_AWAITINMG_QUEUE = 2

    def __init__(self, queue, enqueued, session):
        self.__state = self.STATE_UNSPECIFIED
        self.__queue = queue
        self.__enqueued = enqueued
        self.__session = session

    @property
    def state(self):
        return self.__state

    @property
    def task(self):
        return self.__task

    def start(self):
        self.__task = asyncio.create_task(self.run())

    def stop(self):
        self.__task.cancel()

    async def run(self):
        while True:
            self.__state = self.STATE_AWAITINMG_QUEUE
            url = await self.__queue.get()

            self.__state = self.STATE_AWAITING_PAGE_GET
            result = await get_page_links(self.__session, url)
            # result = await get_list(url)

            self.__state = self.STATE_UNSPECIFIED
            for i in result:
                if i not in self.__enqueued:
                    self.__queue.put_nowait(i)
                    self.__enqueued.add(i)
            self.__queue.task_done()


async def get_page_links(session, url):
    async with session.get(url) as response:
        if response.headers['content-type'] != 'text/html':
            return set()

        html = await response.text()
        return extract_links_from_page(url, html)


def extract_links_from_page(page_url, html):
    page_soup = BeautifulSoup(html, 'html.parser')
    href_list = [a['href']
                 for a in page_soup.find_all('a') if a.has_attr('href')]
    links_set = set()
    for link_url in href_list:
        parsed_url = urlparse(link_url)
        if (parsed_url.scheme in ['', 'http', 'https'] and
            parsed_url.netloc in ['', SITE_NAME]):
            links_set.add(resolve_link_url(page_url, page_soup, link_url))
    print(page_url, links_set)
    return links_set


def resolve_link_url(page_url, page_soup, link_url):
    base_tag = page_soup.find("base")
    base_url = base_tag["href"] if base_tag else page_url
    resolved_link_url = urljoin(base_url, link_url)
    defragged_link_url = urldefrag(resolved_link_url).url
    return defragged_link_url


try:
    asyncio.run(main())
except asyncio.CancelledError:
    print('Done')
