/**
 * Sheet to Sheet Migration - Google Apps Script
 *
 * Entry point for GAS Web App
 */

// GET 요청 처리
function doGet(e: GoogleAppsScript.Events.DoGet): GoogleAppsScript.Content.TextOutput {
  const action = e.parameter.action || 'status';

  let result: ApiResponse<unknown>;

  try {
    switch (action) {
      case 'status':
        result = { success: true, data: { status: 'ok', version: '1.0.0' }, timestamp: new Date().toISOString() };
        break;
      case 'sheets':
        result = getSheetsList(e.parameter.spreadsheetId);
        break;
      case 'preview':
        result = getSheetPreview(e.parameter.spreadsheetId, e.parameter.sheetName, e.parameter.range);
        break;
      case 'triggers':
        result = getTriggersList();
        break;
      case 'logs':
        result = getExecutionLogs(parseInt(e.parameter.limit || '50'), parseInt(e.parameter.offset || '0'));
        break;
      default:
        result = { success: false, error: { code: 'UNKNOWN_ACTION', message: `Unknown action: ${action}` }, timestamp: new Date().toISOString() };
    }
  } catch (error) {
    result = { success: false, error: { code: 'ERROR', message: String(error) }, timestamp: new Date().toISOString() };
  }

  return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
}

// POST 요청 처리
function doPost(e: GoogleAppsScript.Events.DoPost): GoogleAppsScript.Content.TextOutput {
  let result: ApiResponse<unknown>;

  try {
    const data = JSON.parse(e.postData.contents);
    const action = data.action;

    switch (action) {
      case 'migrate':
        result = executeMigration(data);
        break;
      case 'createTrigger':
        result = createTrigger(data);
        break;
      case 'deleteTrigger':
        result = deleteTrigger(data.triggerId);
        break;
      case 'testRun':
        result = testMigration(data);
        break;
      default:
        result = { success: false, error: { code: 'UNKNOWN_ACTION', message: `Unknown action: ${action}` }, timestamp: new Date().toISOString() };
    }
  } catch (error) {
    result = { success: false, error: { code: 'ERROR', message: String(error) }, timestamp: new Date().toISOString() };
  }

  return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
}

// Types
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
  timestamp: string;
}

interface SheetInfo {
  name: string;
  index: number;
  rowCount: number;
  columnCount: number;
}

interface MigrationConfig {
  sourceSpreadsheetId: string;
  sourceSheetName: string;
  sourceRange: string;
  targetSpreadsheetId: string;
  targetSheetName: string;
  targetRange: string;
  mappings: ColumnMapping[];
  transforms: TransformRule[];
}

interface ColumnMapping {
  sourceColumn: string;
  targetColumn: string;
}

interface TransformRule {
  column: string;
  type: 'upper' | 'lower' | 'trim' | 'date' | 'number' | 'regex';
  options?: Record<string, unknown>;
}

// Sheet Service Functions
function getSheetsList(spreadsheetId: string): ApiResponse<SheetInfo[]> {
  const ss = SpreadsheetApp.openById(spreadsheetId);
  const sheets = ss.getSheets().map((sheet, index) => ({
    name: sheet.getName(),
    index,
    rowCount: sheet.getLastRow(),
    columnCount: sheet.getLastColumn()
  }));

  return { success: true, data: sheets, timestamp: new Date().toISOString() };
}

function getSheetPreview(spreadsheetId: string, sheetName: string, range?: string): ApiResponse<unknown[][]> {
  const ss = SpreadsheetApp.openById(spreadsheetId);
  const sheet = ss.getSheetByName(sheetName);

  if (!sheet) {
    return { success: false, error: { code: 'SHEET_NOT_FOUND', message: `Sheet not found: ${sheetName}` }, timestamp: new Date().toISOString() };
  }

  const dataRange = range ? sheet.getRange(range) : sheet.getDataRange();
  const values = dataRange.getValues();

  // 최대 11행만 반환 (헤더 + 10행)
  const preview = values.slice(0, 11);

  return { success: true, data: preview, timestamp: new Date().toISOString() };
}

