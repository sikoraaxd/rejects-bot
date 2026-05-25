from datetime import date
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

from app.core.settings import PROJECT_ROOT, settings
from app.schemas.analysis import CaseOptionsResponse

import requests


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

MONTHS = {
    "январь": 1,
    "февраль": 2,
    "март": 3,
    "апрель": 4,
    "май": 5,
    "июнь": 6,
    "июль": 7,
    "август": 8,
    "сентябрь": 9,
    "октябрь": 10,
    "ноябрь": 11,
    "декабрь": 12,
}

CASES_SHEETS_COLUMN_NAMES = [
    'unk',
    'spc',
    'project_name',
    'employee',
    'technology',
    'grade',
    'source',
    'demand',
    'commentary',
    'expert_analyze',
    'readiness',
    'date'
]

CASE_FILTER_FIELDS = [
    "project_name",
    "employee",
    "technology",
    "grade",
    "source",
    "date",
    "sheet",
]



def extract_google_file_id(url: str) -> str:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")

    if "d" in parts:
        index = parts.index("d") + 1
        if index < len(parts):
            return parts[index]

    raise ValueError(f"Не удалось достать file_id из URL: {url}")


def download_xlsx_from_url(url: str) -> bytes:
    file_id = extract_google_file_id(url)
    parsed = urlparse(url)

    if parsed.netloc == "docs.google.com" and "/spreadsheets/" in parsed.path:
        download_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    else:
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    response = requests.get(download_url, allow_redirects=True, timeout=30)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "").lower()
    if "text/html" in content_type:
        raise RuntimeError(
            "Google вернул HTML, а не xlsx. "
            "Скорее всего, файл приватный или требует авторизацию."
        )

    return response.content


def dataframe_to_text(df: pd.DataFrame, max_rows: int = 500) -> str:
    if df.empty:
        return ""

    limited = df.fillna("").head(max_rows)
    return "\n".join(
        "\t".join(
            str(cell).strip()
            for cell in row
            if str(cell).strip()
        )
        for row in limited.values.tolist()
    ).strip()


def worksheet_rows_to_text(rows: list[list[str]], max_rows: int = 500) -> str:
    return "\n".join(
        "\t".join(cell.strip() for cell in row if cell.strip())
        for row in rows[:max_rows]
    ).strip()


def extract_expert_analyze_from_xlsx_url(url: str) -> str:
    try:
        sheets = pd.read_excel(
            BytesIO(download_xlsx_from_url(url)),
            sheet_name=[1, 2],      # 2-й и 3-й листы, индексация с нуля
            header=None,
            engine="openpyxl",
        )

        parts = []

        for sheet_index, df in sheets.items():
            content = dataframe_to_text(df)
            if content:
                parts.append(content)
    except Exception as e:
        print(f"Ошибка при извлечении анализа из xlsx: {e}")
        return "Не удалось загрузить анализ"
    return "\n\n".join(parts)


class SheetsClient:

    def __init__(self):
        self.sheets = self.load_sheets()


    def _project_path(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else PROJECT_ROOT / path
    

    def _gspread_client(self) -> gspread.Client:
        credentials = Credentials.from_service_account_file(
            self._project_path(settings.google_service_account_file),
            scopes=SCOPES,
        )
        return gspread.authorize(credentials)
    

    def _is_month_enabled(self, sheet: str) -> bool:
        month = MONTHS.get(sheet.strip().lower())
        return month is not None and month <= date.today().month
    

    def load_sheets(self) -> dict[str, pd.DataFrame]:
        spreadsheet = self._gspread_client().open_by_url(settings.sheet_url)

        sheets = {}
        for worksheet in spreadsheet.worksheets():
            if not self._is_month_enabled(worksheet.title):
                continue

            sheet = pd.DataFrame(worksheet.get_all_values()[1:])  # пропускаем заголовок
            if len(sheet.columns) > 12:
                sheet = sheet.iloc[:, :12]
            sheet.columns = CASES_SHEETS_COLUMN_NAMES
            sheet["sheet"] = worksheet.title
            sheets[worksheet.title] = sheet

        return sheets
    

    def get_all_cases(self) -> pd.DataFrame:
        if not self.sheets:
            return pd.DataFrame(columns=[*CASES_SHEETS_COLUMN_NAMES, "sheet"])

        return pd.concat(self.sheets.values(), ignore_index=True, copy=False)
    

    def list_case_options(
        self,
        limit: int = 500,
        filters: dict[str, str] | None = None,
    ) -> CaseOptionsResponse:
        all_cases = self.get_all_cases()
        filtered = all_cases
        for name, value in (filters or {}).items():
            if value and name in filtered.columns:
                filtered = filtered[filtered[name] == value]

        filtered = filtered.fillna("")
        if filtered.empty:
            return CaseOptionsResponse(
                items=[],
                filters={field: [] for field in CASE_FILTER_FIELDS},
            )

        filter_options = {
            field: sorted(
                filtered[field].astype(str).str.strip().loc[lambda values: values != ""].unique(),
                key=str.casefold,
            )
            for field in CASE_FILTER_FIELDS
            if field in filtered.columns
        }

        return CaseOptionsResponse(
            items=filtered.head(limit).to_dict("records"),
            filters=filter_options,
        )


    def extract_excel_data(
        self,
        sheet_url: str,
        sheet_indexes: list[int] | None = None,
        max_rows: int = 500,
    ) -> str:
        try:
            spreadsheet = self._gspread_client().open_by_url(sheet_url)
            worksheets = spreadsheet.worksheets()
            if sheet_indexes is not None:
                worksheets = [
                    worksheet
                    for index, worksheet in enumerate(worksheets)
                    if index in sheet_indexes
                ]

            parts = []
            for worksheet in worksheets:
                content = worksheet_rows_to_text(worksheet.get_all_values(), max_rows=max_rows)
                if content:
                    parts.append(f"{worksheet.title}\n{content}")

            return "\n\n".join(parts)
        except Exception as gspread_error:
            print(f"Google Sheets extraction failed, trying xlsx fallback: {gspread_error}")

        try:
            sheet_name = sheet_indexes if sheet_indexes is not None else None
            sheets = pd.read_excel(
                BytesIO(download_xlsx_from_url(sheet_url)),
                sheet_name=sheet_name,
                header=None,
                engine="openpyxl",
            )
            if isinstance(sheets, pd.DataFrame):
                sheets = {"Sheet1": sheets}

            parts = []
            for sheet_name, df in sheets.items():
                content = dataframe_to_text(df, max_rows=max_rows)
                if content:
                    parts.append(f"{sheet_name}\n{content}")

            return "\n\n".join(parts)
        except Exception as xlsx_error:
            return f"Не удалось загрузить таблицу: {xlsx_error}"


    def extract_expert_analyze(self, sheet_url: str) -> str:
        return self.extract_excel_data(sheet_url, sheet_indexes=[1, 2])


if __name__ == "__main__":
    SHEETS = SheetsClient()
    print(SHEETS.extract_expert_analyze('https://docs.google.com/spreadsheets/d/1oNOETpW_jbgZK0G-BWon2shZHVD3KfeX/edit?gid=839579023#gid=839579023'))
