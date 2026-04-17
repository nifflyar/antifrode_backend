"""ML-ready Excel parser with data cleaning and normalization."""
import re
import hashlib
from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np


class MLExcelParser:
    """Parse and normalize Excel transaction data for ML pipeline."""

    # Column mapping: (original_name_pattern, normalized_name, parser_func)
    COLUMN_MAPPINGS = {
        "ticket_no": (r"номер.*билета", "ticket_no"),
        "order_no": (r"номер.*заказа", "order_no"),
        "operation": (r"операция", "operation"),
        "price": (r"цена|тариф", "price"),
        "fees": (r"(сбор|комиссия)", "fees"),
        "op_datetime": (r"дата.*операции|время.*операции", "op_datetime"),
        "dep_datetime": (r"дата.*отправи|дата.*рейса", "dep_datetime"),
        "train_no": (r"номер.*поезда|рейс", "train_no"),
        "channel": (r"канал|точка продажи", "channel"),
        "aggregator": (r"агрегатор", "aggregator"),
        "terminal": (r"терминал", "terminal"),
        "point_of_sale": (r"место продажи", "point_of_sale"),
        "passenger_fio": (r"ф\.и\.о|фио|фамилия", "passenger_fio"),
        "passenger_iin": (r"ии[нн]|идентификацион", "passenger_iin"),
        "passenger_doc": (r"документ|паспорт|№.*документа", "passenger_doc"),
        "passenger_phone": (r"телефон|номер.*телефона", "passenger_phone"),
        "station_from": (r"станция.*отправ|откуда", "station_from"),
        "station_to": (r"станция.*назначен|куда", "station_to"),
    }

    def __init__(self):
        self.parsed_df = None
        self.parsing_stats = {}

    def normalize_text(self, x: str | None) -> Optional[str]:
        """Normalize text: strip, lowercase, deduplicate spaces."""
        if pd.isna(x) or x is None:
            return None
        s = str(x).strip()
        s = re.sub(r"\s+", " ", s)  # normalize spaces
        return s if s else None

    def parse_money(self, series: pd.Series) -> pd.Series:
        """Parse money: handle spaces, commas, remove non-numeric."""
        s = series.astype(str)
        s = s.str.replace("\u00a0", "", regex=False)  # nbsp
        s = s.str.replace(" ", "", regex=False)
        s = s.str.replace(",", ".", regex=False)
        s = s.str.replace(r"[^0-9\.\-]", "", regex=True)
        return pd.to_numeric(s, errors="coerce")

    def parse_datetime(self, series: pd.Series) -> pd.Series:
        """Parse datetime with day-first format (DD.MM.YYYY)."""
        return pd.to_datetime(series, errors="coerce", dayfirst=True)

    def detect_operation_type(self, row: dict) -> str:
        """Infer operation type from row data."""
        op_raw = str(row.get("operation", "")).lower().strip()

        # Explicit mapping
        if any(x in op_raw for x in ["возврат", "refund", "return"]):
            return "refund"
        if any(x in op_raw for x in ["продажа", "sale", "продаж", "покупка"]):
            return "sale"
        if any(x in op_raw for x in ["выкуп", "redeem", "redemption"]):
            return "redeem"

        return "other"

    def build_passenger_key(self, row: dict) -> Optional[str]:
        """Build passenger identification key with priority order."""
        # Priority: doc -> iin -> (fio + phone) -> fio -> phone
        candidates = [
            ("doc", row.get("passenger_doc")),
            ("iin", row.get("passenger_iin")),
            ("fio_phone", f"{row.get('passenger_fio')}|{row.get('passenger_phone')}"
             if row.get("passenger_fio") and row.get("passenger_phone") else None),
            ("fio", row.get("passenger_fio")),
            ("phone", row.get("passenger_phone")),
        ]

        for key_type, value in candidates:
            if pd.notna(value) and value:
                return f"{key_type}:{value}"

        return None

    def hash_passenger_id(self, key: str) -> str:
        """Create deterministic 12-char hash for passenger."""
        if pd.isna(key) or not key:
            return None
        return hashlib.sha1(str(key).encode("utf-8")).hexdigest()[:12]

    def find_header_row(self, raw: pd.DataFrame, max_rows: int = 50) -> int:
        """Detect header row by looking for key column names."""
        key_cols = ["номер", "операция", "цена", "дата"]

        for i in range(min(max_rows, len(raw))):
            row = raw.iloc[i].astype(str).fillna("").str.lower()
            hits = sum(
                any(k in str(cell).lower() for cell in row.values)
                for k in key_cols
            )
            if hits >= 2:
                return i

        return 0

    def map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map raw Excel columns to normalized column names."""
        col_mapping = {}
        df_cols_lower = [c.lower() for c in df.columns]

        for key, pattern in [
            ("ticket_no", self.COLUMN_MAPPINGS["ticket_no"]),
            ("order_no", self.COLUMN_MAPPINGS["order_no"]),
            ("operation", self.COLUMN_MAPPINGS["operation"]),
            ("price", self.COLUMN_MAPPINGS["price"]),
            ("fees", self.COLUMN_MAPPINGS["fees"]),
            ("op_datetime", self.COLUMN_MAPPINGS["op_datetime"]),
            ("dep_datetime", self.COLUMN_MAPPINGS["dep_datetime"]),
            ("train_no", self.COLUMN_MAPPINGS["train_no"]),
            ("channel", self.COLUMN_MAPPINGS["channel"]),
            ("aggregator", self.COLUMN_MAPPINGS["aggregator"]),
            ("terminal", self.COLUMN_MAPPINGS["terminal"]),
            ("point_of_sale", self.COLUMN_MAPPINGS["point_of_sale"]),
            ("passenger_fio", self.COLUMN_MAPPINGS["passenger_fio"]),
            ("passenger_iin", self.COLUMN_MAPPINGS["passenger_iin"]),
            ("passenger_doc", self.COLUMN_MAPPINGS["passenger_doc"]),
            ("passenger_phone", self.COLUMN_MAPPINGS["passenger_phone"]),
            ("station_from", self.COLUMN_MAPPINGS["station_from"]),
            ("station_to", self.COLUMN_MAPPINGS["station_to"]),
        ]:
            pattern_re = pattern[0]
            for col in df.columns:
                if re.search(pattern_re, col.lower()):
                    col_mapping[col] = key
                    break

        df = df.rename(columns=col_mapping)
        return df

    def parse_excel(self, file_path: Path, sheet_name: int = 0) -> pd.DataFrame:
        """Parse Excel file and return normalized ML-ready DataFrame."""
        # 1. Read with dynamic header detection
        raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, dtype=str)
        header_row = self.find_header_row(raw)

        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row, dtype=str)

        # 2. Remove unnamed columns and empty rows
        df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
        df = df.dropna(how="all").reset_index(drop=True)

        # 3. Map columns to normalized names
        df = self.map_columns(df)

        # 4. Normalize text fields
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].apply(self.normalize_text)

        # 5. Parse numeric fields
        if "price" in df.columns:
            df["price"] = self.parse_money(df["price"])
        if "fees" in df.columns:
            df["fees"] = self.parse_money(df["fees"])

        # 6. Parse datetime fields
        if "op_datetime" in df.columns:
            df["op_datetime"] = self.parse_datetime(df["op_datetime"])
        if "dep_datetime" in df.columns:
            df["dep_datetime"] = self.parse_datetime(df["dep_datetime"])

        # 7. Infer operation type
        df["operation_type"] = df.apply(self.detect_operation_type, axis=1)

        # 8. Create passenger identifiers
        df["passenger_key"] = df.apply(self.build_passenger_key, axis=1)
        df["passenger_id_hash"] = df["passenger_key"].apply(self.hash_passenger_id)

        # 9. Derived fields
        if "station_from" in df.columns and "station_to" in df.columns:
            df["route"] = (
                df["station_from"].fillna("") + " → " + df["station_to"].fillna("")
            )
            df.loc[df["route"].str.replace("→", "").str.strip().eq(""), "route"] = np.nan

        if "op_datetime" in df.columns:
            df["op_date"] = df["op_datetime"].dt.date
            df["op_hour"] = df["op_datetime"].dt.hour

        if "price" in df.columns:
            fees = df["fees"].fillna(0) if "fees" in df.columns else 0
            df["total_amount"] = df["price"].fillna(0) + fees

        # 10. Stats
        self.parsing_stats = {
            "rows": len(df),
            "columns": df.shape[1],
            "unique_passengers": df["passenger_id_hash"].nunique(dropna=True),
            "missing_passenger_share": float(df["passenger_id_hash"].isna().mean()),
            "operations_by_type": df["operation_type"].value_counts().to_dict(),
        }

        self.parsed_df = df
        return df

    def get_stats(self) -> dict:
        """Return parsing statistics."""
        return self.parsing_stats
