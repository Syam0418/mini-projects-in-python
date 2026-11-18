
import os
import sqlite3
import configparser
import tempfile
import json

from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qsl, quote
from collections import Counter, defaultdict

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


# ---------------------------------------------------------
# 1. FIND FIREFOX PROFILE
# ---------------------------------------------------------

def find_firefox_profiles():

    appdata = os.environ.get("APPDATA")

    if not appdata:
        return []

    firefox_folder = Path(appdata) / "Mozilla" / "Firefox"
    profiles_file = firefox_folder / "profiles.ini"

    if not profiles_file.exists():
        return []

    config = configparser.ConfigParser()
    config.read(profiles_file, encoding="utf-8")

    profiles = []

    for section in config.sections():

        if not section.startswith("Profile"):
            continue

        profile_path = config.get(section, "Path", fallback=None)

        if not profile_path:
            continue

        is_relative = config.get(
            section, "IsRelative", fallback="1"
        )

        if is_relative == "1":
            full_path = firefox_folder / profile_path
        else:
            full_path = Path(profile_path)

        database_path = full_path / "places.sqlite"

        if database_path.exists():
            is_default = config.get(
                section, "Default", fallback="0"
            )

            profiles.append({
                "name": section,
                "path": full_path,
                "database": database_path,
                "default": is_default == "1"
            })

    return profiles


# ---------------------------------------------------------
# 2. SELECT FIREFOX DATABASE
# ---------------------------------------------------------

def select_firefox_database():

    print("\n========== FIREFOX PROFILE DETECTION ==========")

    profiles = find_firefox_profiles()

    if not profiles:
        print("Firefox profile was not detected automatically.")

        manual_path = input(
            "Enter the full path of places.sqlite: "
        ).strip().strip('"')

        database_path = Path(manual_path)

        if not database_path.exists():
            raise FileNotFoundError(
                "The specified places.sqlite file does not exist."
            )

        return database_path

    print("\nAvailable Firefox profiles:\n")

    for index, profile in enumerate(profiles, start=1):

        default_text = " (Default)" if profile["default"] else ""

        print(
            f"{index}. {profile['name']}{default_text}"
        )

        print(f"   {profile['database']}")

    default_profiles = [
        i for i, profile in enumerate(profiles)
        if profile["default"]
    ]

    if len(profiles) == 1:
        selected = 1

    elif len(default_profiles) == 1:
        selected = default_profiles[0] + 1

        answer = input(
            f"\nUse the default profile ({selected})? "
            "Press Enter for Yes, or enter another number: "
        ).strip()

        if answer:
            selected = int(answer)

    else:
        selected = int(
            input("\nEnter the profile number to use: ")
        )

    if selected < 1 or selected > len(profiles):
        raise ValueError("Invalid Firefox profile selection.")

    return profiles[selected - 1]["database"]


# ---------------------------------------------------------
# 3. CREATE A SAFE DATABASE COPY
# ---------------------------------------------------------

def create_database_copy(original_database, temporary_folder):

    copied_database = Path(temporary_folder) / "places_copy.sqlite"

    # Open the original database in read-only mode.
    database_uri = original_database.as_uri() + "?mode=ro"

    source_connection = sqlite3.connect(
        database_uri,
        uri=True,
        timeout=15
    )

    destination_connection = sqlite3.connect(
        str(copied_database)
    )

    try:
        # SQLite backup API safely copies database contents.
        source_connection.backup(destination_connection)

    finally:
        destination_connection.close()
        source_connection.close()

    return copied_database


# ---------------------------------------------------------
# 4. GET URL DETAILS
# ---------------------------------------------------------

def extract_url_details(url):

    try:
        parsed = urlsplit(url)

        domain = (parsed.hostname or "").lower()

        query_parameters = parse_qsl(
            parsed.query,
            keep_blank_values=True
        )

        query_data = [
            {
                "parameter": key,
                "value": value
            }
            for key, value in query_parameters
        ]

        return {
            "domain": domain,
            "path": parsed.path,
            "query_string": parsed.query,
            "query_parameters": json.dumps(
                query_data,
                ensure_ascii=False
            ),
            "fragment": parsed.fragment
        }

    except Exception:
        return {
            "domain": "",
            "path": "",
            "query_string": "",
            "query_parameters": "[]",
            "fragment": ""
        }


# ---------------------------------------------------------
# 5. MATCH WEBSITE OR DOMAIN
# ---------------------------------------------------------

