import ollama


def get_models():

    response = ollama.list()

    models = []

    for model in response["models"]:
        models.append(model["model"])

    return models


def ask_model(model_name, messages):

    response = ollama.chat(
        model=model_name,
        messages=messages
    )

    return response.message.content
