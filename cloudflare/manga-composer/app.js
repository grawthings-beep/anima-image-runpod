(() => {
  const canvas = document.getElementById("pageCanvas");
  const ctx = canvas.getContext("2d");

  const pagePresets = {
    portrait: { width: 1080, height: 1520 },
    square: { width: 1200, height: 1200 },
    webtoon: { width: 1080, height: 1920 }
  };

  const fontStack = '"Hiragino Sans", "Yu Gothic", Meiryo, "Noto Sans CJK JP", system-ui, sans-serif';
  const imageCache = new Map();
  let nextId = 1;

  const state = {
    page: { width: 1080, height: 1520, background: "#ffffff", backgroundImage: null },
    objects: [],
    selectedId: null,
    drag: null
  };

  const el = {
    pagePreset: document.getElementById("pagePreset"),
    pageSizeLabel: document.getElementById("pageSizeLabel"),
    layerList: document.getElementById("layerList"),
    selectionLabel: document.getElementById("selectionLabel"),
    xInput: document.getElementById("xInput"),
    yInput: document.getElementById("yInput"),
    wInput: document.getElementById("wInput"),
    hInput: document.getElementById("hInput"),
    textInput: document.getElementById("textInput"),
    presetInput: document.getElementById("presetInput"),
    fontSizeInput: document.getElementById("fontSizeInput"),
    rotationInput: document.getElementById("rotationInput"),
    strokeWidthInput: document.getElementById("strokeWidthInput"),
    verticalInput: document.getElementById("verticalInput"),
    fillInput: document.getElementById("fillInput"),
    strokeInput: document.getElementById("strokeInput"),
    bubbleFillInput: document.getElementById("bubbleFillInput"),
    bubbleStrokeInput: document.getElementById("bubbleStrokeInput"),
    fitInput: document.getElementById("fitInput"),
    imageSection: document.getElementById("imageSection"),
    textSection: document.getElementById("textSection"),
    bubbleSection: document.getElementById("bubbleSection"),
    backgroundInput: document.getElementById("backgroundInput"),
    panelImageInput: document.getElementById("panelImageInput"),
    importJsonInput: document.getElementById("importJsonInput")
  };

  const textPresets = {
    clean: { fontSize: 52, fill: "#151515", stroke: "#ffffff", strokeWidth: 5, rotation: 0, vertical: false, scaleX: 1, scaleY: 1, jitter: 0, echo: false },
    impact: { fontSize: 110, fill: "#111111", stroke: "#ffffff", strokeWidth: 13, rotation: -10, vertical: true, scaleX: 1.18, scaleY: 0.96, jitter: 0, echo: true },
    whisper: { fontSize: 32, fill: "#4e4a43", stroke: "#ffffff", strokeWidth: 3, rotation: 0, vertical: false, scaleX: 1, scaleY: 1, jitter: 0, echo: false },
    shake: { fontSize: 56, fill: "#181818", stroke: "#ffffff", strokeWidth: 6, rotation: -3, vertical: false, scaleX: 1, scaleY: 1, jitter: 2, echo: true },
    dark: { fontSize: 68, fill: "#ffffff", stroke: "#111111", strokeWidth: 8, rotation: 0, vertical: false, scaleX: 1, scaleY: 1, jitter: 0, echo: false }
  };

  function makeId(prefix) {
    const id = `${prefix}-${nextId}`;
    nextId += 1;
    return id;
  }

  function selectedObject() {
    return state.objects.find((object) => object.id === state.selectedId) || null;
  }

  function setSelected(id) {
    state.selectedId = id;
    updateInspector();
    render();
  }

  function addObject(object) {
    state.objects.push(object);
    setSelected(object.id);
  }

  function addPanel() {
    addObject({
      id: makeId("panel"),
      type: "panel",
      name: "コマ",
      x: 80,
      y: 90,
      w: 430,
      h: 520,
      fill: "#ffffff",
      stroke: "#141414",
      strokeWidth: 7,
      imageSrc: null,
      imageFit: "cover"
    });
  }

  function addBubble() {
    addObject({
      id: makeId("bubble"),
      type: "bubble",
      name: "吹き出し",
      x: 590,
      y: 110,
      w: 330,
      h: 210,
      tailX: 560,
      tailY: 350,
      fill: "#ffffff",
      stroke: "#151515",
      strokeWidth: 5,
      text: "ここにセリフ",
      fontSize: 38,
      textFill: "#151515",
      textStroke: "#ffffff",
      textStrokeWidth: 0,
      vertical: true,
      preset: "clean"
    });
  }

  function addDialogText() {
    addObject({
      id: makeId("text"),
      type: "text",
      name: "文字",
      x: 250,
      y: 700,
      w: 360,
      h: 140,
      text: "モノローグ",
      fontSize: 44,
      fill: "#151515",
      stroke: "#ffffff",
      strokeWidth: 4,
      rotation: 0,
      vertical: false,
      preset: "clean",
      scaleX: 1,
      scaleY: 1,
      jitter: 0,
      echo: false
    });
  }

  function addSfxText() {
    addObject({
      id: makeId("sfx"),
      type: "sfx",
      name: "効果音",
      x: 740,
      y: 650,
      w: 260,
      h: 420,
      text: "ドン",
      fontSize: 112,
      fill: "#111111",
      stroke: "#ffffff",
      strokeWidth: 13,
      rotation: -12,
      vertical: true,
      preset: "impact",
      scaleX: 1.16,
      scaleY: 0.96,
      jitter: 0,
      echo: true
    });
  }

  function loadImage(src) {
    if (!src) return null;
    if (imageCache.has(src)) return imageCache.get(src);
    const image = new Image();
    image.onload = render;
    image.src = src;
    imageCache.set(src, image);
    return image;
  }

  function drawBackground() {
    ctx.fillStyle = state.page.background || "#ffffff";
    ctx.fillRect(0, 0, state.page.width, state.page.height);
    if (!state.page.backgroundImage) return;
    const image = loadImage(state.page.backgroundImage);
    if (!image || !image.complete) return;
    drawImageFit(image, 0, 0, state.page.width, state.page.height, "cover");
  }

  function drawImageFit(image, x, y, w, h, fit) {
    const imageRatio = image.width / image.height;
    const boxRatio = w / h;
    let drawW = w;
    let drawH = h;
    if (fit === "contain" ? imageRatio > boxRatio : imageRatio < boxRatio) {
      drawW = w;
      drawH = w / imageRatio;
    } else {
      drawH = h;
      drawW = h * imageRatio;
    }
    const drawX = x + (w - drawW) / 2;
    const drawY = y + (h - drawH) / 2;
    ctx.drawImage(image, drawX, drawY, drawW, drawH);
  }

  function drawPanel(object) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(object.x, object.y, object.w, object.h);
    ctx.clip();
    ctx.fillStyle = object.fill || "#ffffff";
    ctx.fillRect(object.x, object.y, object.w, object.h);
    const image = loadImage(object.imageSrc);
    if (image && image.complete) {
      drawImageFit(image, object.x, object.y, object.w, object.h, object.imageFit || "cover");
    } else if (!object.imageSrc) {
      ctx.fillStyle = "#f3f0ea";
      ctx.fillRect(object.x, object.y, object.w, object.h);
      ctx.fillStyle = "#8b8376";
      ctx.font = `28px ${fontStack}`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("panel image", object.x + object.w / 2, object.y + object.h / 2);
    }
    ctx.restore();
    ctx.lineWidth = object.strokeWidth || 6;
    ctx.strokeStyle = object.stroke || "#111111";
    ctx.strokeRect(object.x, object.y, object.w, object.h);
  }

  function bubblePath(object) {
    const cx = object.x + object.w / 2;
    const cy = object.y + object.h / 2;
    const rx = object.w / 2;
    const ry = object.h / 2;
    const edgeX = object.x + object.w * 0.42;
    const edgeY = object.y + object.h * 0.84;
    ctx.beginPath();
    ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
    ctx.moveTo(edgeX - 18, edgeY - 8);
    ctx.quadraticCurveTo(object.tailX, object.tailY, edgeX + 34, edgeY - 20);
  }

  function drawBubble(object) {
    ctx.save();
    bubblePath(object);
    ctx.fillStyle = object.fill || "#ffffff";
    ctx.fill();
    ctx.lineWidth = object.strokeWidth || 4;
    ctx.strokeStyle = object.stroke || "#111111";
    ctx.stroke();
    ctx.restore();

    drawTextBlock({
      text: object.text || "",
      x: object.x + 34,
      y: object.y + 28,
      w: object.w - 68,
      h: object.h - 56,
      fontSize: object.fontSize || 36,
      fill: object.textFill || "#111111",
      stroke: object.textStroke || "#ffffff",
      strokeWidth: object.textStrokeWidth || 0,
      vertical: !!object.vertical,
      align: "center"
    });
  }

  function graphemes(text) {
    return Array.from(String(text || "").replace(/\r\n/g, "\n"));
  }

  function wrapLines(text, maxWidth, fontSize) {
    const lines = [];
    const hardLines = String(text || "").split("\n");
    ctx.font = `700 ${fontSize}px ${fontStack}`;
    for (const hardLine of hardLines) {
      let line = "";
      for (const char of graphemes(hardLine)) {
        const next = line + char;
        if (line && ctx.measureText(next).width > maxWidth) {
          lines.push(line);
          line = char;
        } else {
          line = next;
        }
      }
      lines.push(line);
    }
    return lines;
  }

  function drawTextStrokeFill(text, x, y, object) {
    if (object.strokeWidth > 0) {
      ctx.lineWidth = object.strokeWidth;
      ctx.strokeStyle = object.stroke;
      ctx.lineJoin = "round";
      ctx.strokeText(text, x, y);
    }
    ctx.fillStyle = object.fill;
    ctx.fillText(text, x, y);
  }

  function drawTextBlock(object) {
    const lineHeight = Math.round(object.fontSize * 1.18);
    ctx.save();
    ctx.font = `700 ${object.fontSize}px ${fontStack}`;
    ctx.textBaseline = "middle";
    ctx.textAlign = object.align || "center";

    if (object.vertical) {
      const chars = graphemes(object.text).filter((char) => char !== "\n");
      const perColumn = Math.max(1, Math.floor(object.h / lineHeight));
      const columns = Math.ceil(chars.length / perColumn);
      const totalWidth = columns * lineHeight;
      let x = object.x + object.w / 2 + totalWidth / 2 - lineHeight / 2;
      for (let column = 0; column < columns; column += 1) {
        const start = column * perColumn;
        const end = start + perColumn;
        const columnChars = chars.slice(start, end);
        const totalHeight = columnChars.length * lineHeight;
        let y = object.y + object.h / 2 - totalHeight / 2 + lineHeight / 2;
        for (const char of columnChars) {
          drawTextStrokeFill(char, x, y, object);
          y += lineHeight;
        }
        x -= lineHeight;
      }
    } else {
      const lines = wrapLines(object.text, object.w, object.fontSize);
      const totalHeight = lines.length * lineHeight;
      let y = object.y + object.h / 2 - totalHeight / 2 + lineHeight / 2;
      for (const line of lines) {
        const x = object.align === "left" ? object.x : object.x + object.w / 2;
        drawTextStrokeFill(line, x, y, object);
        y += lineHeight;
      }
    }
    ctx.restore();
  }

  function drawFreeText(object) {
    const jitter = object.jitter || 0;
    ctx.save();
    ctx.translate(object.x + object.w / 2, object.y + object.h / 2);
    ctx.rotate(((object.rotation || 0) * Math.PI) / 180);
    ctx.scale(object.scaleX || 1, object.scaleY || 1);
    const textBox = {
      text: object.text || "",
      x: -object.w / 2,
      y: -object.h / 2,
      w: object.w,
      h: object.h,
      fontSize: object.fontSize || 56,
      fill: object.fill || "#111111",
      stroke: object.stroke || "#ffffff",
      strokeWidth: object.strokeWidth || 0,
      vertical: !!object.vertical,
      align: "center"
    };

    if (object.echo) {
      ctx.globalAlpha = 0.18;
      drawTextBlock({ ...textBox, x: textBox.x + 12, y: textBox.y + 10 });
      ctx.globalAlpha = 1;
    }

    if (jitter > 0) {
      for (let i = 0; i < 3; i += 1) {
        ctx.globalAlpha = i === 2 ? 1 : 0.42;
        drawTextBlock({
          ...textBox,
          x: textBox.x + (i - 1) * jitter,
          y: textBox.y + (1 - i) * jitter
        });
      }
      ctx.globalAlpha = 1;
    } else {
      drawTextBlock(textBox);
    }
    ctx.restore();
  }

  function drawSelection(object) {
    if (!object) return;
    ctx.save();
    ctx.setLineDash([12, 8]);
    ctx.lineWidth = 3;
    ctx.strokeStyle = "#146c63";
    ctx.strokeRect(object.x, object.y, object.w, object.h);
    ctx.setLineDash([]);
    ctx.fillStyle = "#146c63";
    ctx.fillRect(object.x + object.w - 9, object.y + object.h - 9, 18, 18);
    if (object.type === "bubble") {
      ctx.beginPath();
      ctx.arc(object.tailX, object.tailY, 10, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function render() {
    canvas.width = state.page.width;
    canvas.height = state.page.height;
    drawBackground();
    for (const object of state.objects) {
      if (object.type === "panel") drawPanel(object);
      if (object.type === "bubble") drawBubble(object);
      if (object.type === "text" || object.type === "sfx") drawFreeText(object);
    }
    drawSelection(selectedObject());
    el.pageSizeLabel.textContent = `${state.page.width} x ${state.page.height}`;
    renderLayers();
  }

  function renderLayers() {
    el.layerList.innerHTML = "";
    state.objects.slice().reverse().forEach((object) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = `layer-row${object.id === state.selectedId ? " active" : ""}`;
      row.innerHTML = `<span>${object.name}</span><small>${object.type}</small>`;
      row.addEventListener("click", () => setSelected(object.id));
      el.layerList.appendChild(row);
    });
  }

  function updateInspector() {
    const object = selectedObject();
    const hasText = object && (object.type === "bubble" || object.type === "text" || object.type === "sfx");
    const isPanel = object && object.type === "panel";
    const isBubble = object && object.type === "bubble";

    el.selectionLabel.textContent = object ? `${object.name} / ${object.id}` : "未選択";
    el.imageSection.classList.toggle("hidden", !isPanel);
    el.textSection.classList.toggle("hidden", !hasText);
    el.bubbleSection.classList.toggle("hidden", !isBubble);

    for (const input of [el.xInput, el.yInput, el.wInput, el.hInput]) {
      input.disabled = !object;
    }
    if (!object) return;

    el.xInput.value = Math.round(object.x);
    el.yInput.value = Math.round(object.y);
    el.wInput.value = Math.round(object.w);
    el.hInput.value = Math.round(object.h);

    if (isPanel) {
      el.fitInput.value = object.imageFit || "cover";
    }

    if (hasText) {
      el.textInput.value = object.text || "";
      el.presetInput.value = object.preset || "clean";
      el.fontSizeInput.value = object.fontSize || 48;
      el.rotationInput.value = object.rotation || 0;
      el.strokeWidthInput.value = object.type === "bubble" ? object.textStrokeWidth || 0 : object.strokeWidth || 0;
      el.verticalInput.checked = !!object.vertical;
      el.fillInput.value = object.type === "bubble" ? object.textFill || "#151515" : object.fill || "#151515";
      el.strokeInput.value = object.type === "bubble" ? object.textStroke || "#ffffff" : object.stroke || "#ffffff";
    }

    if (isBubble) {
      el.bubbleFillInput.value = object.fill || "#ffffff";
      el.bubbleStrokeInput.value = object.stroke || "#151515";
    }
  }

  function updateSelectedProperty(key, value) {
    const object = selectedObject();
    if (!object) return;
    object[key] = value;
    render();
  }

  function applyTextPreset(name) {
    const object = selectedObject();
    if (!object || object.type === "panel") return;
    const preset = textPresets[name] || textPresets.clean;
    object.preset = name;
    object.fontSize = preset.fontSize;
    object.vertical = preset.vertical;
    if (object.type === "bubble") {
      object.textFill = preset.fill;
      object.textStroke = preset.stroke;
      object.textStrokeWidth = preset.strokeWidth;
    } else {
      object.fill = preset.fill;
      object.stroke = preset.stroke;
      object.strokeWidth = preset.strokeWidth;
      object.rotation = preset.rotation;
      object.scaleX = preset.scaleX;
      object.scaleY = preset.scaleY;
      object.jitter = preset.jitter;
      object.echo = preset.echo;
    }
    updateInspector();
    render();
  }

  function canvasPoint(event) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * state.page.width,
      y: ((event.clientY - rect.top) / rect.height) * state.page.height
    };
  }

  function hitTest(point) {
    for (let i = state.objects.length - 1; i >= 0; i -= 1) {
      const object = state.objects[i];
      if (object.type === "bubble") {
        const tailDistance = Math.hypot(point.x - object.tailX, point.y - object.tailY);
        if (tailDistance < 22) return { object, zone: "tail" };
      }
      const inBox = point.x >= object.x && point.x <= object.x + object.w && point.y >= object.y && point.y <= object.y + object.h;
      if (!inBox) continue;
      const nearResize = Math.abs(point.x - (object.x + object.w)) < 26 && Math.abs(point.y - (object.y + object.h)) < 26;
      return { object, zone: nearResize ? "resize" : "move" };
    }
    return null;
  }

  function onPointerDown(event) {
    const point = canvasPoint(event);
    const hit = hitTest(point);
    if (!hit) {
      setSelected(null);
      return;
    }
    setSelected(hit.object.id);
    state.drag = {
      mode: hit.zone,
      startX: point.x,
      startY: point.y,
      objectStart: { ...hit.object }
    };
    canvas.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event) {
    if (!state.drag) return;
    const object = selectedObject();
    if (!object) return;
    const point = canvasPoint(event);
    const dx = point.x - state.drag.startX;
    const dy = point.y - state.drag.startY;
    const start = state.drag.objectStart;

    if (state.drag.mode === "resize") {
      object.w = Math.max(40, start.w + dx);
      object.h = Math.max(40, start.h + dy);
    } else if (state.drag.mode === "tail") {
      object.tailX = start.tailX + dx;
      object.tailY = start.tailY + dy;
    } else {
      object.x = start.x + dx;
      object.y = start.y + dy;
      if (object.type === "bubble") {
        object.tailX = start.tailX + dx;
        object.tailY = start.tailY + dy;
      }
    }
    updateInspector();
    render();
  }

  function onPointerUp(event) {
    if (state.drag) {
      state.drag = null;
      canvas.releasePointerCapture(event.pointerId);
    }
  }

  function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
  }

  async function setBackgroundFromFile(file) {
    if (!file) return;
    state.page.backgroundImage = await readFileAsDataUrl(file);
    render();
  }

  async function setPanelImageFromFile(file) {
    const object = selectedObject();
    if (!file || !object || object.type !== "panel") return;
    object.imageSrc = await readFileAsDataUrl(file);
    render();
  }

  function downloadBlob(blob, name) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = name;
    link.click();
    URL.revokeObjectURL(url);
  }

  function downloadText(text, name, type) {
    downloadBlob(new Blob([text], { type }), name);
  }

  function exportPng() {
    render();
    canvas.toBlob((blob) => {
      if (blob) downloadBlob(blob, `manga-page-${Date.now()}.png`);
    }, "image/png");
  }

  function saveJson() {
    const payload = {
      version: 1,
      page: state.page,
      objects: state.objects
    };
    downloadText(JSON.stringify(payload, null, 2), `manga-layout-${Date.now()}.json`, "application/json");
  }

  async function importJson(file) {
    if (!file) return;
    const text = await file.text();
    const payload = JSON.parse(text);
    state.page = payload.page || state.page;
    state.objects = Array.isArray(payload.objects) ? payload.objects : [];
    state.selectedId = null;
    nextId = state.objects.reduce((max, object) => {
      const number = Number(String(object.id).split("-").pop());
      return Number.isFinite(number) ? Math.max(max, number + 1) : max;
    }, 1);
    updateInspector();
    render();
  }

  function moveSelected(delta) {
    const index = state.objects.findIndex((object) => object.id === state.selectedId);
    if (index < 0) return;
    const nextIndex = index + delta;
    if (nextIndex < 0 || nextIndex >= state.objects.length) return;
    const [object] = state.objects.splice(index, 1);
    state.objects.splice(nextIndex, 0, object);
    render();
  }

  function deleteSelected() {
    if (!state.selectedId) return;
    state.objects = state.objects.filter((object) => object.id !== state.selectedId);
    state.selectedId = null;
    updateInspector();
    render();
  }

  function setPagePreset(name) {
    const preset = pagePresets[name] || pagePresets.portrait;
    state.page.width = preset.width;
    state.page.height = preset.height;
    render();
  }

  function blankPage() {
    state.page = { width: 1080, height: 1520, background: "#ffffff", backgroundImage: null };
    state.objects = [];
    state.selectedId = null;
    nextId = 1;
    el.pagePreset.value = "portrait";
    updateInspector();
    render();
  }

  function demoPage() {
    blankPage();
    addObject({ id: makeId("panel"), type: "panel", name: "コマ 1", x: 58, y: 70, w: 458, h: 560, fill: "#ffffff", stroke: "#141414", strokeWidth: 7, imageSrc: null, imageFit: "cover" });
    addObject({ id: makeId("panel"), type: "panel", name: "コマ 2", x: 554, y: 70, w: 468, h: 355, fill: "#ffffff", stroke: "#141414", strokeWidth: 7, imageSrc: null, imageFit: "cover" });
    addObject({ id: makeId("panel"), type: "panel", name: "コマ 3", x: 554, y: 455, w: 468, h: 520, fill: "#ffffff", stroke: "#141414", strokeWidth: 7, imageSrc: null, imageFit: "cover" });
    addObject({ id: makeId("panel"), type: "panel", name: "コマ 4", x: 58, y: 665, w: 458, h: 785, fill: "#ffffff", stroke: "#141414", strokeWidth: 7, imageSrc: null, imageFit: "cover" });
    addObject({ id: makeId("bubble"), type: "bubble", name: "吹き出し", x: 626, y: 118, w: 310, h: 184, tailX: 596, tailY: 360, fill: "#ffffff", stroke: "#151515", strokeWidth: 5, text: "ここに\nセリフ", fontSize: 36, textFill: "#151515", textStroke: "#ffffff", textStrokeWidth: 0, vertical: true, preset: "clean" });
    addObject({ id: makeId("sfx"), type: "sfx", name: "効果音", x: 692, y: 600, w: 260, h: 360, text: "ドン", fontSize: 116, fill: "#111111", stroke: "#ffffff", strokeWidth: 14, rotation: -12, vertical: true, preset: "impact", scaleX: 1.16, scaleY: 0.96, jitter: 0, echo: true });
    setSelected(state.objects[state.objects.length - 1].id);
  }

  function bindEvents() {
    document.getElementById("addPanelButton").addEventListener("click", addPanel);
    document.getElementById("addBubbleButton").addEventListener("click", addBubble);
    document.getElementById("addDialogButton").addEventListener("click", addDialogText);
    document.getElementById("addSfxButton").addEventListener("click", addSfxText);
    document.getElementById("exportButton").addEventListener("click", exportPng);
    document.getElementById("saveJsonButton").addEventListener("click", saveJson);
    document.getElementById("moveUpButton").addEventListener("click", () => moveSelected(1));
    document.getElementById("moveDownButton").addEventListener("click", () => moveSelected(-1));
    document.getElementById("deleteButton").addEventListener("click", deleteSelected);
    document.getElementById("demoButton").addEventListener("click", demoPage);
    document.getElementById("blankButton").addEventListener("click", blankPage);
    document.getElementById("clearBackgroundButton").addEventListener("click", () => {
      state.page.backgroundImage = null;
      render();
    });

    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerUp);

    el.pagePreset.addEventListener("change", (event) => setPagePreset(event.target.value));
    el.backgroundInput.addEventListener("change", (event) => setBackgroundFromFile(event.target.files[0]));
    el.panelImageInput.addEventListener("change", (event) => setPanelImageFromFile(event.target.files[0]));
    el.importJsonInput.addEventListener("change", (event) => importJson(event.target.files[0]));

    el.xInput.addEventListener("input", (event) => updateSelectedProperty("x", Number(event.target.value)));
    el.yInput.addEventListener("input", (event) => updateSelectedProperty("y", Number(event.target.value)));
    el.wInput.addEventListener("input", (event) => updateSelectedProperty("w", Math.max(20, Number(event.target.value))));
    el.hInput.addEventListener("input", (event) => updateSelectedProperty("h", Math.max(20, Number(event.target.value))));
    el.fitInput.addEventListener("change", (event) => updateSelectedProperty("imageFit", event.target.value));
    el.textInput.addEventListener("input", (event) => updateSelectedProperty("text", event.target.value));
    el.presetInput.addEventListener("change", (event) => applyTextPreset(event.target.value));
    el.fontSizeInput.addEventListener("input", (event) => updateSelectedProperty("fontSize", Number(event.target.value)));
    el.rotationInput.addEventListener("input", (event) => updateSelectedProperty("rotation", Number(event.target.value)));
    el.strokeWidthInput.addEventListener("input", (event) => {
      const object = selectedObject();
      if (!object) return;
      if (object.type === "bubble") object.textStrokeWidth = Number(event.target.value);
      else object.strokeWidth = Number(event.target.value);
      render();
    });
    el.verticalInput.addEventListener("change", (event) => updateSelectedProperty("vertical", event.target.checked));
    el.fillInput.addEventListener("input", (event) => {
      const object = selectedObject();
      if (!object) return;
      if (object.type === "bubble") object.textFill = event.target.value;
      else object.fill = event.target.value;
      render();
    });
    el.strokeInput.addEventListener("input", (event) => {
      const object = selectedObject();
      if (!object) return;
      if (object.type === "bubble") object.textStroke = event.target.value;
      else object.stroke = event.target.value;
      render();
    });
    el.bubbleFillInput.addEventListener("input", (event) => updateSelectedProperty("fill", event.target.value));
    el.bubbleStrokeInput.addEventListener("input", (event) => updateSelectedProperty("stroke", event.target.value));

    window.addEventListener("keydown", (event) => {
      if (event.key === "Delete" || event.key === "Backspace") {
        const active = document.activeElement;
        if (active && ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName)) return;
        event.preventDefault();
        deleteSelected();
      }
    });
  }

  bindEvents();
  demoPage();
})();
