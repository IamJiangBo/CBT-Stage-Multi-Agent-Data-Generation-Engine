import os
from dotenv import load_dotenv

LLM_SERVER_URL = os.getenv("LLM_SERVER_URL")

sign = load_dotenv("/data/.env_secret")
if not sign:
    API_KEY = None
    raise Exception("加载环境变量失败，请检查`/data/.env_secret`中是否正确配置API_KEY.")
    
else:
    API_KEY = os.getenv("XINLIXUE_API_KEY")

CBT_IP   = '127.0.0.1'
CBT_PORT = '8889'
CBT_URL  = f'http://{CBT_IP}:{CBT_PORT}/generate_data'