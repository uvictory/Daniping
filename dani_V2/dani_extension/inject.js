(function () {
  try {
      // 현재 inject.js 는 이미 타겟 프레임 내에서 실행되므로, 굳이 frame 탐색 없이 window 직접 접근
    const target = window;  // inject.js는 주입된 프레임에서 실행되므로, 해당 프레임의 window 자체
      // 기존 notifyDebug 함수를 보존 (원본 함수)
    const original = target.notifyDebug;


    //websocket 전역 변수로 선언해서 재연결 방지
    let ws;
    let cachedIP = null; // IP 캐싱용


    // WebSocket 연결 함수 (Dani에게)
    function connectToLocalDani() {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        ws = new WebSocket("ws://127.0.0.1:9999");  // ✅ 로컬 Dani 포트

        ws.onopen = () => console.log("✅ Dani에 WebSocket 연결됨");
        ws.onerror = (err) => console.warn("❌ WebSocket 오류:", err);
        ws.onclose = () => console.log("🔌 WebSocket 닫힘");
      }
    }

    // notifyDebug가 함수로 정의되어 있는 경우에만 후킹 시도
    if (typeof original === 'function') {
        // NotifyDebug를 재정의: 감지된 알림을 콘솔에 출력하고, 서버로 전송한 후 원래 함수 호출
      target.notifyDebug = async function (data) {
        // 감지된 알림 출력
        console.log("📥 감지된 알림:", data);

        // sender와 subject 추출 시도
        let sender = null;
        let subject = null;
        let notifytype = null;
        let receivedate = null;

        // JSON 형태가 아닌 문자열 로그 형식으로 들어오는 경우 처리
        if (typeof data === "string" && data.includes("sender=[") && data.includes("subject=[")) {
          const senderMatch = data.match(/sender=\[(.*?)\]/);
          const subjectMatch = data.match(/subject=\[(.*?)\]/);
          const notifytypeMatch = data.match(/notifytype=\[(.*?)\]/);
          const receivedateMatch = data.match(/receivedate=\[(.*?)\]/);

          if (senderMatch) sender = senderMatch[1];
          if (subjectMatch) subject = subjectMatch[1];
          if (notifytypeMatch) notifytype = notifytypeMatch[1];
          if (receivedateMatch) receivedate = receivedateMatch[1];
        }

        // sender와 subject 둘 다 존재하면 WebSocket으로 전송
        if (sender && subject) {
          //const ip = await getLocalIP();  // 내부 IP 받아오기
          //console.log("ip = ",ip)
          //if (!ip) return;

          const payload = {

            sender: sender,
            subject: subject,
            notifytype: notifytype || "00", // 없는 경우 기본값
            receivedate: receivedate || new Date().toLocaleString() // 없는 경우 대비
          };

          console.log("📤 다니에게 전송할 데이터:", payload);


          // 연결이 안 돼 있으면 재연결
          if (!ws || ws.readyState !== WebSocket.OPEN) {
            connectToLocalDani();

            ws.onopen = () => {
              ws.send(JSON.stringify(payload));
              console.log("📤 WebSocket 전송 성공 (초기 연결)");
            };
          } else {
            ws.send(JSON.stringify(payload));
            console.log("📤 WebSocket 전송 성공");
          }
        }

        // 원래 notifyDebug 동작 유지
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
