import os
import re
import sys
import json

from metagpt.actions import Action

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import base_role_logger as logger


class AbstractRoleAction(Action):
      async def _aask(self, prompt):
            content = await super()._aask(prompt)
            if '<think>' in content:
                  return content.split('</think>')[-1]
            else:
                  return content
            
      async def extract_by_regex(self, result) -> str:
            patterns = {
                  'response': r'"response":\s*"([^"]*)"',
                  'reason': r'"reason":\s*"([^"]*)"'
            }
            results = {}
            for key, pattern in patterns.items():
                  match = re.search(pattern, result)
                  if match:
                        results[key] = match.group(1)
            return json.dumps(results, ensure_ascii=False)
