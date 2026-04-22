'use strict';

// ---------------------------------------------------------------------------
// Module-scope state (spec 004 — Exam Page)
// ---------------------------------------------------------------------------
let currentIndex = 0;
let examSession = null;
let answerMap = {};
const flagSet = new Set();
let activeStream = null;
let timerInterval = null;
let timerStartTime = null;
let timerTotalSeconds = 0;
let isSubmitting = false;
let autoSubmitted = false;
let remainingSeconds = 0; // U1 fix: track via variable, not DOM parsing
let dashboard = null;
let aiIntervalId = null;
let speechPollIntervalId = null;
let cloudVisionIntervalId = null;
let aiInFlight = false;
let aiCanvas = null;
let aiContext = null;
const EYE_GAZE_STREAM_INTERVAL_MS = 250;
const SPEECH_POLL_INTERVAL_MS = 2000;
const CLOUD_VISION_INTERVAL_MS = 5000; // modal_Frame_Rate

// ---------------------------------------------------------------------------
// T012 — DOMContentLoaded: load session and initialise page
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
  const result = await window.bridge.getExamSession();

  if (!result || !result.ok) {
    window.location.replace('../login/index.html');
    return;
  }

  examSession = result.session;
  const questions = examSession.questions;

  // C2 fix: guard for empty or missing questions array
  if (!questions?.length) {
    document.getElementById('examTitle').textContent = 'Error: No Questions';
    document.getElementById('skeletonOverlay').classList.add('hidden');
    return;
  }

  // Parse duration "HH:mm:ss"
  const parts = (examSession.duration || '00:00:00').split(':');
  const h = parseInt(parts[0], 10) || 0;
  const m = parseInt(parts[1], 10) || 0;
  const s = parseInt(parts[2], 10) || 0;
  timerTotalSeconds = h * 3600 + m * 60 + s;
  remainingSeconds = timerTotalSeconds;

  initPage();
  renderQuestion(0);
  startTimer();
  initWebcam();
  
  // Initialize AI Dashboard
  dashboard = new DashboardController();
  dashboard.init();

  // T032 — release camera tracks on navigation
  window.addEventListener('beforeunload', () => {
    activeStream?.getTracks().forEach(t => t.stop());
    dashboard?.destroy();
    stopAiStreaming();
  });

  document.getElementById('skeletonOverlay').classList.add('hidden');
});

// ---------------------------------------------------------------------------
// T014 — initPage: title, pills, and all event wiring
// ---------------------------------------------------------------------------

function initPage() {
  document.getElementById('examTitle').textContent = examSession.quizTitle || 'Exam';

  // Build navigator pills
  const pillsContainer = document.getElementById('pillsContainer');
  pillsContainer.innerHTML = '';
  examSession.questions.forEach((_, i) => {
    const btn = document.createElement('button');
    btn.className = 'nav-pill';
    btn.dataset.index = i;
    btn.textContent = i + 1;
    btn.setAttribute('role', 'listitem');
    btn.setAttribute('aria-label', `Question ${i + 1}`);
    btn.addEventListener('click', () => {
      currentIndex = i;
      renderQuestion(currentIndex);
    });
    pillsContainer.appendChild(btn);
  });

  // T017 — Prev button
  document.getElementById('prevBtn').addEventListener('click', () => {
    if (currentIndex > 0) {
      currentIndex--;
      renderQuestion(currentIndex);
    }
  });

  // T017 — Next button
  document.getElementById('nextBtn').addEventListener('click', () => {
    if (currentIndex < examSession.questions.length - 1) {
      currentIndex++;
      renderQuestion(currentIndex);
    }
  });

  // T018 — Jump to input
  document.getElementById('jumpInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const val = parseInt(e.target.value, 10);
      if (!isNaN(val) && val >= 1 && val <= examSession.questions.length) {
        currentIndex = val - 1;
        renderQuestion(currentIndex);
      }
      e.target.value = '';
      e.target.focus();
    }
  });

  // T021 — Submit Exam button → open confirmation modal
  document.getElementById('submitExamBtn').addEventListener('click', () => {
    const total = examSession.questions.length;
    const answered = Object.keys(answerMap).length;
    const unanswered = total - answered;

    document.getElementById('modalTitle').textContent = examSession.quizTitle || 'Submit Exam';

    if (answered === 0) {
      document.getElementById('modalMessage').textContent =
        "You haven't answered any questions yet.";
    } else if (unanswered > 0) {
      document.getElementById('modalMessage').textContent =
        `${unanswered} question(s) remaining unanswered.`;
    } else {
      document.getElementById('modalMessage').textContent =
        'All questions answered. Ready to submit.';
    }

    document.getElementById('modalBackdrop').classList.remove('hidden');
  });

  // T022 — modal Cancel
  document.getElementById('modalCancelBtn').addEventListener('click', () => {
    document.getElementById('modalBackdrop').classList.add('hidden');
  });

  // T024 — modal Confirm → submit
  document.getElementById('modalConfirmBtn').addEventListener('click', () => {
    submitExam(false);
  });

  // T025 — Retry button
  document.getElementById('retryBtn').addEventListener('click', () => {
    submitExam(autoSubmitted);
  });
}

