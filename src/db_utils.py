import time
from contextlib import contextmanager
from pathlib import Path

import duckdb

DB_PATH = "db/marketing.duckdb"
LOCK_PATH = "db/marketing.duckdb.lock"


@contextmanager
def locked_duckdb_connection(read_only: bool = False, timeout_seconds: int = 30):
    import fcntl

    Path("db").mkdir(parents=True, exist_ok=True)
    lock_path = Path(LOCK_PATH)
    lock_path.touch(exist_ok=True)

    with lock_path.open("r+", encoding="utf-8") as lock_file:
        start = time.time()
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() - start >= timeout_seconds:
                    raise TimeoutError(f"DuckDB lock wait timed out after {timeout_seconds} seconds")
                time.sleep(0.2)

        conn = duckdb.connect(DB_PATH, read_only=read_only)
        try:
            yield conn
        finally:
            conn.close()
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
