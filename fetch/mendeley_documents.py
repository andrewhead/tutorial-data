import logging
import time
from peewee import fn
from tqdm import tqdm

from fetch.api import make_request, default_requests_session, _get_mendeley_item_count, \
    _get_next_page_url
from models import MendeleyDocument


logger = logging.getLogger('data')
API_URL = "https://api.mendeley.com/documents"
DEFAULT_PARAMS = {
    'limit': 500,  # the maximum number of documents
}
REQUEST_DELAY = 0.1  # The Stack Exchange API requests you don't query more than 30 times / second
tag_cache = {}  # We avoid querying for tags when we don't need to by keeping them in this cache.


def _save_document(document, fetch_index):
    MendeleyDocument.create(
        fetch_index=fetch_index,
        title=document['title'],
        document_id=document['id'],
    )


def fetch_documents(fetch_index, token, group_id):

    # Prepare initial API query parameters
    params = DEFAULT_PARAMS.copy()
    params['group_id'] = group_id

    # Prepare the request authorization
    headers = {'Authorization': 'Bearer ' + token}

    # We intentionally choose to iterate until the results tell us there are 'no more'.
    # The Stack Exchange API documents tell us that requesting a 'total' from the API
    # will double the request time, so we don't fetch the total.
    next_page_url = API_URL

    first_iteration = True
    progress_bar = None
    while next_page_url is not None:

        response = make_request(
            default_requests_session.get, next_page_url, params=params, headers=headers)

        if response is not None:
            documents = response.json()

            # Create the progress bar if we know the total number of documents
            item_count = _get_mendeley_item_count(response)
            if item_count is not None and first_iteration and progress_bar is None:
                progress_bar = tqdm(total=item_count)

            # Save records for each document
            for document in documents:
                _save_document(document, fetch_index)

                if progress_bar is not None:
                    progress_bar.update()

            time.sleep(REQUEST_DELAY)

            # Advance to the next page of results
            next_page_url = _get_next_page_url(response)

        first_iteration = False

    if progress_bar is not None:
        progress_bar.close()


def main(group_id, token, *args, **kwargs):  # pylint: disable=unused-argument

    # Create a new fetch index.
    last_fetch_index = MendeleyDocument.select(fn.Max(MendeleyDocument.fetch_index)).scalar() or 0
    fetch_index = last_fetch_index + 1
    fetch_documents(fetch_index, token, group_id)


def configure_parser(parser):
    parser.description = "Fetch Mendeley document IDs for a group."
    parser.add_argument(
        "group_id",
        type=str,
        help=(
            "ID of a Mendeley group for which to retrieve all documents. To find the ID of " +
            "a group, use the Mendeley API explorer for your account at " +
            "https://api.mendeley.com/apidocs/docs#!/groups"
            ))
    parser.add_argument(
        "token",
        type=str,
        help=(
            "Mendeley API token. Generate by following directions from " +
            "https://dev.mendeley.com/getting_started/hello_mendeley.html"
            ))
