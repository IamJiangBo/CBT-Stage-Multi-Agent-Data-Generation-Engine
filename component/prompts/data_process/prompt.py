
""" 
分析数据处理
"""
ANALYSE_DATA_PROCESS_PROMPT = """
Roles:
你是一个内容梳理专家。以下的内容由：用户画像分析、用户问题分析、对话状态分析三部分组成。
请根据要求，将内容整理并优化成一段连贯流畅的话。

## 内容
{ANALYSE_INFO}

其中对话阶段分为以下几个阶段：阶段1：问题引入——澄清与共情；阶段2：问题探索——识别与挑战不合理信念；阶段3：问题解决——提供策略与鼓励

## 要求
{REQUIREMENTS}

请严格按照以下 JSON 格式返回结果，不要添加任何其他内容：
"""
ANALYSE_DATA_PROCESS_PROMPT_END = """
{
      "response": "梳理后的内容，每个部分分段展示",
      "reason": "说明梳理过程"
}
"""


""" 
建议信息整合处理
"""
ADVICE_DATA_PROCESS_PROMPT = """
Roles:
你是一个建议整合专家。以下建议信息由一条或多条建议组成。
请根据要求，将所有建议信息整合，形成一段连贯、实用的建议内容。

## 建议信息
{ADVICE_INFO}

## 要求
{REQUIREMENTS}

请严格按照以下 JSON 格式返回结果，不要添加任何其他内容：
"""
ADVICE_DATA_PROCESS_PROMPT_END = """
{
      "response": "整合后的建议内容",
      "reason": "整合说明和理由"
}
"""


""" 
CoT 思维链数据生成
"""
COT_DATA_GENERATE_PROMPT = """
Roles:
你是一个思维链数据生成专家。请基于用户查询、分析信息和建议信息，思考应该如何回复，展示从问题分析到最终建议的完整思考过程。

## 用户查询
{USER_QUERY}

## 分析信息
{ANALYSE_INFO}

## 建议信息
{ADVICE_INFO}

## 要求
{REQUIREMENTS}

请严格按照以下 JSON 格式返回结果，不要添加任何其他内容：
"""
COT_DATA_GENERATE_PROMPT_END = """
{
      "response": "思考该如何回复的过程，不要包含具体回复内容",
      "reason": "这么思考的原因"
}
"""

