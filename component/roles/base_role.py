import re
import os
import sys
import json
import time
from datetime import datetime

from metagpt.roles.role import Role
from metagpt.schema import Message
from metagpt.const import MESSAGE_ROUTE_TO_NONE

root_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, '../../')))
sys.path.append(root_dir)

from tools.logger import base_role_logger as logger

from sql_utils.DbRag import DbRag
from sql_utils.schema.TableCbtWorkflow2Result import TableCbtWorkflow2Result


class CBTAbstractRole(Role):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.dbrag = DbRag()
        self.sample_id = 0
        
        self.dummy_message: Message = Message(content="dummy message", send_to=MESSAGE_ROUTE_TO_NONE)
    
    async def build_pub_msg(self, delivery, todo, role, send_to=None):
        content_dict_str = json.dumps(delivery.get_attrs(), ensure_ascii=False, indent=4)
        to_pub_msg = Message(
            content=content_dict_str,
            role=role,
            cause_by=type(todo),
            send_to=send_to if send_to is not None else MESSAGE_ROUTE_TO_NONE
        )
        return to_pub_msg
    
    async def get_need_messages(self, msg, action_name, k=1):
        """ 过滤不需要的消息 """
        if k == 1:
            msg = [m for m in msg if str(m.cause_by).split('.')[-1] == action_name][-1]
        else:
            msg = [m for m in msg if str(m.cause_by).split('.')[-1] == action_name][-k:]
        return msg    
    
    async def concat_infos(self, **kwargs):
        return {k: v for k, v in kwargs.items()}
    
    ## =============== json tools ==================
    def replace_invalid_str(self, output_str):
        bad_list = ['“', '，', '。']
        for s in bad_list:
            output_str = output_str.replace(s, '')
        
        if output_str[-2:] == '""':
            output_str = output_str[:-1]
        
        return output_str
    
    async def clean_json_string(self, s):
        return s.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')

    async def extract_by_regex(self, result) -> str:
        
        """ 提取 reason 字段（简单字符串） """
        results = {}
        reason_pattern = r'"reason":\s*"([^"]*)"'
        reason_match = re.search(reason_pattern, result)
        if reason_match:
            results['reason'] = reason_match.group(1)
        else:
            results['reason'] = ""
        
        """ 提取 response 字段（可能是嵌套的JSON字符串） """
        # 方法1: 尝试匹配带引号的JSON字符串（包含转义引号）
        # 使用更智能的方法：找到 "response": " 之后，匹配到下一个不转义的引号
        response_pattern1 = r'"response":\s*"((?:[^"\\]|\\.)*)"'
        response_match1 = re.search(response_pattern1, result, re.DOTALL)
        if response_match1:
            response_str = response_match1.group(1)
            # 处理转义字符
            try:
                # 尝试解析转义的JSON字符串
                if response_str.strip().startswith('{'):
                    # 替换转义的引号
                    import json
                    # 先尝试直接解析
                    try:
                        json.loads(response_str)
                        results['response'] = response_str
                    except:
                        # 如果失败，尝试处理转义
                        unescaped = response_str.encode().decode('unicode_escape')
                        try:
                            json.loads(unescaped)
                            results['response'] = unescaped
                        except:
                            # 如果还是失败，尝试手动处理转义
                            manual_unescaped = response_str.replace('\\"', '"').replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
                            try:
                                json.loads(manual_unescaped)
                                results['response'] = manual_unescaped
                            except:
                                results['response'] = response_str
                else:
                    results['response'] = response_str
            except Exception as e:
                logger.warning(f"Error processing response string: {e}")
                results['response'] = response_str
        
        # 方法2: 如果方法1失败，尝试匹配不带引号的JSON对象
        if "response" not in results:
            # 使用括号匹配来找到完整的JSON对象
            response_pattern2 = r'"response":\s*(\{)(?:\s*)'
            match_start = re.search(response_pattern2, result)
            if match_start:
                start_pos = match_start.end() - 1  # JSON对象开始位置
                # 使用栈来匹配括号
                brace_count = 0
                in_string = False
                escape_next = False
                end_pos = start_pos
                for i in range(start_pos, len(result)):
                    char = result[i]
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = i + 1
                                break
                if brace_count == 0:
                    json_str = result[start_pos:end_pos]
                    try:
                        import json
                        json.loads(json_str)
                        results['response'] = json_str
                    except:
                        pass
        
        # 方法3: 如果还是失败，尝试简单匹配（可能格式有问题）
        if "response" not in results:
            # 尝试匹配到下一个字段或结束
            response_pattern3 = r'"response":\s*"([^"]*)"'
            response_match3 = re.search(response_pattern3, result, re.DOTALL)
            if response_match3:
                results['response'] = response_match3.group(1)
        
        if "response" not in results:
            logger.error(f"response not in results: {result[:500]}")
            results['response'] = ""
        
        return json.dumps(results, ensure_ascii=False)

    async def extract_think_by_regex(self, result):
        patterns = {
            'is_valid': r'"is_valid":\s*"([^"]*)"',
            'reason': r'"reason":\s*"([^"]*)"',
            'suggestion': r'"suggestion":\s*"([^"]*)"'
        }
        results = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, result)
            if match:
                results[key] = match.group(1)
        return json.dumps(results, ensure_ascii=False)
    
    def valid_types(self, save_data: dict):
        valid_types = {
            "USER_QUERY": str,
            "HISTORY_CHAT_RECORD": str,
            "HISTORY_PHRASE_STATUS": str,

            "ANALYSE_USER_PROFILE_PROMPT": str,
            "ANALYSE_USER_PROFILE_RESPONSE": str,
            "ANALYSE_USER_PROFILE_REASON": str,
            "ANALYSE_USER_PROFILE_TIME_COST": float,

            "ANALYSE_USER_PROBLEM_TYPE_PROMPT": str,
            "ANALYSE_USER_PROBLEM_TYPE_RESPONSE": str,
            "ANALYSE_USER_PROBLEM_TYPE_REASON": str,
            "ANALYSE_USER_PROBLEM_TYPE_TIME_COST": float,

            "ANALYSE_CONVERSATION_STATUS_PROMPT": str,
            "ANALYSE_CONVERSATION_STATUS_RESPONSE": str,
            "ANALYSE_USER_EMOTION_RESPONSE": str,
            "ANALYSE_CONVERSATION_STATUS_REASON": str,
            "ANALYSE_CONVERSATION_STATUS_TIME_COST": float,

            "GENERATE_DRAFT_RESPONSE_PROMPT": str,
            "GENERATE_DRAFT_RESPONSE_RESPONSE": str,
            "GENERATE_DRAFT_RESPONSE_REASON": str,
            "GENERATE_DRAFT_RESPONSE_TIME_COST": float,
            
            "GENERATE_RESPONSE_HISTORY": list,

            "CONTENT_CHECKER_PROMPT": str,
            "CONTENT_CHECKER_RESPONSE": str,
            "CONTENT_CHECKER_REASON": str,
            "CONTENT_CHECKER_TIME_COST": float,
            
            "CONTENT_CHECKER_HISTORY": list,

            "DYNAMIC_ROUTING_PROMPT": str,
            "DYNAMIC_ROUTING_RESPONSE": str,
            "DYNAMIC_ROUTING_REASON": str,
            "DYNAMIC_ROUTING_TIME_COST": float,

            "SEEKING_FOR_ADVICES_PROMPT": str,
            "SEEKING_FOR_ADVICES_RESPONSE": str,
            "SEEKING_FOR_ADVICES_REASON": str,
            "SEEKING_FOR_ADVICES_TIME_COST": float,

            "SEEKING_FOR_ADVICES_HISTORY": list,

            "GENERATE_FINAL_RESPONSE_PROMPT": str,
            "GENERATE_FINAL_RESPONSE_RESPONSE": str,
            "GENERATE_FINAL_RESPONSE_REASON": str,
            "GENERATE_FINAL_RESPONSE_TIME_COST": float,
            
            "TIMESTAMP_LOG":list,

            "LOOP_K": int,
            "CONV_K": int,
            "CONV_UUID": str,
            "TOTAL_ROUNDS": int,
        }
        
        new_save_data = {}
        for key, value in save_data.items():
            key_type = valid_types[key]
            value = key_type(value)
            new_save_data[key] = value
            
        return new_save_data
    
    ## =============== sft data tools ==================
    async def save_sft_data(self, save_data: dict):
        
        """ 处理一下需要处理的字段 """

        ## 丢掉不需要的字段
        save_data = self.valid_types(save_data)
        
        ## create dict data
        dict_upload = {
            **save_data,
        }

        # 创建数据库记录对象
        db_record = TableCbtWorkflow2Result(dict_upload)
        
        # 构建插入SQL
        fields = ", ".join(db_record.table_schema[1:])  # 跳过id字段
        placeholders = ", ".join(["%s"] * (len(db_record.table_schema) - 1))
        sql = f"INSERT INTO {db_record.table_name} ({fields}) VALUES ({placeholders})"
        
        now = datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # 准备数据
        values = [
            db_record.USER_QUERY,
            db_record.HISTORY_CHAT_RECORD,
            db_record.HISTORY_PHRASE_STATUS,

            db_record.ANALYSE_USER_PROFILE_PROMPT,
            db_record.ANALYSE_USER_PROFILE_RESPONSE,
            db_record.ANALYSE_USER_PROFILE_REASON,
            db_record.ANALYSE_USER_PROFILE_TIME_COST,

            db_record.ANALYSE_USER_PROBLEM_TYPE_PROMPT,
            db_record.ANALYSE_USER_PROBLEM_TYPE_RESPONSE,
            db_record.ANALYSE_USER_PROBLEM_TYPE_REASON,
            db_record.ANALYSE_USER_PROBLEM_TYPE_TIME_COST,

            db_record.ANALYSE_CONVERSATION_STATUS_PROMPT,
            db_record.ANALYSE_CONVERSATION_STATUS_RESPONSE,
            db_record.ANALYSE_USER_EMOTION_RESPONSE,
            db_record.ANALYSE_CONVERSATION_STATUS_REASON,
            db_record.ANALYSE_CONVERSATION_STATUS_TIME_COST,

            db_record.GENERATE_DRAFT_RESPONSE_PROMPT,
            db_record.GENERATE_DRAFT_RESPONSE_RESPONSE,
            db_record.GENERATE_DRAFT_RESPONSE_REASON,
            db_record.GENERATE_DRAFT_RESPONSE_TIME_COST,

            db_record.CONTENT_CHECKER_PROMPT,
            db_record.CONTENT_CHECKER_RESPONSE,
            db_record.CONTENT_CHECKER_REASON,
            db_record.CONTENT_CHECKER_TIME_COST,

            db_record.DYNAMIC_ROUTING_PROMPT,
            db_record.DYNAMIC_ROUTING_RESPONSE,
            db_record.DYNAMIC_ROUTING_REASON,
            db_record.DYNAMIC_ROUTING_TIME_COST,

            db_record.SEEKING_FOR_ADVICES_PROMPT,
            db_record.SEEKING_FOR_ADVICES_RESPONSE,
            db_record.SEEKING_FOR_ADVICES_REASON,
            db_record.SEEKING_FOR_ADVICES_TIME_COST,

            db_record.GENERATE_FINAL_RESPONSE_PROMPT,
            db_record.GENERATE_FINAL_RESPONSE_RESPONSE,
            db_record.GENERATE_FINAL_RESPONSE_REASON,
            db_record.GENERATE_FINAL_RESPONSE_TIME_COST,
            json.dumps(db_record.TIMESTAMP_LOG),
            db_record.LOOP_K,
            db_record.CONV_K,
            db_record.CONV_UUID,
            db_record.TOTAL_ROUNDS,
            
            time_str,  # created_at
            time_str   # updated_at
        ]
        
        # 执行插入
        self.dbrag.insert_sql_data(sql, values)
        
        logger.success(f"Successfully saved data to database table `{db_record.table_name}`")
