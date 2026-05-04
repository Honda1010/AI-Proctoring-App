'use strict';

const { app, BrowserWindow, ipcMain, net, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const keytar = require('keytar');

// ---------------------------------------------------------------------------
// Module-level state (exported for internal use by later task expansions)
// ---------------------------------------------------------------------------
// changes
/** @type {BrowserWindow | null} */
let mainWindow = null;

/** @type {import('child_process').ChildProcess | null} */
let pythonProcess = null;

/** @type {'idle' | 'starting' | 'ready' | 'failed' | 'crashed' | 'stopping'} */
let bridgeState = 'idle';

/** @type {import('child_process').ChildProcess | null} */
let aiRouterProcess = null;

let aiRpcNextId = 1;
const aiRpcPending = new Map();

/**
 * Resolve the absolute path to config.json based on packaging state.
 * @returns {string}
 */
function resolveConfigPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'config.json');
  }
  return path.join(__dirname, '..', 'config.json');
}

/**
 * Spawn the AI Router process (router.py).
 * Captures JSON-RPC notifications from stdout and forwards them to the renderer.
 */
function startAIRouter() {
  const routerScript = path.join(__dirname, '..', 'python_bridge', 'router.py');
  const configPath = resolveConfigPath();
  const projectRoot = path.join(__dirname, '..');

  // Prefer the venv Python so all AI packages are available.
  // Fall back to the system 'python' / 'python3' if venv is absent.
  const venvPython = process.platform === 'win32'
    ? path.join(projectRoot, '.venv', 'Scripts', 'python.exe')
    : path.join(projectRoot, '.venv', 'bin', 'python');
  const pythonExe = fs.existsSync(venvPython) ? venvPython : 'python';

  aiRouterProcess = spawn(pythonExe, [routerScript], {
    env: { ...process.env, LUMINA_CONFIG_PATH: configPath },
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  let buffer = '';
  aiRouterProcess.stdout.on('data', (chunk) => {
    buffer += chunk.toString();
    let lines = buffer.split('\n');
    buffer = lines.pop(); // Keep partial line in buffer

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.jsonrpc !== '2.0') continue;

        if (msg.id != null) {
          const pending = aiRpcPending.get(msg.id);
          if (pending) {
            aiRpcPending.delete(msg.id);
            clearTimeout(pending.timer);
            if (msg.error) {
              pending.resolve({ ok: false, error: msg.error });
            } else {
              pending.resolve({ ok: true, result: msg.result });
            }
          }
          continue;
        }

        // Only forward notifications (detection, alert, riskScore) to renderer
        if (msg.method && !msg.id) {
          mainWindow?.webContents.send('bridge:ai-event', msg);
        }
      } catch (err) {
        process.stderr.write(`[router] JSON parse error: ${err.message}\n`);
      }
    }
  });

  aiRouterProcess.stderr.on('data', (chunk) => {
    process.stderr.write(`[router-err] ${chunk}`);
  });

  aiRouterProcess.on('close', (code) => {
    process.stderr.write(`[router] exited with code ${code}\n`);
  });
}

/**
 * Send a JSON-RPC request to the AI router stdin and await the response.
 * @param {string} method
 * @param {object} params
 * @param {number} timeoutMs
 * @returns {Promise<{ok: true, result: object} | {ok: false, error: object}>}
 */
function sendAiRpc(method, params = {}, timeoutMs = 10000) {
  if (!aiRouterProcess || !aiRouterProcess.stdin || aiRouterProcess.killed) {
    return Promise.resolve({
      ok: false,
      error: { code: 'ROUTER_NOT_READY', message: 'AI router process is not running.' },
    });
  }

  if (!method || typeof method !== 'string') {
    return Promise.resolve({
      ok: false,
      error: { code: 'INVALID_REQUEST', message: 'AI router method must be a string.' },
    });
  }

  const id = aiRpcNextId++;
  const payload = { jsonrpc: '2.0', id, method, params };

  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      aiRpcPending.delete(id);
      resolve({
        ok: false,
        error: { code: 'ROUTER_TIMEOUT', message: `AI router timed out for ${method}.` },
      });
    }, timeoutMs);

    aiRpcPending.set(id, { resolve, timer });

    try {
      aiRouterProcess.stdin.write(`${JSON.stringify(payload)}\n`);
    } catch (err) {
      aiRpcPending.delete(id);
      clearTimeout(timer);
      resolve({
        ok: false,
        error: { code: 'ROUTER_WRITE_FAILED', message: err.message },
      });
    }
  });
}

