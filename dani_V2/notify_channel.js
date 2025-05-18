(function () {
  try {
    const original = window.notifyDebug;
    if (typeof original === "function") {
      window.notifyDebug = function (data) {
        console.log("📥 감지된 알림:", data);

        // Qt WebChannel을 통해 Python으로 메시지 전달
        if (window.channelObject && window.channelObject.receiveNotification) {
          window.channelObject.receiveNotification(JSON.stringify(data));
        }

        return original.apply(this, arguments);
      };
      console.log("✅ notifyDebug 후킹 성공!");
    } else {
      console.log("❌ notifyDebug 함수 없음");
    }
  } catch (e) {
    console.error("⛔ 후킹 중 오류:", e);
  }
})();