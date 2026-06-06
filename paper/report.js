
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType, VerticalAlign,
  LevelFormat, TabStopType, TabStopPosition, PageBreak, HeadingLevel
} = require("docx");
const fs = require("fs");

// ── Page settings ─────────────────────────────────────────────────────────────
// A4: 11906 x 16838 DXA | Left 1" = 1440 | Right 0.5" = 720 | Top/Bottom 1" = 1440
// Content width = 11906 - 1440 - 720 = 9746 DXA
const PAGE = { width: 11906, height: 16838 };
const MARGINS = { top: 1440, bottom: 1440, left: 1440, right: 720 };
const CW = 9746; // content width

// ── Colours ───────────────────────────────────────────────────────────────────
const MAROON = "8B0000";
const BLACK  = "000000";
const WHITE  = "FFFFFF";
const LGREY  = "F2F2F2";
const DGREY  = "D3D3D3";

// ── Borders ───────────────────────────────────────────────────────────────────
const thinB  = { style: BorderStyle.SINGLE, size: 4,  color: "000000" };
const thickB = { style: BorderStyle.SINGLE, size: 12, color: MAROON   };
const noneB  = { style: BorderStyle.NONE,   size: 0,  color: WHITE    };
const allThin = { top: thinB, bottom: thinB, left: thinB, right: thinB };
const allNone = { top: noneB, bottom: noneB, left: noneB, right: noneB };

// ── Line spacing helper ───────────────────────────────────────────────────────
const sp15 = { spacing: { before: 0, after: 120, line: 360, lineRule: "auto" } };
const sp10 = { spacing: { before: 0, after: 80,  line: 240, lineRule: "auto" } };
const spSect = { spacing: { before: 200, after: 120, line: 360, lineRule: "auto" } };

// ── Text run helpers ──────────────────────────────────────────────────────────
const tr = (text, opts = {}) => new TextRun({ text, font: "Times New Roman", size: 24, color: BLACK, ...opts });
const trB = (text, opts = {}) => tr(text, { bold: true, ...opts });
const trI = (text, opts = {}) => tr(text, { italics: true, ...opts });
const trBI = (text, opts = {}) => tr(text, { bold: true, italics: true, ...opts });

// ── Paragraph helpers ─────────────────────────────────────────────────────────
const body = (text, opts = {}) => new Paragraph({
  children: Array.isArray(text) ? text : [tr(text)],
  alignment: AlignmentType.JUSTIFIED,
  ...sp15, ...opts
});

const bodyB = (text, opts = {}) => new Paragraph({
  children: [trB(text)],
  alignment: AlignmentType.JUSTIFIED,
  ...sp15, ...opts
});

const ctr = (children, opts = {}) => new Paragraph({
  children: Array.isArray(children) ? children : [children],
  alignment: AlignmentType.CENTER,
  ...sp10, ...opts
});

const gap = (n = 1) => Array.from({ length: n }, () => new Paragraph({ children: [], spacing: { before: 0, after: 120 } }));

const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

// Chapter title: 16pt bold uppercase centered
const chapterTitle = (num, title) => new Paragraph({
  children: [trB(`CHAPTER ${num}`, { size: 32, allCaps: true }),
             trB(`\n${title}`, { size: 32, allCaps: true })],
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 240, line: 360, lineRule: "auto" },
});

// Section heading: 14pt bold (each word caps)
const sect = (text, opts = {}) => new Paragraph({
  children: [trB(text, { size: 28 })],
  alignment: AlignmentType.LEFT,
  spacing: { before: 240, after: 120, line: 360, lineRule: "auto" },
  ...opts
});

// Subsection: 12pt bold
const subsect = (text) => new Paragraph({
  children: [trB(text, { size: 24 })],
  alignment: AlignmentType.LEFT,
  spacing: { before: 200, after: 80, line: 360, lineRule: "auto" },
});

// Figure placeholder
const figPlaceholder = (num, caption) => [
  new Paragraph({
    children: [tr(`<<FIGURE ${num}: ${caption}>>`, { size: 22, color: "666666", italics: true })],
    alignment: AlignmentType.CENTER,
    border: { top: thinB, bottom: thinB, left: thinB, right: thinB },
    spacing: { before: 160, after: 60, line: 240, lineRule: "auto" },
    shading: { fill: "F7F7F7", type: ShadingType.CLEAR },
  }),
  new Paragraph({
    children: [trB(`Fig ${num}: ${caption}`, { size: 22 })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 40, after: 160, line: 240, lineRule: "auto" },
  }),
];

// Table caption
const tableCaption = (num, caption) => new Paragraph({
  children: [trB(`Table ${num}: ${caption}`, { size: 22 })],
  alignment: AlignmentType.CENTER,
  spacing: { before: 160, after: 60, line: 240, lineRule: "auto" },
});

// Simple 2-col table row
const trow = (cells, isHeader = false) => new TableRow({
  tableHeader: isHeader,
  children: cells.map((c, i) => new TableCell({
    borders: allThin,
    shading: { fill: isHeader ? "2E4057" : (i % 2 === 0 ? WHITE : LGREY), type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 120, right: 120 },
    width: { size: Math.floor(CW / cells.length), type: WidthType.DXA },
    children: [new Paragraph({
      children: [isHeader ? trB(c, { size: 22, color: WHITE }) : tr(c, { size: 22 })],
      alignment: AlignmentType.LEFT,
      spacing: { before: 0, after: 0 },
    })],
  })),
});

// Bullet list item
const bullet = (text) => new Paragraph({
  children: [tr(text)],
  numbering: { reference: "bullets", level: 0 },
  alignment: AlignmentType.JUSTIFIED,
  spacing: { before: 0, after: 80, line: 360, lineRule: "auto" },
});

// Numbered list item
const numItem = (text) => new Paragraph({
  children: [tr(text)],
  numbering: { reference: "numbers", level: 0 },
  alignment: AlignmentType.JUSTIFIED,
  spacing: { before: 0, after: 80, line: 360, lineRule: "auto" },
});

// Reference item
const ref = (num, text) => new Paragraph({
  children: [tr(`[${num}] ${text}`)],
  alignment: AlignmentType.JUSTIFIED,
  spacing: { before: 0, after: 120, line: 360, lineRule: "auto" },
});

// ══════════════════════════════════════════════════════════════════════════════
// DOCUMENT CHILDREN
// ══════════════════════════════════════════════════════════════════════════════
const children = [

// ─────────────────────────────────────────────────────────────────────────────
// COVER PAGE
// ─────────────────────────────────────────────────────────────────────────────
  ctr([trB("SRM INSTITUTE OF SCIENCE AND TECHNOLOGY", { size: 28, color: MAROON })]),
  ctr([trB("DEPARTMENT OF COMPUTATIONAL INTELLIGENCE", { size: 24, color: MAROON })]),
  ctr([trB("COLLEGE OF ENGINEERING AND TECHNOLOGY", { size: 24, color: MAROON })]),
  ctr([tr("KATTANKULATHUR – 603 203", { size: 22 })]),
  ...gap(1),
  ctr([tr("<<SRM LOGO PLACEHOLDER>>", { size: 20, italics: true, color: "888888" })]),
  ...gap(1),
  new Paragraph({
    children: [trB("21CSP302L – MINOR RESEARCH PROJECT", { size: 28 })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 80 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: MAROON, space: 1 } },
  }),
  ...gap(1),
  ctr([trB("SafeHer: AI-Powered Women Safety and Emergency Response System", { size: 36, color: MAROON })], { spacing: { before: 200, after: 200 } }),
  ...gap(1),
  ctr([tr("in partial fulfillment of the requirements for the degree of", { size: 22, italics: true })]),
  ctr([trB("BACHELOR OF TECHNOLOGY", { size: 28 })]),
  ctr([trB("in", { size: 24 })]),
  ctr([trB("COMPUTER SCIENCE AND ENGINEERING", { size: 28 })]),
  ctr([tr("with specialization in Data Science and Business Systems", { size: 22 })]),
  ...gap(1),
  ctr([trB("Submitted by", { size: 22 })]),
  ...gap(1),
  ctr([trB("ADITYA SHARMA [RA2111003010042]", { size: 28 })]),
  ctr([trB("PARI GUPTA [RA2111003010047]", { size: 28 })]),
  ...gap(1),
  ctr([tr("Under the Guidance of", { size: 22, italics: true })]),
  ctr([trB("Dr. P. RAJASEKAR", { size: 26, color: MAROON })]),
  ctr([tr("Associate Professor, Department of Data Science and Business Systems", { size: 22 })]),
  ...gap(2),
  ctr([trB("MAY 2026", { size: 24 })]),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// DECLARATION
// ─────────────────────────────────────────────────────────────────────────────
  new Paragraph({
    children: [trB("SRM INSTITUTE OF SCIENCE AND TECHNOLOGY", { size: 28, color: MAROON })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 0, after: 60 },
  }),
  ctr([trB("KATTANKULATHUR – 603 203", { size: 22 })]),
  ctr([trB("OWN WORK DECLARATION", { size: 28 })], { spacing: { before: 240, after: 240 } }),
  body("This sheet must be filled in and signed, confirming that all conditions listed below have been met. It must be included with the submitted project report. Work will not be evaluated unless this form is properly completed."),
  ...gap(1),
  bodyB("Degree / Course:"),
  body("Bachelor of Technology in Computer Science and Engineering (Data Science and Business Systems)"),
  bodyB("Student Names and Registration Numbers:"),
  body("Aditya Sharma [RA2111003010042], Pari Gupta [RA2111003010047]"),
  bodyB("Title of Work:"),
  body("SafeHer: AI-Powered Women Safety and Emergency Response System"),
  ...gap(1),
  body("We hereby certify that this project report complies with the University's Rules and Regulations relating to academic misconduct and plagiarism, as listed on the University Website. We confirm that:"),
  bullet("All sources have been clearly referenced and listed as appropriate."),
  bullet("All quoted text has been placed in inverted commas with sources cited."),
  bullet("Sources of all pictures, data, and figures not our own have been provided."),
  bullet("We have not made use of reports or essays of any other student, past or present."),
  bullet("Any help received from others (peers, technicians, external sources) has been duly acknowledged."),
  bullet("We have complied with all plagiarism criteria specified in the course handbook."),
  ...gap(1),
  body("We understand that any false claim in this work will be penalized in accordance with University policies and regulations."),
  ...gap(2),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [CW / 2, CW / 2],
    rows: [
      new TableRow({ children: [
        new TableCell({ borders: allNone, width: { size: CW/2, type: WidthType.DXA },
          children: [body("DECLARATION: I am aware of the University's policy on Academic Misconduct and Plagiarism and certify that this assessment is our own work.")] }),
        new TableCell({ borders: allNone, width: { size: CW/2, type: WidthType.DXA },
          children: [body("")] }),
      ]}),
      new TableRow({ children: [
        new TableCell({ borders: allNone, width: { size: CW/2, type: WidthType.DXA },
          children: [body("Aditya Sharma\n<<Signature>>\nDate: _____________")] }),
        new TableCell({ borders: allNone, width: { size: CW/2, type: WidthType.DXA },
          children: [body("Pari Gupta\n<<Signature>>\nDate: _____________")] }),
      ]}),
    ],
  }),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// BONAFIDE CERTIFICATE
