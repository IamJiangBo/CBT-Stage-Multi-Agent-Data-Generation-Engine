import os
import sys
import time
import json
from typing import Dict, List

from .base_action import AbstractRoleAction

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from component.prompts.dynamic_routing.prompt import (
      ROUTING_TO_EXPERT_PROMPT,
      ROUTING_TO_EXPERT_PROMPT_END
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
      EXPERT3_REQUIREMENTS
)

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import dynamic_routing_logger as logger


class RoutingToExperts(AbstractRoleAction):
      name: str = "RoutingToExpert"
      profile: str = "路由到专家"
      
      async def run(self, PHRASE_TYPE: str, RESPONSE_EVALUATION: str, REQUIREMENTS: str):
            start_time = time.time()
            prompt = ROUTING_TO_EXPERT_PROMPT.format(
                  PHRASE_TYPE=PHRASE_TYPE,
                  RESPONSE_EVALUATION=RESPONSE_EVALUATION,
                  REQUIREMENTS=REQUIREMENTS
            )
            prompt += ROUTING_TO_EXPERT_PROMPT_END
            response = await self._aask(prompt)
            end_time = time.time()
            time_cost = end_time - start_time
            return prompt, response, time_cost


class SeekingForAdvices(AbstractRoleAction):
      name: str = "SeekingForAdvices"
      profile: str = "寻求建议"
      
      async def run(self, experts_needed, **kwargs):
            
            # SCORE_INFO, SCORE_REASON_INFO = json.loads(kwargs['RESPONSE_EVALUATION']), json.loads(kwargs['RESPONSE_EVALUATION_REASON'])
            SCORE_INFO = kwargs['RESPONSE_EVALUATION']
            SCORE_REASON_INFO = kwargs['RESPONSE_EVALUATION_REASON']
            
            response_return = {
                  "expert1": "",
                  "expert2": "",
                  "expert3": ""
            }
            
            prompt_return = {
                  "expert1": "",
                  "expert2": "",
                  "expert3": ""
            }
            
            time_cost_return = {
                  "expert1": "",
                  "expert2": "",
                  "expert3": ""
            }
            
            for expert_id in experts_needed:
                  start_time = time.time()
                  if expert_id == 1:
                        prompt = EXPERT1_PROMPT
                        prompt_end = EXPERT1_PROMPT_END
                        REQUIREMENTS = EXPERT1_REQUIREMENTS
                        NOW_SCORE_INFO, NOW_SCORE_REASON_INFO = json.dumps(SCORE_INFO, ensure_ascii=False), SCORE_REASON_INFO
                  elif expert_id == 2:
                        prompt = EXPERT2_PROMPT
                        prompt_end = EXPERT2_PROMPT_END
                        REQUIREMENTS = EXPERT2_REQUIREMENTS
                        NOW_SCORE_INFO, NOW_SCORE_REASON_INFO = json.dumps(SCORE_INFO, ensure_ascii=False), SCORE_REASON_INFO
                  elif expert_id == 3:
                        prompt = EXPERT3_PROMPT
                        prompt_end = EXPERT3_PROMPT_END
                        REQUIREMENTS = EXPERT3_REQUIREMENTS
                        NOW_SCORE_INFO, NOW_SCORE_REASON_INFO = json.dumps(SCORE_INFO, ensure_ascii=False), SCORE_REASON_INFO
                  else:
                        logger.error(f"专家编号 {expert_id} 不存在")
                        continue
                  
                  prompt = prompt.format(
                        PROBLEM_TYPE=kwargs['PROBLEM_TYPE'],
                        USER_QUERY=kwargs['USER_QUERY'],
                        HISTORY_CONTEXT=kwargs['HISTORY_CONTEXT'],
                        USER_INFO=kwargs['USER_INFO'],
                        PHRASE_TYPE=kwargs['PHRASE_TYPE'],
                        RESPONSE_DRAFT=kwargs['RESPONSE_DRAFT'],
                        RESPONSE_EVALUATION=NOW_SCORE_INFO,
                        RESPONSE_EVALUATION_REASON=NOW_SCORE_REASON_INFO,
                        REQUIREMENTS=REQUIREMENTS
                  )

                  prompt += prompt_end
                  response = await self._aask(prompt)
                  end_time = time.time()
                  time_cost = end_time - start_time

                  prompt_return[f"expert{expert_id}"] = prompt
                  response_return[f"expert{expert_id}"] = response
                  time_cost_return[f"expert{expert_id}"] = time_cost
                  
            return prompt_return, response_return, time_cost_return
