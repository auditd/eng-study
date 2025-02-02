let mediaRecorder;
let audioChunks = [];
let websocket;

// WebSocket 연결
function connectWebSocket() {
  websocket = new WebSocket(`ws://${window.location.host}/ws`);

  websocket.onopen = function (event) {
    console.log("WebSocket connected!");
  };

  websocket.onmessage = function (event) {
    const data = JSON.parse(event.data);
    console.log("Message from server:", data);
    if (data.speaker && data.text) {
      updateConversation(data.speaker, data.text);
    }
  };

  websocket.onerror = function (event) {
    console.error("WebSocket error:", event);
  };

  websocket.onclose = function (event) {
    console.log("WebSocket closed.");
  };
}

// 페이지 로드 시 WebSocket 연결
window.addEventListener("load", connectWebSocket);

// 녹음 시작
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
      audioChunks.push(event.data);
    };

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
      const audioUrl = URL.createObjectURL(audioBlob);
      document.getElementById("audioPlayer").src = audioUrl;

      // 서버로 오디오 데이터 전송 준비 (sendAudioToGeminiAndPronunciationAssessment 함수에서 처리)
    };

    mediaRecorder.start();
    document.getElementById("recordBtn").textContent = "Stop Recording";
    toggleButtonStates(true, false, true, true); // 녹음 중 상태로 버튼 활성화/비활성화
  } catch (err) {
    console.error("Error accessing microphone:", err);
  }
}

// 녹음 중지
function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    document.getElementById("recordBtn").textContent = "Record";
    toggleButtonStates(false, true, false, false); //  버튼 상태 복구
  }
}

// 녹음/중지 버튼 클릭 이벤트
document.getElementById("recordBtn").addEventListener("click", () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    stopRecording();
  } else {
    startRecording();
  }
});

// 취소 버튼 클릭 이벤트
document.getElementById("cancelBtn").addEventListener("click", () => {
  audioChunks = [];
  document.getElementById("audioPlayer").src = "";
  toggleButtonStates(false, false, false, false); // 버튼 상태 복구
});

// 재생 버튼 클릭 이벤트
document.getElementById("playBtn").addEventListener("click", () => {
  document.getElementById("audioPlayer").play();
});

// 전송 버튼 클릭 이벤트
document.getElementById("sendBtn").addEventListener("click", () => {
    if (audioChunks.length > 0) {
      const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
  
      // Blob을 ArrayBuffer로 변환
      const reader = new FileReader();
      reader.readAsArrayBuffer(audioBlob);
      reader.onloadend = () => {
        const arrayBuffer = reader.result;
        const byteArray = new Uint8Array(arrayBuffer);
  
        // CSRF 토큰을 헤더에 추가
        const headers = new Headers();
        headers.append("X-CSRFToken", csrftoken);
  
        // WebSocket을 통해 서버로 오디오 데이터와 헤더 전송
        websocket.send(byteArray);
  
        // 임시 메시지 출력
        updateConversation("user", "[Audio Sent]", null);
  
        toggleButtonStates(true, true, true, true); // 전송 중 상태로 버튼 비활성화
      };
    }
  });

// 대화 내용을 화면에 출력
function updateConversation(speaker, text) {
  const conversationDiv = document.getElementById("conversation");
  const messageDiv = document.createElement("div");
  messageDiv.classList.add(
    speaker === "user" ? "user-message" : "gemini-message"
  );

  // 사용자 발화 또는 Gemini 응답 텍스트
  const textSpan = document.createElement("span");
  textSpan.textContent = `${speaker === "user" ? "You" : "Gemini"}: ${text}`;
  messageDiv.appendChild(textSpan);

  conversationDiv.appendChild(messageDiv);

  // 스크롤을 아래로 이동
  conversationDiv.scrollTop = conversationDiv.scrollHeight;

  // Gemini 응답 후 버튼 상태 업데이트
  if (speaker === "assistant") {
    toggleButtonStates(false, false, false, false); // 버튼 상태 복구
  }
}

// 버튼 상태 관리 함수: 녹음 중에는 전송, 재생, 취소 버튼 비활성화
function toggleButtonStates(recordDisabled, cancelDisabled, playDisabled, sendDisabled) {
    document.getElementById("recordBtn").disabled = recordDisabled;
    document.getElementById("cancelBtn").disabled = cancelDisabled;
    document.getElementById("playBtn").disabled = playDisabled;
    document.getElementById("sendBtn").disabled = sendDisabled;
}

// 적용 버튼 클릭 이벤트: 지시사항을 서버로 전송
document.getElementById("applyBtn").addEventListener("click", () => {
    const instructionType = document.getElementById("instructionType").value;
    const instructionText = document.getElementById("instructionInput").value.trim();
  
    if (instructionText) {
      // WebSocket을 통해 서버로 지시사항 전송
      const headers = new Headers();
      headers.append("X-CSRFToken", csrftoken);
      websocket.send(JSON.stringify({ type: instructionType, text: instructionText, headers: headers }));
  
      // 지시사항 입력 필드 초기화
      document.getElementById("instructionInput").value = "";
  
      // 적용된 지시사항 업데이트
      document.getElementById("applied-instruction").textContent = instructionText;
    }
  });