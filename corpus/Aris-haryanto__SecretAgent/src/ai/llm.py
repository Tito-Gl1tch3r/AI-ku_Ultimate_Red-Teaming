import time
from ollama import chat, ChatResponse


class AI:
    def __init__(self, env):
        self.env = env

    def helpAI(self, url):
        start_time = time.time()
        # response: ChatResponse = chat(model="deepseek-r1:7b", messages=[
        response: ChatResponse = chat(model="granite3.2:8b", messages=[
            {
                "role": "system",
                "content": f"only answer with 'this is malicious url' or 'this is safe url' and short reason. is this url malicious ? {url}"
            }
        ])

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Time to AI Analyze : {elapsed_time:.2f} seconds")
        return response['message']['content']
        