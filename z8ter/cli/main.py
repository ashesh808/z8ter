"""Z8ter command-line interface.

Commands:
  - new <project_name>          Create a new Z8ter project scaffold.
  - create_page <name>          Scaffold a page (view, template, content, TS).
  - create_api <name>           Scaffold an API class.
  - run [dev|prod|WAN|LAN]      Run the app (dev enables autoreload).
  - db init                     Initialize database with tables.
  - db reset                    Reset database (destructive).
  - db status                   Show database status.

Notes:
  - The CLI assumes the current working directory is your app root.
  - `z8ter.set_app_dir(Path.cwd())` sets paths used by scaffolding helpers.

"""

import argparse
from pathlib import Path

import z8ter
from z8ter.cli.create import create_api, create_page
from z8ter.cli.database import db_init, db_reset, db_status
from z8ter.cli.new import new_project
from z8ter.cli.run_server import run_server


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser for the Z8ter CLI."""
    parser = argparse.ArgumentParser(prog="z8", description="Z8ter CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # new
    p_new = sub.add_parser("new", help="Create a new Z8ter project")
    p_new.add_argument("project_name", help="Folder name for the new project")

    # create_page
    p_create = sub.add_parser("create_page", help="Create a new page scaffold")
    p_create.add_argument("name", help="Page name (e.g., 'home' or 'app/home')")

    # create_api
    p_api = sub.add_parser("create_api", help="Create a new API scaffold")
    p_api.add_argument("name", help="API name (e.g., 'hello' or 'billing')")

    # run
    p_run = sub.add_parser("run", help="Run the app (default: prod)")
    p_run.add_argument(
        "mode",
        nargs="?",
        choices=["dev", "prod", "WAN", "LAN"],
        default="prod",
        help="Select run mode. Use 'dev' for autoreload.",
    )

    # db subcommands
    p_db = sub.add_parser("db", help="Database management commands")
    db_sub = p_db.add_subparsers(dest="db_cmd", required=True)

    # db init
    p_db_init = db_sub.add_parser("init", help="Initialize database with tables")
    p_db_init.add_argument(
        "--url", help="Database URL (default: DATABASE_URL env or sqlite:///data/app.db)"
    )

    # db reset
    p_db_reset = db_sub.add_parser("reset", help="Reset database (DROP all tables)")
    p_db_reset.add_argument(
        "--url", help="Database URL (default: DATABASE_URL env or sqlite:///data/app.db)"
    )
    p_db_reset.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation prompt"
    )

    # db status
    p_db_status = db_sub.add_parser("status", help="Show database status")
    p_db_status.add_argument(
        "--url", help="Database URL (default: DATABASE_URL env or sqlite:///data/app.db)"
    )

    return parser


def main() -> None:
    """Entry point for the `z8` CLI."""
    z8ter.set_app_dir(Path.cwd())
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "create_page":
        create_page(args.name)
        print("Page created.")
    elif args.cmd == "create_api":
        create_api(args.name)
        print("API created.")
    elif args.cmd == "new":
        new_project(args.project_name)
        print("Project created.")
    elif args.cmd == "run":
        run_server(mode=args.mode)
    elif args.cmd == "db":
        if args.db_cmd == "init":
            db_init(url=args.url)
        elif args.db_cmd == "reset":
            db_reset(url=args.url, force=args.force)
        elif args.db_cmd == "status":
            db_status(url=args.url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
