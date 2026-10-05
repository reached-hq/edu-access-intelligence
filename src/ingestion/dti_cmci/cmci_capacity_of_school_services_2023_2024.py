import time

import pandas as pd
import requests
from bs4 import BeautifulSoup


PROCESS_URL = "https://cmci.dti.gov.ph/data-portal-process.php"

YEARS = [2023, 2024]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    )
}


def get_capacity_of_school_services_score(lgu, year):
    """Request the CMCI Capacity of School Services score for one LGU-year."""

    payload = [
        ("chk-indicators[]", "css"),
        ("chk-lgu[]", lgu),
        ("chk-year[]", str(year)),
    ]

    try:
        response = requests.post(
            PROCESS_URL,
            headers=HEADERS,
            data=payload,
            timeout=30,
        )
    except requests.RequestException:
        return None, "cmci_server_error"

    if response.status_code != 200:
        return None, "cmci_server_error"

    soup = BeautifulSoup(response.text, "html.parser")

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["th", "td"])
            ]

            if (
                len(cells) >= 2
                and cells[0].strip() == "Capacity of School Services"
            ):
                return clean_score(cells[1])

    return None, "cmci_missing"


def clean_score(score):
    """Convert a CMCI score to numeric and assign a status."""

    if score is None:
        return None, "cmci_missing"

    score = str(score).strip()

    if score == "-":
        return None, "cmci_missing"

    try:
        return float(score), "valid"
    except ValueError:
        return None, "unexpected_value"


def main():
    lgu_file = "/Volumes/edu_access/00-source/raw/cmci/cmci_lgu_list.csv"
    output_file = "cmci_capacity_of_school_services_2023_2024.csv"

    lgu_df = pd.read_csv(lgu_file)
    lgus = lgu_df["lgu"].dropna().tolist()

    results = []
    total = len(lgus) * len(YEARS)
    count = 0

    for lgu in lgus:
        for year in YEARS:
            count += 1

            capacity_of_school_services, status = (
                get_capacity_of_school_services_score(lgu, year)
            )

            print(
                f"[{count}/{total}] "
                f"{lgu} | {year} | "
                f"{capacity_of_school_services} | {status}"
            )

            results.append(
                {
                    "lgu": lgu,
                    "year": year,
                    "capacity_of_school_services": capacity_of_school_services,
                    "status": status,
                }
            )

            time.sleep(0.2)

    df = pd.DataFrame(results)

    df.to_csv(output_file, index=False)

    print("\nScraping complete.")
    print("Shape:", df.shape)
    print("Unique LGUs:", df["lgu"].nunique())
    print("Years:", sorted(df["year"].unique()))
    print(
        "Duplicate LGU-year combinations:",
        df.duplicated(["lgu", "year"]).sum(),
    )

    print("\nStatus counts:")
    print(df["status"].value_counts(dropna=False))

    print(
        "\nMissing capacity of school services scores:",
        df["capacity_of_school_services"].isna().sum(),
    )

    print("\nSaved:", output_file)


if __name__ == "__main__":
    main()