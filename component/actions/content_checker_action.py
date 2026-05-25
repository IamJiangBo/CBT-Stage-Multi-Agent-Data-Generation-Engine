import os
import sys
import time
from typing import Dict, List

from .base_action import AbstractRoleAction

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompts.content_checker.prompt import (
      
      ## 对内容进行检查
      CONTENT_CHECKER_PROMPT,
      CONTENT_CHECKER_PROMPT_END,
)


root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import content_checker_logger as logger


class ContentChecker(AbstractRoleAction):
      name: str = "ContentChecker"
      profile: str = "对内容进行检查，返回检查结果"

      async def run(
            self, 
            PROBLEM_TYPE: str,
            USER_QUERY: str, HISTORY_CONTEXT: str, USER_INFO: str, PHRASE_TYPE: str, RESPONSE: str,
            REQUIREMENTS: str
      ):
            start_time = time.time()
            prompt = CONTENT_CHECKER_PROMPT.format(
                  PROBLEM_TYPE=PROBLEM_TYPE,
                  USER_QUERY=USER_QUERY,
                  HISTORY_CONTEXT=HISTORY_CONTEXT,
                  USER_INFO=USER_INFO,
                  PHRASE_TYPE=PHRASE_TYPE,
                  RESPONSE=RESPONSE,
                  REQUIREMENTS=REQUIREMENTS
            )
            prompt += CONTENT_CHECKER_PROMPT_END
            response = await self._aask(prompt)
            end_time = time.time()
            time_cost = end_time - start_time
            return prompt, response, time_cost
