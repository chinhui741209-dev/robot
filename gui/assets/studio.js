/* Demo Studio front-end: camera lock overlay + three.js 6-axis arm & dexterous
   hand + per-motor telemetry, polling /state.json. Vanilla JS + global THREE. */
'use strict';

const IMG_W = 640, IMG_H = 480;
let state = null;

/* ---------------- camera + lock overlay ---------------- */
const cam = document.getElementById('cam');
const overlay = document.getElementById('overlay');
const octx = overlay.getContext('2d');
let scanT = 0;

function sizeOverlay() {
  overlay.width = overlay.clientWidth;
  overlay.height = overlay.clientHeight;
}
window.addEventListener('resize', sizeOverlay);

function drawOverlay() {
  sizeOverlay();
  const W = overlay.width, H = overlay.height;
  octx.clearRect(0, 0, W, H);
  const lk = state && state.lock;
  if (!lk) return;
  const sx = W / IMG_W, sy = H / IMG_H;
  if (lk.status === 'locating') {
    scanT += 0.05;
    const y = (Math.sin(scanT) * 0.5 + 0.5) * H;
    octx.strokeStyle = 'rgba(127,209,255,0.8)'; octx.lineWidth = 2;
    octx.beginPath(); octx.moveTo(0, y); octx.lineTo(W, y); octx.stroke();
    octx.fillStyle = '#7fd1ff'; octx.font = '14px sans-serif';
    octx.fillText('LOCATING…', 12, 22);
  } else if (lk.status === 'locked') {
    const x = (lk.cx - lk.w / 2) * sx, y = (lk.cy - lk.h / 2) * sy;
    const w = lk.w * sx, h = lk.h * sy;
    octx.strokeStyle = '#6ee7a0'; octx.lineWidth = 3;
    octx.strokeRect(x, y, w, h);
    // crosshair
    const cx = lk.cx * sx, cy = lk.cy * sy;
    octx.strokeStyle = 'rgba(110,231,160,0.7)'; octx.lineWidth = 1;
    octx.beginPath(); octx.moveTo(cx - 14, cy); octx.lineTo(cx + 14, cy);
    octx.moveTo(cx, cy - 14); octx.lineTo(cx, cy + 14); octx.stroke();
    octx.fillStyle = '#6ee7a0'; octx.font = 'bold 14px sans-serif';
    octx.fillText(`LOCKED: ${lk.class} ${(lk.score * 100 | 0)}%`, x, Math.max(y - 6, 14));
  } else if (lk.status === 'fallback') {
    octx.fillStyle = '#f0b35e'; octx.font = '14px sans-serif';
    octx.fillText(`未鎖定 (${lk.reason || 'fallback'}) — 點畫面手動鎖定`, 12, 22);
  }
}

// click-to-lock fallback (maps displayed coords back to image coords)
overlay.addEventListener('click', (e) => {
  const r = overlay.getBoundingClientRect();
  const cx = (e.clientX - r.left) / r.width * IMG_W;
  const cy = (e.clientY - r.top) / r.height * IMG_H;
  post('/lock', { cx: cx | 0, cy: cy | 0, label: 'object' });
});

/* ---------------- three.js: full Unitree G1 via URDF ---------------- */
const view = document.getElementById('view3d');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0d14);
const cam3 = new THREE.PerspectiveCamera(45, 1, 0.01, 50);
cam3.position.set(0.7, 0.95, 1.05);
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
function sizeView() {
  const s = view.clientWidth;
  renderer.setSize(s, s); cam3.aspect = 1; cam3.updateProjectionMatrix();
}
view.appendChild(renderer.domElement);
const controls = new THREE.OrbitControls(cam3, renderer.domElement);
controls.target.set(0, 0.7, 0); controls.enableDamping = true;

scene.add(new THREE.AmbientLight(0xffffff, 0.7));
const key = new THREE.DirectionalLight(0xffffff, 0.9); key.position.set(1, 2, 1); scene.add(key);
const grid = new THREE.GridHelper(2, 20, 0x223047, 0x16203044); scene.add(grid);

