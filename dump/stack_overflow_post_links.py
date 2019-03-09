from __future__ import unicode_literals
import logging

from dump.dump import dump_csv
from models import Post, PostTag, PostLink
from peewee import fn


logger = logging.getLogger('data')

@dump_csv(__name__, column_names=[
    'Post ID', 'Link to Post', 'Title', 'Creation Date', 'Score', 'Is Accepted', 'Tags',
    'Outgoing Link', 'Outgoing Link Anchor'], delimiter="\t")
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
            post.post_id,
            'https://stackoverflow.com/a/' + str(post.post_id),
            post.title,
            post.creation_date,
            post.score,
            post.is_accepted,
            ]

        post_tags = (
            PostTag
            .select()
            .where(PostTag.post == post)
            )
        tags = "".join(["<" + pt.tag_name + ">" for pt in post_tags])
        base_post_record.append(tags)

        post_links = (
            PostLink
            .select()
            .where(PostLink.post == post)
            )
        for post_link in post_links:
            post_record_with_links = base_post_record + [post_link.url, post_link.anchor_text]
            post_records.append(post_record_with_links)

        yield post_records


def configure_parser(parser):
    parser.description = "Dump all Stack Overflow posts with one line per tag."
    parser.add_argument(
        "--fetch-index",
        type=int,
        default=-1,
        help="Index of fetched data to dump from. Defaults to latest."
        )
