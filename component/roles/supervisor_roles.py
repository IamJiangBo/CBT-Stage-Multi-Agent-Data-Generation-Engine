import os
import sys
import json
import time

from typing import List, Dict, Optional

from metagpt.schema import Message
from metagpt.const import MESSAGE_ROUTE_TO_NONE
from metagpt.roles.role import RoleReactMode

from .base_role import CBTAbstractRole

from component.prompts.react.react_prompt import (
      REACT_PROMPT,
      REACT_PROMPT_END
)
from component.prompts.react.react_requirements import (
      REACT_REQUIREMENTS
)

from component.actions.counsellor_actions import DynamicRoutingStrategy

from component.actions.supervisor_actions import (
      
      VerificationAndEmpathy,
      VerificationAndEmpathyCache,
      
      IdentifyKeyIdeasOrBeliefs,
      IdentifyKeyIdeasOrBeliefsCache,
      
      PoseChallengeOrReflect,
      PoseChallengeOrReflectCache,
      
      ProvideStrategiesOrInsights,
      ProvideStrategiesOrInsightsCache,
      
      EncouragementAndAnticipation,
      EncouragementAndAnticipationCache,
      
      RoutingResultsToActions,
      AcceptAllAdvices,
)

from component.prompts.supervisor.supervisor_requirements import (
      VERIFICATIONANDEMPATHY_REQUIREMENTS,
      IDENTIFYKEYIDEASORBELIEFS_REQUIREMENTS,
      POSECHALLENGEORREFLECT_REQUIREMENTS,
      PROVIDESTRATEGIESORINSIGHTS_REQUIREMENTS,
      ENCOURAGEMENTANDANTICIPATION_REQUIREMENTS,
)

from component.actions.supervisor_actions import RewriteResponse
from component.prompts.supervisor.supervisor_requirements import REWRITE_RESPONSE_REQUIREMENTS

from component.obj.delivery import DeliveryObj

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import BaseRoleLogger as logger