const MAT_ROBOT = new THREE.MeshStandardMaterial({ color: 0x9fb3c8, metalness: 0.55, roughness: 0.5 });

// Telemetry arm-joint name (sim, degrees) -> G1 URDF joint (drive the LEFT arm).
// Hand fingers (thumb_j0..pinky_j1) have no joints in g1_29dof.urdf -> telemetry-only.
const JOINT_MAP = {
  shoulder_pitch: 'left_shoulder_pitch_joint',
  shoulder_roll:  'left_shoulder_roll_joint',
  shoulder_yaw:   'left_shoulder_yaw_joint',
  elbow:          'left_elbow_joint',
  wrist_roll:     'left_wrist_roll_joint',
  wrist_pitch:    'left_wrist_pitch_joint',
  wrist_yaw:      'left_wrist_yaw_joint',
};
let g1 = null, modelReady = false, framed = false;

const urdfLoader = new URDFLoader();
urdfLoader.loadMeshCb = function (path, manager, done) {
  new THREE.STLLoader(manager).load(path, function (geom) {
    geom.computeVertexNormals();
    done(new THREE.Mesh(geom, MAT_ROBOT));
  }, undefined, function () { done(null); });
};
urdfLoader.load('/assets/g1/g1_29dof.urdf', function (robot) {
  robot.rotation.x = -Math.PI / 2;   // URDF Z-up -> three.js Y-up
  scene.add(robot);
  g1 = robot; modelReady = true;
}, undefined, function () {
  view.innerHTML = '<div style="padding:24px;color:#f0b35e;font:14px sans-serif;line-height:1.6">' +
    'G1 模型載入失敗（assets/g1 未部署？執行 scripts/fetch_g1_assets.sh）。<br>' +
    '馬達遙測與相機鎖定仍正常運作。</div>';
});

const deg = (d) => d * Math.PI / 180;
function applyPose(joints) {
  if (!modelReady || !g1) return;
  for (const j of joints) {
    const jn = JOINT_MAP[j.name];
    if (!jn) continue;                 // hand / unmapped -> telemetry-only
    const joint = g1.joints[jn];
    if (joint) joint.setJointValue(deg(j.actual));
  }
}

function frameRobot() {
  // 等所有 STL mesh 載齊（bbox 有效）後，自動把整台 G1 框進畫面、腳底貼到地面格線。
  const box = new THREE.Box3().setFromObject(g1);
  const size = box.getSize(new THREE.Vector3());
  if (!isFinite(size.y) || size.y < 0.5) return false;      // mesh 尚未載齊
  g1.position.y -= box.min.y;                               // 腳底 -> y=0（grid 平面）
  const b = new THREE.Box3().setFromObject(g1);
  const c = b.getCenter(new THREE.Vector3());
  const s = b.getSize(new THREE.Vector3());
  const maxDim = Math.max(s.x, s.y, s.z);
  const dist = (maxDim / 2) / Math.tan(Math.PI / 180 * 45 / 2) * 1.5;  // 1.5 = 邊距
  controls.target.set(c.x, c.y, c.z);                       // 看向身體中心
  cam3.position.set(c.x + dist * 0.55, c.y + s.y * 0.12, c.z + dist);
  cam3.far = Math.max(50, dist * 12); cam3.updateProjectionMatrix();
  controls.update();
  return true;
}

function render3d() {
  controls.update();
  if (modelReady && g1 && !framed) framed = frameRobot();   // 載入後自動框全身（一次）
  if (renderer.domElement.parentNode) renderer.render(scene, cam3);
  requestAnimationFrame(render3d);
}

