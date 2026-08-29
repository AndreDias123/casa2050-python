/**
 * Maquete 3D do dashboard — mesma cena Three.js do protótipo "Tour 3D",
 * agora conectada ao banco de verdade: os 10 dispositivos modelados
 * (mapeados por nome, ver NAME_TO_SCENE) refletem dispositivo.ativo ao
 * carregar, clicar chama a mesma rota POST /dispositivo/<id>/alternar que
 * o resto do app usa, e um poll periódico em /api/dispositivos pega
 * mudanças feitas pelo agendador ou por outra aba/pessoa.
 *
 * Carregada só quando a aba "Maquete 3D" é aberta pela primeira vez (ver
 * dashboard.html) — não pesa no carregamento normal do painel.
 */
window.iniciarCasa3D = function (opts) {
  "use strict";

  var NAME_TO_SCENE = {
    "Luz da Sala": "luz-sala",
    "TV da Sala": "tv-sala",
    "Luz da Cozinha": "luz-cozinha",
    "Robô Aspirador": "robo",
    "Luz do Quarto": "luz-quarto",
    "Ar-condicionado": "ac",
    "Janela do Quarto": "janela-quarto",
    "Porta da Garagem": "porta-garagem",
    "Luz Externa": "luz-externa",
    "Câmera Externa": "camera-externa"
  };

  opts.deviceMap = {};
  (opts.dispositivos || []).forEach(function (d) {
    var sceneId = NAME_TO_SCENE[d.nome];
    if (sceneId) opts.deviceMap[sceneId] = d;
  });

  var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var wrap = document.getElementById('iso3d-wrap');
  var appEl = document.getElementById('iso3d-app');

  var ACCENT = 0x2fd8cf;
  var WARM = 0xffb870;
  var COOL = 0xbfe0ff;
  var WALL_H = 2.6, WALL_T = 0.2;
  var wallColor = 0xd7d2c4;

  var renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  if (renderer.outputEncoding !== undefined) renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  appEl.appendChild(renderer.domElement);

  var scene = new THREE.Scene();
  var skyColor = 0x080b14;
  scene.background = new THREE.Color(skyColor);
  scene.fog = new THREE.Fog(skyColor, 18, 55);

  var camera = new THREE.PerspectiveCamera(52, wrap.clientWidth / wrap.clientHeight, 0.1, 200);
  camera.position.set(0, 14, 22);

  var hemi = new THREE.HemisphereLight(0x33415c, 0x0a0a0a, 0.55);
  scene.add(hemi);
  var moon = new THREE.DirectionalLight(0x9fb6d9, 0.55);
  moon.position.set(-14, 20, 10);
  moon.castShadow = true;
  moon.shadow.mapSize.set(2048, 2048);
  moon.shadow.camera.left = -26; moon.shadow.camera.right = 26;
  moon.shadow.camera.top = 26; moon.shadow.camera.bottom = -26;
  moon.shadow.camera.far = 60;
  moon.shadow.bias = -0.0015;
  scene.add(moon);

  (function stars() {
    var n = 700, pos = new Float32Array(n * 3);
    for (var i = 0; i < n; i++) {
      var r = 70 + Math.random() * 30;
      var theta = Math.random() * Math.PI * 2;
      var phi = Math.random() * Math.PI * 0.5;
      pos[i*3] = r * Math.sin(phi) * Math.cos(theta);
      pos[i*3+1] = 8 + r * Math.cos(phi) * 0.6;
      pos[i*3+2] = r * Math.sin(phi) * Math.sin(theta);
    }
    var g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    var m = new THREE.PointsMaterial({ color: 0xffffff, size: 0.35, transparent: true, opacity: 0.65 });
    scene.add(new THREE.Points(g, m));
  })();

  function box(w, h, d, color, o) {
    o = o || {};
    var mat = new THREE.MeshStandardMaterial({
      color: color, roughness: o.roughness !== undefined ? o.roughness : 0.85, metalness: o.metalness || 0,
      emissive: o.emissive || 0x000000, emissiveIntensity: o.emissiveIntensity || 0,
      transparent: !!o.transparent, opacity: o.opacity !== undefined ? o.opacity : 1
    });
    var m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
    m.castShadow = o.castShadow !== false;
    m.receiveShadow = o.receiveShadow !== false;
    return m;
  }
  function orb(r, color, o) {
    o = o || {};
    var mat = new THREE.MeshStandardMaterial({ color: color, roughness: 0.4, emissive: o.emissive || color, emissiveIntensity: o.emissiveIntensity || 0 });
    var m = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 16), mat);
    m.castShadow = false;
    return m;
  }
  function place(mesh, x, y, z, ry) { mesh.position.set(x, y, z); if (ry) mesh.rotation.y = ry; scene.add(mesh); return mesh; }
  function wallEW(cx, cz, length, h, t) { h = h || WALL_H; t = t || WALL_T; return place(box(length, h, t, wallColor, { roughness: 0.9 }), cx, h / 2, cz); }
  function wallNS(cx, cz, length, h, t) { h = h || WALL_H; t = t || WALL_T; return place(box(t, h, length, wallColor, { roughness: 0.9 }), cx, h / 2, cz); }
  function floorPlane(cx, cz, w, d, color, y) {
    var m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshStandardMaterial({ color: color, roughness: 0.95 }));
    m.rotation.x = -Math.PI / 2; m.position.set(cx, y || 0.02, cz); m.receiveShadow = true; scene.add(m); return m;
  }

  floorPlane(0, 0, 90, 90, 0x0b0f0c, -0.02);
  floorPlane(-3, -11, 18, 10, 0x171a15, 0.0);
  floorPlane(-5, -12.5, 3.4, 9, 0x3b382f, 0.01);
  floorPlane(-4, -3, 8, 6, 0x2a251f);
  floorPlane(-4, 3, 8, 6, 0x212a25);
  floorPlane(4, 0, 8, 12, 0x2a2320);
  floorPlane(-11, -3, 6, 6, 0x1b1c1e);

  wallEW(-6.95, -6, 2.1); wallEW(1.95, -6, 12.1); wallEW(0, 6, 16);
  wallNS(-8, 3, 6); wallNS(8, 0, 12);
  wallEW(-5.3, 0, 5.4); wallEW(-0.7, 0, 1.4);
  wallNS(0, -4.3, 3.4); wallNS(0, 2.3, 7.4);
  wallNS(-8, -4.8, 2.4); wallNS(-8, -1.2, 2.4);
  wallNS(-14, -3, 6); wallEW(-11, 0, 6);
  place(box(6, 0.4, WALL_T, wallColor), -11, WALL_H - 0.2, -6);

  var devices = {};
  var deviceOrder = [];
  function registerDevice(sceneId, mesh, apply) {
    var d = (opts.deviceMap || {})[sceneId];
    var initialOn = d ? d.ativo : false;
    devices[sceneId] = { name: d ? d.nome : sceneId, realId: d ? d.id : null, podeControlar: d ? d.pode_controlar : false, mesh: mesh, on: initialOn, apply: apply };
    deviceOrder.push(sceneId);
    mesh.userData.deviceId = sceneId;
    apply(initialOn);
  }

  var garagePanel = place(box(5.6, 2.2, 0.12, 0x8b8f96, { metalness: 0.4, roughness: 0.5 }), -11, 1.1, -6);
  var garageClosedY = 1.1, garageOpenY = 2.85, garageTargetY = garageClosedY;

  var quartoWindow = place(box(0.08, 1.3, 2.4, COOL, { emissive: COOL, emissiveIntensity: 0.35, transparent: true, opacity: 0.55, metalness: 0.1, roughness: 0.1, castShadow: false }), 7.92, 1.55, -2.3);
  place(box(0.1, 1.34, 0.08, 0x2a2a2a), 7.9, 1.55, -2.3);
  place(box(0.1, 0.08, 2.44, 0x2a2a2a), 7.9, 1.55, -2.3);

  place(box(2.5, 0.5, 0.95, 0x3c342c), -7.2, 0.3, -3.2);
  place(box(2.5, 0.55, 0.2, 0x3c342c), -7.2, 0.65, -3.66);
  place(box(0.85, 0.32, 0.5, 0x2a2620), -6.0, 0.2, -2.2);
  var tv = place(box(1.5, 0.85, 0.06, 0x0c0c0c, { emissive: COOL, emissiveIntensity: 0.9, castShadow: false }), -7.87, 1.55, -3.2);
  place(box(0.9, 0.06, 0.9, 0x120f0c), -6.0, 0.03, -2.4);
  var salaLamp = new THREE.PointLight(WARM, 0.6, 8, 2); salaLamp.position.set(-5.2, 1.7, -1.2); scene.add(salaLamp);
  var salaBulb = place(orb(0.09, WARM, { emissiveIntensity: 0.9 }), -5.2, 1.7, -1.2);

  place(box(6.4, 0.9, 0.7, 0x342c24), -4.6, 0.45, 5.55);
  place(box(6.4, 0.5, 0.6, 0x241f1a), -4.6, 2.15, 5.6);
  place(box(0.85, 1.9, 0.72, 0x1c1c1c, { metalness: 0.3, roughness: 0.4 }), -7.4, 0.95, 1.2);
  var kitchenStrip = place(box(0.05, 1.5, 0.05, ACCENT, { emissive: ACCENT, emissiveIntensity: 1.1, castShadow: false }), -6.98, 0.95, 1.2);
  place(box(1.1, 0.75, 1.1, 0x2c2620), -1.6, 0.38, 4.3);
  var kitLamp = new THREE.PointLight(0xfff2d9, 0.5, 7, 2); kitLamp.position.set(-4.6, 2.3, 3.5); scene.add(kitLamp);

  var robot = place(box(0.55, 0.14, 0.55, 0x1a1a1a, { roughness: 0.4 }), -2.4, 0.09, 3.6);
  robot.geometry = new THREE.CylinderGeometry(0.28, 0.28, 0.12, 20);
  var robotBaseX = -2.4, robotBaseZ = 3.6;
  var robotRing = place(box(0.5, 0.02, 0.5, ACCENT, { emissive: ACCENT, emissiveIntensity: 1.4, castShadow: false, receiveShadow: false }), -2.4, 0.02, 3.6);
  robotRing.geometry = new THREE.RingGeometry(0.2, 0.26, 24);
  robotRing.rotation.x = -Math.PI / 2;

  place(box(2.0, 0.4, 2.6, 0x241f1a), 6.3, 0.2, -2.6);
  place(box(1.9, 0.35, 2.5, 0xd9d2c2, { roughness: 0.9 }), 6.3, 0.55, -2.6);
  place(box(1.9, 0.22, 0.6, 0xffffff, { roughness: 0.95 }), 6.3, 0.78, -3.75);
  place(box(0.55, 0.5, 0.5, 0x2a231d), 7.4, 0.25, -4.3);
  var nightLamp = new THREE.PointLight(WARM, 0.85, 6, 2); nightLamp.position.set(7.4, 0.75, -4.3); scene.add(nightLamp);
  var nightBulb = place(orb(0.1, WARM, { emissiveIntensity: 0.75 }), 7.4, 0.65, -4.3);
  place(box(1.3, 1.7, 0.5, 0x2a241d), 4.3, 0.85, 5.4);
  var acUnit = place(box(0.7, 0.35, 0.35, 0x232323, { roughness: 0.6, emissive: COOL, emissiveIntensity: 0 }), 6.6, 1.6, 3.5);

  place(box(3.6, 0.55, 1.6, 0x1c2430, { metalness: 0.5, roughness: 0.35 }), -11, 0.42, -2.6);
  place(box(1.7, 0.5, 1.35, 0x161c26, { metalness: 0.5, roughness: 0.35 }), -11, 0.92, -2.6);
  [[-12.5,-3.7],[-9.5,-3.7],[-12.5,-1.5],[-9.5,-1.5]].forEach(function (p) { place(box(0.32, 0.32, 0.18, 0x0c0c0c, { roughness: 0.7 }), p[0], 0.16, p[1]); });
  place(box(0.4, 1.8, 1.6, 0x241f1a), -13.4, 0.9, -1.2);

  var post = place(box(0.12, 3, 0.12, 0x2a2a2a), -6.3, 1.5, -10.5);
  var postBulb = place(box(0.28, 0.28, 0.28, WARM, { emissive: WARM, emissiveIntensity: 1.1, castShadow: false }), -6.3, 3.05, -10.5);
  var postLight = new THREE.PointLight(WARM, 1.1, 10, 2); postLight.position.set(-6.3, 3, -10.5); scene.add(postLight);
  var camHead = place(box(0.34, 0.2, 0.2, 0x18181a, { roughness: 0.4 }), -3.4, 1.85, -6.75);
  place(box(0.08, 1.8, 0.08, 0x1c1c1c), -3.4, 0.9, -6.6);
  var camLed = place(box(0.05, 0.05, 0.05, 0xff4d4d, { emissive: 0xff4d4d, emissiveIntensity: 1.5, castShadow: false }), -3.4, 1.9, -6.6);

  function foliage(x, z, s) {
    place(box(0.14 * s, 0.7 * s, 0.14 * s, 0x2b2118), x, 0.35 * s, z);
    var top = new THREE.Mesh(new THREE.IcosahedronGeometry(0.55 * s, 0), new THREE.MeshStandardMaterial({ color: 0x1b2a1c, roughness: 1 }));
    top.position.set(x, 0.95 * s, z); top.castShadow = true; scene.add(top);
  }
  foliage(-9.5, -11, 1.4); foliage(3, -11.5, 1.1); foliage(6.5, -9.5, 0.9);

  var robotActive = false, camActive = true;
  registerDevice('luz-sala', salaBulb, function (on) { salaLamp.intensity = on ? 0.6 : 0; salaBulb.material.emissiveIntensity = on ? 0.9 : 0.08; });
  registerDevice('tv-sala', tv, function (on) { tv.material.emissiveIntensity = on ? 0.9 : 0; tv.material.color.set(on ? 0x0c0c0c : 0x050505); });
  registerDevice('luz-cozinha', kitchenStrip, function (on) { kitLamp.intensity = on ? 0.5 : 0; kitchenStrip.material.emissiveIntensity = on ? 1.1 : 0.15; });
  registerDevice('robo', robot, function (on) {
    robotActive = on; robotRing.material.emissiveIntensity = on ? 1.4 : 0.25;
    if (!on) { robot.position.set(robotBaseX, 0.09, robotBaseZ); robotRing.position.set(robotBaseX, 0.02, robotBaseZ); }
  });
  registerDevice('luz-quarto', nightBulb, function (on) { nightLamp.intensity = on ? 0.85 : 0; nightBulb.material.emissiveIntensity = on ? 0.75 : 0.08; });
  registerDevice('ac', acUnit, function (on) { acUnit.material.emissiveIntensity = on ? 0.5 : 0; });
  registerDevice('janela-quarto', quartoWindow, function (on) { quartoWindow.material.opacity = on ? 0.18 : 0.55; quartoWindow.material.emissiveIntensity = on ? 0.05 : 0.35; });
  registerDevice('porta-garagem', garagePanel, function (on) { garageTargetY = on ? garageOpenY : garageClosedY; });
  registerDevice('luz-externa', postBulb, function (on) { postLight.intensity = on ? 1.1 : 0; postBulb.material.emissiveIntensity = on ? 1.1 : 0.08; });
  registerDevice('camera-externa', camHead, function (on) { camActive = on; camLed.material.emissiveIntensity = on ? 1.1 : 0.15; });

  var countOnEl = document.getElementById('iso3d-count-on');
  var countTotalEl = document.getElementById('iso3d-count-total');
  countTotalEl.textContent = deviceOrder.length;
  function refreshCount() {
    var n = 0;
    for (var i = 0; i < deviceOrder.length; i++) if (devices[deviceOrder[i]].on) n++;
    countOnEl.textContent = n;
  }
  refreshCount();

  var posPts = [
    new THREE.Vector3(0, 15, 24), new THREE.Vector3(-3, 5, -14), new THREE.Vector3(-5, 1.7, -11),
    new THREE.Vector3(-5, 1.6, -6.5), new THREE.Vector3(-4, 1.6, -3), new THREE.Vector3(-2.5, 1.6, -1.5),
    new THREE.Vector3(-2, 1.6, 0.4), new THREE.Vector3(-1.8, 1.7, 2.1), new THREE.Vector3(-1.5, 1.7, 2.5),
    new THREE.Vector3(-1, 1.6, -1), new THREE.Vector3(0.4, 1.6, -2), new THREE.Vector3(3, 1.7, -2.5),
    new THREE.Vector3(5.5, 1.7, -3.6), new THREE.Vector3(2.5, 2.2, 2), new THREE.Vector3(-2, 1.6, -2.5),
    new THREE.Vector3(-7.6, 1.6, -3), new THREE.Vector3(-10, 1.7, -1.5), new THREE.Vector3(-12.5, 2.2, -4.2),
    new THREE.Vector3(12, 11, 22)
  ];
  var lookPts = [
    new THREE.Vector3(0, 1, 0), new THREE.Vector3(-5, 1.5, -8), new THREE.Vector3(-5, 1.5, -6),
    new THREE.Vector3(-5, 1.4, -3), new THREE.Vector3(-6.5, 1.4, -1.5), new THREE.Vector3(-2, 1.4, 0.5),
    new THREE.Vector3(-2, 1.4, 3), new THREE.Vector3(-4.6, 1.2, 5.4), new THREE.Vector3(-2.4, 1, 3.6),
    new THREE.Vector3(0, 1.4, -2), new THREE.Vector3(3, 1.4, -2.2), new THREE.Vector3(6.3, 1.3, -2.6),
    new THREE.Vector3(7.6, 1.5, -2.3), new THREE.Vector3(5, 1.4, 1), new THREE.Vector3(-6, 1.4, -2.8),
    new THREE.Vector3(-11, 1.4, -3), new THREE.Vector3(-11, 1, -2.6), new THREE.Vector3(-11, 1.1, -2.6),
    new THREE.Vector3(0, 1, 0)
  ];
  var posCurve = new THREE.CatmullRomCurve3(posPts, false, 'centripetal', 0.5);
  var lookCurve = new THREE.CatmullRomCurve3(lookPts, false, 'centripetal', 0.5);
  var NPTS = posPts.length;
  var segDur = [5, 2, 2, 2.5, 3, 2, 1.5, 3, 2.5, 2.5, 1.5, 3, 3, 3, 3, 1.5, 3, 5];
  var segCum = [0];
  for (var si = 0; si < segDur.length; si++) segCum.push(segCum[si] + segDur[si]);
  var TOTAL = segCum[segCum.length - 1];
  function smoothstep(x) { return x * x * (3 - 2 * x); }
  function uFromElapsed(sec) {
    var s = Math.max(0, Math.min(sec, TOTAL - 0.0001)), i = 0;
    while (i < segDur.length - 1 && s >= segCum[i + 1]) i++;
    var localT = (s - segCum[i]) / segDur[i];
    var eased = smoothstep(Math.max(0, Math.min(1, localT)));
    return Math.min(0.9999, (i + eased) / (NPTS - 1));
  }
  var labelStops = [
    { at: 0.00, label: 'Vista aérea' }, { at: 0.10, label: 'Área Externa' }, { at: 0.235, label: 'Sala' },
    { at: 0.337, label: 'Cozinha' }, { at: 0.480, label: 'Sala' }, { at: 0.531, label: 'Quarto' },
    { at: 0.745, label: 'Sala' }, { at: 0.806, label: 'Garagem' }, { at: 0.95, label: 'Vista aérea' }
  ];
  function labelFor(frac) { var lbl = labelStops[0].label; for (var i = 0; i < labelStops.length; i++) if (frac >= labelStops[i].at) lbl = labelStops[i].label; return lbl; }

  var elapsed = 0, playing = !reducedMotion, freeMode = !!reducedMotion;
  var clock = new THREE.Clock();
  var orbit = new THREE.OrbitControls(camera, renderer.domElement);
  orbit.enableDamping = true; orbit.dampingFactor = 0.08;
  orbit.minDistance = 3; orbit.maxDistance = 55; orbit.maxPolarAngle = Math.PI * 0.49;
  orbit.target.set(0, 1.2, 0); orbit.enabled = freeMode;
  if (freeMode) { camera.position.set(16, 10, 22); orbit.update(); }

  var playBtn = document.getElementById('iso3d-play');
  var playIcon = document.getElementById('iso3d-play-icon');
  var pauseIcon = document.getElementById('iso3d-pause-icon');
  var restartBtn = document.getElementById('iso3d-restart');
  var freeToggle = document.getElementById('iso3d-freetoggle');
  var roomLabel = document.getElementById('iso3d-room');
  var fill = document.getElementById('iso3d-fill');
  var toast = document.getElementById('iso3d-toast');
  var toastName = document.getElementById('iso3d-toast-name');
  var toastState = document.getElementById('iso3d-toast-state');

  var toastTimer = null;
  function showToast(name, on, texto) {
    toastName.textContent = name;
    toastState.textContent = texto || (on ? 'Ligado / ativo' : 'Desligado / inativo');
    toastState.className = 's' + (on ? ' on' : '');
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove('show'); }, 2400);
  }

  function syncPlayIcon() {
    playIcon.style.display = playing ? 'none' : 'block';
    pauseIcon.style.display = playing ? 'block' : 'none';
    playBtn.setAttribute('aria-label', playing ? 'Pausar tour' : 'Retomar tour');
  }
  function setFreeMode(on) {
    freeMode = on; orbit.enabled = on;
    freeToggle.classList.toggle('active', on);
    freeToggle.textContent = on ? 'Tour automático' : 'Controle livre';
    if (on) { orbit.target.copy(lookCurve.getPoint(uFromElapsed(elapsed))); orbit.update(); }
  }
  setFreeMode(freeMode);
  syncPlayIcon();
  roomLabel.textContent = reducedMotion ? 'Explore livremente' : labelFor(0);

  playBtn.addEventListener('click', function () { if (freeMode) setFreeMode(false); playing = !playing; syncPlayIcon(); });
  restartBtn.addEventListener('click', function () { elapsed = 0; playing = true; syncPlayIcon(); if (freeMode) setFreeMode(false); });
  freeToggle.addEventListener('click', function () { setFreeMode(!freeMode); });

  // ---------- integração com o back-end de verdade ----------
  function csrfHeaders() { return { 'X-CSRFToken': opts.csrfToken }; }

  function toggleDevice(sceneId) {
    var d = devices[sceneId];
    if (!d) return;
    if (!d.realId) return;
    if (!d.podeControlar) { showToast(d.name, d.on, 'Sem permissão pra controlar'); return; }

    var novoEstado = !d.on;
    d.on = novoEstado;
    d.apply(novoEstado);
    refreshCount();
    showToast(d.name, novoEstado);
    if (playing && !freeMode) { playing = false; syncPlayIcon(); }

    fetch('/dispositivo/' + d.realId + '/alternar', { method: 'POST', headers: csrfHeaders() })
      .catch(function () {})
      .then(function () { setTimeout(syncFromServer, 300); });
  }

  function syncFromServer() {
    fetch('/api/dispositivos').then(function (r) { return r.json(); }).then(function (lista) {
      lista.forEach(function (real) {
        var sceneId = NAME_TO_SCENE[real.nome];
        if (!sceneId) return;
        var d = devices[sceneId];
        if (!d) return;
        d.realId = real.id;
        d.podeControlar = real.pode_controlar;
        if (d.on !== real.ativo) {
          d.on = real.ativo;
          d.apply(d.on);
          refreshCount();
          showToast(d.name, d.on, (d.on ? 'Ligado' : 'Desligado') + ' — atualizado');
        }
      });
    }).catch(function () {});
  }
  setInterval(syncFromServer, 5000);

  var raycaster = new THREE.Raycaster();
  var pointerNdc = new THREE.Vector2();
  var interactiveMeshes = deviceOrder.map(function (id) { return devices[id].mesh; });

  function ndcFromEvent(ev) {
    var rect = renderer.domElement.getBoundingClientRect();
    var cx = (ev.touches && ev.touches[0]) ? ev.touches[0].clientX : ev.clientX;
    var cy = (ev.touches && ev.touches[0]) ? ev.touches[0].clientY : ev.clientY;
    pointerNdc.x = ((cx - rect.left) / rect.width) * 2 - 1;
    pointerNdc.y = -((cy - rect.top) / rect.height) * 2 + 1;
  }
  function deviceUnderPointer() {
    raycaster.setFromCamera(pointerNdc, camera);
    var hits = raycaster.intersectObjects(interactiveMeshes, false);
    return hits.length ? hits[0].object.userData.deviceId : null;
  }
  renderer.domElement.addEventListener('pointermove', function (ev) {
    ndcFromEvent(ev);
    renderer.domElement.style.cursor = deviceUnderPointer() ? 'pointer' : 'grab';
  });
  renderer.domElement.addEventListener('click', function (ev) {
    ndcFromEvent(ev);
    var id = deviceUnderPointer();
    if (id) toggleDevice(id);
  });

  function animate() {
    requestAnimationFrame(animate);
    var dt = clock.getDelta();

    if (!reducedMotion && robotActive) {
      robot.position.x = robotBaseX + Math.sin(clock.elapsedTime * 0.35) * 1.6;
      robot.position.z = robotBaseZ + Math.cos(clock.elapsedTime * 0.35) * 0.5;
      robotRing.position.x = robot.position.x; robotRing.position.z = robot.position.z;
    }
    if (!reducedMotion && camActive) camLed.material.emissiveIntensity = 1.1 + Math.sin(clock.elapsedTime * 3.2) * 0.9;
    if (Math.abs(garagePanel.position.y - garageTargetY) > 0.001) {
      garagePanel.position.y += (garageTargetY - garagePanel.position.y) * Math.min(1, dt * 4);
    }

    if (!freeMode && playing) {
      elapsed += dt;
      if (elapsed >= TOTAL) { elapsed = TOTAL; playing = false; syncPlayIcon(); }
      var u = uFromElapsed(elapsed);
      camera.position.copy(posCurve.getPoint(u));
      camera.lookAt(lookCurve.getPoint(u));
      var frac = elapsed / TOTAL;
      fill.style.width = (frac * 100) + '%';
      roomLabel.textContent = labelFor(frac);
    } else if (freeMode) {
      orbit.update();
    }
    renderer.render(scene, camera);
  }

  function onResize() {
    camera.aspect = wrap.clientWidth / wrap.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  }
  window.addEventListener('resize', onResize);
  if (window.ResizeObserver) new ResizeObserver(onResize).observe(wrap);

  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      var loading = document.getElementById('iso3d-loading');
      loading.style.opacity = '0';
      setTimeout(function () { loading.style.display = 'none'; }, 450);
    });
  });

  animate();
};