// ---------------------------------------------------------------------------
// IPC handlers
// ---------------------------------------------------------------------------

ipcMain.handle('bridge:get-status', () => bridgeState);

/**
 * bridge:get-ui-config — Return the ui section of config.json to the renderer.
 * Used by exam.js to read polling intervals without hardcoding them in JS.
 * Returns: { ok: true, ui: object } | { ok: false }
 */
ipcMain.handle('bridge:get-ui-config', () => {
  try {
    const configPath = resolveConfigPath();
    const data = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    return { ok: true, ui: data.ui ?? {} };
  } catch (err) {
    process.stderr.write(`[config] bridge:get-ui-config error: ${err.message}\n`);
    return { ok: false };
  }
});

/**
 * bridge:ai-rpc — Forward a JSON-RPC request to the AI router stdin.
 * Expected args: { method: string, params?: object, timeoutMs?: number }
 */
ipcMain.handle('bridge:ai-rpc', async (_event, { method, params, timeoutMs } = {}) => {
  return sendAiRpc(method, params || {}, Number.isFinite(timeoutMs) ? timeoutMs : 10000);
});

/**
 * bridge:get-session-log — Read a session's JSONL log file from disk.
 * Arg: { sessionId: string }
 */
ipcMain.handle('bridge:get-session-log', async (_event, { sessionId }) => {
  try {
    const logPath = path.join(__dirname, '..', 'sessions', `${sessionId}.jsonl`);
    if (!fs.existsSync(logPath)) {
      return { ok: false, error: { code: 'LOG_NOT_FOUND', message: 'Session log not found.' } };
    }
    const content = fs.readFileSync(logPath, 'utf-8');
    const lines = content.split('\n').filter(line => line.trim());
    return { ok: true, data: lines };
  } catch (err) {
    return { ok: false, error: { code: 'IO_ERROR', message: err.message } };
  }
});

/**
 * bridge:export-pdf — Export current webContents to a PDF file.
 */
ipcMain.handle('bridge:export-pdf', async (_event, { filename }) => {
  try {
    const { filePath } = await shell.showSaveDialog(mainWindow, {
      defaultPath: filename,
      filters: [{ name: 'PDF Files', extensions: ['pdf'] }]
    });

    if (!filePath) return { ok: false };

    const data = await mainWindow.webContents.printToPDF({
      printBackground: true,
      margins: { top: 0, bottom: 0, left: 0, right: 0 }
    });

    fs.writeFileSync(filePath, data);
    return { ok: true, path: filePath };
  } catch (err) {
    process.stderr.write(`[pdf] export failed: ${err.message}\n`);
    return { ok: false };
  }
});

// ---------------------------------------------------------------------------
// Session IPC handlers (T008 bridge:login, T014 get-saved-session + clear-session)
// ---------------------------------------------------------------------------

/**
 * Port the Python bridge is listening on.
 * Set during startup after config is read; used by IPC handlers.
 * @type {number}
 */
let bridgePort = 5050;

/**
 * In-memory session for users who did NOT check "Remember this device".
 * Cleared when the app quits. Never written to the OS keychain.
 * @type {object | null}
 */
let sessionMemory = null;

/**
 * Exam session data returned by the LMS on a successful exam start.
 * Stored here so the Exam page can retrieve it via bridge:get-exam-session.
 * In-memory only — not persisted across app restarts.
 * @type {object | null}
 */
let examSession = null;

/**
 * Submit result returned by the LMS after the exam is submitted.
 * Stored here so the Result page can retrieve it via bridge:get-submit-result.
 * In-memory only — not persisted across app restarts.
 * @type {object | null}
 */
let submitResult = null;

