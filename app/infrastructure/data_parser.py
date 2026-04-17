"""Data parser for transaction scoring - inspired by production Excel processing scripts."""
import re
import logging
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Text and data normalization utilities."""

    @staticmethod
    def normalize_text(x: Any) -> Optional[str]:
        """
        Normalize text: trim, collapse whitespace, handle NaN.

        Args:
            x: Input value (any type)

        Returns:
            Normalized string or None if NaN
        """
        if pd.isna(x):
            return None
        s = str(x).strip()
        s = re.sub(r"\s+", " ", s)
        return s if s else None

    @staticmethod
    def parse_money(series: pd.Series) -> pd.Series:
        """
        Parse money values: remove currency symbols, convert to float.

        Handles:
        - Non-breaking spaces and regular spaces
        - Comma/period decimal separators
        - Currency symbols and letters

        Args:
            series: Series with money values (strings or numbers)

        Returns:
            Numeric series with NaN for unparseable values
        """
        s = series.astype(str)
        # Remove non-breaking space and spaces
        s = s.str.replace("\u00a0", " ", regex=False).str.replace(" ", "", regex=False)
        # Normalize decimal separators
        s = s.str.replace(",", ".", regex=False)
        # Remove currency symbols and letters
        s = s.str.replace(r"[^0-9\.\-]", "", regex=True)
        return pd.to_numeric(s, errors="coerce")

    @staticmethod
    def parse_datetime(series: pd.Series, dayfirst: bool = True) -> pd.Series:
        """
        Parse datetime values with flexible format detection.

        Args:
            series: Series with datetime values
            dayfirst: Interpret ambiguous dates as day first (default: True for Russian dates)

        Returns:
            Datetime series with NaT for unparseable values
        """
        return pd.to_datetime(series, errors="coerce", dayfirst=dayfirst)

    @staticmethod
    def normalize_columns(columns) -> List[str]:
        """Normalize column names: trim, collapse spaces, lowercase."""
        return [DataNormalizer.normalize_text(c).lower() if DataNormalizer.normalize_text(c) else c
                for c in columns]


class ColumnMatcher:
    """Match and alias column names flexibly."""

    # Map of canonical names to possible variants
    COLUMN_ALIASES = {
        "ticket_no": ["номер билета", "ticket_no", "ticket number", "ticket"],
        "order_no": ["номер заказа", "order_no", "order number", "order"],
        "passenger_id": ["пассажир_id", "passenger_id", "пассажир id"],
        "fio": ["ф.и.о. пассажира", "фио", "fio", "name", "полное имя"],
        "phone": ["номер телефона", "phone", "телефон"],
        "op_type": ["операция", "op_type", "operation", "тип операции"],
        "op_datetime": ["дата операции", "op_datetime", "operation date", "время операции"],
        "dep_datetime": ["дата/время отправки", "dep_datetime", "departure", "departure time"],
        "dep_station": ["станция отправления", "dep_station", "departure station"],
        "arr_station": ["станция назначения", "arr_station", "arrival station"],
        "price": ["цена", "price", "стоимость"],
        "fees": ["разные сборы", "fees", "commissions", "сборы"],
        "source": ["источник", "source"],
    }

    @staticmethod
    def find_canonical_name(col_name: str) -> Optional[str]:
        """Find canonical name for a column."""
        col_normalized = col_name.lower().strip()

        for canonical, aliases in ColumnMatcher.COLUMN_ALIASES.items():
            for alias in aliases:
                if col_normalized == alias.lower():
                    return canonical

        return None

    @staticmethod
    def auto_match_columns(df: pd.DataFrame) -> Dict[str, str]:
        """
        Auto-match columns using fuzzy logic.

        Args:
            df: DataFrame with unknown column names

        Returns:
            Dict mapping DataFrame column names to canonical names
        """
        mapping = {}
        for col in df.columns:
            canonical = ColumnMatcher.find_canonical_name(col)
            if canonical:
                mapping[col] = canonical
        return mapping


class TransactionDataParser:
    """Parse and validate transaction data from various sources."""

    REQUIRED_FIELDS = {
        "ticket_no": str,
        "passenger_id": (int, float),
        "op_type": str,
        "op_datetime": "datetime",
        "fio": str,
    }

    OPTIONAL_FIELDS = {
        "order_no": str,
        "phone": str,
        "dep_datetime": "datetime",
        "dep_station": str,
        "arr_station": str,
        "price": float,
        "fees": float,
        "source": str,
    }

    @classmethod
    def parse_dataframe(cls, df: pd.DataFrame, auto_match: bool = True) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Parse and clean transaction dataframe.

        Args:
            df: Input dataframe (any column naming)
            auto_match: Auto-match column names to canonical names

        Returns:
            Tuple of (cleaned_df, metadata)

        Raises:
            ValueError: If required fields are missing or validation fails
        """
        metadata = {
            "rows_before": len(df),
            "rows_after": 0,
            "columns_matched": 0,
            "issues": [],
        }

        # Step 1: Normalize column names
        df_work = df.copy()
        df_work.columns = DataNormalizer.normalize_columns(df_work.columns)

        # Step 2: Auto-match columns if requested
        if auto_match:
            mapping = ColumnMatcher.auto_match_columns(df_work)
            metadata["columns_matched"] = len(mapping)
            df_work = df_work.rename(columns=mapping)

        # Step 3: Verify required fields
        missing = [f for f in cls.REQUIRED_FIELDS if f not in df_work.columns]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        # Step 4: Normalize text fields
        for col in df_work.columns:
            if df_work[col].dtype == object:
                df_work[col] = df_work[col].apply(DataNormalizer.normalize_text)

        # Step 5: Parse money fields
        for col in ["price", "fees"]:
            if col in df_work.columns:
                df_work[col] = DataNormalizer.parse_money(df_work[col])

        # Step 6: Parse datetime fields
        for col in ["op_datetime", "dep_datetime"]:
            if col in df_work.columns:
                df_work[col] = DataNormalizer.parse_datetime(df_work[col])

        # Step 7: Derive fields
        df_work = cls._derive_fields(df_work)

        # Step 8: Validate required fields
        validation_issues = cls._validate_data(df_work)
        metadata["issues"] = validation_issues

        if validation_issues:
            logger.warning(f"Data validation issues found: {validation_issues}")

        # Step 9: Drop completely empty rows
        df_clean = df_work.dropna(how="all").reset_index(drop=True)
        metadata["rows_after"] = len(df_clean)

        logger.info(
            f"Data parsing complete: {metadata['rows_before']} → {metadata['rows_after']} rows, "
            f"{len(df_clean.columns)} columns, {metadata['columns_matched']} auto-matched"
        )

        return df_clean, metadata

    @staticmethod
    def _derive_fields(df: pd.DataFrame) -> pd.DataFrame:
        """Derive computed fields from raw data."""
        df_work = df.copy()

        # Route: from dep_station to arr_station
        if "dep_station" in df_work.columns and "arr_station" in df_work.columns:
            df_work["route"] = (
                df_work["dep_station"].fillna("") + " → " + df_work["arr_station"].fillna("")
            )
            df_work.loc[df_work["route"].str.replace("→", "").str.strip().eq(""), "route"] = None

        # Total amount: price + fees
        if "price" in df_work.columns:
            fees = df_work.get("fees", 0)
            df_work["total_amount"] = df_work["price"].fillna(0) + pd.Series(fees).fillna(0)

        # Date features from op_datetime
        if "op_datetime" in df_work.columns:
            df_work["op_date"] = df_work["op_datetime"].dt.date
            df_work["op_month"] = df_work["op_datetime"].dt.to_period("M").astype(str)
            df_work["op_hour"] = df_work["op_datetime"].dt.hour
            df_work["op_dayofweek"] = df_work["op_datetime"].dt.dayofweek

        # Departure date from dep_datetime
        if "dep_datetime" in df_work.columns:
            df_work["dep_date"] = df_work["dep_datetime"].dt.date

        # Hours to departure: dep_datetime - op_datetime
        if "dep_datetime" in df_work.columns and "op_datetime" in df_work.columns:
            df_work["hours_to_departure"] = (
                (df_work["dep_datetime"] - df_work["op_datetime"]).dt.total_seconds() / 3600
            )

        # Night operation: hour between 0-5
        if "op_hour" in df_work.columns:
            df_work["is_night"] = df_work["op_hour"].between(0, 5).astype(int)

        # Late refund: refund < 24h before departure
        if "hours_to_departure" in df_work.columns and "op_type" in df_work.columns:
            df_work["is_late_refund"] = (
                (df_work["op_type"].str.lower() == "возврат") &
                (df_work["hours_to_departure"] < 24)
            ).astype(int)

        return df_work

    @staticmethod
    def _validate_data(df: pd.DataFrame) -> List[str]:
        """Validate data quality and return issues."""
        issues = []

        # Check for missing critical fields
        for col in ["ticket_no", "passenger_id", "op_datetime"]:
            if col in df.columns:
                missing_pct = df[col].isna().mean()
                if missing_pct > 0.1:
                    issues.append(f"{col}: {missing_pct:.1%} missing")

        # Check for invalid passenger_id
        if "passenger_id" in df.columns:
            invalid = (df["passenger_id"].notna() &
                      ((df["passenger_id"] <= 0) | (df["passenger_id"] != df["passenger_id"].astype(int)))).sum()
            if invalid > 0:
                issues.append(f"passenger_id: {invalid} invalid values")

        # Check for invalid prices
        if "price" in df.columns:
            negative = (df["price"] < 0).sum()
            if negative > 0:
                issues.append(f"price: {negative} negative values")

        # Check for future dates
        if "op_datetime" in df.columns:
            future = (df["op_datetime"] > datetime.now()).sum()
            if future > 0:
                issues.append(f"op_datetime: {future} future dates")

        return issues


class DataQualityReport:
    """Generate QC report for processed data."""

    @staticmethod
    def generate_report(df: pd.DataFrame, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive QC report.

        Args:
            df: Processed dataframe
            metadata: Parsing metadata

        Returns:
            QC report dict
        """
        report = {
            "rows_before": metadata["rows_before"],
            "rows_after": metadata["rows_after"],
            "rows_removed": metadata["rows_before"] - metadata["rows_after"],
            "columns": df.shape[1],
            "columns_matched": metadata["columns_matched"],
            "validation_issues": metadata["issues"],

            # Field completeness
            "field_completeness": {
                col: float((~df[col].isna()).mean())
                for col in df.columns
            },

            # Passengers
            "unique_passengers": int(df["passenger_id"].nunique()),
            "transactions_per_passenger_avg": float(df.groupby("passenger_id").size().mean()),
            "transactions_per_passenger_max": int(df.groupby("passenger_id").size().max()),

            # Dates
            "date_range": {
                "min": str(df["op_datetime"].min()) if "op_datetime" in df.columns else None,
                "max": str(df["op_datetime"].max()) if "op_datetime" in df.columns else None,
            },
        }

        return report
