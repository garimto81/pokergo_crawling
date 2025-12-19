/**
 * NAMS Sheets Sync - 작업자 시트 → NAMS 시트 동기화
 * Google Apps Script + CLASP
 */

// ============================================================
// 설정
// ============================================================

const CONFIG = {
  // 소스 시트 (작업자 시트)
  SOURCE_SHEET_ID: "소스_시트_ID를_여기에_입력",
  SOURCE_SHEET_NAME: "Sheet1",
  SOURCE_RANGE: "A:C",  // 파일명, 카테고리, 제목

  // 타겟 시트 (NAMS 시트)
  TARGET_SHEET_ID: "타겟_시트_ID를_여기에_입력",
  TARGET_SHEET_NAME: "Metadata_Import",

  // 로그 시트
  LOG_SHEET_NAME: "Sync_Log",

  // 알림 이메일
  ADMIN_EMAIL: "admin@example.com"
};

// ============================================================
// 메인 동기화 함수
// ============================================================

/**
 * 작업자 시트에서 NAMS 시트로 메타데이터 동기화
 */
function syncMetadata() {
  const startTime = new Date();
  let rowCount = 0;
  let status = "success";
  let errorMessage = "";

  try {
    // 소스 시트 열기
    const sourceSpreadsheet = SpreadsheetApp.openById(CONFIG.SOURCE_SHEET_ID);
    const sourceSheet = sourceSpreadsheet.getSheetByName(CONFIG.SOURCE_SHEET_NAME);

    if (!sourceSheet) {
      throw new Error(`소스 시트를 찾을 수 없음: ${CONFIG.SOURCE_SHEET_NAME}`);
    }

    // 데이터 읽기
    const sourceData = sourceSheet.getRange(CONFIG.SOURCE_RANGE).getValues();

    // 빈 행 제거
    const filteredData = sourceData.filter(row => row[0] !== "");
    rowCount = filteredData.length;

    if (rowCount === 0) {
      throw new Error("동기화할 데이터가 없습니다");
    }

    // 타겟 시트 열기
    const targetSpreadsheet = SpreadsheetApp.openById(CONFIG.TARGET_SHEET_ID);
    let targetSheet = targetSpreadsheet.getSheetByName(CONFIG.TARGET_SHEET_NAME);

    // 타겟 시트가 없으면 생성
    if (!targetSheet) {
      targetSheet = targetSpreadsheet.insertSheet(CONFIG.TARGET_SHEET_NAME);
      // 헤더 추가
      targetSheet.getRange(1, 1, 1, 4).setValues([["파일명", "카테고리", "제목", "동기화일시"]]);
    }

    // 기존 데이터 클리어 (헤더 제외)
    const lastRow = targetSheet.getLastRow();
    if (lastRow > 1) {
      targetSheet.getRange(2, 1, lastRow - 1, 4).clearContent();
    }

    // 동기화 시간 추가
    const syncTime = new Date().toISOString();
    const dataWithTimestamp = filteredData.map(row => [...row.slice(0, 3), syncTime]);

    // 데이터 복사
    if (dataWithTimestamp.length > 0) {
      targetSheet.getRange(2, 1, dataWithTimestamp.length, 4).setValues(dataWithTimestamp);
    }

    Logger.log(`동기화 완료: ${rowCount}행`);

  } catch (error) {
    status = "failed";
    errorMessage = error.message;
    Logger.log(`동기화 실패: ${errorMessage}`);

    // 에러 알림 발송
    sendErrorEmail(errorMessage);
  }

  // 로그 기록
  logSync(startTime, rowCount, status, errorMessage);

  return {
    status: status,
    rowCount: rowCount,
    error: errorMessage
  };
}

// ============================================================
// 로그 기록
// ============================================================

/**
 * 동기화 결과를 로그 시트에 기록
 */
function logSync(startTime, rowCount, status, errorMessage) {
  try {
    const targetSpreadsheet = SpreadsheetApp.openById(CONFIG.TARGET_SHEET_ID);
    let logSheet = targetSpreadsheet.getSheetByName(CONFIG.LOG_SHEET_NAME);

    // 로그 시트가 없으면 생성
    if (!logSheet) {
      logSheet = targetSpreadsheet.insertSheet(CONFIG.LOG_SHEET_NAME);
      logSheet.getRange(1, 1, 1, 5).setValues([
        ["실행시간", "종료시간", "행수", "상태", "에러메시지"]
      ]);
    }

    const endTime = new Date();
    logSheet.appendRow([
      startTime.toISOString(),
      endTime.toISOString(),
      rowCount,
      status,
      errorMessage || ""
    ]);

  } catch (error) {
    Logger.log(`로그 기록 실패: ${error.message}`);
  }
}

// ============================================================
// 에러 알림
// ============================================================

/**
 * 동기화 실패 시 이메일 알림 발송
 */
function sendErrorEmail(errorMessage) {
  try {
    const subject = "[NAMS] Sheets 동기화 실패";
    const body = `
NAMS Sheets 동기화 중 오류가 발생했습니다.

시간: ${new Date().toISOString()}
에러: ${errorMessage}

확인 후 조치해 주세요.
    `;

    MailApp.sendEmail(CONFIG.ADMIN_EMAIL, subject, body);
    Logger.log(`에러 알림 발송: ${CONFIG.ADMIN_EMAIL}`);

  } catch (error) {
    Logger.log(`이메일 발송 실패: ${error.message}`);
  }
}

// ============================================================
// 트리거 관리
// ============================================================

/**
 * 매일 트리거 생성 (오전 6시)
 */
function createDailyTrigger() {
  // 기존 트리거 삭제
  deleteTriggers();

  // 새 트리거 생성
  ScriptApp.newTrigger('syncMetadata')
    .timeBased()
    .everyDays(1)
    .atHour(6)
    .create();

  Logger.log("매일 트리거 생성 완료 (06:00 AM)");
}

/**
 * 모든 트리거 삭제
 */
function deleteTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    ScriptApp.deleteTrigger(trigger);
  });
  Logger.log(`${triggers.length}개 트리거 삭제됨`);
}

/**
 * 현재 트리거 목록 확인
 */
function listTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    Logger.log(`트리거: ${trigger.getHandlerFunction()} - ${trigger.getTriggerSource()}`);
  });
  return triggers.length;
}

// ============================================================
// 유틸리티
// ============================================================

/**
 * 수동 테스트 실행
 */
function testSync() {
  const result = syncMetadata();
  Logger.log(`테스트 결과: ${JSON.stringify(result)}`);
}

/**
 * 설정 확인
 */
function checkConfig() {
  Logger.log(`소스 시트 ID: ${CONFIG.SOURCE_SHEET_ID}`);
  Logger.log(`타겟 시트 ID: ${CONFIG.TARGET_SHEET_ID}`);
  Logger.log(`관리자 이메일: ${CONFIG.ADMIN_EMAIL}`);
}
