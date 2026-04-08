from sqlalchemy import text


def run_sqlite_safe_migrations(engine) -> None:
    """
    Añade columnas nuevas a la tabla events si todavía no existen.
    Enfocado a una migración simple y segura para desarrollo.
    """
    with engine.begin() as conn:
        result = conn.execute(text("PRAGMA table_info(events)"))
        existing_columns = {row[1] for row in result.fetchall()}

        columns_to_add = [
            ("source", "ALTER TABLE events ADD COLUMN source TEXT"),
            ("external_id", "ALTER TABLE events ADD COLUMN external_id TEXT"),
            ("commence_time", "ALTER TABLE events ADD COLUMN commence_time DATETIME"),
            ("home_team", "ALTER TABLE events ADD COLUMN home_team TEXT"),
            ("away_team", "ALTER TABLE events ADD COLUMN away_team TEXT"),
        ]

        for column_name, sql in columns_to_add:
            if column_name not in existing_columns:
                conn.execute(text(sql))