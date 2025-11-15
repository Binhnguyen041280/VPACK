import base64
import csv
import logging
import os
from io import BytesIO

import pandas as pd

# Thiết lập logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def force_split_excel_text(df: pd.DataFrame) -> pd.DataFrame:
    if df.shape[1] == 1 and isinstance(df.columns[0], str) and "\t" in df.columns[0]:
        raw = df.to_csv(index=False, header=False)
        reader = csv.reader(raw.splitlines(), delimiter="\t")
        rows = list(reader)
        df_fixed = pd.DataFrame(rows[1:], columns=rows[0])
        logger.debug(
            f"[DEBUG] After force_split_excel_text - df.columns: {df_fixed.columns.tolist()}"
        )
        logger.debug(f"[DEBUG] After force_split_excel_text - df.shape: {df_fixed.shape}")
        return df_fixed
    return df


def parse_uploaded_file(
    file_content: str = None, file_path: str = None, is_excel: bool = False
) -> pd.DataFrame:
    """
    Decode base64-encoded file content or read from file path and return a pandas DataFrame.
    Supports both CSV and Excel formats.
    Raises detailed exceptions instead of falling back silently.
    """
    logger.debug(
        f"parse_uploaded_file called with is_excel={is_excel}, file_content={'provided' if file_content else 'not provided'}, file_path={file_path}"
    )

    if not file_content and not file_path:
        raise ValueError("Either file_content or file_path must be provided.")

    if file_content:
        try:
            file_bytes = base64.b64decode(file_content)
        except Exception as e:
            raise ValueError(f"Failed to decode base64 content: {e}")
        buffer = BytesIO(file_bytes)
    elif file_path:
        if not os.path.exists(file_path):
            raise ValueError(f"File not found at path: {file_path}")
        buffer = file_path  # pandas can read directly from file path

    try:
        if is_excel:
            logger.debug("Reading file as Excel (pd.read_excel)")
            try:
                df = pd.read_excel(buffer, header=None, engine="openpyxl")  # Xóa encoding
            except Exception as e:
                logger.debug(f"Failed to read Excel with pd.read_excel: {str(e)}")
                logger.debug("Falling back to pd.read_csv")
                buffer.seek(0)  # Reset con trỏ file để đọc lại
                df = pd.read_csv(buffer, sep=",", encoding="utf-8-sig", engine="python")
            logger.debug(f"[DEBUG] Raw DataFrame before processing: {df.to_dict()}")
            logger.debug(f"[DEBUG] Raw first row (potential header): {df.iloc[0].tolist()}")
            if df.shape[0] > 1:
                df.columns = df.iloc[0].values.tolist()
                df = df[1:]
                df = force_split_excel_text(df)  # Fix nếu dính lỗi tab
            else:
                raise ValueError("Excel file missing header/data")
            logger.debug(f"[DEBUG] df.columns: {df.columns.tolist()}")
            logger.debug(f"[DEBUG] df.shape: {df.shape}")
            logger.debug(f"[DEBUG] df.head(2): {df.head(2).to_dict()}")
            return df
        else:
            logger.debug("Reading file as CSV (pd.read_csv)")
            try:
                df = pd.read_csv(
                    buffer, sep=",", encoding="latin1", engine="python"
                )  # Thử dấu phẩy trước
                # Kiểm tra nếu chỉ có 1 cột và cột đó chứa dấu ;
                if (
                    len(df.columns) == 1
                    and df.columns[0]
                    and isinstance(df.columns[0], str)
                    and ";" in df.columns[0]
                ):
                    logger.debug("Detected single column with semicolon, retrying with sep=';'")
                    if file_content:
                        buffer.seek(0)  # Reset con trỏ file để đọc lại nếu dùng file_content
                    df = pd.read_csv(buffer, sep=";", encoding="latin1", engine="python")
                return df
            except pd.errors.ParserError:
                if file_content:
                    buffer.seek(0)  # Reset con trỏ file để đọc lại nếu dùng file_content
                return pd.read_csv(
                    buffer, sep=";", encoding="latin1", engine="python"
                )  # Nếu lỗi, thử dấu chấm phẩy
    except Exception as e:
        file_type = "Excel" if is_excel else "CSV"
        raise ValueError(f"Failed to read {file_type} file: {e}")