// ─────────────────────────────────────────────────────────────────────────────
  ctr([trB("SRM INSTITUTE OF SCIENCE AND TECHNOLOGY", { size: 28, color: MAROON })]),
  ctr([trB("KATTANKULATHUR – 603 203", { size: 22 })]),
  ...gap(1),
  ctr([trB("BONAFIDE CERTIFICATE", { size: 28 })], { spacing: { before: 200, after: 200 } }),
  body([
    tr("Certified that "),
    trB("21CSP302L – Minor Research Project"),
    tr(" titled "),
    trB("\"SafeHer: AI-Powered Women Safety and Emergency Response System\""),
    tr(" is the bonafide work of "),
    trB("\"Aditya Sharma [RA2111003010042] and Pari Gupta [RA2111003010047]\""),
    tr(", who carried out the project work under my supervision. Certified further that, to the best of my knowledge, the work reported herein does not form part of any other project report or dissertation on the basis of which a degree or award was conferred on an earlier occasion on this or any other candidate."),
  ]),
  ...gap(3),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [CW/2, CW/2],
    rows: [
      new TableRow({ children: [
        new TableCell({ borders: allNone, width: { size: CW/2, type: WidthType.DXA },
          children: [
            body("<<Signature>>"),
            bodyB("Dr. P. RAJASEKAR"),
            body("Associate Professor"),
            body("Department of Data Science and Business Systems"),
            body("SRM Institute of Science and Technology"),
          ] }),
        new TableCell({ borders: allNone, width: { size: CW/2, type: WidthType.DXA },
          children: [
            body("<<Signature>>"),
            bodyB("DR. R. ANNIE UTHRA"),
            body("Professor & Head"),
            body("Department of Computational Intelligence"),
            body("SRM Institute of Science and Technology"),
          ] }),
      ]}),
    ],
  }),
  ...gap(2),
  body("EXAMINER 1: Name & Signature ________________________"),
  body("EXAMINER 2: Name & Signature ________________________"),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// ACKNOWLEDGEMENT
// ─────────────────────────────────────────────────────────────────────────────
  ctr([trB("ACKNOWLEDGEMENTS", { size: 32 })], { spacing: { before: 0, after: 240 } }),
  body("We express our humble gratitude to the Vice-Chancellor, SRM Institute of Science and Technology, for the facilities extended for the project work and his continued encouragement and support throughout our academic journey."),
  body("We extend our sincere thanks to the Dean, College of Engineering and Technology, SRM Institute of Science and Technology, for his invaluable support and for fostering a culture of innovation and research within the institution."),
  body("We wish to thank Dr. Revathi Venkataraman, Professor and Chairperson, School of Computing, SRM Institute of Science and Technology, for her continued support throughout the project work and for inspiring us to pursue meaningful research."),
  body("We are incredibly grateful to the Head of the Department, Department of Data Science and Business Systems, SRM Institute of Science and Technology, for her suggestions and encouragement at all stages of our project work and for providing us with the resources needed to complete this research."),
  body("We convey our sincere thanks to our Project Coordinators, Panel Head, and Panel Members, Department of Data Science and Business Systems, SRM Institute of Science and Technology, for their constructive inputs during the project reviews and for their guidance throughout the development process."),
  body("We register our immeasurable thanks to our Faculty Advisor, Department of Data Science and Business Systems, SRM Institute of Science and Technology, for leading and helping us to complete our course and for continuously motivating us to achieve excellence."),
  body("Our deepest respect and gratitude go to our guide, Dr. P. Rajasekar, Associate Professor, Department of Data Science and Business Systems, SRM Institute of Science and Technology, for providing us with the opportunity to pursue this project under his expert mentorship. His passion for solving real-world problems using artificial intelligence, his clarity of thought, and his commitment to research have been a constant source of inspiration. His guidance, freedom to explore, and timely support were invaluable in shaping this work."),
  body("We sincerely thank all the staff members of the Department of Data Science and Business Systems, School of Computing, SRM Institute of Science and Technology, for their assistance during our project. Finally, we would like to thank our parents, family members, and friends for their unconditional love, constant support, and unwavering encouragement throughout this journey."),
  ...gap(2),
  ctr([trB("Authors")]),
  ctr([tr("Aditya Sharma & Pari Gupta")]),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// ABSTRACT
// ─────────────────────────────────────────────────────────────────────────────
  ctr([trB("ABSTRACT", { size: 32 })], { spacing: { before: 0, after: 240 } }),
  body("Women's personal safety in urban environments remains one of the most pressing societal challenges of the twenty-first century. Existing navigation platforms such as Google Maps and Apple Maps optimise routes exclusively for time and distance, offering no mechanism for crime-risk-aware routing or real-time emergency response. SafeHer is a comprehensive AI-powered women safety and emergency response system that addresses this gap through an integrated multi-modal framework combining real-time crime risk prediction, GPS-based location tracking, instant SOS alert dispatch, and intelligent safe-route recommendation."),
  body("The system employs a two-component machine learning architecture trained on 8.4 million crime incidents from the City of Chicago Crimes Dataset (2001–2025). A LightGBM regressor predicts spatial danger scores per 200-metre grid cell using a Crime Danger Index (CDI) percentile target—achieving R² = 0.9997 and High-Risk Precision of 99.2%—while a 168-slot empirical temporal multiplier (violent crime rate by hour × day-of-week) modulates risk dynamically. Together, these components regenerate a full-city risk heatmap in under one second, over 100 times faster than CNN-LSTM baselines."),
  body("The React.js frontend integrates with the Google Maps JavaScript API to render a live, colour-coded heatmap that visually changes as users drag an hour slider, and recommends up to three alternative driving routes ranked by safety. The Flask-based REST API ensures that heatmap colours and route risk scores are always computed from the same underlying model, guaranteeing mathematical consistency—a property termed unified risk coupling that is absent from all prior women-safety navigation systems."),
  body("Additional safety features include an SOS emergency alert module with GPS coordinate dispatch to pre-registered emergency contacts, voice-activated emergency triggers, safe and unsafe zone delineation based on historical crime density, and a community-sourced incident reporting interface. The system was evaluated through functional testing, performance benchmarking, and user acceptance testing, demonstrating sub-second heatmap regeneration, reliable SOS dispatch, and measurably improved route safety scores compared to distance-optimal routing."),
  body("SafeHer aligns with United Nations Sustainable Development Goal 5 (Gender Equality) and SDG 11 (Sustainable Cities and Communities) by providing women with a data-driven, accessible, and real-time safety tool for urban navigation. This report documents the system design, machine learning methodology, backend architecture, frontend implementation, sprint-based development process, evaluation results, and directions for future enhancement including IoT wearable integration and multi-city generalisation."),
  ...gap(1),
  body([trB("Keywords: "), tr("Women Safety, AI, LightGBM, Crime Prediction, Safe Navigation, SOS Alert, GPS Tracking, Real-Time Heatmap, Flask, React.js, Google Maps API")]),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// TABLE OF CONTENTS
// ─────────────────────────────────────────────────────────────────────────────
  ctr([trB("TABLE OF CONTENTS", { size: 32 })], { spacing: { before: 0, after: 240 } }),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [7000, 2746],
    rows: [
      trow(["SECTION", "PAGE NO."], true),
      trow(["Abstract", "v"]),
      trow(["Table of Contents", "vi"]),
      trow(["List of Figures", "vii"]),
      trow(["List of Tables", "viii"]),
      trow(["Abbreviations", "ix"]),
      trow(["CHAPTER 1: INTRODUCTION", "1"]),
      trow(["  1.1  Introduction to the Project", "2"]),
      trow(["  1.2  Problem Statement and Description", "4"]),
      trow(["  1.3  Motivation", "5"]),
      trow(["  1.4  Sustainable Development Goals", "6"]),
      trow(["CHAPTER 2: LITERATURE SURVEY", "7"]),
      trow(["  2.1  Overview of the Research Area", "8"]),
      trow(["  2.2  Existing Systems and Research", "9"]),
      trow(["  2.3  Research Gaps", "12"]),
      trow(["  2.4  Research Objectives", "13"]),
      trow(["  2.5  Product Backlog (User Stories)", "14"]),
      trow(["  2.6  Plan of Action (Project Roadmap)", "16"]),
      trow(["CHAPTER 3: SPRINT PLANNING AND EXECUTION", "18"]),
      trow(["  3.1  Sprint I – ML Pipeline and Risk Model", "19"]),
      trow(["  3.2  Sprint II – Backend API and Frontend", "27"]),
      trow(["CHAPTER 6: RESULTS AND DISCUSSIONS", "35"]),
      trow(["  6.1  Performance Evaluation", "36"]),
      trow(["  6.2  Testing and Comparisons", "40"]),
      trow(["CHAPTER 7: CONCLUSION AND FUTURE ENHANCEMENT", "43"]),
      trow(["References", "45"]),
      trow(["Appendix A – Code Samples", "48"]),
      trow(["Appendix B – Publications", "50"]),
    ],
  }),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// LIST OF FIGURES
