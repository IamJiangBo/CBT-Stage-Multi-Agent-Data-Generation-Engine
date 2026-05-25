from ast import Str
import os
import sys
import time
import json
import asyncio
import uvicorn
import argparse
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
import metagpt
from metagpt.schema import Message
from metagpt.context import Context
from metagpt.environment import Environment

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from roles.data_process_role import DataProcessAgent

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import agent_workflow_logger as logger

print("metagpt file: ", metagpt.__file__)
class CoTDataAgentRequest(BaseModel):
      
      user_query: str
      analyse_info: str
      draft_respone: str
      advice_info: str
      conv_k: Optional[int] = 1
      max_loop_times: Optional[int] = 3
      conv_uuid: Optional[str] = None
      total_rounds: Optional[int] = 0
      agent_max_react_times: int = 3
      timeout: float = 600.0
      output_dir: str = "agent_outputs"
      output_file_name: str = "sft_data.jsonl"


def init_env(request: CoTDataAgentRequest):
      
      ## output infos
      show_str = f"""
      *********** cbt agent 系统 ************
      -- agent_max_react_times: {request.agent_max_react_times}
      """
      logger.info(f'{show_str}')
      
      # 输出路径配置
      os.makedirs(request.output_dir, exist_ok=True)
      output_path = os.path.join(request.output_dir, request.output_file_name)

      # 初始化环境
      context = Context()
      env = Environment(context=context)

      # 定义角色列表
      role_list = [
            DataProcessAgent(),
      ]
      
      env.add_roles(role_list)
      return env


app = FastAPI()


@app.post("/generate_data")
async def generate_data(request: CoTDataAgentRequest):

      env = init_env(request)
      logger.info(f"env init done.")

      # try:

      send_msg = {
            "user_query": request.user_query,
            "analyse_info": request.analyse_info,
            "draft_respone": request.draft_respone,
            "advice_info": request.advice_info,
            "conv_k": request.conv_k,
            "conv_uuid": request.conv_uuid,
            "total_rounds": request.total_rounds
      }
      send_msg = json.dumps(send_msg, ensure_ascii=False, indent=4)
      
      env.publish_message(
            Message(
                  content=send_msg, 
                  send_to=[DataProcessAgent()]
            )
      )

      # 当生成结束时，env.is_idle 为 True
      start_time = time.time()
      while not env.is_idle:
            logger.info(f"[SERVICE LOGGING]: Current execution time: {time.time() - start_time:.2f}s, env.is_idle: {env.is_idle}")
            
            ## 多并发的跑全部roles
            await env.run()
            
            if (time.time() - start_time) > request.timeout:
                  logger.warning(f"Timeout reached after {time.time() - start_time:.2f}s")
                  env.is_idle = True
                  
                  return {"status": "failed", "message": "数据生成超时"}

      logger.info(f"pipeline finished.")
      
      """ workflow 运行结束之后，获取最后一个角色的最后一次记忆 """

      last_role = list(env.roles.values())[-1]
      last_role_memory = last_role.get_memories(k=1)
      last_role_memory_content = last_role_memory[0].content

      return_info = json.loads(last_role_memory_content)
      # print('这里',return_info)
      return_info = {
            "response": return_info["response"],
            # "phrase": return_info["phrase"],
            # "extra_infos": return_info["extra_infos"]
      }
      
      return {"status": "success", "return_info": return_info}

      # except Exception as e:
      #       logger.error(f"Error in generate_data: {str(e)}")
      #       raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
      
      parser = argparse.ArgumentParser()
      parser.add_argument("--port", type=int, default=1001)
      args = parser.parse_args()

      uvicorn.run(app, host="0.0.0.0", port=args.port)
