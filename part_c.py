%%writefile part_c.py
import re
import json
import random
import time
import pandas as pd
from mock_llm import chat, reset, est_tokens, TransientLLMError

def redact_text(text):
    text, e_count = re.subn(r'[\w.+-]+@[\w-]+\.[\w.]+', '[EMAIL]', text)
    text, p_count = re.subn(r'\b[6-9]\d{9}\b', '[PHONE]', text)
    text, o_count = re.subn(r'ORD-\d{6}', '[ORDER_ID]', text)
    return text, e_count, p_count, o_count

def resilient_call(messages, system_prompt):
    base_delay = 0.05
    for attempt in range(3):
        try:
            full_msgs = [{"role": "system", "content": system_prompt}] + messages
            return chat(full_msgs)
        except TransientLLMError:
            wait = base_delay * (2 ** attempt) * random.uniform(0.9, 1.15)
            time.sleep(wait)
    raise RuntimeError("Failed after 3 retries")

def run_part_c():
    reset()
    tickets = pd.read_csv("data/raw/tickets.csv", keep_default_na=False)
    segments = pd.read_csv("outputs/customer_segments.csv")

    zero_prompt = "CLASSIFY. Allowed categories: billing, delivery, technical, fraud. Reply strictly in JSON: {\"category\": \"...\", \"reason\": \"...\"}"
    few_prompt = "CLASSIFY. EXAMPLES: {\"text\": \"Unauthorized transaction\", \"category\": \"fraud\"} Allowed categories: billing, delivery, technical, fraud. Reply strictly in JSON."

    results = []
    total_tokens = 0

    for idx, row in tickets.iterrows():
        tid = row['ticket_id']
        cid = row['customer_id']
        text = row['text']

        # 1. Input Guardrails
        if not text or not text.strip():
            results.append({'ticket_id': tid, 'customer_id': cid, 'status': 'skipped_empty', 'category': '', 'tokens_used': 0})
            continue

        if est_tokens(text) > 400:
            results.append({'ticket_id': tid, 'customer_id': cid, 'status': 'flagged_long', 'category': '', 'tokens_used': 0})
            continue

        # 2. Redaction
        redacted, _, _, _ = redact_text(text)

        # 4 & 5. Model call & Validation
        try:
            resp = resilient_call([{"role": "user", "content": redacted}], few_prompt)
            total_tokens += resp.usage.total_tokens
            content = resp.choices[0].message.content

            # Try parsing JSON
            cat = None
            try:
                parsed = json.loads(content)
                if parsed.get('category') in ['billing', 'delivery', 'technical', 'fraud']:
                    status = 'classified_json'
                    cat = parsed['category']
                else:
                    status = 'flagged_invalid_output'
            except json.JSONDecodeError:
                words = re.findall(r"[a-z]+", content.lower())
                allowed = ['billing', 'delivery', 'technical', 'fraud']
                matches = [w for w in allowed if w in words]
                if len(matches) == 1:
                    status = 'classified_keyword'
                    cat = matches[0]
                else:
                    status = 'flagged_invalid_output'
        except Exception:
            status = 'flagged_invalid_output'
            cat = None

        results.append({'ticket_id': tid, 'customer_id': cid, 'status': status, 'category': cat or '', 'tokens_used': total_tokens})

    res_df = pd.DataFrame(results)
    res_df = res_df.merge(segments[['customer_id', 'segment_name', 'is_premium']], on='customer_id', how='left')

    # Routing logic
    def route_ticket(r):
        if r['status'] in ['skipped_empty', 'flagged_long', 'flagged_invalid_output']:
            return 'human_review', 'NORMAL'
        if r['category'] == 'fraud':
            return 'security_team', 'HIGH'
        if r['is_premium'] == True:
            return 'premium_desk', 'HIGH'
        return 'support_queue', 'NORMAL'

    res_df[['route', 'priority']] = res_df.apply(lambda r: pd.Series(route_ticket(r)), axis=1)
    res_df.to_csv("outputs/triage_results.csv", index=False)

    # Demo budget file
    res_df.head(50).to_csv("outputs/triage_budget_demo.csv", index=False)
    print("Part C completed successfully.")

