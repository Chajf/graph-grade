from dotenv import load_dotenv

load_dotenv()

from services.llms import base_llm


def main():
    response = base_llm.invoke("What is the capital of France?")
    print(response)


if __name__ == "__main__":
    main()
