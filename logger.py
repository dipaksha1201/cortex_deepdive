# Configure logging
import logging
import os

# Get absolute path to project root
project_root = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(project_root, "logs")
service_log_file_path = os.path.join(log_dir, "runner.log")

# Create logs directory
os.makedirs(log_dir, exist_ok=True)

# Configure reasoning logger
runner_logger = logging.getLogger("runner_logger")
runner_logger.setLevel(logging.INFO)
runner_logger.format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
runner_logger.addHandler(logging.FileHandler(service_log_file_path, mode='a'))
runner_logger.addHandler(logging.StreamHandler())

cortex_log_file_path = os.path.join(log_dir, "cortex.log")

# Create logs directory
os.makedirs(log_dir, exist_ok=True)

# Configure reasoning logger
cortex_logger = logging.getLogger("cortex_logger")
cortex_logger.setLevel(logging.INFO)
cortex_logger.format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
cortex_logger.addHandler(logging.FileHandler(cortex_log_file_path, mode='a'))
cortex_logger.addHandler(logging.StreamHandler())

agent_log_file_path = os.path.join(log_dir, "agent.log")

# Create logs directory
os.makedirs(log_dir, exist_ok=True)

# Configure reasoning logger
agent_logger = logging.getLogger("agent_logger")
agent_logger.setLevel(logging.INFO)
agent_logger.format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
agent_logger.addHandler(logging.FileHandler(agent_log_file_path, mode='a'))
agent_logger.addHandler(logging.StreamHandler())