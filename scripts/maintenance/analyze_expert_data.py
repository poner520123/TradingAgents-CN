import requests
from collections import defaultdict

# 获取专家排行数据
response = requests.get('http://localhost:8000/api/astock/expert-ranking')
data = response.json()

print('专家排行数据分析:')
print(f'总数据条数: {len(data["data"])}')

# 统计股票代码重复情况
code_counts = defaultdict(int)
for item in data['data']:
    code = item['code']
    code_counts[code] += 1

print('\n股票代码重复情况:')
for code, count in code_counts.items():
    if count > 1:
        print(f'{code}: {count}次')

# 检查是否有缺失股票代码的情况
missing_codes = []
for item in data['data']:
    if not item['code'] or item['code'].strip() == '':
        missing_codes.append(item)

print(f'\n缺失股票代码的记录数: {len(missing_codes)}')
if missing_codes:
    print('缺失股票代码的记录:')
    for item in missing_codes:
        print(f'专家: {item["expert_name"]}, 股票名称: {item["name"]}')
