import logging
import math
import time
from peewee import fn
from tqdm import tqdm

from fetch.api import make_request, default_requests_session
from models import Post


logger = logging.getLogger('data')
API_BASE_URL = "https://api.stackexchange.com/2.2/posts/"
DEFAULT_PARAMS = {
    'site': 'stackoverflow',
    'filter': '!)qFc_3CbvFS44UCin0(T',
    'pagesize': '100',
    'key': ')8bWqMwdZLM)87SK8n)LUA((',
}
REQUEST_DELAY = 0.05  # The Stack Exchange API requests you don't query more than 30 times / second
BATCH_SIZE = 100  # Maximum number of posts that can be requested at a time


def fetch_post_bodies(fetch_index):

    # Prepare initial API query parameters
    params = DEFAULT_PARAMS.copy()

    total_posts = Post.select(Post.fetch_index == fetch_index).count()
    batches = math.ceil(float(total_posts) / BATCH_SIZE)

    progress_bar = tqdm(total=total_posts)

    for batch_index in range(1, batches + 1):

        post_batch = (
            Post
            .select()
            .where(Post.fetch_index == fetch_index)
            .paginate(batch_index, BATCH_SIZE)
            )
        post_ids = [str(p.post_id) for p in post_batch]

        # To request multiple posts, join their IDs with a semi-colon.
        url = API_BASE_URL + ";".join(post_ids)
        response = make_request(default_requests_session.get, url, params=params)

        if response is not None:
            response_data = response.json()
            post_body_dict = dict((p['post_id'], p['body']) for p in response_data['items'])

            for post in post_batch:
                if post.post_id in post_body_dict:
                    post.body_html = post_body_dict[post.post_id]
                    post.save()
                    progress_bar.update()

            time.sleep(REQUEST_DELAY)

    progress_bar.close()


def main(fetch_index, *args, **kwargs):  # pylint: disable=unused-argument
    if fetch_index == -1:
        fetch_index = Post.select(fn.Max(Post.fetch_index)).scalar()
    fetch_post_bodies(fetch_index)


def configure_parser(parser):
    parser.description = "Fetch HTML body for Stack Overflow posts."
    parser.add_argument(
        "--fetch-index",
        type=int,
        default=-1,
        help="Index of fetched posts for which to fetch bodies. Defaults to latest."
        )
