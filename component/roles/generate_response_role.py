import os
import sys
import json
import time

from typing import List, Optional, Dict

from metagpt.schema import Message
from metagpt.const import MESSAGE_ROUTE_TO_NONE
from metagpt.roles.role import Role, RoleReactMode

from .base_role import CBTAbstractRole

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from component.obj.delivery import DeliveryObj

from component.actions.analyse_user_profile_action import (
      AnalyseUserProblemType
)

from component.actions.analyse_conversation_status_action import (
      AnalyseConversationStatus
)

from component.prompts.generate_response.requirements import (
      STATUS_REQUIREMENTS_LIST,
      GENERATE_RESPONSE_REQUIREMENTS,
      RE_GENERATE_RESPONSE_REQUIREMENTS
)

from component.actions.dynamic_routing_action import (
      SeekingForAdvices
)

from component.actions.generate_response_action import (
      GenerateResponse
)

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import generate_response_logger as logger


class GenerateResponseAgent(CBTAbstractRole):
      name: str = "GenerateResponseAgent"
      profile: str = "生成响应的智能体"
      max_react_times: int = 3
      max_loop_times: int = 3

      def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.set_actions([GenerateResponse])
            self._watch([AnalyseUserProblemType, AnalyseConversationStatus, SeekingForAdvices])

      async def process_generate_response(self, todo, REQUIREMENTS, **kwargs):        
            prompt, response, time_cost = await todo.run(
                  PROBLEM_TYPE=kwargs['PROBLEM_TYPE'],
                  PHRASE_TYPE=kwargs['PHRASE_TYPE'],
                  USER_PROFILE=kwargs['USER_PROFILE'],
                  HISTORY_CHAT_RECORD=kwargs['HISTORY_CHAT_RECORD'],
                  USER_QUERY=kwargs['USER_QUERY'],
                  REQUIREMENTS=REQUIREMENTS,
                  STATUS_REQUIREMENTS = kwargs['STATUS_REQUIREMENTS'],
                  IS_REWRITE=kwargs['IS_REWRITE'],
                  DRAFT_RESPONSE=kwargs.get('DRAFT_RESPONSE', None),
                  RESPONSE_EVALUATION=kwargs.get('RESPONSE_EVALUATION', None),
                  RESPONSE_EVALUATION_REASON=kwargs.get('RESPONSE_EVALUATION_REASON', None),
                  EXPERT_FEEDBACK=kwargs.get('EXPERT_FEEDBACK', None)
            )
      
            try:
                  response = json.loads(response)
            except Exception as e:
                  response = await self.extract_by_regex(response)
                  response = json.loads(response)
            
            response, reason = response["response"], response["reason"]
            
            return prompt, response, reason, time_cost
      
      async def process_seeking_for_advices(self, todo, **kwargs):
            prompt, response, time_cost = await todo.run(
                  **kwargs
            )
            return prompt, response, time_cost
      
      """ think next movement """
      async def _think_next_action(self):
            """ 思考下一步动作 """
            msg = self.get_memories(k=0)
            advices_msg = await self.get_need_messages(msg, 'SeekingForAdvices', k=3)
            if len(advices_msg) > 0:
                  logger.info(f"判断是否需要进入循环过程。")
                  advices_msg = advices_msg[-1]
                  advices_msg = json.loads(advices_msg.content)
                  advices_response = advices_msg['SEEKING_FOR_ADVICES_RESPONSE']
                  return advices_response
            else:
                  logger.info("未进入循环过程。")
                  return None
      
      async def _act(self) -> Message:
            
            logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
            
            advices_response = await self._think_next_action()
            if advices_response is not None:
                  
                  logger.info("\033[32m>>> start action: RE-GenerateResponse\033[0m")
                  
                  IS_REWRITE = True
                  
                  msg = self.get_memories(k=0)
                  msg = await self.get_need_messages(msg, 'SeekingForAdvices')
                  
                  received_infos = json.loads(msg.content)
                  
                  USER_QUERY = received_infos['USER_QUERY']
                  HISTORY_CHAT_RECORD = received_infos['HISTORY_CHAT_RECORD']
                  HISTORY_PHRASE_STATUS = received_infos['HISTORY_PHRASE_STATUS']
                  CONV_K = received_infos['CONV_K']
                  CONV_UUID = received_infos['CONV_UUID']
                  TOTAL_ROUNDS = received_infos['TOTAL_ROUNDS']
                  
                  ANALYSE_USER_PROFILE_PROMPT = received_infos['ANALYSE_USER_PROFILE_PROMPT']
                  ANALYSE_USER_PROFILE_RESPONSE = received_infos['ANALYSE_USER_PROFILE_RESPONSE']
                  ANALYSE_USER_PROFILE_REASON = received_infos['ANALYSE_USER_PROFILE_REASON']
                  ANALYSE_USER_PROFILE_TIME_COST = received_infos['ANALYSE_USER_PROFILE_TIME_COST']
                  
                  ANALYSE_USER_PROBLEM_TYPE_PROMPT = received_infos['ANALYSE_USER_PROBLEM_TYPE_PROMPT']
                  ANALYSE_USER_PROBLEM_TYPE_RESPONSE = received_infos['ANALYSE_USER_PROBLEM_TYPE_RESPONSE']
                  ANALYSE_USER_PROBLEM_TYPE_REASON = received_infos['ANALYSE_USER_PROBLEM_TYPE_REASON']
                  ANALYSE_USER_PROBLEM_TYPE_TIME_COST = received_infos['ANALYSE_USER_PROBLEM_TYPE_TIME_COST']
                  
                  ANALYSE_CONVERSATION_STATUS_PROMPT = received_infos['ANALYSE_CONVERSATION_STATUS_PROMPT']
                  ANALYSE_CONVERSATION_STATUS_RESPONSE = received_infos['ANALYSE_CONVERSATION_STATUS_RESPONSE']
                  ANALYSE_USER_EMOTION_RESPONSE = received_infos['ANALYSE_USER_EMOTION_RESPONSE']
                  ANALYSE_CONVERSATION_STATUS_REASON = received_infos['ANALYSE_CONVERSATION_STATUS_REASON']
                  ANALYSE_CONVERSATION_STATUS_TIME_COST = received_infos['ANALYSE_CONVERSATION_STATUS_TIME_COST']
                  
                  GENERATE_DRAFT_RESPONSE_PROMPT = received_infos['GENERATE_DRAFT_RESPONSE_PROMPT']
                  GENERATE_DRAFT_RESPONSE_RESPONSE = received_infos['GENERATE_DRAFT_RESPONSE_RESPONSE']
                  GENERATE_DRAFT_RESPONSE_REASON = received_infos['GENERATE_DRAFT_RESPONSE_REASON']
                  GENERATE_DRAFT_RESPONSE_TIME_COST = received_infos['GENERATE_DRAFT_RESPONSE_TIME_COST']
                  
                  CONTENT_CHECKER_PROMPT = received_infos['CONTENT_CHECKER_PROMPT']
                  CONTENT_CHECKER_RESPONSE = received_infos['CONTENT_CHECKER_RESPONSE']
                  CONTENT_CHECKER_REASON = received_infos['CONTENT_CHECKER_REASON']
                  CONTENT_CHECKER_HISTORY = received_infos['CONTENT_CHECKER_HISTORY']
                  CONTENT_CHECKER_TIME_COST = received_infos['CONTENT_CHECKER_TIME_COST']
                  
                  # 新增：获取生成回复历史记录
                  GENERATE_RESPONSE_HISTORY = received_infos.get('GENERATE_RESPONSE_HISTORY', [])
                  
                  DYNAMIC_ROUTING_PROMPT = received_infos['DYNAMIC_ROUTING_PROMPT']
                  DYNAMIC_ROUTING_RESPONSE = received_infos['DYNAMIC_ROUTING_RESPONSE']
                  DYNAMIC_ROUTING_REASON = received_infos['DYNAMIC_ROUTING_REASON']
                  DYNAMIC_ROUTING_TIME_COST = received_infos['DYNAMIC_ROUTING_TIME_COST']
                  
                  SEEKING_FOR_ADVICES_PROMPT = received_infos['SEEKING_FOR_ADVICES_PROMPT']
                  SEEKING_FOR_ADVICES_RESPONSE = received_infos['SEEKING_FOR_ADVICES_RESPONSE']
                  SEEKING_FOR_ADVICES_REASON = received_infos['SEEKING_FOR_ADVICES_REASON']
                  SEEKING_FOR_ADVICES_TIME_COST = received_infos['SEEKING_FOR_ADVICES_TIME_COST']
                  
                  SEEKING_FOR_ADVICES_HISTORY = received_infos['SEEKING_FOR_ADVICES_HISTORY']

                  CONCAT_INFOS = await self.concat_infos(
                        USER_QUERY=USER_QUERY,
                        HISTORY_CHAT_RECORD=HISTORY_CHAT_RECORD,
                        HISTORY_PHRASE_STATUS=HISTORY_PHRASE_STATUS,
                        CONV_K=CONV_K,
                        CONV_UUID=CONV_UUID,
                        TOTAL_ROUNDS=TOTAL_ROUNDS,
                        
                        ANALYSE_USER_PROFILE_PROMPT=ANALYSE_USER_PROFILE_PROMPT,
                        ANALYSE_USER_PROFILE_RESPONSE=ANALYSE_USER_PROFILE_RESPONSE,
                        ANALYSE_USER_PROFILE_REASON=ANALYSE_USER_PROFILE_REASON,
                        ANALYSE_USER_PROFILE_TIME_COST=ANALYSE_USER_PROFILE_TIME_COST,
                        
                        ANALYSE_USER_PROBLEM_TYPE_PROMPT=ANALYSE_USER_PROBLEM_TYPE_PROMPT,
                        ANALYSE_USER_PROBLEM_TYPE_RESPONSE=ANALYSE_USER_PROBLEM_TYPE_RESPONSE,
                        ANALYSE_USER_PROBLEM_TYPE_REASON=ANALYSE_USER_PROBLEM_TYPE_REASON,
                        ANALYSE_USER_PROBLEM_TYPE_TIME_COST=ANALYSE_USER_PROBLEM_TYPE_TIME_COST,
                        
                        ANALYSE_CONVERSATION_STATUS_PROMPT=ANALYSE_CONVERSATION_STATUS_PROMPT,
                        ANALYSE_CONVERSATION_STATUS_RESPONSE=ANALYSE_CONVERSATION_STATUS_RESPONSE,
                        ANALYSE_USER_EMOTION_RESPONSE = ANALYSE_USER_EMOTION_RESPONSE,
                        ANALYSE_CONVERSATION_STATUS_REASON=ANALYSE_CONVERSATION_STATUS_REASON,
                        ANALYSE_CONVERSATION_STATUS_TIME_COST=ANALYSE_CONVERSATION_STATUS_TIME_COST,
                        
                        GENERATE_DRAFT_RESPONSE_PROMPT=GENERATE_DRAFT_RESPONSE_PROMPT,
                        GENERATE_DRAFT_RESPONSE_RESPONSE=GENERATE_DRAFT_RESPONSE_RESPONSE,
                        GENERATE_DRAFT_RESPONSE_REASON=GENERATE_DRAFT_RESPONSE_REASON,
                        GENERATE_DRAFT_RESPONSE_TIME_COST=GENERATE_DRAFT_RESPONSE_TIME_COST,
                        
                        CONTENT_CHECKER_PROMPT=CONTENT_CHECKER_PROMPT,
                        CONTENT_CHECKER_RESPONSE=CONTENT_CHECKER_RESPONSE,
                        CONTENT_CHECKER_REASON=CONTENT_CHECKER_REASON,
                        CONTENT_CHECKER_HISTORY=CONTENT_CHECKER_HISTORY,
                        CONTENT_CHECKER_TIME_COST=CONTENT_CHECKER_TIME_COST,
                        
                        GENERATE_RESPONSE_HISTORY=GENERATE_RESPONSE_HISTORY,
                        
                        DYNAMIC_ROUTING_PROMPT=DYNAMIC_ROUTING_PROMPT,
                        DYNAMIC_ROUTING_RESPONSE=DYNAMIC_ROUTING_RESPONSE,
                        DYNAMIC_ROUTING_REASON=DYNAMIC_ROUTING_REASON,
                        DYNAMIC_ROUTING_TIME_COST=DYNAMIC_ROUTING_TIME_COST,
                        
                        SEEKING_FOR_ADVICES_PROMPT=SEEKING_FOR_ADVICES_PROMPT,
                        SEEKING_FOR_ADVICES_RESPONSE=SEEKING_FOR_ADVICES_RESPONSE,
                        SEEKING_FOR_ADVICES_REASON=SEEKING_FOR_ADVICES_REASON,
                        SEEKING_FOR_ADVICES_TIME_COST=SEEKING_FOR_ADVICES_TIME_COST,
                        SEEKING_FOR_ADVICES_HISTORY=SEEKING_FOR_ADVICES_HISTORY
                  )
                  
                  GENERATE_FINAL_RESPONSE_RESPONSE = received_infos.get("GENERATE_FINAL_RESPONSE_RESPONSE", "")
                  STATUS_REQUIREMENTS = STATUS_REQUIREMENTS_LIST.get(ANALYSE_CONVERSATION_STATUS_RESPONSE, "")
                  act_start = time.time()
                  prompt, response, reason, time_cost = await self.process_generate_response(
                        todo=self.rc.todo, 
                        REQUIREMENTS=RE_GENERATE_RESPONSE_REQUIREMENTS.format(PHRASE_TYPE=ANALYSE_CONVERSATION_STATUS_RESPONSE),
                        STATUS_REQUIREMENTS = STATUS_REQUIREMENTS,
                        PROBLEM_TYPE=ANALYSE_USER_PROBLEM_TYPE_RESPONSE,
                        PHRASE_TYPE=ANALYSE_CONVERSATION_STATUS_RESPONSE,
                        USER_PROFILE=ANALYSE_USER_PROFILE_RESPONSE,
                        HISTORY_CHAT_RECORD=HISTORY_CHAT_RECORD,
                        USER_QUERY=USER_QUERY,
                        IS_REWRITE=IS_REWRITE,
                        DRAFT_RESPONSE=GENERATE_DRAFT_RESPONSE_RESPONSE if GENERATE_FINAL_RESPONSE_RESPONSE == "" else GENERATE_FINAL_RESPONSE_RESPONSE,
                        RESPONSE_EVALUATION=CONTENT_CHECKER_RESPONSE,
                        RESPONSE_EVALUATION_REASON=CONTENT_CHECKER_REASON,
                        EXPERT_FEEDBACK=SEEKING_FOR_ADVICES_RESPONSE,
                  )
                  act_end = time.time()
                  TIMESTAMP_LOG = received_infos['TIMESTAMP_LOG']
                  TIMESTAMP_LOG.append({f"{self.rc.todo.name}": [act_start,act_end]})
                  
                  CONCAT_INFOS['TIMESTAMP_LOG'] = TIMESTAMP_LOG
                  
                  CONCAT_INFOS['GENERATE_FINAL_RESPONSE_PROMPT'] = prompt
                  CONCAT_INFOS['GENERATE_FINAL_RESPONSE_RESPONSE'] = response
                  CONCAT_INFOS['GENERATE_FINAL_RESPONSE_REASON'] = reason
                  CONCAT_INFOS['GENERATE_FINAL_RESPONSE_TIME_COST'] = time_cost
                  
                  # 新增：将当前回复添加到历史记录中
                  current_response_info = {
                        "response": response,
                        "reason": reason,
                        "time_cost": time_cost,
                  }
                  CONCAT_INFOS['GENERATE_RESPONSE_HISTORY'].append(current_response_info)
                  
                  delivery = DeliveryObj()
                  delivery.add_attrs(**CONCAT_INFOS)

                  logger.info(f"\n\n>>> 重写回复：\n{response}\n\n判别原因：\n{reason}\n\n")
                  
                  LOOP_K = received_infos.get("LOOP_K", 1)
                  logger.info(f"当前循环次数：{LOOP_K}")
                  
                  """ 说明不需要重写了 """
                  if SEEKING_FOR_ADVICES_RESPONSE == "" or LOOP_K >= self.max_loop_times:
                        """ 发送给自己 """
                        
                        if LOOP_K >= self.max_loop_times:
                              logger.info(f"超过最大求助次数，结束思考，直接输出回复。")
                        else:
                              logger.info(f"不需要修改，结束思考，直接输出回复。")
                        
                        CONCAT_INFOS['LOOP_K'] = LOOP_K
                        delivery.add_attrs(LOOP_K=LOOP_K)
                        
                        """ 把结果添加到记忆中 """
                        return_info = {
                              "response": delivery.get_attrs()['GENERATE_FINAL_RESPONSE_RESPONSE'], 
                              "phrase": delivery.get_attrs()['ANALYSE_CONVERSATION_STATUS_RESPONSE'],
                              "extra_infos": CONCAT_INFOS
                        }
                        return_info = json.dumps(return_info, ensure_ascii=False, indent=4)
                        
                        leave_msg = Message(
                              content=return_info,
                              role=self.profile,
                              cause_by=type(self.rc.todo),
                              send_to=MESSAGE_ROUTE_TO_NONE
                        )
                        
                        self.rc.memory.add(leave_msg)
                        
                        """ 保存到sql """
                        await self.save_sft_data(delivery.get_attrs())
                        
                        """ 不需要 return """
                        
                  else:
                        """ 继续循环 """
                        logger.info(f"进入循环过程。")
                        delivery.add_attrs(LOOP_K=LOOP_K)
                        
                        """ 保存到sql """
                        await self.save_sft_data(delivery.get_attrs())
                        
                        delivery.__setattr__('LOOP_K', LOOP_K + 1)
                        to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, "ContentCheckerAgent")

                        self.rc.env.publish_message(to_pub_msg)
                        self.rc.memory.add(to_pub_msg)
                        
                        return to_pub_msg
                  
            else:
                  
                  logger.info("\033[32m>>> start action: GenerateResponse\033[0m")
                  
                  IS_REWRITE = False 
            
                  msg = self.get_memories(k=0)
                  
                  user_problem_type_msg = await self.get_need_messages(msg, 'AnalyseUserProblemType')
                  conversation_status_msg = await self.get_need_messages(msg, 'AnalyseConversationStatus')
                  
                  user_problem_type_received_infos = json.loads(user_problem_type_msg.content)
                  conversation_status_received_infos = json.loads(conversation_status_msg.content)
                  
                  USER_QUERY = user_problem_type_received_infos['USER_QUERY']
                  HISTORY_CHAT_RECORD = user_problem_type_received_infos['HISTORY_CHAT_RECORD']
                  HISTORY_PHRASE_STATUS = user_problem_type_received_infos['HISTORY_PHRASE_STATUS']
                  CONV_K = user_problem_type_received_infos['CONV_K']
                  CONV_UUID = user_problem_type_received_infos['CONV_UUID']
                  TOTAL_ROUNDS = user_problem_type_received_infos['TOTAL_ROUNDS']
                  
                  ANALYSE_USER_PROFILE_PROMPT = user_problem_type_received_infos['ANALYSE_USER_PROFILE_PROMPT']
                  ANALYSE_USER_PROFILE_RESPONSE = user_problem_type_received_infos['ANALYSE_USER_PROFILE_RESPONSE']
                  ANALYSE_USER_PROFILE_REASON = user_problem_type_received_infos['ANALYSE_USER_PROFILE_REASON']
                  ANALYSE_USER_PROFILE_TIME_COST = user_problem_type_received_infos['ANALYSE_USER_PROFILE_TIME_COST']
                        
                  ANALYSE_USER_PROBLEM_TYPE_PROMPT = user_problem_type_received_infos['ANALYSE_USER_PROBLEM_TYPE_PROMPT']
                  ANALYSE_USER_PROBLEM_TYPE_RESPONSE = user_problem_type_received_infos['ANALYSE_USER_PROBLEM_TYPE_RESPONSE']
                  ANALYSE_USER_PROBLEM_TYPE_REASON = user_problem_type_received_infos['ANALYSE_USER_PROBLEM_TYPE_REASON']
                  ANALYSE_USER_PROBLEM_TYPE_TIME_COST = user_problem_type_received_infos['ANALYSE_USER_PROBLEM_TYPE_TIME_COST']
            
                  ANALYSE_CONVERSATION_STATUS_PROMPT = conversation_status_received_infos['ANALYSE_CONVERSATION_STATUS_PROMPT']
                  ANALYSE_CONVERSATION_STATUS_RESPONSE = conversation_status_received_infos['ANALYSE_CONVERSATION_STATUS_RESPONSE']
                  ANALYSE_USER_EMOTION_RESPONSE = conversation_status_received_infos['ANALYSE_USER_EMOTION_RESPONSE']
                  ANALYSE_CONVERSATION_STATUS_REASON = conversation_status_received_infos['ANALYSE_CONVERSATION_STATUS_REASON']
                  ANALYSE_CONVERSATION_STATUS_TIME_COST = conversation_status_received_infos['ANALYSE_CONVERSATION_STATUS_TIME_COST']
                  
                  CONCAT_INFOS = await self.concat_infos(
                        USER_QUERY=USER_QUERY,
                        HISTORY_CHAT_RECORD=HISTORY_CHAT_RECORD,
                        HISTORY_PHRASE_STATUS=HISTORY_PHRASE_STATUS,
                        CONV_K=CONV_K,
                        CONV_UUID=CONV_UUID,
                        TOTAL_ROUNDS=TOTAL_ROUNDS,
                        
                        ANALYSE_USER_PROFILE_PROMPT=ANALYSE_USER_PROFILE_PROMPT,
                        ANALYSE_USER_PROFILE_RESPONSE=ANALYSE_USER_PROFILE_RESPONSE,
                        ANALYSE_USER_PROFILE_REASON=ANALYSE_USER_PROFILE_REASON,
                        ANALYSE_USER_PROFILE_TIME_COST=ANALYSE_USER_PROFILE_TIME_COST,
                        
                        ANALYSE_USER_PROBLEM_TYPE_PROMPT=ANALYSE_USER_PROBLEM_TYPE_PROMPT,
                        ANALYSE_USER_PROBLEM_TYPE_RESPONSE=ANALYSE_USER_PROBLEM_TYPE_RESPONSE,
                        ANALYSE_USER_PROBLEM_TYPE_REASON=ANALYSE_USER_PROBLEM_TYPE_REASON,
                        ANALYSE_USER_PROBLEM_TYPE_TIME_COST=ANALYSE_USER_PROBLEM_TYPE_TIME_COST,
                        
                        ANALYSE_CONVERSATION_STATUS_PROMPT=ANALYSE_CONVERSATION_STATUS_PROMPT,
                        ANALYSE_CONVERSATION_STATUS_RESPONSE=ANALYSE_CONVERSATION_STATUS_RESPONSE,
                        ANALYSE_USER_EMOTION_RESPONSE=ANALYSE_USER_EMOTION_RESPONSE,
                        ANALYSE_CONVERSATION_STATUS_REASON=ANALYSE_CONVERSATION_STATUS_REASON,
                        ANALYSE_CONVERSATION_STATUS_TIME_COST=ANALYSE_CONVERSATION_STATUS_TIME_COST,
                        
                        # 新增：初始化生成回复历史记录
                        GENERATE_RESPONSE_HISTORY=[]
                  )
                  
                  TIMESTAMP_LOG = []
                  for ts in user_problem_type_received_infos['TIMESTAMP_LOG'] + conversation_status_received_infos['TIMESTAMP_LOG']:
                        if ts not in TIMESTAMP_LOG:
                              TIMESTAMP_LOG.append(ts)
                  # TIMESTAMP_LOG = list(dict.fromkeys(TIMESTAMP_LOG_USER_PROBLEM_TYPE+TIMESTAMP_LOG_ANALYSE_CONVERSATION_STATUS))
                  act_start = time.time()
                  STATUS_REQUIREMENTS = STATUS_REQUIREMENTS_LIST.get(ANALYSE_CONVERSATION_STATUS_RESPONSE, "")
                  prompt, response, reason, time_cost = await self.process_generate_response(
                        todo=self.rc.todo, 
                        REQUIREMENTS=GENERATE_RESPONSE_REQUIREMENTS,
                        STATUS_REQUIREMENTS = STATUS_REQUIREMENTS,
                        USER_QUERY=USER_QUERY,
                        HISTORY_CHAT_RECORD=HISTORY_CHAT_RECORD,
                        USER_PROFILE=ANALYSE_USER_PROFILE_RESPONSE,
                        PROBLEM_TYPE=ANALYSE_USER_PROBLEM_TYPE_RESPONSE,
                        PHRASE_TYPE=ANALYSE_CONVERSATION_STATUS_RESPONSE,
                        IS_REWRITE=IS_REWRITE
                  )
                  act_end = time.time()
                  TIMESTAMP_LOG.append({f"{self.rc.todo.name}": [act_start,act_end]})
                  CONCAT_INFOS['TIMESTAMP_LOG'] = TIMESTAMP_LOG
                  
                  CONCAT_INFOS['GENERATE_DRAFT_RESPONSE_PROMPT'] = prompt
                  CONCAT_INFOS['GENERATE_DRAFT_RESPONSE_RESPONSE'] = response
                  CONCAT_INFOS['GENERATE_DRAFT_RESPONSE_REASON'] = reason
                  CONCAT_INFOS['GENERATE_DRAFT_RESPONSE_TIME_COST'] = time_cost
                  
                  # 新增：将当前回复添加到历史记录中
                  current_response_info = {
                        "response": response,
                        "reason": reason,
                        "time_cost": time_cost
                  }
                  CONCAT_INFOS['GENERATE_RESPONSE_HISTORY'].append(current_response_info)
                  
                  delivery = DeliveryObj()
                  delivery.add_attrs(**CONCAT_INFOS)

                  logger.info(f"\n\n>>> 生成回复：\n{response}\n\n判别原因：\n{reason}\n\n")
                  if self.max_loop_times <= 0:
                        logger.info(f"直接使用草稿回复，不调专家")
                        LOOP_K = 0
                        CONCAT_INFOS['LOOP_K'] = LOOP_K
                        delivery.add_attrs(LOOP_K=LOOP_K)
                        """ 把结果添加到记忆中 """
                        return_info = {
                              "response": delivery.get_attrs()['GENERATE_DRAFT_RESPONSE_RESPONSE'], 
                              "phrase": delivery.get_attrs()['ANALYSE_CONVERSATION_STATUS_RESPONSE'],
                              "extra_infos": CONCAT_INFOS
                        }
                        return_info = json.dumps(return_info, ensure_ascii=False, indent=4)
                        leave_msg = Message(
                              content=return_info,
                              role=self.profile,
                              cause_by=type(self.rc.todo),
                              send_to=MESSAGE_ROUTE_TO_NONE
                        )
                        
                        self.rc.memory.add(leave_msg)
                        
                        """ 保存到sql """
                        await self.save_sft_data(delivery.get_attrs())
                  else:
                        to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, "ContentCheckerAgent")
                        self.rc.env.publish_message(to_pub_msg)
                        self.rc.memory.add(to_pub_msg)
                        
                        return to_pub_msg
