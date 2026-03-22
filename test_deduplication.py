#!/usr/bin/env python3
"""
Test script to verify deduplication for popularity and capital flow data
"""

import logging
from app.services.scrapy_crawler_service import ScrapyCrawlerService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_popularity_deduplication():
    """Test deduplication for popularity data"""
    logger.info("=== Testing popularity data deduplication ===")
    
    service = ScrapyCrawlerService()
    data, total = service.get_popularity_data(page=1, page_size=50)
    
    logger.info(f"Total unique stocks: {total}")
    logger.info(f"Returned data count: {len(data)}")
    
    # Check for duplicates
    codes = []
    duplicates = []
    for item in data:
        code = item.get('code')
        if code in codes:
            duplicates.append(code)
        codes.append(code)
    
    if duplicates:
        logger.error(f"❌ Found duplicate codes: {duplicates}")
        return False
    else:
        logger.info("✅ No duplicates found in popularity data")
        # Show first few items
        for i, item in enumerate(data[:5], 1):
            logger.info(f"  {i}. {item['code']} - {item['name']} (Rank: {item['rank']})")
        return True

def test_capital_flow_deduplication():
    """Test deduplication for capital flow data"""
    logger.info("\n=== Testing capital flow data deduplication ===")
    
    service = ScrapyCrawlerService()
    data, total = service.get_capital_flow_data(page=1, page_size=50)
    
    logger.info(f"Total unique stocks: {total}")
    logger.info(f"Returned data count: {len(data)}")
    
    # Check for duplicates
    codes = []
    duplicates = []
    for item in data:
        code = item.get('code')
        if code in codes:
            duplicates.append(code)
        codes.append(code)
    
    if duplicates:
        logger.error(f"❌ Found duplicate codes: {duplicates}")
        return False
    else:
        logger.info("✅ No duplicates found in capital flow data")
        # Show first few items
        for i, item in enumerate(data[:5], 1):
            logger.info(f"  {i}. {item['code']} - {item['name']} (Main Flow: {item['main_flow']})")
        return True

if __name__ == "__main__":
    logger.info("Starting deduplication tests...")
    
    success1 = test_popularity_deduplication()
    success2 = test_capital_flow_deduplication()
    
    if success1 and success2:
        logger.info("\n🎉 All deduplication tests passed!")
    else:
        logger.error("\n❌ Some deduplication tests failed!")
