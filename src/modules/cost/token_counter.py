import tiktoken

def token_counter(message, model="gpt-4o-mini"):
    enc = tiktoken.encoding_for_model(model)
    total = 0

    for m in message:
        total += len(enc.encode(m["content"]))

    return total