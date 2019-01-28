#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import logging
# WARNING: progressbar no longer in use for this repository. Replace with tqdm.
from progressbar import ProgressBar, Percentage, Bar, ETA, Counter, RotatingMarker

from dump import dump_json
from models import Post, Tag, PostTag


logger = logging.getLogger('data')
PACKAGES = [
    "express",
    "gulp",
    "async.js",
    "node-request",
    "lodash",
    "browserify",
    "gruntjs",
    "pm2",
    "socket.io",
    "node-commander",
    "mongoose",
    "mocha",
    "forever",
    "bower",
    "momentjs",
    "underscore.js",
    "chalk",
    "q",
    "gulp-uglify",
    "cheerio",
    "npm",
    "passport.js",
    "hapijs",
    "nodemailer",
    "bluebird",
    "gulp-concat",
    "node-redis",
    "coffeescript",
    "gulp-sass",
    "karma-runner",
    "reactjs",
    "jade",
    "node-mysql",
    "nodemon",
]


@dump_json(__name__)
def main(show_progress, *args, **kwargs):

    # Set up progress bar.
    if show_progress:
        progress_bar = ProgressBar(maxval=len(PACKAGES), widgets=[
            'Progress: ', Percentage(),
            ' ', Bar(marker=RotatingMarker()),
            ' ', ETA(),
            ' Fetched posts for ', Counter(), ' / ' + str(len(PACKAGES)) + ' packages.'
        ])
        progress_bar.start()

    # Fetch statistics for posts related to each tag
    for package_count, package in enumerate(PACKAGES, start=1):

        records = (
            Tag.select()
            .join(PostTag, on=(Tag.id == PostTag.tag_id))
            .join(Post, on=(Post.id == PostTag.post_id))
            .where(Tag.tag_name == package)
            .select(Tag.tag_name, Post.title, Post.creation_date, Post.answer_count,
                    Post.comment_count, Post.favorite_count, Post.score, Post.view_count)
            .dicts()
        )
        yield records

        if show_progress:
            progress_bar.update(package_count)

    if show_progress:
        progress_bar.finish()

    raise StopIteration


def configure_parser(parser):
    parser.description = "Dump count statistics for frequently used Node packages."
    parser.add_argument(
        '--show-progress',
        action='store_true',
        help="Show progress in loading content from the file."
    )
