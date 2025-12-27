import json
from datetime import datetime

# Mock data simulating duplicate records from error.txt
mock_data = [
    {
        "expert_name": "盘感",
        "name": "五洲特纸",
        "code": "",
        "analysis_reason": "涨停过左峰",
        "analysis_time": "2025-12-26  09:00",
        "analysis_price": "14.19",
        "success_count": 23,
        "success_rate": 191.67,
        "source_url": "https://www.178448.com/fjzt-2.html?page=3",
        "popularity_rank": None,
        "capital_flow_rank": None,
        "crawled_at": datetime.fromisoformat("2025-12-26T11:26:24.397000")
    },
    {
        "expert_name": "盘感",
        "name": "五洲特纸",
        "code": "605007",
        "analysis_reason": "涨停过左峰",
        "analysis_time": "2025-12-26  09:00",
        "analysis_price": "14.19",
        "success_count": 23,
        "success_rate": 191.67,
        "source_url": "https://www.178448.com/fjzt-2.html?page=3",
        "popularity_rank": 82,
        "capital_flow_rank": None,
        "crawled_at": datetime.fromisoformat("2025-12-26T12:29:45.660000")
    },
    {
        "expert_name": "feverxu",
        "name": "再升科技",
        "code": "603601",
        "analysis_reason": "涨停基因",
        "analysis_time": "2025-12-26  08:59",
        "analysis_price": "12.13",
        "success_count": 595,
        "success_rate": 91.12,
        "source_url": "https://www.178448.com/fjzt-2.html?page=3",
        "popularity_rank": 8,
        "capital_flow_rank": None,
        "crawled_at": datetime.fromisoformat("2025-12-26T12:29:45.675000")
    },
    {
        "expert_name": "feverxu",
        "name": "再升科技",
        "code": "",
        "analysis_reason": "涨停基因",
        "analysis_time": "2025-12-26  08:59",
        "analysis_price": "12.13",
        "success_count": 595,
        "success_rate": 91.12,
        "source_url": "https://www.178448.com/fjzt-2.html?page=3",
        "popularity_rank": None,
        "capital_flow_rank": None,
        "crawled_at": datetime.fromisoformat("2025-12-26T11:26:24.402000")
    },
    {
        "expert_name": "\tLQ寻根做强",
        "name": "通宇通讯",
        "code": "002792",
        "analysis_reason": "涨停密码002792",
        "analysis_time": "2025-12-26  07:47",
        "analysis_price": "38.18",
        "success_count": 934,
        "success_rate": 88.36,
        "source_url": "https://www.178448.com/fjzt-2.html?page=9",
        "popularity_rank": 11,
        "capital_flow_rank": 49,
        "crawled_at": datetime.fromisoformat("2025-12-26T12:29:46.383000")
    },
    {
        "expert_name": "\tLQ寻根做强",
        "name": "通宇通讯",
        "code": "",
        "analysis_reason": "涨停密码002792",
        "analysis_time": "2025-12-26  07:47",
        "analysis_price": "38.18",
        "success_count": 934,
        "success_rate": 88.36,
        "source_url": "https://www.178448.com/fjzt-2.html?page=9",
        "popularity_rank": None,
        "capital_flow_rank": None,
        "crawled_at": datetime.fromisoformat("2025-12-26T11:26:24.829000")
    }
]

def test_deduplication_logic(data):
    """Test the deduplication logic using expert_name + stock_name as unique key"""
    # De-duplicate based on expert_name and name (stock name) as unique index
    # Priority is given to records with code (stock code)
    # If both records have code, keep the most recently crawled one
    unique_items = {}
    for item in data:
        # Create a unique key using expert_name and name (stock name)
        expert_name = item.get('expert_name', '')
        stock_name = item.get('name', '')
        unique_key = f"{expert_name}_{stock_name}"
        
        # Check if this key already exists
        if unique_key in unique_items:
            # If the existing record doesn't have code but current one does, replace it
            existing_item = unique_items[unique_key]
            if not existing_item.get('code') and item.get('code'):
                unique_items[unique_key] = item
            # If both have code, keep the one with newer crawled_at timestamp
            elif existing_item.get('code') and item.get('code'):
                existing_time = existing_item.get('crawled_at', datetime.min)
                current_time = item.get('crawled_at', datetime.min)
                if current_time > existing_time:
                    unique_items[unique_key] = item
        else:
            # Add new item if key doesn't exist
            unique_items[unique_key] = item
    
    return list(unique_items.values())

# Run the test
print("Running deduplication test...")
print(f"Original record count: {len(mock_data)}")

deduplicated_data = test_deduplication_logic(mock_data)

print(f"Deduplicated record count: {len(deduplicated_data)}")
print("\nDeduplicated records:")

for item in deduplicated_data:
    print(f"- Expert: {item['expert_name']}, Stock: {item['name']}, Code: {item['code']}, Crawled at: {item['crawled_at']}")

# Verify the results
print("\nVerification:")

# Check that each expert-stock pair has only one record
unique_pairs = {(item['expert_name'], item['name']) for item in deduplicated_data}
print(f"Unique (expert, stock) pairs: {len(unique_pairs)}")

# Check that records with stock codes are preferred
code_count = sum(1 for item in deduplicated_data if item.get('code'))
print(f"Records with stock code: {code_count}/{len(deduplicated_data)}")

