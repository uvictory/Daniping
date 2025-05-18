
// WebSocket 연결 관리
let socket = null;
let socketConnected = false;

function connectWebSocket() {
  if (socketConnected) return

  socket = new WebSocket("ws://localhost:9999");

  socket.onopen = () => {
    socketConnected = true;
    console.log("✅ WebSocket 연결 완료");
  };

  socket.onclose = () => {
    socketConnected = false;
    console.warn("⚠️ WebSocket 연결 종료됨 → 재연결 대기 중...");
    setTimeout(connectWebSocket, 1000); // 재연결

  };

  socket.onerror = (err) => {
    console.error(" WebSocket 에러:", err);
  };
}
  function sendViaWebSocket(payload){
    if (socket && socketConnected) {
      socket.send(JSON.stringify(payload));
      console.log("📤 WebSocket 전송됨:", payload);
  } else {
    console.warn("❌ WebSocket 아직 연결 안됨 → 전송 보류", payload);
  }
}

// 초기 연결 시도
  connectWebSocket();


// 후킹 방지 플래그
if (window.__dani_injected) {
  console.log("⚠️ 이미 inject 완료 → 중복 방지");
} else {
  window.__dani_injected = true;

  function injectScriptFileToFrame(frame) {
    try {
      const js_code = `
        (function () {
          try {
            const target = window;
            const original = target.notifyDebug;
            
              function sendViaWebSocket(payload){
                try{ 
                  const socket = new WebSocket("ws://localhost:9999");
                  socket.onopen = () => {
                    socket.send(JSON.stringify(payload));
                    console.log("📤 WebSocket 전송됨:", payload);
                    socket.close(); // 단발성 연결 후 종료
                    };
                    socket.onerror = (e) => console.error(" Websocket 오류:",e);
                    } catch (e) {
                      console.error(" Websocket 예외:",e);
                      }
                     }
            
            
            if (typeof original === 'function') {
              target.notifyDebug = function (data) {
                console.log("📥 감지된 알림:", data);

                let sender = null, subject = null, notifytype = null, receivedate = null;
                if (typeof data === "string" && data.includes("sender=[")) {
                  const senderMatch = data.match(/sender=\\[(.*?)\\]/);
                  const subjectMatch = data.match(/subject=\\[(.*?)\\]/);
                  const notifytypeMatch = data.match(/notifytype=\\[(.*?)\\]/);
                  const receivedateMatch = data.match(/receivedate=\\[(.*?)\\]/);
                  if (senderMatch) sender = senderMatch[1];
                  if (subjectMatch) subject = subjectMatch[1];
                  if (notifytypeMatch) notifytype = notifytypeMatch[1];
                  if (receivedateMatch) receivedate = receivedateMatch[1];
                }

                if (sender && subject) {
                  const payload = {
                    sender: sender,
                    subject: subject,
                    notifytype: notifytype || "00",
                    receivedate: receivedate || new Date().toLocaleString()
                  };
                  console.log("📤 다니에게 전송할 데이터:", payload);
                  sendViaWebSocket(payload); // 다니에게 전송
                  
                }

                return original.apply(this, arguments);
              };
              console.log("✅ notifyDebug 후킹 성공!");
            } else {
              console.log("⚠️ notifyDebug 없음 (정의되지 않음)");
            }
          } catch (err) {
            console.error("⛔ 후킹 중 오류 발생:", err);
          }
        })();
      `;

      const script = frame.document.createElement('script');
      script.textContent = js_code;
      frame.document.documentElement.appendChild(script);
      console.log("✅ inject.js 삽입 성공");

    } catch (e) {
      console.warn("❌ inject 실패:", e);
    }
  }

  function waitAndInject() {
    let retries = 0;
    const maxRetries = 30;

    const interval = setInterval(() => {
      try {
        for (let i = 0; i < window.frames.length; i++) {
          const frame = window.frames[i];
          if (frame.document && frame.document.readyState == "complete"){
            injectScriptFileToFrame(frame)
            clearInterval(interval);
            return;
          }
        }
      } catch (e) {
        console.warn("❌ 프레임 접근 실패:", e);
      }

      if ( ++retries >= maxRetries) {
        clearInterval(interval);
        console.warn("🐠 프레임 접근 제한: inject 중단");
      }
    }, 1000);
  }

  waitAndInject();
}
