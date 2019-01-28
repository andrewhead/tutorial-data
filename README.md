# Data Processing Template

Throughout the years, I've worked on many projects with
shared data processing needs:

* It should be easy to write a new data processing script
* The data should be stored in an easy-to-query database
* The data should be easily exportable to CSV
* There should be some record of when I ran certain data
  processing actions, and when I produced derivative CSV
  files. All of this should be by default

The result is this repository, which provides an extensible
starting point for managing Python data processing scripts
and the data that they produce.

## Running commands

First, install the dependencies:

```bash
virtualenv venv -p python3
source venv/bin/activate
pip install -r reqs.txt
```

The main interface to the code is the `data.py` script. The
rest of the commands can be run as subcommands corresponding
to files in the subdirectories. For instance, to run a
`queries.py` script in the `fetch/` directory, run the
following command:

```bash
python data.py fetch queries
```

You can use the `--help` argument for any command to find
out what its arguments are.

By default, data will be stored in a SQLite database called
`data.db`. If you want to change this, use the `--db`
commands. For example, you can save to a PostgreSQL database
using the arguments `--db postgres --db-config postgres-config.json`
where `postgres-config.json` is a file containing your
Postgres credentials. (If you use PostgreSQL, you will also
need to pip install the `psycopg2` package.)

## Data-dump format

Data dumping commands will be of the form:

```
python data.py dump <dump-module-name>
```

This will produce a file `data/dump.<module-name>-<timestamp>`
where `timestamp` is the time that the data was dumped.
These can be produced in CSV, JSON, or text format,
depending on the decorators given to the dump function in
the dump modules.

## Running migrations

You can manage the database tables and changes to them using
migrations with the Peewee migrations API. These can help
you document and automate your changes to the database
schema. This might be particularly helpful if you are
collaborating with someone else.

Migrations should be saved in the `migrations/` directory.
You can see an example migration in the file
`migrations/0000_example_migration.py`. You can run a
migration with the command:

```bash
python data.py migrate run_migration 0000_example_migration
```

To see the available migrations, call
`python data.py migrate run_migration --help`.

## Writing data processing scripts

Examples of different types of data processing scripts can
be found in the `examples/` directory. Below are more
detailed instructions on how to create each type of data
processing script.

### Structure of a fetching or importing module

A module for fetching or importing a specific type of data
should have, at the least:

* A `configure_parser` method that takes in a subcommand
  parser for, and sets the command description and arguments.
* A `main` method that has the signature
  `main(<expected args>, *args, **kwargs)` where
  `<expected args>` are the arguments that you added in
  the `configure_parser` method.

New modules should be added to the appropriate `SUBMODULES`
lists at the top of the `data.py` file.  The `main` method
of a fetching module can optionally be wrapped with the
`lock_method(<filename>)` decorator, which enforces that the
main method is only invoked once at a time.

### Writing a migration

If you update a model, it might be a courtesy to write a
migration script that will apply to existing databases to
bring them up to date.

Migrations are easy to write.  First, create a Python module
in the `migrate` directory.  Its file name should start with
a four-digit index after the index of the last-written
migration (e.g., `0007` if the last migration started with
`0006`).

Then, write the forward migration procedure.  You do this by
instantiating a single method called `forward`, that takes a
`migrator` as its only argument.  Call Peewee `migrate`
methods on this object to transform the database.  For a
list of available migration methods, see the [Peewee
docs](http://docs.peewee-orm.com/en/latest/peewee/playhouse.html#schema-migrations).
This should only take a few lines of code.

Only forward migrations are supported with the current code.

### Writing a data dump module

To add a script for dumping a certain type of data, decorate
the `main` function of your module with `dump_json` from the
`dump` module.  This decorator takes one argument: the
basename of a file to save in the `data/` directory.  The
`main` should do some queries to the database, and `yield`
lists of records that will be saved as JSON.

### Logging messages

Every file you write should include this line after the
imports and before any logic:

    logger = logging.getLogger('data')

All logging should be performed through `logger`, instead of
using the `logging` module directly.  Sticking to this
convention lets us configure logging globally without
touching any other loggers.

### Writing and running tests

As you develop, you may want to write tests. If so, you
can write them in `tests` directory. Tests in this directory
will be run automatically with this command:

```bash
python data.py tests
```
