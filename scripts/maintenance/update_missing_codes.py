from pymongo import MongoClient
from app.core.config import settings
from app.services.stock_map_service import stock_map_service

# 连接数据库
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]

# 查找缺失股票代码的记录
missing_records = list(db.expert_ranking_data.find({'code': {'$exists': False}}))
print(f'找到 {len(missing_records)} 条缺失股票代码的记录')

# 更新缺失的股票代码
updated_count = 0
for record in missing_records:
    stock_name = record.get('name')
    if stock_name:
        # 尝试从映射表获取股票代码
        code = stock_map_service.get_code_by_name(stock_name)
        if code:
            # 更新数据库记录
            result = db.expert_ranking_data.update_one(
                {'_id': record['_id']},
                {'$set': {'code': code}}
            )
            if result.modified_count > 0:
                updated_count += 1
                print(f'更新成功: {stock_name} -> {code}')
            else:
                print(f'更新失败: {stock_name}')
        else:
            print(f'未找到股票代码: {stock_name}')

print(f'\n共更新 {updated_count} 条记录')