// ---------------------------------------------------------------------------
// T013 — renderQuestion: display the question at the given index
// ---------------------------------------------------------------------------

const CHOICE_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F'];

function renderQuestion(index) {
  const q = examSession.questions[index];
  const total = examSession.questions.length;

  // Update badge
  document.getElementById('questionBadge').textContent = `Question ${index + 1} of ${total}`;

  // Update question text
  document.getElementById('questionText').textContent = q.questionText;

  // Rebuild choices list
  const list = document.getElementById('choicesList');
  list.innerHTML = '';

  q.choices.forEach((choice, ci) => {
    const li = document.createElement('li');
    li.className = 'choice-item';
    li.dataset.questionId = q.id;
    li.dataset.choiceId = choice.id;
    li.setAttribute('role', 'radio');
    li.setAttribute('aria-checked', answerMap[q.id] === choice.id ? 'true' : 'false');

    if (answerMap[q.id] === choice.id) {
      li.classList.add('is-selected');
    }

    const letter = document.createElement('span');
    letter.className = 'choice-letter';
    letter.setAttribute('aria-hidden', 'true');
    letter.textContent = CHOICE_LETTERS[ci] || String(ci + 1);

    const text = document.createElement('span');
    text.className = 'choice-text';
    text.textContent = choice.choiceText;

    li.appendChild(letter);
    li.appendChild(text);

    // T019 — choice click handler
    li.addEventListener('click', () => {
      const qId = +li.dataset.questionId;
      const cId = +li.dataset.choiceId;
      answerMap[qId] = cId;

      list.querySelectorAll('.choice-item').forEach(el => {
        el.classList.remove('is-selected');
        el.setAttribute('aria-checked', 'false');
      });
      li.classList.add('is-selected');
      li.setAttribute('aria-checked', 'true');

      updatePillStates();
    });

    list.appendChild(li);
  });

  // Update Prev/Next disabled states
  document.getElementById('prevBtn').disabled = index === 0;
  document.getElementById('nextBtn').disabled = index === total - 1;

  // Update flag button state (T029 — re-bind per question)
  const flagBtn = document.getElementById('flagBtn');
  if (flagSet.has(q.id)) {
    flagBtn.classList.add('is-flagged');
  } else {
    flagBtn.classList.remove('is-flagged');
  }

  flagBtn.onclick = () => {
    if (flagSet.has(q.id)) {
      flagSet.delete(q.id);
      flagBtn.classList.remove('is-flagged');
    } else {
      flagSet.add(q.id);
      flagBtn.classList.add('is-flagged');
    }
    updatePillStates();
  };

  updatePillStates();
}

// ---------------------------------------------------------------------------
// T015 — updatePillStates: reflect answered / current / flagged per pill
// U2 fix: use question.id to look up answerMap, not array index
// ---------------------------------------------------------------------------

function updatePillStates() {
  const pills = document.querySelectorAll('.nav-pill');
  pills.forEach((pill, i) => {
    const question = examSession.questions[i];
    pill.classList.remove('is-answered', 'is-current', 'is-flagged');

    // U2 fix: check by question id, not array index
    if (question.id in answerMap) {
      pill.classList.add('is-answered');
    }
    if (i === currentIndex) {
      pill.classList.add('is-current');
    }
    // Flagged takes priority — applied last, overwrites answered
    if (flagSet.has(question.id)) {
      pill.classList.add('is-flagged');
    }
  });
}

// ---------------------------------------------------------------------------
// T027 — startTimer: drift-corrected countdown timer
// ---------------------------------------------------------------------------

function formatSeconds(secs) {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  return [h, m, s].map(n => String(n).padStart(2, '0')).join(':');
}

function startTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
  }
  timerStartTime = Date.now();

  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - timerStartTime) / 1000);
    remainingSeconds = Math.max(0, timerTotalSeconds - elapsed); // U1 fix

    document.getElementById('timerDisplay').textContent = formatSeconds(remainingSeconds);

    const timerChip = document.getElementById('timerChip');
    if (remainingSeconds <= 300) {
      timerChip.classList.add('is-warning');
    } else {
      timerChip.classList.remove('is-warning');
    }

    if (remainingSeconds === 0 && !autoSubmitted) {
      clearInterval(timerInterval);
      timerInterval = null;
      autoSubmitted = true;
      submitExam(true);
    }
  }, 1000);
}

// ---------------------------------------------------------------------------
// T028 — resumeTimer: restart timer using remainingSeconds variable (U1 fix)
// ---------------------------------------------------------------------------

function resumeTimer() {
  // U1 fix: use remainingSeconds directly instead of parsing DOM text
  timerTotalSeconds = remainingSeconds;
  timerStartTime = Date.now();
  startTimer();
}