/* ---------------- motor telemetry table ---------------- */
const mrows = document.getElementById('mrows');
function tempCls(t) { return t > 55 ? 'hot' : t > 45 ? 'warm' : 'cool'; }
function renderMotors(joints) {
  let html = '', grp = '';
  for (const j of joints) {
    if (j.group !== grp) { grp = j.group;
      html += `<tr class="grp"><td colspan="7">${grp === 'arm' ? 'G1 手臂 7 軸' : 'Dex2/5 手 10 DoF'}</td></tr>`;
    }
    const tgt = ((j.target + 180) / 360 * 52) | 0;
    const act = ((j.actual + 180) / 360 * 52) | 0;
    html += `<tr>
      <td class="name">${j.name}</td>
      <td><span class="gauge"><span class="a" style="width:${act}px"></span>
          <span class="t" style="left:${tgt}px"></span></span> ${j.actual.toFixed(0)}</td>
      <td>${j.vel.toFixed(0)}</td>
      <td>${j.torque.toFixed(2)}</td>
      <td>${j.current.toFixed(2)}</td>
      <td class="${tempCls(j.temp)}">${j.temp.toFixed(1)}</td>
      <td><span class="barbg"><span class="bar" style="width:${(j.load * 0.46) | 0}px;
          background:${j.load > 70 ? '#ff6b6b' : j.load > 40 ? '#f0b35e' : '#2bb673'}"></span></span></td>
    </tr>`;
  }
  mrows.innerHTML = html;
}

/* ---------------- phase pills + log ---------------- */
const pills = [...document.querySelectorAll('.pill')];
function renderPhase(p) {
  pills.forEach(el => el.classList.toggle('on', el.dataset.p === p));
}
const logEl = document.getElementById('log');
let lastLog = '';
function pushLog(s) { if (s && s !== lastLog) { lastLog = s;
  logEl.innerHTML = `<div>• ${s}</div>` + logEl.innerHTML; } }

/* ---------------- command + voice ---------------- */
const cmd = document.getElementById('cmd');
function post(url, body) {
  return fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}) });
}
function sendCmd() { const t = cmd.value.trim(); if (!t) return;
  pushLog('指令: ' + t); post('/command', { text: t }); }
document.getElementById('send').onclick = sendCmd;
cmd.addEventListener('keydown', e => { if (e.key === 'Enter') sendCmd(); });

const micBtn = document.getElementById('mic');
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR) {
  const rec = new SR(); rec.lang = 'zh-TW'; rec.interimResults = false;
  micBtn.onclick = () => { try { rec.start(); micBtn.classList.add('on'); } catch (e) {} };
  rec.onresult = (e) => { cmd.value = e.results[0][0].transcript; micBtn.classList.remove('on'); sendCmd(); };
  rec.onend = () => micBtn.classList.remove('on');
  rec.onerror = () => micBtn.classList.remove('on');
} else {
  micBtn.title = '此瀏覽器不支援語音，請用文字'; micBtn.disabled = true; micBtn.style.opacity = .4;
}

/* ---------------- poll loop ---------------- */
async function tick() {
  try {
    state = await (await fetch('/state.json?' + Date.now())).json();
    applyPose(state.joints);
    renderMotors(state.joints);
    renderPhase(state.phase);
    if (state.lock && state.lock.status === 'locked')
      pushLog(`鎖定 ${state.lock.class} (${(state.lock.score * 100 | 0)}%)`);
    if (state.lock && state.lock.status === 'fallback')
      pushLog('未鎖定: ' + (state.lock.reason || 'fallback'));
    if (!hintShown && state.providers !== undefined) {
      hintShown = true;
      const names = { gemini: 'Gemini', openai: 'OpenAI', claude: 'Claude' };
      const ov = (state.providers && state.providers.length)
        ? state.providers.map(p => names[p] || p).join('→') : '無 key';
      const onnx = state.onnx ? '本地 ONNX(pen/box/apple/orange)' : '無本地模型';
      document.getElementById('camHint').textContent =
        `鎖定鏈：開放詞彙[${ov}] → ${onnx} → 點畫面手動鎖定。任意物體都可說出物名或點畫面。`;
    }
  } catch (e) {}
}
let hintShown = false;
cam.onerror = () => { document.getElementById('camHint').textContent =
  '相機串流無法載入（cv2 未安裝或無相機）。3D 與馬達面板仍可運作。'; };

sizeView(); window.addEventListener('resize', sizeView);
render3d();
setInterval(tick, 60);
setInterval(drawOverlay, 40);
