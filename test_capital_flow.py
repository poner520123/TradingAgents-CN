import os
import subprocess
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_capital_flow_crawler():
    """Test capital flow crawler directly"""
    logger.info("Testing capital flow crawler...")
    
    # Get the path to the scrapy project
    scrapy_project_path = os.path.join(os.path.dirname(__file__), 'app', 'scrapy_project', 'crawler')
    
    # Command to run the crawler
    cmd = f"python -m scrapy crawl capital_flow -o -:jsonlines"
    
    try:
        # Run the command
        result = subprocess.run(
            cmd, 
            shell=True, 
            cwd=scrapy_project_path, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            timeout=60
        )
        
        logger.info(f"Return code: {result.returncode}")
        
        if result.returncode != 0:
            logger.error(f"Error output: {result.stderr}")
            return False
        
        logger.info(f"Output length: {len(result.stdout)} characters")
        
        # Parse the output
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            logger.info(f"Number of lines in output: {len(lines)}")
            
            # Parse each JSON line
            data = []
            for i, line in enumerate(lines[:5]):  # Show first 5 items
                if line.strip():
                    try:
                        item = json.loads(line)
                        data.append(item)
                        logger.info(f"Item {i+1}: {item.get('code')} - {item.get('name')} - Flow: {item.get('main_flow_text')}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse line {i+1}: {e}")
                        logger.error(f"Line content: {line}")
            
            logger.info(f"Successfully parsed {len(data)} items")
            return len(data) > 0
        else:
            logger.warning("No output from crawler")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Crawler timed out")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_capital_flow_crawler()
    if success:
        logger.info("✅ Capital flow crawler test PASSED")
    else:
        logger.error("❌ Capital flow crawler test FAILED")
