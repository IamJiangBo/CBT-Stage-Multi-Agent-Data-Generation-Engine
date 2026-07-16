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

from metagpt.schema import Message
from metagpt.context import Context
from metagpt.environment import Environment

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from roles.analyse_conversation_status_role import AnalyseConversationStatusAgent
from roles.analyse_user_profile_role import AnalyseUserProfileAgent
from roles.content_checker_role import ContentCheckerAgent
from roles.dynamic_routing_role import DynamicRoutingAgent
from roles.generate_response_role import GenerateResponseAgent
from metagpt.config2 import Config
from pathlib import Path

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import agent_workflow_logger as logger


class CBTAgentRequest(BaseModel):
      
      user_query: str
      
      history_chat_record: Optional[str] = None
      history_phrase_status: Optional[str] = None
      history_user_profile: Optional[str] = None
      
      conv_k: Optional[int] = 1
      
      confidence_threshold: Optional[int] = 75
      medium_confidence_threshold: Optional[int] = 60
      critical_risk_threshold: Optional[int] = 54
      
      max_loop_times: Optional[int] = 1
      
      conv_uuid: Optional[str] = None
      total_rounds: Optional[int] = 0
      
      output_dir: str = "agent_outputs"
      output_file_name: str = "sft_data.jsonl"
      
      agent_max_react_times: int = 3
      
      timeout: float = 600.0


def init_env(request: CBTAgentRequest):
      
      ## output infos
      show_str = f"""
      *********** cbt agent 系统 ************
      -- agent_max_react_times: {request.agent_max_react_times}
      """
      logger.info(f'{show_str}')
      
      # 初始化环境
      context = Context()
      env = Environment(context=context)

      # 定义角色列表
      role_list = [
            AnalyseConversationStatusAgent(),
            AnalyseUserProfileAgent(),
            GenerateResponseAgent(
                  max_loop_times=request.max_loop_times
            ),
            ContentCheckerAgent(),
            DynamicRoutingAgent(),
      ]
      
      config_path = Path("./config/config2.yaml")
      new_config = Config.from_yaml_file(config_path)
      custom_llm = context.llm_with_cost_manager_from_llm_config(new_config.llm)
      
      for i, role in enumerate(role_list):
            # 设置Role的LLM
            role.set_llm(custom_llm,override=True)
            logger.info(f"custom_llm:{custom_llm.model}\n")
            # 验证Action的LLM设置（Role应该自动设置，这里作为备份）
            for action in role.actions:
                  logger.info(f"Action {action.name} 的LLM：{action.llm.model}")
                  if action.llm != custom_llm:
                        action.set_llm(custom_llm,override=True)
                        logger.info(f"手动设置Action {action.name} 的LLM为{action.llm.model}")
      
      env.add_roles(role_list)
      return env


app = FastAPI()


@app.post("/generate_data")
async def generate_data(request: CBTAgentRequest):

      env = init_env(request)
      logger.info(f"env init done.")

      try:

            send_msg = {
                  "user_query": request.user_query,
                  "history_chat_record": request.history_chat_record,
                  "history_phrase_status": request.history_phrase_status,
                  "history_user_profile": request.history_user_profile,
                  "conv_k": request.conv_k,
                  "conv_uuid": request.conv_uuid,
                  "total_rounds": request.total_rounds,
                  "TIMESTAMP_LOG":[]
            }
            send_msg = json.dumps(send_msg, ensure_ascii=False, indent=4)
            
            env.publish_message(
                  Message(
                        content=send_msg, 
                        send_to=[AnalyseConversationStatusAgent(), AnalyseUserProfileAgent()]
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
                        # env.is_idle = True
                        
                        return {"status": "failed", "message": "数据生成超时"}

            logger.info(f"pipeline finished.")
            
            """ workflow 运行结束之后，获取最后一个角色的最后一次记忆 """
            last_role = list(env.roles.values())[-3]
            last_role_memory = last_role.get_memories(k=1)
            last_role_memory_content = last_role_memory[0].content

            return_info = json.loads(last_role_memory_content)
            
            return_info = {
                  "response": return_info["response"],
                  "phrase": return_info["phrase"],
                  "extra_infos": return_info["extra_infos"]
            }
            
            return {"status": "success", "return_info": return_info}

      except Exception as e:
            logger.error(f"Error in generate_data: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
      
      parser = argparse.ArgumentParser()
      parser.add_argument("--port", type=int, default=8899)
      args = parser.parse_args()
      print(args)
      uvicorn.run(app, host="0.0.0.0", port=args.port)
