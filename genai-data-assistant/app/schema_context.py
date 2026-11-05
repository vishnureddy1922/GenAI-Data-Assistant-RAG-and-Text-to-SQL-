"""Describe the warehouse schema to the model (tables, columns, types, comments)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Engine, text

COLUMNS_SQL = text(
    """
    select c.table_name, c.column_name, c.data_type,
           col_description(format('%I.%I', c.table_schema, c.table_name)::regclass, c.ordinal_position) as comment,
           obj_description(format('%I.%I', c.table_schema, c.table_name)::regclass, 'pg_class') as table_comment
    from information_schema.columns c
    where c.table_schema = :schema
    order by c.table_name, c.ordinal_position
    """
)


@dataclass
class TableInfo:
    name: str
    comment: str | None = None
    columns: list[tuple[str, str, str | None]] = field(default_factory=list)


@dataclass
class SchemaContext:
    schema: str
    tables: dict[str, TableInfo]

    @property
    def allowed_tables(self) -> set[str]:
        return {f"{self.schema}.{t}" for t in self.tables}

    def to_prompt(self) -> str:
        lines = []
        for t in self.tables.values():
            header = f"TABLE {self.schema}.{t.name}"
            if t.comment:
                header += f"  -- {t.comment}"
            lines.append(header)
            for col, dtype, comment in t.columns:
                lines.append(f"  {col} {dtype}" + (f"  -- {comment}" if comment else ""))
            lines.append("")
        return "\n".join(lines).strip()

    @classmethod
    def from_database(cls, engine: Engine, schema: str) -> SchemaContext:
        tables: dict[str, TableInfo] = {}
        with engine.connect() as conn:
            for row in conn.execute(COLUMNS_SQL, {"schema": schema}):
                info = tables.setdefault(row.table_name, TableInfo(row.table_name, row.table_comment))
                info.columns.append((row.column_name, row.data_type, row.comment))
        if not tables:
            raise RuntimeError(f"No tables found in schema '{schema}'. Did the init SQL run?")
        return cls(schema=schema, tables=tables)
