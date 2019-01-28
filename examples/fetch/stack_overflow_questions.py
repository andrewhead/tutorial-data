#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import logging
import time
from peewee import fn
import datetime

from fetch.api import make_request, default_requests_session
from models import QuestionSnapshot, Tag, QuestionSnapshotTag


logger = logging.getLogger('data')
API_URL = "https://api.stackexchange.com/2.2/search/advanced"
DEFAULT_PARAMS = {
    # This filter was created with the form: https://api.stackexchange.com/docs/advanced-search
    # The filter specifies the fields of question data that we want to have returned.
    'filter': '!-NChB-j*JnX7P6Vg_m6ss21bRoVv((_0x',
    'site': 'stackoverflow',
    'key': ')8bWqMwdZLM)87SK8n)LUA((',
    'page_size': 100,  # the maximum page size
}
REQUEST_DELAY = 0.1  # The Stack Exchange API requests you don't query more than 30 times / second
tag_cache = {}  # We avoid querying for tags when we don't need to by keeping them in this cache.


def _save_question(question, fetch_index):

    # It seems that the the ID of the owner is missing from some records.
    # This little bit of logic checks to see if it's missing.
    owner_id = question['owner']['user_id']\
        if 'owner' in question and 'user_id' in question['owner']\
        else None

    # Dates are returned by the Stack Exchange API in Unix epoch time.
    # This inline method converts the timestamps to datetime objects that
    # can be stored in a Postgres database.  Note that the times will be
    # converted to _local times_ on this server rather than their original
    # UTC times.  I chose to do this as the date of creation of these records
    # will also be in local time.
    timestamp_to_datetime = lambda ts: datetime.datetime.fromtimestamp(ts)

    # Create a snapshot of this question
    snapshot = QuestionSnapshot.create(
        fetch_index=fetch_index,
        question_id=question['question_id'],
        owner_id=owner_id,
        comment_count=question['comment_count'],
        delete_vote_count=question['delete_vote_count'],
        reopen_vote_count=question['reopen_vote_count'],
        close_vote_count=question['close_vote_count'],
        is_answered=question['is_answered'],
        view_count=question['view_count'],
        favorite_count=question['favorite_count'],
        down_vote_count=question['down_vote_count'],
        up_vote_count=question['up_vote_count'],
        answer_count=question['answer_count'],
        score=question['score'],
        last_activity_date=timestamp_to_datetime(question['last_activity_date']),
        creation_date=timestamp_to_datetime(question['creation_date']),
        title=question['title'],
        body=question['body'],
    )

    # Link this snapshot to all tags related to it
    for tag_name in question['tags']:

        if tag_name in tag_cache:
            tag = tag_cache[tag_name]
        else:
            try:
                tag = Tag.get(tag_name=tag_name)
            except Tag.DoesNotExist:
                tag = None
            tag_cache[tag_name] = tag

        if tag is not None:
            QuestionSnapshotTag.create(question_snapshot_id=snapshot.id, tag_id=tag.id)


def fetch_questions_for_tag(tag, fetch_index):

    # Prepare initial API query parameters
    params = DEFAULT_PARAMS.copy()
    params['tagged'] = tag
    params['page'] = 1  # paging for Stack Exchange API starts at 1

    # We intentionally choose to iterate until the results tell us there are 'no more'.
    # The Stack Exchange API documents tell us that requesting a 'total' from the API
    # will double the request time, so we don't fetch the total.
    more_results = True
    while more_results:

        response = make_request(default_requests_session.get, API_URL, params=params)

        if response is not None:
            response_data = response.json()
            for question in response_data['items']:
                _save_question(question, fetch_index)

        # Advance the page if there are more results coming
        more_results = response_data['has_more'] if response is not None else True
        time.sleep(REQUEST_DELAY)
        params['page'] += 1


def main(tags, *args, **kwargs):

    # Create a new fetch index.
    last_fetch_index = QuestionSnapshot.select(fn.Max(QuestionSnapshot.fetch_index)).scalar() or 0
    fetch_index = last_fetch_index + 1

    with open(tags) as tag_file:
        tag_list = [t.strip() for t in tag_file.readlines()]

    for tag in tag_list:
        fetch_questions_for_tag(tag, fetch_index)


def configure_parser(parser):
    parser.description = "Fetch snapshots of Stack Overflow questions related to a list of tags."
    parser.add_argument(
        'tags',
        help="the name of a file containing a list of Stack Overflow tags " +
             "for which to fetch question."
    )
