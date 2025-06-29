import pandas as pd

def filter_top_features(feature_file, top_n=10):
    features = pd.read_csv(feature_file, index_col=0)
    # 这里简单用方差筛选，实际可用更复杂的特征重要性方法
    variances = features.var().sort_values(ascending=False)
    top_features = variances.head(top_n).index.tolist()
    return features[top_features]

if __name__ == "__main__":
    top_features = filter_top_features('drift_features.csv', top_n=10)
    top_features.to_csv('top_drift_features.csv')