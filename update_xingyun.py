from pymongo import MongoClient
from app.core.config import settings

# 连接数据库
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]

# 查找行云科技的记录
record = db.expert_ranking_data.find_one({'name': '行云科技', 'expert_name': 'Q玄'})
print('记录详情:', record)

if record:
    # 更新股票代码
    result = db.expert_ranking_data.update_one(
        {'_id': record['_id']},
        {'$set': {'code': '300209'}}
    )
    print('更新结果:', result.modified_count)
