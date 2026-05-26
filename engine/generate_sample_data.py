#!/usr/bin/env python3

from curses import COLOR_CYAN
import uuid
import time
import requests
import json
import datetime
import os, signal
from tool_weaker import get_response
from weaker_agent import generate_prompt_info, initialize_clients, judge_end, judge_questions
import time
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor,as_completed
from openai import OpenAI
import openai
import uuid
import re
import pandas as pd
from dotenv import load_dotenv
import tiktoken
import random
from thefuzz import fuzz
from tools.logger import generate_sample_logger as logger
encoding = tiktoken.get_encoding("cl100k_base")


from component.prompts.patient.prompt import (
      PATIENT_EMOTION_LIST_PROMPT,
      PATIENT_STYLE_LIST,
      PATIENT_EMOTION_REQUIREMENTS,
      PATIENT_EMOTION_SYSTEM_PROMPT,
      PATIENT_PROMPT,
      PATIENT_SYSTEM_PROMPT
)

_ = load_dotenv("/data/.env_secret")

LLM_SERVER_URL = os.getenv("LLM_SERVER_URL")
API_KEY = os.getenv("XINLIXUE_API_KEY")
if not LLM_SERVER_URL or not API_KEY:
    raise Exception(
        "Failed to load environment variables. Please configure LLM_SERVER_URL and XINLIXUE_API_KEY in `.env` or `/data/.env_secret`."
    )
MODEL_NAME = os.getenv("MODEL_NAME")

CBT_IP = os.getenv("CBT_IP", "127.0.0.1")
CBT_PORT = os.getenv("CBT_PORT", "1111")
CBT_URL  = f'http://{CBT_IP}:{CBT_PORT}/generate_data'

local_client, local_model_name = initialize_clients()

TIMEOUT  = 6000   # seconds
MAX_LOOP_TIME = 3
AGENT_MAX_REACT_TIME = 3

def request_for_response(index,
        query,
        history_chat_record, history_phrase_status,history_user_profile,
        conv_k, conv_uuid, total_rounds, session, service_url
):
    sucess_msg = None
    failure_msg = "CBT service response error. Please check the logs."
    """Synchronous POST request"""
    data_agent_request = {
        "user_query": query,
        "history_chat_record": history_chat_record,
        "history_phrase_status": history_phrase_status,
        "history_user_profile": history_user_profile,
        "conv_k": conv_k,
        "conv_uuid": conv_uuid,
        "total_rounds": total_rounds,
        "max_loop_times": MAX_LOOP_TIME,
        "agent_max_react_times": AGENT_MAX_REACT_TIME,
        "timeout": TIMEOUT
    }
    try:
        response = session.post(
            service_url,
            json=data_agent_request,
            timeout=TIMEOUT           # requests timeout (seconds)
        )
        response.raise_for_status()

        return True, response.json(), sucess_msg
    except requests.exceptions.Timeout as e:
        logger.error(f"Request timeout: sample {index + 1}, error: {e}")
        return False, None, failure_msg + f"\t{e}"
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: sample {index + 1}, error: {e}")
        return False, None, failure_msg + f"\t{e}"
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: sample {index + 1}, error: {e}")
        return False, None, failure_msg + f"\t{e}"
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: sample {index + 1}, error: {e}")
        return False, None, failure_msg + f"\t{e}"
    except ValueError as e:
        logger.error(f"Invalid response format: sample {index + 1}, error: {e}, response: {response.text}")
        return False, None, failure_msg + f"\t{e}"
    except Exception as e:
        logger.error(f"Unexpected error: sample {index + 1}, error: {e}, response: {response.text}")
        return False, None, failure_msg + f"\t{e}"

