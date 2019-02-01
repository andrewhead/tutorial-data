import json
import logging
import os.path
from tqdm import tqdm
import pdfkit


logger = logging.getLogger('data')


def _fetch_pdf(urls, tutorial_id):
    OUTPUT_DIRECTORY = os.path.join('data', 'pdfs')
    if not os.path.exists(OUTPUT_DIRECTORY):
        os.makedirs(OUTPUT_DIRECTORY)

    OUTPUT_FILENAME = os.path.join(OUTPUT_DIRECTORY, str(tutorial_id) + '.pdf')
    try:
        pdfkit.from_url(
            urls,
            OUTPUT_FILENAME,
            {
                'quiet': None,
                'page-width': 200,
                'page-height': 2000,
                'title': tutorial_id,
            })
    except OSError as e:
        print(e)
        logger.warning("Could not download PDF: %s", e)


def fetch_tutorials(tutorials):
    for tutorial in tqdm(tutorials):
        urls = tutorial['links'].split(' ')
        _fetch_pdf(urls, tutorial['tutorial_id'])


def main(tutorials_filename, *args, **kwargs):  # pylint: disable=unused-argument
    tutorials = []
    with open(tutorials_filename) as tutorials_file:
        for line in tutorials_file:
            tutorials.append(json.loads(line))
    fetch_tutorials(tutorials)


def configure_parser(parser):
    parser.description = "Fetch PDFs for a set of tutorials."
    parser.add_argument(
        'tutorials_filename',
        type=str,
        help=(
            "Data file where each line describes a tutorial. Each line is a separate JSON " +
            "object with two keys: tutorial_id (a unique ID for the tutorial) and links (a " +
            "string containing URLs where the tutorial is hosted, with each URL delimited by ' '"
            )
        )
