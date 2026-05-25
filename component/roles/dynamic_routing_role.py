import os
import re
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

from component.actions.dynamic_routing_action import (
      RoutingToExperts,
      SeekingForAdvices
)

from component.prompts.dynamic_routing.prompt import (
      EXPERT1_PROMPT,
      EXPERT1_PROMPT_END,
      EXPERT2_PROMPT,
      EXPERT2_PROMPT_END,
      EXPERT3_PROMPT,
      EXPERT3_PROMPT_END
)

from component.prompts.dynamic_routing.requirements import (
      EXPERT1_REQUIREMENTS,
      EXPERT2_REQUIREMENTS,
      EXPERT3_REQUIREMENTS,
      EXPERT1_ID2NAME,
      EXPERT2_ID2NAME,
      EXPERT3_ID2NAME
)

from component.prompts.dynamic_routing.requirements import ROUTING_TO_EXPERT_REQUIREMENTS

from component.actions.content_checker_action import (
      ContentChecker
)

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import dynamic_routing_logger as logger


class DynamicRoutingAgent(CBTAbstractRole):
      name: str = "DynamicRoutingAgent"
      profile: str = "动态路由的智能体"
      max_react_times: int = 3

      def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.set_actions([RoutingToExperts, SeekingForAdvices])
            self._watch([ContentChecker])
            self._set_react_mode(react_mode=RoleReactMode.BY_ORDER.value)

      async def extract_by_regex_dynamic_routing(self, response):
            patterns = {
                  'needs_expert': r'"needs_expert":\s*"([^"]*)"',
                  'experts_needed': r'"experts_needed":\s*"([^"]*)"',
                  'reason': r'"reason":\s*"([^"]*)"'
            }
            results = {}
            for key, pattern in patterns.items():
                  match = re.search(pattern, response)
                  if match:
                        results[key] = match.group(1)
            results = json.dumps(results, ensure_ascii=False)
            return results
      async def nonempty_list(self,value): #尝试解析为 list
            if isinstance(value, list) and len(value) > 0:
                  return value
            if isinstance(value, str):
                  try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list) and len(parsed) > 0:
                              return parsed
                  except Exception:
                        pass
            return []
      async def process_dynamic_routing(self, todo, REQUIREMENTS, **kwargs):        
                
            #     # 改为按新标准走LLM判断（定性触发），不再基于分数阈值
            #     prompt, response, time_cost = await todo.run(
            #           PHRASE_TYPE=kwargs['PHRASE_TYPE'],
            #           RESPONSE_EVALUATION=kwargs['RESPONSE_EVALUATION'],
            #           REQUIREMENTS=REQUIREMENTS
            #     )

            #     try:
            #           response_obj = json.loads(response)
            #     except Exception:
            #           response_obj = await self.extract_by_regex_dynamic_routing(response)
            #           response_obj = json.loads(response_obj)
                
            #     experts_needed = response_obj.get('experts_needed', '[]')
            #     reason = response_obj.get('reason', '')
            #     if not isinstance(experts_needed, list):
            #           try:
            #                 experts_needed = eval(experts_needed)
            #           except Exception:
            #                 experts_needed = []
            #     response = json.dumps(experts_needed, ensure_ascii=False)
            
            ## 使用规则判断专家
            RESPONSE_EVALUATION=kwargs['RESPONSE_EVALUATION']
            try:
                  RESPONSE_EVALUATION = json.loads(RESPONSE_EVALUATION)
            except Exception as e:
                  pass
            PHASE = RESPONSE_EVALUATION.get('phase', 'not found.')
            PROBLEM = RESPONSE_EVALUATION.get('problem', 'not found.')
            PROBLEM = [item[0] for item in PROBLEM]
            response = []
            # PHASE = await self.nonempty_list(PHASE)
            PROBLEM = await self.nonempty_list(PROBLEM)
            
            mapping = {                          # 问题->专家映射表
                  1: {1.1, 1.2, 1.3, 1.4},       # 专家1
                  2: {2.1, 2.2, 2.3, 2.4},       # 专家2
                  3: {3.1, 3.2, 3.3, 3.4}     # 专家3
            }
            for expert_id, problem_set in mapping.items():
                  if any(str(p) in map(str, problem_set) for p in PROBLEM):
                        response.append(expert_id) # 添加专家ID
                        
            response = list(dict.fromkeys(response))
            # response = [1,2,3] ##强制调专家改写
            response = json.dumps(response, ensure_ascii=False)
            reason = f"当前状态为 {PHASE}，存在问题：{PROBLEM}"
            prompt,time_cost = '',0
            return prompt, response, reason, time_cost
      
      async def extract_by_regex_seeking_for_advices(self, response, expert_id):
            """ 获取专家建议 """
            if expert_id == 1:
                  patterns = {
                        'improved_response': r'"improved_response":\s*"([^"]*)"',
                        'used_strategies': r'"used_strategies":\s*"([^"]*)"',
                        'reason': r'"reason":\s*"([^"]*)"'
                  }
                  
                  results = {}
                  for key, pattern in patterns.items():
                        match = re.search(pattern, response)
                        if match:
                              results[key] = match.group(1)
                  
                  if "used_strategies" not in results:
                        pattern = r'"used_strategies":\s*(\{[\s\S]*?\})(?=,\s*"|\s*\})'
                        match = re.search(pattern, response)
                        if match:
                              results['used_strategies'] = match.group(1)
                  
                  """ LLM直接输出的是list """ 
                  if 'used_strategies' not in results:
                        pattern = r'"used_strategies":\s*(\[[^\]]*\])'
                        match = re.search(pattern, response)
                        if match:
                              results['used_strategies'] = match.group(1)
                    
                  used_strategies_str = ""
                  used_strategies = results["used_strategies"]
                  if not isinstance(used_strategies, list):
                        used_strategies = eval(used_strategies)
                        
                  for sid, strategy_id in enumerate(used_strategies):
                        strategy_id = str(strategy_id)
                        if sid == len(used_strategies) - 1:
                              used_strategies_str += f"{EXPERT1_ID2NAME[strategy_id]}"
                        else:
                              used_strategies_str += f"{EXPERT1_ID2NAME[strategy_id]}\n"
            
                  # response = f"改写的建议为：\n{results['improved_response']}\n使用策略为：\n{used_strategies_str}"
                  response = f"专家建议回复：\n{results['improved_response']}\n"
                  reason = results['reason']
                  
                  # response = f"改写的建议为：\n{results['improved_response']}\n改写的理由为：\n{reason}\n使用策略为：\n{used_strategies_str}"
                  
            elif expert_id == 2:
                  patterns = {
                        'improved_response': r'"improved_response":\s*"([^"]*)"',
                        'used_strategies': r'"used_strategies":\s*"([^"]*)"',
                        'distortion_type': r'"distortion_type":\s*"([^"]*)"',
                        'reason': r'"reason":\s*"([^"]*)"'
                  }
                  
                  results = {}
                  for key, pattern in patterns.items():
                        match = re.search(pattern, response)
                        if match:
                              results[key] = match.group(1)
                  
                  if "used_strategies" not in results:
                        pattern = r'"used_strategies":\s*(\{[\s\S]*?\})(?=,\s*"|\s*\})'
                        match = re.search(pattern, response)
                        if match:
                              results['used_strategies'] = match.group(1)
                  
                  if "used_strategies" not in results:
                        pattern = r'"used_strategies":\s*(\[[^\]]*\])'
                        match = re.search(pattern, response)
                        if match:
                              results['used_strategies'] = match.group(1)
                  
                  used_strategies_str = ""
                  used_strategies = results["used_strategies"]
                  if not isinstance(used_strategies, list):
                        used_strategies = eval(used_strategies)
                        
                  for sid, strategy_id in enumerate(used_strategies):
                        strategy_id = str(strategy_id)
                        if sid == len(used_strategies) - 1:
                              used_strategies_str += f"{EXPERT2_ID2NAME[strategy_id]}"
                        else:
                              used_strategies_str += f"{EXPERT2_ID2NAME[strategy_id]}\n"
            
                  # response = f"改写的建议为：\n{results['improved_response']}\n使用的策略为：\n{used_strategies_str}\n识别的扭曲类型为：\n{results['distortion_type']}"
                  response = f"专家建议回复：\n{results['improved_response']}\n"
                  reason = results['reason']
                  
                  # response = f"改写的建议为：\n{results['improved_response']}\n改写的理由为：\n{reason}\n使用的策略为：\n{used_strategies_str}\n识别的扭曲类型为：\n{results['distortion_type']}"
                  
            elif expert_id == 3:
                  patterns = {
                        'improved_response': r'"improved_response":\s*"([^"]*)"',
                        'used_strategies': r'"used_strategies":\s*"([^"]*)"',
                        'reason': r'"reason":\s*"([^"]*)"'
                  }
                  
                  results = {}
                  for key, pattern in patterns.items():
                        match = re.search(pattern, response)
                        if match:
                              results[key] = match.group(1)
                  
                  if "used_strategies" not in results:
                        pattern = r'"used_strategies":\s*(\{[\s\S]*?\})(?=,\s*"|\s*\})'
                        match = re.search(pattern, response)
                        if match:
                              results['used_strategies'] = match.group(1)
                  
                  if "used_strategies" not in results:
                        pattern = r'"used_strategies":\s*(\[[^\]]*\])'
                        match = re.search(pattern, response)
                        if match:
                              results['used_strategies'] = match.group(1)
                  
                  used_strategies_str = ""
                  used_strategies = results["used_strategies"]
                  if not isinstance(used_strategies, list):
                        used_strategies = eval(used_strategies)
                        
                  for sid, strategy_id in enumerate(used_strategies):
                        strategy_id = str(strategy_id)
                        if sid == len(used_strategies) - 1:
                              used_strategies_str += f"{EXPERT3_ID2NAME[strategy_id]}"
                        else:
                              used_strategies_str += f"{EXPERT3_ID2NAME[strategy_id]}\n"
            
                  # response = f"改写的建议为：\n{results['improved_response']}\n使用策略为：\n{used_strategies_str}"
                  response = f"专家建议回复：\n{results['improved_response']}\n"
                  reason = results['reason']
                  
                  # response = f"改写的建议为：\n{results['improved_response']}\n改写的理由为：\n{reason}\n使用策略为：\n{used_strategies_str}"
            
            results = {
                  "response": response,
                  "reason": reason
            }
            
            results = json.dumps(results, ensure_ascii=False)
            return results

      async def process_seeking_for_advices(self, todo, experts_needed, **kwargs):
            
            prompt, response, time_cost = await todo.run(
                  experts_needed=experts_needed,
                  **kwargs
            )
            
            return prompt, response, time_cost
      
      async def _act(self) -> Message:
            
            """ 
            接收到问题检查结果，进行动态路由，选择专家给出修改建议，发给 GenerateResponseAgent 进行改写
            """
            
            logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
            
            if isinstance(self.rc.todo, SeekingForAdvices):
                  logger.info("\033[32m>>> start action: SeekingForAdvices\033[0m")
                  
                  msg = self.get_memories(k=0)
                  msg = await self.get_need_messages(msg, 'RoutingToExperts')
                  
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
                  
                  GENERATE_RESPONSE_HISTORY = received_infos['GENERATE_RESPONSE_HISTORY']
                  
                  # 新增：获取寻求建议历史记录
                  SEEKING_FOR_ADVICES_HISTORY = received_infos.get('SEEKING_FOR_ADVICES_HISTORY', [])
                  
                  CONTENT_CHECKER_PROMPT = received_infos['CONTENT_CHECKER_PROMPT']
                  CONTENT_CHECKER_RESPONSE = received_infos['CONTENT_CHECKER_RESPONSE']
                  CONTENT_CHECKER_REASON = received_infos['CONTENT_CHECKER_REASON']
                  CONTENT_CHECKER_HISTORY = received_infos['CONTENT_CHECKER_HISTORY']
                  CONTENT_CHECKER_TIME_COST = received_infos['CONTENT_CHECKER_TIME_COST']
                  
                  DYNAMIC_ROUTING_PROMPT = received_infos['DYNAMIC_ROUTING_PROMPT']
                  DYNAMIC_ROUTING_RESPONSE = received_infos['DYNAMIC_ROUTING_RESPONSE']
                  DYNAMIC_ROUTING_REASON = received_infos['DYNAMIC_ROUTING_REASON']
                  DYNAMIC_ROUTING_TIME_COST = received_infos['DYNAMIC_ROUTING_TIME_COST']
                  
                  LOOP_K = None if "LOOP_K" not in received_infos else received_infos["LOOP_K"]
                  
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
                        
                        GENERATE_RESPONSE_HISTORY=GENERATE_RESPONSE_HISTORY,
                        
                        SEEKING_FOR_ADVICES_HISTORY=SEEKING_FOR_ADVICES_HISTORY,
                        
                        CONTENT_CHECKER_PROMPT=CONTENT_CHECKER_PROMPT,
                        CONTENT_CHECKER_RESPONSE=CONTENT_CHECKER_RESPONSE,
                        CONTENT_CHECKER_REASON=CONTENT_CHECKER_REASON,
                        CONTENT_CHECKER_HISTORY=CONTENT_CHECKER_HISTORY,
                        CONTENT_CHECKER_TIME_COST=CONTENT_CHECKER_TIME_COST,
                        
                        DYNAMIC_ROUTING_PROMPT=DYNAMIC_ROUTING_PROMPT,
                        DYNAMIC_ROUTING_RESPONSE=DYNAMIC_ROUTING_RESPONSE,
                        DYNAMIC_ROUTING_REASON=DYNAMIC_ROUTING_REASON,
                        DYNAMIC_ROUTING_TIME_COST=DYNAMIC_ROUTING_TIME_COST
                  )
                  
                  
                  GENERATE_FINAL_RESPONSE_RESPONSE = received_infos.get("GENERATE_FINAL_RESPONSE_RESPONSE", '')
                  if GENERATE_FINAL_RESPONSE_RESPONSE != "":
                        CONCAT_INFOS['GENERATE_FINAL_RESPONSE_PROMPT'] = received_infos['GENERATE_FINAL_RESPONSE_PROMPT']
                        CONCAT_INFOS['GENERATE_FINAL_RESPONSE_RESPONSE'] = received_infos['GENERATE_FINAL_RESPONSE_RESPONSE']
                        CONCAT_INFOS['GENERATE_FINAL_RESPONSE_REASON'] = received_infos['GENERATE_FINAL_RESPONSE_REASON']
                        CONCAT_INFOS['GENERATE_FINAL_RESPONSE_TIME_COST'] = received_infos['GENERATE_FINAL_RESPONSE_TIME_COST']
                  
                  act_start = time.time()
                  prompt, response, time_cost = await self.process_seeking_for_advices(
                        todo=self.rc.todo, 
                        experts_needed=eval(DYNAMIC_ROUTING_RESPONSE),
                        PROBLEM_TYPE=ANALYSE_USER_PROBLEM_TYPE_RESPONSE,
                        USER_QUERY=USER_QUERY,
                        HISTORY_CONTEXT=HISTORY_CHAT_RECORD,
                        USER_INFO=ANALYSE_USER_PROFILE_RESPONSE,
                        PHRASE_TYPE=ANALYSE_CONVERSATION_STATUS_RESPONSE,
                        RESPONSE_DRAFT=GENERATE_DRAFT_RESPONSE_RESPONSE if GENERATE_FINAL_RESPONSE_RESPONSE == "" else GENERATE_FINAL_RESPONSE_RESPONSE,
                        RESPONSE_EVALUATION=CONTENT_CHECKER_RESPONSE,
                        RESPONSE_EVALUATION_REASON=CONTENT_CHECKER_REASON
                  )
                  act_end = time.time()
                  TIMESTAMP_LOG = received_infos['TIMESTAMP_LOG']
                  TIMESTAMP_LOG.append({f"{self.rc.todo.name}": [act_start,act_end]})
                  CONCAT_INFOS['TIMESTAMP_LOG'] = TIMESTAMP_LOG
                  
                  final_prompt = ""
                  final_response = ""
                  final_reason = ""
                  final_time_cost = 0
                  
                  for expert_name in response:
                        
                        now_prompt = prompt[expert_name]
                        now_time_cost = time_cost[expert_name]
                        now_response = response[expert_name]
                        
                        if now_response == "":
                              continue
                        
                        expert_id = expert_name.split("expert")[1]
                        expert_id = int(expert_id)
                        extract_response = await self.extract_by_regex_seeking_for_advices(now_response, expert_id)
                        extract_response = json.loads(extract_response)
                        real_response = extract_response['response']
                        real_reason = extract_response['reason']
                        
                        final_prompt += f"专家 - [{expert_name}]:\n" + now_prompt + '\n\n'
                        final_response += f"专家 - [{expert_name}]:\n" + real_response + '\n\n'
                        final_reason += f"专家 - [{expert_name}]:\n" + real_reason + '\n\n'
                        final_time_cost += now_time_cost
                        
                  CONCAT_INFOS['SEEKING_FOR_ADVICES_PROMPT'] = final_prompt
                  CONCAT_INFOS['SEEKING_FOR_ADVICES_RESPONSE'] = final_response
                  CONCAT_INFOS['SEEKING_FOR_ADVICES_REASON'] = final_reason
                  CONCAT_INFOS['SEEKING_FOR_ADVICES_TIME_COST'] = final_time_cost
                  
                  # 新增：将当前寻求建议结果添加到历史记录中
                  current_advice_info = {
                        "response": final_response,
                        "reason": final_reason,
                        "time_cost": final_time_cost,
                        "experts_needed": eval(DYNAMIC_ROUTING_RESPONSE)
                  }
                  CONCAT_INFOS['SEEKING_FOR_ADVICES_HISTORY'].append(current_advice_info)
                  
                  if LOOP_K is not None:
                        CONCAT_INFOS['LOOP_K'] = LOOP_K
                  
                  delivery = DeliveryObj()
                  delivery.add_attrs(**CONCAT_INFOS)
                  
                  logger.info(f"\n\n>>> 寻求建议结果：\n{final_response}\n\n判别原因：\n{final_reason}\n\n")
                  
                  to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, "GenerateResponseAgent")
                  self.rc.env.publish_message(to_pub_msg)
                  self.rc.memory.add(to_pub_msg)
                  
                  return to_pub_msg
                  
            elif isinstance(self.rc.todo, RoutingToExperts):
                  logger.info("\033[32m>>> start action: RoutingToExperts\033[0m")
            
                  msg = self.get_memories(k=0)
                  msg = await self.get_need_messages(msg, 'ContentChecker')
                  
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
                  GENERATE_RESPONSE_HISTORY = received_infos['GENERATE_RESPONSE_HISTORY']
                  
                  # 新增：获取寻求建议历史记录
                  SEEKING_FOR_ADVICES_HISTORY = received_infos.get('SEEKING_FOR_ADVICES_HISTORY', [])
                  
                  CONTENT_CHECKER_PROMPT = received_infos['CONTENT_CHECKER_PROMPT']
                  CONTENT_CHECKER_RESPONSE = received_infos['CONTENT_CHECKER_RESPONSE']
                  CONTENT_CHECKER_REASON = received_infos['CONTENT_CHECKER_REASON']
                  CONTENT_CHECKER_HISTORY = received_infos['CONTENT_CHECKER_HISTORY']
                  CONTENT_CHECKER_TIME_COST = received_infos['CONTENT_CHECKER_TIME_COST']
                  
                  LOOP_K = None if "LOOP_K" not in received_infos else received_infos["LOOP_K"]
                  
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
                        
                        GENERATE_RESPONSE_HISTORY=GENERATE_RESPONSE_HISTORY,
                        
                        SEEKING_FOR_ADVICES_HISTORY=SEEKING_FOR_ADVICES_HISTORY,
                        
                        CONTENT_CHECKER_PROMPT=CONTENT_CHECKER_PROMPT,
                        CONTENT_CHECKER_RESPONSE=CONTENT_CHECKER_RESPONSE,
                        CONTENT_CHECKER_REASON=CONTENT_CHECKER_REASON,
                        CONTENT_CHECKER_HISTORY=CONTENT_CHECKER_HISTORY,
                        CONTENT_CHECKER_TIME_COST=CONTENT_CHECKER_TIME_COST
                  )
                  
                  act_start = time.time()
                  prompt, response, reason, time_cost = await self.process_dynamic_routing(
                        todo=self.rc.todo, 
                        REQUIREMENTS=ROUTING_TO_EXPERT_REQUIREMENTS,
                        PHRASE_TYPE=ANALYSE_CONVERSATION_STATUS_RESPONSE,
                        # RESPONSE_EVALUATION=json.loads(CONTENT_CHECKER_RESPONSE)
                        RESPONSE_EVALUATION=CONTENT_CHECKER_RESPONSE
                  )
                  act_end = time.time()
                  TIMESTAMP_LOG = received_infos['TIMESTAMP_LOG']
                  TIMESTAMP_LOG.append({f"{self.rc.todo.name}": [act_start,act_end]})
                  CONCAT_INFOS['TIMESTAMP_LOG'] = TIMESTAMP_LOG
                  
                  CONCAT_INFOS['DYNAMIC_ROUTING_PROMPT'] = prompt
                  CONCAT_INFOS['DYNAMIC_ROUTING_RESPONSE'] = response
                  CONCAT_INFOS['DYNAMIC_ROUTING_REASON'] = reason
                  CONCAT_INFOS['DYNAMIC_ROUTING_TIME_COST'] = time_cost
                  
                  if LOOP_K is not None:
                        CONCAT_INFOS['LOOP_K'] = LOOP_K
                  
                  GENERATE_FINAL_RESPONSE_RESPONSE = received_infos.get("GENERATE_FINAL_RESPONSE_RESPONSE", '')
                  if GENERATE_FINAL_RESPONSE_RESPONSE != "":
                        CONCAT_INFOS['GENERATE_FINAL_RESPONSE_PROMPT'] = received_infos['GENERATE_FINAL_RESPONSE_PROMPT']
                        CONCAT_INFOS['GENERATE_FINAL_RESPONSE_RESPONSE'] = received_infos['GENERATE_FINAL_RESPONSE_RESPONSE']
                        CONCAT_INFOS['GENERATE_FINAL_RESPONSE_REASON'] = received_infos['GENERATE_FINAL_RESPONSE_REASON']
                        CONCAT_INFOS['GENERATE_FINAL_RESPONSE_TIME_COST'] = received_infos['GENERATE_FINAL_RESPONSE_TIME_COST']
                  
                  delivery = DeliveryObj()
                  delivery.add_attrs(**CONCAT_INFOS)

                  logger.info(f"\n\n>>> 动态路由结果：\n{response}\n\n判别原因：\n{reason}\n\n")

                  to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, self.name)
                  self.rc.env.publish_message(to_pub_msg)
                  self.rc.memory.add(to_pub_msg)
                  
                  return to_pub_msg
