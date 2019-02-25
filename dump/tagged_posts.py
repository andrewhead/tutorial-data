from __future__ import unicode_literals
import logging

from dump.dump import dump_csv
from models import Post, PostTag
from peewee import fn


logger = logging.getLogger('data')

@dump_csv(__name__, column_names=[
    'Question ID', 'Link', 'Title', 'Creation Date', 'Score', 'Answer Count', 'Tag'
    ], delimiter="\t")
def main(fetch_index, *_, **__):

    if fetch_index == -1:
        fetch_index = Post.select(fn.Max(Post.fetch_index)).scalar()

    posts = (
        Post
        .select()
        .where(Post.fetch_index == fetch_index)
        .order_by(fn.Random())
        )

    for post in posts:

        post_records = []
        base_post_record = [
            post.question_id,
            post.link,
            post.title,
            post.creation_date,
            post.score,
            post.answer_count,
            ]

        post_tags = (
            PostTag
            .select()
            .where(PostTag.post == post)
            )
        for post_tag in post_tags:
            tagged_post_record = base_post_record + [post_tag.tag_name]
            post_records.append(tagged_post_record)

        yield post_records


def configure_parser(parser):
    parser.description = "Dump all Stack Overflow posts with one line per tag."
    parser.add_argument(
        "--fetch-index",
        type=int,
        default=-1,
        help="Index of fetched data to dump from. Defaults to latest."
        )
