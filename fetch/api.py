#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import requests
import logging
import time
import ConfigParser
import os
import base64
import re


logger = logging.getLogger('data')


USER_AGENT = "Andrew Head (for academic research) <andrewhead@eecs.berekeley.edu>"
default_requests_session = requests.Session()
default_requests_session.headers['User-Agent'] = USER_AGENT
GITHUB_PAGE_SIZE = 100  # the maximum page size for many GitHub queries


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
        logger.warn(
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
            logger.warn("Waiting %d seconds for before retrying.", int(retry_delay))
            time.sleep(retry_delay)
            attempts += 1

    return res


'''
A class for connecting to the GitHub API.
Users mus have their GitHub API credentials stored at ~/.github/github.cfg
'''
github_config = ConfigParser.ConfigParser()
github_config.read(os.path.expanduser(os.path.join('~', '.github', 'github.cfg')))
github_username = github_config.get('auth', 'username')
github_password = github_config.get('auth', 'password')

# Define a unique session for each GitHub API calls, for
# which we can set parameters like the page size.
GITHUB_API_URL = 'https://api.github.com'
GITHUB_DELAY = 1  # Max request rate: 5000 / hour -> (1 request / .72s)
github_session = requests.Session()
github_session.headers['User-Agent'] = USER_AGENT
github_session.headers['Authorization'] =\
    "Basic " + base64.b64encode(github_username + ':' + github_password)
github_session.params = {
    'per_page': GITHUB_PAGE_SIZE
}


def _get_next_page_url(response):

    # If there is no "Link" header, then there is no next page
    if 'Link' not in response.headers:
        return None

    # Extract the next URL from the Link header.
    next_url = None
    next_url_match = re.match("<([^>]*)>; rel=\"next\",", response.headers['Link'])
    if next_url_match is not None:
        next_url = next_url_match.group(1)
    return next_url


def github_get(start_url, results_callback, delay=GITHUB_DELAY, *args, **kwargs):

    # Make the first request to the GitHub API
    response = make_request(github_session.get, start_url, *args, **kwargs)

    # Notify the calling routine via a callback that results have been returned
    if response is not None:
        results_callback(response.json())

        # While there is another page to visit, continue to query the GitHub API
        # until there are no more links to follow.  After each round of results,
        # notify the caller of the partial results from that page.
        next_url = _get_next_page_url(response)
        while response is not None and next_url is not None:
            response = make_request(github_session.get, next_url)
            if response is not None:
                results_callback(response.json())
                next_url = _get_next_page_url(response)
                time.sleep(delay)
