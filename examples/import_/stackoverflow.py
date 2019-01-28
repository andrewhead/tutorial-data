#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import logging
import xml.etree.cElementTree as etree
import re
import os.path
# WARNING: progressbar no longer in use for this repository. Replace with tqdm.
from progressbar import ProgressBar, Percentage, Bar, ETA, Counter, RotatingMarker

from models import BatchInserter
from models import Post, Tag, PostHistory, PostLink, Vote, Comment, Badge, User


logger = logging.getLogger('data')

# This is a map from names of data types to the models they correspond to.
# To enable importing a new type of data, one should define a new model
# in the models module, and then add an entry here.
DATA_TYPES = {
    'posts': Post,
    'tags': Tag,
    'post-histories': PostHistory,
    'post-links': PostLink,
    'votes': Vote,
    'comments': Comment,
    'badges': Badge,
    'users': User,
}


# A cache for storing translations of camel case spellings to underscores
translation_cache = {}


def camel_case_to_underscores(string):
    '''
    Method courtesy of Stack Overflow user epost:
    http://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
    '''
    if string in translation_cache:
        return translation_cache[string]
    else:
        translated1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)
        translated2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', translated1).lower()
        translation_cache[string] = translated2
        return translated2


def main(data_type, data_file, batch_size, show_progress, *args, **kwargs):
    '''
    Parsing procedure is based on a script by a user on the Meta Stack Exchange:
    http://meta.stackexchange.com/questions/28221/scripts-to-convert-data-dump-to-other-formats
    '''

    Model = DATA_TYPES[data_type]
    batch_inserter = BatchInserter(Model, batch_size, fill_missing_fields=True)

    # Set up progress bar.
    if show_progress:
        file_size = os.path.getsize(data_file)
        progress_bar = ProgressBar(maxval=file_size, widgets=[
            'Progress: ', Percentage(),
            ' ', Bar(marker=RotatingMarker()),
            ' ', ETA(),
            ' Read ', Counter(), ' characters.'
        ])
        progress_bar.start()
        amount_read = 0

    # Read data from XML file and load it into the table
    with open(data_file) as data_file_obj:

        # Events need to be written as "bytes".
        # Reference: http://bugs.python.org/msg110252
        # By default in this file, strings are declared as Unicode, so we declare them as bytes
        tree = etree.iterparse(data_file_obj, events=(b'start', b'end'))
        for event, row in tree:

            # Save the parent element of the rows so that we can clean up memory as we go
            # Apparently, `iterparse` isn't good at cleaning up after itself
            # (http://stackoverflow.com/questions/7697710/python-running-out-of-memory-parsing-xml-using-celementtree-iterparse).
            if event == 'start' and row.tag != 'row':
                parent_element = row

            # Skip this row if it is not a primary record in the file
            if not (event == 'end' and row.tag == 'row'):
                continue

            # Format attributes as kwargs for creating the model
            attributes = row.attrib
            renamed_attributes = {camel_case_to_underscores(k): v for k, v in attributes.items()}

            # Records shouldn't have a 'class' field, as this conflicts with Python syntax
            if 'class' in renamed_attributes.keys():
                renamed_attributes['class_'] = renamed_attributes['class']
                del(renamed_attributes['class'])

            batch_inserter.insert(renamed_attributes)

            if show_progress:
                string_size = len(etree.tostring(row))
                amount_read += string_size
                progress_bar.update(amount_read)

            # Clean up the allocated XML element
            row.clear()
            parent_element.remove(row)

    # Insert any remaining data that wasn't in one of the batches
    batch_inserter.flush()

    if show_progress:
        progress_bar.finish()


def configure_parser(parser):
    parser.description = "Import data from a Stack Overflow dump."
    parser.add_argument(
        'data_type',
        choices=DATA_TYPES.keys(),
        help="The type of data to import."
    )
    parser.add_argument(
        'data_file',
        help="XML file containing a dump of Stack Overflow data."
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=20,
        help="The number of records to insert at a time. Increasing this value " +
        "should greatly increase the speed of importing data. " +
        "The default value %(default)s was chosen to work " +
        "for all models, for all databases."
    )
    parser.add_argument(
        '--show-progress',
        action='store_true',
        help="Show progress in loading content from the file. " +
        "Note that this may slow down execution as the program will have " +
        "to count the amount of the file that is being read."
    )