/**
 * Enrollment state for the current exam attempt.
 * Set after a successful bridge:enroll-reference call.
 * Cleared on all exam exit paths (submit, back-to-home, clear-session).
 * @type {{ sessionId: string, enrolledAt: Date, succeeded: boolean } | null}
 */
let enrollmentState = null;

/** keytar service identifier shared across all session keys. */
const KEYTAR_SERVICE = 'lumina-ai-proctoring';

// ---------------------------------------------------------------------------
// Config resolution (research.md decision 4)
// Packaged:     <resources>/config.json   (electron-builder extraResources)
// Development:  <project root>/config.json
// ---------------------------------------------------------------------------

/**
 * Resolve the absolute path to config.json based on packaging state.
 * @returns {string}
 */
function resolveConfigPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'config.json');
  }
  // In development, main.js lives at frontend/main.js — config.json is one
  // level up at the project root.
  return path.join(__dirname, '..', 'config.json');
}

/**
 * Read and parse config.json.
 * Returns the parsed object, or throws with a typed error shape that mirrors
 * the Python ConfigError so Electron can surface it uniformly.
 *
 * @returns {{ baseUrl: string, pythonPort: number }}
 */
function readConfig() {
  const configPath = resolveConfigPath();

  if (!fs.existsSync(configPath)) {
    const err = new Error(`config.json not found at path: ${configPath}`);
    err.code = 'FILE_NOT_FOUND';
    throw err;
  }

  let raw;
  try {
    raw = fs.readFileSync(configPath, 'utf-8');
  } catch (ioErr) {
    const err = new Error(`Could not read config.json: ${ioErr.message}`);
    err.code = 'FILE_NOT_FOUND';
    throw err;
  }

  let data;
  try {
    data = JSON.parse(raw);
  } catch (parseErr) {
    const err = new Error(`config.json contains invalid JSON: ${parseErr.message}`);
    err.code = 'INVALID_JSON';
    throw err;
  }

  const { baseUrl, pythonPort = 5050 } = data;

  if (!baseUrl || typeof baseUrl !== 'string' || !baseUrl.trim()) {
    const err = new Error("config.json must contain a non-empty 'baseUrl' string.");
    err.code = 'MISSING_BASE_URL';
    throw err;
  }

  if (!baseUrl.trim().startsWith('https://')) {
    const err = new Error('baseUrl must use HTTPS (https://). HTTP URLs are not permitted.');
    err.code = 'INSECURE_PROTOCOL';
    throw err;
  }

  if (typeof pythonPort !== 'number' || !Number.isInteger(pythonPort) || pythonPort < 1024 || pythonPort > 65535) {
    const err = new Error(`pythonPort must be an integer between 1024 and 65535, got ${pythonPort}.`);
    err.code = 'INVALID_PORT';
    throw err;
  }

  return { baseUrl: baseUrl.trim().replace(/\/$/, ''), pythonPort };
}

// ---------------------------------------------------------------------------
// Session helpers (keytar + in-memory)
// ---------------------------------------------------------------------------

/**
 * Delete all 6 keytar entries for this application.
 * Idempotent — safe to call even if no entries exist.
 * Errors are swallowed and logged to stderr (never thrown).
 */
async function clearAllKeytarEntries() {
  const keys = [
    'access-token',
    'refresh-token',
    'token-expiry',
    'refresh-expiry',
    'user-profile',
    'remember-flag',
  ];
  for (const key of keys) {
    try {
      await keytar.deletePassword(KEYTAR_SERVICE, key);
    } catch (err) {
      process.stderr.write(`[session] clearAllKeytarEntries: key=${key} error=${err.message}\n`);
    }
  }
}

/**
 * Persist a successful login session.
 *
 * If remember=true, write all 6 entries to the OS keychain.
 * If remember=false, store the session object in module-level memory only
 * (cleared automatically when the app quits).
 *
 * Security: the raw password is NOT passed to this function and never stored.
 *
 * @param {object} data    LoginResponse object from the LMS (relayed by bridge).
 * @param {boolean} remember  Whether the user checked "Remember this device".
 */