def request_for_one_turn(index,
        query,
        history_chat_record, history_phrase_status,history_user_profile,
        conv_k, conv_uuid, total_rounds
):

    # requests timeout can be a scalar or a (connect, read) tuple
    with requests.Session() as session:
        status, response, status_msg = request_for_response(index,
            query,
            history_chat_record, history_phrase_status,history_user_profile,
            conv_k, conv_uuid, total_rounds,
            session, CBT_URL
        )
        if not status:
            raise Exception(status_msg)

        return_info = response["return_info"]
        response_text = return_info["response"]
        phrase = return_info["phrase"]
        extra_infos = return_info["extra_infos"]
        return response_text, phrase, extra_infos

def request_for_one_sample(index, conversation, phrase_status_list,history_user_profile, conv_uuid=''):
    if conv_uuid == "":
        conv_uuid = str(uuid.uuid4())

    total_rounds = len(conversation)

    # Build conversation history
    if len(conversation) == 1:
        finished_conv = []
        last_conv = conversation[0]
        history_chat_record = []
    else:
        finished_conv = conversation[:-1]
        last_conv = conversation[-1]
        history_chat_record = [
            {"human": nc['human'], "assistant": nc['assistant']}
            for nc in finished_conv
        ]

    now_conv_num = len(conversation)
    history_chat_record = json.dumps(history_chat_record, ensure_ascii=False)
    history_phrase_status = json.dumps(phrase_status_list, ensure_ascii=False)

    query = last_conv['human']
    emo = last_conv['emo']

     # Request counselor reply
    response, phrase_status, extra_infos = request_for_one_turn(index,
        query,
        history_chat_record, history_phrase_status,history_user_profile,
        conv_k=now_conv_num,
        conv_uuid=conv_uuid,
        total_rounds=total_rounds
    )

    last_conv = {"emo":emo,"human": query, "assistant": response}
    phrase_status_list.append(phrase_status)

    conversation[-1] = last_conv
    return conversation, phrase_status_list, extra_infos, conv_uuid

def response_extract(index, raw):
    # Remove thinking chains, markdown wrappers, etc.
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text.strip())

    # Extract JSON body
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {"response": [], "reason": []}

    try:
        data = json.loads(match.group(0))
    except Exception:
        # Try simple repair (remove trailing commas)
        fixed = re.sub(r",\s*([\]}])", r"\1", match.group(0))
        try:
            data = json.loads(fixed)
        except Exception as e:
            raise ValueError(f"Failed to parse emotion list.\n\nInput: {raw}\nError: {e}\n\n") from e
    # Extract fields with fallback handling
    response = data.get("response") or []
    reason = data.get("reason") or []

    if isinstance(response, str):
        response = [response]
    if isinstance(reason, str):
        reason = [reason]
    return {"response": response, "reason": reason}

def clean_patient_reply(text):
    # Remove tone/action descriptions in parentheses
    text = re.sub(r'[\(\（][^\)\）]{0,15}[\)\）]', '', text)
    # Strip extra Claude-style segments
    if "claude" in text.lower():
        text = re.split(r'(?i)claude\s*:', text)[0]
    return text.strip()

def parse_json(raw_str):
    if isinstance(raw_str, (dict, list)):
        return raw_str
    try:
        # First attempt: parse directly
        return json.loads(raw_str)
    except json.JSONDecodeError:
        cleaned = raw_str.replace("'", '"')
        cleaned1 = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        cleaned2 = re.sub(r'\n', '', cleaned1)
        return json.loads(cleaned2)

