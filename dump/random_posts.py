from __future__ import unicode_literals
import logging

from dump.dump import dump_csv
from models import Post, PostTag
from peewee import fn


RANDOM_RECORD_COUNT = 200
logger = logging.getLogger('data')

@dump_csv(__name__, column_names=[
    'Question ID', 'Creation Date', 'Title', 'Link', 'Score', 'Answer Count', 'Body Markdown',
    'Tag 1', 'Tag 2', 'Tag 3', 'Tag 4', 'Tag 5'
    ], delimiter="\t")
def main(fetch_index, *_, **__):

    if fetch_index == -1:
        fetch_index = Post.select(fn.Max(Post.fetch_index)).scalar()

    posts = (
        Post
        .select()
        .where(Post.fetch_index == fetch_index)
        .order_by(fn.Random())
        .limit(RANDOM_RECORD_COUNT)
        )

    for post in posts:

        record = [
            post.question_id,
            post.creation_date,
            post.title,
            post.link,
            post.score,
            post.answer_count,
            post.body_markdown,
            ]

        post_tags = (
            PostTag
            .select()
            .where(PostTag.post == post)
            )
        for post_tag in post_tags:
            record.append(post_tag.tag_name)

        yield [record]

    raise StopIteration


def configure_parser(parser):
    parser.description = "Dump random subset of Stack Overflow posts."
    parser.add_argument(
        "--fetch-index",
        type=int,
        default=-1,
        help="Index of fetched data to dump from. Defaults to latest."
        )
