import os
import sys
import time
import json
from typing import Dict, List, Optional

from .base_action import AbstractRoleAction

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompts.generate_response.prompt import (
      
      ## 生成回复
      GENERATE_RESPONSE_PROMPT,
      GENERATE_RESPONSE_PROMPT_END,
       
      ## 改写回复
      RE_GENERATE_RESPONSE_PROMPT,
      RE_GENERATE_RESPONSE_PROMPT_END
)


root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import generate_response_logger as logger


class GenerateResponse(AbstractRoleAction):
      name: str = "GenerateResponse"
      profile: str = "生成回复"

      async def run(
            self,
            PROBLEM_TYPE: str,
            PHRASE_TYPE: str,
            USER_PROFILE: str,
            HISTORY_CHAT_RECORD: str,
            USER_QUERY: str,
            REQUIREMENTS: str,
            STATUS_REQUIREMENTS: str,
            IS_REWRITE: Optional[bool] = False,
            DRAFT_RESPONSE: Optional[str] = None,
            RESPONSE_EVALUATION: Optional[str] = None,
            RESPONSE_EVALUATION_REASON: Optional[str] = None,
            EXPERT_FEEDBACK: Optional[str] = None
      ):
            
            start_time = time.time()
            
            if IS_REWRITE:
                  prompt = RE_GENERATE_RESPONSE_PROMPT.format(
                        PROBLEM_TYPE=PROBLEM_TYPE,
                        PHRASE_TYPE=PHRASE_TYPE,
                        USER_PROFILE=USER_PROFILE,
                        HISTORY_CHAT_RECORD=HISTORY_CHAT_RECORD,
                        USER_QUERY=USER_QUERY,
                        DRAFT_RESPONSE=DRAFT_RESPONSE,
                        RESPONSE_EVALUATION=RESPONSE_EVALUATION,
                        RESPONSE_EVALUATION_REASON=RESPONSE_EVALUATION_REASON,
                        EXPERT_FEEDBACK=EXPERT_FEEDBACK,
                        REQUIREMENTS=REQUIREMENTS,
                  )
                  prompt += RE_GENERATE_RESPONSE_PROMPT_END
                  
                  logger.info(f"开始重写, 专家建议：\n{EXPERT_FEEDBACK}\n\n")
                  
                  if EXPERT_FEEDBACK == '':
                        response = json.dumps(
                              {
                                    "response": DRAFT_RESPONSE,
                                    "reason": "不需要重写"
                              },
                              ensure_ascii=False
                        )
                  else:
                        response = await self._aask(prompt)
            else:
                  prompt = GENERATE_RESPONSE_PROMPT.format(
                        PROBLEM_TYPE=PROBLEM_TYPE,
                        PHRASE_TYPE=PHRASE_TYPE,
                        USER_PROFILE=USER_PROFILE,
                        HISTORY_CHAT_RECORD=HISTORY_CHAT_RECORD,
                        USER_QUERY=USER_QUERY,
                        REQUIREMENTS=REQUIREMENTS,
                        STATUS_REQUIREMENTS = STATUS_REQUIREMENTS
                  )
                  prompt += GENERATE_RESPONSE_PROMPT_END
                  response = await self._aask(prompt)

            end_time = time.time()
            time_cost = end_time - start_time
            
            return prompt, response, time_cost
