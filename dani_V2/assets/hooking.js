(function () {
  if (window.__dani_injected) return;
  window.__dani_injected = true;

  console.log("🟡 Dani hooking.js 시작됨");

  // 후킹 함수 정의
  function hookNotifyDebug() {
    const target = window;
    const original = target.notifyDebug;

    if (typeof original === "function") {
      target.notifyDebug = function (data) {
        console.log("📥 감지된 알림:", data);

        let sender = null, subject = null, notifytype = null, receivedate = null;
        if (typeof data === "string" && data.includes("sender=[")) {
          const senderMatch = data.match(/sender=\[(.*?)\]/);
          const subjectMatch = data.match(/subject=\[(.*?)\]/);
          const notifytypeMatch = data.match(/notifytype=\[(.*?)\]/);
          const receivedateMatch = data.match(/receivedate=\[(.*?)\]/);
          if (senderMatch) sender = senderMatch[1];
          if (subjectMatch) subject = subjectMatch[1];
          if (notifytypeMatch) notifytype = notifytypeMatch[1];
          if (receivedateMatch) receivedate = receivedateMatch[1];
        }

        const payload = {
          sender,
          subject,
          notifytype: notifytype || "00",
          receivedate: receivedate || new Date().toLocaleString(),
        };

        // WebChannel이 연결되었을 경우
        if (
          window.channelObject &&
          typeof window.channelObject.receiveNotification === "function"
        ) {
          console.log("📤 Qt 채널로 전송:", payload);
          window.channelObject.receiveNotification(JSON.stringify(payload));
        } else {
          // 아직 연결 안 된 경우 → 보관
          console.warn("⚠️ Qt 채널 없음 → payload 대기", payload);
          window.__dani_pending = payload;
        }

        return original.apply(this, arguments);
      };

      console.log("✅ notifyDebug 후킹 성공!");
    } else {
      console.warn("⚠️ notifyDebug 함수가 아직 정의되지 않음");
    }
  }

  // QWebChannel 연결 시도 (최대 30회 시도)
  function waitForQt(retries = 0) {
    if (typeof QWebChannel !== "undefined" && typeof qt !== "undefined") {
      console.log("✅ QWebChannel 및 qt 객체 감지됨");

      new QWebChannel(qt.webChannelTransport, function (channel) {
        window.channelObject = channel.objects.channelObject;
        console.log("✅ WebChannel 연결 완료");

        // 연결 성공 후 대기 중이던 메시지 전송
        if (window.__dani_pending) {
          channel.objects.channelObject.receiveNotification(JSON.stringify(window.__dani_pending));
          console.log("📤 대기 중이던 payload 전송 완료");
          delete window.__dani_pending;
        }
      });
    } else {
      if (retries < 30) {
        console.warn(`⏳ Qt 객체 대기 중... (${retries})`);
        setTimeout(() => waitForQt(retries + 1), 300);
      } else {
        console.error("⛔ Qt 객체 연결 실패 (재시도 초과)");
      }
    }
  }

  // 실행 시작
  hookNotifyDebug();
  waitForQt();
})();
