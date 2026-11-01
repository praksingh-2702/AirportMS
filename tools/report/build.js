// Build docs/AMS_SAD_Report.docx :  node tools/report/build.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, LevelFormat, Header, Footer, PageNumber,
  TableOfContents, HeadingLevel, BorderStyle, ImageRun,
} = require("docx");
const L = require("./lib");
const c1 = require("./content1");
const c2 = require("./content2");
const c3 = require("./content3");

const T = (text, size, opts = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: opts.after ?? 160 },
  children: [new TextRun({ text, size, bold: opts.bold, italics: opts.italics, color: opts.color })] });

function cover() {
  const logo = fs.readFileSync(path.join(L.ROOT, "docs", "mit_logo.png"));
  return [
    new Paragraph({ alignment: AlignmentType.RIGHT, spacing: { after: 400 },
      children: [new ImageRun({ type: "png", data: logo, transformation: { width: 92, height: 108 },
        altText: { title: "MIT Manipal logo", description: "Manipal Institute of Technology logo", name: "mit_logo" } })] }),
    new Paragraph({ spacing: { before: 400 }, children: [] }),
    T("MANIPAL INSTITUTE OF TECHNOLOGY, MANIPAL", 28, { bold: true }),
    T("Department of Computer Science and Engineering", 24, { after: 600 }),
    T("Software Application Design Laboratory", 26),
    T("Mini-Project Report", 26, { after: 500 }),
    T("AIRPORT MANAGEMENT SYSTEM", 40, { bold: true, after: 200 }),
    T("Function-Oriented Design, Object-Oriented Design, Implementation and Testing", 24, { italics: true, after: 900 }),
    T("Submitted by", 24, { bold: true, after: 120 }),
    T("Prakhar Singh  -  240958196", 24, { after: 60 }),
    T("Prasang Saxena  -  240958278", 24, { after: 60 }),
    T("Krishna Gupta  -  240958222", 24, { after: 500 }),
    T("Under the guidance of", 24, { bold: true, after: 120 }),
    T("Srikanth Prabhu", 24, { after: 600 }),
    T("Session 2026-27", 22),
  ];
}

function tocPage() {
  return [
    new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun("Contents")] }),
    new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  ];
}

const body = [
  ...cover(), ...tocPage(),
  ...c1.ch1(), ...c1.ch2(), ...c1.ch3(), ...c1.ch4(), ...c1.ch5(), ...c1.ch6(),
  ...c2.ch7(), ...c2.ch8(), ...c2.ch9(),
  ...c3.ch10(), ...c3.ch11(), ...c3.ch12(), ...c3.ch13(), ...c3.references(), ...c3.appendixA(), ...c3.appendixB(),
];

const doc = new Document({
  creator: "SAD Lab Group",
  title: "Airport Management System - SAD Mini-Project Report",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: L.BODY_FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: "000000", font: L.BODY_FONT },
        paragraph: { spacing: { before: 120, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: "000000", font: L.BODY_FONT },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1, keepNext: true } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: "000000", font: L.BODY_FONT },
        paragraph: { spacing: { before: 220, after: 100 }, outlineLevel: 2, keepNext: true } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [
      { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
      { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 270 } } } },
    ] },
    { reference: "steps", levels: [
      { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } },
    ] },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } },
    },
    children: body,
  }],
});

const out = path.join(L.ROOT, "docs", "AMS_SAD_Report.docx");
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log("wrote", out, (buf.length / 1024 / 1024).toFixed(1), "MB"); });
