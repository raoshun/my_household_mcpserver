import os
from typing import Optional

import pandas as pd


# 年月を指定して1か月分のcsvファイルを取得する
def load_csv_from_month(
    year: Optional[int], month: Optional[int], src_dir: str = "data"
) -> pd.DataFrame:
    """指定された年月の家計簿データを含むCSVファイルを読み込む.

    Args:
        year (int): 年
        month (int): 月
        src_dir (str, optional): CSVファイルが格納されているディレクトリ. Defaults to "data".

    Returns:
        pd.DataFrame: 読み込まれたデータフレーム
    """
    # 共通の引数を定義
    common_kwargs = {
        "encoding": "cp932",
        "dtype": {
            "計算対象": "Int64",
            "金額（円）": "Int64",
            "大分類": "category",
            "中分類": "category",
        },
    }

    # 年や月が指定されていない場合は全てのデータを対象とする
    if year is None:  # yearが指定されていない場合は全てのデータを対象とする
        df = pd.concat(
            [
                pd.read_csv(os.path.join(src_dir, f), **common_kwargs)
                for f in os.listdir(src_dir)
                if f.endswith(".csv")
            ]
        )
        return df
    elif (
        month is None
    ):  # yearは指定されているがmonthが指定されていない場合はその年の全てのデータを対象とする
        files = [
            f for f in os.listdir(src_dir) if f.startswith(f"収入・支出詳細_{year}-")
        ]
        df = pd.concat(
            [
                pd.read_csv(os.path.join(src_dir, f), **common_kwargs)
                for f in files
                if f.endswith(".csv")
            ]
        )
        return df
    elif month == 2:  # 指定された月の末日がファイル名に含まれるので推定
        end_day = 28
    elif month in [4, 6, 9, 11]:
        end_day = 30
    else:
        end_day = 31

    csv_filename = (
        f"収入・支出詳細_{year}-{month:02d}-01_{year}-{month:02d}-{end_day}.csv"
    )
    csv_path = os.path.join(src_dir, csv_filename)
    df = pd.read_csv(csv_path, **common_kwargs)
    # 計算対象=1かつ金額（円）がマイナスの行を抽出
    df = df.loc[(df["計算対象"] == 1) & (df["金額（円）"] < 0)]

    return df
