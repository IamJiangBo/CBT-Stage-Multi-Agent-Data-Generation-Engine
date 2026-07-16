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

from component.prompts.content_checker.requirements import (
      CONTENT_CHECKER_REQUIREMENTS
      
      # CONTENT_CHECKER_EMPATHY_REQUIREMENTS,
      # CONTENT_CHECKER_PERSPECTIVE_REQUIREMENTS,
      # CONTENT_CHECKER_STRATEGY_REQUIREMENTS
)

from component.actions.content_checker_action import (
      ContentChecker
)

from component.actions.generate_response_action import (
      GenerateResponse
)

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import content_checker_logger as logger
from tools.logger import content_checker_prompt_logger as prompt_logger


class ContentCheckerAgent(CBTAbstractRole):
      name: str = "ContentCheckerAgent"
      profile: str = "内容检查的智能体"
      max_react_times: int = 3

      def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.set_actions([ContentChecker])
            self._watch([GenerateResponse])

      async def extract_by_regex_content_checker(self, response):
            patterns = {
                  'phase': r'"phase":\s*"([^"]*)"',
                  'problem': r'"problem":\s*(\[[^\]]*\])',
                  'reason': r'"reason":\s*"([^"]*)"'
            }
            results = {}
            for key, pattern in patterns.items():
                  match = re.search(pattern, response)
                  if match:
                        results[key] = match.group(1)
            return results
      
      async def process_content_checker(self, todo, REQUIREMENTS, **kwargs):        
            
            prompt, response, time_cost = await todo.run(
                  PROBLEM_TYPE=kwargs['PROBLEM_TYPE'],
                  USER_QUERY=kwargs['USER_QUERY'],
                  HISTORY_CONTEXT=kwargs['HISTORY_CONTEXT'],
                  USER_INFO=kwargs['USER_INFO'],
                  PHRASE_TYPE=kwargs['PHRASE_TYPE'],
                  RESPONSE=kwargs['RESPONSE'],
                  REQUIREMENTS=REQUIREMENTS
            )
            try:
                  response_obj = json.loads(response)
            except Exception:
                  response_obj = await self.extract_by_regex_content_checker(response)
            
            reason = response_obj.get('problem_reason', 'not found.')
            phase = response_obj.get('phase', 'not found.')
            problem = response_obj.get('problem', 'not found.')
            
            response = {
                  "phase": phase,
                  "problem": problem,
                  "reason": reason
            }
            return prompt, response, reason, time_cost
      
      # """ ask split """
      # async def extract_by_regex_content_checker_split(self, response, check_type='empathy'):
      #       patterns = {
      #             'score': r'"score":\s*"([^"]*)"',
      #             'reason': r'"reason":\s*"([^"]*)"'
      #       }
      #       results = {}
      #       for key, pattern in patterns.items():
      #             match = re.search(pattern, response)
      #             if match:
      #                   results[key] = match.group(1)
            
      #       results['response'] = "{}_score: {}".format(
      #             check_type, results.get('score', 'not found.')
      #       )
      #       results[f'{check_type}_score'] = results["score"]
      #       results = json.dumps(results, ensure_ascii=False)
      #       return results

      # async def process_content_checker(self, todo, REQUIREMENTS, check_type, **kwargs):        
            
      #       prompt, response, time_cost = await todo.run(
      #             PROBLEM_TYPE=kwargs['PROBLEM_TYPE'],
      #             USER_QUERY=kwargs['USER_QUERY'],
      #             HISTORY_CONTEXT=kwargs['HISTORY_CONTEXT'],
      #             USER_INFO=kwargs['USER_INFO'],
      #             PHRASE_TYPE=kwargs['PHRASE_TYPE'],
      #             RESPONSE=kwargs['RESPONSE'],
      #             REQUIREMENTS=REQUIREMENTS
      #       )

      #       response_str = await self.extract_by_regex_content_checker_split(response, check_type)     
      #       reason = json.loads(response_str)["reason"]
            
      #       return prompt, response_str, reason, time_cost
      
      async def _act(self) -> Message:
            
            logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
            
            logger.info("\033[32m>>> start action: ContentChecker\033[0m")

            msg = self.get_memories(k=0)
            msg = await self.get_need_messages(msg, 'GenerateResponse')
            
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
            SEEKING_FOR_ADVICES_HISTORY = received_infos.get('SEEKING_FOR_ADVICES_HISTORY', [])
            
            LOOP_K = None if "LOOP_K" not in received_infos else received_infos["LOOP_K"]
            
            # 新增：累积记录内容检查结果历史
            CONTENT_CHECKER_HISTORY = received_infos.get('CONTENT_CHECKER_HISTORY', [])
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
                  
                  CONTENT_CHECKER_HISTORY=CONTENT_CHECKER_HISTORY,
                  SEEKING_FOR_ADVICES_HISTORY=SEEKING_FOR_ADVICES_HISTORY
            )
            
            GENERATE_FINAL_RESPONSE_RESPONSE = received_infos.get("GENERATE_FINAL_RESPONSE_RESPONSE", "")
            if GENERATE_FINAL_RESPONSE_RESPONSE != "":
                  CONCAT_INFOS['GENERATE_FINAL_RESPONSE_PROMPT'] = received_infos['GENERATE_FINAL_RESPONSE_PROMPT']
                  CONCAT_INFOS['GENERATE_FINAL_RESPONSE_RESPONSE'] = received_infos['GENERATE_FINAL_RESPONSE_RESPONSE']
                  CONCAT_INFOS['GENERATE_FINAL_RESPONSE_REASON'] = received_infos['GENERATE_FINAL_RESPONSE_REASON']
                  CONCAT_INFOS['GENERATE_FINAL_RESPONSE_TIME_COST'] = received_infos['GENERATE_FINAL_RESPONSE_TIME_COST']
            act_start = time.time()
            # 新标准：一次性调用，返回 score 与 reason
            prompt, response, reason, time_cost = await self.process_content_checker(
                  todo=self.rc.todo, 
                  REQUIREMENTS=CONTENT_CHECKER_REQUIREMENTS,
                  PROBLEM_TYPE=ANALYSE_USER_PROBLEM_TYPE_RESPONSE,
                  USER_QUERY=USER_QUERY,
                  HISTORY_CONTEXT=HISTORY_CHAT_RECORD,
                  USER_INFO=ANALYSE_USER_PROFILE_RESPONSE,
                  PHRASE_TYPE=ANALYSE_CONVERSATION_STATUS_RESPONSE,
                  RESPONSE=GENERATE_DRAFT_RESPONSE_RESPONSE if GENERATE_FINAL_RESPONSE_RESPONSE == "" else GENERATE_FINAL_RESPONSE_RESPONSE
            )
            
            act_end = time.time()
            TIMESTAMP_LOG = received_infos['TIMESTAMP_LOG']
            TIMESTAMP_LOG.append({f"{self.rc.todo.name}": [act_start,act_end]})
            CONCAT_INFOS['TIMESTAMP_LOG'] = TIMESTAMP_LOG
            
            CONCAT_INFOS['CONTENT_CHECKER_PROMPT'] = prompt
            CONCAT_INFOS['CONTENT_CHECKER_RESPONSE'] = response
            CONCAT_INFOS['CONTENT_CHECKER_REASON'] = reason
            CONCAT_INFOS['CONTENT_CHECKER_TIME_COST'] = time_cost

            current_checker_info = {
                        "response": response,
                        "reason": reason,
                        "time_cost": time_cost,
                  }
            CONCAT_INFOS['CONTENT_CHECKER_HISTORY'].append(current_checker_info)
            
            if LOOP_K is not None:
                  CONCAT_INFOS['LOOP_K'] = LOOP_K
            
            delivery = DeliveryObj()
            delivery.add_attrs(**CONCAT_INFOS)
            
            cur_anser=GENERATE_DRAFT_RESPONSE_RESPONSE if GENERATE_FINAL_RESPONSE_RESPONSE == "" else GENERATE_FINAL_RESPONSE_RESPONSE
            logger.info(f"\n>>> 对话用户：CONV_UUID: {CONV_UUID}, \n阶段： CONV_K: {CONV_K},   LOOP_K: {LOOP_K} \n")
            logger.info(f"\n\n>>> 用户问题\n{USER_QUERY}\n\n当前回复：\n{cur_anser}\n\n")
            logger.info(f"\n\n>>> 内容检查结果：\n{response}\n\n判别原因：\n{reason}\n\n")
            
            to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, "DynamicRoutingAgent")
            self.rc.env.publish_message(to_pub_msg)
            self.rc.memory.add(to_pub_msg)
            
            return to_pub_msg
