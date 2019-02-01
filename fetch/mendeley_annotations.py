import logging
import time
from peewee import fn
from tqdm import tqdm

from fetch.api import make_request, default_requests_session, _get_next_page_url
from models import MendeleyDocument, MendeleyAnnotation


logger = logging.getLogger('data')
API_URL = "https://api.mendeley.com/annotations"
DEFAULT_PARAMS = {
    'limit': 200,  # the maximum number of annotations that can be fetched at once
}
REQUEST_DELAY = 0.1


def _save_annotation(document, annotation, fetch_index):

    annotation_id = annotation['id']

    left = top = right = bottom = None
    if not annotation['positions']:
        logger.warning("Annotation %s does not have any positions. Not saving.", annotation_id)
        return
    if len(annotation['positions']) > 1:
        logger.warning(
            "Annotation %s has more than one position. Saving first position.", annotation_id)

    position = annotation['positions'][0]
    left = position['top_left']['x']
    top = position['top_left']['y']
    right = position['bottom_right']['x']
    bottom = position['bottom_right']['y']
    page = position['page']

    MendeleyAnnotation.create(
        fetch_index=fetch_index,
        document=document,
        annotation_id=annotation_id,
        type=annotation['type'],
        text=annotation.get('text', 'no text'),
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        page=page,
    )


def fetch_annotations(fetch_index, token, document):

    # Prepare initial API query parameters
    params = DEFAULT_PARAMS.copy()
    params['document_id'] = document.document_id

    # Prepare the request authorization
    headers = {'Authorization': 'Bearer ' + token}

    next_page_url = API_URL
    while next_page_url is not None:

        response = make_request(
            default_requests_session.get, next_page_url, params=params, headers=headers)

        if response is not None:
            annotations = response.json()

            # Save records for each annotation
            for annotation in annotations:
                _save_annotation(document, annotation, fetch_index)

            time.sleep(REQUEST_DELAY)

            # Advance to the next page of results
            next_page_url = _get_next_page_url(response)


def main(token, document_fetch_index, *args, **kwargs):  # pylint: disable=unused-argument

    if document_fetch_index == -1:
        document_fetch_index = MendeleyDocument.select(
            fn.Max(MendeleyDocument.fetch_index)).scalar()

    # Create a new fetch index.
    last_fetch_index = MendeleyAnnotation.select(
        fn.Max(MendeleyAnnotation.fetch_index)).scalar() or 0
    fetch_index = last_fetch_index + 1

    documents = (
        MendeleyDocument
        .select()
        .where(
            MendeleyDocument.fetch_index == document_fetch_index
        ))
    for document in tqdm(documents):
        fetch_annotations(fetch_index, token, document)


def configure_parser(parser):
    parser.description = "Fetch annotations for Mendeley documents."
    parser.add_argument(
        "token",
        type=str,
        help=(
            "Mendeley API token. Generate by following directions from " +
            "https://dev.mendeley.com/getting_started/hello_mendeley.html"
            ))
    parser.add_argument(
        "--document-fetch-index",
        type=int,
        default=-1,
        help="Index of Mendeley documents to fetch annotations for. Defaults to most recent."
        )
