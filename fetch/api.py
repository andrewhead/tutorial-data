#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import requests
import logging
import time
import re


logger = logging.getLogger('data')


USER_AGENT = "Andrew Head (for academic research) <andrewhead@eecs.berekeley.edu>"
default_requests_session = requests.Session()
default_requests_session.headers['User-Agent'] = USER_AGENT


def make_request(method, *args, **kwargs):

    # We read the max_attempts and retry_delay arguments from the kwargs dictionary
    # instead of named kwargs because we want to preserve the order of the
    # "request" method's positional arguments for clients of this method.
    max_attempts = kwargs.get('max_attempts', 2)
    retry_delay = kwargs.get('retry_delay', 10)

    try_again = True
    attempts = 0
    res = None

    def log_error(err_msg):
        logger.warning(
            "Error (%s) For API call %s, Args: %s, Kwargs: %s",
            str(err_msg), str(method), str(args), str(kwargs)
        )

    while try_again and attempts < max_attempts:

        try:
            res = method(*args, **kwargs)
            if hasattr(res, 'status_code') and res.status_code not in [200]:
                log_error(str(res.status_code))
                res = None
            try_again = False
        except requests.exceptions.ConnectionError:
            log_error("ConnectionError")
        except requests.exceptions.ReadTimeout:
            log_error("ReadTimeout")

        if try_again:
            logger.warning("Waiting %d seconds for before retrying.", int(retry_delay))
            time.sleep(retry_delay)
            attempts += 1

    return res


def _get_mendeley_item_count(response):
    '''
    Returns and integer if a count was found, otherwise returns None.
    See https://dev.mendeley.com/reference/topics/pagination.html for more documentation.
    '''

    if 'mendeley-count' not in response.headers:
        return None

    count = response.headers['mendeley-count']
    count_int = None
    try:
        count_int = int(count)
    except ValueError as e:
        logger.warning("Unexpected item count %s: %s", count, e)

    return count_int


def _get_next_page_url(response):

    # If there is no "Link" header, then there is no next page
    header = None
    if 'Link' in response.headers:
        header = response.headers['Link']
    elif 'link' in response.headers:
        header = response.headers['link']

    if header is None:
        return None

    # Extract the next URL from the Link header.
    next_url = None
    next_url_match = re.search("<([^>]*)>; rel=\"next\"", header)
    if next_url_match is not None:
        next_url = next_url_match.group(1)
    return next_url
