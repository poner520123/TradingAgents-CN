import requests

print("=== 最终验证报告 ===\n")

# 测试资金榜API
print("1. 测试资金榜API:")
try:
    response = requests.get('http://localhost:8000/api/ranking/fund')
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 资金榜API正常，返回 {len(data['data'])} 条数据")
        # 检查是否有股票代码缺失
        missing_codes = [item for item in data['data'] if not item.get('code')]
        if missing_codes:
            print(f"   ⚠️ 发现 {len(missing_codes)} 条记录缺失股票代码")
        else:
            print("   ✅ 所有记录都有股票代码")
    else:
        print(f"   ❌ 资金榜API错误: {response.status_code}")
except Exception as e:
    print(f"   ❌ 资金榜API调用失败: {str(e)}")

# 测试人气榜API
print("\n2. 测试人气榜API:")
try:
    response = requests.get('http://localhost:8000/api/ranking/popularity')
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 人气榜API正常，返回 {len(data['data'])} 条数据")
        # 检查是否有股票代码缺失
        missing_codes = [item for item in data['data'] if not item.get('code')]
        if missing_codes:
            print(f"   ⚠️ 发现 {len(missing_codes)} 条记录缺失股票代码")
        else:
            print("   ✅ 所有记录都有股票代码")
    else:
        print(f"   ❌ 人气榜API错误: {response.status_code}")
except Exception as e:
    print(f"   ❌ 人气榜API调用失败: {str(e)}")

# 测试专家排行API
print("\n3. 测试专家排行API:")
try:
    response = requests.get('http://localhost:8000/api/astock/expert-ranking')
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 专家排行API正常，返回 {len(data['data'])} 条数据")
        # 检查股票代码重复情况
        codes = [item['code'] for item in data['data']]
        unique_codes = set(codes)
        if len(codes) != len(unique_codes):
            print(f"   ⚠️ 发现股票代码重复: {len(codes)}条记录，{len(unique_codes)}个唯一代码")
        else:
            print("   ✅ 股票代码无重复")
        # 检查是否有股票代码缺失
        missing_codes = [item for item in data['data'] if not item.get('code')]
        if missing_codes:
            print(f"   ⚠️ 发现 {len(missing_codes)} 条记录缺失股票代码")
        else:
            print("   ✅ 所有记录都有股票代码")
    else:
        print(f"   ❌ 专家排行API错误: {response.status_code}")
except Exception as e:
    print(f"   ❌ 专家排行API调用失败: {str(e)}")

# 测试交叉分析API
print("\n4. 测试交叉分析API:")
try:
    response = requests.get('http://localhost:8000/api/astock/cross-analysis')
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 交叉分析API正常，返回 {len(data['data'])} 条数据")
    else:
        print(f"   ❌ 交叉分析API错误: {response.status_code}")
except Exception as e:
    print(f"   ❌ 交叉分析API调用失败: {str(e)}")

print("\n=== 验证完成 ===")
