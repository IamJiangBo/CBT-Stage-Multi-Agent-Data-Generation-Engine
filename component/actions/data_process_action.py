import os
import sys
import time
from typing import Dict, List

from .base_action import AbstractRoleAction
from tools.logger import data_process_logger as logger


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompts.data_process.prompt import (
      
      ## 对用户进行全方面的分析
      ANALYSE_DATA_PROCESS_PROMPT,
      ANALYSE_DATA_PROCESS_PROMPT_END,
      
      ## 建议信息整合
      ADVICE_DATA_PROCESS_PROMPT,
      ADVICE_DATA_PROCESS_PROMPT_END,
      
      ## CoT 思维链数据生成
      COT_DATA_GENERATE_PROMPT,
      COT_DATA_GENERATE_PROMPT_END,

)


root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)


class AnalyseDataProcess(AbstractRoleAction):
      name: str = "AnalyseDataProcess"
      profile: str = "处理用户状态分析数据"

      async def run(self, ANALYSE_INFO: str, REQUIREMENTS: str):
            start_time = time.time()
            prompt = ANALYSE_DATA_PROCESS_PROMPT.format(
                  ANALYSE_INFO=ANALYSE_INFO,
                  REQUIREMENTS=REQUIREMENTS
            )
            prompt += ANALYSE_DATA_PROCESS_PROMPT_END
            # logger.info(f"\n\n>>> 用户分析prompt：\n{prompt}\n")
            response = await self._aask(prompt)
            end_time = time.time()
            time_cost = end_time - start_time
            return prompt, response, time_cost


class AdviceDataProcess(AbstractRoleAction):
      name: str = "AdviceDataProcess"
      profile: str = "处理建议信息数据"

      async def run(self, ADVICE_INFO: str, REQUIREMENTS: str):
            start_time = time.time()
            prompt = ADVICE_DATA_PROCESS_PROMPT.format(
                  ADVICE_INFO=ADVICE_INFO,
                  REQUIREMENTS=REQUIREMENTS
            )
            prompt += ADVICE_DATA_PROCESS_PROMPT_END
            response = await self._aask(prompt)
            end_time = time.time()
            time_cost = end_time - start_time
            return prompt, response, time_cost


class CoTDataGenerate(AbstractRoleAction):
      name: str = "CoTDataGenerate"
      profile: str = "生成CoT思维链数据"

      async def run(self, USER_QUERY: str, ANALYSE_INFO: str, ADVICE_INFO: str, REQUIREMENTS: str):
            start_time = time.time()
            prompt = COT_DATA_GENERATE_PROMPT.format(
                  USER_QUERY=USER_QUERY,
                  ANALYSE_INFO=ANALYSE_INFO,
                  ADVICE_INFO=ADVICE_INFO,
                  REQUIREMENTS=REQUIREMENTS
            )
            prompt += COT_DATA_GENERATE_PROMPT_END
            response = await self._aask(prompt)
            end_time = time.time()
            time_cost = end_time - start_time
            return prompt, response, time_cost


