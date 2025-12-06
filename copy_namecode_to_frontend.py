#!/usr/bin/env python3
import os
import shutil

# 定义源文件和目标文件路径
source_path = 'newstock/data/namecode.csv'
destination_path = 'frontend/public/namecode.csv'

print(f'正在检查源文件: {source_path}')
if os.path.exists(source_path):
    print(f'源文件存在，大小: {os.path.getsize(source_path)} 字节')
    
    # 确保目标目录存在
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    
    # 复制文件，指定编码为UTF-8
    print(f'正在将文件复制到: {destination_path}')
    try:
        # 读取源文件内容
        with open(source_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 写入目标文件，确保编码为UTF-8
        with open(destination_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f'文件复制成功，目标文件大小: {os.path.getsize(destination_path)} 字节')
        print('文件编码已确保为UTF-8')
    except Exception as e:
        print(f'文件复制失败: {e}')
else:
    print(f'源文件不存在: {source_path}')
