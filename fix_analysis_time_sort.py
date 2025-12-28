#!/usr/bin/env python3

# 修复 get_cross_analysis_data 方法，使其按 analysis_time 降序排序
with open('d:\\projects\\TradingAgents-CN\\app\\services\\scrapy_crawler_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_method = '''    def get_cross_analysis_data(self, page=1, page_size=20):
        """Get cross analysis data with popularity and capital flow ranks."""
        # Get all expert ranking data first for de-duplication
        cursor = self.expert_ranking_collection.find()
        cursor = cursor.sort([
            ("success_rate", DESCENDING),
            ("success_count", DESCENDING)
        ])
        
        all_data = list(cursor)
        # Convert ObjectId to string
        for d in all_data:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        
        # De-duplicate based on expert_name and name (stock name) as unique index
        # Priority is given to records with code (stock code), and if both have code, keep the newer one
        unique_items = {}
        for item in all_data:
            # Create a unique key using expert_name and name (stock name)
            expert_name = item.get('expert_name', '')
            stock_name = item.get('name', '')
            unique_key = f"{expert_name}_{stock_name}"
            
            # Check if this key already exists
            if unique_key in unique_items:
                existing_item = unique_items[unique_key]
                existing_has_code = existing_item.get('code') is not None
                current_has_code = item.get('code') is not None
                
                # If the existing record doesn't have code but current one does, replace it
                if not existing_has_code and current_has_code:
                    unique_items[unique_key] = item
                # If both have code, keep the newer one
                elif existing_has_code and current_has_code:
                    existing_time = existing_item.get('analysis_time', '')
                    current_time = item.get('analysis_time', '')
                    if current_time > existing_time:
                        unique_items[unique_key] = item
                # If existing has code but current doesn't, keep existing
            else:
                # Add new item if key doesn't exist
                unique_items[unique_key] = item
        
        # Convert back to list
        unique_data = list(unique_items.values())
        total = len(unique_data)
        
        # Apply pagination
        skip = (page - 1) * page_size
        paginated_data = unique_data[skip:skip + page_size]'''

new_method = '''    def get_cross_analysis_data(self, page=1, page_size=20):
        """Get cross analysis data with popularity and capital flow ranks."""
        # Get all expert ranking data first for de-duplication
        cursor = self.expert_ranking_collection.find()
        
        all_data = list(cursor)
        # Convert ObjectId to string
        for d in all_data:
            if '_id' in d:
                d['_id'] = str(d['_id'])
        
        # De-duplicate based on expert_name and name (stock name) as unique index
        # Priority is given to records with code (stock code), and if both have code, keep the newer one
        unique_items = {}
        for item in all_data:
            # Create a unique key using expert_name and name (stock name)
            expert_name = item.get('expert_name', '')
            stock_name = item.get('name', '')
            unique_key = f"{expert_name}_{stock_name}"
            
            # Check if this key already exists
            if unique_key in unique_items:
                existing_item = unique_items[unique_key]
                existing_has_code = existing_item.get('code') is not None
                current_has_code = item.get('code') is not None
                
                # If the existing record doesn't have code but current one does, replace it
                if not existing_has_code and current_has_code:
                    unique_items[unique_key] = item
                # If both have code, keep the newer one
                elif existing_has_code and current_has_code:
                    existing_time = existing_item.get('analysis_time', '')
                    current_time = item.get('analysis_time', '')
                    if current_time > existing_time:
                        unique_items[unique_key] = item
                # If existing has code but current doesn't, keep existing
            else:
                # Add new item if key doesn't exist
                unique_items[unique_key] = item
        
        # Convert back to list and sort by analysis_time in descending order
        unique_data = list(unique_items.values())
        unique_data.sort(key=lambda x: x.get('analysis_time', ''), reverse=True)
        total = len(unique_data)
        
        # Apply pagination
        skip = (page - 1) * page_size
        paginated_data = unique_data[skip:skip + page_size]'''

updated_content = content.replace(old_method, new_method)

with open('d:\\projects\\TradingAgents-CN\\app\\services\\scrapy_crawler_service.py', 'w', encoding='utf-8') as f:
    f.write(updated_content)

print("✅ File updated successfully! The get_cross_analysis_data method now sorts by analysis_time descending")