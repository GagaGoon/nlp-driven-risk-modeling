from pathlib import Path

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
    """Download one filing and it's metadata."""
    directory = output_dir / filing.form / ticker
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / (
        f"{filing.accession_no}.txt"
    )

    if path.exists():
        return "skipped"

    content = filing.full_text_submission()

    if not content:
        raise ValueError("Got empty file")

    temporary_path = path.with_suffix(".txt.part")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)

    return "downloaded"


def main():
    pass

if __name__ == "__main__":
    main()
