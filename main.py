from src.etl import load_csv_to_duckdb

if __name__ == "__main__":
    load_csv_to_duckdb()
    print("DuckDBへのロードが完了しました。")