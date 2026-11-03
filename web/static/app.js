/* plot3d 手机版 — Three.js 查看器 */
'use strict';

const $ = (s) => document.querySelector(s);
const canvas = $('#scene');
const statusEl = $('#status');

/* ---------- Three 基础 ---------- */
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x1e1e2e);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, 1, 0.05, 800);
camera.position.set(6, 5, 8);
const controls = new THREE.OrbitControls(camera, canvas);
controls.enableDamping = true; controls.dampingFactor = 0.08;

scene.add(new THREE.AmbientLight(0xffffff, 0.45));
const dl = new THREE.DirectionalLight(0xffffff, 0.85);
dl.position.set(-4, -5, 7); scene.add(dl);
const dl2 = new THREE.DirectionalLight(0x89b4fa, 0.25);
dl2.position.set(5, 6, -4); scene.add(dl2);

const axes = new THREE.AxesHelper(3);
const grid = new THREE.GridHelper(10, 20, 0x45475a, 0x313244);
scene.add(axes); scene.add(grid);

const geoGroup = new THREE.Group();
scene.add(geoGroup);

let lastBBox = null, wireMode = false, polyEdges = null;
const mats = [];                     // 记录材质以便切换线框

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h; camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
window.addEventListener('orientationchange', () => setTimeout(resize, 250));

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

/* ---------- 几何 → Three ---------- */
function clearGeo() {
  while (geoGroup.children.length) {
    const o = geoGroup.children.pop();
    o.geometry && o.geometry.dispose();
    if (o.material) (Array.isArray(o.material) ? o.material : [o.material])
      .forEach(m => m.dispose());
  }
  mats.length = 0;
  polyEdges = null;
}

function fitCamera(bbox) {
  if (!bbox) return;
  const cx = (bbox[0] + bbox[3]) / 2, cy = (bbox[1] + bbox[4]) / 2,
        cz = (bbox[2] + bbox[5]) / 2;
  const r = Math.max(
    Math.hypot(bbox[3] - bbox[0], bbox[4] - bbox[1], bbox[5] - bbox[2]) / 2, 0.8);
  controls.target.set(cx, cy, cz);
  const d = r * 3.1;
  camera.position.set(cx + d * 0.75, cy + d * 0.5, cz + d * 0.85);
  camera.near = Math.max(d / 200, 0.01); camera.far = d * 60;
  camera.updateProjectionMatrix();
  axes.scale.setScalar(Math.max(r, 1));
  grid.scale.setScalar(Math.max(r * 2 / 10, 1));
}

function renderGeo(g) {
  clearGeo();
  const col = new THREE.Color(g.color || '#89b4fa');
  if (g.type === 'mesh') {
    const pos = new Float32Array(g.vertices);
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geom.setIndex(g.faces);
    geom.computeVertexNormals();
    const mat = new THREE.MeshPhongMaterial({
      color: col, shininess: 40, side: THREE.DoubleSide,
      specular: 0x222233, wireframe: wireMode && !g.edges });
    mats.push(mat);
    geoGroup.add(new THREE.Mesh(geom, mat));
    if (g.edges) {                    // 多面体: 真棱线框（无扇形对角线）
      const eg = new THREE.BufferGeometry();
      eg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(g.vertices), 3));
      eg.setIndex(g.edges);
      polyEdges = new THREE.LineSegments(eg,
        new THREE.LineBasicMaterial({ color: 0xcdd6f4 }));
      polyEdges.visible = wireMode;
      geoGroup.add(polyEdges);
    }
  } else if (g.type === 'lines') {
    for (const L of g.lines) {
      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.BufferAttribute(new Float32Array(L), 3));
      const mat = new THREE.LineBasicMaterial({ color: col });
      mats.push(mat);
      geoGroup.add(new THREE.Line(geom, mat));
    }
  }
  fitCamera(g.bbox);
  lastBBox = g.bbox;
}

/* ---------- 状态与交互 ---------- */
let LIB = [];

function toast(msg, ok = false) {
  const t = $('#toast');
  t.textContent = msg;
  t.className = 'show' + (ok ? ' ok' : '');
  clearTimeout(t._h);
  t._h = setTimeout(() => t.className = '', 3200);
}

function buildLib(entries) {
  LIB = entries;
  const box = $('#lib-list'); box.innerHTML = '';
  const cats = [...new Set(entries.map(e => e.category))];
  for (const c of cats) {
    const h = document.createElement('div');
    h.className = 'cat-h';
    h.textContent = `${c} · ${entries.filter(e => e.category === c).length}`;
    box.appendChild(h);
    for (const e of entries.filter(x => x.category === c)) {
      const d = document.createElement('div');
      d.className = 'item'; d.dataset.key = e.key;
      d.innerHTML = `<img loading="lazy" src="/thumbs/${e.key}.png" alt="">` +
        `<div><div class="nm"></div><div class="ds"></div></div>`;
      d.querySelector('.nm').textContent = e.name;
      d.querySelector('.ds').textContent = e.desc || '';
      d.onclick = () => { selectEntry(e.key); closeDrawer(); };
      box.appendChild(d);
    }
  }
}

