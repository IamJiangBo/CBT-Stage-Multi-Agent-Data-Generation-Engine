import os
import sys
import json
import time
import re
from typing import List

from metagpt.schema import Message
from metagpt.const import MESSAGE_ROUTE_TO_NONE
from metagpt.roles.role import RoleReactMode

from .base_role import CBTAbstractRole

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.analyse_user_profile_action import (
    AnalyseUserProfile,
    AnalyseUserProblemType
)

from prompts.analyse_user_profile.requirements import (
      ANALYSE_USER_PROFILE_REQUIREMENTS,
      ANALYSE_USER_PROBLEM_TYPE_REQUIREMENTS
)


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from component.obj.delivery import DeliveryObj

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import analyse_user_profile_logger as logger


class AnalyseUserProfileAgent(CBTAbstractRole):
      name: str = "Analyse User Profile Agent"
      profile: str = "分析用户画像专家"
      max_react_times: int = 3
      
      def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.set_actions([AnalyseUserProfile, AnalyseUserProblemType])
            self._set_react_mode(react_mode=RoleReactMode.BY_ORDER.value)

      async def process_analyse_user_profile(self, todo, REQUIREMENTS, **kwargs):
            
            prompt, response, time_cost = await todo.run(
                  USER_QUERY=kwargs['USER_QUERY'],
                  HISTORY_USER_PROFILE=kwargs['HISTORY_USER_PROFILE'],
                  LAST_ASSISTANT_REPLY=kwargs['LAST_ASSISTANT_REPLY'],
                  REQUIREMENTS=REQUIREMENTS
            )
            
            try:
                  json_str = re.search(r'\{[\s\S]*\}', re.sub(r'^.*?```json\s*|\s*```$', '', response, flags=re.DOTALL)).group(0)
                  response = json.loads(json_str)
                  # response = json.loads(response)
            except Exception as e:
                  response = await self.extract_by_regex(response)
                  response = json.loads(response)
                  
            # response,patient_info,doctor_info, reason = response["response"],response["patient_info"],response["doctor_info"], response["reason"]
            response, reason = response["response"], response["reason"]
            return prompt, response, reason, time_cost
      
      
      async def process_analyse_user_problem_type(self, todo, REQUIREMENTS, **kwargs):
            
            prompt, response, time_cost = await todo.run(
                  USER_QUERY=kwargs['USER_QUERY'],
                  ANALYSE_USER_PROFILE_RESPONSE=kwargs['ANALYSE_USER_PROFILE_RESPONSE'],
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

            logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")

            if isinstance(self.rc.todo, AnalyseUserProfile):
                  
                  logger.info("\033[32m>>> start action: AnalyseUserProfile\033[0m")
                  
                  msg = self.get_memories(k=1)[0]
                  received_infos = json.loads(msg.content)
                  USER_QUERY = received_infos['user_query']
                  HISTORY_PHRASE_STATUS = received_infos['history_phrase_status']
                  HISTORY_CHAT_RECORD = received_infos['history_chat_record']
                  CONV_K = received_infos['conv_k']
                  CONV_UUID = received_infos['conv_uuid']
                  TOTAL_ROUNDS = received_infos['total_rounds']
                  HISTORY_USER_PROFILE = received_infos['history_user_profile'] 
                  
                  ## 读取最新医生回复
                  history = json.loads(HISTORY_CHAT_RECORD)
                  LAST_ASSISTANT_REPLY = history[-1].get("assistant", "") if history else None
                  
                  act_start = time.time()
                  prompt, response, reason, time_cost = await self.process_analyse_user_profile(
                        todo=self.rc.todo, REQUIREMENTS=ANALYSE_USER_PROFILE_REQUIREMENTS,
                        USER_QUERY=USER_QUERY,
                        HISTORY_USER_PROFILE=HISTORY_USER_PROFILE,
                        LAST_ASSISTANT_REPLY = LAST_ASSISTANT_REPLY
                  )
                  act_end = time.time()
                  TIMESTAMP_LOG = received_infos['TIMESTAMP_LOG']
                  TIMESTAMP_LOG.append({f"{self.rc.todo.name}": [act_start,act_end]})
                  
                  CONCAT_INFO = {
                        
                        "USER_QUERY": USER_QUERY,
                        "HISTORY_PHRASE_STATUS": HISTORY_PHRASE_STATUS,
                        "HISTORY_CHAT_RECORD": HISTORY_CHAT_RECORD,
                        "CONV_K": CONV_K,
                        "CONV_UUID": CONV_UUID,
                        "TOTAL_ROUNDS": TOTAL_ROUNDS,
                        
                        "ANALYSE_USER_PROFILE_PROMPT": prompt,
                        "ANALYSE_USER_PROFILE_RESPONSE": response,
                        "ANALYSE_USER_PROFILE_REASON": reason,
                        "ANALYSE_USER_PROFILE_TIME_COST": time_cost,
                        
                        "TIMESTAMP_LOG":TIMESTAMP_LOG
                  }
                  
                  delivery = DeliveryObj()
                  delivery.add_attrs(**CONCAT_INFO)
                  
                  # logger.info(f"\n\n>>> 摘要prompt：\n{prompt}\n\n")
                  logger.info(f"\n\n>>> 多轮对话摘要：\n{response}\n\n判别原因：\n{reason}\n\n")

                  to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, self.name)
                  self.rc.env.publish_message(to_pub_msg)
                  self.rc.memory.add(to_pub_msg)

                  return to_pub_msg
            
            elif isinstance(self.rc.todo, AnalyseUserProblemType):
                  
                  logger.info("\033[32m>>> start action: AnalyseUserProblemType\033[0m")
                  
                  msg = self.get_memories(k=0)
                  msg = await self.get_need_messages(msg, "AnalyseUserProfile")
                  
                  received_infos = json.loads(msg.content)
                  
                  USER_QUERY = received_infos['USER_QUERY']
                  HISTORY_PHRASE_STATUS = received_infos['HISTORY_PHRASE_STATUS']
                  HISTORY_CHAT_RECORD = received_infos['HISTORY_CHAT_RECORD']
                  CONV_K = received_infos['CONV_K']
                  CONV_UUID = received_infos['CONV_UUID']
                  TOTAL_ROUNDS = received_infos['TOTAL_ROUNDS']
                  
                  ANALYSE_USER_PROFILE_PROMPT = received_infos['ANALYSE_USER_PROFILE_PROMPT']
                  ANALYSE_USER_PROFILE_RESPONSE = received_infos['ANALYSE_USER_PROFILE_RESPONSE']
                  ANALYSE_USER_PROFILE_REASON = received_infos['ANALYSE_USER_PROFILE_REASON']
                  ANALYSE_USER_PROFILE_TIME_COST = received_infos['ANALYSE_USER_PROFILE_TIME_COST']
                  
                  act_start = time.time()
                  prompt, response, reason, time_cost = await self.process_analyse_user_problem_type(
                        self.rc.todo, 
                        ANALYSE_USER_PROBLEM_TYPE_REQUIREMENTS,
                        USER_QUERY=USER_QUERY,
                        ANALYSE_USER_PROFILE_RESPONSE=ANALYSE_USER_PROFILE_RESPONSE
                  )
                  act_end = time.time()
                  TIMESTAMP_LOG = received_infos['TIMESTAMP_LOG']
                  TIMESTAMP_LOG.append({f"{self.rc.todo.name}": [act_start,act_end]})
                  
                  CONCAT_INFO = {
                        
                        "USER_QUERY": USER_QUERY,
                        "HISTORY_PHRASE_STATUS": HISTORY_PHRASE_STATUS,
                        "HISTORY_CHAT_RECORD": HISTORY_CHAT_RECORD,
                        "CONV_K": CONV_K,
                        "CONV_UUID": CONV_UUID,
                        "TOTAL_ROUNDS": TOTAL_ROUNDS,
                        
                        "ANALYSE_USER_PROFILE_PROMPT": ANALYSE_USER_PROFILE_PROMPT,
                        "ANALYSE_USER_PROFILE_RESPONSE": ANALYSE_USER_PROFILE_RESPONSE,
                        "ANALYSE_USER_PROFILE_REASON": ANALYSE_USER_PROFILE_REASON,
                        "ANALYSE_USER_PROFILE_TIME_COST": ANALYSE_USER_PROFILE_TIME_COST,
                        
                        "ANALYSE_USER_PROBLEM_TYPE_PROMPT": prompt,
                        "ANALYSE_USER_PROBLEM_TYPE_RESPONSE": response,
                        "ANALYSE_USER_PROBLEM_TYPE_REASON": reason,
                        "ANALYSE_USER_PROBLEM_TYPE_TIME_COST": time_cost,
                        
                        "TIMESTAMP_LOG":TIMESTAMP_LOG
                  }
                  
                  delivery = DeliveryObj()
                  delivery.add_attrs(**CONCAT_INFO)
                  
                  logger.info(f"\n\n>>> 用户问题类型：\n{response}\n\n判别原因：\n{reason}\n\n")
                  
                  to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, "GenerateResponseAgent")
                  self.rc.env.publish_message(to_pub_msg)
                  self.rc.memory.add(to_pub_msg)
                  
                  return to_pub_msg
