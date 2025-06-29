import sqlite3
import random
from datetime import datetime, timedelta

# 连接数据库（如果不存在会自动创建）
conn = sqlite3.connect('your_db_path.db')
cursor = conn.cursor()

# 创建交易表
cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product TEXT,
    price FLOAT,
    quantity INTEGER,
    trade_time DATETIME
)
''')

# 随机生成2000条数据
products = ['汽水', '矿泉水', '果汁', '茶饮', '咖啡']
start_date = datetime(2023, 1, 1)
for i in range(2000):
    user_id = random.randint(1, 100)
    product = random.choice(products)
    if product == '汽水':
        price = round(random.uniform(5, 15), 2)
    elif product == '矿泉水':
        price = round(random.uniform(1, 5), 2)
    elif product == '果汁':
        price = round(random.uniform(8, 20), 2)
    elif product == '茶饮':
        price = round(random.uniform(6, 18), 2)
    else:
        price = round(random.uniform(10, 30), 2)
    quantity = random.randint(1, 10)
    trade_time = start_date + timedelta(days=random.randint(0, 364), hours=random.randint(0, 23), minutes=random.randint(0, 59))
    cursor.execute('''
        INSERT INTO transactions (user_id, product, price, quantity, trade_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, product, price, quantity, trade_time.strftime('%Y-%m-%d %H:%M:%S')))

conn.commit()
conn.close()
print("交易表已创建并插入2000条数据。")