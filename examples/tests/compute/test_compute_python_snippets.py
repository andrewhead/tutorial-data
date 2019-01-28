#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import logging

from tests.base import TestCase
from tests.modelfactory import create_post, create_tag
from compute.python_snippets import extract_snippets
from models import Post, PostSnippet, PostTag, Tag, SnippetPattern


logger = logging.getLogger('data')


class ExtractPythonSnippetsTest(TestCase):

    def __init__(self, *args, **kwargs):
        super(ExtractPythonSnippetsTest, self).__init__(
            [Post, PostSnippet, PostTag, Tag, SnippetPattern],
            *args, **kwargs
        )

    def _extract(self, patterns, tags=None, lines_of_context=2):
        extract_snippets(patterns, tags, 0, lines_of_context)

    def _make_post_body(self, code):
        return '\n'.join([
            '<div>',
            '  <pre>',
            '    <code>' + code + '</code>',
            '  </pre>',
            '</div>',
        ])

    def test_skip_nonpython_code(self):
        create_post(body=self._make_post_body('\n'.join([
            'var $ = require("jquery")',
            '$("div").text("div text")',
            'var ranomString = "re.match";',
        ])), view_count=375)
        self._extract(['re.match'])
        self.assertEqual(PostSnippet.select().count(), 0)

    def test_find_snippet(self):

        # First, we create the models in memory
        post = create_post(body=self._make_post_body('\n'.join([
            'import re',
            '',
            'string = "foo"',
            'characters = re.findall(r"\w", string)',
            '',
            'for c in characters:',
            '    print c',
        ])))

        # Here is the line of code that actually performs the extraction for a pattern
        # By default, it should run extraction for all posts
        self._extract(['re.findall'])

        # There are a few effects that we check
        # First, that the number of snippets has increased
        self.assertEqual(PostSnippet.select().count(), 1)

        # The content of this snippet should show context around the pattern
        self.assertEqual(PostSnippet.select().first().snippet, '\n'.join([
            '',
            'string = "foo"',
            'characters = re.findall(r"\w", string)',
            '',
            'for c in characters:',
        ]))

        # The snippet should link back to the post that it was create from
        self.assertEqual(PostSnippet.select().first().post, post)

        # A model for the pattern should have been created
        self.assertEqual(SnippetPattern.select().count(), 1)
        self.assertEqual(SnippetPattern.select().first().pattern, 're.findall')

        # The snippet should be linked back to the pattern
        self.assertEqual(SnippetPattern.select().first(), PostSnippet.select().first().pattern)

    def test_find_snippet_with_tags(self):

        # These two posts are equivalent, except that only is tagged with a tag that we
        # will use for filtering in the test.
        post1 = create_post(body=self._make_post_body('\n'.join([
            'import re',
            'characters = re.findall(r"\w", "foo")',
            'for c in characters:',
            '    print c',
        ])))
        post2 = create_post(body=self._make_post_body('\n'.join([
            'import re',
            'characters = re.findall(r"\w", "foo")',
            'for c in characters:',
            '    print c',
        ])))
        tag1 = create_tag(tag_name='javascript')
        tag2 = create_tag(tag_name='python')
        PostTag.create(post_id=post1.id, tag_id=tag1.id)
        PostTag.create(post_id=post2.id, tag_id=tag2.id)

        self._extract(['re.findall'], tags=['python'])
        self.assertEqual(PostSnippet.select().count(), 1)
        self.assertEqual(PostSnippet.select().first().post, post2)

    def test_find_snippets_for_multiple_patterns(self):
        create_post(body=self._make_post_body('\n'.join([
            'import re',
            '',
            'string = "foo"',
            'characters = re.findall(r"\w", string)',
            '',
            'for c in characters:',
            '    print c',
        ])))
        self._extract(['re.findall', '"foo"'])
        self.assertEqual(PostSnippet.select().count(), 2)
        snippets = [s.snippet for s in PostSnippet.select()]
        patterns = [s.pattern.pattern for s in PostSnippet.select()]
        self.assertIn('\n'.join([
            '',
            'string = "foo"',
            'characters = re.findall(r"\w", string)',
            '',
            'for c in characters:',
        ]), snippets)
        self.assertIn('\n'.join([
            'import re',
            '',
            'string = "foo"',
            'characters = re.findall(r"\w", string)',
            '',
        ]), snippets)
        self.assertIn('re.findall', patterns)
        self.assertIn('"foo"', patterns)

    def test_specify_lines_of_context(self):
        create_post(body=self._make_post_body('\n'.join([
            'import re',
            '',
            'string = "foo"',
            'characters = re.findall(r"\w", string)',
            '',
            'for c in characters:',
            '    print c',
        ])))
        self._extract(['re.findall'], lines_of_context=1)
        self.assertEqual(PostSnippet.select().first().snippet, '\n'.join([
            'string = "foo"',
            'characters = re.findall(r"\w", string)',
            '',
        ]))

    def test_find_multiple_snippets_in_one_post(self):
        create_post(body=self._make_post_body('\n'.join([
            'import re',
            '',
            'string = "foo"',
            'characters = re.findall(r"\w", string)',
            'for c in characters:',
            '    print c',
            '',
            'digits = re.findall(r"\w", string)',
            'for d in digits:',
            '    print d',
        ])))
        self._extract(['re.findall'])
        self.assertEqual(PostSnippet.select().count(), 2)
        snippets = [code.snippet for code in PostSnippet.select()]
        self.assertIn('\n'.join([
            '',
            'string = "foo"',
            'characters = re.findall(r"\w", string)',
            'for c in characters:',
            '    print c',
        ]), snippets)
        self.assertIn('\n'.join([
            '    print c',
            '',
            'digits = re.findall(r"\w", string)',
            'for d in digits:',
            '    print d',
        ]), snippets)

    def test_handle_missing_pre_context(self):
        # If there is no context available in the lines above the one where a pattern is found,
        # make sure that the extraction is still successful.
        create_post(body=self._make_post_body('\n'.join([
            'characters = re.findall(r"\w", string)',
            '',
            'for c in characters:',
            '    print c',
        ])))
        self._extract(['re.findall'])
        self.assertEqual(PostSnippet.select().first().snippet, '\n'.join([
            'characters = re.findall(r"\w", string)',
            '',
            'for c in characters:',
        ]))

    def test_handle_missing_post_context(self):
        # If there is no context available in the lines below the one where a pattern is found,
        # make sure that the extraction is still successful.
        create_post(body=self._make_post_body('\n'.join([
            'import re',
            '',
            'characters = re.findall(r"\w", string)',
        ])))
        self._extract(['re.findall'])
        self.assertEqual(PostSnippet.select().first().snippet, '\n'.join([
            'import re',
            '',
            'characters = re.findall(r"\w", string)',
        ]))

    def test_skip_non_code_nodes_plaintext(self):
        create_post(body='<p>re.findall</p>')
        self._extract(['re.findall'])
        self.assertEqual(PostSnippet.select().count(), 0)