async function storeSession(data, remember) {
  const tokenExpiry = new Date(Date.now() + data.expinresIn * 1000).toISOString();
  const userProfile = JSON.stringify({
    id: data.id,
    email: data.email,
    firstName: data.firstName,
    lastName: data.lastName,
    profilePictureUrl: data.profilePictureUrl ?? null,
  });

  const session = {
    accessToken: data.token,
    refreshToken: data.refreshToken,
    tokenExpiry,
    refreshExpiry: data.refreshTokenExpiration,
    userProfile: JSON.parse(userProfile),
  };

  if (!remember) {
    sessionMemory = session;
    return;
  }

  // Persist to OS keychain
  const entries = {
    'access-token':   data.token,
    'refresh-token':  data.refreshToken,
    'token-expiry':   tokenExpiry,
    'refresh-expiry': data.refreshTokenExpiration,
    'user-profile':   userProfile,
    'remember-flag':  '1',
  };

  for (const [key, value] of Object.entries(entries)) {
    try {
      await keytar.setPassword(KEYTAR_SERVICE, key, value);
    } catch (err) {
      process.stderr.write(`[session] storeSession: key=${key} error=${err.message}\n`);
    }
  }
}

/**
 * Attempt to restore a previously saved session from the OS keychain.
 *
 * Checks (in order):
 *   1. remember-flag === '1'
 *   2. refresh-expiry is a future date
 *   3. All remaining 4 keys are present and user-profile is valid JSON
 *
 * On any failure: clears all keytar entries and returns null.
 *
 * @returns {Promise<object|null>} Session object or null if no valid session.
 */
