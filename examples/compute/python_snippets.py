#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import logging
# WARNING: progressbar no longer in use for this repository. Replace with tqdm.
from progressbar import ProgressBar, Percentage, Bar, ETA, Counter, RotatingMarker
from bs4 import BeautifulSoup
from peewee import fn
import re
import ast

from models import Post, PostTag, Tag, PostSnippet, SnippetPattern
from compute._scan import NodeScanner


logger = logging.getLogger('data')


def extract_snippets(patterns, tags, compute_index, lines_of_context, show_progress=False):

    # Fetch all posts, filtering by those for which tags have been specified
    posts = Post.select(Post.id, Post.body)
    if tags is not None:
        posts = (
            posts
            .join(PostTag, on=(Post.id == PostTag.post_id))
            .join(Tag, on=(Tag.id == PostTag.tag_id))
            .where(Tag.tag_name << tags)
        )

    # Initialize the progress bar
    if show_progress:
        post_count = posts.count()
        progress_bar = ProgressBar(maxval=post_count, widgets=[
            'Progress: ', Percentage(),
            ' ', Bar(marker=RotatingMarker()),
            ' ', ETA(),
            ' Processing web page ', Counter(), ' / ' + str(post_count) + '.'
        ])
        progress_bar.start()

    # Zip all patterns with a scanner that scans for it
    pattern_scanner_pairs = []
    for pattern in patterns:
        snippet_pattern, _ = SnippetPattern.get_or_create(pattern=pattern)
        extractor = PythonSnippetExtractor(pattern, lines_of_context)
        scanner = NodeScanner(extractor, tags=['pre', 'code'])
        pattern_scanner_pairs.append((snippet_pattern, scanner))

    # For each post, extract snippets for all patterns
    # Note that currently there is some repeated work: each extractor will
    # try to parse all relevant nodes as Python
    for post_index, post in enumerate(posts, start=1):
        document = BeautifulSoup(post.body, 'html.parser')

        for snippet_pattern, scanner in pattern_scanner_pairs:
            snippets = scanner.scan(document)

            # Store a record of each snippet that was found
            for snippet in snippets:
                PostSnippet.create(
                    post=post,
                    snippet=snippet,
                    compute_index=compute_index,
                    pattern=snippet_pattern,
                )

        if show_progress:
            progress_bar.update(post_index)

    if show_progress:
        progress_bar.finish()


class PythonSnippetExtractor(object):
    '''
    Given a BeautifulSoup representation of an HTML node, this returns a list of
    all Python code snippets in that document matching that pattern.
    '''

    def __init__(self, pattern, lines_of_context):
        '''
        pattern: a Python regular expression of code to match.
        lines_of_context: how many lines to save on either side of a line that matches the pattern.
        '''
        self.pattern = pattern
        self.lines_of_context = lines_of_context

    def extract(self, node):

        snippets = []
        content = node.text

        # First, check to see if this is legal Python by trying to parse it
        try:
            ast.parse(content)
        except (SyntaxError, ValueError, MemoryError):
            logger.debug("Code content could not be parsed as Python.")
            return []

        # Check for the pattern on each line
        content_lines = content.splitlines()
        for line_index, line in enumerate(content_lines):

            # If the line matches, save a snippet of the line plus some context
            if re.search(self.pattern, line):
                top_line_index = max(line_index - self.lines_of_context, 0)
                bottom_line_index = min(line_index + self.lines_of_context, len(content_lines) - 1)
                snippet = '\n'.join(content_lines[top_line_index:bottom_line_index + 1])
                snippets.append(snippet)

        return snippets


def main(patterns, tags, lines_of_context, show_progress, *args, **kwargs):

    # Create a new index for this computation
    last_compute_index = PostSnippet.select(fn.Max(PostSnippet.compute_index)).scalar() or 0
    compute_index = last_compute_index + 1

    # Read patterns from a file
    with open(patterns) as patterns_file:
        pattern_list = [p.strip() for p in patterns_file.readlines()]

    # Run snippet extraction
    extract_snippets(pattern_list, tags, compute_index, lines_of_context, show_progress)


def configure_parser(parser):
    parser.description = "Extract Python code snippets from Stack Overflow posts."
    parser.add_argument(
        'patterns',
        help="A file where each line is a Python regular expression specifying lines to extract."
    )
    parser.add_argument(
        '--lines-of-context',
        type=int,
        default=2,
        help="Number of lines of context to save above and below each match (default: %(default)s)."
    )
    parser.add_argument(
        '--tags',
        nargs='+',
        help="Extract snippets only from posts with the specified tags."
    )
    parser.add_argument(
        '--show-progress',
        action='store_true',
        help="Show progress of the number of posts scanned."
    )
