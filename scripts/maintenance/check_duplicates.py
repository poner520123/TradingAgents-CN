#!/usr/bin/env python3
"""
Script to check for duplicate popularity data in the database
"""

import logging
from pymongo import MongoClient
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def check_popularity_duplicates():
    """Check for duplicate popularity data"""
    logger.info("=== Checking popularity data duplicates ===")
    
    # Connect to MongoDB
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    collection = db.popularity_data
    
    # Get total count
    total_count = collection.count_documents({})
    logger.info(f"Total popularity records: {total_count}")
    
    # Get unique code count
    unique_codes = collection.distinct("code")
    logger.info(f"Unique stock codes: {len(unique_codes)}")
    
    # Find duplicate codes
    pipeline = [
        {
            "$group": {
                "_id": "$code",
                "count": {"$sum": 1}
            }
        },
        {
            "$match": {
                "count": {"$gt": 1}
            }
        },
        {
            "$sort": {
                "count": -1
            }
        }
    ]
    
    duplicates = list(collection.aggregate(pipeline))
    logger.info(f"Duplicate codes found: {len(duplicates)}")
    
    if duplicates:
        logger.info("Top 5 duplicate codes:")
        for item in duplicates[:5]:
            logger.info(f"  {item['_id']}: {item['count']} records")
        
        # Check a specific duplicate code
        if duplicates:
            test_code = duplicates[0]['_id']
            logger.info(f"\nExamining records for code {test_code}:")
            records = list(collection.find(
                {"code": test_code},
                {"code": 1, "name": 1, "rank": 1, "crawled_at": 1}
            ).sort("crawled_at", -1).limit(5))
            
            for i, record in enumerate(records, 1):
                logger.info(f"  {i}. Name: {record.get('name')}, Rank: {record.get('rank')}, Crawled: {record.get('crawled_at')}")
    
    client.close()
    return duplicates

def test_aggregation_pipeline():
    """Test the aggregation pipeline used in the fix"""
    logger.info("\n=== Testing aggregation pipeline ===")
    
    # Connect to MongoDB
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    collection = db.popularity_data
    
    # Test the aggregation pipeline from our fix
    pipeline = [
        {
            "$sort": {"code": 1, "crawled_at": -1}
        },
        {
            "$group": {
                "_id": "$code",
                "doc": {"$first": "$$ROOT"}
            }
        },
        {
            "$replaceRoot": {"newRoot": "$doc"}
        },
        {
            "$sort": {"rank": 1}
        },
        {
            "$skip": 0
        },
        {
            "$limit": 20
        }
    ]
    
    result = list(collection.aggregate(pipeline))
    logger.info(f"Pipeline returned {len(result)} records")
    
    # Check for duplicates in the result
    codes = []
    duplicate_codes = []
    for item in result:
        code = item.get('code')
        if code in codes:
            duplicate_codes.append(code)
        codes.append(code)
    
    if duplicate_codes:
        logger.error(f"❌ Found duplicates in pipeline result: {duplicate_codes}")
    else:
        logger.info("✅ No duplicates in pipeline result")
    
    # Show first few results
    logger.info("\nFirst 5 results from pipeline:")
    for i, item in enumerate(result[:5], 1):
        logger.info(f"  {i}. {item.get('code')} - {item.get('name')} (Rank: {item.get('rank')})")
    
    client.close()
    return result

if __name__ == "__main__":
    logger.info("Starting duplicate check...")
    duplicates = check_popularity_duplicates()
    test_aggregation_pipeline()
    logger.info("Duplicate check completed!")