def create_domain_filter(user_input):

    user_input = user_input.strip()

    if not user_input:
        raise ValueError("Website URL or domain cannot be empty.")

    # Accept either a domain or a complete URL.
    if "://" not in user_input:
        candidate = "https://" + user_input
    else:
        candidate = user_input

    parsed = urlsplit(candidate)
    hostname = (parsed.hostname or "").lower()

    if hostname:
        return hostname, ""

    # If the input is not a valid hostname, use URL keyword matching.
    return "", user_input.lower()


def matches_website(url, domain, keyword):

    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").lower()

    if domain:
        return (
            hostname == domain
            or hostname.endswith("." + domain)
        )

    return keyword in url.lower()


# ---------------------------------------------------------
# 6. GET HISTORY RECORDS
# ---------------------------------------------------------

def read_firefox_history(database_path):

    connection = sqlite3.connect(
        database_path,
        timeout=15
    )

    connection.row_factory = sqlite3.Row

    try:

        query = """
        SELECT
            p.id AS place_id,
            p.url AS url,
            p.title AS title,
            p.visit_count AS total_visit_count,

            v.id AS visit_id,
            v.visit_date AS visit_date,
            v.visit_type AS visit_type,

            referrer.url AS referrer_url

        FROM moz_places AS p

        INNER JOIN moz_historyvisits AS v
            ON p.id = v.place_id

        LEFT JOIN moz_historyvisits AS previous_visit
            ON v.from_visit = previous_visit.id

        LEFT JOIN moz_places AS referrer
            ON previous_visit.place_id = referrer.id

        ORDER BY v.visit_date DESC
        """

        cursor = connection.execute(query)

        return [dict(row) for row in cursor.fetchall()]

    finally:
        connection.close()


# ---------------------------------------------------------
# 7. FILTER HISTORY BY DOMAIN AND DATE
# ---------------------------------------------------------

def filter_history(records, website, start_date, end_date):

    domain, keyword = create_domain_filter(website)

    filtered_records = []

    for record in records:

        url = record["url"] or ""

        if not matches_website(url, domain, keyword):
            continue

        visit_timestamp = record["visit_date"]

        if visit_timestamp is None:
            continue

        # Firefox stores visit_date as microseconds since Unix epoch.
        visit_datetime = datetime.fromtimestamp(
            visit_timestamp / 1_000_000,
            tz=timezone.utc
        ).astimezone()

        visit_date = visit_datetime.date()

        if start_date and visit_date < start_date:
            continue

        if end_date and visit_date > end_date:
            continue

        details = extract_url_details(url)

        filtered_records.append({
            "page_title": record["title"] or "",
            "url": url,
            "domain": details["domain"],
            "path": details["path"],
            "query_string": details["query_string"],
            "query_parameters": details["query_parameters"],
            "fragment": details["fragment"],
            "visit_datetime": visit_datetime.strftime(
                "%Y-%m-%d %H:%M:%S %Z"
            ),
            "visit_type": record["visit_type"],
            "total_visit_count": record["total_visit_count"],
            "referrer_url": record["referrer_url"] or ""
        })

    return filtered_records


# ---------------------------------------------------------
# 8. CREATE UNIQUE URL RECORDS
# ---------------------------------------------------------

def create_unique_urls(records):

    unique = {}

    for record in records:

        url = record["url"]

        if url not in unique:

            unique[url] = {
                "page_title": record["page_title"],
                "url": url,
                "domain": record["domain"],
                "path": record["path"],
                "query_string": record["query_string"],
                "query_parameters": record["query_parameters"],
                "fragment": record["fragment"],
                "visits_in_selected_period": 0,
                "total_firefox_visit_count": record[
                    "total_visit_count"
                ]
            }

        unique[url]["visits_in_selected_period"] += 1

    return list(unique.values())


# ---------------------------------------------------------
# 9. CREATE DOMAIN SUMMARY
# ---------------------------------------------------------

def create_domain_summary(records):

    summary = defaultdict(
        lambda: {
            "total_visits": 0,
            "unique_urls": set()
        }
    )

    for record in records:

        domain = record["domain"]

        summary[domain]["total_visits"] += 1
        summary[domain]["unique_urls"].add(record["url"])

    output = []

    for domain, values in summary.items():

        output.append({
            "domain": domain,
            "total_visits": values["total_visits"],
            "unique_urls": len(values["unique_urls"])
        })

    return sorted(
        output,
        key=lambda item: item["total_visits"],
        reverse=True
    )


