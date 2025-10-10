from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

try:
    models = client.models.list()
    print("Success! Models found:")
    for m in models.data[:5]:
        print("-", m.id)
except Exception as e:
    print("Error:", e)