class GPTChatHttpClient:
    """GPT chat client (HTTP version)"""

    def __init__(self, server_url, API_KEY, MODEL_NAME):
        self.server_url = server_url
        self.current_model = MODEL_NAME
        self.supported_models = [
            "gpt-3.5-turbo",
            "gpt-4",
            "chatgpt-4o-latest",
            "deepseek-r1",
            "deepseek-v3",
            "qwen-turbo",
            "gpt-5-mini",
            "gpt-5"
        ]
        self.session_id = str(uuid.uuid4())
        self.client = OpenAI(base_url=server_url, api_key=API_KEY)
    def set_model(self, model):
        """Set the active model."""
        if model in self.supported_models:
            self.current_model = model
            logger.info(f"Switched to model: {model}")
            return True
        else:
            logger.info(f"Unsupported model: {model}")
            logger.info(f'Supported models: {", ".join(self.supported_models)}')
            return False

    def list_models(self):
        """List supported models."""
        logger.debug("\nSupported models:")
        for i, model in enumerate(self.supported_models, 1):
            marker = " (current)" if model == self.current_model else ""
            logger.debug(f"{i:2d}. {model}{marker}")


    def select_model_on_startup(self):
        """Select a model at startup."""
        logger.debug("\nSupported models:")
        for i, model in enumerate(self.supported_models, 1):
            marker = " (default)" if model == self.current_model else ""
            logger.debug(f"{i:2d}. {model}{marker}")
        logger.debug(
            f"\nSelect a model within 10 seconds (1-{len(self.supported_models)}), or press Enter for the default"
        )
        logger.debug(f"Default model: {self.current_model}")

        import threading

        user_input = [""]  # mutable container
        input_received = threading.Event()

        def get_input():
            try:
                result = input(
                    "\nEnter choice (1-{}) or press Enter: ".format(len(self.supported_models))
                )
                user_input[0] = result
                input_received.set()
            except (EOFError, KeyboardInterrupt):
                input_received.set()

        input_thread = threading.Thread(target=get_input, daemon=True)
        input_thread.start()

        for i in range(10, 0, -1):
            if input_received.is_set():
                break
            logger.debug(f"\rCountdown: {i}s...", end="", flush=True)
            time.sleep(1)

        if input_received.is_set() and user_input[0]:
            choice = user_input[0].strip()
            if choice:
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(self.supported_models):
                        selected_model = self.supported_models[choice_num - 1]
                        self.current_model = selected_model
                        logger.debug(f"\nSelected model: {selected_model}")
                        return
                    else:
                        logger.debug(f"\nInvalid choice, using default model: {self.current_model}")
                        return
                except ValueError:
                    logger.debug(f"\nInvalid input, using default model: {self.current_model}")
                    return
            else:
                logger.debug(f"\nUsing default model: {self.current_model}")
                return

        logger.debug(f"\nTime is up. Using default model: {self.current_model}")

    def get_value_by_fuzzy_key(self, data_dict: dict, search_key: str):
        """
        Get a dictionary value via fuzzy key matching.
        """
        if search_key in data_dict:
            print(f"Exact key match: '{search_key}'")
            return data_dict[search_key]

        if not data_dict:
            return None  # empty dict

        best_match_key = None
        highest_ratio = 0


        for key in data_dict.keys():
            # fuzz.ratio returns a similarity score from 0 to 100
            ratio = fuzz.ratio(search_key, key)
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match_key = key

        # Treat matches above 60 as related; otherwise raise.
        if highest_ratio > 60:
            logger.info(f"No exact match. Fuzzy matched key: '{best_match_key}' (similarity: {highest_ratio}%)")
            return data_dict[best_match_key]
        else:
            raise ValueError(f"No exact match and no sufficiently similar key (best similarity: {highest_ratio}%).")

    def send_message(self, index, content, system_prompt, model=None):
        """Send a message to the server over HTTP and return the reply."""
        resp = None
        if model is None:
            model = self.current_model
        elif model not in self.supported_models:
            logger.info(f"Model {model} is not supported; using default model {self.current_model}")
            model = self.current_model
        try:
            resp = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": content}],
                stream=False,
                user=self.session_id,
            #     extra_body={
            #     "chat_template_kwargs": {"enable_thinking": False},
            # },
            )
            return resp.choices[0].message.content, self.session_id
        except openai.APIStatusError as e:
            if e.body.get("error", {}).get("code") == "pre_consume_token_quota_failed":
                raise ValueError(f"Failed to generate emotion list for sample {index + 1}: account quota exceeded. Details: {e}") from e
            else:
                raise ValueError(f"Failed to generate emotion list for sample {index + 1}: upstream service error. Details: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to generate emotion list for sample {index + 1}. Model response: {resp}, \n\nInput:\n {content}\n\nError: {e}\n") from e

    def show_help(self):
        """Show help information."""
        print("\nHelp:")
        print("- quit/exit/q: Exit the program")
        print("- help: Show this help message")
        print("- models: List supported models")
        print("- model <name>: Switch to the specified model")
        print("- Any other input: Send a message to GPT")
    
    def strip_quotes_fast(self, s: str) -> str:
        start, end = 0, len(s)
        while end - start >= 2 and s[start] == s[end - 1] and s[start] in {'"', "'"}:
            start += 1
            end -= 1
        return s[start:end]

    def run_auto_chat_cbt(self, index, role_desc, patient_reply, max_rounds=5):
        """
        Run role-play auto conversation.
        All exceptions propagate to the caller; outer layer records failures.
        """
        MAX_ATTEMPTS = 3
        attempts = 0
        patient_style=PATIENT_STYLE_LIST[random.randint(0, len(PATIENT_STYLE_LIST)-1)]
        emo_list_prompt = PATIENT_EMOTION_LIST_PROMPT.format(
            patient_style=patient_style,
            patient_identity=role_desc,
            patient_reply=patient_reply,
            min_length=max_rounds-5,
            max_length=max_rounds+5
        )
        try:
            emo_list_response, session_id_from_header = self.send_message(index, emo_list_prompt, PATIENT_EMOTION_SYSTEM_PROMPT)
            emo_list_response = response_extract(index, emo_list_response)
        except Exception as e:
            raise RuntimeError(f"Failed to generate emotion list. Check send_message or response_extract. Details: {e}") from e
        emo_list = emo_list_response["response"]

        logger.info(f'Sample {index + 1}\tpatient type: {re.split(r"[：:]", patient_style, maxsplit=1)[0]}\temotion curve:\t{emo_list}')
        conv_uuid = ''
        phrase_status_list = []
        conversation = []
        chat_details = []
        history_user_profile = ''
        
        conversation.append({"human": self.strip_quotes_fast(patient_reply),"emo":""})
        chat_details.append({"emo":'',"assistant":'',"human": patient_reply,"patient_infos":[],"assist_infos":[]})

        # Multi-turn conversation
        patient_total_time = 0
        assistant_total_time = 0
        current_round = 1
        while current_round <= len(emo_list):
            # Counselor reply (may raise)
            t11 = time.time()
            try:

                conversation, phrase_status_list, extra_infos, conv_uuid = request_for_one_sample(index,
                    conversation, phrase_status_list,history_user_profile, conv_uuid
                )
            except Exception as e:
                raise RuntimeError(f"Failed to get counselor reply. Check request_for_one_sample. Details: {str(e)}") from e
            spend_time = time.time() - t11
            assistant_total_time += spend_time

            next_emo = emo_list[current_round - 1]

            emo_requirement = self.get_value_by_fuzzy_key(PATIENT_EMOTION_REQUIREMENTS, next_emo)
            
            history_user_profile = extra_infos['ANALYSE_USER_PROFILE_RESPONSE']
            history_user_profile_dict = parse_json(history_user_profile)
            
            # Profile fields (Chinese keys from CBT agent ANALYSE_USER_PROFILE_RESPONSE)
            chat_topic = history_user_profile_dict['对话主题与核心困境']
            patient_state = history_user_profile_dict['病人核心状态']
            assist_progress = history_user_profile_dict['医生主要干预与治疗进展']
            patient_infos = history_user_profile_dict['病人信息点']
            assist_infos = history_user_profile_dict['医生信息点']
            
            history_user_profile = json.dumps(history_user_profile, ensure_ascii=False) if isinstance(history_user_profile, (dict, list)) else history_user_profile

            user_emotion = extra_infos['ANALYSE_USER_EMOTION_RESPONSE']
            counselor_reply = conversation[-1]['assistant']
            
            human_reply_last3 = "\n".join([f"{i+1}. {text}" for i, text in enumerate([item['human'] for item in conversation[-3:]])])
            # Patient reply
            patient_reminder_prompt = PATIENT_PROMPT.format(
                patient_identity=role_desc,
                patient_style=patient_style,
                pre_emotion=user_emotion,
                next_emotion=next_emo,
                emo_requirement=emo_requirement,
                chat_topic=chat_topic,
                patient_state=patient_state,
                assist_progress=assist_progress,
                patient_infos=patient_infos,
                patient_reply=human_reply_last3,
                counselor_reply=counselor_reply,
            )
            t12 = time.time()
            reply, session_id_from_header = self.send_message(index,patient_reminder_prompt, PATIENT_SYSTEM_PROMPT)
            patient_total_time += time.time()-t12

            if not reply:
                raise RuntimeError("GPT server returned no content (patient reply)")

            patient_reply = reply.get("content", reply) if isinstance(reply, dict) else reply
            if isinstance(patient_reply, list):
                patient_reply = patient_reply[0]['text']
            patient_reply = clean_patient_reply(patient_reply)
            conversation.append({"human": patient_reply,"emo":next_emo})
            chat_details.append({"emo":next_emo,"assistant":counselor_reply,"human": patient_reply})
            current_round += 1
            logger.debug(f"conv_uuid: {conv_uuid} --->>> sample {index + 1}, model {MODEL_NAME}: round {current_round} patient reply time: {time.time()-t12}")
            logger.debug(f"conv_uuid: {conv_uuid} --->>> sample {index + 1}, model {MODEL_NAME}: round {current_round} counselor reply time: {spend_time}")
            
        logger.debug(f"conv_uuid: {conv_uuid} --->>> sample {index + 1}, rounds {current_round}, patient total time: {patient_total_time}s, counselor total time: {assistant_total_time}s")

        # Final counselor reply (may also raise)
        try:
            conversation, phrase_status_list, extra_infos, conv_uuid = request_for_one_sample(index,
                conversation, phrase_status_list,history_user_profile, conv_uuid
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get counselor reply on final round. Check request_for_one_sample. Details: {str(e)}") from e

        return {
            "conv_uuid": conv_uuid,
            "role_desc": role_desc,
            "rounds": current_round,
            "conversation": conversation,
        }

    def _show_help(self):
        """Show help information."""
        print('\nHelp:')
        print('- quit/exit/q: Exit the program')
        print('- help: Show this help message')
        print('- status: Show connection status')
        print('- Any other input: Send a message to GPT')
    
    def _show_status(self):
        """Show status information."""
        print(f'\nStatus:')
        print(f'- Server URL: {self.server_url}')
        print(f'- Connection: {"connected" if self.connected else "disconnected"}')
        print(f'- Session: {"registered" if self.session_registered else "not registered"}')
        print(f'- Session ID: {self.session_id}')
        print(f'- Pending messages: {len(self.pending_messages)}')
        print(f'- Received responses: {len(self.responses)}')

def process_problem(index, total, problem_role, max_rounds, file_type='.jsonl'):

    COLOR_CYAN = "\033[96m"
    COLOR_YELLOW = "\033[93m"
    COLOR_RESET = "\033[0m"
    t1 = time.time()
    logger.info(f"Sample {index + 1}/{total}{COLOR_RESET}, starting... file type: {file_type}")
    client = GPTChatHttpClient(LLM_SERVER_URL, API_KEY, MODEL_NAME)
    try:
        if file_type == '.csv':
            patient_style=PATIENT_STYLE_LIST[random.randint(0, 4)]
            role_prompt, _ = generate_prompt_info(problem_role, patient_style)
            messages = [{"role": "system", "content": role_prompt}]
            # logger.info("Generating patient role via local Qwen...")
            response = get_response(messages, local_client, local_model_name, temperature=1.0, top_p=0.95)
            data = json.loads(response)
            role_desc = data.get("role_desc", "")
            problem = data.get("question", "")
        elif file_type == '.jsonl':
            problem = problem_role.get("problem")
            role_desc = problem_role.get("role_desc", "")
        
        if not role_desc: raise Exception("Provide role_desc or use .csv extension—system will auto-generate it from the file.")

    except Exception as e:
        logger.info(f"Failed to load patient role or problem for sample {COLOR_YELLOW}{index + 1}/{total}{COLOR_RESET}, error: {e}")
        raise e

    try:

        result = client.run_auto_chat_cbt(index, role_desc, problem, max_rounds)
        result["model_name"] = MODEL_NAME

        logger.info(f"Completed sample {COLOR_YELLOW}{index + 1}/{total}{COLOR_RESET}, elapsed: {time.time() - t1:.3f}s")
        return result

    except Exception as e:
        logger.info(f"Failed to process sample {COLOR_YELLOW}{index + 1}/{total}{COLOR_RESET}, error: {e}")
        raise e

def load_problems_csv(file_path):
    df = pd.read_csv(file_path, sep=',')
    problem_list =  df.to_dict(orient='records')
    return problem_list

def load_problems_jsonl(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        problem_list = [json.loads(line) for line in f]
    return problem_list

def main():
    """Main entry point."""
    num_conversations_to_generate = 11000

    # MAX_WORKERS = os.cpu_count()
    MAX_WORKERS = 25
    max_rounds = 10
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_json_path=f"./conversation_logs/auto_chat_results_{timestamp}_{num_conversations_to_generate}_{MODEL_NAME}.jsonl"
    os.makedirs(os.path.dirname(save_json_path), exist_ok=True)
    
    problem_text = "./problems/role_problem/test_problem_role_10.jsonl"
    # problem_text = "./problems/problem/problem.csv"
    file_type = problem_text[problem_text.rfind('.'):]  # jsonl or csv

    if file_type == '.csv':
        problem_list = load_problems_csv(problem_text)
    elif file_type == '.jsonl':
        problem_list = load_problems_jsonl(problem_text)
    else:
        raise Exception(f"Unsupported file format: {file_type}")

    # selected_indices = [13, 38, 56, 57]
    # problem_list = [problem_list[i] for i in selected_indices]
    problem_list = problem_list[0:num_conversations_to_generate]
    total = len(problem_list)
    logger.info(f"Starting sample generation. Total problems: {total}, workers: {MAX_WORKERS}")

    start_time = time.time()
    try:
        # Process problems in parallel
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks to the process pool
            futures = {executor.submit(process_problem, index, total, problem, max_rounds, file_type): problem for index, problem in enumerate(problem_list)}
            for future in tqdm(as_completed(futures), total=len(problem_list), desc="Progress"):
                try:
                    problem = futures[future]
                    sample_data = future.result()
                    if sample_data is not None:
                        # Write JSON only on success
                        with open(save_json_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps(sample_data, ensure_ascii=False) + "\n")
                    else:
                        raise Exception(f"Failed to save data; sample_data is: {sample_data}")

                except Exception as e:
                    logger.info(f"Task failed: {e}", "\n", problem, "\n")
    except KeyboardInterrupt:
        logger.info("Caught Ctrl+C, shutting down...")
        executor.shutdown(cancel_futures=True)
        os.killpg(os.getpgid(os.getpid()), signal.SIGKILL)  # force-kill process group
    
    logger.info(f"All tasks completed in {time.time() - start_time:.3f}s")
    logger.info(f"Results saved to: {save_json_path}")

  


if __name__ == '__main__':
    main()
