// Helper functions for building the report with docx-js.
const fs = require("fs");
const path = require("path");
const {
  Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType,
  ShadingType, BorderStyle, ImageRun, PageBreak, VerticalAlign,
} = require("docx");

const ROOT = path.resolve(__dirname, "..", "..");
const CONTENT_W = 9746;          // A4 width 11906 - 2 x 1080 margins (DXA)
const MAX_IMG_W_PX = 640;        // ~6.25 in at 96 px/in
const MAX_IMG_H_PX = 820;        // ~8.5 in
const BODY_FONT = "Times New Roman";
const MONO_FONT = "Courier New";

let figNo = 0;
let tabNo = 0;
let chapter = 0;
function setChapter(n) { chapter = n; figNo = 0; tabNo = 0; }

// **bold** and `code` inline markup -> TextRuns
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(new TextRun({ text: tok.slice(2, -2), bold: true, ...base }));
    else out.push(new TextRun({ text: tok.slice(1, -1), font: MONO_FONT, size: 20, ...base }));
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

const H1 = (t, opts = {}) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: opts.newPage !== false,
  spacing: opts.newPage === false ? { before: 360 } : undefined, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const P = (t, opts = {}) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 }, ...opts, children: runs(t) });
const Center = (t, size = 24, bold = false) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [new TextRun({ text: t, size, bold })] });
const Bullets = (items, level = 0) => items.map((t) => new Paragraph({ numbering: { reference: "bullets", level },
  spacing: { after: 60 }, alignment: AlignmentType.LEFT, children: runs(t) }));
const Numbered = (items, ref = "steps") => items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 },
  spacing: { after: 60 }, children: runs(t) }));
const Break = () => new Paragraph({ children: [new PageBreak()] });

function Code(lines) {
  return lines.map((line, i) => new Paragraph({
    spacing: { before: i === 0 ? 80 : 0, after: i === lines.length - 1 ? 120 : 0, line: 240 },
    indent: { left: 120 },
    children: [new TextRun({ text: line.length ? line : " ", font: MONO_FONT, size: 17 })],
  }));
}

function Caption(kind, text) {
  const n = kind === "Figure" ? ++figNo : ++tabNo;
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 200 },
    children: [new TextRun({ text: `${kind} ${chapter}.${n}: `, bold: true, size: 22 }),
               new TextRun({ text, size: 22 })] });
}

function pngSize(file) {
  const buf = fs.readFileSync(file);
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20), buf };
}

function Img(rel, caption, opts = {}) {
  const file = path.join(ROOT, rel);
  const { w, h, buf } = pngSize(file);
  const maxW = opts.maxW || MAX_IMG_W_PX, maxH = opts.maxH || MAX_IMG_H_PX;
  const scale = Math.min(maxW / w, maxH / h);
  const width = Math.round(w * scale), height = Math.round(h * scale);
  const out = [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120 },
    children: [new ImageRun({ type: "png", data: buf, transformation: { width, height },
      altText: { title: caption, description: caption, name: path.basename(file) } })] })];
  if (caption) out.push(Caption("Figure", caption));
  return out;
}


// Two figures side by side (borderless table), each with its own figure number and caption.
function ImgPair(relA, capA, relB, capB, opts = {}) {
  const cellW = Math.floor(CONTENT_W / 2);
  const maxW = opts.maxW || Math.floor(MAX_IMG_W_PX / 2) - 8, maxH = opts.maxH || 420;
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const nob = { top: none, bottom: none, left: none, right: none };
  const cell = (rel, cap) => {
    const { w, h, buf } = pngSize(path.join(ROOT, rel));
    const scale = Math.min(maxW / w, maxH / h);
    return new TableCell({ borders: nob, width: { size: cellW, type: WidthType.DXA }, verticalAlign: VerticalAlign.BOTTOM,
      margins: { top: 40, bottom: 40, left: 60, right: 60 },
      children: [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120 },
        children: [new ImageRun({ type: "png", data: buf, transformation: { width: Math.round(w * scale), height: Math.round(h * scale) },
          altText: { title: cap, description: cap, name: path.basename(rel) } })] }), Caption("Figure", cap)] });
  };
  return [new Table({ width: { size: cellW * 2, type: WidthType.DXA }, columnWidths: [cellW, cellW],
    borders: { top: none, bottom: none, left: none, right: none, insideHorizontal: none, insideVertical: none },
    rows: [new TableRow({ cantSplit: true, children: [cell(relA, capA), cell(relB, capB)] })] }),
    new Paragraph({ spacing: { after: 60 }, children: [] })];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
const borders = { top: border, bottom: border, left: border, right: border };

// widths: relative numbers; header row shaded
function Tbl(headers, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cols = widths.map((w) => Math.floor((w / total) * CONTENT_W));
  cols[cols.length - 1] += CONTENT_W - cols.reduce((a, b) => a + b, 0);
  const size = opts.size || 19;
  const cell = (text, i, header, fill) => new TableCell({
    borders, width: { size: cols[i], type: WidthType.DXA }, verticalAlign: VerticalAlign.TOP,
    shading: fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: String(text).split("\n").map((line) => new Paragraph({ spacing: { after: 0 },
      children: header ? [new TextRun({ text: line, bold: true, size })] : runs(line, { size }) })),
  });
  const trs = [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true, undefined)) })];
  rows.forEach((r) => trs.push(new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false, undefined)) })));
  const out = [new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: cols, rows: trs })];
  if (opts.caption) out.unshift(Caption("Table", opts.caption));
  out.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
  return out;
}

// Two-column key/value table (e.g. use-case descriptions)
function KV(pairs, caption) {
  const cols = [Math.floor(CONTENT_W * 0.24), CONTENT_W - Math.floor(CONTENT_W * 0.24)];
  const rows = pairs.map(([k, v]) => new TableRow({ cantSplit: false, children: [
    new TableCell({ borders, width: { size: cols[0], type: WidthType.DXA },
      margins: { top: 50, bottom: 50, left: 90, right: 90 },
      children: [new Paragraph({ children: [new TextRun({ text: k, bold: true, size: 19 })] })] }),
    new TableCell({ borders, width: { size: cols[1], type: WidthType.DXA }, margins: { top: 50, bottom: 50, left: 90, right: 90 },
      children: (Array.isArray(v) ? v : [v]).map((line) => new Paragraph({ spacing: { after: 20 }, children: runs(line, { size: 19 }) })) }),
  ] }));
  const out = [new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: cols, rows })];
  if (caption) out.unshift(Caption("Table", caption));
  out.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
  return out;
}

// Extract a Python function's source (from "def name" to the next def/class at same or lower indent)
function pySource(rel, name) {
  const lines = fs.readFileSync(path.join(ROOT, rel), "utf8").split("\n");
  const start = lines.findIndex((l) => new RegExp(`^\\s*def ${name}\\(`).test(l));
  if (start < 0) throw new Error(`def ${name} not found in ${rel}`);
  const indent = lines[start].match(/^\s*/)[0].length;
  let end = start + 1;
  while (end < lines.length) {
    const l = lines[end];
    if (l.trim() && l.match(/^\s*/)[0].length <= indent && !l.trim().startsWith(")")) break;
    end++;
  }
  while (!lines[end - 1].trim()) end--;
  return lines.slice(start, end).map((l) => l.slice(indent));
}

module.exports = { ROOT, CONTENT_W, BODY_FONT, MONO_FONT, H1, H2, H3, P, Center, Bullets, Numbered, Break, Code, ImgPair,
  Caption, Img, Tbl, KV, runs, setChapter, pySource };
