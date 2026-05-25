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

from component.actions.analyse_action import (
      AnalyseUserInfo
)
from component.actions.counsellor_actions import (
      
      DraftResponseGeneration,
      DraftResponseGenerationCache,
      
      DynamicRoutingStrategy,
      DynamicRoutingStrategyCache
      
)

from component.prompts.counsellor.counsellor_prompts import (
      DynamicRoutingStrategy_PROMPT,
      DynamicRoutingStrategy_PROMPT_END
)

from component.prompts.counsellor.counsellor_requirements import (
      DRAFT_RESPONSE_REQUIREMENTS,
      DRAFTRESPONSEGENERATION_NEW_REQUIREMENTS,
      DYNAMIC_ROUTING_REQUIREMENTS
)


from component.prompts.react.react_prompt import (
      REACT_PROMPT, 
      REACT_PROMPT_END
)
from component.prompts.react.react_requirements import (
      REACT_REQUIREMENTS
)

from component.actions.supervisor_actions import RewriteResponse

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import BaseRoleLogger as logger


class CounsellorAgent(CBTAbstractRole):
      name: str = "CounsellorAgent"
      profile: str = "与用户直接交互的智能体, ·咨询专家·"
      max_react_times: int = 3
      CONFIDENCE_THRESHOLD: int = 75
      MEDIUM_CONFIDENCE_THRESHOLD: int = 60
      CRITICAL_RISK_THRESHOLD: int = 54
      
      def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.set_actions([DraftResponseGeneration, DynamicRoutingStrategy])
            self._watch([AnalyseUserInfo, RewriteResponse])
            self._set_react_mode(react_mode=RoleReactMode.BY_ORDER.value)
      
      """ draft response generation """
      async def _single_think_draft_response_generation(self, specific_requirement, last_run_response: Optional[str] = None, **kwargs): 
            
            ## first think, skip.
            if last_run_response is None:
                  return False, 'first loop, skip think.', None
            else:
                  ## 构造提示词
                  prompt = REACT_PROMPT.format(
                        REACT_REQUIREMENTS=REACT_REQUIREMENTS,
                        REQUIREMENTS=specific_requirement,
                        PROCESS_RESULT=last_run_response
                  )
                  prompt += REACT_PROMPT_END

                  ## 调用 LLM 进行推理
                  response = await self.llm.aask(prompt)

                  ## 解析返回结果
                  try:
                        response = json.loads(response)
                  except Exception as e:
                        response = await self.extract_think_by_regex(response)
                        response = json.loads(response)

                  is_valid = response['is_valid']
                  reason = response['reason']
                  suggestion = response["suggestion"]


                  return is_valid, reason, suggestion

      async def _single_act_draft_response_generation(self, m: Message, todo, action, cache_action, suggestion: Optional[str] = None) -> DeliveryObj:
            
            ## 解析消息内容
            params = json.loads(m.content)
            
            USER_QUERY = params['USER_QUERY']
            USER_BASIC_INFO = params['USER_BASIC_INFO']
            
            ## 执行动作
            start_time = time.time()
            prompt, response = await todo.run(
                  USER_BASIC_INFO=USER_BASIC_INFO,
                  USER_QUERY=USER_QUERY,
                  REQUIREMENTS=DRAFTRESPONSEGENERATION_NEW_REQUIREMENTS,
                  suggestion=suggestion
            )
            
            end_time = time.time()
            generation_time_cost = end_time - start_time
            
            ## 解析返回结果
            try:
                  extract_result = json.loads(response)
            except Exception as e:
                  extract_result = await self.extract_by_regex(response)
                  extract_result = json.loads(extract_result)
                  
            response, reason = extract_result["response"], extract_result["reason"]
            
            ## 构造发布的消息信息
            content_dict = {
                  "DRAFT_RESPONSE_PROMPT": prompt,
                  "DRAFT_RESPONSE": response,
                  "DRAFT_RESPONSE_GENERATE_REASON": reason,
                  "DRAFT_RESPONSE_GENERATE_TIME_COST": generation_time_cost
            }
            
            delivery = DeliveryObj()
            delivery.add_attrs(**content_dict)
      
            return delivery

      async def _single_react_draft_response_generation(self, m: Message, todo, action, cache_action, requirements: Optional[str] = None) -> DeliveryObj:
            react_count = 0
            
            act_result = None
            while react_count < self.max_react_times:
                  
                  ## 是否达到要求
                  is_satisfy, react_reason, suggestion = await self._single_think_draft_response_generation(
                        specific_requirement=requirements,
                        last_run_response=act_result.get_attr('DRAFT_RESPONSE') if act_result is not None else None
                  )

                  if is_satisfy:
                        break
                  
                  ## 没达到要求，执行动作
                  act_result = await self._single_act_draft_response_generation(m, todo, action, cache_action, suggestion)
            
                  ## 更新 react_count
                  react_count += 1
            
            return act_result

      """ dynamic routing strategy """
      async def _single_act_dynamic_routing_strategy(
            self, m: Message, todo, 
            action, cache_action, 
            suggestion: Optional[str] = None, 
            rewrite_response: Optional[str] = None,
            history_todo_actions: Optional[str] = None
      ):
            
            ## 解析消息内容
            params = json.loads(m.content)
            
            USER_QUERY = params.get("USER_QUERY", "")
            HISTORY_CHAT_RECORD = params.get("HISTORY_CHAT_RECORD", "")
            CONV_K = params.get("CONV_K", 1)

            USER_BASIC_INFO = params.get("USER_BASIC_INFO", "")
            DRAFT_RESPONSE = params.get("DRAFT_RESPONSE", "")
            
            ## 执行动作
            professional_judgement_response_final, professional_judgement_reason, professional_judgement_prompt, professional_judgement_time_cost, \
                  confidence_judgement_response_final, confidence_judgement_reason, confidence_judgement_prompt, confidence_judgement_time_cost, \
                  conversation_memory_judgement_response_final, conversation_memory_judgement_reason, conversation_memory_judgement_prompt, conversation_memory_judgement_time_cost, \
                  dynamic_routing_strategy_prompt, dynamic_routing_strategy_response, routing_generation_time_cost = await todo.run(
                        CONV_K=CONV_K,
                        USER_BASIC_INFO=USER_BASIC_INFO,
                        USER_QUERY=USER_QUERY,
                        DRAFT_RESPONSE=DRAFT_RESPONSE,
                        CONVERSATION_MEMORY=HISTORY_CHAT_RECORD,
                        REQUIREMENTS=DYNAMIC_ROUTING_REQUIREMENTS,
                        suggestion=suggestion,
                        rewrite_response=rewrite_response,
                        history_todo_actions=history_todo_actions,
                        CONFIDENCE_THRESHOLD=self.CONFIDENCE_THRESHOLD,
                        MEDIUM_CONFIDENCE_THRESHOLD=self.MEDIUM_CONFIDENCE_THRESHOLD,
                        CRITICAL_RISK_THRESHOLD=self.CRITICAL_RISK_THRESHOLD
                  )
            
            ## 解析返回结果
            extract_result = json.loads(dynamic_routing_strategy_response)
            
            response, reason = extract_result["response"], extract_result["reason"]
            
            if not isinstance(response, list):
                  response = eval(response)
            
            ## 构造发布的消息信息
            content_dict = {
                  "PROFESSIONAL_JUDGEMENT_RESPONSE": professional_judgement_response_final,
                  "PROFESSIONAL_JUDGEMENT_REASON": professional_judgement_reason,
                  "PROFESSIONAL_JUDGEMENT_PROMPT": professional_judgement_prompt,
                  "PROFESSIONAL_JUDGEMENT_GENERATE_TIME_COST": professional_judgement_time_cost,
                  
                  "CONFIDENCE_JUDGEMENT_RESPONSE": confidence_judgement_response_final,
                  "CONFIDENCE_JUDGEMENT_REASON": confidence_judgement_reason,
                  "CONFIDENCE_JUDGEMENT_PROMPT": confidence_judgement_prompt,
                  "CONFIDENCE_JUDGEMENT_GENERATE_TIME_COST": confidence_judgement_time_cost,
                  
                  "CONVERSATION_MEMORY_JUDGEMENT_RESPONSE": conversation_memory_judgement_response_final,
                  "CONVERSATION_MEMORY_JUDGEMENT_REASON": conversation_memory_judgement_reason,
                  "CONVERSATION_MEMORY_JUDGEMENT_PROMPT": conversation_memory_judgement_prompt,
                  "CONVERSATION_MEMORY_JUDGEMENT_GENERATE_TIME_COST": conversation_memory_judgement_time_cost,
                  
                  "ROUTING_RESULT_PROMPT": dynamic_routing_strategy_prompt,
                  "ROUTING_RESULT": response,
                  "ROUTING_RESULT_REASON": reason,
                  "ROUTING_RESULT_GENERATE_TIME_COST": routing_generation_time_cost
            }
            
            delivery = DeliveryObj()
            delivery.add_attrs(**content_dict)
            
            return delivery

      async def _single_react_dynamic_routing_strategy(
            self, m: Message, todo, action, cache_action, requirements: Optional[str] = None, 
            rewrite_response: Optional[str] = None, history_todo_actions: Optional[str] = None
      ):
            """ 直接执行动作，不进行思考 """
            act_result = await self._single_act_dynamic_routing_strategy(
                  m, todo, action, cache_action, 
                  suggestion=None, 
                  rewrite_response=rewrite_response, history_todo_actions=history_todo_actions
            )
            return act_result

      """ rewrite response """
      async def _single_act_rewrite_response(self, m: Message, todo, action, cache_action, suggestion: Optional[str] = None):
            """ 直接执行动作，不进行思考 """
            act_result = await self._single_act_rewrite_response(m, todo, action, cache_action, suggestion=None)
            act_result = json.loads(act_result)
            
            content_dict_str = json.dumps(act_result, ensure_ascii=False, indent=4)
            return content_dict_str

      async def _single_react_rewrite_response(self, m: Message, todo, action, cache_action, requirements: Optional[str] = None):
            """ 直接执行动作，不进行思考 """
            act_result = await self._single_act_rewrite_response(m, todo, action, cache_action, suggestion=None)
            act_result = json.loads(act_result)
            
            content_dict_str = json.dumps(act_result, ensure_ascii=False, indent=4)
            return content_dict_str

      """ think next movement """
      async def _think_next_action(self):
            """ 思考下一步动作 """
            msg = self.get_memories(k=0)
            ## 最大询问专家数为3次。
            rewrite_msg = await self.get_need_messages(msg, 'RewriteResponse', k=3)
            if len(rewrite_msg) > 0:
                  logger.info(f"已进入循环过程。")
                  ## 如果进入循环的话，就把 rewrite_response 赋值给 draft_response
                  rewrite_msg = rewrite_msg[-1]
                  rewrite_msg = json.loads(rewrite_msg.content)
                  rewrite_response = rewrite_msg['REWRITE_RESPONSE']
                  return rewrite_response
            else:
                  logger.info("未进入循环过程。")
                  return None
      
      async def _act(self) -> Message:
            """ 
            1. 先生成草稿响应
            2. 然后判断是否需要求助，进入loop
            3. 返回最终响应结果
            """
            logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
            
            if isinstance(self.rc.todo, DraftResponseGeneration):
                  
                  if await self._think_next_action() is not None:
                        logger.info("\n\n>>> 进入循环过程，跳过草稿响应生成\n\n")
                        return self.dummy_message
                  
                  # logger.info(">>> start action: DraftResponseGeneration")
                  logger.info("\033[32m>>> start action: DraftResponseGeneration\033[0m")
                  
                  msg = self.get_memories(k=0)
                  msg = await self.get_need_messages(msg, 'AnalyseUserInfo')
                  
                  received_infos = json.loads(msg.content)
                  
                  USER_QUERY = received_infos['USER_QUERY']
                  HISTORY_CHAT_RECORD = received_infos['HISTORY_CHAT_RECORD']
                  HISTORY_TODO_ACTIONS = received_infos['HISTORY_TODO_ACTIONS']
                  CONV_K = received_infos['CONV_K']
                  CONV_UUID = received_infos['CONV_UUID']
                  TOTAL_ROUNDS = received_infos['TOTAL_ROUNDS']
                  
                  USER_BASIC_INFO = received_infos['USER_BASIC_INFO']
                  USER_BASIC_INFO_GENERATE_REASON = received_infos['USER_BASIC_INFO_GENERATE_REASON']
                  USER_BASIC_INFO_PROMPT = received_infos['USER_BASIC_INFO_PROMPT']
                  USER_BASIC_INFO_GENERATE_TIME_COST = received_infos['USER_BASIC_INFO_GENERATE_TIME_COST']
                  
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
                        "USER_BASIC_INFO_GENERATE_TIME_COST": USER_BASIC_INFO_GENERATE_TIME_COST
                  }
                  
                  """ 先生成草稿响应 """
                  delivery = await self._single_react_draft_response_generation(
                        m=msg, 
                        todo=self.rc.todo, 
                        action=DraftResponseGeneration, 
                        cache_action=DraftResponseGenerationCache,
                        requirements=DRAFT_RESPONSE_REQUIREMENTS
                  )
                  delivery.add_attrs(**CONCAT_INFOS)
                  
                  to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, self.name)
                  
                  self.rc.env.publish_message(to_pub_msg)
                  self.rc.memory.add(to_pub_msg)
                  
                  self.rc.todo = DynamicRoutingStrategy()
                  
                  return to_pub_msg

            elif isinstance(self.rc.todo, DynamicRoutingStrategy):
                  
                  # logger.info(">>> start action: DynamicRoutingStrategy")
                  logger.info("\033[32m>>> start action: DynamicRoutingStrategy\033[0m")
                  
                  msg = self.get_memories(k=0)
                  
                  rewrite_response = await self._think_next_action()
                  if rewrite_response is not None:
                        
                        msg = await self.get_need_messages(msg, 'RewriteResponse')
                        
                        received_infos = json.loads(msg.content)
                        
                        USER_QUERY = received_infos['USER_QUERY']
                        HISTORY_CHAT_RECORD = received_infos['HISTORY_CHAT_RECORD']
                        HISTORY_TODO_ACTIONS = received_infos['HISTORY_TODO_ACTIONS']
                        CONV_K = received_infos['CONV_K']
                        CONV_UUID = received_infos['CONV_UUID']
                        TOTAL_ROUNDS = received_infos['TOTAL_ROUNDS']
                        
                        USER_BASIC_INFO = received_infos['USER_BASIC_INFO']
                        USER_BASIC_INFO_GENERATE_REASON = received_infos['USER_BASIC_INFO_GENERATE_REASON']
                        USER_BASIC_INFO_PROMPT = received_infos['USER_BASIC_INFO_PROMPT']
                        USER_BASIC_INFO_GENERATE_TIME_COST = received_infos['USER_BASIC_INFO_GENERATE_TIME_COST']
                        
                        DRAFT_RESPONSE_PROMPT = received_infos['REWRITE_RESPONSE_PROMPT']
                        DRAFT_RESPONSE = received_infos['REWRITE_RESPONSE']
                        DRAFT_RESPONSE_GENERATE_REASON = received_infos['REWRITE_RESPONSE_GENERATE_REASON']
                        DRAFT_RESPONSE_GENERATE_TIME_COST = received_infos['REWRITE_RESPONSE_GENERATE_TIME_COST']

                        logger.info("进入循环，将草稿响应替换为重写响应")
                        
                  else:
                        msg = await self.get_need_messages(msg, 'DraftResponseGeneration')
                  
                        received_infos = json.loads(msg.content)
                        
                        USER_QUERY = received_infos['USER_QUERY']
                        HISTORY_CHAT_RECORD = received_infos['HISTORY_CHAT_RECORD']
                        HISTORY_TODO_ACTIONS = received_infos['HISTORY_TODO_ACTIONS']
                        CONV_K = received_infos['CONV_K']
                        CONV_UUID = received_infos['CONV_UUID']
                        TOTAL_ROUNDS = received_infos['TOTAL_ROUNDS']
                        
                        USER_BASIC_INFO = received_infos['USER_BASIC_INFO']
                        USER_BASIC_INFO_GENERATE_REASON = received_infos['USER_BASIC_INFO_GENERATE_REASON']
                        USER_BASIC_INFO_PROMPT = received_infos['USER_BASIC_INFO_PROMPT']
                        USER_BASIC_INFO_GENERATE_TIME_COST = received_infos['USER_BASIC_INFO_GENERATE_TIME_COST']
                        
                        DRAFT_RESPONSE_PROMPT = received_infos['DRAFT_RESPONSE_PROMPT']
                        DRAFT_RESPONSE = received_infos['DRAFT_RESPONSE']
                        DRAFT_RESPONSE_GENERATE_REASON = received_infos['DRAFT_RESPONSE_GENERATE_REASON']
                        DRAFT_RESPONSE_GENERATE_TIME_COST = received_infos['DRAFT_RESPONSE_GENERATE_TIME_COST']
                  
                  LOOP_K = received_infos.get("LOOP_K", 1)
                  logger.info(f"当前循环次数：{LOOP_K}")

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
                        
                        "LOOP_K": LOOP_K
                  }
                  
                  """ 作出路由决策 """
                  delivery = await self._single_react_dynamic_routing_strategy(
                        m=msg,
                        todo=self.rc.todo, 
                        action=DynamicRoutingStrategy, 
                        cache_action=DynamicRoutingStrategyCache,
                        requirements=DYNAMIC_ROUTING_REQUIREMENTS,
                        rewrite_response=rewrite_response if rewrite_response is not None else None,
                        history_todo_actions=HISTORY_TODO_ACTIONS
                  )
                  delivery.add_attrs(**CONCAT_INFOS)
                  to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, "SupervisorsAgent")

                  logger.info(f"to pub msg cause by: {to_pub_msg.cause_by}, send to: {to_pub_msg.send_to}")
                  
                  self.rc.env.publish_message(to_pub_msg)
                  self.rc.memory.add(to_pub_msg)

                  return to_pub_msg

