from pathlib import Path

import pandas as pd
from edgar import Company, set_identity

set_identity("John Doe john.doe@company.com")

def list_filings(ticker, forms):
    """Get a list of available filings."""
    company = Company(ticker)

    filings = company.get_filings(
        form=forms,
        amendments=False,
        trigger_full_load=True,
    )

    return filings


def download_filing(filing, ticker, output_dir):
    """Download one filing."""
    directory = output_dir / filing.form / ticker
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / (
        f"{filing.accession_no}.txt"
    )

    # Skip previously saved filings when running the script again.
    if path.exists():
        return "skipped"

    content = filing.full_text_submission()

    if not content:
        raise ValueError("Got empty file")

    # Write to a temporary file first so an interrupted write does not
    # leave an incomplete filing that would be treated as downloaded.
    temporary_path = path.with_suffix(".txt.part")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)

    return "downloaded"


def main():
    """Iterate over companies and forms, and output the results."""
    tickers = ['AAPL', 'MSFT', 'AMZN', 'JPM', 'XOM', 'JNJ', 'WMT', 'CAT', 'NEE', 'KO',
               'UPS', 'NVDA']
    forms = ["10-K", "10-Q", "10-K405"]

    project_dir = Path(__file__).resolve().parent.parent
    output_dir = project_dir / "data" / "raw"

    for ticker in tickers:
        try:
            filings = list(list_filings(ticker, forms))
        except Exception as error:
            print(f"{ticker}: failed to retrieve the list.: {error}")
            continue

        registry = pd.DataFrame([
            {
                "accession_number": filing.accession_no,
                "form": filing.form,
                "filing_date": filing.filing_date,
                "status": "pending",
                "error": "",
            }
            for filing in filings
        ])

        registry_dir = project_dir / "data" / "indexes"
        registry_dir.mkdir(parents=True, exist_ok=True)

        registry_path = registry_dir / f"{ticker}.csv"
        # Save the complete list of filings with pending status before downloading.
        registry.to_csv(registry_path, index=False)

        for i, filing in enumerate(filings):
            try:
                status = download_filing(filing, ticker, output_dir)
                # Existing files also count as downloaded: the registry tracks
                # document availability, not the outcome of the current attempt.
                registry.loc[i, "status"] = ("downloaded" if status == "skipped" else 
                                             status
                                            )
                print(ticker, filing.accession_no, status)
            except Exception as error:
                registry.loc[i, "status"] = "error"
                registry.loc[i, "error"] = str(error)
                print(f"{ticker}, {filing.accession_no}: "
                      f"download error: {error}"
                     )

            registry.to_csv(registry_path, index=False)

if __name__ == "__main__":
    main()