async function getSavedSession() {
  try {
    const flag = await keytar.getPassword(KEYTAR_SERVICE, 'remember-flag');
    if (flag !== '1') return null;

    const refreshExpiry = await keytar.getPassword(KEYTAR_SERVICE, 'refresh-expiry');
    if (!refreshExpiry || new Date(refreshExpiry) <= new Date()) {
      await clearAllKeytarEntries();
      return null;
    }

    const accessToken   = await keytar.getPassword(KEYTAR_SERVICE, 'access-token');
    const refreshToken  = await keytar.getPassword(KEYTAR_SERVICE, 'refresh-token');
    const tokenExpiry   = await keytar.getPassword(KEYTAR_SERVICE, 'token-expiry');
    const profileRaw    = await keytar.getPassword(KEYTAR_SERVICE, 'user-profile');

    if (!accessToken || !refreshToken || !tokenExpiry || !profileRaw) {
      await clearAllKeytarEntries();
      return null;
    }

    let userProfile;
    try {
      userProfile = JSON.parse(profileRaw);
    } catch (_parseErr) {
      await clearAllKeytarEntries();
      return null;
    }

    return { accessToken, refreshToken, tokenExpiry, refreshExpiry, userProfile };
  } catch (err) {
    process.stderr.write(`[session] getSavedSession error: ${err.message}\n`);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Single-instance lock (research.md decision 5)
// Prevents two Electron windows + two Python bridges competing for port 5050.
// MUST be called before app.whenReady().
// ---------------------------------------------------------------------------

const gotLock = app.requestSingleInstanceLock();

if (!gotLock) {
  // Another instance is already running — focus its window and quit.
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

// ---------------------------------------------------------------------------
// Exports (used by T011/T012 expansions and tests)
// ---------------------------------------------------------------------------

module.exports = {
  getMainWindow: () => mainWindow,
  getPythonProcess: () => pythonProcess,
  getBridgeState: () => bridgeState,
  resolveConfigPath,
  readConfig,
  // Setters used internally by startup sequence tasks
  _setMainWindow: (w) => { mainWindow = w; },
  _setPythonProcess: (p) => { pythonProcess = p; },
  _setBridgeState: (s) => { bridgeState = s; },
};

// ---------------------------------------------------------------------------
// IPC handlers
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Session IPC handlers (T008 bridge:login, T014 get-saved-session + clear-session)
// ---------------------------------------------------------------------------

/**
 * bridge:login — Proxy login credentials to the Python bridge.
 *
 * Expected args: { email: string, password: string, remember: boolean }
 * Returns: { ok: true, data: LoginResponse } | { ok: false, error: BridgeLoginError }
 *
 * Security: password is never logged.
 */
ipcMain.handle('bridge:login', async (_event, { email, password, remember }) => {
  try {
    const response = await net.fetch(`http://127.0.0.1:${bridgePort}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const body = await response.json();

    if (response.ok) {
      await storeSession(body, Boolean(remember));
      return { ok: true, data: body };
    }

    return { ok: false, error: body };
  } catch (_err) {
    return {
      ok: false,
      error: {
        code: 'BRIDGE_ERROR',
        message: 'Unable to reach the server. Please check your connection and try again.',
      },
    };
  }
});

/**
 * bridge:get-saved-session — Return a previously stored session or indicate none.
 *
 * Returns: { ok: true, session: StoredSession } | { ok: false }
 */
ipcMain.handle('bridge:get-saved-session', async () => {
  const session = await getSavedSession();
  return session ? { ok: true, session } : { ok: false };
});

/**
 * bridge:clear-session — Delete all keytar entries and in-memory session.
 *
 * Idempotent. Returns: { ok: true }
 */
ipcMain.handle('bridge:clear-session', async () => {
  await clearAllKeytarEntries();
  sessionMemory = null;
  // T029 — Unenroll face recognition embedding on logout (fire-and-forget)
  sendAiRpc('unenrollReference', { sessionId: enrollmentState?.sessionId }).catch(() => {});
  enrollmentState = null;
  return { ok: true };
});

// ---------------------------------------------------------------------------
// Identity Verification IPC handlers (spec 010)
// ---------------------------------------------------------------------------

/**
 * bridge:enroll-reference — Enroll a captured reference photo for face recognition.
 *
 * Expected args: { frame: string }  — base64 data URL of the captured JPEG
 * Returns: { ok: true } | { ok: false, error: { code, message } }
 *
 * Chains face-detect → enroll via the AI router (FaceRecognitionService.enroll).
 * On success sets enrollmentState so the exam page guard can pass.
 */
ipcMain.handle('bridge:enroll-reference', async (_event, { frame } = {}) => {
  if (!frame || typeof frame !== 'string') {
    return { ok: false, error: { code: 'BRIDGE_ERROR', message: 'No frame provided.' } };
  }

  const sessionId = examSession?.attemptId ? String(examSession.attemptId) : 'default-session';

  // Retrieve the official profile picture URL from the stored session.
  // sessionMemory is preferred (in-memory, set on login); falls back to keytar for
  // "Remember this device" sessions. The renderer never holds this value.
  let profilePictureUrl = null;
  try {
    if (sessionMemory?.userProfile?.profilePictureUrl) {
      profilePictureUrl = sessionMemory.userProfile.profilePictureUrl;
    } else {
      const profileRaw = await keytar.getPassword(KEYTAR_SERVICE, 'user-profile');
      if (profileRaw) {
        const parsed = JSON.parse(profileRaw);
        profilePictureUrl = parsed?.profilePictureUrl ?? null;
      }
    }
  } catch (_err) {
    // profilePictureUrl stays null — enrollment proceeds without identity confirmation
    process.stderr.write(`[enroll] failed to read profilePictureUrl: ${_err.message}\n`);
  }

  const rpcResult = await sendAiRpc('enrollReference', {
    frame,
    sessionId,
    profilePictureUrl,
  }, 45000);

  if (rpcResult.ok && rpcResult.result?.ok === true) {
    enrollmentState = { sessionId, enrolledAt: new Date(), succeeded: true };
    return { ok: true };
  }

  // Propagate typed error from the service layer when available
  const error = rpcResult.result?.error || rpcResult.error || {
    code: 'ENROLLMENT_FAILED',
    message: 'Enrollment did not succeed.',
  };
  return { ok: false, error };
});

/**
 * bridge:get-enrollment-status — Check whether enrollment has succeeded.
 *
 * Returns: { enrolled: boolean }
 * Returns { enrolled: false } (not an error) when no enrollment has occurred.
 */
ipcMain.handle('bridge:get-enrollment-status', () => ({
  enrolled: enrollmentState?.succeeded === true,
}));

/**
 * bridge:open-external — Open a URL in the system default browser.
 *
 * Only https:// URLs are allowed; all others are silently ignored
 * to prevent open-redirect abuse.
 */
ipcMain.handle('bridge:open-external', async (_event, url) => {
  if (typeof url === 'string' && url.startsWith('https://')) {
    await shell.openExternal(url);
  }
});

// ---------------------------------------------------------------------------
// Exam IPC handlers (spec 003)
// ---------------------------------------------------------------------------

/**
 * bridge:start-exam — Validate an exam code and start an attempt.
 *
 * Expected args: { quizCode: string }
 * Returns:
 *   { ok: true, data: ExamSession }         — success
 *   { ok: false, redirect: 'login' }        — expired token; session cleared in main.js
 *   { ok: false, error: BridgeExamError }   — typed error
 *
 * Security: token is read from session store only; never from renderer args;
 *           never logged; never echoed in error responses.
 */
ipcMain.handle('bridge:start-exam', async (_event, { quizCode }) => {
  try {
    const accessToken =
      sessionMemory?.accessToken ||
      (await keytar.getPassword(KEYTAR_SERVICE, 'access-token'));

    const response = await net.fetch(`http://127.0.0.1:${bridgePort}/exam-access`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quizCode, token: accessToken }),
    });

    const body = await response.json();

    if (response.ok) {
      examSession = body;

      const sessionId = examSession?.attemptId ? String(examSession.attemptId) : 'default-session';
      await Promise.all([
        sendAiRpc('startService', { service: 'eye-gaze', sessionId }),
        sendAiRpc('startService', { service: 'speech-detection', sessionId }),
        // Cloud (Modal) services. If not configured, router responds with an error
        // and the UI will remain "Inactive" (status poll retries continuously).
        sendAiRpc('startService', { service: 'face-recognition', sessionId }),
        sendAiRpc('startService', { service: 'face-detection', sessionId }),
        sendAiRpc('startService', { service: 'object-detection', sessionId }),
      ]);

      return { ok: true, data: examSession };
    }

    // Expired/invalid token — clear session and signal the renderer to redirect
    if (body?.code === 'UNAUTHORIZED') {
      await clearAllKeytarEntries();
      sessionMemory = null;
      return { ok: false, redirect: 'login' };
    }

    return { ok: false, error: body };
  } catch (_err) {
    return {
      ok: false,
      error: {
        code: 'BRIDGE_ERROR',
        message: 'Unable to reach the server. Please check your connection and try again.',
      },
    };
  }
});

/**
 * bridge:get-exam-session — Return the stored ExamSession to the Exam page.
 *
 * Returns: { ok: true, session: ExamSession } | { ok: false }
 */
ipcMain.handle('bridge:get-exam-session', async () => {
  if (examSession) {
    return { ok: true, session: examSession };
  }
  return { ok: false };
});

/**
 * bridge:submit-exam — Forward exam answers to the Python bridge.
 *
 * Reads the stored JWT token from keytar to attach as Authorization header.
 * Returns { ok: true, data } on success or { ok: false, redirect: 'login' } /
 * { ok: false, error } on failure.
 *
 * Returns: { ok: true, data: object } | { ok: false, redirect: 'login' } | { ok: false, error: object }
 */
ipcMain.handle('bridge:submit-exam', async (_event, { answers }) => {
  try {
    const accessToken =
      sessionMemory?.accessToken ||
      (await keytar.getPassword(KEYTAR_SERVICE, 'access-token'));

    const attemptId = examSession?.attemptId;

    const response = await net.fetch(`http://127.0.0.1:${bridgePort}/submit-exam`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ attemptId, answers, token: accessToken }),
    });

    const body = await response.json();

    if (response.ok) {
      submitResult = body;
      // T027 — Unenroll face recognition embedding on exam submit (fire-and-forget)
      sendAiRpc('unenrollReference', { sessionId: enrollmentState?.sessionId }).catch(() => {});
      enrollmentState = null;
      return { ok: true, data: submitResult };
    }

    if (body?.code === 'UNAUTHORIZED') {
      await clearAllKeytarEntries();
      sessionMemory = null;
      mainWindow?.loadFile(path.join(__dirname, 'pages/login/index.html'));
      return; // renderer IPC call never resolves — main.js navigates away
    }

    return { ok: false, error: body };
  } catch {
    return {
      ok: false,
      error: {
        code: 'BRIDGE_ERROR',
        message: 'Unable to reach the server. Please check your connection and try again.',
      },
    };
  }
});

