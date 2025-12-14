import os
import re

# 定义要替换的字符串
old_str = "TA"
new_str = "TA"

# 定义要跳过的目录
skip_dirs = [
    ".git",
    ".github",
    "node_modules",
    "dist",
    "build",
    ".streamlit",
    "__pycache__",
    ".pytest_cache"
]

# 定义要处理的文件类型
file_extensions = [
    ".py",
    ".vue",
    ".ts",
    ".js",
    ".html",
    ".css",
    ".scss",
    ".json",
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".bat",
    ".ps1",
    ".sh"
]

def should_process_file(file_path):
    """检查文件是否应该被处理"""
    # 跳过指定目录
    for skip_dir in skip_dirs:
        if skip_dir in file_path:
            return False
    # 只处理指定扩展名的文件
    _, ext = os.path.splitext(file_path)
    return ext in file_extensions

def replace_in_file(file_path):
    """替换文件中的字符串"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查文件中是否包含要替换的字符串
        if old_str not in content:
            return False
        
        # 替换字符串
        new_content = content.replace(old_str, new_str)
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """主函数"""
    root_dir = "."
    processed_files = 0
    modified_files = 0
    
    print(f"开始替换所有文件中的 '{old_str}' 为 '{new_str}'")
    print(f"跳过目录: {skip_dirs}")
    print(f"处理文件类型: {file_extensions}")
    print("=" * 50)
    
    # 遍历所有文件
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 从dirnames中移除要跳过的目录
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            processed_files += 1
            
            if should_process_file(file_path):
                if replace_in_file(file_path):
                    modified_files += 1
                    print(f"✓ {file_path}")
    
    print("=" * 50)
    print(f"处理文件总数: {processed_files}")
    print(f"修改文件数量: {modified_files}")
    print("替换完成!")

if __name__ == "__main__":
    main()
