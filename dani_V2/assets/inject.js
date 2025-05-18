// ✅ 중복 삽입 방지
if (window.__dani_injected) {
  console.log("⚠️ 이미 inject 완료 → 중복 방지");
} else {
  window.__dani_injected = true;

  // ✅ WebSocket 연결 (필요 없으면 제거 가능)
  const ws = new WebSocket("ws://127.0.0.1:9999");
  ws.onopen = () => console.log("✅ WebSocket 연결됨");
  ws.onerror = (err) => console.error("❌ WebSocket 오류:", err);

  // ✅ notifyDebug 후킹
  (function () {
    try {
      const target = window;
      const original = target.notifyDebug;

      if (typeof original === 'function') {
        target.notifyDebug = function (data) {
          console.log("📥 감지된 알림:", data);

          let sender = null;
          let subject = null;
          let notifytype = null;
          let receivedate = null;

          // 문자열 파싱 (정규식)
          if (typeof data === "string") {
            const senderMatch = data.match(/sender=\[(.*?)\]/);
            const subjectMatch = data.match(/subject=\[(.*?)\]/);
            const notifytypeMatch = data.match(/notifytype=\[(.*?)\]/);
            const receivedateMatch = data.match(/receivedate=\[(.*?)\]/);

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

            // ✅ PyQt WebChannel로 전송
            if (window.channelObject && typeof window.channelObject.receiveNotification === "function") {
              window.channelObject.receiveNotification(JSON.stringify(payload));
              console.log("📡 Qt 채널로 전송됨:", payload);
            } else {
              console.warn("❌ WebChannel 연결 안됨: channelObject 누락");
            }

            // ✅ 필요 시 WebSocket 병렬 전송
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify(payload));
              console.log("📤 WebSocket으로도 전송됨:", payload);
            }
          }

          return original.apply(this, arguments);
        };

        console.log("✅ notifyDebug 후킹 성공!");
      } else {
        console.warn("⚠️ notifyDebug 함수가 정의되지 않음");
      }
    } catch (err) {
      console.error("⛔ 후킹 중 오류 발생:", err);
    }
  })();
}
