"""Dev-only DB helpers: table counts, recent runs. Gate destructive ops behind env."""
import os
import sys

from sqlalchemy import select, func, text

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.config import DBConfig
from app.db.engine import create_engine_from_config
from app.db.base import Base
import app.db.models  # noqa: F401


def table_counts(engine) -> dict[str, int]:
    """Return row count per table (for dev inspection)."""
    counts = {}
    for table in Base.metadata.sorted_tables:
        (n,) = engine.connect().execute(select(func.count()).select_from(table)).fetchone()
        counts[table.name] = n
    return counts


def print_table_counts(db_url: str | None = None) -> None:
    """Print table counts. Uses DB_URL env or default sqlite path."""
    url = db_url or os.environ.get("DB_URL") or "sqlite:///./data/app.db"
    cfg = DBConfig(db_url=url)
    engine = create_engine_from_config(cfg)
    for name, n in table_counts(engine).items():
        print(f"  {name}: {n}")
    engine.dispose()


def print_recent_runs(db_url: str | None = None, limit: int = 5) -> None:
    """Print recent runs (id, workspace_id, run_type, status, started_at)."""
    from app.db.models.run import Run
    url = db_url or os.environ.get("DB_URL") or "sqlite:///./data/app.db"
    cfg = DBConfig(db_url=url)
    engine = create_engine_from_config(cfg)
    with engine.connect() as conn:
        rows = conn.execute(
            select(Run.id, Run.workspace_id, Run.run_type, Run.status, Run.started_at)
            .order_by(Run.started_at.desc())
            .limit(limit)
        ).fetchall()
    for r in rows:
        print(f"  {r.id} | {r.workspace_id} | {r.run_type} | {r.status} | {r.started_at}")
    engine.dispose()


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="DB dev tools")
    p.add_argument("--counts", action="store_true", help="Print table row counts")
    p.add_argument("--runs", type=int, nargs="?", const=5, metavar="N", help="Print N recent runs")
    p.add_argument("--db-url", default=None, help="Database URL (default: env DB_URL or sqlite:///./data/app.db)")
    args = p.parse_args()
    if args.counts:
        print("Table counts:")
        print_table_counts(args.db_url)
    if args.runs is not None:
        print(f"Recent runs (limit={args.runs}):")
        print_recent_runs(args.db_url, limit=args.runs)
    if not args.counts and args.runs is None:
        p.print_help()


if __name__ == "__main__":
    main()
