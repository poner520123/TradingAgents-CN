#!/usr/bin/env python3
"""
测试Silicon Flow上的DeepSeek模型
"""

import requests
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_siliconflow_deepseek(api_key: str):
    """测试Silicon Flow上的DeepSeek模型"""
    # Silicon Flow API配置
    base_url = "https://api.siliconflow.cn/v1"
    test_models = [
        "deepseek-ai/deepseek-chat",
        "deepseek-ai/deepseek-chat-v2",
        "deepseek-ai/deepseek-coder-v2:16b-instruct",
        "deepseek-ai/deepseek-vl-1.5-chat"
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    test_prompt = "Hello, please respond with 'OK' if you can read this."
    
    for model in test_models:
        logger.info(f"🧪 测试模型: {model}")
        
        try:
            # 构建请求数据
            data = {
                "model": model,
                "messages": [
                    {"role": "user", "content": test_prompt}
                ],
                "max_tokens": 20,
                "temperature": 0.1
            }
            
            # 发送请求
            response = requests.post(
                f"{base_url}/chat/completions",
                json=data,
                headers=headers,
                timeout=15
            )
            
            logger.info(f"📡 响应状态: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"✅ 测试成功! 响应: {content.strip()}")
                else:
                    logger.error(f"❌ 响应格式异常: {result}")
            else:
                try:
                    error_detail = response.json()
                    logger.error(f"❌ 测试失败: {error_detail.get('error', {}).get('message', '未知错误')}")
                except:
                    logger.error(f"❌ 测试失败: {response.text[:500]}")
                    
        except requests.exceptions.Timeout:
            logger.error(f"❌ 连接超时")
        except Exception as e:
            logger.error(f"❌ 测试异常: {str(e)}")
        
        logger.info("=" * 50)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python test_siliconflow_deepseek.py <SILICONFLOW_API_KEY>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    test_siliconflow_deepseek(api_key)