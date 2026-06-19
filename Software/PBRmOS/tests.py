import os

import modules.lib as lib
import modules.ai_driver as ai

ASSISTANT_MODEL = "Gemma2-2B-Q8.gguf"
ASSISTANT_PATH = os.path.join(lib.AI_DIR, "LLM", "model", ASSISTANT_MODEL)

assistant = ai.AIAssistant(ASSISTANT_PATH)

for i in range(3):
    print(assistant.ask(input()))