function filterLib(q) {
  q = q.trim().toLowerCase();
  document.querySelectorAll('#lib-list .item').forEach(el => {
    const e = LIB.find(x => x.key === el.dataset.key);
    const hit = !q || (e.name + e.desc + e.key).toLowerCase().includes(q);
    el.style.display = hit ? '' : 'none';
  });
  document.querySelectorAll('#lib-list .cat-h').forEach(h => {
    let n = h.nextElementSibling, vis = 0;
    while (n && n.classList.contains('item')) { vis += n.style.display !== 'none'; n = n.nextElementSibling; }
    h.style.display = vis ? '' : 'none';
  });
}

async function selectEntry(key, fromCustom = false) {
  document.querySelectorAll('#lib-list .item').forEach(el =>
    el.classList.toggle('sel', el.dataset.key === key));
  statusEl.textContent = '加载中…';
  const url = fromCustom
    ? '/api/geometry?expr=' + encodeURIComponent(key)
    : '/api/geometry?key=' + encodeURIComponent(key);
  try {
    const r = await fetch(url);
    const g = await r.json();
    if (!r.ok) throw new Error(g.error || r.status);
    renderGeo(g);
    const e = LIB.find(x => x.key === key);
    const kindName = { parametric: '参数曲线', explicit2d: '显式曲线',
      implicit2d: '隐式曲线', param_surface: '参数曲面', surface: '显式曲面',
      implicit3d: '隐式曲面', polyhedron: '多面体', triangulated: '三角剖分曲面',
      heightfield: '高度场' }[g.kind] || g.kind;
    statusEl.textContent = (e ? e.name : '自定义') + ` · ${kindName}` +
      (g.type === 'mesh' ? ` · ${g.faces.length / 3} 面片` : ` · ${g.lines.length} 线`);
    showCard(key, g);
  } catch (ex) {
    statusEl.textContent = '渲染失败';
    toast('该条目暂不支持手机端渲染: ' + ex.message);
  }
}

function showCard(key, g) {
  const e = LIB.find(x => x.key === key);
  const body = $('#card-body');
  if (!e) { body.innerHTML = '<h2>自定义表达式</h2>'; return; }
  body.innerHTML = '';
  const h = document.createElement('h2'); h.textContent = e.name;
  const cat = document.createElement('div'); cat.className = 'cat';
  cat.textContent = e.category;
  body.append(h, cat);
  if (e.formula) {
    const f = document.createElement('div'); f.className = 'formula';
    f.textContent = e.formula; body.appendChild(f);
  }
  if (e.props && e.props.length) {
    const ul = document.createElement('ul'); ul.className = 'props';
    e.props.forEach(p => { const li = document.createElement('li'); li.textContent = p; ul.appendChild(li); });
    body.appendChild(ul);
  }
  if (e.trivia) {
    const t = document.createElement('div'); t.className = 'trivia';
    t.textContent = e.trivia; body.appendChild(t);
  }
  if (e.desc) {
    const d = document.createElement('div'); d.className = 'desc';
    d.textContent = e.desc; body.appendChild(d);
  }
  if (e.expr) {
    const ex = document.createElement('div'); ex.className = 'expr';
    ex.textContent = e.expr; body.appendChild(ex);
  }
  const img = document.createElement('img');
  img.src = '/thumbs/' + e.key + '.png'; body.appendChild(img);
}

/* ---------- 抽屉 / 卡片 / 按钮 ---------- */
function openDrawer() { $('#drawer').classList.add('open'); $('#drawer-mask').classList.add('open'); }
function closeDrawer() { $('#drawer').classList.remove('open'); $('#drawer-mask').classList.remove('open'); }

$('#btn-lib').onclick = () => $('#drawer').classList.contains('open') ? closeDrawer() : openDrawer();
$('#drawer-mask').onclick = closeDrawer;
$('#q').oninput = (ev) => filterLib(ev.target.value);
$('#btn-info').onclick = () => $('#card').classList.toggle('open');
$('#card-close').onclick = () => $('#card').classList.remove('open');
$('#btn-plot').onclick = () => {
  const ex = $('#custom-expr').value.trim();
  if (!ex) return;
  closeDrawer();
  selectEntry(ex, true);
};

document.querySelectorAll('#ctrl .tgl, #ctrl [data-act=reset]').forEach(b => {
  b.onclick = () => {
    const act = b.dataset.act;
    if (act === 'axes') { axes.visible = !axes.visible; b.classList.toggle('on', axes.visible); }
    if (act === 'grid') { grid.visible = !grid.visible; b.classList.toggle('on', grid.visible); }
    if (act === 'wire') {
      wireMode = !wireMode; b.classList.toggle('on', wireMode);
      if (polyEdges) {                // 多面体: 只显示真棱, 隐藏实体面
        polyEdges.visible = wireMode;
        geoGroup.children.forEach(o => { if (o.isMesh) o.visible = !wireMode; });
        mats.forEach(m => { if ('wireframe' in m) m.wireframe = false; });
      } else {
        mats.forEach(m => { if ('wireframe' in m) m.wireframe = wireMode; });
      }
    }
    if (act === 'reset') fitCamera(lastBBox);
  };
});

/* ---------- 启动 ---------- */
(async function init() {
  resize(); animate();
  try {
    const r = await fetch('/api/library');
    const d = await r.json();
    buildLib(d.entries);
    statusEl.textContent = `${d.entries.length} 条曲线/曲面 · 点 ☰ 浏览`;
    // 默认展示第一条可渲染条目
    if (d.entries.length) selectEntry(d.entries[0].key);
  } catch (ex) {
    toast('加载图形库失败: ' + ex.message);
  }
})();
