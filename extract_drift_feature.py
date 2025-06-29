import pandas as pd
import sqlite3
from tsfresh import extract_features

def load_data(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    return df

def extract_tsfresh_features(df):
    # 假设以天为单位聚合
    df['trade_date'] = pd.to_datetime(df['trade_time']).dt.date
    daily = df.groupby('trade_date').agg({'price': 'mean', 'quantity': 'sum'}).reset_index()
    daily['id'] = range(len(daily))
    # 保存id到日期的映射
    daily[['id', 'trade_date']].to_csv('id_date_map.csv', index=False)
    # tsfresh需要id和time列
    daily = daily.rename(columns={'trade_date': 'time'})
    features = extract_features(daily, column_id='id', column_sort='time')
    return features

if __name__ == "__main__":
    df = load_data('your_db_path.db')
    features = extract_tsfresh_features(df)
    features.to_csv('drift_features.csv')

    # 分类特征因子
    price_features = [col for col in features.columns if col.startswith('price_')]
    quantity_features = [col for col in features.columns if col.startswith('quantity_')]
    other_features = [col for col in features.columns if not (col.startswith('price_') or col.startswith('quantity_'))]

    print("\n与价格相关的特征因子 (price_*) 共{}个：".format(len(price_features)))
    for f in price_features:
        print(f)
    print("\n与数量相关的特征因子 (quantity_*) 共{}个：".format(len(quantity_features)))
    for f in quantity_features:
        print(f)
    print("\n其他特征因子 共{}个：".format(len(other_features)))
    for f in other_features:
        print(f)