if __name__ == "__main__":
    run_part_c()%%writefile part_c.py
import re
import json
import random
import time
import pandas as pd
from mock_llm import chat, reset, est_tokens, TransientLLMError

def redact_text(text):
    text, e_count = re.subn(r'[\w.+-]+@[\w-]+\.[\w.]+', '[EMAIL]', text)
    text, p_count = re.subn(r'\b[6-9]\d{9}\b', '[PHONE]', text)
    text, o_count = re.subn(r'ORD-\d{6}', '[ORDER_ID]', text)
    return text, e_count, p_count, o_count

def resilient_call(messages, system_prompt):
    base_delay = 0.05
    for attempt in range(3):
        try:
            full_msgs = [{"role": "system", "content": system_prompt}] + messages
            return chat(full_msgs)
        except TransientLLMError:
            wait = base_delay * (2 ** attempt) * random.uniform(0.9, 1.15)
            time.sleep(wait)
    raise RuntimeError("Failed after 3 retries")

def run_part_c():
    reset()
    tickets = pd.read_csv("data/raw/tickets.csv", keep_default_na=False)
    segments = pd.read_csv("outputs/customer_segments.csv")

    zero_prompt = "CLASSIFY. Allowed categories: billing, delivery, technical, fraud. Reply strictly in JSON: {\"category\": \"...\", \"reason\": \"...\"}"
    few_prompt = "CLASSIFY. EXAMPLES: {\"text\": \"Unauthorized transaction\", \"category\": \"fraud\"} Allowed categories: billing, delivery, technical, fraud. Reply strictly in JSON."

    results = []
    total_tokens = 0

    for idx, row in tickets.iterrows():
        tid = row['ticket_id']
        cid = row['customer_id']
        text = row['text']

        # 1. Input Guardrails
        if not text or not text.strip():
            results.append({'ticket_id': tid, 'customer_id': cid, 'status': 'skipped_empty', 'category': '', 'tokens_used': 0})
            continue

        if est_tokens(text) > 400:
            results.append({'ticket_id': tid, 'customer_id': cid, 'status': 'flagged_long', 'category': '', 'tokens_used': 0})
            continue

        # 2. Redaction
        redacted, _, _, _ = redact_text(text)

        # 4 & 5. Model call & Validation
        try:
            resp = resilient_call([{"role": "user", "content": redacted}], few_prompt)
            total_tokens += resp.usage.total_tokens
            content = resp.choices[0].message.content

            # Try parsing JSON
            cat = None
            try:
                parsed = json.loads(content)
                if parsed.get('category') in ['billing', 'delivery', 'technical', 'fraud']:
                    status = 'classified_json'
                    cat = parsed['category']
                else:
                    status = 'flagged_invalid_output'
            except json.JSONDecodeError:
                words = re.findall(r"[a-z]+", content.lower())
                allowed = ['billing', 'delivery', 'technical', 'fraud']
                matches = [w for w in allowed if w in words]
                if len(matches) == 1:
                    status = 'classified_keyword'
                    cat = matches[0]
                else:
                    status = 'flagged_invalid_output'
        except Exception:
            status = 'flagged_invalid_output'
            cat = None

        results.append({'ticket_id': tid, 'customer_id': cid, 'status': status, 'category': cat or '', 'tokens_used': total_tokens})

    res_df = pd.DataFrame(results)
    res_df = res_df.merge(segments[['customer_id', 'segment_name', 'is_premium']], on='customer_id', how='left')

    # Routing logic
    def route_ticket(r):
        if r['status'] in ['skipped_empty', 'flagged_long', 'flagged_invalid_output']:
            return 'human_review', 'NORMAL'
        if r['category'] == 'fraud':
            return 'security_team', 'HIGH'
        if r['is_premium'] == True:
            return 'premium_desk', 'HIGH'
        return 'support_queue', 'NORMAL'

    res_df[['route', 'priority']] = res_df.apply(lambda r: pd.Series(route_ticket(r)), axis=1)
    res_df.to_csv("outputs/triage_results.csv", index=False)

    # Demo budget file
    res_df.head(50).to_csv("outputs/triage_budget_demo.csv", index=False)
    print("Part C completed successfully.")

if __name__ == "__main__":
    run_part_c()
