import os
import sys
import time
from typing import Dict, List

from .base_action import AbstractRoleAction

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompts.analyse_conversation_status.prompt import (
      
      ## 对对话状态进行分析
      ANALYSE_CONVERSATION_STATUS_PROMPT,
      ANALYSE_CONVERSATION_STATUS_PROMPT_END,
      
)


root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import analyse_conversation_status_logger as logger


class AnalyseConversationStatus(AbstractRoleAction):
      name: str = "AnalyseConversationStatus"
      profile: str = "对对话状态进行分析，返回对话状态信息"

      async def run(self, USER_QUERY: str, HISTORY_CHAT_RECORD: str, REQUIREMENTS: str):
            start_time = time.time()
            prompt = ANALYSE_CONVERSATION_STATUS_PROMPT.format(
                  USER_QUERY=USER_QUERY,
                  HISTORY_CHAT_RECORD=HISTORY_CHAT_RECORD,
                  REQUIREMENTS=REQUIREMENTS
            )
            prompt += ANALYSE_CONVERSATION_STATUS_PROMPT_END
            response = await self._aask(prompt)
            end_time = time.time()
            time_cost = end_time - start_time
            return prompt, response, time_cost
