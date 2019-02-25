import logging
import time
import datetime
from peewee import fn
from tqdm import tqdm

from fetch.api import make_request, default_requests_session
from models import Post, PostTag


logger = logging.getLogger('data')
API_URL = "https://api.stackexchange.com/2.2/search/excerpts"
DEFAULT_PARAMS = {
    # This filter was created with the form: https://api.stackexchange.com/docs/advanced-search
    # The filter specifies the fields of question data that we want to have returned.
    'site': 'stackoverflow',
    'q': 'is:answer score:1',
    'body': '"this tutorial"',
    'filter': '!S_Vkl7.BKMaT7fJaJ)',
    'key': ')8bWqMwdZLM)87SK8n)LUA((',
    'page_size': 100,  # the maximum page size
}
REQUEST_DELAY = 0.05  # The Stack Exchange API requests you don't query more than 30 times / second


def _save_post(post_data, fetch_index):

    # Dates are returned by the Stack Exchange API in Unix epoch time.
    # This inline method converts the timestamps to datetime objects that
    # can be stored in a Postgres database.  Note that the times will be
    # converted to _local times_ on this server rather than their original
    # UTC times.  I chose to do this as the date of creation of these records
    # will also be in local time.
    timestamp_to_datetime = datetime.datetime.fromtimestamp

    # Create a snapshot of this post
    post = Post.create(
        fetch_index=fetch_index,
        creation_date=timestamp_to_datetime(post_data['creation_date']),
        post_id=post_data['answer_id'],
        title=post_data['title'],
        body_text=post_data['body'],
        score=post_data['score'],
        is_accepted=post_data['is_accepted'],
    )

    # Link this snapshot to all tags related to it
    for tag_name in post_data['tags']:
        PostTag.create(post=post, tag_name=tag_name)


def fetch_posts(fetch_index):

    # Prepare initial API query parameters
    params = DEFAULT_PARAMS.copy()
    params['page'] = 1  # paging for Stack Exchange API starts at 1

    # We intentionally choose to iterate until the results tell us there are 'no more'.
    # The Stack Exchange API documents tell us that requesting a 'total' from the API
    # will double the request time, so we don't fetch the total.
    more_results = True

    progress_bar = None
    while more_results:

        response = make_request(default_requests_session.get, API_URL, params=params)

        if response is not None:
            response_data = response.json()

            # Create the progress bar
            if progress_bar is None and response_data['total'] is not None:
                progress_bar = tqdm(total=response_data['total'])

            for post in response_data['items']:
                _save_post(post, fetch_index)

                if progress_bar is not None:
                    progress_bar.update()

            # Advance the page if there are more results coming
            more_results = response_data['has_more'] if response is not None else True
            time.sleep(REQUEST_DELAY)
            params['page'] += 1

    if progress_bar is not None:
        progress_bar.close()


def main(*args, **kwargs):  # pylint: disable=unused-argument

    # Create a new fetch index.
    last_fetch_index = Post.select(fn.Max(Post.fetch_index)).scalar() or 0
    fetch_index = last_fetch_index + 1
    fetch_posts(fetch_index)


def configure_parser(parser):
    parser.description = "Fetch Stack Overflow posts that reference tutorials."
