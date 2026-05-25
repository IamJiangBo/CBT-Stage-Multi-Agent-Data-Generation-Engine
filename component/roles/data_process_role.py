import os
import sys
import json
import time

from typing import List

from metagpt.schema import Message
from metagpt.const import MESSAGE_ROUTE_TO_NONE
from metagpt.roles.role import RoleReactMode

from .base_role import CBTAbstractRole

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.data_process_action import (
    AnalyseDataProcess,
    AdviceDataProcess,
    CoTDataGenerate
)

from prompts.data_process.requirements import (
      PROCESS_ANALYSE_DATA_REQUIREMENTS,
      PROCESS_ADVICE_DATA_REQUIREMENTS,
      PROCESS_COT_DATA_GENERATE_REQUIREMENTS
)


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from component.obj.delivery import DeliveryObj

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import data_process_logger as logger


class DataProcessAgent(CBTAbstractRole):
      name: str = "Data Process Agent"
      profile: str = "数据处理专家"
      max_react_times: int = 3
      
      def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.set_actions([AnalyseDataProcess, AdviceDataProcess, CoTDataGenerate])
            self._set_react_mode(react_mode=RoleReactMode.BY_ORDER.value)

      async def process_user_analyse_data(self, todo, REQUIREMENTS, **kwargs):
            
            prompt, response, time_cost = await todo.run(
                  ANALYSE_INFO=kwargs['ANALYSE_INFO'],
                  REQUIREMENTS=REQUIREMENTS
            )
            try:
                  response = json.loads(response)
            except Exception as e:
                  response = await self.extract_by_regex(response)
                  response = json.loads(response)
                  
            response, reason = response["response"], response["reason"]
            
            return prompt, response, reason, time_cost
      
      async def process_advice_data(self, todo, REQUIREMENTS, **kwargs):
            
            prompt, response, time_cost = await todo.run(
                  ADVICE_INFO=kwargs['ADVICE_INFO'],
                  REQUIREMENTS=REQUIREMENTS
            )
            
            
            try:
                  response = json.loads(response)
            except Exception as e:
                  response = await self.extract_by_regex(response)
                  response = json.loads(response)
                  
            response, reason = response["response"], response["reason"]
            
            return prompt, response, reason, time_cost
      
      async def process_cot_data(self, todo, REQUIREMENTS, **kwargs):
            
            prompt, response, time_cost = await todo.run(
                  USER_QUERY=kwargs['USER_QUERY'],
                  ANALYSE_INFO=kwargs['ANALYSE_INFO'],
                  ADVICE_INFO=kwargs['ADVICE_INFO'],
                  REQUIREMENTS=REQUIREMENTS
            )
            
            try:
                  response = json.loads(response)
            except Exception as e:
                  response = await self.extract_by_regex(response)
                  response = json.loads(response)
                  
            response, reason = response["response"], response["reason"]
            
            return prompt, response, reason, time_cost
      
      async def _act(self) -> Message:

            # logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")

            if isinstance(self.rc.todo, AnalyseDataProcess):
                  
                  # logger.info("\n\033[32m>>> start action: AnalyseDataProcess\033[0m")
                  
                  msg = self.get_memories(k=1)[0]
            
                  received_infos = json.loads(msg.content)
                  USER_QUERY = received_infos['user_query']
                  ANALYSE_INFO = received_infos['analyse_info']
                  DRAFT_RESPONSE = received_infos['draft_respone']
                  ADVICE_INFO = received_infos['advice_info']
                  CONV_K = received_infos['conv_k']
                  CONV_UUID = received_infos['conv_uuid']
                  TOTAL_ROUNDS = received_infos['total_rounds']
                  logger.info(f"\n\n>>> 输入用户分析信息：\n{ANALYSE_INFO}\n")
                  prompt, response, reason, time_cost = await self.process_user_analyse_data(
                        todo=self.rc.todo, 
                        ANALYSE_INFO=ANALYSE_INFO,
                        REQUIREMENTS=PROCESS_ANALYSE_DATA_REQUIREMENTS
                  )
                  
                  CONCAT_INFO = {
                        
                        "USER_QUERY": USER_QUERY,
                        "ANALYSE_INFO": ANALYSE_INFO,
                        "DRAFT_RESPONSE": DRAFT_RESPONSE,
                        "ADVICE_INFO": ADVICE_INFO,   
                        "CONV_K": CONV_K,
                        "CONV_UUID": CONV_UUID,
                        "TOTAL_ROUNDS": TOTAL_ROUNDS,
                        
                        "ANALYSE_DATA_PROCESS_PROMPT": prompt,
                        "ANALYSE_DATA_PROCESS_RESPONSE": response,
                        "ANALYSE_DATA_PROCESS_REASON": reason,
                        "ANALYSE_DATA_PROCESS_TIME_COST": time_cost
                  }
                  
                  delivery = DeliveryObj()
                  delivery.add_attrs(**CONCAT_INFO)
                  logger.info("\n>>>CONV_UUID: {CONV_UUID}  CONV_K: {CONV_K}\n")
                  logger.info("\n>>>用户提问：\n{USER_QUERY}\n")
                  logger.info(f"\n\n>>> 数据处理结果：\n{response}\n\n判别原因： \n{reason}\n\n")

                  to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, self.name)
                  self.rc.env.publish_message(to_pub_msg)
                  self.rc.memory.add(to_pub_msg)

                  return to_pub_msg
            
            elif isinstance(self.rc.todo, AdviceDataProcess):
                  
                  logger.info("\n\033[32m>>> start action: AdviceDataProcess\033[0m")
                  
                  msg = self.get_memories(k=0)
                  msg = await self.get_need_messages(msg, "AnalyseDataProcess")
                  
                  received_infos = json.loads(msg.content)
                  
                  USER_QUERY = received_infos['USER_QUERY']
                  ANALYSE_INFO = received_infos['ANALYSE_INFO']
                  DRAFT_RESPONSE = received_infos['DRAFT_RESPONSE']
                  ADVICE_INFO = received_infos['ADVICE_INFO']
                  CONV_K = received_infos['CONV_K']
                  CONV_UUID = received_infos['CONV_UUID']
                  TOTAL_ROUNDS = received_infos['TOTAL_ROUNDS']
                  
                  ANALYSE_DATA_PROCESS_PROMPT = received_infos['ANALYSE_DATA_PROCESS_PROMPT']
                  ANALYSE_DATA_PROCESS_RESPONSE = received_infos['ANALYSE_DATA_PROCESS_RESPONSE']
                  ANALYSE_DATA_PROCESS_REASON = received_infos['ANALYSE_DATA_PROCESS_REASON']
                  ANALYSE_DATA_PROCESS_TIME_COST = received_infos['ANALYSE_DATA_PROCESS_TIME_COST']
                  logger.info(f"\n\n>>> 输入建议信息：\n{ADVICE_INFO}\n")
                  prompt, response, reason, time_cost = await self.process_advice_data(
                        todo=self.rc.todo, 
                        ADVICE_INFO=ADVICE_INFO,
                        REQUIREMENTS=PROCESS_ADVICE_DATA_REQUIREMENTS
                  )
                  
                  CONCAT_INFO = {
                        
                        "USER_QUERY": USER_QUERY,
                        "ANALYSE_INFO": ANALYSE_INFO,
                        "DRAFT_RESPONSE": DRAFT_RESPONSE,
                        "ADVICE_INFO": ADVICE_INFO,
                        "CONV_K": CONV_K,
                        "CONV_UUID": CONV_UUID,
                        "TOTAL_ROUNDS": TOTAL_ROUNDS,
                        
                        "ANALYSE_DATA_PROCESS_PROMPT": ANALYSE_DATA_PROCESS_PROMPT,
                        "ANALYSE_DATA_PROCESS_RESPONSE": ANALYSE_DATA_PROCESS_RESPONSE,
                        "ANALYSE_DATA_PROCESS_REASON": ANALYSE_DATA_PROCESS_REASON,
                        "ANALYSE_DATA_PROCESS_TIME_COST": ANALYSE_DATA_PROCESS_TIME_COST,
                        
                        "ADVICE_DATA_PROCESS_PROMPT": prompt,
                        "ADVICE_DATA_PROCESS_RESPONSE": response,
                        "ADVICE_DATA_PROCESS_REASON": reason,
                        "ADVICE_DATA_PROCESS_TIME_COST": time_cost,
                        "response": response
                  }
                  
                  delivery = DeliveryObj()
                  delivery.add_attrs(**CONCAT_INFO)
                  
                  logger.info(f"\n\n>>> 建议信息整合结果：\n{response}\n\n整合说明：\n{reason}\n\n")
                  
                  to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, self.name)
                  self.rc.env.publish_message(to_pub_msg)
                  self.rc.memory.add(to_pub_msg)

                  return to_pub_msg
            
            elif isinstance(self.rc.todo, CoTDataGenerate):
                  
                  logger.info("\n\033[32m>>> start action: CoTDataGenerate\033[0m")
                  
                  msg = self.get_memories(k=0)
                  msg = await self.get_need_messages(msg, "AdviceDataProcess")
                  
                  received_infos = json.loads(msg.content)
                  
                  USER_QUERY = received_infos['USER_QUERY']
                  ANALYSE_INFO = received_infos['ANALYSE_INFO']
                  DRAFT_RESPONSE = received_infos['DRAFT_RESPONSE']
                  ADVICE_INFO = received_infos['ADVICE_INFO']
                  CONV_K = received_infos['CONV_K']
                  CONV_UUID = received_infos['CONV_UUID']
                  TOTAL_ROUNDS = received_infos['TOTAL_ROUNDS']
                  
                  ANALYSE_DATA_PROCESS_PROMPT = received_infos['ANALYSE_DATA_PROCESS_PROMPT']
                  ANALYSE_DATA_PROCESS_RESPONSE = received_infos['ANALYSE_DATA_PROCESS_RESPONSE']
                  ANALYSE_DATA_PROCESS_REASON = received_infos['ANALYSE_DATA_PROCESS_REASON']
                  ANALYSE_DATA_PROCESS_TIME_COST = received_infos['ANALYSE_DATA_PROCESS_TIME_COST']
                  
                  ADVICE_DATA_PROCESS_PROMPT = received_infos['ADVICE_DATA_PROCESS_PROMPT']
                  ADVICE_DATA_PROCESS_RESPONSE = received_infos['ADVICE_DATA_PROCESS_RESPONSE']
                  ADVICE_DATA_PROCESS_REASON = received_infos['ADVICE_DATA_PROCESS_REASON']
                  ADVICE_DATA_PROCESS_TIME_COST = received_infos['ADVICE_DATA_PROCESS_TIME_COST']
                  
                  logger.info(f"\n\n>>> 生成CoT思维链数据：\n用户查询：{USER_QUERY}\n分析信息：{ANALYSE_INFO}\n建议信息：{ADVICE_INFO}\n")
                  
                  prompt, response, reason, time_cost = await self.process_cot_data(
                        todo=self.rc.todo, 
                        USER_QUERY=USER_QUERY,
                        ANALYSE_INFO=ANALYSE_INFO,
                        ADVICE_INFO=ADVICE_INFO,
                        REQUIREMENTS=PROCESS_COT_DATA_GENERATE_REQUIREMENTS
                  )
                  
                  CONCAT_INFO = {
                        
                        "USER_QUERY": USER_QUERY,
                        "ANALYSE_INFO": ANALYSE_INFO,
                        "ADVICE_INFO": ADVICE_INFO,
                        "CONV_K": CONV_K,
                        "CONV_UUID": CONV_UUID,
                        "TOTAL_ROUNDS": TOTAL_ROUNDS,
                        
                        "ANALYSE_DATA_PROCESS_PROMPT": ANALYSE_DATA_PROCESS_PROMPT,
                        "ANALYSE_DATA_PROCESS_RESPONSE": ANALYSE_DATA_PROCESS_RESPONSE,
                        "ANALYSE_DATA_PROCESS_REASON": ANALYSE_DATA_PROCESS_REASON,
                        "ANALYSE_DATA_PROCESS_TIME_COST": ANALYSE_DATA_PROCESS_TIME_COST,
                        
                        "ADVICE_DATA_PROCESS_PROMPT": ADVICE_DATA_PROCESS_PROMPT,
                        "ADVICE_DATA_PROCESS_RESPONSE": ADVICE_DATA_PROCESS_RESPONSE,
                        "ADVICE_DATA_PROCESS_REASON": ADVICE_DATA_PROCESS_REASON,
                        "ADVICE_DATA_PROCESS_TIME_COST": ADVICE_DATA_PROCESS_TIME_COST,
                        
                        "COT_DATA_GENERATE_PROMPT": prompt,
                        "COT_DATA_GENERATE_RESPONSE": response,
                        "COT_DATA_GENERATE_REASON": reason,
                        "COT_DATA_GENERATE_TIME_COST": time_cost,
                        "response": response
                  }
                  
                  delivery = DeliveryObj()
                  delivery.add_attrs(**CONCAT_INFO)

                  logger.info(f"\n\n>>> CoT思维链数据prompt：\n{prompt}\n\n")
                  logger.info(f"\n\n>>> CoT思维链数据生成结果：\n{response}\n\n生成说明：\n{reason}\n\n")
                  
                  to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, self.name)
                  self.rc.env.publish_message(to_pub_msg)
                  self.rc.memory.add(to_pub_msg)
                  
                  return to_pub_msg
            
