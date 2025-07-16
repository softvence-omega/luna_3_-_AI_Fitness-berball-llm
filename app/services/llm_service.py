import httpx
from fastapi import HTTPException
from app.config.settings import OPENAI_API_KEY, OPENAI_API_URL
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")

    async def generate_response(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        print(OPENAI_API_KEY)

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.2,
            "stop": ["---"]
             }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(OPENAI_API_URL, headers=headers, json=data, timeout=15)
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise HTTPException(status_code=500, detail=f"OpenAI API request failed: {e}")

            try:
                result_json = response.json()
                if not result_json.get("choices") or not result_json["choices"][0].get("message"):
                    raise HTTPException(status_code=500, detail="Invalid response structure from OpenAI API")
                return result_json["choices"][0]["message"]["content"].strip()
            except (KeyError, IndexError) as e:
                raise HTTPException(status_code=500, detail=f"Failed to parse OpenAI API response: {e}")

    def build_response_prompt(self, user_feedback: str, chat_history=None) -> str:
        if chat_history is None:
            chat_history = []
        history_str = ""
        for msg in chat_history:
            history_str += f"{msg['role']}: {msg['content']}\n"
        return f"""
You are an AI assistant providing helpful and accurate responses. Based on the user's feedback and the chat history, generate a clear and relevant response. If the feedback is about a technical topic like FastAPI, include specific code examples where applicable.

### Chat History:
{history_str}

### User Feedback:
\"\"\"{user_feedback}\"\"\"
### Instructions:
- Provide a concise, accurate, and relevant response.
- If the feedback involves a technical query (e.g., FastAPI), include a code example like a route or async function.
- Keep the response under 300 tokens.
"""

    def build_improved_response_prompt(self, user_feedback: str, original_response: str, rating: str, comment: str) -> str:
        return f"""
You are an AI assistant tasked with improving a previous response based on user feedback, rating, and a specific comment. The original response was rated '{rating}', indicating it was not helpful. Use the user's comment to address specific issues and generate an improved response that is clear, relevant, and includes specific details or code examples (e.g., FastAPI routes) if applicable.

### User Feedback:
\"\"\"{user_feedback}\"\"\"
### Original Response:
\"\"\"{original_response}\"\"\"
### User Comment:
\"\"\"{comment}\"\"\"
### Instructions:
- Address the issues raised in the comment.
- If the comment suggests missing examples, include relevant code snippets (e.g., FastAPI routes or async functions).
- Keep the response concise and focused.
"""

    def build_analysis_prompt(self, user_feedback: str, original_response: str, rating: str, comment: str) -> str:
        return f"""
You are an AI Quality Control Assistant. Analyze the user's feedback, the AI-generated response, the rating, and the comment with the following objectives:

### Instructions:
1. Summarize the user's sentiment in one concise sentence.
2. Evaluate the quality of the AI response, noting strengths and weaknesses.
3. Suggest specific, actionable improvements, including relevant FastAPI code examples if applicable (e.g., routes, async endpoints).
4. Conclude with a one-word sentiment tag: Positive, Negative, or Neutral.
5. Keep the response concise and focused.

### Example Output:
- User Sentiment Summary: The user found the response unhelpful due to missing examples.
- Response Evaluation: The response explained FastAPI but lacked practical examples.
- Suggested Improvements: Include a FastAPI route, e.g., `@app.get('/') async def read_root(): return {{'message': 'Hello, World!'}}`.
- Sentiment Tag: Negative

---

🧠 User Feedback:
\"\"\"{user_feedback}\"\"\"
🧠 AI Response:
\"\"\"{original_response}\"\"\"
✅ User Rating: **{rating}**
🗣 Comment: **\"{comment}\"\"\"
"""

# Create a singleton instance
llm_service = LLMService() 