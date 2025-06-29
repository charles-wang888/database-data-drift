import pandas as pd
import sqlite3
import requests
import numpy as np
import re

def load_transactions(db_path):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    df['trade_time'] = pd.to_datetime(df['trade_time'])
    df['trade_date'] = df['trade_time'].dt.date
    return df

def load_top_features(feature_path):
    features = pd.read_csv(feature_path, index_col=0, encoding='utf-8')
    return features

def detect_drift_points(series, threshold=2.5):
    # 用z-score检测异常点
    z_scores = (series - series.mean()) / series.std()
    drift_points = series.index[z_scores.abs() > threshold].tolist()
    drift_scores = z_scores[z_scores.abs() > threshold].tolist()
    return drift_points, drift_scores

def get_drift_context(trade_df, drift_date):
    # 获取该日期的所有交易明细
    details = trade_df[trade_df['trade_date'] == drift_date]
    return details

def call_ollama_for_drift_analysis(feature_name, drift_date, drift_value, drift_score, details):
    import json
    prompt = (
        f"检测到特征【{feature_name}】在日期【{drift_date}】发生数据漂移，漂移系数为{drift_score:.2f}，该特征值为{drift_value}。\n"
        f"以下是该日期的交易明细（部分字段）：\n"
        f"{details[['user_id', 'product', 'price', 'quantity']].to_string(index=False)}\n"
        "注意：特征因子的计算方法已经由专业算法（tsfresh）完成，无需你推理或反思特征的计算方式。\n"
        "请只关注给定的特征值、日期和交易明细，进行归因和解释，不要讨论特征的计算过程,思考过程尽量精简。\n"
        "请分析：\n"
        "1. 为什么认为该点是数据漂移（论据）？\n"
        "2. 该漂移的可能归因分析（如用户、商品、价格、数量等异常变化），提炼要点，并控制在150字以内？\n"
        "请用结构化表格输出，字段为：数据漂移点、数据漂移的发生时间、认为是数据漂移论据、数据漂移系数、数据漂移归因分析。"
    )
    try:
        with requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen3:4b",
                    "prompt": prompt,
                    "stream": True
                },
                timeout=300,
                stream=True
        ) as response:
            response.raise_for_status()
            result = ""
            print("大模型流式输出：", flush=True)
            for line in response.iter_lines(decode_unicode=True):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    chunk = data.get("response", "")
                    print(chunk, end="", flush=True)  # 实时打印
                    result += chunk
                except Exception as e:
                    print(f"\n解析流式输出出错: {e}")
            print("\n")  # 输出结束换行
            return result
    except Exception as e:
        print(f"Ollama API调用失败: {e}")
        return None

def load_id_date_map(map_path):
    id_date_map = pd.read_csv(map_path)
    id2date = dict(zip(id_date_map['id'], id_date_map['trade_date']))
    return id2date

def parse_llm_output(llm_output):
    """
    尝试从大模型输出中提取结构化表格内容。
    支持markdown表格、csv、或常见的文本表格。
    """
    # 尝试提取markdown表格
    table_pattern = re.compile(r'\|.*\|')
    lines = [line for line in llm_output.split('\n') if '|' in line]
    if len(lines) >= 2:
        # 处理markdown表格
        header = [h.strip() for h in lines[0].split('|')[1:-1]]
        data = []
        for row in lines[2:]:
            cols = [c.strip() for c in row.split('|')[1:-1]]
            if len(cols) == len(header):
                data.append(cols)
        if data:
            return pd.DataFrame(data, columns=header)
    # 尝试提取csv格式
    try:
        df = pd.read_csv(pd.compat.StringIO(llm_output))
        if not df.empty:
            return df
    except Exception:
        pass
    # 尝试用分隔符空格等
    return None

def extract_conclusion(text):
    # 常见的分隔符
    for sep in ['结论：', '结论:', '结论', '<think>', '分析过程：', '分析过程:']:
        if sep in text:
            return text.split(sep)[0].strip()
    return text.strip()

if __name__ == "__main__":
    db_path = 'your_db_path.db'
    feature_path = 'top_drift_features.csv'
    id_date_map_path = 'id_date_map.csv'

    # ========== 新增：可配置参数 ==========
    FEATURE_TO_ANALYZE = 'quantity__abs_energy'  # 要分析的特征名，如quantity__abs_energy
    TOP_N_DRIFT_POINTS = 5  # 只分析前N个漂移点
    # ========== END ==========

    trade_df = load_transactions(db_path)
    features = load_top_features(feature_path)
    id2date = load_id_date_map(id_date_map_path)
    results = []
    summary_rows = []

    if FEATURE_TO_ANALYZE not in features.columns:
        raise ValueError(f"特征 {FEATURE_TO_ANALYZE} 不在特征表中！可选特征有: {list(features.columns)}")

    series = features[FEATURE_TO_ANALYZE]
    drift_points, drift_scores = detect_drift_points(series)
    # 只取前N个漂移点
    drift_points = drift_points[:TOP_N_DRIFT_POINTS]
    drift_scores = drift_scores[:TOP_N_DRIFT_POINTS]
    for drift_id, drift_score in zip(drift_points, drift_scores):
        drift_date = id2date.get(drift_id, str(drift_id))  # 还原成具体日期
        drift_value = series.loc[drift_id]
        details = get_drift_context(trade_df, pd.to_datetime(drift_date).date())

        result = call_ollama_for_drift_analysis(
            FEATURE_TO_ANALYZE, drift_date, drift_value, drift_score, details
        )
        if result:
            results.append(result)
            # 尝试结构化解析
            df = parse_llm_output(result)
            if df is not None:
                # 只保留需要的字段
                for _, row in df.iterrows():
                    summary_rows.append({
                        '数据漂移的发生时间': row.get('数据漂移的发生时间', drift_date),
                        '认为是数据漂移的论据': row.get('认为是数据漂移论据', ''),
                        '数据漂移系数': row.get('数据漂移系数', drift_score),
                        '数据漂移归因分析': extract_conclusion(row.get('数据漂移归因分析', ''))
                    })
            else:
                # 若无法结构化解析，简单记录
                summary_rows.append({
                    '数据漂移的发生时间': drift_date,
                    '认为是数据漂移的论据': '',
                    '数据漂移系数': drift_score,
                    '数据漂移归因分析': extract_conclusion(result)
                })

    summary_table = pd.DataFrame(summary_rows, columns=[
        '数据漂移的发生时间',
        '认为是数据漂移的论据',
        '数据漂移系数',
        '数据漂移归因分析'
    ])
    print('汇总表：')
    print(summary_table)
    summary_table.to_csv('data_drift_root_cause.csv', index=False, encoding='utf-8-sig')