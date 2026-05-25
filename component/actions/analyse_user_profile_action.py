import os
import sys
import time
from typing import Dict, List

from .base_action import AbstractRoleAction

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompts.analyse_user_profile.prompt import (
      
      ## 对用户进行全方面的分析
      ANALYSE_USER_PROFILE_PROMPT,
      ANALYSE_USER_PROFILE_PROMPT_END,
      
      ## 对用户问题类型进行分析
      ANALYSE_USER_PROBLEM_TYPE_PROMPT,
      ANALYSE_USER_PROBLEM_TYPE_PROMPT_END,
)


root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import analyse_user_profile_logger as logger


class AnalyseUserProfile(AbstractRoleAction):
      name: str = "AnalyseUserProfile"
      profile: str = "对用户进行全方面的分析，返回用户画像信息"

      async def run(self, USER_QUERY: str, HISTORY_USER_PROFILE: str, LAST_ASSISTANT_REPLY:str, REQUIREMENTS: str):
            start_time = time.time()
            prompt = ANALYSE_USER_PROFILE_PROMPT.format(
                  USER_QUERY=USER_QUERY,
                  LAST_ASSISTANT_REPLY=LAST_ASSISTANT_REPLY,
                  HISTORY_USER_PROFILE=HISTORY_USER_PROFILE,
                  REQUIREMENTS=REQUIREMENTS
            )
            prompt += ANALYSE_USER_PROFILE_PROMPT_END
            response = await self._aask(prompt)
            end_time = time.time()
            time_cost = end_time - start_time
            return prompt, response, time_cost


class AnalyseUserProblemType(AbstractRoleAction):
      name: str = "AnalyseUserProblemType"
      profile: str = "对用户的问题类型进行分析，返回问题类型"

      async def run(self, USER_QUERY: str, ANALYSE_USER_PROFILE_RESPONSE: str, REQUIREMENTS: str):
            start_time = time.time()
            prompt = ANALYSE_USER_PROBLEM_TYPE_PROMPT.format(
                  USER_QUERY=USER_QUERY,
                  ANALYSE_USER_PROFILE_RESPONSE=ANALYSE_USER_PROFILE_RESPONSE,
                  REQUIREMENTS=REQUIREMENTS
            )
            prompt += ANALYSE_USER_PROBLEM_TYPE_PROMPT_END
            response = await self._aask(prompt)
            end_time = time.time()
            time_cost = end_time - start_time
            return prompt, response, time_cost