/**
 * bridge:get-submit-result — Return the stored SubmitResult to the Result page.
 *
 * Returns: { ok: true, data: object } | { ok: false }
 */
ipcMain.handle('bridge:get-submit-result', async () => {
  if (submitResult) {
    return { ok: true, data: submitResult };
  }
  return { ok: false };
});

/**
 * bridge:get-result — Recover the result from the LMS when submitResult is absent.
 *
 * Reads examSession.attemptId and the stored JWT from keytar / sessionMemory,
 * then POSTs to the Python bridge /result route which calls
 * GET /api/QuizAttempts/result/{attemptId} on the LMS.
 *
 * On success caches the result as submitResult so subsequent calls to
 * bridge:get-submit-result return it directly.
 *
 * Returns: { ok: true, data: object } | { ok: false, redirect: 'login' } | { ok: false, error: object }
 */
ipcMain.handle('bridge:get-result', async () => {
  try {
    const attemptId = examSession?.attemptId;
    if (attemptId == null) {
      return { ok: false, redirect: 'login' };
    }

    const accessToken =
      sessionMemory?.accessToken ||
      (await keytar.getPassword(KEYTAR_SERVICE, 'access-token'));

    const response = await net.fetch(`http://127.0.0.1:${bridgePort}/result`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ attemptId, token: accessToken }),
    });

    const body = await response.json();

    if (response.ok) {
      submitResult = body;
      return { ok: true, data: submitResult };
    }

    if (body?.code === 'UNAUTHORIZED') {
      await clearAllKeytarEntries();
      sessionMemory = null;
      mainWindow?.loadFile(path.join(__dirname, 'pages/login/index.html'));
      return; // renderer IPC call never resolves — main.js navigates away
    }

    return { ok: false, error: body };
  } catch {
    return {
      ok: false,
      error: {
        code: 'BRIDGE_ERROR',
        message: 'Unable to reach the server. Please check your connection and try again.',
      },
    };
  }
});

