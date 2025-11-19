"""
Run a complete end-to-end test:
1. Send Oct 30th data via producer
2. Run consumer to process and generate predictions
3. Verify predictions are generated
"""
import sys
import os
import subprocess
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("END-TO-END PIPELINE TEST")
    logger.info("=" * 60)
    logger.info("")
    
    # Step 1: Run producer to send Oct 30th data
    logger.info("Step 1: Running producer to send Oct 30th data...")
    logger.info("  Command: python producer.py --date 2025-10-30 --delay 5")
    logger.info("")
    
    try:
        producer_result = subprocess.run(
            [sys.executable, "producer.py", "--date", "2025-10-30", "--delay", "5"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=False,
            text=True
        )
        
        if producer_result.returncode != 0:
            logger.error("✗ Producer failed!")
            return False
        
        logger.info("✓ Producer completed")
        logger.info("")
        
    except Exception as e:
        logger.error(f"✗ Error running producer: {e}")
        return False
    
    # Step 2: Wait a bit for messages to be available
    logger.info("Waiting 3 seconds for messages to be available...")
    time.sleep(3)
    logger.info("")
    
    # Step 3: Run consumer to process messages and generate predictions
    logger.info("Step 2: Running consumer to process messages and generate predictions...")
    logger.info("  Command: python consumer.py --max-messages 20")
    logger.info("")
    
    try:
        consumer_result = subprocess.run(
            [sys.executable, "consumer.py", "--max-messages", "20"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=False,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if consumer_result.returncode != 0:
            logger.error("✗ Consumer failed!")
            return False
        
        logger.info("✓ Consumer completed")
        logger.info("")
        
    except subprocess.TimeoutExpired:
        logger.warning("⚠ Consumer timed out (this is OK if it's still processing)")
    except Exception as e:
        logger.error(f"✗ Error running consumer: {e}")
        return False
    
    # Step 4: Verify predictions were generated
    logger.info("Step 3: Verifying predictions were generated...")
    logger.info("")
    
    try:
        test_result = subprocess.run(
            [sys.executable, "test_e2e_simple.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        logger.info(test_result.stdout)
        if test_result.stderr:
            logger.error(test_result.stderr)
        
        if test_result.returncode == 0:
            logger.info("")
            logger.info("=" * 60)
            logger.info("✓ END-TO-END TEST PASSED!")
            logger.info("=" * 60)
            return True
        else:
            logger.info("")
            logger.warning("⚠ Test completed but predictions may not have been generated yet")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error verifying predictions: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