// Trigger Service Functions
function getTriggersList(): ApiResponse<unknown[]> {
  const triggers = ScriptApp.getProjectTriggers().map(trigger => ({
    id: trigger.getUniqueId(),
    functionName: trigger.getHandlerFunction(),
    type: trigger.getEventType().toString(),
    source: trigger.getTriggerSource().toString()
  }));

  return { success: true, data: triggers, timestamp: new Date().toISOString() };
}

function createTrigger(data: { schedule: string; functionName: string }): ApiResponse<{ triggerId: string }> {
  // 간단한 일일 트리거 예시
  const trigger = ScriptApp.newTrigger(data.functionName)
    .timeBased()
    .everyDays(1)
    .atHour(6)
    .create();

  return { success: true, data: { triggerId: trigger.getUniqueId() }, timestamp: new Date().toISOString() };
}

function deleteTrigger(triggerId: string): ApiResponse<{ deleted: boolean }> {
  const triggers = ScriptApp.getProjectTriggers();
  const target = triggers.find(t => t.getUniqueId() === triggerId);

  if (target) {
    ScriptApp.deleteTrigger(target);
    return { success: true, data: { deleted: true }, timestamp: new Date().toISOString() };
  }

  return { success: false, error: { code: 'TRIGGER_NOT_FOUND', message: `Trigger not found: ${triggerId}` }, timestamp: new Date().toISOString() };
}

function getExecutionLogs(limit: number, offset: number): ApiResponse<unknown[]> {
  // 실행 로그는 PropertiesService에 저장 가능
  const props = PropertiesService.getScriptProperties();
  const logsJson = props.getProperty('executionLogs') || '[]';
  const logs = JSON.parse(logsJson) as unknown[];

  const paginated = logs.slice(offset, offset + limit);

  return { success: true, data: paginated, timestamp: new Date().toISOString() };
}

// Migration Functions
function executeMigration(config: MigrationConfig): ApiResponse<{ rowsProcessed: number }> {
  const sourceSheet = SpreadsheetApp.openById(config.sourceSpreadsheetId).getSheetByName(config.sourceSheetName);
  const targetSheet = SpreadsheetApp.openById(config.targetSpreadsheetId).getSheetByName(config.targetSheetName);

  if (!sourceSheet || !targetSheet) {
    return { success: false, error: { code: 'SHEET_NOT_FOUND', message: 'Source or target sheet not found' }, timestamp: new Date().toISOString() };
  }

  const sourceData = sourceSheet.getRange(config.sourceRange).getValues();

  // TODO: Apply mappings and transforms
  const transformedData = sourceData;

  targetSheet.getRange(config.targetRange).setValues(transformedData);

  // Log execution
  logExecution('migrate', sourceData.length, 'success');

  return { success: true, data: { rowsProcessed: sourceData.length }, timestamp: new Date().toISOString() };
}

function testMigration(config: MigrationConfig): ApiResponse<{ preview: unknown[][] }> {
  const sourceSheet = SpreadsheetApp.openById(config.sourceSpreadsheetId).getSheetByName(config.sourceSheetName);

  if (!sourceSheet) {
    return { success: false, error: { code: 'SHEET_NOT_FOUND', message: 'Source sheet not found' }, timestamp: new Date().toISOString() };
  }

  const sourceData = sourceSheet.getRange(config.sourceRange).getValues();

  // TODO: Apply mappings and transforms
  const preview = sourceData.slice(0, 5);

  return { success: true, data: { preview }, timestamp: new Date().toISOString() };
}

function logExecution(action: string, rowCount: number, status: string): void {
  const props = PropertiesService.getScriptProperties();
  const logsJson = props.getProperty('executionLogs') || '[]';
  const logs = JSON.parse(logsJson) as unknown[];

  logs.unshift({
    action,
    rowCount,
    status,
    timestamp: new Date().toISOString()
  });

  // 최대 100개 로그만 유지
  if (logs.length > 100) {
    logs.pop();
  }

  props.setProperty('executionLogs', JSON.stringify(logs));
}
