import os, json, time
import httpx
import uuid
import asyncio
import argparse
from tqdm import tqdm, trange
from typing import Optional
from loguru import logger

from tools.logger import chat_logger

def configs():
      parser = argparse.ArgumentParser()
      
      parser.add_argument('--ip', default='0.0.0.0', type=str)
      parser.add_argument('--port', default='8889', type=str)
      
      parser.add_argument('--max_workers', type=int, default=1)

      parser.add_argument('--agent_max_react_times', type=int, default=2)
      parser.add_argument('--max_loop_times', type=int, default=0)
      parser.add_argument('--timeout', type=int, default=600)
      
      args = parser.parse_args()
      return args


async def request_for_response(
      args, query, 
      history_chat_record, history_todo_actions,history_user_profile,
      conv_k, conv_uuid, total_rounds, client, service_url
):
      """ request """
      data_agent_request = {
            "user_query": query,
            "history_chat_record": history_chat_record,
            "history_phrase_status": history_todo_actions,
            "history_user_profile": history_user_profile,
            "conv_k": conv_k,
            "conv_uuid": conv_uuid,
            "total_rounds": total_rounds,
            "max_loop_times": args.max_loop_times,
            "agent_max_react_times": args.agent_max_react_times,
            "timeout": args.timeout
      }
      
      ## generate data
      response = await client.post(
            service_url, 
            json=data_agent_request
      )
      return response.json()


async def request_for_one_turn(
      args, query, 
      history_chat_record, history_todo_actions,history_user_profile,
      conv_k, conv_uuid, total_rounds
):
      
      service_url = f'http://{args.ip}:{args.port}/generate_data'

      timeout = httpx.Timeout(args.timeout, read=None, connect=None)
      async with httpx.AsyncClient(timeout=timeout) as client:
            response = await request_for_response(
                  args, query, 
                  history_chat_record, history_todo_actions,history_user_profile,
                  conv_k, conv_uuid, total_rounds, client, service_url
            )
            return_info = response["return_info"]
            response = return_info["response"]
            phrase = return_info["phrase"]
            extra_infos = return_info["extra_infos"]
            return response, phrase, extra_infos


async def request_for_one_sample(args, conversation, todo_actions_list,history_user_profile, conv_uuid=''):
      
      if conv_uuid == "":
            conv_uuid = str(uuid.uuid4())
            
      total_rounds = len(conversation)
      logger.info(f"conv_uuid: {conv_uuid}, total_rounds: {total_rounds}")
      
      start_time = time.time()
      
      if len(conversation) == 1:
            finished_conv = []
            last_conv = conversation[0]
            history_chat_record = []
      else:
            finished_conv = conversation[:-1]
            last_conv = conversation[-1]
            history_chat_record = []
            for nc in finished_conv:
                  history_chat_record.append({"human": nc['human'], "assistant": nc['assistant']})
      
      now_conv_num = len(conversation)
      history_chat_record = json.dumps(history_chat_record, ensure_ascii=False)
      history_todo_actions = json.dumps(todo_actions_list, ensure_ascii=False)
      
      logger.info(f"start process round {total_rounds} ...")
      
      now_start_time = time.time()
      
      query = last_conv['human']
      
      response, todo_actions, extra_infos = await request_for_one_turn(
            args, query, 
            history_chat_record, history_todo_actions,history_user_profile,
            conv_k=now_conv_num,
            conv_uuid=conv_uuid,
            total_rounds=total_rounds
      )
      
      last_conv = {"human": query, "assistant": response}
      todo_actions_list.append(todo_actions)

      now_end_time = time.time()
      logger.info(f"[round {now_conv_num} time cost]: {(now_end_time - now_start_time)/60:.2f} min.")
      
      end_time = time.time()
      logger.info(f"[conversation time cost]: {(end_time - start_time)/60:.2f} min.")

      conversation[-1] = last_conv
      
      return conversation, todo_actions_list, extra_infos, conv_uuid


async def main():
      args = configs()

      # conv_uuid = ''
      conv_uuid = str(uuid.uuid4())
      todo_actions_list = []
      conversation = []
      history_user_profile = ''
      # conversation = [
      #       {
      #             "human": "我是一位母亲，今年48岁，常常不知道该怎么表达对女儿的爱，和女儿对话总会让女儿生气，甚至会不理我，不接受我，想逃离我，我不知道如何与孩子说话，才能让孩子快乐，不会让孩子讨厌我",
      #             "assistant": "我能感受到您作为母亲对女儿那份深沉而细腻的爱，以及您现在面临的困惑和焦虑。面对这样的挑战，您感到非常内疚，担心自己的言行会让女儿感到不快，甚至想要远离您。请相信，您并不是孤军奋战，很多家长都会遇到类似的难题。您愿意分享最近一次让你们关系变得紧张的具体情况吗？这样我可以更好地了解您的处境，我们一起来寻找解决的方法。", 
      #       }
      # ]
      
      while True:
            
            user_input = input("请输入你的问题（输入 exit 或 退出 结束）：")
            if user_input.lower() in ["exit", "q", "停止"]:
                  print("对话结束。")
                  break
            
            conversation.append({"human": user_input})
            
            conversation, todo_actions_list, extra_infos, conv_uuid = await request_for_one_sample(
                  args, conversation, todo_actions_list, history_user_profile,
                  conv_uuid
            )
            
            last_turn = conversation[-1]
            history_user_profile = extra_infos['ANALYSE_USER_PROFILE_RESPONSE']
            
            logger.info(f"[当前对话阶段]：{todo_actions_list[-1]}\n")
            logger.info(f"[用户]：{last_turn['human']}\n")
            logger.info(f"[草稿回复]：{extra_infos['GENERATE_DRAFT_RESPONSE_RESPONSE']}\n")
            logger.info(f"[最终回复]: {last_turn['assistant']}\n")      
            
            # chat_logger.info(f"\n>>> 历史对话记录：\n{extra_infos['HISTORY_CHAT_RECORD']}\n")
            # chat_logger.info(f"\n>>> 用户当前咨询问题：\n{extra_infos['USER_QUERY']}\n")
            # chat_logger.info(f"\n>>> 所有回复：\n{extra_infos['GENERATE_RESPONSE_HISTORY']}\n")
            
            # logger.info(f"评分信息\n: {extra_infos['CONTENT_CHECKER_HISTORY']}")
            # logger.info(f"回复信息\n: {extra_infos['GENERATE_RESPONSE_HISTORY']}")
            # logger.info(f"建议信息\n: {extra_infos['SEEKING_FOR_ADVICES_HISTORY']}")


asyncio.run(main())
