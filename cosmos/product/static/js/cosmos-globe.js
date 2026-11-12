/* COSMOS-AI — interactive globe renderer.
 *
 * Hand-written WebGL. No library, no build step, no network: the console keeps working offline,
 * which is why Three.js is not used here (it would have to be downloaded and vendored).
 *
 * What this file does NOT do, deliberately:
 *   - it never computes a position, a velocity, a sub-satellite point or a ground track. Every
 *     coordinate it draws arrives from GET /api/globe/objects, where cosmos/product/geometry.py
 *     derives it from the archived perigee, apogee and inclination and labels the orbit
 *     orientation as a non-physical screen layout;
 *   - it never animates an object along its orbit, because that would assert propagation. The only
 *     motion is the camera, and the only pulse is the selection marker.
 *
 * Frame: geocentric, +z along the Earth's rotation axis, 1 unit = 1 Earth radius, matching the API.
 */
(function (global) {
  'use strict';

  // ----------------------------------------------------------------- small matrix helpers
  function mat4() { return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]); }

  function perspective(out, fovyRad, aspect, near, far) {
    var f = 1.0 / Math.tan(fovyRad / 2), nf = 1 / (near - far);
    out[0]=f/aspect; out[1]=0; out[2]=0; out[3]=0;
    out[4]=0; out[5]=f; out[6]=0; out[7]=0;
    out[8]=0; out[9]=0; out[10]=(far+near)*nf; out[11]=-1;
    out[12]=0; out[13]=0; out[14]=2*far*near*nf; out[15]=0;
    return out;
  }

  function lookAt(out, eye, centre, up) {
    var zx=eye[0]-centre[0], zy=eye[1]-centre[1], zz=eye[2]-centre[2];
    var zl=Math.hypot(zx,zy,zz) || 1; zx/=zl; zy/=zl; zz/=zl;
    var xx=up[1]*zz-up[2]*zy, xy=up[2]*zx-up[0]*zz, xz=up[0]*zy-up[1]*zx;
    var xl=Math.hypot(xx,xy,xz) || 1; xx/=xl; xy/=xl; xz/=xl;
    var yx=zy*xz-zz*xy, yy=zz*xx-zx*xz, yz=zx*xy-zy*xx;
    out[0]=xx; out[1]=yx; out[2]=zx; out[3]=0;
    out[4]=xy; out[5]=yy; out[6]=zy; out[7]=0;
    out[8]=xz; out[9]=yz; out[10]=zz; out[11]=0;
    out[12]=-(xx*eye[0]+xy*eye[1]+xz*eye[2]);
    out[13]=-(yx*eye[0]+yy*eye[1]+yz*eye[2]);
    out[14]=-(zx*eye[0]+zy*eye[1]+zz*eye[2]);
    out[15]=1;
    return out;
  }

  function multiply(out, a, b) {
    for (var i = 0; i < 4; i++) {
      var ai0=a[i], ai1=a[i+4], ai2=a[i+8], ai3=a[i+12];
      for (var j = 0; j < 4; j++) {
        out[i+j*4] = ai0*b[j*4] + ai1*b[j*4+1] + ai2*b[j*4+2] + ai3*b[j*4+3];
      }
    }
    return out;
  }

  function transform(m, p) {
    return [
      m[0]*p[0] + m[4]*p[1] + m[8]*p[2] + m[12],
      m[1]*p[0] + m[5]*p[1] + m[9]*p[2] + m[13],
      m[2]*p[0] + m[6]*p[1] + m[10]*p[2] + m[14],
      m[3]*p[0] + m[7]*p[1] + m[11]*p[2] + m[15]
    ];
  }

  // ----------------------------------------------------------------- shaders
  var EARTH_VS = [
    'attribute vec3 aPos; attribute vec2 aUV;',
    'uniform mat4 uMVP; varying vec2 vUV; varying vec3 vN;',
    'void main(){ vUV = aUV; vN = normalize(aPos); gl_Position = uMVP * vec4(aPos, 1.0); }'
  ].join('\n');

  // Lighting is a soft term about the view direction, not a sun: a day/night terminator would
  // imply an epoch the archive does not provide.
  var EARTH_FS = [
    'precision mediump float;',
    'uniform sampler2D uTex; uniform vec3 uView; uniform float uHasTex;',
    'varying vec2 vUV; varying vec3 vN;',
    'void main(){',
    '  vec3 base = uHasTex > 0.5 ? texture2D(uTex, vUV).rgb : vec3(0.08, 0.16, 0.27);',
    '  float facing = max(dot(normalize(vN), normalize(uView)), 0.0);',
    '  float shade = 0.42 + 0.58 * pow(facing, 0.65);',
    '  float rim = pow(1.0 - facing, 3.0);',
    '  vec3 c = base * shade + vec3(0.11, 0.42, 0.62) * rim * 0.55;',
    '  gl_FragColor = vec4(c, 1.0);',
    '}'
  ].join('\n');

  var ATMO_VS = EARTH_VS;
  var ATMO_FS = [
    'precision mediump float;',
    'uniform vec3 uView; varying vec3 vN; varying vec2 vUV;',
    'void main(){',
    '  float facing = max(dot(normalize(vN), normalize(uView)), 0.0);',
    '  float glow = pow(1.0 - facing, 2.4);',
    '  gl_FragColor = vec4(vec3(0.24, 0.62, 0.95) * glow, glow * 0.55);',
    '}'
  ].join('\n');

  var LINE_VS = [
    'attribute vec3 aPos; attribute vec3 aColor; attribute float aIndex;',
    'uniform mat4 uMVP; uniform float uSelected;',
    'varying vec4 vColor;',
    'void main(){',
    '  float sel = step(abs(aIndex - uSelected), 0.5);',
    '  float anySel = step(-0.5, uSelected);',
    '  float a = mix(mix(0.40, 0.13, anySel), 0.95, sel);',
    '  vColor = vec4(mix(aColor, vec3(1.0), 0.40 * sel), a);',
    '  gl_Position = uMVP * vec4(aPos, 1.0);',
    '}'
  ].join('\n');

  var LINE_FS = [
    'precision mediump float; varying vec4 vColor;',
    'void main(){ gl_FragColor = vColor; }'
  ].join('\n');

  var POINT_VS = [
    'attribute vec3 aPos; attribute vec3 aColor; attribute float aIndex;',
    'uniform mat4 uMVP; uniform float uSelected; uniform float uPulse; uniform float uScale;',
    'varying vec4 vColor;',
    'void main(){',
    '  float sel = step(abs(aIndex - uSelected), 0.5);',
    '  float anySel = step(-0.5, uSelected);',
    '  vColor = vec4(mix(aColor, vec3(1.0), 0.5 * sel), mix(mix(0.9, 0.5, anySel), 1.0, sel));',
    '  gl_Position = uMVP * vec4(aPos, 1.0);',
    '  gl_PointSize = uScale * mix(5.5, 12.0 + 2.5 * uPulse, sel);',
    '}'
  ].join('\n');

  var POINT_FS = [
    'precision mediump float; varying vec4 vColor;',
    'void main(){',
    '  vec2 d = gl_PointCoord - vec2(0.5);',
    '  float r = length(d);',
    '  if (r > 0.5) discard;',
    '  float core = smoothstep(0.5, 0.12, r);',
    '  gl_FragColor = vec4(vColor.rgb, vColor.a * core);',
    '}'
  ].join('\n');

  // ----------------------------------------------------------------- gl plumbing
  function compile(gl, type, src) {
    var sh = gl.createShader(type);
    gl.shaderSource(sh, src);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      var log = gl.getShaderInfoLog(sh);
      gl.deleteShader(sh);
      throw new Error('shader compile failed: ' + log);
    }
    return sh;
  }

  function program(gl, vsSrc, fsSrc) {
    var p = gl.createProgram();
    gl.attachShader(p, compile(gl, gl.VERTEX_SHADER, vsSrc));
    gl.attachShader(p, compile(gl, gl.FRAGMENT_SHADER, fsSrc));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
      throw new Error('program link failed: ' + gl.getProgramInfoLog(p));
    }
    return p;
  }

  function buffer(gl, data, target) {
    var b = gl.createBuffer();
    gl.bindBuffer(target || gl.ARRAY_BUFFER, b);
    gl.bufferData(target || gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    return b;
  }

  function isPowerOfTwo(value) { return (value & (value - 1)) === 0 && value > 0; }

  function sphere(segments, rings, radius) {
    var pos = [], uv = [], idx = [];
    for (var r = 0; r <= rings; r++) {
      var v = r / rings, lat = (0.5 - v) * Math.PI;       // +90 at v=0, matching the texture
      var cl = Math.cos(lat), sl = Math.sin(lat);
      for (var s = 0; s <= segments; s++) {
        var u = s / segments, lon = (u - 0.5) * 2 * Math.PI;  // -180 at u=0
        pos.push(radius * cl * Math.cos(lon), radius * cl * Math.sin(lon), radius * sl);
        uv.push(u, v);
      }
    }
    var row = segments + 1;
    for (r = 0; r < rings; r++) {
      for (s = 0; s < segments; s++) {
        var a = r * row + s, b = a + row;
        idx.push(a, b, a + 1, a + 1, b, b + 1);
      }
    }
    return { pos: new Float32Array(pos), uv: new Float32Array(uv), idx: new Uint16Array(idx) };
  }

  // Class colour: meaning is carried by the legend, not by taste. Cyan payload, violet rocket
  // body, slate component, amber fragment; unknown stays neutral.
  var CLASS_COLOUR = {
    P: [0.31, 0.78, 0.94], R: [0.65, 0.49, 0.93], C: [0.55, 0.65, 0.78], D: [0.90, 0.68, 0.33]
  };

  function colourFor(obj) {
    var c = CLASS_COLOUR[String(obj.object_class || '').trim().toUpperCase()];
    return c || [0.58, 0.68, 0.80];
  }

  // ----------------------------------------------------------------- public factory
  function create(canvas, options) {
    options = options || {};
    var gl = null;
    try {
      var attrs = { antialias: true, alpha: false, depth: true, preserveDrawingBuffer: true };
      gl = canvas.getContext('webgl', attrs) || canvas.getContext('experimental-webgl', attrs);
    } catch (e) { gl = null; }
    if (!gl) { return null; }

    var api = {};
    var progEarth, progAtmo, progLine, progPoint;
    try {
      progEarth = program(gl, EARTH_VS, EARTH_FS);
      progAtmo = program(gl, ATMO_VS, ATMO_FS);
      progLine = program(gl, LINE_VS, LINE_FS);
      progPoint = program(gl, POINT_VS, POINT_FS);
    } catch (err) {
      if (options.onError) { options.onError(err); }
      return null;
    }

    var earth = sphere(72, 36, 1.0);
    var atmo = sphere(48, 24, 1.035);
    var bufs = {
      earthPos: buffer(gl, earth.pos), earthUV: buffer(gl, earth.uv),
      earthIdx: buffer(gl, earth.idx, gl.ELEMENT_ARRAY_BUFFER),
      atmoPos: buffer(gl, atmo.pos), atmoUV: buffer(gl, atmo.uv),
      atmoIdx: buffer(gl, atmo.idx, gl.ELEMENT_ARRAY_BUFFER),
      linePos: gl.createBuffer(), lineColour: gl.createBuffer(), lineIndex: gl.createBuffer(),
      pointPos: gl.createBuffer(), pointColour: gl.createBuffer(), pointIndex: gl.createBuffer()
    };

    var texture = gl.createTexture();
    var hasTexture = 0;
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE,
                  new Uint8Array([20, 41, 66, 255]));
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);

    if (options.textureUrl) {
      var img = new Image();
      img.onload = function () {
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
        // WebGL 1 rejects mipmaps and REPEAT on a non-power-of-two texture (it then samples black),
        // so the parameters follow the image that actually arrived.
        var pot = isPowerOfTwo(img.width) && isPowerOfTwo(img.height);
        if (pot) {
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
          gl.generateMipmap(gl.TEXTURE_2D);
        } else {
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        }
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        hasTexture = 1;
      };
      img.onerror = function () { hasTexture = 0; };   // the flat sphere colour stands in
      img.src = options.textureUrl;
    }

    // scene state
    var objects = [];
    var markers = null, markerColour = null, markerIndex = null, markerCount = 0;
    var lineCount = 0;
    var selected = -1;
    var hovered = -1;
    var byNorad = {};

    // camera
    var cam = { az: -1.05, el: 0.42, dist: 3.4 };
    var home = { az: -1.05, el: 0.42, dist: 3.4 };
    var autoRotate = options.autoRotate !== false;
    var dragging = false, lastX = 0, lastY = 0, moved = 0;
    var mvp = mat4(), proj = mat4(), view = mat4();
    var width = 1, height = 1, dpr = 1;
    var running = true, frame = 0;

    function eye() {
      var ce = Math.cos(cam.el), se = Math.sin(cam.el);
      return [cam.dist * ce * Math.cos(cam.az), cam.dist * ce * Math.sin(cam.az), cam.dist * se];
    }

    function resize() {
      dpr = Math.min(global.devicePixelRatio || 1, 2);
      var w = Math.max(1, canvas.clientWidth), h = Math.max(1, canvas.clientHeight);
      width = w; height = h;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      gl.viewport(0, 0, canvas.width, canvas.height);
    }

    api.setScene = function (payload) {
      objects = (payload && payload.objects) || [];
      byNorad = {};
      var linePos = [], lineCol = [], lineIdx = [];
      var mPos = [], mCol = [], mIdx = [];
      objects.forEach(function (obj, i) {
        byNorad[obj.norad] = i;
        var c = colourFor(obj);
        var p = obj.orbit_earth_radii || [];
        for (var k = 0; k + 5 < p.length; k += 3) {           // one GL_LINES pair per segment
          linePos.push(p[k], p[k+1], p[k+2], p[k+3], p[k+4], p[k+5]);
          lineCol.push(c[0], c[1], c[2], c[0], c[1], c[2]);
          lineIdx.push(i, i);
        }
        var m = obj.marker_earth_radii;
        if (m && m.length === 3) {
          mPos.push(m[0], m[1], m[2]); mCol.push(c[0], c[1], c[2]); mIdx.push(i);
        }
      });
      lineCount = lineIdx.length;
      markerCount = mIdx.length;
      markers = new Float32Array(mPos); markerColour = new Float32Array(mCol);
      markerIndex = new Float32Array(mIdx);
      gl.bindBuffer(gl.ARRAY_BUFFER, bufs.linePos);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(linePos), gl.STATIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, bufs.lineColour);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(lineCol), gl.STATIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, bufs.lineIndex);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(lineIdx), gl.STATIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, bufs.pointPos);
      gl.bufferData(gl.ARRAY_BUFFER, markers, gl.STATIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, bufs.pointColour);
      gl.bufferData(gl.ARRAY_BUFFER, markerColour, gl.STATIC_DRAW);
      gl.bindBuffer(gl.ARRAY_BUFFER, bufs.pointIndex);
      gl.bufferData(gl.ARRAY_BUFFER, markerIndex, gl.STATIC_DRAW);
      if (selected >= 0 && !objects[selected]) { selected = -1; }
      return objects.length;
    };

    api.select = function (norad) {
      var i = (norad === null || norad === undefined) ? -1 : byNorad[norad];
      selected = (i === undefined) ? -1 : i;
      return selected >= 0 ? objects[selected] : null;
    };
    api.selected = function () { return selected >= 0 ? objects[selected] : null; };
    api.resetCamera = function () { cam.az = home.az; cam.el = home.el; cam.dist = home.dist; };
    api.setAutoRotate = function (on) { autoRotate = !!on; return autoRotate; };
    api.autoRotate = function () { return autoRotate; };
    api.zoom = function (factor) {
      cam.dist = Math.min(40, Math.max(1.35, cam.dist * factor));
    };
    api.objectCount = function () { return objects.length; };

    // Screen position of a world point, and whether the Earth hides it.
    function project(p) {
      var clip = transform(mvp, p);
      if (clip[3] <= 0) { return null; }
      var e = eye();
      var dx = p[0]-e[0], dy = p[1]-e[1], dz = p[2]-e[2];
      var a = dx*dx + dy*dy + dz*dz;
      var b = 2*(e[0]*dx + e[1]*dy + e[2]*dz);
      var c = e[0]*e[0] + e[1]*e[1] + e[2]*e[2] - 1.0;
      var disc = b*b - 4*a*c;
      var occluded = false;
      if (disc > 0) {
        var sq = Math.sqrt(disc);
        var t1 = (-b - sq) / (2*a), t2 = (-b + sq) / (2*a);
        occluded = (t1 > 1e-4 && t1 < 1) || (t2 > 1e-4 && t2 < 1);
      }
      return {
        x: (clip[0] / clip[3] * 0.5 + 0.5) * width,
        y: (1 - (clip[1] / clip[3] * 0.5 + 0.5)) * height,
        occluded: occluded
      };
    }

    api.screenPosition = function (norad) {
      var i = byNorad[norad];
      if (i === undefined || !markers) { return null; }
      return project([markers[i*3], markers[i*3+1], markers[i*3+2]]);
    };

    function pick(px, py) {
      if (!markers) { return -1; }
      var best = -1, bestD = 18;
      for (var i = 0; i < markerCount; i++) {
        var s = project([markers[i*3], markers[i*3+1], markers[i*3+2]]);
        if (!s || s.occluded) { continue; }
        var d = Math.hypot(s.x - px, s.y - py);
        if (d < bestD) { bestD = d; best = i; }
      }
      return best;
    }

    // ----------------------------------------------------------------- interaction
    function onDown(ev) {
      dragging = true; moved = 0;
      lastX = ev.clientX; lastY = ev.clientY;
      canvas.setPointerCapture && ev.pointerId !== undefined && canvas.setPointerCapture(ev.pointerId);
    }

    function onMove(ev) {
      var rect = canvas.getBoundingClientRect();
      var px = ev.clientX - rect.left, py = ev.clientY - rect.top;
      if (dragging) {
        var dx = ev.clientX - lastX, dy = ev.clientY - lastY;
        moved += Math.abs(dx) + Math.abs(dy);
        lastX = ev.clientX; lastY = ev.clientY;
        cam.az -= dx * 0.006;
        cam.el = Math.max(-1.48, Math.min(1.48, cam.el + dy * 0.005));
        return;
      }
      var i = pick(px, py);
      if (i !== hovered) {
        hovered = i;
        canvas.style.cursor = i >= 0 ? 'pointer' : 'grab';
        if (options.onHover) { options.onHover(i >= 0 ? objects[i] : null); }
      }
    }

    function onUp(ev) {
      if (dragging && moved < 6) {
        var rect = canvas.getBoundingClientRect();
        var i = pick(ev.clientX - rect.left, ev.clientY - rect.top);
        if (i >= 0) {
          selected = i;
          if (options.onSelect) { options.onSelect(objects[i]); }
        }
      }
      dragging = false;
    }

    function onWheel(ev) {
      ev.preventDefault();
      api.zoom(Math.exp((ev.deltaY || 0) * 0.0012));
    }

    canvas.addEventListener('pointerdown', onDown);
    canvas.addEventListener('pointermove', onMove);
    canvas.addEventListener('pointerup', onUp);
    canvas.addEventListener('pointerleave', function () {
      dragging = false;
      if (hovered !== -1) { hovered = -1; if (options.onHover) { options.onHover(null); } }
    });
    canvas.addEventListener('wheel', onWheel, { passive: false });
    canvas.addEventListener('dblclick', api.resetCamera);
    canvas.style.cursor = 'grab';
    canvas.setAttribute('tabindex', '0');
    canvas.addEventListener('keydown', function (ev) {
      var step = 0.08;
      if (ev.key === 'ArrowLeft') { cam.az -= step; }
      else if (ev.key === 'ArrowRight') { cam.az += step; }
      else if (ev.key === 'ArrowUp') { cam.el = Math.min(1.48, cam.el + step); }
      else if (ev.key === 'ArrowDown') { cam.el = Math.max(-1.48, cam.el - step); }
      else if (ev.key === '+' || ev.key === '=') { api.zoom(0.9); }
      else if (ev.key === '-') { api.zoom(1.1); }
      else if (ev.key === 'r' || ev.key === 'R') { api.resetCamera(); }
      else { return; }
      ev.preventDefault();
    });

    // ----------------------------------------------------------------- draw
    function bindAttrib(prog, name, buf, size) {
      var loc = gl.getAttribLocation(prog, name);
      if (loc < 0) { return; }
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
    }

    function draw(time) {
      if (!running) { return; }
      if (canvas.clientWidth !== width || canvas.clientHeight !== height) { resize(); }
      if (autoRotate && !dragging) { cam.az += 0.0011; }

      var e = eye();
      perspective(proj, 42 * Math.PI / 180, Math.max(0.2, width / Math.max(1, height)), 0.05, 200);
      lookAt(view, e, [0, 0, 0], [0, 0, 1]);
      multiply(mvp, proj, view);

      gl.clearColor(0.031, 0.055, 0.094, 1.0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST);
      gl.depthFunc(gl.LEQUAL);
      gl.disable(gl.BLEND);

      // Earth
      gl.useProgram(progEarth);
      bindAttrib(progEarth, 'aPos', bufs.earthPos, 3);
      bindAttrib(progEarth, 'aUV', bufs.earthUV, 2);
      gl.uniformMatrix4fv(gl.getUniformLocation(progEarth, 'uMVP'), false, mvp);
      gl.uniform3fv(gl.getUniformLocation(progEarth, 'uView'), new Float32Array(e));
      gl.uniform1f(gl.getUniformLocation(progEarth, 'uHasTex'), hasTexture);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.uniform1i(gl.getUniformLocation(progEarth, 'uTex'), 0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, bufs.earthIdx);
      gl.drawElements(gl.TRIANGLES, earth.idx.length, gl.UNSIGNED_SHORT, 0);

      // Atmosphere: additive shell, depth tested but not written.
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE);
      gl.depthMask(false);
      gl.useProgram(progAtmo);
      bindAttrib(progAtmo, 'aPos', bufs.atmoPos, 3);
      bindAttrib(progAtmo, 'aUV', bufs.atmoUV, 2);
      gl.uniformMatrix4fv(gl.getUniformLocation(progAtmo, 'uMVP'), false, mvp);
      gl.uniform3fv(gl.getUniformLocation(progAtmo, 'uView'), new Float32Array(e));
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, bufs.atmoIdx);
      gl.drawElements(gl.TRIANGLES, atmo.idx.length, gl.UNSIGNED_SHORT, 0);

      // Orbits and markers
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      if (lineCount > 0) {
        gl.useProgram(progLine);
        bindAttrib(progLine, 'aPos', bufs.linePos, 3);
        bindAttrib(progLine, 'aColor', bufs.lineColour, 3);
        bindAttrib(progLine, 'aIndex', bufs.lineIndex, 1);
        gl.uniformMatrix4fv(gl.getUniformLocation(progLine, 'uMVP'), false, mvp);
        gl.uniform1f(gl.getUniformLocation(progLine, 'uSelected'), selected);
        gl.drawArrays(gl.LINES, 0, lineCount);
      }
      if (markerCount > 0) {
        gl.useProgram(progPoint);
        bindAttrib(progPoint, 'aPos', bufs.pointPos, 3);
        bindAttrib(progPoint, 'aColor', bufs.pointColour, 3);
        bindAttrib(progPoint, 'aIndex', bufs.pointIndex, 1);
        gl.uniformMatrix4fv(gl.getUniformLocation(progPoint, 'uMVP'), false, mvp);
        gl.uniform1f(gl.getUniformLocation(progPoint, 'uSelected'), selected);
        gl.uniform1f(gl.getUniformLocation(progPoint, 'uPulse'),
                     0.5 + 0.5 * Math.sin((time || 0) * 0.0032));
        gl.uniform1f(gl.getUniformLocation(progPoint, 'uScale'), dpr);
        gl.drawArrays(gl.POINTS, 0, markerCount);
      }
      gl.depthMask(true);

      if (options.onFrame) { options.onFrame(frame++); }
      global.requestAnimationFrame(draw);
    }

    api.destroy = function () { running = false; };
    api.info = function () {
      var dbg = gl.getExtension('WEBGL_debug_renderer_info');
      return {
        renderer: 'webgl',
        version: gl.getParameter(gl.VERSION),
        vendor: gl.getParameter(gl.VENDOR),
        hardware: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
        textureLoaded: hasTexture === 1,
        objects: objects.length,
        orbitVertices: lineCount,
        markers: markerCount,
        frames: frame,
        running: running,
        canvasPx: [canvas.width, canvas.height],
        cssPx: [width, height],
        camera: { azimuth: cam.az, elevation: cam.el, distance: cam.dist },
        autoRotate: autoRotate,
        selected: selected >= 0 && objects[selected] ? objects[selected].norad : null
      };
    };

    canvas.addEventListener('webglcontextlost', function (ev) {
      ev.preventDefault(); running = false;
      if (options.onError) { options.onError(new Error('WebGL context lost')); }
    });

    resize();
    global.requestAnimationFrame(draw);
    return api;
  }

  global.CosmosGlobe = { create: create, CLASS_COLOUR: CLASS_COLOUR };
})(window);
