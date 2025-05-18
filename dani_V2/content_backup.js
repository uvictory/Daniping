// QWebChannel 초기화
  if (typeof qt !== "undefined") {
    new QWebChannel(qt.webChannelTransport, function (channel) {
      window.channelObject = channel.objects.channelObject;
      console.log("✅ WebChannel 연결 완료");
    });
  } else {
    console.warn("❌ qt 객체 없음 - QWebChannel 연결 실패");
  }

function sendToQt(payload) {
  const maxRetries = 10;
  let retries = 0;

  const trySend = () => {
    if (window.channelObject && typeof window.channelObject.receiveNotification === "function") {
      window.channelObject.receiveNotification(JSON.stringify(payload));
      console.log("📤 Qt 채널로 전송됨:", payload);
    } else {
      retries++;
      if (retries <= maxRetries) {
        console.warn("❌ channelObject 아직 준비 안 됨, 재시도 중...");
        setTimeout(trySend, 500);
      } else {
        console.error("⛔ Qt 채널로 전송 실패: 재시도 초과");
      }
    }
  };

  trySend();
}


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
            
            function sendToQt(payload) {
  const maxRetries = 10;
  let retries = 0;

  const trySend = () => {
    if (window.channelObject && typeof window.channelObject.receiveNotification === "function") {
      window.channelObject.receiveNotification(JSON.stringify(payload));
      console.log("📤 Qt 채널로 전송됨:", payload);
    } else {
      retries++;
      if (retries <= maxRetries) {
        console.warn("❌ channelObject 아직 준비 안 됨, 재시도 중...");
        setTimeout(trySend, 500);
      } else {
        console.error("⛔ Qt 채널로 전송 실패: 재시도 초과");
      }
    }
  };

  trySend();
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
                  sendToQt(payload);  // ← 여기에만 집중
                  
                  const interval = setInterval(() => {
                  if (window.channelObject && typeof window.channelObject.receiveNotification === "function") {
                    console.log("📤 Qt 채널로 전송 준비 중...");
                    window.channelObject.receiveNotification(JSON.stringify(payload));
                    console.log("📤 Qt 채널로 전송됨2:", payload);
                  } else {
                    console.warn("❌ channelObject 또는 receiveNotification 정의 안됨");
                  }
                  },1000);
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
          if (frame.document && frame.document.readyState === "complete") {
            injectScriptFileToFrame(frame);
            clearInterval(interval);
            return;
          }
        }
      } catch (e) {
        console.warn("❌ 프레임 접근 실패:", e);
      }

      if (++retries >= maxRetries) {
        clearInterval(interval);
        console.warn("⛔ 프레임 접근 제한: inject 중단");
      }
    }, 1000);
  }

  waitAndInject();
}
