from abc import ABC, abstractmethod
import argparse
from dataclasses import dataclass
import pickle
import re
import subprocess
import requests
from bs4 import BeautifulSoup
import time
import traceback
# Move cwd to the directory of this file
import os
import shlex

os.chdir(os.path.dirname(os.path.abspath(__file__)))


urls_to_ignore = ["/threads/rules-terms-of-service"]

PROBLEM_WORD_COUNT_NOT_FOUND = "word count not found"


class Exception404(Exception):
    pass


@dataclass
class RateLimitPoint:
    time: float
    requests: int


@dataclass
class Thread:
    name: str
    url: str
    word_count: str = "-1"


class BaseSite(ABC):
    url: str
    url_pattern: str
    start_text: str
    end_text: str
    error_text: str
    rate_limit_time: int = 5
    """ How long to wait between requests, in seconds, if we get rate limited """

    @abstractmethod
    def get_word_count_text(self, threadmark_text: str) -> str:
        pass


class SV(BaseSite):
    url_pattern = "{}/threadmarks"
    start_text = "Statistics ("
    end_text = "words"
    error_text = "Oops! We ran into some problems."

    def __init__(self, url) -> None:
        super().__init__()
        self.url = url
        print("\n")
        print("=========================")
        print("== Sufficient Velocity ==")
        print("=========================")

    def get_word_count_text(self, threadmark_text: str) -> str:
        start = threadmark_text.find(self.start_text)
        if start == -1:
            return PROBLEM_WORD_COUNT_NOT_FOUND

        end = threadmark_text.find(self.end_text, start)
        if end == -1:
            return PROBLEM_WORD_COUNT_NOT_FOUND

        wc_text = threadmark_text[start+len(self.start_text):end]

        if wc_text == "":
            return PROBLEM_WORD_COUNT_NOT_FOUND
        elif len(wc_text) < 5:
            # If the word count is less than 5 characters, it's probably wrong
            print(f"WARNING: Word count is less than 5 characters. '{wc_text}'")
        
        return wc_text
class QQ(BaseSite):
    url = "https://forum.questionablequesting.com/threads/questing-for-insertion-qq-self-insert-archive.1094"
    url_pattern = "{}/threadmarks?category_id=1"
    start_text = "Statistics ("
    threadmark_pattern = r"\t*((?:\d+,)?\d+[\s\w]+), Word Count: (\d+\.?\d+[kKmM]?)"
    error_text = "Oops! We ran into some problems."

    def __init__(self) -> None:
        super().__init__()
        print("\n")
        print("===========================")
        print("== Questionable Questing ==")
        print("===========================")


    def get_word_count_text(self, threadmark_text: str) -> str:
        """
        QQ's threadmark page has a different format than SV's

        QQ's format is::
    
            Statistics x,xxx threadmarks, Word Count: x[k|m]

        But the output from BeautifulSoup looks like this (example)::

            Statistics\\t\\t\\t7 threadmarks, Word Count: 4.9k9adam4 (7 threadmarks)

        So use the regex to extract the threadmarks and word count, groups 1 and 2 respectively
        """
        start = threadmark_text.find(self.start_text)
        if start == -1:
            return PROBLEM_WORD_COUNT_NOT_FOUND
        
        cur_text = threadmark_text[start+len(self.start_text):]
        match = re.search(self.threadmark_pattern, cur_text)
        if match is None:
            return PROBLEM_WORD_COUNT_NOT_FOUND
        
        return f"{match.group(1)}, {match.group(2)}"
    
        

        
class SB(BaseSite):
    url = ""
    url_pattern = "{}/threadmarks"
    start_text = "Word Count:"
    end_text = "K"
    error_text = "Oops! We ran into some problems."