"""
验证与同理心、识别关键思想或信念、提出挑战或反思、提供策略或洞察力、鼓励与预见s
"""
class SupervisorsAgent(CBTAbstractRole):
      name: str = "SupervisorsAgent"
      profile: str = "CBT专家"
      max_react_times: int = 3
      max_loop_times: int = 3
      
      def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.set_actions([RoutingResultsToActions, AcceptAllAdvices, RewriteResponse])
            self._watch([DynamicRoutingStrategy])
            self._set_react_mode(react_mode=RoleReactMode.BY_ORDER.value)
            
      async def _planning(self, routing_result):
            todo_actions = []
            for routing_result in routing_result:
                  if routing_result == '验证与同理心专家':
                        todo_actions.append("VerificationAndEmpathy")
                  elif routing_result == '识别关键思想或信念专家':
                        todo_actions.append("IdentifyKeyIdeasOrBeliefs")
                  elif routing_result == '提出挑战或反思专家':
                        todo_actions.append("PoseChallengeOrReflect")
                  elif routing_result == '提供策略或洞察力专家':
                        todo_actions.append("ProvideStrategiesOrInsights")
                  elif routing_result == '鼓励与预见专家':
                        todo_actions.append("EncouragementAndAnticipation")
            return todo_actions
      
      async def receive_experts_result(self, todo, USER_BASIC_INFO, USER_QUERY, DRAFT_RESPONSE, REQUIREMENTS):
            
            start_time = time.time()
            
            now_prompt, now_response = await todo.run(
                  USER_BASIC_INFO=USER_BASIC_INFO,
                  USER_QUERY=USER_QUERY,
                  DRAFT_RESPONSE=DRAFT_RESPONSE,
                  REQUIREMENTS=REQUIREMENTS
            )
            
            try:
                  extract_result = json.loads(now_response)
            except:
                  extract_result = await self.extract_by_regex(now_response)
                  extract_result = json.loads(extract_result)
                  
            now_response = extract_result['response']
            now_reason = extract_result['reason']
            
            end_time = time.time()
            now_time_cost = end_time - start_time
            
            return now_prompt, now_response, now_reason, now_time_cost
      
      async def _act(self) -> Message:
            
            logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
      
            if isinstance(self.rc.todo, RoutingResultsToActions):
                  
                  # logger.info(">>> start action: RoutingResultsToActions")
                  logger.info("\033[32m>>> start action: RoutingResultsToActions\033[0m")
                  
                  msg = self.get_memories(k=0)
                  msg = await self.get_need_messages(msg, 'DynamicRoutingStrategy')
                  
                  content = msg.content
                  content = json.loads(content)
                  
                  USER_QUERY = content['USER_QUERY']
                  HISTORY_CHAT_RECORD = content['HISTORY_CHAT_RECORD']
                  HISTORY_TODO_ACTIONS = content['HISTORY_TODO_ACTIONS']
                  CONV_K = content['CONV_K']
                  CONV_UUID = content['CONV_UUID']
                  TOTAL_ROUNDS = content['TOTAL_ROUNDS']
                  
                  USER_BASIC_INFO = content['USER_BASIC_INFO']
                  USER_BASIC_INFO_GENERATE_REASON = content['USER_BASIC_INFO_GENERATE_REASON']
                  USER_BASIC_INFO_PROMPT = content['USER_BASIC_INFO_PROMPT']
                  USER_BASIC_INFO_GENERATE_TIME_COST = content['USER_BASIC_INFO_GENERATE_TIME_COST']
                  
                  DRAFT_RESPONSE_PROMPT = content['DRAFT_RESPONSE_PROMPT']
                  DRAFT_RESPONSE = content['DRAFT_RESPONSE']
                  DRAFT_RESPONSE_GENERATE_REASON = content['DRAFT_RESPONSE_GENERATE_REASON']
                  DRAFT_RESPONSE_GENERATE_TIME_COST = content['DRAFT_RESPONSE_GENERATE_TIME_COST']
                  
                  PROFESSIONAL_JUDGEMENT_RESPONSE = content['PROFESSIONAL_JUDGEMENT_RESPONSE']
                  PROFESSIONAL_JUDGEMENT_REASON = content['PROFESSIONAL_JUDGEMENT_REASON']
                  PROFESSIONAL_JUDGEMENT_PROMPT = content['PROFESSIONAL_JUDGEMENT_PROMPT']
                  PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST = content['PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST']
                  
                  CONFIDENCE_JUDGEMENT_RESPONSE = content['CONFIDENCE_JUDGEMENT_RESPONSE']
                  CONFIDENCE_JUDGEMENT_REASON = content['CONFIDENCE_JUDGEMENT_REASON']
                  CONFIDENCE_JUDGEMENT_PROMPT = content['CONFIDENCE_JUDGEMENT_PROMPT']
                  CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST = content['CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST']
                  
                  CONVERSATION_MEMORY_JUDGEMENT_RESPONSE = content['CONVERSATION_MEMORY_JUDGEMENT_RESPONSE']
                  CONVERSATION_MEMORY_JUDGEMENT_REASON = content['CONVERSATION_MEMORY_JUDGEMENT_REASON']
                  CONVERSATION_MEMORY_JUDGEMENT_PROMPT = content['CONVERSATION_MEMORY_JUDGEMENT_PROMPT']
                  CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST = content['CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST']
                  
                  ROUTING_RESULT = content['ROUTING_RESULT']
                  ROUTING_RESULT_PROMPT = content['ROUTING_RESULT_PROMPT']
                  ROUTING_RESULT_REASON = content['ROUTING_RESULT_REASON']
                  ROUTING_RESULT_GENERATE_TIME_COST = content['ROUTING_RESULT_GENERATE_TIME_COST']
                  
                  LOOP_K = content['LOOP_K']
                  
                  CONCAT_INFOS = {
                        "USER_QUERY": USER_QUERY,
                        "HISTORY_CHAT_RECORD": HISTORY_CHAT_RECORD,
                        "HISTORY_TODO_ACTIONS": HISTORY_TODO_ACTIONS,
                        "CONV_K": CONV_K,
                        "CONV_UUID": CONV_UUID,
                        "TOTAL_ROUNDS": TOTAL_ROUNDS,
                        
                        "USER_BASIC_INFO": USER_BASIC_INFO,
                        "USER_BASIC_INFO_GENERATE_REASON": USER_BASIC_INFO_GENERATE_REASON,
                        "USER_BASIC_INFO_PROMPT": USER_BASIC_INFO_PROMPT,
                        "USER_BASIC_INFO_GENERATE_TIME_COST": USER_BASIC_INFO_GENERATE_TIME_COST,
                        
                        "DRAFT_RESPONSE_PROMPT": DRAFT_RESPONSE_PROMPT,
                        "DRAFT_RESPONSE": DRAFT_RESPONSE,
                        "DRAFT_RESPONSE_GENERATE_REASON": DRAFT_RESPONSE_GENERATE_REASON,
                        "DRAFT_RESPONSE_GENERATE_TIME_COST": DRAFT_RESPONSE_GENERATE_TIME_COST,
                        
                        "PROFESSIONAL_JUDGEMENT_RESPONSE": PROFESSIONAL_JUDGEMENT_RESPONSE,
                        "PROFESSIONAL_JUDGEMENT_REASON": PROFESSIONAL_JUDGEMENT_REASON,
                        "PROFESSIONAL_JUDGEMENT_PROMPT": PROFESSIONAL_JUDGEMENT_PROMPT,
                        "PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST": PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST,
                        
                        "CONFIDENCE_JUDGEMENT_RESPONSE": CONFIDENCE_JUDGEMENT_RESPONSE,
                        "CONFIDENCE_JUDGEMENT_REASON": CONFIDENCE_JUDGEMENT_REASON,
                        "CONFIDENCE_JUDGEMENT_PROMPT": CONFIDENCE_JUDGEMENT_PROMPT,
                        "CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST": CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST,
                        
                        "CONVERSATION_MEMORY_JUDGEMENT_RESPONSE": CONVERSATION_MEMORY_JUDGEMENT_RESPONSE,
                        "CONVERSATION_MEMORY_JUDGEMENT_REASON": CONVERSATION_MEMORY_JUDGEMENT_REASON,
                        "CONVERSATION_MEMORY_JUDGEMENT_PROMPT": CONVERSATION_MEMORY_JUDGEMENT_PROMPT,
                        "CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST": CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST,
                        
                        "ROUTING_RESULT": ROUTING_RESULT,
                        "ROUTING_RESULT_PROMPT": ROUTING_RESULT_PROMPT,
                        "ROUTING_RESULT_REASON": ROUTING_RESULT_REASON,
                        "ROUTING_RESULT_GENERATE_TIME_COST": ROUTING_RESULT_GENERATE_TIME_COST,
                        
                        "LOOP_K": LOOP_K
                  }
                  
                  routing_result = await self.rc.todo.run(routing_result=ROUTING_RESULT)
                  todo_actions = await self._planning(routing_result)
                  
                  delivery = DeliveryObj()
                  delivery.add_attrs(**CONCAT_INFOS)
                  delivery.add_attrs(todo_actions=todo_actions)
                  to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, self.name)
                  
                  self.rc.env.publish_message(to_pub_msg)
                  self.rc.memory.add(to_pub_msg)
                  
                  return to_pub_msg

            elif isinstance(self.rc.todo, AcceptAllAdvices):

                  # logger.info(">>> start action: AcceptAllAdvices")
                  logger.info("\033[32m>>> start action: AcceptAllAdvices\033[0m")
                  
                  msg = self.get_memories(k=0)
                  
                  msg = await self.get_need_messages(msg, 'RoutingResultsToActions')
                  content = msg.content
                  content = json.loads(content)
                  
                  USER_QUERY = content['USER_QUERY']
                  HISTORY_CHAT_RECORD = content['HISTORY_CHAT_RECORD']
                  HISTORY_TODO_ACTIONS = content['HISTORY_TODO_ACTIONS']
                  CONV_K = content['CONV_K']
                  CONV_UUID = content['CONV_UUID']
                  TOTAL_ROUNDS = content['TOTAL_ROUNDS']
                  
                  USER_BASIC_INFO = content['USER_BASIC_INFO']
                  USER_BASIC_INFO_GENERATE_REASON = content['USER_BASIC_INFO_GENERATE_REASON']
                  USER_BASIC_INFO_PROMPT = content['USER_BASIC_INFO_PROMPT']
                  USER_BASIC_INFO_GENERATE_TIME_COST = content['USER_BASIC_INFO_GENERATE_TIME_COST']
                  
                  DRAFT_RESPONSE_PROMPT = content['DRAFT_RESPONSE_PROMPT']
                  DRAFT_RESPONSE = content['DRAFT_RESPONSE']
                  DRAFT_RESPONSE_GENERATE_REASON = content['DRAFT_RESPONSE_GENERATE_REASON']
                  DRAFT_RESPONSE_GENERATE_TIME_COST = content['DRAFT_RESPONSE_GENERATE_TIME_COST']
                  
                  PROFESSIONAL_JUDGEMENT_RESPONSE = content['PROFESSIONAL_JUDGEMENT_RESPONSE']
                  PROFESSIONAL_JUDGEMENT_REASON = content['PROFESSIONAL_JUDGEMENT_REASON']
                  PROFESSIONAL_JUDGEMENT_PROMPT = content['PROFESSIONAL_JUDGEMENT_PROMPT']
                  PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST = content['PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST']
                  
                  CONFIDENCE_JUDGEMENT_RESPONSE = content['CONFIDENCE_JUDGEMENT_RESPONSE']
                  CONFIDENCE_JUDGEMENT_REASON = content['CONFIDENCE_JUDGEMENT_REASON']
                  CONFIDENCE_JUDGEMENT_PROMPT = content['CONFIDENCE_JUDGEMENT_PROMPT']
                  CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST = content['CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST']
                  
                  CONVERSATION_MEMORY_JUDGEMENT_RESPONSE = content['CONVERSATION_MEMORY_JUDGEMENT_RESPONSE']
                  CONVERSATION_MEMORY_JUDGEMENT_REASON = content['CONVERSATION_MEMORY_JUDGEMENT_REASON']
                  CONVERSATION_MEMORY_JUDGEMENT_PROMPT = content['CONVERSATION_MEMORY_JUDGEMENT_PROMPT']
                  CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST = content['CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST']
                  
                  ROUTING_RESULT = content['ROUTING_RESULT']
                  ROUTING_RESULT_PROMPT = content['ROUTING_RESULT_PROMPT']
                  ROUTING_RESULT_REASON = content['ROUTING_RESULT_REASON']
                  ROUTING_RESULT_GENERATE_TIME_COST = content['ROUTING_RESULT_GENERATE_TIME_COST']
                  
                  LOOP_K = content['LOOP_K']
                  
                  todo_actions = content.get('todo_actions', [])
                  
                  CONCAT_INFOS = {
                        "USER_QUERY": USER_QUERY,
                        "HISTORY_CHAT_RECORD": HISTORY_CHAT_RECORD,
                        "HISTORY_TODO_ACTIONS": HISTORY_TODO_ACTIONS,
                        "CONV_K": CONV_K,
                        "CONV_UUID": CONV_UUID,
                        "TOTAL_ROUNDS": TOTAL_ROUNDS,
                        
                        "USER_BASIC_INFO": USER_BASIC_INFO,
                        "USER_BASIC_INFO_GENERATE_REASON": USER_BASIC_INFO_GENERATE_REASON,
                        "USER_BASIC_INFO_PROMPT": USER_BASIC_INFO_PROMPT,
                        "USER_BASIC_INFO_GENERATE_TIME_COST": USER_BASIC_INFO_GENERATE_TIME_COST,
                        
                        "DRAFT_RESPONSE_PROMPT": DRAFT_RESPONSE_PROMPT,
                        "DRAFT_RESPONSE": DRAFT_RESPONSE,
                        "DRAFT_RESPONSE_GENERATE_REASON": DRAFT_RESPONSE_GENERATE_REASON,
                        "DRAFT_RESPONSE_GENERATE_TIME_COST": DRAFT_RESPONSE_GENERATE_TIME_COST,
                        
                        "PROFESSIONAL_JUDGEMENT_RESPONSE": PROFESSIONAL_JUDGEMENT_RESPONSE,
                        "PROFESSIONAL_JUDGEMENT_REASON": PROFESSIONAL_JUDGEMENT_REASON,
                        "PROFESSIONAL_JUDGEMENT_PROMPT": PROFESSIONAL_JUDGEMENT_PROMPT,
                        "PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST": PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST,
                        
                        "CONFIDENCE_JUDGEMENT_RESPONSE": CONFIDENCE_JUDGEMENT_RESPONSE,
                        "CONFIDENCE_JUDGEMENT_REASON": CONFIDENCE_JUDGEMENT_REASON,
                        "CONFIDENCE_JUDGEMENT_PROMPT": CONFIDENCE_JUDGEMENT_PROMPT,
                        "CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST": CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST,
                        
                        "CONVERSATION_MEMORY_JUDGEMENT_RESPONSE": CONVERSATION_MEMORY_JUDGEMENT_RESPONSE,
                        "CONVERSATION_MEMORY_JUDGEMENT_REASON": CONVERSATION_MEMORY_JUDGEMENT_REASON,
                        "CONVERSATION_MEMORY_JUDGEMENT_PROMPT": CONVERSATION_MEMORY_JUDGEMENT_PROMPT,
                        "CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST": CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST,
                        
                        "ROUTING_RESULT": ROUTING_RESULT,
                        "ROUTING_RESULT_PROMPT": ROUTING_RESULT_PROMPT,
                        "ROUTING_RESULT_REASON": ROUTING_RESULT_REASON,
                        "ROUTING_RESULT_GENERATE_TIME_COST": ROUTING_RESULT_GENERATE_TIME_COST,
                        
                        "LOOP_K": LOOP_K,
                        
                        "todo_actions": todo_actions
                  }
                  
                  
                  logger.info(f">>> 选择的专家列表为：\n{todo_actions}")
                  
                  start_time = time.time()
                  
                  if len(todo_actions) == 0:
                        all_experts_response_map = {}
                  else:
                        todo_actions_map = dict.fromkeys(todo_actions)
                        
                        for todo_action in todo_actions:
                              
                              if todo_action == "VerificationAndEmpathy":
                                    now_todo = VerificationAndEmpathy()
                                    now_prompt, now_response, now_reason, now_time_cost = await self.receive_experts_result(
                                          now_todo, 
                                          USER_BASIC_INFO, USER_QUERY, DRAFT_RESPONSE, 
                                          VERIFICATIONANDEMPATHY_REQUIREMENTS
                                    )
      
                              elif todo_action == "IdentifyKeyIdeasOrBeliefs":
                                    now_todo = IdentifyKeyIdeasOrBeliefs()
                                    now_prompt, now_response, now_reason, now_time_cost = await self.receive_experts_result(
                                          now_todo, 
                                          USER_BASIC_INFO, USER_QUERY, DRAFT_RESPONSE, 
                                          IDENTIFYKEYIDEASORBELIEFS_REQUIREMENTS
                                    )
                                    
                              elif todo_action == "PoseChallengeOrReflect":
                                    now_todo = PoseChallengeOrReflect()
                                    now_prompt, now_response, now_reason, now_time_cost = await self.receive_experts_result(
                                          now_todo, 
                                          USER_BASIC_INFO, USER_QUERY, DRAFT_RESPONSE, 
                                          POSECHALLENGEORREFLECT_REQUIREMENTS
                                    )
                                    
                              elif todo_action == "ProvideStrategiesOrInsights":
                                    now_todo = ProvideStrategiesOrInsights()
                                    now_prompt, now_response, now_reason, now_time_cost = await self.receive_experts_result(
                                          now_todo, 
                                          USER_BASIC_INFO, USER_QUERY, DRAFT_RESPONSE, 
                                          PROVIDESTRATEGIESORINSIGHTS_REQUIREMENTS
                                    )
                                    
                              elif todo_action == "EncouragementAndAnticipation":
                                    now_todo = EncouragementAndAnticipation()
                                    now_prompt, now_response, now_reason, now_time_cost = await self.receive_experts_result(
                                          now_todo, 
                                          USER_BASIC_INFO, USER_QUERY, DRAFT_RESPONSE, 
                                          ENCOURAGEMENTANDANTICIPATION_REQUIREMENTS
                                    )
                                    
                              todo_actions_map[todo_action] = {
                                    "RESULT": now_response,
                                    "REASON": now_reason,
                                    "PROMPT": now_prompt,
                                    "TIME_COST": now_time_cost
                              }
                              
                        all_experts_response_map = todo_actions_map
                  
                  end_time = time.time()
                  experts_generation_time_cost = end_time - start_time
                  
                  delivery = DeliveryObj()
                  delivery.add_attrs(**CONCAT_INFOS)
                  delivery.add_attrs(ALL_ADVICES=all_experts_response_map, ALL_ADVICES_GENERATE_TIME_COST=experts_generation_time_cost)
                  to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, self.name)

                  self.rc.env.publish_message(to_pub_msg)
                  self.rc.memory.add(to_pub_msg)

                  return to_pub_msg
            
            elif isinstance(self.rc.todo, RewriteResponse):
                  
                  # logger.info(">>> start action: RewriteResponse")
                  logger.info("\033[32m>>> start action: RewriteResponse\033[0m")
                  
                  msg = self.get_memories(k=0)
                  
                  msg = await self.get_need_messages(msg, 'AcceptAllAdvices')
                  
                  content = msg.content
                  content = json.loads(content)
                  
                  USER_QUERY = content['USER_QUERY']
                  HISTORY_CHAT_RECORD = content['HISTORY_CHAT_RECORD']
                  HISTORY_TODO_ACTIONS = content['HISTORY_TODO_ACTIONS']
                  CONV_K = content['CONV_K']
                  CONV_UUID = content['CONV_UUID']
                  TOTAL_ROUNDS = content['TOTAL_ROUNDS']
                  
                  USER_BASIC_INFO = content['USER_BASIC_INFO']
                  USER_BASIC_INFO_GENERATE_REASON = content['USER_BASIC_INFO_GENERATE_REASON']
                  USER_BASIC_INFO_PROMPT = content['USER_BASIC_INFO_PROMPT']
                  USER_BASIC_INFO_GENERATE_TIME_COST = content['USER_BASIC_INFO_GENERATE_TIME_COST']
                  
                  DRAFT_RESPONSE_PROMPT = content['DRAFT_RESPONSE_PROMPT']
                  DRAFT_RESPONSE = content['DRAFT_RESPONSE']
                  DRAFT_RESPONSE_GENERATE_REASON = content['DRAFT_RESPONSE_GENERATE_REASON']
                  DRAFT_RESPONSE_GENERATE_TIME_COST = content['DRAFT_RESPONSE_GENERATE_TIME_COST']
                  
                  PROFESSIONAL_JUDGEMENT_RESPONSE = content['PROFESSIONAL_JUDGEMENT_RESPONSE']
                  PROFESSIONAL_JUDGEMENT_REASON = content['PROFESSIONAL_JUDGEMENT_REASON']
                  PROFESSIONAL_JUDGEMENT_PROMPT = content['PROFESSIONAL_JUDGEMENT_PROMPT']
                  PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST = content['PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST']
                  
                  CONFIDENCE_JUDGEMENT_RESPONSE = content['CONFIDENCE_JUDGEMENT_RESPONSE']
                  CONFIDENCE_JUDGEMENT_REASON = content['CONFIDENCE_JUDGEMENT_REASON']
                  CONFIDENCE_JUDGEMENT_PROMPT = content['CONFIDENCE_JUDGEMENT_PROMPT']
                  CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST = content['CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST']
                  
                  CONVERSATION_MEMORY_JUDGEMENT_RESPONSE = content['CONVERSATION_MEMORY_JUDGEMENT_RESPONSE']
                  CONVERSATION_MEMORY_JUDGEMENT_REASON = content['CONVERSATION_MEMORY_JUDGEMENT_REASON']
                  CONVERSATION_MEMORY_JUDGEMENT_PROMPT = content['CONVERSATION_MEMORY_JUDGEMENT_PROMPT']
                  CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST = content['CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST']
                  
                  ROUTING_RESULT = content['ROUTING_RESULT']
                  ROUTING_RESULT_PROMPT = content['ROUTING_RESULT_PROMPT']
                  ROUTING_RESULT_REASON = content['ROUTING_RESULT_REASON']
                  ROUTING_RESULT_GENERATE_TIME_COST = content['ROUTING_RESULT_GENERATE_TIME_COST']
                  
                  todo_actions = content['todo_actions']
                  
                  ALL_ADVICES = content['ALL_ADVICES']
                  ALL_ADVICES_GENERATE_TIME_COST = content['ALL_ADVICES_GENERATE_TIME_COST']
                  
                  LOOP_K = content['LOOP_K']
                  
                  CONCAT_INFOS = {
                        "USER_QUERY": USER_QUERY,
                        "HISTORY_CHAT_RECORD": HISTORY_CHAT_RECORD,
                        "HISTORY_TODO_ACTIONS": HISTORY_TODO_ACTIONS,
                        "CONV_K": CONV_K,
                        "CONV_UUID": CONV_UUID,
                        "TOTAL_ROUNDS": TOTAL_ROUNDS,
                        
                        "USER_BASIC_INFO": USER_BASIC_INFO,
                        "USER_BASIC_INFO_GENERATE_REASON": USER_BASIC_INFO_GENERATE_REASON,
                        "USER_BASIC_INFO_PROMPT": USER_BASIC_INFO_PROMPT,
                        "USER_BASIC_INFO_GENERATE_TIME_COST": USER_BASIC_INFO_GENERATE_TIME_COST,
                        
                        "DRAFT_RESPONSE_PROMPT": DRAFT_RESPONSE_PROMPT,
                        "DRAFT_RESPONSE": DRAFT_RESPONSE,
                        "DRAFT_RESPONSE_GENERATE_REASON": DRAFT_RESPONSE_GENERATE_REASON,
                        "DRAFT_RESPONSE_GENERATE_TIME_COST": DRAFT_RESPONSE_GENERATE_TIME_COST,

                        "PROFESSIONAL_JUDGEMENT_RESPONSE": PROFESSIONAL_JUDGEMENT_RESPONSE,
                        "PROFESSIONAL_JUDGEMENT_REASON": PROFESSIONAL_JUDGEMENT_REASON,
                        "PROFESSIONAL_JUDGEMENT_PROMPT": PROFESSIONAL_JUDGEMENT_PROMPT,
                        "PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST": PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST,
                        
                        "CONFIDENCE_JUDGEMENT_RESPONSE": CONFIDENCE_JUDGEMENT_RESPONSE,
                        "CONFIDENCE_JUDGEMENT_REASON": CONFIDENCE_JUDGEMENT_REASON,
                        "CONFIDENCE_JUDGEMENT_PROMPT": CONFIDENCE_JUDGEMENT_PROMPT,
                        "CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST": CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST,
                        
                        "CONVERSATION_MEMORY_JUDGEMENT_RESPONSE": CONVERSATION_MEMORY_JUDGEMENT_RESPONSE,
                        "CONVERSATION_MEMORY_JUDGEMENT_REASON": CONVERSATION_MEMORY_JUDGEMENT_REASON,
                        "CONVERSATION_MEMORY_JUDGEMENT_PROMPT": CONVERSATION_MEMORY_JUDGEMENT_PROMPT,
                        "CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST": CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST,
                        
                        "ROUTING_RESULT": ROUTING_RESULT,
                        "ROUTING_RESULT_PROMPT": ROUTING_RESULT_PROMPT,
                        "ROUTING_RESULT_REASON": ROUTING_RESULT_REASON,
                        "ROUTING_RESULT_GENERATE_TIME_COST": ROUTING_RESULT_GENERATE_TIME_COST,
                        
                        "todo_actions": todo_actions,
                        
                        "ALL_ADVICES": ALL_ADVICES,
                        "ALL_ADVICES_GENERATE_TIME_COST": ALL_ADVICES_GENERATE_TIME_COST
                  }
                  
                  if ALL_ADVICES == {}:
                        
                        """ 当没有专家建议时，使用草稿回复 """
                        response = DRAFT_RESPONSE
                        reason = DRAFT_RESPONSE_GENERATE_REASON
                        prompt = DRAFT_RESPONSE_PROMPT
                        rewrite_response_time_cost = 0
                        
                        send_to = None
                        
                        delivery = DeliveryObj()
                        delivery.add_attrs(**CONCAT_INFOS)
                        delivery.add_attrs(
                              REWRITE_RESPONSE=response, REWRITE_RESPONSE_GENERATE_REASON=reason, 
                              REWRITE_RESPONSE_PROMPT=prompt, REWRITE_RESPONSE_GENERATE_TIME_COST=rewrite_response_time_cost,
                              LOOP_K=LOOP_K + 1 if LOOP_K != -1 else 1
                        )
                        
                        to_pub_msg = self.dummy_message

                  else:
                        all_advices_str = ""
                        for k, v in ALL_ADVICES.items():
                              all_advices_str += f"{k}: \n{v['RESULT']}\n"
                        
                        start_time = time.time()
                        
                        prompt, response = await self.rc.todo.run(
                              USER_BASIC_INFO=USER_BASIC_INFO,
                              USER_QUERY=USER_QUERY,
                              DRAFT_RESPONSE=DRAFT_RESPONSE,
                              ADVICES=all_advices_str,
                              REQUIREMENTS=REWRITE_RESPONSE_REQUIREMENTS
                        )
                        
                        try:
                              extract_result = json.loads(response)
                        except:
                              extract_result = await self.extract_by_regex(response)
                              extract_result = json.loads(extract_result)
                        
                        response = extract_result['response']
                        reason = extract_result['reason']
                        
                        end_time = time.time()
                        rewrite_response_time_cost = end_time - start_time
                        
                        send_to = "CounsellorAgent"
                        
                        delivery = DeliveryObj()
                        delivery.add_attrs(**CONCAT_INFOS)
                        delivery.add_attrs(
                              REWRITE_RESPONSE=response, REWRITE_RESPONSE_GENERATE_REASON=reason, 
                              REWRITE_RESPONSE_PROMPT=prompt, REWRITE_RESPONSE_GENERATE_TIME_COST=rewrite_response_time_cost,
                              LOOP_K=LOOP_K + 1 if LOOP_K != -1 else 1
                        )
                        
                        if LOOP_K == self.max_loop_times:
                              to_pub_msg = self.dummy_message
                              logger.info(f"\033[31m>>> 循环次数大于{self.max_loop_times}，不再继续循环\033[0m")
                        else:
                              to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, send_to)
                              self.rc.env.publish_message(to_pub_msg)
                              self.rc.memory.add(to_pub_msg)
                  
                  logger.info(f"\n\nnow conv_uuid: {CONV_UUID}, CONV_K: {CONV_K}, total_rounds: {TOTAL_ROUNDS}, \n response: {response}\n\n")
                  
                  await self.save_sft_data(delivery.get_attrs())

                  """ 把结果添加到记忆中 """
                  return_info = {
                        "response": delivery.get_attrs()['REWRITE_RESPONSE'], 
                        "todo_actions": delivery.get_attrs()['todo_actions']
                  }
                  return_info = json.dumps(return_info, ensure_ascii=False, indent=4)
                  self.rc.memory.add(
                        Message(
                              content=return_info,
                              role=self.profile,
                              cause_by=type(self.rc.todo),
                              send_to=MESSAGE_ROUTE_TO_NONE
                        )
                  )
                  
                  return to_pub_msg
