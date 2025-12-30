import pandas as pd
import os
import math


def split_csv_by_parts(
    input_csv: str,
    parts: int,
    output_dir: str = "splitted_csv"
):
    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_csv(input_csv)
    total_rows = len(df)

    if parts <= 0:
        raise ValueError("Количество частей должно быть > 0")

    rows_per_part = math.ceil(total_rows / parts)

    for i in range(parts):
        start = i * rows_per_part
        end = min(start + rows_per_part, total_rows)

        if start >= total_rows:
            break

        chunk = df.iloc[start:end]
        out_path = os.path.join(output_dir, f"part_{i+1}.csv")
        chunk.to_csv(out_path, index=False)

        print(f"Сохранён {out_path} ({len(chunk)} строк)")


if __name__ == "__main__":
    split_csv_by_parts(
        input_csv="runs_out/Run_20251225_171759/timeseries_bundle.csv",
        parts=9

    )
