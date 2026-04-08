from pymongo import MongoClient
from datetime import datetime, timedelta
from app.core.config import settings

# Connect to MongoDB
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]
collection = db['expert_ranking_data']

# Get all expert ranking data from the last 7 days
one_week_ago = datetime.utcnow() - timedelta(days=7)
cursor = collection.find({
    "crawled_at": {"$gte": one_week_ago}
})

all_data = list(cursor)
print(f"Total records from DB: {len(all_data)}")

# Check if any records have code=None
code_none_count = 0
for i, item in enumerate(all_data):
    if item.get('code') is None:
        code_none_count += 1
        if code_none_count <= 10:
            print(f"Record {i}: expert_name={item.get('expert_name')}, name={item.get('name')}, code={item.get('code')}")

print(f"\nTotal records with code=None: {code_none_count}")

# Check the deduplication logic
unique_items = {}
for item in all_data:
    expert_name = item.get('expert_name', '')
    stock_name = item.get('name', '')
    unique_key = f"{expert_name}_{stock_name}"
    
    if unique_key not in unique_items:
        unique_items[unique_key] = item
    else:
        existing_item = unique_items[unique_key]
        existing_has_code = existing_item.get('code') is not None
        current_has_code = item.get('code') is not None
        
        if not existing_has_code and current_has_code:
            unique_items[unique_key] = item
        elif existing_has_code and current_has_code:
            existing_crawled = existing_item.get('crawled_at', datetime.min)
            current_crawled = item.get('crawled_at', datetime.min)
            
            if current_crawled > existing_crawled:
                unique_items[unique_key] = item

unique_data = list(unique_items.values())
print(f"\nAfter deduplication: {len(unique_data)}")

# Check if any records in unique_data have code=None
code_none_count_after_dedup = 0
for i, item in enumerate(unique_data):
    if item.get('code') is None:
        code_none_count_after_dedup += 1
        if code_none_count_after_dedup <= 10:
            print(f"Unique record {i}: expert_name={item.get('expert_name')}, name={item.get('name')}, code={item.get('code')}")

print(f"\nTotal unique records with code=None: {code_none_count_after_dedup}")
