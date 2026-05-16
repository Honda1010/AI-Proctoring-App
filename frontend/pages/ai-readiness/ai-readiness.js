'use strict';

const EYE_CALIBRATION_INTERVAL_MS = 100;
const SPEECH_POLL_INTERVAL_MS = 1000;
const STATUS_POLL_INTERVAL_MS = 1000;

let stream = null;
let canvas = null;
let ctx = null;
let eyeTimer = null;
let speechTimer = null;
let statusTimer = null;
let eyeReady = false;
let speechReady = false;
let inFlight = false;
let unsubscribeAi = null;

const eyeStatusEl = document.getElementById('eyeStatus');
const speechStatusEl = document.getElementById('speechStatus');
const hintTextEl = document.getElementById('hintText');
const continueBtn = document.getElementById('continueBtn');
const webcamFeed = document.getElementById('webcamFeed');
const cameraUnavailable = document.getElementById('cameraUnavailable');

document.addEventListener('DOMContentLoaded', async () => {
  const result = await window.bridge.getExamSession();
  if (!result?.ok) {
    window.location.replace('../exam-code/index.html');
    return;
  }

  continueBtn.addEventListener('click', () => {
    window.location.href = '../exam-instructions/index.html';
  });

  unsubscribeAi = window.bridge.onAiEvent((event) => {
    const data = event?.params || event;
    const msgType = event?.type || event?.method;

    // FIX: Handle serviceError notifications for eye-gaze.
    // Previously only 'detection' events were handled, so a model-load failure
    // (e.g. missing face_landmarker.task) was silently ignored and the pill
    // stayed on 'Calibrating' forever.
    if (msgType === 'serviceError' && data?.service === 'eye-gaze') {
      eyeReady = false;
      setPill(eyeStatusEl, 'error', 'Unavailable');
      updateGate();
      return;
    }

    if (msgType !== 'detection') return;
    if (data?.service !== 'eye-gaze') return;

    const status = data?.payload?.status || 'initializing';
    if (status !== 'initializing') {
      eyeReady = true;
      setPill(eyeStatusEl, 'ready', 'Ready');
    } else {
      setPill(eyeStatusEl, 'pending', 'Calibrating');
    }
    updateGate();
  });

  await initCamera();
  startReadinessLoops();
});

window.addEventListener('beforeunload', () => {
  stopReadinessLoops();
  stream?.getTracks().forEach((t) => t.stop());
  if (unsubscribeAi) unsubscribeAi();
});

async function initCamera() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    webcamFeed.srcObject = stream;
    cameraUnavailable.classList.add('hidden');
    hintTextEl.textContent = 'Please look at the screen and keep your face visible.';
  } catch {
    webcamFeed.classList.add('hidden');
    cameraUnavailable.classList.remove('hidden');
    setPill(eyeStatusEl, 'error', 'Camera Error');
    hintTextEl.textContent = 'Camera access is required to calibrate eye gaze.';
  }
}

function startReadinessLoops() {
  canvas = document.createElement('canvas');
  canvas.width = 320;
  canvas.height = 240;
  ctx = canvas.getContext('2d');

  eyeTimer = setInterval(runEyeCalibrationTick, EYE_CALIBRATION_INTERVAL_MS);
  speechTimer = setInterval(runSpeechTick, SPEECH_POLL_INTERVAL_MS);
  statusTimer = setInterval(syncStatusTick, STATUS_POLL_INTERVAL_MS);
}

function stopReadinessLoops() {
  if (eyeTimer) clearInterval(eyeTimer);
  if (speechTimer) clearInterval(speechTimer);
  if (statusTimer) clearInterval(statusTimer);
  eyeTimer = null;
  speechTimer = null;
  statusTimer = null;
}

async function runEyeCalibrationTick() {
  if (inFlight || !ctx || !webcamFeed || webcamFeed.readyState < 2) return;
  inFlight = true;
  try {
    ctx.drawImage(webcamFeed, 0, 0, canvas.width, canvas.height);
    const frame = canvas.toDataURL('image/jpeg', 0.6);
    await window.bridge.aiRpc('predict', { service: 'eye-gaze', frame }, { timeoutMs: 5000 });
  } catch {
    setPill(eyeStatusEl, 'pending', 'Calibrating');
  } finally {
    inFlight = false;
    updateGate();
  }
}

async function runSpeechTick() {
  try {
    const res = await window.bridge.aiRpc(
      'predict',
      { service: 'speech-detection', frame: 'MIC_POLL' },
      { timeoutMs: 5000 }
    );
    if (res?.ok) {
      speechReady = true;
      setPill(speechStatusEl, 'ready', 'Ready');
    } else {
      // Service not running or router error — mark as not available
      speechReady = false;
      setPill(speechStatusEl, 'error', 'Not Running');
    }
  } catch {
    setPill(speechStatusEl, 'pending', 'Checking');
  } finally {
    updateGate();
  }
}

async function syncStatusTick() {
  try {
    const res = await window.bridge.aiRpc('queryStatus', {}, { timeoutMs: 5000 });
    if (!res?.ok) {
      // Router unreachable — surface an error so pills don't stay pending forever
      setPill(eyeStatusEl, 'error', 'Not Running');
      setPill(speechStatusEl, 'error', 'Not Running');
      eyeReady = false;
      speechReady = false;
      return;
    }
    const statuses = res.result || {};
    const eyeStatus = statuses['eye-gaze'];
    const speechStatus = statuses['speech-detection'];

    if (eyeStatus !== 'running') {
      // FIX: Only set eyeReady=false and show an error pill when the service is
      // genuinely not running/unavailable.  Do NOT override eyeReady=true here —
      // a previous detection event may have already completed calibration and set
      // it. The status poll only fires every 1 s, so clobbering 'ready' would
      // cause a 1-second flicker even when calibration succeeded.
      if (!eyeReady) {
        const label = eyeStatus === 'unavailable' ? 'Unavailable' : 'Not Running';
        setPill(eyeStatusEl, 'error', label);
      }
      eyeReady = false;
    }
    if (speechStatus === 'running' && !speechReady) {
      setPill(speechStatusEl, 'pending', 'Checking');
    } else if (speechStatus !== 'running') {
      const label = speechStatus === 'unavailable' ? 'Unavailable' : 'Not Running';
      setPill(speechStatusEl, 'error', label);
      speechReady = false;
    }
  } catch {
    // Ignore transient router errors.
  } finally {
    updateGate();
  }
}

function updateGate() {
  const allReady = eyeReady && speechReady;
  const wasDisabled = continueBtn.disabled;
  continueBtn.disabled = !allReady;
  hintTextEl.textContent = allReady
    ? 'All checks complete. You can continue to the exam.'
    : 'Preparing models. Keep looking at the screen for eye calibration.';

  // Auto-navigate once calibration succeeds — give the student 800 ms to see
  // the "All checks complete" message before proceeding automatically.
  if (allReady && wasDisabled) {
    setTimeout(() => continueBtn.click(), 800);
  }
}

function setPill(el, kind, text) {
  el.className = `pill ${kind}`;
  el.textContent = text;
}