class Scraper:
    def __init__(self, site: BaseSite):
        self.site = site
        self.links_found: list[Thread] = []

        self.rate_limited = False
        self.rate_calc: list[RateLimitPoint] = []

    def parse_index_page(self, url, start_link,
                         end_link,
                         prev_threads: list[Thread] = None) -> list[Thread]:
        """
        Parse the index page of a thread, and return a list of all the threads. 
        Does not count the word count of the threads.

        @param url: The url of the index page
        @param start_link: The name of the first thread to parse 
        @param end_link: The name of the last thread to parse
        @return: A list of all the threads between start_link and end_link
        """
        print(f"Parse {url}")

        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')

        links = soup.find_all('a')
        threads: list[Thread] = []

        start = False
        for link in links:
            if link.text == start_link:
                start = True
                continue

            # If, for some reason, someone uses a vertical bar in their thread name
            # we'll just delete it
            link_text = link.text.replace("|", "")

            if not start or not self._is_link_useful(
                    link.get('href'),
                    link_text):
                continue

            threads.append(Thread(link_text, link.get('href')))

            if link_text == end_link:
                break

        if prev_threads is not None:
            threads = prev_threads + threads

        return threads

    def status_code_429(self, page: requests.Response, p_cur, p_max) -> None:
        self.hit_rate_limit(p_cur, p_max)

        print(f"(..{p_cur}/{p_max}..)")
        time.sleep(self.site.rate_limit_time)

    def hit_rate_limit(self, p_cur: int, p_max: int):
        """
        Once the rate limit kicks in, we can calculate how many requests per second
        we successfully are making.
        Then, we can use that to get an ETA on how long it will take to finish the
        program.
        """
        # First, handle when we just hit the rate limit
        if not self.rate_limited:
            self.rate_limited = True
            self.rate_calc = [RateLimitPoint(time.time(), p_cur)]
            return

        # If we're already rate limited, we need to calculate the rate
        # We'll calculate the rate by taking the number of requests we've made
        # since we were last rate limited, and dividing that by the time since
        # we were last rate limited
        # We'll then take the average of the last 5 rates, and use that to
        # calculate the ETA
        self.rate_calc.append(RateLimitPoint(time.time(), p_cur))
        if len(self.rate_calc) > 5:
            self.rate_calc.pop(0)

        # Calculate the rate
        rate = (self.rate_calc[-1].requests - self.rate_calc[0].requests) / \
            (self.rate_calc[-1].time - self.rate_calc[0].time)

        # Calculate the ETA
        eta = (p_max - p_cur) / rate

        print(f"Rate limited! Rate: {rate:.2f} req/s, ETA: {self.fmt_sec(int(eta))}")

    @staticmethod
    def fmt_sec(sec: int) -> str:
        """ Format seconds into a string: HH:MM:SS """
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def get_word_count(self, thread: Thread, p_cur: int = -1, p_max: int = -1) -> str:
        """
        Get the word count of a thread from its threadmark page

        Given the content of a threadmark page, try to get the word count.

        On SV, if a story has few enough chapters, the threadmark page doesn't display the
        `/Statistics \(\d+ threadmarks, /\d+\.?\d+[KM]?/ words\)/` line.


        @param url: The url of the threadmark page
        @return: Number of threadmarks + word count of the thread
        """
        full_url = self.site.url_pattern.format(thread.url)
        while True:
            try:
                page = requests.get(full_url)

                # "Unlisted Fiction" returns a 404 when you try to access it
                # if you're not logged in
                # Check if we're getting a 404
                if page.status_code == 404:
                    raise Exception404(full_url)
                # Check if we're getting rate throttled (429)
                if page.status_code == 429:
                    self.status_code_429(page, p_cur, p_max)
                    continue

                soup = BeautifulSoup(page.content, 'html.parser')
                # Get the text of the page, and make sure to remove newlines,
                # since we don't want any extraneous newlines in the CSV, since it
                # will mess up the formatting
                text = soup.get_text().replace("\n", "")

                # Check if we get some kind of error message
                if self.site.error_text in text:
                    raise Exception(
                        f"Some other error happened, code: {page.status_code}")

                return self.site.get_word_count_text(text)

            except:
                raise

    def retrieve_word_counts(self, threads: list[Thread]):
        """
        Retrieve the word counts of the threads
        """
        for i, thread in enumerate(threads):
            try:
                thread.word_count = self.get_word_count(
                    thread, p_cur=i+1, p_max=len(threads))
            except Exception as e:
                print(f"Error with '{thread.url}': '{e}'")
                traceback.print_exc()
                continue

            # Ensure no newlines in anything
            thread.name = thread.name.replace("\n", "")
            thread.word_count = thread.word_count.replace("\n", "")
            print(f"{thread.name}: {thread.word_count}")

    def _is_link_useful(self, link_raw: str, link_text_raw: str) -> bool:
        """
        Check if a link found on the index page is useful 
        """
        if link_raw is None or link_raw == "" or link_text_raw is None or link_text_raw == "":
            return False

        link = link_raw.strip()
        link_text = link_text_raw.strip()

        if not link.startswith("http") or link in urls_to_ignore \
                or link_text is None or link_text == "" \
                or "Sufficiently Velocity" in link_text or "into a problem" in link_text:
            return False
        return True

