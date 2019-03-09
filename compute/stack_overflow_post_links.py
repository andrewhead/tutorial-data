#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import logging
from tqdm import tqdm
from bs4 import BeautifulSoup
from peewee import fn

from models import Post, PostLink


logger = logging.getLogger('data')


def extract_links(fetch_index):

    posts = (
        Post
        .select()
        .where(Post.fetch_index == fetch_index)
        )

    for post in tqdm(posts):
        document = BeautifulSoup(post.body_html, 'html.parser')
        for link in document.find_all('a', href=True):
            PostLink.create(
                post=post,
                url=link['href'],
                anchor_text=link.text
                )


def main(fetch_index, *args, **kwargs):  # pylint: disable=unused-argument
    if fetch_index == -1:
        fetch_index = Post.select(fn.Max(Post.fetch_index)).scalar()
    extract_links(fetch_index)


def configure_parser(parser):
    parser.description = "Extract links from Stack Overflow posts."
    parser.add_argument(
        "--fetch-index",
        type=int,
        default=-1,
        help="Index of fetched posts for which to extract links. Defaults to latest."
        )
