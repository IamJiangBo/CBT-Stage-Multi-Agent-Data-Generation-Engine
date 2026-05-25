import os
import re
import sys
import json
import time

from typing import List

from metagpt.schema import Message
from metagpt.const import MESSAGE_ROUTE_TO_NONE
from metagpt.roles.role import RoleReactMode

from .base_role import CBTAbstractRole

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from actions.analyse_conversation_status_action import (
    AnalyseConversationStatus
)

from prompts.analyse_conversation_status.requirements import (
      ANALYSE_CONVERSATION_STATUS_REQUIREMENTS
)


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from component.obj.delivery import DeliveryObj

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import analyse_conversation_status_logger as logger


class AnalyseConversationStatusAgent(CBTAbstractRole):
      name: str = "Analyse Conversation Status Agent"
      profile: str = "分析对话状态专家"
      max_react_times: int = 3
      
      def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.set_actions([AnalyseConversationStatus])

      async def extract_by_regex_analyse_conversation_status(self, response):
            """提取chat_stage、user_emotion和reason字段"""
            results = {}
            
            # 使用更精确的正则表达式，避免匹配到其他JSON内容
            # 匹配 "chat_stage": "..." 格式，但不匹配包含其他JSON字段的内容
            patterns = {
                  'chat_stage': r'"chat_stage"\s*:\s*"([^"]*)"',
                  'user_emotion': r'"user_emotion"\s*:\s*"([^"]*)"',
                  'reason': r'"reason"\s*:\s*"((?:[^"\\]|\\.)*)"'
            }
            
            for key, pattern in patterns.items():
                  match = re.search(pattern, response)
                  if match:
                        value = match.group(1)
                        # 处理转义字符
                        if key == 'reason':
                              try:
                                    value = value.encode().decode('unicode_escape')
                              except:
                                    pass
                        # 清理值，确保不包含其他JSON字段的开始标记
                        if '"' in value and '{' in value:
                              # 如果值包含引号和花括号，可能是误匹配，只取引号前的内容
                              value = value.split('"')[0] if value.split('"')[0] else value
                        results[key] = value
                  else:
                        # 如果匹配失败，设置默认空值
                        results[key] = ""
            
            # 确保所有字段都存在
            if "chat_stage" not in results:
                  results["chat_stage"] = ""
            if "user_emotion" not in results:
                  results["user_emotion"] = ""
            if "reason" not in results:
                  results["reason"] = ""
            
            return json.dumps(results, ensure_ascii=False)
      
      async def process_analyse_conversation_status(self, todo, REQUIREMENTS, **kwargs):
            
            prompt, raw_response, time_cost = await todo.run(
                  USER_QUERY=kwargs['USER_QUERY'],
                  HISTORY_CHAT_RECORD=kwargs['HISTORY_CHAT_RECORD'],
                  REQUIREMENTS=REQUIREMENTS
            )
            
            # 保存原始响应以便调试
            original_response = raw_response
            
            try:
                  parsed_response = json.loads(raw_response)
            except Exception as e:
                  logger.warning(f"JSON parse failed, trying regex extraction. Error: {str(e)}, Response preview: {raw_response[:500]}")
                  try:
                        extracted_response = await self.extract_by_regex_analyse_conversation_status(raw_response)
                        parsed_response = json.loads(extracted_response)
                  except Exception as e2:
                        logger.error(f"Regex extraction also failed. Error: {str(e2)}, Raw response: {raw_response[:1000]}")
                        # 解析失败，返回默认值
                        return prompt, "阶段1", "初步信任", f"解析失败：{str(e2)}", time_cost
            
            # 安全地提取字段
            chat_stage = parsed_response.get("chat_stage", "")
            user_emotion = parsed_response.get("user_emotion", "")
            reason = parsed_response.get("reason", "")
            
            # 验证和清理字段值
            # 清理chat_stage：移除可能误匹配的其他JSON内容
            if chat_stage:
                  # 如果包含引号或花括号，可能是误匹配，只取第一个有效部分
                  if '"' in chat_stage or '{' in chat_stage:
                        # 找到第一个引号或花括号的位置，只保留之前的内容
                        for char in ['"', '{']:
                              if char in chat_stage:
                                    chat_stage = chat_stage.split(char)[0].strip()
                                    break
            
            # 清理user_emotion：同样处理
            if user_emotion:
                  if '"' in user_emotion or '{' in user_emotion:
                        for char in ['"', '{']:
                              if char in user_emotion:
                                    user_emotion = user_emotion.split(char)[0].strip()
                                    break
            
            # 验证字段值是否为空或无效
            if not chat_stage or not chat_stage.strip():
                  logger.warning(f"chat_stage is empty or invalid, using default")
                  chat_stage = "阶段1"
            if not user_emotion or not user_emotion.strip():
                  logger.warning(f"user_emotion is empty or invalid, using default")
                  user_emotion = "初步信任"
            if not reason:
                  reason = "解析失败"
            
            """ fix response """
            if '一' in chat_stage:
                  chat_stage = chat_stage.replace("一", "1")
            if '二' in chat_stage:
                  chat_stage = chat_stage.replace("二", "2")
            if '三' in chat_stage:
                  chat_stage = chat_stage.replace("三", "3")
            
            """ 防止输出不是格式化 """
            if '1' in chat_stage:
                  chat_stage = '阶段1'
            elif '2' in chat_stage:
                  chat_stage = '阶段2'
            elif '3' in chat_stage:
                  chat_stage = '阶段3'
            
            return prompt, chat_stage, user_emotion, reason, time_cost
      
      async def _act(self) -> Message:

            logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")

            logger.info("\033[32m>>> start action: AnalyseConversationStatus\033[0m")
            
            msg = self.get_memories(k=1)[0]
      
            received_infos = json.loads(msg.content)
            USER_QUERY = received_infos['user_query']
            HISTORY_PHRASE_STATUS = received_infos['history_phrase_status']
            HISTORY_CHAT_RECORD = received_infos['history_chat_record']
            CONV_K = received_infos['conv_k']
            CONV_UUID = received_infos['conv_uuid']
            TOTAL_ROUNDS = received_infos['total_rounds']
            
            act_start = time.time()
            prompt, chat_stage, user_emotion, reason, time_cost = await self.process_analyse_conversation_status(
                  todo=self.rc.todo, 
                  USER_QUERY=USER_QUERY,
                  HISTORY_CHAT_RECORD=HISTORY_CHAT_RECORD,
                  REQUIREMENTS=ANALYSE_CONVERSATION_STATUS_REQUIREMENTS
            )
            act_end = time.time()
            
            TIMESTAMP_LOG = received_infos['TIMESTAMP_LOG']
            TIMESTAMP_LOG.append({f"{self.rc.todo.name}": [act_start,act_end]})
            
            CONCAT_INFO = {
                  
                  "USER_QUERY": USER_QUERY,
                  "HISTORY_PHRASE_STATUS": HISTORY_PHRASE_STATUS,
                  "HISTORY_CHAT_RECORD": HISTORY_CHAT_RECORD,
                  "CONV_K": CONV_K,
                  "CONV_UUID": CONV_UUID,
                  "TOTAL_ROUNDS": TOTAL_ROUNDS,
                  
                  "ANALYSE_CONVERSATION_STATUS_PROMPT": prompt,
                  "ANALYSE_CONVERSATION_STATUS_RESPONSE": chat_stage,
                  "ANALYSE_USER_EMOTION_RESPONSE": user_emotion,
                  "ANALYSE_CONVERSATION_STATUS_REASON": reason,
                  "ANALYSE_CONVERSATION_STATUS_TIME_COST": time_cost,
                  
                  "TIMESTAMP_LOG": TIMESTAMP_LOG
            }
            
            delivery = DeliveryObj()
            delivery.add_attrs(**CONCAT_INFO)

            logger.info(f"\n\n>>> 当前对话状态：\n{chat_stage}\n\n用户心理状态：\n{user_emotion}\n\n判别原因：\n{reason}\n\n")
            
            to_pub_msg = await self.build_pub_msg(delivery, self.rc.todo, self.profile, "GenerateResponseAgent")
            self.rc.env.publish_message(to_pub_msg)
            self.rc.memory.add(to_pub_msg)

            return to_pub_msg