print("\nTest completed!")
import json
from datetime import datetime

# Mock data simulating duplicate records from error.txt
mock_data = [
    {
        "expert_name": "盘感",
        "name": "五洲特纸",
        "code": "",
        "analysis_reason": "涨停过左峰",
        "analysis_time": "2025-12-26  09:00",
        "analysis_price": "14.19",
        "success_count": 23,
        "success_rate": 191.67,
        "source_url": "https://www.178448.com/fjzt-2.html?page=3",
        "popularity_rank": None,
        "capital_flow_rank": None,
        "crawled_at": datetime.fromisoformat("2025-12-26T11:26:24.397000")
    },
    {
        "expert_name": "盘感",
        "name": "五洲特纸",
        "code": "605007",
        "analysis_reason": "涨停过左峰",
        "analysis_time": "2025-12-26  09:00",
        "analysis_price": "14.19",
        "success_count": 23,
        "success_rate": 191.67,
        "source_url": "https://www.178448.com/fjzt-2.html?page=3",
        "popularity_rank": 82,
        "capital_flow_rank": None,
        "crawled_at": datetime.fromisoformat("2025-12-26T12:29:45.660000")
    },
    {
        "expert_name": "feverxu",
        "name": "再升科技",
        "code": "603601",
        "analysis_reason": "涨停基因",
        "analysis_time": "2025-12-26  08:59",
        "analysis_price": "12.13",
        "success_count": 595,
        "success_rate": 91.12,
        "source_url": "https://www.178448.com/fjzt-2.html?page=3",
        "popularity_rank": 8,
        "capital_flow_rank": None,
        "crawled_at": datetime.fromisoformat("2025-12-26T12:29:45.675000")
    },
    {
        "expert_name": "feverxu",
        "name": "再升科技",
        "code": "",
        "analysis_reason": "涨停基因",
        "analysis_time": "2025-12-26  08:59",
        "analysis_price": "12.13",
        "success_count": 595,
        "success_rate": 91.12,
        "source_url": "https://www.178448.com/fjzt-2.html?page=3",
        "popularity_rank": None,
        "capital_flow_rank": None,
        "crawled_at": datetime.fromisoformat("2025-12-26T11:26:24.402000")
    },
    {
        "expert_name": "\tLQ寻根做强",
        "name": "通宇通讯",
        "code": "002792",
        "analysis_reason": "涨停密码002792",
        "analysis_time": "2025-12-26  07:47",
        "analysis_price": "38.18",
        "success_count": 934,
        "success_rate": 88.36,
        "source_url": "https://www.178448.com/fjzt-2.html?page=9",
        "popularity_rank": 11,
        "capital_flow_rank": 49,
        "crawled_at": datetime.fromisoformat("2025-12-26T12:29:46.383000")
    },
    {
        "expert_name": "\tLQ寻根做强",
        "name": "通宇通讯",
        "code": "",
        "analysis_reason": "涨停密码002792",
        "analysis_time": "2025-12-26  07:47",
        "analysis_price": "38.18",
        "success_count": 934,
        "success_rate": 88.36,
        "source_url": "https://www.178448.com/fjzt-2.html?page=9",
        "popularity_rank": None,
        "capital_flow_rank": None,
        "crawled_at": datetime.fromisoformat("2025-12-26T11:26:24.829000")
    }
]

def test_deduplication_logic(data):
    """Test the deduplication logic using expert_name + stock_name as unique key"""
    # De-duplicate based on expert_name and name (stock name) as unique index
    # Priority is given to records with code (stock code)
    # If both records have code, keep the most recently crawled one
    unique_items = {}
    for item in data:
        # Create a unique key using expert_name and name (stock name)
        expert_name = item.get('expert_name', '')
        stock_name = item.get('name', '')
        unique_key = f"{expert_name}_{stock_name}"
        
        # Check if this key already exists
        if unique_key in unique_items:
            # If the existing record doesn't have code but current one does, replace it
            existing_item = unique_items[unique_key]
            if not existing_item.get('code') and item.get('code'):
                unique_items[unique_key] = item
            # If both have code, keep the one with newer crawled_at timestamp
            elif existing_item.get('code') and item.get('code'):
                existing_time = existing_item.get('crawled_at', datetime.min)
                current_time = item.get('crawled_at', datetime.min)
                if current_time > existing_time:
                    unique_items[unique_key] = item
        else:
            # Add new item if key doesn't exist
            unique_items[unique_key] = item
    
    return list(unique_items.values())

# Run the test
print("Running deduplication test...")
print(f"Original record count: {len(mock_data)}")

deduplicated_data = test_deduplication_logic(mock_data)

print(f"Deduplicated record count: {len(deduplicated_data)}")
print("\nDeduplicated records:")

for item in deduplicated_data:
    print(f"- Expert: {item['expert_name']}, Stock: {item['name']}, Code: {item['code']}, Crawled at: {item['crawled_at']}")

# Verify the results
print("\nVerification:")

# Check that each expert-stock pair has only one record
unique_pairs = {(item['expert_name'], item['name']) for item in deduplicated_data}
print(f"Unique (expert, stock) pairs: {len(unique_pairs)}")

# Check that records with stock codes are preferred
code_count = sum(1 for item in deduplicated_data if item.get('code'))
print(f"Records with stock code: {code_count}/{len(deduplicated_data)}")

print("\nTest completed!")