// ---------------------------------------------------------------------------
// T023 — submitExam: build payload, call bridge, handle result / error
// ---------------------------------------------------------------------------

async function submitExam(isAutoSubmit) {
  // Guard: prevent double-submit (including duplicate auto-submit)
  if (isSubmitting) return;

  isSubmitting = true;
  document.body.classList.add('exam-page-loading');
  document.getElementById('modalBackdrop').classList.add('hidden');
  document.getElementById('errorBanner').classList.add('hidden');

  // Pause timer
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }

  // Build answers payload (only answered questions)
  const answers = Object.entries(answerMap).map(([qId, cId]) => ({
    questionId: +qId,
    choiceId: cId,
  }));

  let result;
  try {
    result = await window.bridge.submitExam(answers);
  } catch {
    result = {
      ok: false,
      error: {
        code: 'BRIDGE_ERROR',
        message: 'Unable to reach the server. Please check your connection and try again.',
      },
    };
  }

  // I1 fix: guard against undefined result (UNAUTHORIZED — main.js navigated away)
  if (!result) return;

  if (result.ok) {
    window.location.href = '../result/index.html';
    return;
  }

  // Error recovery
  isSubmitting = false;
  document.body.classList.remove('exam-page-loading');
  document.getElementById('errorBannerText').textContent =
    result.error?.message || 'An unexpected error occurred.';
  document.getElementById('errorBanner').classList.remove('hidden');

  if (!isAutoSubmit) {
    // Resume timer for manual-submit failures only
    resumeTimer();
  }
  // For auto-submit failures: leave timer frozen at 00:00:00
}

// ---------------------------------------------------------------------------
// T031 — initWebcam: request camera access and display stream
// ---------------------------------------------------------------------------

async function initWebcam() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    activeStream = stream;
    document.getElementById('webcamFeed').srcObject = stream;
    startAiStreaming();
  } catch {
    document.getElementById('webcamFeed').classList.add('hidden');
    document.getElementById('cameraUnavailable').classList.remove('hidden');
  }
}

// ---------------------------------------------------------------------------
// AI streaming — capture frames and send predict to router
// ---------------------------------------------------------------------------

function startAiStreaming() {
  if (aiIntervalId || !window.bridge?.aiRpc) return;

  const video = document.getElementById('webcamFeed');
  if (!video) return;

  aiCanvas = document.createElement('canvas');
  aiCanvas.width = 320;
  aiCanvas.height = 240;
  aiContext = aiCanvas.getContext('2d');

  aiIntervalId = setInterval(async () => {
    if (aiInFlight || !aiContext) return;
    if (video.readyState < 2) return; // Not enough data yet

    aiInFlight = true;
    try {
      aiContext.drawImage(video, 0, 0, aiCanvas.width, aiCanvas.height);
      const frame = aiCanvas.toDataURL('image/jpeg', 0.6);

      await window.bridge.aiRpc('predict', { service: 'eye-gaze', frame });
    } catch {
      // Eye-gaze may be disabled; ignore polling errors.
    } finally {
      aiInFlight = false;
    }
  }, EYE_GAZE_STREAM_INTERVAL_MS);

  // Cloud vision services (Modal): send frames at a lower rate to avoid extra load.
  // These calls create detection events which get written into sessions/<attemptId>.jsonl
  // via the Python orchestrator.
  cloudVisionIntervalId = setInterval(async () => {
    try {
      if (!aiContext) return;
      if (video.readyState < 2) return;
      aiContext.drawImage(video, 0, 0, aiCanvas.width, aiCanvas.height);
      const frame = aiCanvas.toDataURL('image/jpeg', 0.6);

      await Promise.all([
        window.bridge.aiRpc('predict', { service: 'face-recognition', frame }),
        window.bridge.aiRpc('predict', { service: 'object-detection', frame }),
      ]);
    } catch {
      // Services may be unconfigured/stopped; ignore transient router errors.
    }
  }, CLOUD_VISION_INTERVAL_MS);

  // Speech detection runs local mic capture in the Python service and
  // this periodic predict call flushes speech violations to the UI/orchestrator.
  speechPollIntervalId = setInterval(async () => {
    try {
      await window.bridge.aiRpc('predict', { service: 'speech-detection', frame: 'MIC_POLL' });
    } catch {
      // Ignore transient router errors; status polling handles recovery.
    }
  }, SPEECH_POLL_INTERVAL_MS);
}

function stopAiStreaming() {
  if (aiIntervalId) {
    clearInterval(aiIntervalId);
    aiIntervalId = null;
  }
  if (speechPollIntervalId) {
    clearInterval(speechPollIntervalId);
    speechPollIntervalId = null;
  }
  if (cloudVisionIntervalId) {
    clearInterval(cloudVisionIntervalId);
    cloudVisionIntervalId = null;
  }
  aiCanvas = null;
  aiContext = null;
}