// ─────────────────────────────────────────────────────────────────────────────
  ctr([trB("LIST OF FIGURES", { size: 32 })], { spacing: { before: 0, after: 240 } }),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [1200, 6800, 1746],
    rows: [
      new TableRow({ tableHeader: true, children: [
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1200, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("Fig. No.", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 6800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("Title", { size: 22, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1746, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("Page No.", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
      ]}),
      ...[
        ["1.1","SafeHer System Overview Diagram","3"],
        ["1.2","Sustainable Development Goals Alignment","6"],
        ["2.1","Comparison of Existing Safety Applications","10"],
        ["2.2","Project Roadmap / Gantt Chart","17"],
        ["3.1","ML Pipeline Architecture","21"],
        ["3.2","Severity Class Distribution (Class Imbalance)","22"],
        ["3.3","Crime Danger Index Formula and Distribution","23"],
        ["3.4","LightGBM Feature Importance Chart","25"],
        ["3.5","Temporal Multiplier Heatmap (24 × 7 Grid)","26"],
        ["3.6","SafeHer System Architecture Diagram","29"],
        ["3.7","Database Entity Relationship Diagram","31"],
        ["3.8","API Flow Diagram","32"],
        ["3.9","Risk Heatmap UI Screenshot","33"],
        ["3.10","Safe Route Recommendation UI Screenshot","34"],
        ["6.1","Model Performance Comparison – R² and MAE","37"],
        ["6.2","Grid Generation Speed – LightGBM vs CNN-LSTM","38"],
        ["6.3","SOS Alert Flow Testing Results","41"],
        ["6.4","User Acceptance Testing Results","42"],
      ].map(([n, t, p]) => new TableRow({ children: [
        new TableCell({ borders: allThin, width: { size: 1200, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [tr(n, { size: 22 })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, width: { size: 6800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [tr(t, { size: 22 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 1746, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [tr(p, { size: 22 })], alignment: AlignmentType.CENTER })] }),
      ]})),
    ],
  }),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// LIST OF TABLES
// ─────────────────────────────────────────────────────────────────────────────
  ctr([trB("LIST OF TABLES", { size: 32 })], { spacing: { before: 0, after: 240 } }),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [1200, 6800, 1746],
    rows: [
      new TableRow({ tableHeader: true, children: [
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1200, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("Table No.", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 6800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("Title", { size: 22, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1746, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("Page No.", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
      ]}),
      ...[
        ["2.1","Comparison of Existing Women Safety Applications","11"],
        ["2.2","Product Backlog – User Stories","15"],
        ["3.1","Sprint I – Objectives and Deliverables","20"],
        ["3.2","Dataset Summary Statistics","22"],
        ["3.3","Feature Engineering Summary","24"],
        ["3.4","Sprint II – Objectives and Deliverables","28"],
        ["3.5","API Endpoint Reference","32"],
        ["6.1","Spatial Risk Model Comparison (Table I)","37"],
        ["6.2","System Timing Evaluation (Table II)","39"],
        ["6.3","Functional Test Cases and Results","41"],
        ["6.4","User Acceptance Testing Scores","42"],
      ].map(([n, t, p]) => new TableRow({ children: [
        new TableCell({ borders: allThin, width: { size: 1200, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [tr(n, { size: 22 })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, width: { size: 6800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [tr(t, { size: 22 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 1746, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [tr(p, { size: 22 })], alignment: AlignmentType.CENTER })] }),
      ]})),
    ],
  }),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// ABBREVIATIONS
// ─────────────────────────────────────────────────────────────────────────────
  ctr([trB("ABBREVIATIONS", { size: 32 })], { spacing: { before: 0, after: 240 } }),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [2400, 7346],
    rows: [
      trow(["Abbreviation", "Full Form"], true),
      ...([
        ["AI","Artificial Intelligence"],["API","Application Programming Interface"],
        ["CDI","Crime Danger Index"],["CNN","Convolutional Neural Network"],
        ["CSS","Cascading Style Sheet"],["CSV","Comma-Separated Values"],
        ["DB","Database"],["EDA","Exploratory Data Analysis"],
        ["GPS","Global Positioning System"],["GBM","Gradient Boosting Machine"],
        ["HTML","Hyper Text Markup Language"],["HTTP","Hyper Text Transfer Protocol"],
        ["JSON","JavaScript Object Notation"],["JS","JavaScript"],
        ["LightGBM","Light Gradient Boosting Machine"],["MAE","Mean Absolute Error"],
        ["ML","Machine Learning"],["R²","Coefficient of Determination"],
        ["REST","Representational State Transfer"],["RF","Random Forest"],
        ["SDG","Sustainable Development Goal"],["SOS","Save Our Souls (Emergency Signal)"],
        ["SQL","Structured Query Language"],["UI","User Interface"],
        ["URL","Uniform Resource Locator"],["XGBoost","Extreme Gradient Boosting"],
      ]).map(([a, f]) => trow([a, f])),
    ],
  }),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// CHAPTER 1: INTRODUCTION
// ─────────────────────────────────────────────────────────────────────────────
  chapterTitle("1", "INTRODUCTION"),

  sect("1.1 Introduction to the Project"),
  body("In urban environments across the world, personal safety — particularly for women — remains a profoundly underserved concern. Despite significant technological advances in navigation, communication, and data analytics, mainstream mapping and transportation platforms continue to optimise routes exclusively for travel time and shortest distance. No consideration is given to the relative safety of a path, the historical crime profile of a neighbourhood, or the time-of-day variation in criminal activity. This fundamental gap creates a measurable disadvantage for women navigating public spaces, particularly after dark."),
  body("SafeHer is an AI-powered, real-time women safety and emergency response system designed to address this gap through a comprehensive multi-modal framework. The system combines machine learning-driven crime risk prediction, GPS-based live location tracking, SOS emergency alert dispatch, voice-activated emergency triggers, and intelligent safe-route recommendation — all accessible through an intuitive web and mobile interface built on React.js and integrated with the Google Maps JavaScript API."),
  body("At the core of SafeHer lies a two-component risk model: a LightGBM regressor trained on 8.4 million historical crime incidents from the City of Chicago (2001–2025) predicts spatial danger scores per 200-metre grid cell, while a 168-slot empirical temporal multiplier captures how crime risk varies by hour and day of week. Together, these components power a live heatmap that updates in under one second as users move the time slider — a capability that no prior women-safety system has demonstrated in the published literature."),
  body("The system's most architecturally significant property is its unified risk coupling: both the visual heatmap and the route-scoring engine are powered by the exact same model call. This guarantees that the green, amber, or red colour a user sees on the heatmap for any neighbourhood is mathematically identical to the risk contribution of a route passing through that neighbourhood. This consistency — absent from all prior systems — ensures that the system's safety recommendations are always grounded in the same empirical evidence the user can visually inspect."),
  ...figPlaceholder("1.1", "SafeHer System Overview — Components and Data Flow"),

  sect("1.2 Problem Statement and Description"),
  body("Women face disproportionate levels of street harassment, assault, and violence in public spaces, particularly during nighttime travel. A 2020 study by Vera-Gray and Kelly [1] demonstrated that fear of crime significantly restricts women's mobility, limits their participation in public life, and induces route modifications that prioritise perceived safety over efficiency — often at substantial cost in time and convenience. Despite this well-documented need, the technology industry has largely failed to incorporate safety as a first-class routing criterion."),
  body("The problem has three computable dimensions. First, existing navigation applications have no mechanism for crime-risk-aware routing; they treat all streets as equally safe at all times. Second, existing safety-focused applications — such as Safetipin and similar crowdsourced platforms — rely on subjective user audits that are geographically sparse, temporally static, and dependent on sustained community participation, making them unreliable for real-time navigation decisions. Third, when academic systems do incorporate crime data, they typically use static, time-averaged risk maps that do not reflect the dramatic intra-day variation in crime patterns (for example, a zone that is safe at 2PM may be genuinely dangerous at 11PM)."),
  body("SafeHer addresses all three dimensions: it integrates real crime data at 200-metre spatial resolution with hourly temporal granularity, provides consistent risk scoring across both map visualisation and route recommendation, and includes emergency response capabilities that existing systems entirely lack. The core problem statement is: given a city-wide grid of geographic cells and a temporal query (hour, day), compute a risk score for every cell such that the score reflects the historical crime danger at that location at that specific time, can be computed in under one second across 14,129 cells, and is consistent across both the heatmap display and the route safety scorer."),

  sect("1.3 Motivation"),
  body("The motivation for SafeHer emerges from three converging imperatives: social necessity, technological opportunity, and academic originality."),
  body("From the social perspective, published statistics paint a sobering picture. According to the National Crime Records Bureau (NCRB) of India, crimes against women increased by 15.3% between 2019 and 2021. In the United States, the FBI Uniform Crime Reporting (UCR) data indicates that violent crime disproportionately affects women in public spaces during evening and nighttime hours. Yet the tools available to women for real-time safety decision-making remain primitive: most rely on manual reporting or subjective community ratings, offer no temporal sensitivity, and provide no integration between what is displayed on a map and what is recommended as a route."),
  body("From the technological perspective, the convergence of open crime datasets (such as Chicago's publicly available 8.4 million-incident dataset), lightweight gradient-boosting models capable of sub-second inference, and modern web APIs for mapping and location services creates an unprecedented opportunity to build a genuinely useful safety tool at low cost and high quality. The key insight driving SafeHer's design is that heatmap visualisation and route scoring are fundamentally the same operation: given a location and a time, produce a risk score. Grounding both in a single shared model eliminates the inconsistency that afflicts all prior systems."),
  body("From the academic perspective, SafeHer makes five novel contributions to the literature on women-safety systems and spatial crime prediction: (1) a Crime Danger Index (CDI) percentile target that resolves the class imbalance and label ambiguity of per-incident severity classification; (2) a two-component risk architecture separating spatial ML from empirical temporal lookup; (3) unified risk coupling between heatmap and route scorer; (4) 13-feature spatial engineering from public data alone; and (5) a dynamic temporal heatmap that changes visually hour-by-hour, which no prior women-safety navigation system has demonstrated."),

  sect("1.4 Sustainable Development Goal (SDG) Alignment"),
  body("SafeHer directly addresses the United Nations Sustainable Development Goals 5 and 11, and contributes indirectly to SDG 3 and SDG 16."),
  body([trB("SDG 5 – Gender Equality: "), tr("Target 5.2 mandates the elimination of all forms of violence against women in the public sphere. SafeHer directly serves this target by providing women with actionable, data-driven information about the relative safety of urban spaces at different times of day, enabling safer movement without dependence on subjective or crowdsourced assessments.")]),
  body([trB("SDG 11 – Sustainable Cities and Communities: "), tr("Target 11.7 calls for universal access to safe, inclusive, and accessible public spaces, particularly for women. SafeHer contributes to this target by making real-time crime risk information accessible and understandable to any user through a standard web browser.")]),
  body([trB("SDG 3 – Good Health and Well-Being: "), tr("By reducing the number of situations in which women are exposed to dangerous environments unknowingly, SafeHer contributes to physical safety and mental health outcomes associated with reduced fear and anxiety during urban navigation.")]),
  body([trB("SDG 16 – Peace, Justice and Strong Institutions: "), tr("SafeHer's use of officially reported crime data (rather than arrests or convictions) and its presentation of risk as a relative percentile rather than an absolute count aligns with principles of fairness and evidence-based public safety.")]),
  ...figPlaceholder("1.2", "SDG Alignment Diagram for SafeHer"),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// CHAPTER 2: LITERATURE SURVEY
// ─────────────────────────────────────────────────────────────────────────────
  chapterTitle("2", "LITERATURE SURVEY"),

  sect("2.1 Overview of the Research Area"),
  body("The intersection of artificial intelligence, geographic information systems (GIS), and personal safety represents a rapidly growing research domain. Three sub-fields are directly relevant to SafeHer: (i) machine learning-based crime prediction and spatial risk modelling; (ii) safety-aware navigation and route recommendation; and (iii) real-time emergency response systems. This chapter reviews the state of the art in each sub-field, identifies the gaps that SafeHer addresses, and situates the project's contributions within the existing literature."),
  body("Crime prediction using machine learning has a substantial academic history. Early approaches relied on kernel density estimation (KDE) [2] to produce static hotspot maps from historical incident data. While KDE is computationally simple and widely deployed by law enforcement agencies, it produces entirely static risk representations with no temporal variation and no route-scoring capability. More recent work has applied ensemble methods — including Random Forest [3] and gradient-boosting models [4] — to tabular crime data, demonstrating substantially improved prediction accuracy when spatial features such as community area and distance to police stations are incorporated. Deep learning approaches, particularly CNN-LSTM hybrid architectures [5], have achieved competitive predictive accuracy but at substantially higher inference cost, estimated at approximately 90 seconds per full-city heatmap generation at 200-metre resolution, making them unsuitable for real-time applications."),
  body("Safety-aware navigation represents a smaller but growing sub-field. SafePath [6] constructs a graph of city streets with crime-weighted edges and applies Dijkstra's algorithm to find safer paths. CrimeTravel [7] extends this with multi-objective optimisation balancing safety against travel time. Both systems suffer from two structural limitations: their risk models are time-invariant (treating a zone as equally dangerous at noon and at midnight), and their map visualisation and route-scoring components use independently computed risk estimates, producing mathematical inconsistency between the heatmap and the recommended route. WalkSafe [8] uses smartphone sensor data for pedestrian safety but does not model spatial crime density."),
  body("Emergency response systems for women have largely followed a different track, focusing on SOS alerting, GPS tracking, and contact notification rather than risk prediction. Applications such as Safetipin [9], bSafe, and Nimb operate in this space, using crowdsourced safety audits and sensor-based panic buttons. These systems are geographically sparse, temporally static, and entirely separate from any navigation or routing functionality. SafeHer bridges both tracks — integrating real-time emergency response with AI-driven risk prediction and route recommendation in a single unified system."),

  sect("2.2 Existing Systems and Research"),
  tableCaption("2.1", "Comparison of Existing Women Safety Applications and Research Systems"),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [2000, 2500, 2000, 3246],
    rows: [
      new TableRow({ tableHeader: true, children: [
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 2000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("System", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 2500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("Approach", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 2000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("Limitations", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 3246, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("SafeHer Advantage", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
      ]}),
      ...[
        ["Safetipin", "Crowdsourced safety audits + POI data", "Subjective, sparse, no real-time update", "Uses 8.4M official police records; objective and dense"],
        ["SafePath [6]", "Crime-weighted graph + Dijkstra routing", "Static risk; route and heatmap decoupled", "Dynamic temporal risk; unified risk coupling"],
        ["CrimeTravel [7]", "Multi-objective optimisation (safety + time)", "No temporal variation; no heatmap", "168-slot temporal multiplier; live heatmap"],
        ["WalkSafe [8]", "Smartphone sensors for pedestrian safety", "No spatial crime density model", "LightGBM spatial regressor; 200m grid cells"],
        ["bSafe / Nimb", "SOS button + live GPS share", "No risk prediction or routing", "Full SOS + routing + heatmap in one system"],
        ["KDE Hotspot [2]", "Kernel density estimation on incident data", "Static; no temporal variation; no routing", "Dynamic hourly heatmap; route scoring"],
        ["CNN-LSTM [5]", "Deep learning spatial-temporal model", "~90s per heatmap; needs GPU", "LightGBM: <1s; runs on CPU; 105x faster"],
        ["Google Maps", "Time/distance optimal routing", "No safety consideration whatsoever", "Safety-ranked routes from same model as heatmap"],
      ].map(([s, a, l, adv]) => new TableRow({ children: [
        new TableCell({ borders: allThin, width: { size: 2000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [tr(s, { size: 20 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 2500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [tr(a, { size: 20 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 2000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [tr(l, { size: 20 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 3246, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [tr(adv, { size: 20 })], alignment: AlignmentType.LEFT })] }),
      ]})),
    ],
  }),
  ...figPlaceholder("2.1", "Comparison of Existing Safety Applications – Feature Matrix"),
  body("The review of prior work reveals that existing systems fall into two disjoint categories: those that predict crime or display risk maps, and those that respond to emergencies. No existing system simultaneously provides temporally-dynamic risk scoring at pedestrian spatial granularity, risk-coupled route recommendation using the same underlying model as the map visualisation, sub-second heatmap regeneration for real-time interaction, and integrated SOS emergency response. SafeHer is designed to close all four dimensions of this gap in a single, deployable web application."),

  sect("2.3 Research Gaps Identified from Literature"),
  body("The following key gaps have been identified from a systematic review of the literature:"),
  bullet("Gap 1 – Temporal Static Risk Models: All existing crime-aware navigation systems use time-averaged risk scores. None account for the fact that the same location can be safe at 9AM and genuinely dangerous at 11PM. The temporal multiplier in SafeHer, covering 168 time slots (24 hours × 7 days), directly addresses this gap."),
  bullet("Gap 2 – Inconsistency Between Heatmap and Route Scorer: Existing systems that display a risk heatmap and also recommend routes compute these using separate, independently-tuned risk estimates. SafeHer introduces unified risk coupling — both features use the same model call — as a first-class design property."),
  bullet("Gap 3 – Scalability of Deep Learning Approaches: CNN-LSTM models achieve strong predictive accuracy but require approximately 90 seconds to regenerate a city-wide heatmap at 200-metre resolution, making them incompatible with real-time interactive use. SafeHer's LightGBM regressor achieves the same spatial accuracy in under one second."),
  bullet("Gap 4 – Class Imbalance in Crime Severity Prediction: Per-incident severity classification is ill-posed because the same location at the same time can produce both low-severity (theft) and high-severity (assault) incidents, yielding identical feature vectors with different labels. The CDI percentile target, introduced in SafeHer, resolves this by aggregating to one row per grid cell with a uniform 0–1 distribution."),
  bullet("Gap 5 – Separation of Safety Navigation and Emergency Response: No existing system combines AI-driven risk prediction, route recommendation, and SOS emergency alerting in a single platform. Users currently must switch between safety-focused apps and navigation apps, losing coherence and response speed."),

  sect("2.4 Research Objectives"),
  body("Based on the identified gaps, the following research objectives were defined for the SafeHer project:"),
  numItem("Design a crime-risk target variable (CDI percentile) that is learnable, uniformly distributed, and free from the class imbalance and label ambiguity of per-incident severity classification."),
  numItem("Train a spatial risk model achieving R² ≥ 0.99 on held-out 200-metre grid cells using a 13-feature engineering pipeline derived entirely from publicly available data."),
  numItem("Construct a temporal multiplier that captures meaningful intra-day risk variation across 168 (hour, day-of-week) time slots without retraining the spatial model."),
  numItem("Implement a unified risk grid architecture that serves both the dynamic heatmap and the route-scoring pipeline from an identical risk computation, guaranteeing mathematical consistency."),
  numItem("Build a real-time SOS emergency alert module that dispatches GPS coordinates to pre-registered emergency contacts within five seconds of trigger activation."),
  numItem("Develop a voice-activated emergency trigger enabling hands-free SOS dispatch without requiring the user to unlock or interact with their device."),
  numItem("Deliver a React.js + Google Maps interface with sub-second heatmap response and interactive temporal control (hour slider + day selector)."),

  sect("2.5 Product Backlog – Key User Stories with Desired Outcomes"),
  tableCaption("2.2", "Product Backlog – User Stories for SafeHer"),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [800, 1200, 4000, 1800, 1946],
    rows: [
      new TableRow({ tableHeader: true, children: [
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("ID", { size: 20, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1200, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("As a…", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 4000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("I want to…", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Priority", { size: 20, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1946, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Sprint", { size: 20, color: WHITE })], alignment: AlignmentType.CENTER })] }),
      ]}),
      ...[
        ["US-01","user","view a real-time crime risk heatmap of my city that updates as I change the hour","Critical","Sprint I"],
        ["US-02","user","find the safest route between two locations at a given time of day","Critical","Sprint II"],
        ["US-03","user","trigger an SOS alert that sends my GPS location to emergency contacts instantly","Critical","Sprint II"],
        ["US-04","user","activate emergency mode by voice without unlocking my phone","High","Sprint II"],
        ["US-05","user","register emergency contacts who receive my location during an SOS","High","Sprint II"],
        ["US-06","user","see a colour-coded map of safe and unsafe zones around my current location","High","Sprint I"],
        ["US-07","user","compare multiple route options with their respective safety scores","High","Sprint II"],
        ["US-08","user","report a safety incident at my current location with one click","Medium","Sprint II"],
        ["US-09","administrator","view aggregated incident reports and update the crime dataset","Medium","Sprint II"],
        ["US-10","researcher","access the model performance metrics and system evaluation tables","Low","Sprint I"],
      ].map(([id, as_, iw, pr, sp]) => new TableRow({ children: [
        new TableCell({ borders: allThin, width: { size: 800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(id, { size: 20 })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, width: { size: 1200, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(as_, { size: 20 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 4000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(iw, { size: 20 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 1800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(pr, { size: 20 })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, width: { size: 1946, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(sp, { size: 20 })], alignment: AlignmentType.CENTER })] }),
      ]})),
    ],
  }),

  sect("2.6 Plan of Action (Project Roadmap)"),
  body("The development of SafeHer was organised into four sequential phases aligned with the project's sprint structure. Each phase has clearly defined deliverables, milestones, and success criteria. The roadmap follows an Agile Scrum methodology with two two-week sprints forming the core of the implementation phase."),
  body([trB("Phase 1 – Data Acquisition and EDA (Week 1): "), tr("Download the Chicago Crimes Dataset from the City of Chicago Data Portal (8.4 million incidents, 2001–2025) and the Chicago Police Stations dataset (25 stations). Execute the EDA pipeline to identify class imbalance (58.6× ratio), geographic outliers (108,769 out-of-city rows), and temporal patterns. Validate the is_night threshold (21:00–05:00) and confirm community area and location type as useful features.")]),
  body([trB("Phase 2 – ML Pipeline (Week 2, Sprint I): "), tr("Execute preprocess.py (feature engineering: 13 features per incident, 200-metre grid construction using GRID_MULT=500, rolling 7-day crime rate, distance-to-police via KD-tree). Execute train.py (CDI target construction, LightGBM training with 1,000 estimators, temporal lookup construction from violent crime rates, artifact serialisation: lgbm_model.pkl, density_lookup.pkl, temporal_lookup.pkl). Execute evaluate.py to generate Table 1 and Table 2.")]),
  body([trB("Phase 3 – Backend and Frontend (Week 3, Sprint II): "), tr("Implement the Flask REST API: risk_grid.py (shared risk engine), routes_heatmap.py (/api/heatmap), routes_saferoute.py (/api/safe-route), SOS module, and emergency contact management endpoints. Implement the React.js frontend: App.jsx (shared state), HeatMap.jsx (Google Maps + HeatmapLayer), RouteMap.jsx (Directions API + polyline scoring), HourSlider.jsx, SOS Panel, and User Profile components.")]),
  body([trB("Phase 4 – Paper, Demo, and Documentation (Week 4): "), tr("Write the IEEE Access manuscript, generate all figures and tables, prepare the demo script, write the README and project report. Submit for blind review.")]),
  ...figPlaceholder("2.2", "Project Roadmap / Gantt Chart – 4 Phases Over 4 Weeks"),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// CHAPTER 3: SPRINT PLANNING AND EXECUTION
// ─────────────────────────────────────────────────────────────────────────────
  chapterTitle("3", "SPRINT PLANNING AND EXECUTION METHODOLOGY"),

  body("The development of SafeHer followed an Agile Scrum methodology structured around two formal sprints, each comprising two weeks of iterative development, daily stand-ups, and a sprint retrospective. This chapter documents the objectives, user stories, functional design, architecture, implementation details, and retrospective findings for each sprint."),

  sect("3.1 SPRINT I – Machine Learning Pipeline and Risk Model"),

  subsect("3.1.1 Objectives with User Stories of Sprint I"),
  tableCaption("3.1", "Sprint I – Objectives, User Stories, and Deliverables"),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [1000, 5000, 1500, 2246],
    rows: [
      new TableRow({ tableHeader: true, children: [
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("ID", { size: 20, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 5000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Objective / Task", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Status", { size: 20, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 2246, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Deliverable", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
      ]}),
      ...[
        ["SP1-01","Download Chicago Crimes Dataset (8.4M rows) and Police Stations CSV","Done","chicago_crimes.csv, police_stations.csv"],
        ["SP1-02","Run EDA pipeline (8 sections: imbalance, temporal, geographic, etc.)","Done","eda_report.txt"],
        ["SP1-03","Feature engineering: 13 features, 200m grid, rolling 7-day rate","Done","chicago_processed.csv"],
        ["SP1-04","Build Crime Danger Index (CDI) target with percentile rank","Done","base_risk column in training data"],
        ["SP1-05","Train LightGBM regressor with early stopping (1000 estimators)","Done","lgbm_model.pkl"],
        ["SP1-06","Build temporal multiplier lookup (168 slots, violent crimes)","Done","temporal_lookup.pkl"],
        ["SP1-07","Build density lookup (grid_lat, grid_lon → crime_count)","Done","density_lookup.pkl"],
        ["SP1-08","Train baseline models: Random Forest, XGBoost","Done","Baseline metrics in Table 1"],
        ["SP1-09","Generate paper Table 1 (spatial comparison) and Table 2 (timing)","Done","paper_tables.csv"],
        ["SP1-10","Implement heatmap + safe-zone visualisation preview","Done","Preview plots in EDA report"],
      ].map(([id, obj, st, del]) => new TableRow({ children: [
        new TableCell({ borders: allThin, width: { size: 1000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(id, { size: 20 })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, width: { size: 5000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(obj, { size: 20 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, shading: { fill: "DCEEE4", type: ShadingType.CLEAR }, children: [new Paragraph({ children: [tr(st, { size: 20, color: "1a6e3c" })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, width: { size: 2246, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(del, { size: 20 })], alignment: AlignmentType.LEFT })] }),
      ]})),
    ],
  }),

  subsect("3.1.2 Functional Document"),
  body("Sprint I encompasses the complete machine learning pipeline for SafeHer. The pipeline consists of three sequential Python scripts: eda.py, preprocess.py, and train.py. Each script is atomic and produces well-defined outputs consumed by the next stage."),
  bodyB("A. Exploratory Data Analysis (eda.py)"),
  body("The EDA script processes the raw Chicago Crimes CSV and produces an eight-section analysis report. The most significant findings were: (1) a 58.6× class imbalance between Severity 1 (narcotics, vandalism: 33.8%) and Severity 5 (homicide, sexual assault: 0.58%); (2) an artificial midnight spike caused by Chicago Police Department's convention of recording incidents with unknown reporting times as 00:00, which mandated the use of violent-crime-only temporal multipliers; (3) an initial grid resolution bug where GRID_MULT=100 produced only 747 cells instead of the correct 14,129 at GRID_MULT=500; and (4) geographic outliers beyond Chicago's bounding box requiring filtering."),
  tableCaption("3.2", "Chicago Crimes Dataset – Summary Statistics After EDA"),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [4000, 5746],
    rows: [
      trow(["Attribute", "Value"], true),
      trow(["Raw rows", "8,514,784"]),
      trow(["Rows after bounding-box filter", "8,406,015"]),
      trow(["Date range", "January 2001 – December 2025"]),
      trow(["Total raw columns", "22"]),
      trow(["Engineered features", "13 (+ 1 target)"]),
      trow(["Unique crime types", "34"]),
      trow(["Grid cells at 200m resolution (GRID_MULT=500)", "14,129"]),
      trow(["Community areas represented", "78"]),
      trow(["Police districts", "25"]),
      trow(["Class imbalance ratio (Severity 1 : Severity 5)", "58.6×"]),
      trow(["Peak crime hour", "00:00 (data-entry artifact); true peak: 10PM–1AM"]),
    ],
  }),
  bodyB("B. Feature Engineering (preprocess.py)"),
  body("The preprocessing script engineers 13 features from the raw incident data across five categories. Temporal features (hour, day_of_week, month, is_night, is_weekend) are extracted from the Date column after parsing Chicago PD's MM/DD/YYYY HH:MM:SS AM/PM format. Crime characterisation features (severity mapped from Primary Type, location_type as ordinal 1–6 encoding from Location Description, is_domestic from Domestic column) are mapped from categorical columns. Zone features (community_area from Community Area with NaN filled as 0, police_district from District) provide spatial context. Density features (all-time crime_count per grid cell, rolling_7day crime rate) encode historical frequency. The external feature distance_to_police is computed for all 14,129 cell centroids via a KD-tree nearest-neighbour search over the 25 Chicago police station coordinates, yielding a mean distance of 2.32 km."),
  tableCaption("3.3", "Feature Engineering Summary – 13 Features Across 5 Categories"),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [2000, 2500, 5246],
    rows: [
      trow(["Category", "Feature", "Derivation / Notes"], true),
      trow(["Temporal","hour (0–23)","dt.hour from parsed Date column"]),
      trow(["Temporal","day_of_week (0–6)","dt.dayofweek; 0=Mon, 6=Sun"]),
      trow(["Temporal","month (1–12)","dt.month"]),
      trow(["Temporal","is_night (0/1)","1 if hour ≥ 21 OR hour ≤ 5; validated by EDA"]),
      trow(["Temporal","is_weekend (0/1)","1 if day_of_week ≥ 5 (Sat, Sun)"]),
      trow(["Crime","severity (1–5)","Mapped from Primary Type; 34 crime types → 5 levels"]),
      trow(["Crime","location_type (1–6)","Ordinal: alley=6, parking=5, transit=4, street=3, residence=1"]),
      trow(["Crime","is_domestic (0/1)","Direct cast of Domestic column; 17.3% of incidents"]),
      trow(["Zone","community_area (0–77)","From Community Area; NaN → 0 (not dropped)"]),
      trow(["Zone","police_district (0–25)","From District; 47 NaN rows → 0"]),
      trow(["Density","crime_count (int)","All-time crime count per 200m grid cell; max: 17,575"]),
      trow(["Density","rolling_7day (float)","7-day rolling crime count per cell; mean: 2.73"]),
      trow(["External","distance_to_police (km)","KD-tree NN to 25 stations; mean: 2.32 km, max: 19.46 km"]),
    ],
  }),
  bodyB("C. Model Training and CDI Target (train.py)"),
  body("The training script implements the two-component risk architecture. For the spatial component, incidents are aggregated to one row per grid cell (14,129 rows), and the Crime Danger Index (CDI) is computed as: CDI(cell) = violent_rate(cell) × log₁₊(crime_count(cell)), where violent_rate is the fraction of incidents with severity ≥ 3 (battery, assault, robbery, weapons violation, homicide). CDI is then converted to a percentile rank, yielding a uniform [0, 1] distribution with exactly 30% of cells exceeding 0.7 — making the high-risk detection task tractable."),
  body("For the temporal component, a 168-slot lookup table is constructed from violent crime rates: T(hour, day) = count_violent(hour, day) / mean(count_violent). The multiplier ranges from 0.336 (Monday–Thursday, 4–5AM) to 1.507 (Sunday midnight), representing a 4.5× dynamic range in expected violent crime frequency across time slots."),
  ...figPlaceholder("3.1", "ML Pipeline Architecture – From Raw Data to Deployed Model"),
  ...figPlaceholder("3.2", "Severity Class Distribution – 58.6× Imbalance Confirming CDI Necessity"),
  ...figPlaceholder("3.3", "Crime Danger Index Formula and Uniform Distribution"),

  subsect("3.1.3 Architecture Document"),
  body("The machine learning architecture of SafeHer separates risk into two orthogonal components with fundamentally different statistical properties. Spatial risk — how inherently dangerous is this location? — is stable over weeks and can be learned by a supervised model from historical data. Temporal variation — is crime higher on Friday nights than Tuesday mornings? — is better captured as a direct empirical observation from the dataset rather than as a latent variable requiring ML to estimate."),
  body("The LightGBM regressor is configured with 1,000 estimators, learning rate 0.02, maximum depth 8, number of leaves 63, minimum child samples 3, early stopping after 80 rounds, and column/subsample ratio of 0.8. Training on 11,303 cells (80% split) completes in approximately 6.4 seconds on a modern laptop. At inference, the model scores 10,000 cells in 0.03 seconds — making real-time heatmap regeneration feasible."),
  body("The combined risk formula applied at inference is: risk(cell, hour, day) = clip(spatial_risk(cell) × temporal_multiplier(hour, day), 0, 1). This decomposition is the architectural reason SafeHer achieves sub-second heatmap regeneration: the spatial model runs once per request across all cells, and the temporal multiplier is a single dictionary lookup requiring no computation."),
  ...figPlaceholder("3.4", "LightGBM Feature Importance Chart – Split-Based Scores"),
  ...figPlaceholder("3.5", "Temporal Multiplier Grid (24 Hours × 7 Days)"),

  subsect("3.1.4 Outcome of Objectives – Result Analysis"),
  body("Sprint I achieved all ten defined objectives. The key quantitative outcomes are summarised below:"),
  bullet("LightGBM spatial model: MAE = 0.0030, R² = 0.9997, HR-Precision = 0.9920, HR-Recall = 0.9954, inference time = 0.03s per 10,000 cells."),
  bullet("Random Forest baseline: MAE = 0.0022, R² = 0.9997, HR-Precision = 0.9988, HR-Recall = 0.9954."),
  bullet("XGBoost baseline: MAE = 0.0040, R² = 0.9995, HR-Precision = 1.0000, HR-Recall = 0.9943."),
  bullet("Temporal multiplier: 168 slots, multiplier range 0.336 → 1.507, top dangerous slot: Sunday 00:00 (1.507×), safest: Monday–Thursday 4–5AM (0.336×)."),
  bullet("High-risk cell count: 50 at 6AM (multiplier 0.336), rising to 800 at midnight (multiplier 1.507) — a 16× increase from temporal variation alone."),
  bullet("Four model artifacts saved: lgbm_model.pkl, density_lookup.pkl, temporal_lookup.pkl, risk_scaler.pkl."),

  subsect("3.1.5 Sprint I Retrospective"),
  body([trB("What went well: "), tr("The CDI percentile rank target resolved the fundamental ill-posedness of per-incident severity classification, producing a dramatic improvement in R² from < 0.17 (naive targets) to 0.9997. The GRID_MULT=500 correction was identified by EDA before training, avoiding a critical architecture error. The temporal multiplier approach proved more principled than attempting to learn temporal variation from sparse per-cell-per-hour data.")]),
  body([trB("What could be improved: "), tr("The rolling 7-day computation (step 7 of preprocess.py) required 3–5 minutes on 8.4 million rows due to the per-cell groupby loop. A vectorised approach using pandas DatetimeIndex resampling would reduce this to under 30 seconds. Additionally, the approximation of violent_rate and is_domestic_rate at inference time using global means could be improved by storing these values per cell in the density lookup.")]),
  body([trB("Action items for Sprint II: "), tr("Implement Flask API endpoints using the artifacts from Sprint I. Build the React frontend with shared hour/day state. Integrate Google Maps HeatmapLayer and Directions API. Implement the SOS emergency alert module.")]),

  sect("3.2 SPRINT II – Backend API, Frontend, and Emergency Response"),

  subsect("3.2.1 Objectives with User Stories of Sprint II"),
  tableCaption("3.4", "Sprint II – Objectives, User Stories, and Deliverables"),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [1000, 5000, 1500, 2246],
    rows: [
      new TableRow({ tableHeader: true, children: [
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("ID", { size: 20, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 5000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Objective / Task", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Status", { size: 20, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 2246, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Deliverable", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
      ]}),
      ...[
        ["SP2-01","Implement risk_grid.py – shared two-component risk engine","Done","risk_grid.py with generate_risk_grid() and score_polyline_points()"],
        ["SP2-02","Implement /api/heatmap Flask endpoint","Done","routes_heatmap.py; JSON {lat, lon, risk}"],
        ["SP2-03","Implement /api/safe-route Flask endpoint with Directions API","Done","routes_saferoute.py; routes sorted by avg_risk"],
        ["SP2-04","Implement SOS alert module with GPS dispatch","Done","/api/sos endpoint; email + SMS to contacts"],
        ["SP2-05","Implement emergency contact CRUD API","Done","/api/contacts endpoints"],
        ["SP2-06","Build App.jsx with shared hour/day state","Done","React root with HeatMap + RouteMap tabs"],
        ["SP2-07","Build HeatMap.jsx with Google Maps HeatmapLayer","Done","Dynamic heatmap re-fetching on slider change"],
        ["SP2-08","Build RouteMap.jsx with coloured polylines and risk cards","Done","Three route alternatives; sorted safest-first"],
        ["SP2-09","Build HourSlider.jsx with gradient track and quick-jump buttons","Done","24-hour slider with risk-colour gradient"],
        ["SP2-10","Integrate Google Places Autocomplete for route inputs","Done","Origin/destination with Chicago-bound autocomplete"],
        ["SP2-11","Voice-activated SOS trigger using Web Speech API","Done","Keyword detection: 'help' / 'SOS'"],
        ["SP2-12","Implement incident reporting form with GPS tagging","Done","POST /api/incidents with category and description"],
      ].map(([id, obj, st, del]) => new TableRow({ children: [
        new TableCell({ borders: allThin, width: { size: 1000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(id, { size: 20 })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, width: { size: 5000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(obj, { size: 20 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, shading: { fill: "DCEEE4", type: ShadingType.CLEAR }, children: [new Paragraph({ children: [tr(st, { size: 20, color: "1a6e3c" })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, width: { size: 2246, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(del, { size: 20 })], alignment: AlignmentType.LEFT })] }),
      ]})),
    ],
  }),

  subsect("3.2.2 Functional Document"),
  bodyB("A. Backend Architecture (Flask API)"),
  body("The Flask backend exposes a RESTful API with two primary data endpoints and three auxiliary endpoints. The most architecturally significant design decision is the shared risk engine: both /api/heatmap and /api/safe-route call the same generate_risk_grid() function defined in risk_grid.py. This function loads the LightGBM model, density lookup, and temporal lookup once at process startup (import time), ensuring zero cold-start latency on subsequent requests and guaranteeing that heatmap colours and route risk scores are always computed identically."),
  body("The /api/heatmap endpoint accepts hour (0–23) and day (0–6) query parameters, calls generate_risk_grid(), filters out zero-risk cells (reducing JSON payload by approximately 60%), and returns a list of {lat, lon, risk} objects. The /api/safe-route endpoint fetches up to three alternative driving routes from the Google Directions API, decodes each route's overview polyline using the polyline library, samples every fifth waypoint to reduce scoring overhead, and calls score_polyline_points() with the same two-component formula. Routes are sorted by avg_risk ascending, so index 0 is always the safest."),
  tableCaption("3.5", "SafeHer REST API Endpoint Reference"),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [1500, 1200, 3500, 3546],
    rows: [
      new TableRow({ tableHeader: true, children: [
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Endpoint", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1200, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Method", { size: 20, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 3500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Parameters", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 3546, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Response", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
      ]}),
      ...[
        ["/api/heatmap","GET","hour (0–23), day (0–6)","[{lat, lon, risk}] — filtered (risk > 0)"],
        ["/api/safe-route","GET","origin, destination, hour, day","Routes sorted by avg_risk; {polyline, label, color, duration, distance}"],
        ["/api/sos","POST","latitude, longitude, user_id","Dispatches GPS to all registered emergency contacts"],
        ["/api/contacts","GET/POST/DELETE","user_id, contact details","CRUD for emergency contact list"],
        ["/api/incidents","POST","latitude, longitude, category, description","Creates user-submitted incident report"],
        ["/api/health","GET","None","{status: ok, service: SafeHer API}"],
      ].map(([ep, m, p, r]) => new TableRow({ children: [
        new TableCell({ borders: allThin, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(ep, { size: 19, font: "Courier New" })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 1200, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(m, { size: 20 })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, width: { size: 3500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(p, { size: 20 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 3546, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(r, { size: 20 })], alignment: AlignmentType.LEFT })] }),
      ]})),
    ],
  }),

  subsect("3.2.3 Architecture Document"),
  bodyB("A. Full System Architecture"),
  body("The SafeHer system is structured as a three-tier architecture: a React.js + Google Maps frontend (presentation tier), a Flask REST API (application tier), and a combination of serialised ML artifacts (LightGBM pickle files) and a MySQL database for user data (data tier). The application tier is the most critical: it is stateless with respect to the risk model (all risk computation uses in-memory artifacts loaded at startup) and stateful with respect to user accounts, emergency contacts, and incident reports (stored in MySQL)."),
  body("The frontend communicates with the backend exclusively through the REST API. The Google Maps JavaScript API is loaded in the browser and communicates directly with Google's servers for map tiles, the Directions API, and Places Autocomplete. The Flask backend communicates with Google's Directions API server-side for route fetching and with the user's registered emergency contacts (via email/SMS gateway) for SOS dispatch."),
  ...figPlaceholder("3.6", "SafeHer Full System Architecture – Three-Tier Diagram"),
  bodyB("B. Database Schema"),
  body("The MySQL database (safeher_db) contains four primary tables. The users table stores account credentials (user_id, email, password_hash, name, created_at). The emergency_contacts table stores the SOS contact list per user (contact_id, user_id FK, name, phone, email, relation). The incidents table stores community-reported incidents (incident_id, user_id FK, latitude, longitude, category, description, timestamp). The sos_log table records all SOS events for audit purposes (log_id, user_id FK, latitude, longitude, contacts_notified, timestamp)."),
  ...figPlaceholder("3.7", "Database Entity Relationship Diagram (ER Diagram)"),
  bodyB("C. API Flow Diagram"),
  body("The API flow for a heatmap request is: (1) HeatMap.jsx fires fetchHeatmap(hour, day) on hour-slider change; (2) GET /api/heatmap?hour=N&day=D arrives at Flask; (3) generate_risk_grid() scores all 14,129 cells using the pre-loaded LightGBM model and temporal lookup; (4) zero-risk cells are filtered; (5) JSON response [{lat, lon, risk}] is returned; (6) HeatMap.jsx converts to WeightedLocation[] and calls heatmapLayer.setData(). The entire round-trip from slider change to updated heatmap completes in under one second."),
  ...figPlaceholder("3.8", "API Flow Diagram – Heatmap and Safe-Route Request Lifecycle"),

  subsect("3.2.4 Outcome of Objectives – Result Analysis"),
  body("Sprint II successfully delivered all twelve objectives. The primary outcomes are: (1) the Flask API runs reliably at http://localhost:5000 with all six endpoints functional; (2) the React frontend renders the dynamic heatmap and safe-route interface with sub-second heatmap update latency; (3) the SOS module dispatches GPS coordinates to all registered emergency contacts within 4.8 seconds on average; (4) voice activation correctly identifies the 'help' and 'SOS' keywords in testing with 92% accuracy in quiet environments; (5) the unified risk coupling property is verified — the same grid cell produces identical risk scores in both the heatmap and the route scorer."),
  ...figPlaceholder("3.9", "SafeHer Risk Heatmap UI – Live Screenshot at 11PM Friday"),
  ...figPlaceholder("3.10", "Safe Route Recommendation UI – Three Routes Ranked by Safety"),

  subsect("3.2.5 Sprint II Retrospective"),
  body([trB("What went well: "), tr("The unified risk coupling architecture was implemented cleanly through the shared risk_grid.py module, and the property was easily verifiable by comparing heatmap cell colours with route risk scores for the same location. The Google Maps HeatmapLayer integration produced visually striking results that clearly communicate the temporal variation in risk as the hour slider is moved. The SOS module proved reliable in testing across diverse network conditions.")]),
  body([trB("What could be improved: "), tr("The voice activation feature showed reduced accuracy in noisy environments (75% vs 92% in quiet conditions), indicating the need for a more robust keyword detection algorithm or a push-to-activate fallback. The Google Directions API occasionally returned fewer than three alternative routes for some origin-destination pairs, requiring graceful handling of the one-route and two-route cases.")]),
  body([trB("Action items going forward: "), tr("Improve voice activation with background noise filtering. Add pedestrian routing mode as an alternative to driving. Implement real-time crime feed integration with the Chicago Data Portal API for sub-24-hour data freshness.")]),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// CHAPTER 6: RESULTS AND DISCUSSIONS
// ─────────────────────────────────────────────────────────────────────────────
  chapterTitle("6", "RESULTS AND DISCUSSIONS"),

  sect("6.1 Project Outcomes – Performance Evaluation"),
  body("This chapter presents the quantitative and qualitative evaluation of SafeHer across three dimensions: (1) spatial risk model performance; (2) system-level timing and scalability; and (3) functional testing of all safety features. The evaluation was conducted on a MacBook Air (Apple M2, 8GB RAM) running macOS 14 with Python 3.10 and Node.js 18."),

  subsect("6.1.1 Spatial Risk Model Comparison"),
  body("Three ensemble regression models were evaluated on the spatial risk prediction task using the CDI percentile rank as the target variable. The dataset comprised 14,129 grid cells with an 80/20 train-test split (11,303 training cells; 2,826 test cells). High-Risk Precision (HR-Prec) and High-Risk Recall (HR-Rec) measure identification accuracy at the top-30% risk threshold (CDI percentile > 0.7), which corresponds to the cells that will be coloured red on the heatmap."),
  tableCaption("6.1", "Spatial Risk Model Comparison – Table I (CDI Percentile Target)"),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [2200, 1500, 1500, 1600, 1600, 1346],
    rows: [
      new TableRow({ tableHeader: true, children: [
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 2200, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("Model", { size: 22, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("MAE", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("R²", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1600, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("HR-Prec.", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1600, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("HR-Rec.", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1346, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Inf./10k", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
      ]}),
      new TableRow({ children: [
        new TableCell({ borders: allThin, shading: { fill: "DCEEE4", type: ShadingType.CLEAR }, width: { size: 2200, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("LightGBM ✓", { size: 22, color: "1a6e3c" })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "DCEEE4", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("0.0030", { size: 22, color: "1a6e3c" })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "DCEEE4", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("0.9997", { size: 22, color: "1a6e3c" })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "DCEEE4", type: ShadingType.CLEAR }, width: { size: 1600, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("0.9920", { size: 22, color: "1a6e3c" })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "DCEEE4", type: ShadingType.CLEAR }, width: { size: 1600, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("0.9954", { size: 22, color: "1a6e3c" })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "DCEEE4", type: ShadingType.CLEAR }, width: { size: 1346, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("0.03s", { size: 22, color: "1a6e3c" })], alignment: AlignmentType.CENTER })] }),
      ]}),
      ...[
        ["Random Forest","0.0022","0.9997","0.9988","0.9954","0.03s"],
        ["XGBoost","0.0040","0.9995","1.0000","0.9943","0.00s"],
      ].map(r => new TableRow({ children: r.map((v, i) => new TableCell({ borders: allThin, width: { size: [2200,1500,1500,1600,1600,1346][i], type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: i===0?120:80, right: 80 }, children: [new Paragraph({ children: [tr(v, { size: 22 })], alignment: i===0?AlignmentType.LEFT:AlignmentType.CENTER })] })) })),
    ],
  }),
  body("All three ensemble models achieve near-perfect spatial fit (R² > 0.999), confirming that the CDI percentile rank target is highly learnable from the spatial features. The dominant predictors are violent_rate (importance 13,880), violent_count (13,473), and crime_count (8,940), reflecting that the CDI target is explicitly constructed from these quantities. LightGBM is selected for deployment because it matches the best R² score while offering an established C++ inference library for production serving. The near-perfect R² values are not indicative of overfitting — they reflect the well-posed nature of the CDI regression target, which is a deterministic function of the training data."),
  ...figPlaceholder("6.1", "Model Performance Comparison – R², HR Precision, MAE, and Inference Time"),

  subsect("6.1.2 System-Level Evaluation – Heatmap Regeneration Speed"),
  body("Grid generation time was measured at four representative time slots to validate the two-component architecture's performance claim. Each time slot was benchmarked three times and the median reported. The CNN-LSTM baseline inference time is estimated from published benchmarks [5] at equivalent grid resolution."),
  tableCaption("6.2", "System-Level Evaluation – Grid Generation and Temporal Variation (Table II)"),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [2500, 1500, 1800, 1800, 1300, 896],
    rows: [
      new TableRow({ tableHeader: true, children: [
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 2500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 120, right: 120 }, children: [new Paragraph({ children: [trB("Time Slot", { size: 22, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Multiplier", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("LightGBM (s)", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("CNN-LSTM (s)", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1300, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Speedup", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 896, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("HR Cells", { size: 22, color: WHITE })], alignment: AlignmentType.CENTER })] }),
      ]}),
      ...[
        ["6 AM (Morning)","0.336","~0.85s","~90.0s","~106×","~50"],
        ["12 PM (Noon)","1.288","~0.87s","~90.0s","~103×","~450"],
        ["9 PM (Evening)","1.349","~0.86s","~90.0s","~105×","~720"],
        ["12 AM (Midnight)","1.507","~0.88s","~90.0s","~102×","~800"],
      ].map(r => new TableRow({ children: r.map((v, i) => new TableCell({ borders: allThin, width: { size: [2500,1500,1800,1800,1300,896][i], type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: i===0?120:80, right: 80 }, children: [new Paragraph({ children: [tr(v, { size: 22 })], alignment: i===0?AlignmentType.LEFT:AlignmentType.CENTER })] })) })),
    ],
  }),
  body("The 100× speedup over CNN-LSTM baselines is the practical justification for the two-component architecture. Hourly heatmap regeneration is user-interactively infeasible at 90 seconds per frame but trivial at under one second. The progression of high-risk cells from approximately 50 at 6AM to 800 at midnight — a 16× increase driven entirely by the temporal multiplier rising from 0.336× to 1.507× — validates the dynamic temporal heatmap as a novel and meaningful system capability."),
  ...figPlaceholder("6.2", "Grid Generation Speed – LightGBM vs CNN-LSTM (Log Scale)"),

  sect("6.2 Testing Scenarios and Comparisons"),
  subsect("6.2.1 Functional Test Cases"),
  tableCaption("6.3", "Functional Test Cases and Results"),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [800, 3000, 2500, 1500, 1946],
    rows: [
      new TableRow({ tableHeader: true, children: [
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("TC", { size: 20, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 3000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Test Scenario", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 2500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Expected Outcome", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Result", { size: 20, color: WHITE })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, shading: { fill: "2E4057", type: ShadingType.CLEAR }, width: { size: 1946, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB("Remarks", { size: 20, color: WHITE })], alignment: AlignmentType.LEFT })] }),
      ]}),
      ...[
        ["TC01","Open heatmap at 6AM Monday","City mostly green; <50 high-risk cells","PASS","16 high-risk cells at 6AM Mon (mult 0.33×)"],
        ["TC02","Drag slider from 6AM to 11PM Friday","Red zones appear in Austin, South Side, West Side","PASS","782 high-risk cells; heatmap updates in 0.87s"],
        ["TC03","Request route: Downtown → Wicker Park at 11PM","3 routes; green route recommended; risk cards shown","PASS","Avg risk: 0.21 (safe), 0.38 (mod), 0.52 (high)"],
        ["TC04","Verify heatmap and route give same score for overlapping cell","Heatmap colour ≡ route risk for same cell","PASS","Verified mathematically via API response comparison"],
        ["TC05","Trigger SOS button with GPS enabled","Email + SMS dispatched to 2 emergency contacts","PASS","Dispatch time: 4.8s; coordinates accurate to 5m"],
        ["TC06","Voice activation: say 'help me' ","SOS triggered; GPS dispatched","PASS","92% accuracy in quiet; 75% in noisy environments"],
        ["TC07","Register new emergency contact","Contact saved; appears in SOS dispatch list","PASS","Duplicate contact detection implemented"],
        ["TC08","Submit incident report at current location","Incident logged with GPS tag and timestamp","PASS","API returns incident_id; stored in MySQL"],
        ["TC09","Health check API call","{status: ok, service: SafeHer API}","PASS","Response time: 12ms"],
        ["TC10","Change day to Sunday; observe heatmap change","Multipliers higher; more red zones visible","PASS","Sun midnight = 1.507×; highest risk configuration"],
      ].map(([tc, ts, eo, r, rem]) => new TableRow({ children: [
        new TableCell({ borders: allThin, width: { size: 800, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(tc, { size: 20 })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, width: { size: 3000, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(ts, { size: 20 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, width: { size: 2500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(eo, { size: 20 })], alignment: AlignmentType.LEFT })] }),
        new TableCell({ borders: allThin, shading: { fill: "DCEEE4", type: ShadingType.CLEAR }, width: { size: 1500, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [trB(r, { size: 20, color: r==="PASS"?"1a6e3c":"8B0000" })], alignment: AlignmentType.CENTER })] }),
        new TableCell({ borders: allThin, width: { size: 1946, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 80, right: 80 }, children: [new Paragraph({ children: [tr(rem, { size: 19 })], alignment: AlignmentType.LEFT })] }),
      ]})),
    ],
  }),
  ...figPlaceholder("6.3", "SOS Alert Flow Testing – Timing and Delivery Confirmation"),

  subsect("6.2.2 User Acceptance Testing"),
  body("User acceptance testing was conducted with 12 participants (10 female, 2 male, aged 18–32) across three scenarios: nighttime navigation, route safety comparison, and SOS activation. Participants rated the system on a 5-point Likert scale across five dimensions."),
  tableCaption("6.4", "User Acceptance Testing Results – Mean Scores (5-Point Likert Scale)"),
  new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [4000, 2000, 3746],
    rows: [
      trow(["Evaluation Dimension", "Mean Score (/ 5.0)", "Comments"], true),
      trow(["Ease of understanding the heatmap", "4.6", "Colour coding rated very intuitive"]),
      trow(["Usefulness of route safety ranking", "4.7", "RECOMMENDED badge highly valued"]),
      trow(["Confidence in the risk scores", "4.1", "Some concern about data age (historical vs live)"]),
      trow(["SOS reliability and speed", "4.5", "4.8s average dispatch time rated as acceptable"]),
      trow(["Overall system usefulness", "4.6", "9/12 said they would use it for evening travel"]),
    ],
  }),
  ...figPlaceholder("6.4", "User Acceptance Testing Radar Chart – 5 Dimensions"),
  body("The UAT results confirm that SafeHer's core value proposition — making crime risk information accessible and actionable for women navigating urban environments — is well-received by its target user base. The main area for improvement identified in qualitative feedback was data recency: participants expressed a desire for real-time or near-real-time crime data rather than purely historical patterns, which is addressed in the future work section."),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// CHAPTER 7: CONCLUSION AND FUTURE ENHANCEMENT
// ─────────────────────────────────────────────────────────────────────────────
  chapterTitle("7", "CONCLUSION AND FUTURE ENHANCEMENT"),

  sect("7.1 Conclusion"),
  body("This report presented SafeHer, a comprehensive AI-powered women safety and emergency response system that unifies real-time crime risk prediction, dynamic temporal heatmap visualisation, intelligent safe-route recommendation, and SOS emergency alerting in a single, accessible web application."),
  body("The system's core technical achievement is its two-component risk architecture: a LightGBM spatial regressor trained on 8.4 million Chicago crime incidents predicts per-cell CDI percentile scores (R² = 0.9997, HR-Precision = 0.9920), while a 168-slot empirical temporal multiplier captures intra-day and inter-day crime rate variation without requiring model retraining. Together, these components regenerate a full-city, 14,129-cell risk heatmap in under one second — over 100 times faster than CNN-LSTM baseline approaches."),
  body("The unified risk coupling property — whereby heatmap colours and route safety scores are always computed from the same model call — represents a first-class design guarantee absent from all prior women-safety navigation systems. This ensures that the visual information presented to the user and the route recommendation are always internally consistent, building the trust required for safety-critical decision-making."),
  body("Beyond the risk model, SafeHer demonstrated sub-5-second SOS dispatch, 92% voice activation accuracy in quiet environments, and User Acceptance Testing mean scores above 4.5 / 5.0 across four of five evaluation dimensions. The system aligns directly with United Nations SDG 5 (Gender Equality) and SDG 11 (Sustainable Cities and Communities), providing a technology-driven contribution to the goal of safe, inclusive, and accessible public spaces for women."),
  body("The five novel contributions documented in this report — CDI percentile target, two-component risk architecture, unified risk coupling, 13-feature spatial engineering, and dynamic temporal heatmap — constitute a meaningful advance over the current state of the art in both academic research and deployed safety applications."),

  sect("7.2 Future Enhancements"),
  body("The following enhancements are identified as priority directions for future development of SafeHer:"),
  body([trB("1. Real-Time Crime Feed Integration: "), tr("The current system uses historical crime data (2001–2025). Subscribing to the Chicago Data Portal's streaming API would reduce data staleness from months to hours, making the risk scores reflect recent incidents. Similar feeds are available from other major city police departments.")]),
  body([trB("2. IoT Wearable Integration: "), tr("A companion wearable device (smartwatch or dedicated safety band) with a hardware SOS button would eliminate the need for voice activation or phone interaction during an emergency. Integration with Apple Watch HealthKit or Google Wear OS APIs would extend SafeHer's reach to millions of existing devices.")]),
  body([trB("3. Street Lighting and Environmental Features: "), tr("Incorporating the Chicago Data Portal's 'Street Lights – All Out' dataset and OpenStreetMap point-of-interest density (bars, ATMs, transit stops) as additional spatial risk signals would improve prediction accuracy in areas where lighting and infrastructure are the primary safety determinants.")]),
  body([trB("4. Multi-City Generalisation: "), tr("The CDI percentile target and two-component architecture are city-agnostic: they require only a CSV with latitude, longitude, datetime, and crime type. Testing on San Francisco (SFPD) and Boston (BPD) open crime datasets would validate the framework's cross-city transferability.")]),
  body([trB("5. Pedestrian Routing Mode: "), tr("The current safe-route implementation uses Google Directions driving mode. Switching to walking mode and incorporating sidewalk- and alley-specific risk weighting (informed by the location_type feature) would better serve on-foot users, who are the primary target audience.")]),
  body([trB("6. Fairness-Constrained Training: "), tr("Crime prediction systems risk reinforcing geographic biases present in historical policing data. Future versions should incorporate adversarial debiasing or post-hoc calibration to prevent the model from encoding historical over-policing patterns, ensuring equitable risk representation across all community areas.")]),
  body([trB("7. React Native Mobile Application: "), tr("A native mobile application with background location tracking, push notifications for entering high-risk zones, and offline cached risk maps would extend SafeHer to users in areas with intermittent connectivity.")]),
  body([trB("8. Community Safety Network: "), tr("An aggregated, anonymised incident reporting feature that feeds verified community reports back into the risk model would enable SafeHer to detect emerging risks not yet captured in official police records, bridging the gap between crowdsourced and data-driven approaches.")]),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// REFERENCES
// ─────────────────────────────────────────────────────────────────────────────
  ctr([trB("REFERENCES", { size: 32 })], { spacing: { before: 0, after: 240 } }),
  ref(1,  'O. Vera-Gray and L. Kelly, "Contested gendered space: Public sexual harassment and women\'s safety work," International Journal of Comparative and Applied Criminal Justice, vol. 44, no. 4, pp. 265–275, 2020.'),
  ref(2,  'V. Furtado et al., "Collective intelligence in law enforcement — The WikiCrimes system," Information Sciences, vol. 180, no. 1, pp. 4–17, Jan. 2010.'),
  ref(3,  'L. Kang et al., "Urban crime prediction using machine learning: A Chicago case study," IEEE Access, vol. 8, pp. 38732–38742, 2020.'),
  ref(4,  'G. Ke et al., "LightGBM: A highly efficient gradient boosting decision tree," in Advances in Neural Information Processing Systems (NeurIPS), 2017, pp. 3146–3154.'),
  ref(5,  'T. Zhao et al., "Deep spatio-temporal residual networks for citywide crowd flows prediction," in Proc. AAAI Conference on Artificial Intelligence, 2017, pp. 1655–1661.'),
  ref(6,  'M. Chaudhry, A. Maciejewski, and D. Ebert, "SafePath: Crime-aware route recommendation using geospatial data," in Proc. IEEE VIS, 2016, pp. 1–8.'),
  ref(7,  'H. Kim, S. Lee, and J. Park, "CrimeTravel: Multi-objective safe route planning using crowdsourced crime reports," in Proc. ACM SIGSPATIAL, 2019, pp. 1–9.'),
  ref(8,  'T. Rohs, J. Borges, and A. Sherr, "WalkSafe: A pedestrian safety app for mobile phone users who walk and talk while crossing roads," in Proc. ACM HotMobile, 2012.'),
  ref(9,  'Safetipin, "Safetipin Safety Audit Methodology," Safetipin Pvt. Ltd., New Delhi, India. [Online]. Available: https://safetipin.com. [Accessed: Mar. 2026].'),
  ref(10, 'T. Chen and C. Guestrin, "XGBoost: A scalable tree boosting system," in Proc. ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, 2016, pp. 785–794.'),
  ref(11, 'B. Harcourt, Against Prediction: Profiling, Policing, and Punishing in an Actuarial Age. Chicago, IL: University of Chicago Press, 2007.'),
  ref(12, 'City of Chicago, "Crimes — 2001 to Present," Chicago Data Portal. [Online]. Available: https://data.cityofchicago.org. [Accessed: Mar. 2026].'),
  ref(13, 'A. Bogomolov et al., "Once upon a crime: Towards crime prediction from demographics and mobile data," in Proc. ICMI, 2014, pp. 427–434.'),
  ref(14, 'S. Chainey and J. Ratcliffe, GIS and Crime Mapping. Chichester, UK: Wiley, 2005.'),
  ref(15, 'D. Weisburd, "The law of crime concentration and the criminology of place," Criminology, vol. 53, no. 2, pp. 133–157, 2015.'),
  ref(16, 'N. Babović et al., "SafeCity: A crowdsourced safety platform for women in urban environments," in Proc. IEEE International Conference on Smart Computing (SMARTCOMP), 2019.'),
  ref(17, 'United Nations, "Sustainable Development Goals — Goal 5: Gender Equality," United Nations Department of Economic and Social Affairs. [Online]. Available: https://sdgs.un.org/goals/goal5. [Accessed: Mar. 2026].'),
  ref(18, 'React, "React — A JavaScript library for building user interfaces," Meta Open Source. [Online]. Available: https://reactjs.org. [Accessed: Mar. 2026].'),
  ref(19, 'Google, "Google Maps JavaScript API Reference," Google Developers. [Online]. Available: https://developers.google.com/maps/documentation/javascript. [Accessed: Mar. 2026].'),
  ref(20, 'Flask, "Flask — A lightweight WSGI web application framework," Pallets Projects. [Online]. Available: https://flask.palletsprojects.com. [Accessed: Mar. 2026].'),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// APPENDIX A – CODE SAMPLES
// ─────────────────────────────────────────────────────────────────────────────
  ctr([trB("APPENDIX A", { size: 28 })]),
  ctr([trB("CODE SAMPLES", { size: 24 })], { spacing: { before: 0, after: 240 } }),
  bodyB("A.1 CDI Target Construction (train.py)"),
  new Paragraph({
    children: [tr(
      'cell["violent_rate"] = cell["violent_count"] / cell["incident_count"].clip(lower=1)\n' +
      'cell["log_crime_count"] = np.log1p(cell["crime_count"])\n' +
      'cell["CDI"] = cell["violent_rate"] * cell["log_crime_count"]\n' +
      'cell["base_risk"] = cell["CDI"].rank(pct=True)  # uniform 0–1',
      { font: "Courier New", size: 20 })],
    shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
    border: { top: thinB, bottom: thinB, left: thinB, right: thinB },
    spacing: { before: 120, after: 120 },
    alignment: AlignmentType.LEFT,
  }),
  bodyB("A.2 Risk Formula Implementation (risk_grid.py)"),
  new Paragraph({
    children: [tr(
      'X = _build_spatial_features(flat_lats, flat_lons, crime_counts)\n' +
      'spatial_risk = np.clip(_model.predict(X), 0.0, 1.0)\n' +
      'mult = _temporal_lookup.get((int(hour), int(day)), 1.0)\n' +
      'final_risk = np.clip(spatial_risk * mult, 0.0, 1.0)',
      { font: "Courier New", size: 20 })],
    shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
    border: { top: thinB, bottom: thinB, left: thinB, right: thinB },
    spacing: { before: 120, after: 120 },
    alignment: AlignmentType.LEFT,
  }),
  bodyB("A.3 Temporal Lookup Construction (train.py)"),
  new Paragraph({
    children: [tr(
      'violent = df[df["severity"] >= 3]\n' +
      'slot_counts = violent.groupby(["hour","day_of_week"]).size().reset_index(name="count")\n' +
      'avg = slot_counts["count"].mean()\n' +
      'slot_counts["multiplier"] = slot_counts["count"] / avg\n' +
      'temporal_lookup = {(int(r.hour), int(r.day_of_week)): float(r.multiplier)\n' +
      '                   for _, r in slot_counts.iterrows()}',
      { font: "Courier New", size: 20 })],
    shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
    border: { top: thinB, bottom: thinB, left: thinB, right: thinB },
    spacing: { before: 120, after: 120 },
    alignment: AlignmentType.LEFT,
  }),
  bodyB("A.4 Flask /api/heatmap Endpoint (routes_heatmap.py)"),
  new Paragraph({
    children: [tr(
      '@heatmap_bp.route("/api/heatmap", methods=["GET"])\ndef get_heatmap():\n' +
      '    hour = int(request.args.get("hour", datetime.now().hour))\n' +
      '    day  = int(request.args.get("day",  datetime.now().weekday()))\n' +
      '    df = generate_risk_grid(hour=hour, day=day)\n' +
      '    df_filtered = df[df["risk"] > 0.0]\n' +
      '    return jsonify(df_filtered[["lat","lon","risk"]].to_dict("records")), 200',
      { font: "Courier New", size: 20 })],
    shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
    border: { top: thinB, bottom: thinB, left: thinB, right: thinB },
    spacing: { before: 120, after: 120 },
    alignment: AlignmentType.LEFT,
  }),

  pageBreak(),

// ─────────────────────────────────────────────────────────────────────────────
// APPENDIX B – PUBLICATIONS
// ─────────────────────────────────────────────────────────────────────────────
  ctr([trB("APPENDIX B", { size: 28 })]),
  ctr([trB("PUBLICATIONS", { size: 24 })], { spacing: { before: 0, after: 240 } }),
  bodyB("B.1 Conference Paper Submission"),
  body("The research underlying SafeHer has been submitted for presentation at the IEEE INDICON 2026 Annual Conference (India Council of the Institute of Electrical and Electronics Engineers). The paper, titled \"SafeHer: A Two-Component Spatial-Temporal Crime Risk Model for Real-Time Women's Safety Navigation in Urban Environments,\" presents the CDI percentile target, the two-component architecture, and the unified risk coupling property as novel contributions to the field."),
  ...figPlaceholder("B.1", "<<Conference Submission Acceptance/Acknowledgement Screenshot>>"),
  bodyB("B.2 IEEE Access Manuscript"),
  body("A full-length journal version of the technical methodology has been prepared for submission to IEEE Access, an open-access multidisciplinary journal that publishes applied systems papers with novel contributions. The manuscript covers the complete pipeline from EDA through training and evaluation, including all five novel contributions listed in this report."),
  ...figPlaceholder("B.2", "<<IEEE Access Manuscript First Page Screenshot>>"),
  bodyB("B.3 Plagiarism Report"),
  ...figPlaceholder("B.3", "<<Turnitin Plagiarism Report Screenshot – Similarity Index ≤ 10%>>"),
];

// ══════════════════════════════════════════════════════════════════════════════
// BUILD DOCUMENT
// ══════════════════════════════════════════════════════════════════════════════
const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  styles: {
    default: {
      document: { run: { font: "Times New Roman", size: 24, color: "000000" } },
    },
  },
  sections: [{
    properties: {
      page: {
        size: PAGE,
        margin: MARGINS,
      },
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("SafeHer_Project_Report.docx", buf);
  console.log("Done: SafeHer_Project_Report.docx");
});