/**
 * bridge:clear-submit-result — Clear in-memory result + session, navigate to Exam Access page.
 *
 * Called when the student clicks "Back to Home" on the Result page.
 * Clears both submitResult and examSession so subsequent navigations to
 * the Result page redirect to Login (SC-004).
 * Authentication session (keytar / sessionMemory) is NOT cleared (FR-005).
 *
 * Returns: { ok: true }
 */
ipcMain.handle('bridge:clear-submit-result', async () => {
  submitResult = null;
  // T028 — Unenroll face recognition embedding on back-to-home (fire-and-forget)
  sendAiRpc('unenrollReference', { sessionId: enrollmentState?.sessionId }).catch(() => {});
  enrollmentState = null;
  examSession = null;
  mainWindow?.loadFile(path.join(__dirname, 'pages/exam-code/index.html'));
  return { ok: true };
});

// ---------------------------------------------------------------------------
// Bridge startup (T011)
// ---------------------------------------------------------------------------

/**
 * Poll GET /ping until the bridge responds with HTTP 200.
 *
 * Per research.md decision 1 and contracts/ping.md:
 *   - 20 retries × 500 ms interval = 10 s total timeout
 *   - Returns true on first 200 OK, false after all retries exhausted
 *
 * Uses Electron's built-in net module (works inside the main process
 * and respects Electron's network stack).
 *
 * @param {string} url  Full URL to poll, e.g. "http://127.0.0.1:5050/ping"
 * @param {number} retries
 * @param {number} intervalMs
 * @returns {Promise<boolean>}
 */
function pollBridgeReady(url, retries = 20, intervalMs = 500) {
  return new Promise((resolve) => {
    let attempt = 0;

    function tryOnce() {
      attempt += 1;
      const request = net.request({ method: 'GET', url });

      request.on('response', (response) => {
        if (response.statusCode === 200) {
          resolve(true);
        } else if (attempt < retries) {
          setTimeout(tryOnce, intervalMs);
        } else {
          resolve(false);
        }
        // Drain the response body to avoid hanging connections
        response.on('data', () => {});
      });

      request.on('error', () => {
        if (attempt < retries) {
          setTimeout(tryOnce, intervalMs);
        } else {
          resolve(false);
        }
      });

      request.end();
    }

    tryOnce();
  });
}