def init_argparse() -> argparse.ArgumentParser:
    """
    Two arguments, booleans:
    * --sufficient-velocity (-sv)
    * --questionable-questing (-qq)
    * --archive-of-our-own (-ao3)
    """
    parser = argparse.ArgumentParser(
        description="Scrape word counts from SI fanfics on various sites")
    parser.add_argument("-sv", "--sufficient-velocity", action="store_true",
                        help="Scrape word counts from Sufficient Velocity")
    parser.add_argument("-qq", "--questionable-questing", action="store_true",
                        help="Scrape word counts from Questionable Questing")
    parser.add_argument("-ao3", "--archive-of-our-own", action="store_true",
                        help="Scrape word counts from Archive of Our Own")
    parser.add_argument("--start-page", type=int, default=1,
                        help="Start page for AO3 scraping")
    return parser


def run_scraper_sv():
    url = "https://forums.sufficientvelocity.com/threads/sufficiently-inserted-sv-self-insert-archive-v2-0.41389"
    scraper = Scraper(SV(url))

    threads = scraper.parse_index_page(
        scraper.site.url,
        "Go! Unashamed Reincarnation Protagonist Sakura! (Naruto SI)",
        "Come Hell or Helheim (Worm Duo-SI)")
    threads = scraper.parse_index_page(
        scraper.site.url + "/page-2",
        "The Gardener's Tale (Star Wars SI)",
        "My Wish (Worm CYOA SI)",
        threads)

    print(f"Found {len(threads)} threads")
    print("Retrieving word counts...")

    try:
        scraper.retrieve_word_counts(threads)
    except Exception as e:
        print(f"Top level error with {e}!")
        print("Stopping here, outputting what we have.")

    # Pickle the threads in case we need to restart
    with open("sv-threads.pkl", "wb") as f:
        pickle.dump(threads, f)

    # Write threads to CSV file with delimeter = '|'
    # Filename should be current datetime
    with open(f"sv-output-{time.strftime('%Y-%m-%d-%H-%M-%S')}.csv", "w", encoding="utf-8") as f:
        for thread in threads:
            f.write(f"{thread.name}|{thread.url}|{thread.word_count}\n")


def run_scraper_qq():
    url = "https://forum.questionablequesting.com/threads/questing-for-insertion-qq-self-insert-archive.1094"
    scraper = Scraper(SV(url))

    threads = scraper.parse_index_page(
        scraper.site.url,
        "Complete Detachment (Star Wars Prequel SI)",
        "Bruh...I'm Dead AF (DxD SI)")

    print(f"Found {len(threads)} threads")
    print("Retrieving word counts...")

    try:
        scraper.retrieve_word_counts(threads)
    except Exception as e:
        print(f"Top level error with {e}!")
        print("Stopping here, outputting what we have.")

    # Write threads to CSV file with delimeter = '|'
    # Filename should be current datetime
    with open(f"qq-output-{time.strftime('%Y-%m-%d-%H-%M-%S')}.csv", "w") as f:
        for thread in threads:
            f.write(f"{thread.name}|{thread.url}|{thread.word_count}\n")


def run_scraper_ao3(start_page):
    """
    Use AO3Scraper from https://github.com/radiolarian/AO3Scraper instead of writing our own.

    Run the AO3Scraper with the following command:
    ```
    python AO3Scraper/ao3_work_ids.py https://archiveofourown.org/tags/Self-Insert/works?commit=Sort+and+Filter&page=1&work_search%5Bcomplete%5D=&work_search%5Bcrossover%5D=&work_search%5Bdate_from%5D=&work_search%5Bdate_to%5D=&work_search%5Bexcluded_tag_names%5D=&work_search%5Blanguage_id%5D=&work_search%5Bother_tag_names%5D=&work_search%5Bquery%5D=&work_search%5Bsort_column%5D=word_count&work_search%5Bwords_from%5D=&work_search%5Bwords_to%5D=
    ```

    Output the CSV file to the current directory.
    """
    url = "https://archiveofourown.org/tags/Self-Insert/works?commit=Sort+and+Filter&page=1&work_search%5Bcomplete%5D=&work_search%5Bcrossover%5D=&work_search%5Bdate_from%5D=&work_search%5Bdate_to%5D=&work_search%5Bexcluded_tag_names%5D=&work_search%5Blanguage_id%5D=&work_search%5Bother_tag_names%5D=&work_search%5Bquery%5D=&work_search%5Bsort_column%5D=word_count&work_search%5Bwords_from%5D=&work_search%5Bwords_to%5D="
    command = f"python AO3Scraper/ao3_work_ids.py '{url}' --start_page {start_page} --out_csv=ao3-output-{time.strftime('%Y-%m-%d-%H-%M-%S')}"

    # Run the command with subprocess
    s = subprocess.run(shlex.split(command))
    print(s)

if __name__ == "__main__":
    args = init_argparse().parse_args()

    if args.sufficient_velocity:
        run_scraper_sv()
    if args.questionable_questing:
        run_scraper_qq()
    if args.archive_of_our_own:
        run_scraper_ao3(int(args.start_page))

    print("Done!")
