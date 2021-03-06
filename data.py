import logging
import argparse
import unittest
import os
import sys

# Set up logger for the sub-commands to use.
# Note that this setup must occur before the other modules are imported.
# Code stub courtesy of http://stackoverflow.com/questions/7621897/python-logging-module-globally
log_formatter = logging.Formatter(
    fmt="[%(levelname)s] %(asctime)s (%(module)s:%(lineno)d): %(message)s")
log_handler = logging.StreamHandler()
log_handler.setFormatter(log_formatter)
data_logger = logging.getLogger('data')
data_logger.setLevel(logging.DEBUG)
data_logger.addHandler(log_handler)
data_logger.propagate = False

from models import create_tables, init_database, Command  # pylint: disable=wrong-import-position
from migrate import run_migration  # pylint: disable=wrong-import-position

# List out the data processing modules that you've defined in the subdirectories here
from fetch import stack_overflow_posts, tutorial_pdfs  # pylint: disable=wrong-import-position
from fetch import stack_overflow_post_bodies  # pylint: disable=wrong-import-position
from fetch import mendeley_annotations, mendeley_documents  # pylint: disable=wrong-import-position
# from import_ import <module-1>, <module-2>, ...
from compute import stack_overflow_post_links  # pylint: disable=wrong-import-position
from dump import random_posts, stack_overflow_post_links as dump_post_links  # pylint: disable=wrong-import-position

# And then list the imported module under the appropriate subcommands below:
COMMANDS = {
    'fetch': {
        'description': "Fetch data from the web.",
        'module_help': "Type of data to fetch.",
        'modules': [mendeley_annotations, mendeley_documents, stack_overflow_posts,
                    stack_overflow_post_bodies, tutorial_pdfs],
    },
    'import': {
        'description': "Import data from logs.",
        'module_help': "Type of data to import.",
        'modules': [],
    },
    'compute': {
        'description': "Compute derived fields from existing data.",
        'module_help': "Type of data to compute.",
        'modules': [stack_overflow_post_links],
    },
    'migrate': {
        'description':
            "Manage database migrations. (Should only be necessary if you initialized " +
            "your database and then the model files were updated.)",
        'module_help': "Migration operation.",
        'modules': [run_migration],
    },
    'dump': {
        'description': "Dump data to a text file.",
        'module_help': "Type of data to dump.",
        'modules': [random_posts, dump_post_links],
    },
}


def run_tests(*_, **__):
    suite = unittest.defaultTestLoader.discover(os.getcwd())
    unittest.TextTestRunner().run(suite)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Manage data for software packages.")
    subparsers = parser.add_subparsers(help="Sub-commands for managing data", dest='command')

    for command in COMMANDS:

        # Create a parser for each top-level command, with subparsers for each module
        command_spec = COMMANDS[command]
        command_parser = subparsers.add_parser(command, description=command_spec['description'])
        command_subparsers = command_parser.add_subparsers(help=command_spec['module_help'])

        # Initialize arguments for each module of each command
        for module in command_spec['modules']:

            # Create a parser for each low-level module
            module_basename = module.__name__.split('.')[-1]
            module_parser = command_subparsers.add_parser(module_basename)

            # Add default arguments for each fetcher (database configuration)
            module_parser.add_argument(
                '--db',
                default='sqlite',
                help="which type of database to use (postgres, sqlite). Defaults to sqlite."
            )
            module_parser.add_argument(
                '--db-config',
                help="Name of file containing database configuration."
            )

            # Each module defines additional arguments
            module.configure_parser(module_parser)
            module_parser.set_defaults(func=module.main)

    # Add command for running unit tests
    test_parser = subparsers.add_parser('tests', description="Run unit tests.")
    test_parser.set_defaults(func=run_tests)

    # Parse arguments
    args = parser.parse_args()

    # Initialize database
    if args.command != 'tests':
        init_database(args.db, config_filename=args.db_config)
        create_tables()

        # Save a record of this command that we can refer back to later if needed
        Command.create(arguments=str(sys.argv))

    # Invoke the main program that was specified by the submodule
    if args.func is not None:
        args.func(**vars(args))