/**
 * Spawn the Python bridge process.
 *
 * Per research.md decision 1: uses child_process.spawn (not exec) so stdout
 * and stderr streams are available for logging and error parsing.
 *
 * @param {number} port
 * @param {string} configPath
 */
function startBridge(port, configPath) {
  bridgeState = 'starting';

  const serverScript = path.join(__dirname, '..', 'python_bridge', 'server.py');

  pythonProcess = spawn('python', [
    serverScript,
    '--port', String(port),
    '--config', configPath,
  ], {
    env: process.env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  // Collect last few lines of stderr for diagnostic display on crash
  const stderrLines = [];
  pythonProcess.stderr.on('data', (chunk) => {
    const lines = chunk.toString().split('\n').filter(Boolean);
    stderrLines.push(...lines);
    if (stderrLines.length > 10) stderrLines.splice(0, stderrLines.length - 10);
  });

  // Crash / unexpected exit handler
  pythonProcess.on('close', (code) => {
    if (bridgeState === 'stopping') return; // intentional shutdown — ignore

    bridgeState = 'crashed';
    const lastLines = stderrLines.slice(-3).join(' | ');

    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('bridge:status', {
        type: 'crashed',
        code: 'BRIDGE_CRASHED',
        message: `Python bridge exited unexpectedly (code ${code}). ${lastLines}`,
      });
    }
  });
}

// ---------------------------------------------------------------------------
// Full startup sequence (T012)
// ---------------------------------------------------------------------------

app.whenReady().then(async () => {
  // Create the main window — load loading page immediately so the user
  // sees feedback while the bridge starts.
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    show: false, // show after loading page is ready to avoid white flash
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false, // required for preload contextBridge
    },
  });

  mainWindow.once('ready-to-show', () => mainWindow.show());

  await mainWindow.loadFile(path.join(__dirname, 'pages', 'loading', 'loading.html'));

  // --- Validate config before spawning bridge ---
  let config;
  try {
    config = readConfig();
  } catch (configErr) {
    bridgeState = 'failed';
    mainWindow.webContents.send('bridge:status', {
      type: 'config-error',
      code: configErr.code || 'CONFIG_ERROR',
      message: configErr.message,
    });
    return;
  }

  const { pythonPort } = config;
  const configPath = resolveConfigPath();
  const pingUrl = `http://127.0.0.1:${pythonPort}/ping`;

  // Store port at module scope so IPC handlers can reference it
  bridgePort = pythonPort;

  // --- Spawn bridge ---
  startBridge(pythonPort, configPath);
  startAIRouter();

  // --- Poll until ready or timeout ---
  const isReady = await pollBridgeReady(pingUrl);

  if (isReady) {
    bridgeState = 'ready';
    mainWindow.webContents.send('bridge:status', { type: 'ready' });

    // --- Session restore (T015): check for a valid saved session ---
    // Run BEFORE loading any page so the user never sees a flash of login UI
    // if they are already authenticated.
    const savedSession = await getSavedSession();
    if (savedSession !== null) {
      await mainWindow.loadFile(path.join(__dirname, 'pages', 'exam-code', 'index.html'));
      return;
    }

    // No valid session — show the login page
    await mainWindow.loadFile(path.join(__dirname, 'pages', 'login', 'index.html'));
  } else {
    bridgeState = 'failed';
    mainWindow.webContents.send('bridge:status', {
      type: 'failed',
      code: 'BRIDGE_FAILED',
      message: `Bridge did not respond on ${pingUrl} within 10 seconds.`,
    });
  }
});

// ---------------------------------------------------------------------------
// Window lifecycle
// ---------------------------------------------------------------------------

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    bridgeState = 'stopping';
    if (pythonProcess) pythonProcess.kill();
    app.quit();
  }
});

app.on('before-quit', () => {
  bridgeState = 'stopping';
  if (pythonProcess) pythonProcess.kill();
});
