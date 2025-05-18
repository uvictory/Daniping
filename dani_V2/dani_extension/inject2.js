(function () {
  try {
      // 현재 inject.js 는 이미 타겟 프레임 내에서 실행되므로, 굳이 frame 탐색 없이 window 직접 접근
    const target = window;  // inject.js는 주입된 프레임에서 실행되므로, 해당 프레임의 window 자체
      // 기존 notifyDebug 함수를 보존 (원본 함수)
    const original = target.notifyDebug;

        // notifyDebug가 함수로 정의되어 있는 경우에만 후킹 시도
    if (typeof original === 'function') {
        // NotifyDebug를 재정의: 감지된 알림을 콘솔에 출력하고, 서버로 전송한 후 원래 함수 호출
      target.notifyDebug = function (data) {
          // 감지된 알림 출력
        console.log("📥 감지된 알림:", data);

        let sender = "알 수 없음";
        let subject = "제목 없음";
        let notifytype = "00";
        let receivedate = new Date().toLocaleDateString();

        // 정규식 기반 파싱
        if (typeof data == "string"){
          const senderMatch = data.match(/sender=\[(.*?)\]/);
          const subjectMatch = data.match(/sender=\[(.*?)\]/);
          const notifytypeMatch = data.match(/sender=\[(.*?)\]/);
          const receivedateMatch = data.match(/sender=\[(.*?)\]/);

          if (senderMatch) sender = senderMatch[1];
          if (subjectMatch) subject = subjectMatch[1];
          if (notifytypeMatch) notifytype = notifytypeMatch[1];
          if (receivedateMatch) receivedate = receivedateMatch[1];
        }

        const payload = {
          sender,
          subject,
          notifytype,
          receivedate,
        };

        // 💡 WebChannel을 통해 Python 쪽으로 전달
      if (window.channelObject && typeof window.channelObject.receiveNotification === "function") {
        window.channelObject.receiveNotification(JSON.stringify(payload));
        console.log("📤 Qt 채널로 전송됨:", payload);
      } else {
        console.warn("❌ channelObject 또는 receiveNotification 정의 안됨");
      }

      // 원래 동작 유지
      return original.apply(this, arguments);

      };



      console.log("✅ webNotifyProcess 후킹 성공!");
    } else {
      console.log("⚠️ webNotifyProcess 없음 (정의되지 않음)");
    }
  } catch (err) {
    console.error("⛔ 후킹 중 오류 발생:", err);
  }
})();
