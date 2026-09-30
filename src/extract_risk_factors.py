from copy import copy
from pathlib import Path

import pandas as pd
from edgar import Filing, use_local_storage
from edgar.company_reports import TenK, TenQ


class LocalFiling(Filing):
    """Читать основной документ из SGML без обращения к сайту SEC."""

    def html(self):
        # Filing.html() в установленной версии может обращаться к сети,
        # даже если документ уже содержится в локальной подаче.
        return self.sgml().html()


def extract_risk_factors(source_path):
    """Извлечь раздел о факторах риска из сохранённой подачи."""
    filing = LocalFiling.from_sgml(source_path)
    if filing.form == "10-K405":
        # Для старой годовой формы используем разбор разделов 10-K.
        # Исходный файл и форма в реестре остаются без изменений.
        filing = copy(filing)
        filing.form = "10-K"
    report = filing.obj()

    if report is None:
        raise ValueError(
            f"Не удалось создать объект отчёта: {filing.form}"
        )

    if isinstance(report, TenK):
        text = report.get("Item 1A")
    elif isinstance(report, TenQ):
        text = report.get("Part II, Item 1A")
    else:
        raise TypeError(
            f"Неподдерживаемый тип отчёта: {type(report).__name__}"
        )

    if not text:
        return None
    return text.strip() or None


def main():
    """Обработать скачанные подачи и сохранить результаты извлечения."""
    project_dir = Path(__file__).resolve().parent.parent
    raw_dir = project_dir / "data" / "raw"
    registry_dir = project_dir / "data" / "indexes"
    output_dir = project_dir / "data" / "interim" / "risk_factors"

    # Все документы читаются из файлов; повторная загрузка не требуется.
    use_local_storage(raw_dir, allow_network_fallback=False)

    results_dir = registry_dir / "extraction"
    results_dir.mkdir(parents=True, exist_ok=True)

    for registry_path in sorted(registry_dir.glob("*.csv")):
        ticker = registry_path.stem
        registry = pd.read_csv(registry_path, dtype=str, keep_default_na=False)

        # Статусы скачивания остаются в исходных столбцах и реестрах.
        registry["extraction_status"] = "pending"
        registry["extraction_error"] = ""

        result_path = results_dir / registry_path.name
        registry.to_csv(result_path, index=False)

        for i, row in registry.iterrows():
            relative_path = (
                Path(row["form"])
                / ticker
                / f"{row['accession_number']}.txt"
            )
            source_path = raw_dir / relative_path
            target_path = output_dir / relative_path

            try:
                # Удаляем прежний результат, чтобы при неудаче повторного
                # извлечения на диске не остался устаревший текст.
                target_path.unlink(missing_ok=True)

                if not source_path.is_file():
                    status = "source_missing"
                else:
                    text = extract_risk_factors(source_path)

                    if text is None:
                        status = "not_found"
                    else:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        temporary_path = target_path.with_suffix(".txt.part")
                        temporary_path.write_text(text, encoding="utf-8")
                        temporary_path.replace(target_path)
                        status = "extracted"

            except Exception as error:
                status = "error"
                registry.loc[i, "extraction_error"] = str(error)

            registry.loc[i, "extraction_status"] = status
            registry.to_csv(result_path, index=False)
            print(ticker, row["accession_number"], status)


if __name__ == "__main__":
    main()
