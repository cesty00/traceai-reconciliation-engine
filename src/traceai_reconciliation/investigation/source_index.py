from __future__ import annotations

import os
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Iterator
from zipfile import ZipFile

import pandas as pd
from lxml import etree

from .source_readers import (
    WME_STANDARD_COLUMNS,
    detect_csv_delimiter,
    filter_by_period,
)


def _fingerprint(path: str | Path) -> dict[str, int | str]:
    source = Path(path).resolve()
    stat = source.stat()
    return {
        "path": str(source),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _sqlite_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ")
    if isinstance(value, (str, int, float, bytes)):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def _csv_chunks(
    path: Path,
    chunksize: int = 50000,
) -> Iterator[pd.DataFrame]:
    delimiter = detect_csv_delimiter(path)
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "cp1250", "latin1"):
        try:
            iterator = pd.read_csv(
                path,
                sep=delimiter,
                chunksize=chunksize,
                low_memory=False,
                encoding=encoding,
            )
            for chunk in iterator:
                yield chunk
            return
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error


class SQLiteSourceIndex:
    """
    Local reusable index for the three large operational sources.

    The index is rebuilt atomically whenever path/size/mtime_ns changes for
    WMS, WME or production. RAW files are never modified.
    """

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.db_path = self.cache_dir / "operational_sources.sqlite"

    def _expected_meta(
        self,
        wms_path: str | Path,
        wme_path: str | Path,
        production_path: str | Path,
    ) -> dict[str, dict[str, int | str]]:
        return {
            "wms": _fingerprint(wms_path),
            "wme": _fingerprint(wme_path),
            "production": _fingerprint(production_path),
        }

    def is_current(
        self,
        wms_path: str | Path,
        wme_path: str | Path,
        production_path: str | Path,
    ) -> bool:
        if not self.db_path.exists():
            return False

        expected = self._expected_meta(
            wms_path,
            wme_path,
            production_path,
        )
        try:
            with sqlite3.connect(self.db_path) as connection:
                rows = connection.execute(
                    """
                    SELECT source_key, path, size, mtime_ns
                    FROM _source_meta
                    """
                ).fetchall()
        except sqlite3.Error:
            return False

        current = {
            str(source_key): {
                "path": str(path),
                "size": int(size),
                "mtime_ns": int(mtime_ns),
            }
            for source_key, path, size, mtime_ns in rows
        }
        return current == expected

    def ensure_index(
        self,
        wms_path: str | Path,
        wme_path: str | Path,
        production_path: str | Path,
    ) -> bool:
        """
        Ensure a valid index exists.

        Returns True when a rebuild was performed, False when the existing
        index was reused.
        """
        if self.is_current(wms_path, wme_path, production_path):
            return False

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.db_path.with_suffix(".sqlite.tmp")
        temporary.unlink(missing_ok=True)

        try:
            self._build(
                temporary,
                Path(wms_path),
                Path(wme_path),
                Path(production_path),
            )
            os.replace(temporary, self.db_path)
        finally:
            temporary.unlink(missing_ok=True)
        return True

    def _build(
        self,
        target: Path,
        wms_path: Path,
        wme_path: Path,
        production_path: Path,
    ) -> None:
        with sqlite3.connect(target) as connection:
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            connection.execute("PRAGMA temp_store=MEMORY")

            first = True
            for chunk in _csv_chunks(wms_path):
                chunk.to_sql(
                    "wms",
                    connection,
                    if_exists="replace" if first else "append",
                    index=False,
                )
                first = False
            if first:
                raise ValueError(f"Sursa WMS este goală: {wms_path}")

            first = True
            for chunk in _csv_chunks(production_path):
                chunk.to_sql(
                    "production",
                    connection,
                    if_exists="replace" if first else "append",
                    index=False,
                )
                first = False
            if first:
                raise ValueError(
                    f"Sursa de producție este goală: {production_path}"
                )

            self._build_wme(connection, wme_path)

            wms_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(wms)"
                ).fetchall()
            }
            if "Cod articol" not in wms_columns:
                raise ValueError(
                    "Index WMS: coloana 'Cod articol' lipsește."
                )

            production_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(production)"
                ).fetchall()
            }
            required_production = {
                "PRE_Cod Articol",
                "CON_Cod Articol",
            }
            missing_production = (
                required_production - production_columns
            )
            if missing_production:
                raise ValueError(
                    "Index producție: coloane lipsă "
                    f"{sorted(missing_production)}"
                )

            connection.execute(
                'CREATE INDEX idx_wms_product '
                'ON wms("Cod articol")'
            )
            connection.execute(
                'CREATE INDEX idx_prod_pre '
                'ON production("PRE_Cod Articol")'
            )
            connection.execute(
                'CREATE INDEX idx_prod_con '
                'ON production("CON_Cod Articol")'
            )
            connection.execute(
                "CREATE INDEX idx_wme_product "
                "ON wme(ProductName)"
            )

            connection.execute(
                """
                CREATE TABLE _source_meta (
                    source_key TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime_ns INTEGER NOT NULL
                )
                """
            )
            meta = self._expected_meta(
                wms_path,
                wme_path,
                production_path,
            )
            connection.executemany(
                """
                INSERT INTO _source_meta
                (source_key, path, size, mtime_ns)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        key,
                        value["path"],
                        value["size"],
                        value["mtime_ns"],
                    )
                    for key, value in meta.items()
                ],
            )
            connection.commit()

    def _build_wme(
        self,
        connection: sqlite3.Connection,
        path: Path,
        batch_size: int = 5000,
    ) -> None:
        """
        Stream the first XLSX worksheet directly from XML.

        The WME export is large enough that openpyxl row iteration dominates
        index-build time. Direct XML streaming preserves the same raw values
        while avoiding workbook object creation for hundreds of thousands of
        rows.
        """
        connection.execute(
            """
            CREATE TABLE wme (
                LineNo,
                OperationType,
                Document,
                Date,
                Incoming REAL,
                Outgoing REAL,
                Balance REAL,
                Price REAL,
                Account,
                Partner,
                ProductName,
                CounterWarehouse,
                WMEItemId,
                Warehouse,
                Unit,
                Note,
                InternalRef,
                SignedQuantity REAL
            )
            """
        )

        placeholders = ",".join("?" for _ in WME_STANDARD_COLUMNS)
        insert_sql = (
            "INSERT INTO wme ("
            + ",".join(WME_STANDARD_COLUMNS)
            + ") VALUES ("
            + placeholders
            + ")"
        )

        xml_ns = (
            "{http://schemas.openxmlformats.org/"
            "spreadsheetml/2006/main}"
        )
        column_pattern = re.compile(r"([A-Z]+)")
        accepted_columns = set("ABCDEFGHIJKLMNOPQ")

        def to_float(value: object) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        with ZipFile(path) as archive:
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                root = etree.fromstring(
                    archive.read("xl/sharedStrings.xml")
                )
                shared_strings = [
                    "".join(
                        (node.text or "")
                        for node in item.iter(xml_ns + "t")
                    )
                    for item in root.findall(xml_ns + "si")
                ]

            worksheet_names = sorted(
                name
                for name in archive.namelist()
                if name.startswith("xl/worksheets/sheet")
                and name.endswith(".xml")
            )
            if not worksheet_names:
                raise ValueError(
                    f"Index WME: nu găsesc worksheet XML în {path.name}."
                )

            batch: list[tuple[object, ...]] = []
            with archive.open(worksheet_names[0]) as handle:
                context = etree.iterparse(
                    handle,
                    events=("end",),
                    tag=xml_ns + "row",
                )
                for _, row_element in context:
                    values: dict[str, object] = {}

                    for cell in row_element.findall(xml_ns + "c"):
                        reference = cell.get("r") or ""
                        match = column_pattern.match(reference)
                        if match is None:
                            continue
                        column = match.group(1)
                        if column not in accepted_columns:
                            continue

                        cell_type = cell.get("t")
                        value_node = cell.find(xml_ns + "v")
                        value: object = (
                            value_node.text
                            if value_node is not None
                            else None
                        )

                        if (
                            cell_type == "s"
                            and value is not None
                            and shared_strings
                        ):
                            value = shared_strings[int(value)]
                        elif cell_type == "inlineStr":
                            inline = cell.find(xml_ns + "is")
                            if inline is not None:
                                value = "".join(
                                    (node.text or "")
                                    for node in inline.iter(
                                        xml_ns + "t"
                                    )
                                )

                        values[column] = value

                    product_name = str(
                        values.get("K") or ""
                    ).strip()
                    item_id = str(values.get("M") or "").strip()
                    if product_name and item_id:
                        incoming = to_float(values.get("E"))
                        outgoing = to_float(values.get("F"))

                        record = (
                            values.get("A"),
                            values.get("B"),
                            values.get("C"),
                            values.get("D"),
                            incoming,
                            outgoing,
                            to_float(values.get("G")),
                            to_float(values.get("H")),
                            values.get("I"),
                            values.get("J"),
                            product_name,
                            values.get("L"),
                            item_id,
                            values.get("N"),
                            values.get("O"),
                            values.get("P"),
                            values.get("Q"),
                            incoming - outgoing,
                        )
                        batch.append(
                            tuple(
                                _sqlite_value(value)
                                for value in record
                            )
                        )

                        if len(batch) >= batch_size:
                            connection.executemany(
                                insert_sql,
                                batch,
                            )
                            batch.clear()

                    row_element.clear()
                    parent = row_element.getparent()
                    if parent is not None:
                        while row_element.getprevious() is not None:
                            del parent[0]

                if batch:
                    connection.executemany(insert_sql, batch)

    def read_wms_product(
        self,
        product_code: str,
        period: str | None = None,
    ) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as connection:
            frame = pd.read_sql_query(
                """
                SELECT *
                FROM wms
                WHERE TRIM(CAST("Cod articol" AS TEXT)) = ?
                """,
                connection,
                params=(str(product_code).strip(),),
            )
        if period and not frame.empty:
            frame = filter_by_period(frame, period)
        return frame

    def read_wme_product(
        self,
        product_name: str,
        period: str | None = None,
    ) -> tuple[pd.DataFrame, set[str]]:
        with sqlite3.connect(self.db_path) as connection:
            frame = pd.read_sql_query(
                """
                SELECT *
                FROM wme
                WHERE ProductName = ?
                """,
                connection,
                params=(str(product_name).strip(),),
            )

        ids = {
            str(value).strip()
            for value in frame.get(
                "WMEItemId",
                pd.Series(dtype=object),
            ).dropna()
            if str(value).strip()
        }
        if period and not frame.empty:
            frame = filter_by_period(frame, period)
        return frame, ids

    def read_production_product(
        self,
        product_code: str,
        period: str | None = None,
    ) -> pd.DataFrame:
        code = str(product_code).strip()
        with sqlite3.connect(self.db_path) as connection:
            frame = pd.read_sql_query(
                """
                SELECT *
                FROM production
                WHERE TRIM(CAST("PRE_Cod Articol" AS TEXT)) = ?
                   OR TRIM(CAST("CON_Cod Articol" AS TEXT)) = ?
                """,
                connection,
                params=(code, code),
            )
        if period and not frame.empty:
            frame = filter_by_period(frame, period)
        return frame