# ---------------------------------------------------------
# 10. WRITE EXCEL WORKBOOK
# ---------------------------------------------------------

def write_worksheet(workbook, sheet_name, records):

    worksheet = workbook.create_sheet(sheet_name)

    if not records:
        worksheet.append(["No matching records found."])
        return

    headers = list(records[0].keys())

    worksheet.append(headers)

    for record in records:

        row = []

        for header in headers:

            value = record.get(header, "")

            # Prevent Excel from interpreting extracted text as formulas.
            if isinstance(value, str) and value.startswith(
                ("=", "+", "-", "@")
            ):
                value = "'" + value

            row.append(value)

        worksheet.append(row)

    # Format header row.
    for cell in worksheet[1]:

        cell.font = Font(
            bold=True,
            color="FFFFFF"
        )

        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="1F4E78"
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    # Adjust column widths.
    for column_cells in worksheet.columns:

        max_length = 0
        column_letter = column_cells[0].column_letter

        for cell in column_cells:

            cell_length = len(str(cell.value or ""))

            max_length = max(
                max_length,
                min(cell_length, 60)
            )

        worksheet.column_dimensions[
            column_letter
        ].width = max(max_length + 2, 15)


def export_to_excel(records, output_path):

    workbook = Workbook()

    # Remove the default worksheet.
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    unique_records = create_unique_urls(records)

    domain_summary = create_domain_summary(records)

    write_worksheet(
        workbook,
        "All_Matching_URLs",
        records
    )

    write_worksheet(
        workbook,
        "Unique_URLs",
        unique_records
    )

    write_worksheet(
        workbook,
        "Visit_Summary",
        domain_summary
    )

    workbook.save(output_path)


# ---------------------------------------------------------
# 11. MAIN PROGRAM
# ---------------------------------------------------------

def main():

    print("\n======================================")
    print(" FIREFOX HISTORY URL EXTRACTOR")
    print("======================================")

    # Select Firefox history database.
    database_path = select_firefox_database()

    print("\nSelected database:")
    print(database_path)

    # Get website/domain.
    website = input(
        "\nEnter website URL or domain to search: "
    ).strip()

    # Optional date range.
    print("\nDate filter format: YYYY-MM-DD")
    print("Press Enter to include all available dates.")

    start_text = input(
        "Enter start date: "
    ).strip()

    end_text = input(
        "Enter end date: "
    ).strip()

    start_date = (
        datetime.strptime(start_text, "%Y-%m-%d").date()
        if start_text else None
    )

    end_date = (
        datetime.strptime(end_text, "%Y-%m-%d").date()
        if end_text else None
    )

    if start_date and end_date and start_date > end_date:
        raise ValueError("Start date cannot be after end date.")

    # Output Excel file.
    output_text = input(
        "\nEnter Excel output path "
        "(Press Enter for default): "
    ).strip().strip('"')

    if output_text:
        output_path = Path(output_text)
    else:
        output_path = Path.cwd() / "Firefox_History_Extract.xlsx"

    if output_path.suffix.lower() != ".xlsx":
        output_path = output_path.with_suffix(".xlsx")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    print("\nReading Firefox history...")

    # Create a temporary database copy.
    with tempfile.TemporaryDirectory() as temp_folder:

        copied_database = create_database_copy(
            database_path,
            temp_folder
        )

        all_records = read_firefox_history(
            str(copied_database)
        )

    print("Total history visits found:", len(all_records))

    # Filter matching records.
    filtered_records = filter_history(
        all_records,
        website,
        start_date,
        end_date
    )

    print(
        "Matching history visits:",
        len(filtered_records)
    )

    # Export workbook.
    export_to_excel(
        filtered_records,
        output_path
    )

    print("\n======================================")
    print(" EXTRACTION COMPLETED")
    print("======================================")

    print("Matching visits:", len(filtered_records))
    print("Unique URLs:", len(create_unique_urls(filtered_records)))
    print("Excel file:", output_path.resolve())


if __name__ == "__main__":

    try:
        main()

    except PermissionError:
        print(
            "\nPermission error. Close Firefox and run the program again."
        )

    except sqlite3.Error as error:
        print("\nSQLite database error:", error)
        print(
            "Close Firefox and retry. Check that the profile database exists."
        )

    except ValueError as error:
        print("\nInput error:", error)

    except Exception as error:
        print("\nUnexpected error:", error)
