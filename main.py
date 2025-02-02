from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import List
import uvicorn
import json
import os
import io
import wave
from itsdangerous import URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware

from utils.gemini_utils import generate_gemini_response, synthesize_and_play_text
from utils.audio_utils import play_audio_from_bytes

# CSRF 보안을 위한 시크릿 키 설정
SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key_here")

# ItsDangerous 시리얼라이저 생성
s = URLSafeTimedSerializer(SECRET_KEY)

# CSRF 미들웨어 클래스
class CSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            response = await call_next(request)
            if "csrftoken" not in request.cookies:
                token = s.dumps(os.urandom(16).hex())
                response.set_cookie("csrftoken", token)
            return response
        else:
            received_token = request.headers.get("X-CSRFToken") or request.cookies.get("csrftoken")
            if not received_token:
                return HTMLResponse("CSRF token missing", status_code=403)
            try:
                s.loads(received_token, max_age=3600) # 토큰 유효 시간 1시간
            except:
                return HTMLResponse("Invalid CSRF token", status_code=403)
            return await call_next(request)

# 미들웨어 리스트 생성
middleware = [
    Middleware(CSRFMiddleware)
]

app = FastAPI(middleware=middleware)

# 정적 파일 (HTML, CSS, JavaScript) 제공
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 템플릿 설정
templates = Jinja2Templates(directory="utils/templates") # index.html 파일을 utils/templates에 넣고 수정해야함.

# 대화 기록 및 지시사항
conversation_history = []
instructions = {"guideline": None, "topic": None, "repeat": 1}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """메인 페이지"""
    # CSRF 토큰 생성
    token = s.dumps(os.urandom(16).hex())

    # 템플릿 컨텍스트에 토큰 추가
    context = {"request": request, "csrf_token": token}

    return templates.TemplateResponse("index.html", context)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 엔드포인트"""
    await websocket.accept()

    # CSRF 토큰 검증
    received_token = websocket.headers.get("X-CSRFToken") or websocket.cookies.get("csrftoken")
    if not received_token:
        await websocket.close(code=1008, reason="CSRF token missing")
        return
    try:
        s.loads(received_token, max_age=3600)
    except:
        await websocket.close(code=1008, reason="Invalid CSRF token")
        return
    
    # 초기 안내 메시지
    welcome_message = "Welcome to the English conversation practice! Press 'Record' to start speaking."
    conversation_history.append({"role": "assistant", "content": welcome_message})
    synthesize_and_play_text(welcome_message, instructions["repeat"]) # 지시사항에 따라 반복 재생
    await websocket.send_text(json.dumps({"speaker": "assistant", "text": welcome_message}))

    try:
        while True:
            # 클라이언트로부터 메시지 수신 (음성 데이터 또는 지시사항)
            data = await websocket.receive_text()

            # 지시사항 처리
            try:
                data_json = json.loads(data)
                if isinstance(data_json, dict) and data_json.get("type") in instructions:
                    instructions[data_json["type"]] = data_json["text"]
                    print(f"Instruction '{data_json['type']}' updated: {data_json['text']}")
                    continue  # 지시사항을 받은 경우, 음성 처리를 건너뜁니다.
            except json.JSONDecodeError:
                pass # JSON 디코딩에 실패한 경우, 무시하고 계속 진행합니다.

            # 오디오 데이터 임시 저장
            audio_file = "temp_audio.wav"
            with wave.open(audio_file, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(44100)
                wf.writeframes(data)

            # Gemini API에 음성 파일 전송 및 응답 생성 (가정: Gemini 2.0 Flash가 음성 입력 지원)
            gemini_response_text = generate_gemini_response(audio_file, instructions)

            # 사용자에게 음성 데이터 전달
            await websocket.send_text(json.dumps({"speaker": "user", "text": "[Audio Sent]"}))

            # Gemini 응답을 클라이언트로 전송
            conversation_history.append({"role": "assistant", "content": gemini_response_text})
            await websocket.send_text(json.dumps({"speaker": "assistant", "text": gemini_response_text}))

            # Gemini 응답을 음성으로 변환 및 재생
            synthesize_and_play_text(gemini_response_text, instructions["repeat"])

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.send_text(json.dumps({"speaker": "error", "text": "An error occurred."}))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
