import requests

try:
    response = requests.get('http://localhost:8000/api/ranking/fund', timeout=10)
    print('资金榜API状态:', response.status_code)
    if response.status_code == 200:
        data = response.json()
        print('资金榜数据条数:', len(data['data']))
except Exception as e:
    print('API调用失败:', str(e))
