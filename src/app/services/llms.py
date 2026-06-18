from langchain.chat_models import init_chat_model

base_llm = init_chat_model(
    model = "deepseek/deepseek-v4-flash",
    model_provider = "openrouter",
    temperature = 0.7,
)