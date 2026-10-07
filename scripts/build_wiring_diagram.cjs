#!/usr/bin/env node
// 板卡标签依原厂 V1.1 图；触点按客户指定的 2–3 常开接线、4 留空绘制。
const { createCanvas, loadImage, GlobalFonts } = require(process.env.MANUAL_CANVAS_MODULE || '@napi-rs/canvas');
const { writeFileSync } = require('node:fs');
const { resolve } = require('node:path');

(async () => {
  let assets = resolve(__dirname, '../docs/客户使用说明书2插图');
  GlobalFonts.registerFromPath('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'Manual');
  let canvas = createCanvas(2000, 2200);
  let ctx = canvas.getContext('2d');
  ctx.fillStyle = 'white';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = ctx.fillStyle = 'black';
  ctx.lineWidth = 3;
  let segments = [];
  let junctions = [];
  function text(value, x, y, size = 44, align = 'center') {
    ctx.font = `${size}px Manual`;
    ctx.textAlign = align;
    ctx.textBaseline = 'middle';
    ctx.fillStyle = 'black';
    ctx.fillText(value, x, y);
  }
  function line(points, dashed = false) {
    if (!dashed) {
      for (let i = 1; i < points.length; i++) segments.push([points[i - 1], points[i]]);
    }
    ctx.setLineDash(dashed ? [10, 8] : []);
    ctx.beginPath();
    points.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
    ctx.stroke();
    ctx.setLineDash([]);
  }
  function dot(x, y) {
    junctions.push([x, y]);
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fill();
  }
  function box(x, y, w, h, title) {
    ctx.strokeRect(x, y, w, h);
    if (title) text(title, x + w / 2, y + 36);
  }
  function tag(value, x, y, size = 36) {
    ctx.font = `${size}px Manual`;
    let width = ctx.measureText(value).width + 10;
    ctx.fillStyle = 'white';
    ctx.fillRect(x - width / 2, y - size / 2, width, size);
    text(value, x, y, size);
  }

  ctx.drawImage(await loadImage(resolve(assets, 'pcb_lineart_blank.png')), 200, 550, 1600, 900);
  let scale = 1600 / 1672;
  let topPins = Array.from({ length: 11 }, (_, i) => [200 + (513 + 33 * i) * scale, 550 + 216 * scale]);
  let otPins = Array.from({ length: 10 }, (_, i) => [200 + (294 + 35 * i) * scale, 550 + 720 * scale]);
  let powerPins = Array.from({ length: 4 }, (_, i) => [200 + (746 + 35 * i) * scale, 550 + 720 * scale]);
  let screenPins = [[200 + 308 * scale, 550 + 216 * scale], [200 + 342 * scale, 550 + 216 * scale]];
  for (let [i, value] of ['Vin', '5V', '输入', 'B2−', 'GND', 'A2+', 'V0+', 'B3−', 'GND', 'A3+', 'V0+'].entries()) {
    ctx.save();
    ctx.translate(topPins[i][0], topPins[i][1] + 70);
    ctx.rotate(-Math.PI / 2);
    tag(value, 0, 0, 35);
    ctx.restore();
  }
  tag('B1−', screenPins[0][0], screenPins[0][1] + 65, 32);
  tag('A1+', screenPins[1][0], screenPins[1][1] + 110, 32);
  for (let i = 0; i < 10; i++) {
    ctx.save();
    ctx.translate(otPins[i][0], otPins[i][1] + 75);
    ctx.rotate(-Math.PI / 2);
    tag(`OT${i + 1}`, 0, 0, 35);
    ctx.restore();
  }
  for (let [i, value] of ['0V', '0V', '+V', '+V'].entries()) tag(value, powerPins[i][0], powerPins[i][1] - 55, 32);
  tag('控制主板', 650, 1090, 45);
  tag('外扩板', 1540, 1190, 42);

  // 三只温湿度探头的电源和 RS485 共用四根总线，交叉处不额外连接。
  text('温湿度 A／B／C · 第二组 RS485', 710, 35, 44);
  for (let [i, x] of [35, 440, 900].entries()) {
    box(x, 85, 360, 130, `温湿度 ${['A', 'B', 'C'][i]}`);
    for (let [j, name] of ['485−', 'V−', '485+', 'V+'].entries()) {
      let px = x + 40 + 80 * j;
      text(name, px, 178, 32);
      line([[px, 215], [px, 265 + 55 * j]]);
      dot(px, 265 + 55 * j);
    }
  }
  for (let [j, pin] of [3, 4, 5, 6].entries()) {
    let rail = 265 + 55 * j;
    line([[35, rail], [1450, rail]]);
    line([[topPins[pin][0], rail], topPins[pin]]);
    dot(topPins[pin][0], rail);
    tag(['B2−', 'GND', 'A2+', 'V0+'][j], 1390, rail, 36);
  }

  box(880, 465, 650, 140, 'PT100 采集模块');
  for (let [j, name] of ['485−', '电源−', '485+', '电源+'].entries()) {
    let x = 935 + 150 * j;
    text(name, x, 564, 35);
    let pin = [7, 8, 9, 10][j];
    line([[x, 605], [x, 635 + 30 * j], [topPins[pin][0], 635 + 30 * j], topPins[pin]]);
  }

  box(35, 465, 480, 140, '控制屏 RS485');
  text('485−', 145, 564, 37);
  text('485+', 360, 564, 37);
  for (let i = 0; i < 2; i++) {
    line([[145 + 215 * i, 605], [145 + 215 * i, 675 - 45 * i], [screenPins[i][0], 675 - 45 * i], screenPins[i]]);
  }

  // 不画外部电源框；只保留板端 +V 到线圈的控制回路。
  line([powerPins[3], [powerPins[3][0], 1360], [1940, 1360], [1940, 1560], [190, 1560]]);
  tag('+V', 1920, 1560, 38);

  for (let [i, x] of [30, 690, 1350].entries()) {
    box(x, 1620, 620, 315);
    text(`继电器组 ${['A', 'B', 'C'][i]}`, x + 310, 1662, 40);
    let coils = [x + 160, x + 450];
    for (let j = 0; j < 2; j++) {
      let cx = coils[j];
      let n = i * 2 + j;
      let turn = n < 2 ? 1380 + 30 * n : 1580 - 40 * n;
      line([otPins[n], [otPins[n][0], turn], [cx - 110, turn], [cx - 110, 1788], [cx, 1788], [cx, 1770]]);
      tag(`OT${n + 1}`, cx - 110, 1585, 36);
      line([[cx, 1560], [cx, 1710]]);
      dot(cx, 1560);
      ctx.strokeRect(cx - 50, 1710, 100, 60);
      text(`K${n + 1}`, cx, 1740, 36);
      line([[cx + 50, 1740], [cx + 90, 1740], [cx + 90, 1765], [cx + 12, 1765], [cx + 12, 1860]], true);

      // 3 为两组切换触点的共同端；释放态 2–3 断开、3–4 接通，4 无外接线。
      line([[cx - 80, 1888], [cx - 30, 1888], [cx + 12, 1860], [cx + 65, 1860]]);
      dot(cx - 30, 1888);
      line([[cx + 20, 1915], [cx + 65, 1915]]);
      text('3', cx - 65, 1915, 36);
      tag('4 空', cx + 100, 1860, 32);
      text('2', cx + 80, 1915, 36);
    }
    line([[x + 25, 1830], [coils[1] - 80, 1830]]);
    tag('负载进线', x + 310, 1808, 33);
    box(x, 1960, 620, 180, `加热器 ${['A', 'B', 'C'][i]}`);
    for (let j = 0; j < 2; j++) {
      let cx = coils[j];
      let y = 2040 + 65 * j;
      line([[cx - 80, 1830], [cx - 80, 1888]]);
      dot(cx - 80, 1830);
      line([[cx + 65, 1915], [cx + 65, 1930 + j * 20], [x + 100 + 80 * j, 1930 + j * 20], [x + 100 + 80 * j, y], [x + 270, y]]);
      ctx.strokeRect(x + 270, y - 17, 135, 34);
      text(`${['A', 'B', 'C'][i]}${j + 1}`, x + 337, y, 30);
      line([[x + 405, y], [x + 590, y]]);
      dot(x + 590, y);
    }
    line([[x + 590, 2040], [x + 590, 2105]]);
    text('N／−', x + 570, 2000, 32);
  }
  text('使用 2–3 触点，4 留空；线圈与触点电气隔离', 1000, 2170, 38);
  // 导线在非连接交叉处画拱桥，与黑点连接区分。
  for (let [[vx, vy1], [vx2, vy2]] of segments) {
    if (vx !== vx2) continue;
    for (let [[hx1, hy], [hx2, hy2]] of segments) {
      if (hy !== hy2 || hx1 === hx2) continue;
      if (vx <= Math.min(hx1, hx2) + 10 || vx >= Math.max(hx1, hx2) - 10 || hy <= Math.min(vy1, vy2) + 10 || hy >= Math.max(vy1, vy2) - 10) continue;
      if (junctions.some(([x, y]) => Math.abs(x - vx) < 10 && Math.abs(y - hy) < 10)) continue;
      ctx.fillStyle = 'white';
      ctx.fillRect(vx - 4, hy - 11, 18, 22);
      ctx.strokeStyle = 'black';
      ctx.beginPath();
      ctx.moveTo(vx - 4, hy);
      ctx.lineTo(vx + 14, hy);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(vx, hy - 11);
      ctx.bezierCurveTo(vx + 16, hy - 11, vx + 16, hy + 11, vx, hy + 11);
      ctx.stroke();
    }
  }
  writeFileSync(resolve(assets, 'wiring.png'), canvas.toBuffer('image/png'));
  console.log(resolve(assets, 'wiring.png'));
})();
