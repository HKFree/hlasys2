import sqlite3
import click

from flask import current_app, g, Flask


def init_app(app: Flask):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(fill_db_example_command)
    app.cli.add_command(backfill_names_command)


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
            check_same_thread=False,
        )
        g.db.row_factory = dict_factory

    return g.db


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()

    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))


def fill_db_example():
    db = get_db()

    with current_app.open_resource("../example_data/better_example_data.sql") as f:
        db.executescript(f.read().decode("utf8"))


@click.command("init-db")
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo("Initialized the database.")


def backfill_names(apply: bool) -> dict:
    """
    Rewrite stored author names to "<real name> - <nick>".

    New rows get the nick from SSO (given_name); old rows only have the real
    name. The nick is taken from the proposal's own deciders snapshot, falling
    back to the newest snapshot that contains the user. Rows whose author is in
    no snapshot, and the system user 0, are left alone.

    Returns:
        dict: {(table, old_name, new_name): row_count} of planned changes.
    """
    import json
    from .util import display_name

    db = get_db()
    proposals = db.execute("SELECT id, deciders FROM proposal ORDER BY id").fetchall()
    snapshots = {p["id"]: json.loads(p["deciders"]) for p in proposals}
    newest_nick = {}
    for deciders in snapshots.values():
        newest_nick.update(deciders)

    def new_name(author_id, old, proposal_id):
        nick = snapshots.get(proposal_id, {}).get(str(author_id)) or newest_nick.get(str(author_id))
        if not nick or old.endswith(f" - {nick}"):
            return None
        name = display_name(old, nick)
        return name if name != old else None

    changes = {}
    sources = (
        ("event", "SELECT id, author_id, author_name, proposal_id FROM event WHERE author_id != 0"),
        ("proposal", "SELECT id, author_id, author_name, id AS proposal_id FROM proposal"),
    )
    for table, sql in sources:
        for row in db.execute(sql).fetchall():
            name = new_name(row["author_id"], row["author_name"], row["proposal_id"])
            if name is None:
                continue
            key = (table, row["author_name"], name)
            changes[key] = changes.get(key, 0) + 1
            if apply:
                db.execute(
                    f"UPDATE {table} SET author_name = :name WHERE id = :id",
                    {"name": name, "id": row["id"]},
                )
    if apply:
        db.commit()
    return changes


@click.command("backfill-names")
@click.option("--apply", is_flag=True, help="Write the changes. Without it, only list them.")
def backfill_names_command(apply):
    """Add nicks to stored author names ("<real name> - <nick>")."""
    changes = backfill_names(apply)
    for (table, old, new), count in sorted(changes.items()):
        click.echo(f"{table:9} {count:5}x  {old!r} -> {new!r}")
    total = sum(changes.values())
    if apply:
        click.echo(f"Updated {total} rows.")
    else:
        click.echo(f"{total} rows would change. Run again with --apply to write them.")


@click.command("fill-db")
def fill_db_example_command():
    """Fill the databse with example data."""
    fill_db_example()
    click.echo(
        "Filled the db with example data. You can no try running the webserver with 'flask run'"
    )
