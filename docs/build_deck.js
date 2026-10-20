// GlucoTwin — editorial, hand-made deck (12 pages) -> GlucoTwin_Deck.pptx
const pptxgen = require("pptxgenjs");
const path = require("path");
const IMG = (f) => path.join(__dirname, f);
const ICON = (n) => path.join(__dirname, "img", "icons", n + "_#ffffff.png");

// ---- warm editorial palette ------------------------------------------
const C = {
  paper: "FBF6EF", ink: "221E1A", body: "3A342D", teal: "0E7C86", tealD: "0A5157",
  coral: "E05A4D", amber: "D99838", green: "1B9E77", purple: "6E5DC6",
  white: "FFFFFF", muted: "8A7F74", rule: "E3D8C8",
  hiAmber: "FBE6B8", hiCoral: "F7D4CC", hiMint: "CDEDE2",
};
const DISP = "Century Schoolbook", BODY = "Calibri";
const MX = 0.78, CW = 11.77;            // left margin / content width
const L = { x: 0.78, w: 5.55 }, R = { x: 6.95, w: 5.6 };  // 2-col grid

const p = new pptxgen();
p.defineLayout({ name: "W", width: 13.333, height: 7.5 });
p.layout = "W";
p.theme = { headFontFace: DISP, bodyFontFace: BODY };
p.author = "Team Healthcure, IIT Kanpur";
p.title = "GlucoTwin — Predictive Digital Twin for Type 2 Diabetes";

// ---- helpers ----------------------------------------------------------
const panel = (s, x, y, w, h, color) => s.addShape(p.ShapeType.rect, { x, y, w, h, fill: { color }, line: { type: "none" } });
const rule = (s, x, y, w, color, pt) => s.addShape(p.ShapeType.line, { x, y, w, h: 0, line: { color: color || C.rule, width: pt || 1 } });
const penCircle = (s, x, y, w, h, rot, color) => s.addShape(p.ShapeType.ellipse, { x, y, w, h, fill: { type: "none" }, line: { color: color || C.coral, width: 2.4 }, rotate: rot || 356 });
const penArrow = (s, x, y, w, h, rot, color) => s.addShape(p.ShapeType.line, { x, y, w, h, rotate: rot || 0, line: { color: color || C.coral, width: 2.2, endArrowType: "triangle" } });
const dot = (s, x, y, d, color) => s.addShape(p.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color }, line: { type: "none" } });
function iconDot(s, x, y, d, color, icon) { dot(s, x, y, d, color); const pad = d * 0.28; s.addImage({ path: ICON(icon), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad }); }
const kicker = (s, t, color) => s.addText(t.toUpperCase(), { x: MX, y: 0.5, w: CW, h: 0.3, fontFace: BODY, fontSize: 12.5, bold: true, color: color || C.coral, charSpacing: 3, isTextBox: true });
const title = (s, t, w) => s.addText(t, { x: MX, y: 0.82, w: w || CW, h: 0.9, fontFace: DISP, fontSize: 31, bold: true, color: C.ink, isTextBox: true });
function foot(s, n) {
  rule(s, MX, 7.08, CW, C.rule, 1);
  s.addText("GlucoTwin — Digital Twin for Type 2 Diabetes", { x: MX, y: 7.1, w: 8, h: 0.3, fontFace: BODY, fontSize: 9.5, color: C.muted, isTextBox: true });
  s.addText(String(n).padStart(2, "0") + " / 12", { x: 10.55, y: 7.1, w: 2.0, h: 0.3, fontFace: BODY, fontSize: 9.5, color: C.muted, align: "right", isTextBox: true });
}

// ======================================================================
// 1 · COVER
let s = p.addSlide(); s.background = { color: C.tealD };
s.addShape(p.ShapeType.ellipse, { x: 9.3, y: -2.2, w: 6.4, h: 6.4, fill: { color: "0C4A50" }, line: { type: "none" } });
s.addShape(p.ShapeType.ellipse, { x: 11.1, y: 4.5, w: 3.6, h: 3.6, fill: { color: C.coral, transparency: 38 }, line: { type: "none" } });
iconDot(s, MX, 0.78, 0.6, C.coral, "heartbeat");
s.addText("HAPPIEST HEALTH · DIGITAL TWIN CHALLENGE · BENGALURU 2026", { x: 1.5, y: 0.82, w: 11, h: 0.3, fontFace: BODY, fontSize: 11.5, bold: true, color: "7FB0B2", charSpacing: 2, valign: "middle", isTextBox: true, margin: 0 });
s.addText("GlucoTwin", { x: 0.73, y: 2.0, w: 11.5, h: 1.6, fontFace: DISP, fontSize: 80, bold: true, color: C.white, isTextBox: true, margin: 0 });
s.addText([
  { text: "A digital twin that predicts a dangerous blood-sugar spike ", options: { color: "DCE8E7" } },
  { text: " about an hour before it happens ", options: { color: C.ink, highlight: C.hiAmber } },
  { text: " — so a doctor can act in time.", options: { color: "DCE8E7" } },
], { x: MX, y: 3.78, w: 10.9, h: 0.9, fontFace: DISP, fontSize: 21, isTextBox: true, lineSpacingMultiple: 1.2 });
const st = [["ROC-AUC 0.95", C.amber], ["84% caught early", C.green], ["~50 min ahead", C.coral], ["95.8% clinically safe", "8FB9BB"]];
let sx = MX;
st.forEach((d) => { dot(s, sx, 5.46, 0.16, d[1]); s.addText(d[0], { x: sx + 0.26, y: 5.24, w: 2.9, h: 0.5, fontFace: BODY, fontSize: 14, bold: true, color: "EAF2F1", valign: "middle", isTextBox: true, margin: 0 }); sx += d[0].length * 0.118 + 0.55; });
rule(s, MX, 6.4, CW, "2A5A5F", 1);
s.addText("Team Healthcure · IIT Kanpur", { x: MX, y: 6.55, w: 9, h: 0.4, fontFace: BODY, fontSize: 13, italic: true, color: "9FC2C3", isTextBox: true });

// ======================================================================
// 2 · MEERA + THE BURDEN
s = p.addSlide(); s.background = { color: C.paper };
panel(s, 0, 0, 5.0, 7.5, C.coral);
s.addShape(p.ShapeType.ellipse, { x: 1.2, y: 0.95, w: 2.6, h: 2.6, fill: { color: "F7E7DD" }, line: { type: "none" } });
s.addText("M", { x: 1.2, y: 0.95, w: 2.6, h: 2.6, fontFace: DISP, fontSize: 92, bold: true, color: C.coral, align: "center", valign: "middle", isTextBox: true, margin: 0 });
s.addText("Meera R.", { x: 0.3, y: 3.75, w: 4.4, h: 0.6, fontFace: DISP, fontSize: 32, bold: true, color: C.white, align: "center", isTextBox: true });
s.addText("58 · Coimbatore, Tamil Nadu", { x: 0.3, y: 4.35, w: 4.4, h: 0.35, fontFace: BODY, fontSize: 14, color: "FBE4DC", align: "center", isTextBox: true });
[["Type 2 diabetes", "9 years"], ["HbA1c", "8.4 %"], ["Wears", "smartwatch + CGM"]].forEach((d, i) => {
  s.addText([{ text: d[0] + "   ", options: { color: "FAD9D0" } }, { text: d[1], options: { bold: true, color: C.white } }], { x: 0.3, y: 4.95 + i * 0.52, w: 4.4, h: 0.4, fontFace: BODY, fontSize: 14.5, align: "center", isTextBox: true });
});
s.addText("Illustrative persona — not a real patient", { x: 0.3, y: 6.75, w: 4.4, h: 0.3, fontFace: BODY, fontSize: 10, italic: true, color: "F6C9BF", align: "center", isTextBox: true });
// right
const RX = 5.55, RW = 7.0;
s.addText("MEET THE PATIENT", { x: RX, y: 0.62, w: RW, h: 0.3, fontFace: BODY, fontSize: 12.5, bold: true, color: C.coral, charSpacing: 3, isTextBox: true });
s.addText("Meera, and millions like her", { x: RX, y: 0.98, w: RW, h: 0.7, fontFace: DISP, fontSize: 30, bold: true, color: C.ink, isTextBox: true });
s.addText([
  { text: "Her watch and glucose sensor stream all day; her hospital holds nine years of records. ", options: { color: C.body } },
  { text: " Yet the two never talk to each other ", options: { color: C.ink, highlight: C.hiCoral } },
  { text: " — so a dangerous spike is found weeks later, after the damage.", options: { color: C.body } },
], { x: RX, y: 1.95, w: RW, h: 1.2, fontFace: DISP, fontSize: 17, lineSpacingMultiple: 1.22, isTextBox: true });
rule(s, RX, 3.5, RW, C.rule, 1.2);
s.addText("101M", { x: RX - 0.05, y: 3.65, w: 4.2, h: 1.5, fontFace: DISP, fontSize: 96, bold: true, color: C.teal, isTextBox: true, margin: 0 });
s.addText("people live with diabetes in India — the largest burden of any country on earth.", { x: RX + 3.7, y: 3.95, w: 3.3, h: 1.4, fontFace: DISP, fontSize: 16, color: C.body, lineSpacingMultiple: 1.18, isTextBox: true });
[["≈ 1 : 8,000", "endocrinologists per patient — expert time is the scarcest resource", C.amber],
 ["Reactive by default", "excursions are found after the fact, accelerating complications", C.coral]].forEach((d, i) => {
  const y = 5.45 + i * 0.75;
  dot(s, RX, y + 0.07, 0.2, d[2]);
  s.addText([{ text: d[0] + "  —  ", options: { bold: true, color: C.ink } }, { text: d[1], options: { color: C.body } }], { x: RX + 0.35, y, w: RW - 0.35, h: 0.65, fontFace: BODY, fontSize: 13.5, lineSpacingMultiple: 1.1, isTextBox: true });
});

// ======================================================================
// 3 · SOLUTION
s = p.addSlide(); s.background = { color: C.paper };
kicker(s, "Our solution", C.teal); title(s, "From reactive to proactive");
s.addText([
  { text: "GlucoTwin builds a living virtual twin of the patient and predicts a hyperglycemic excursion ", options: { color: C.body } },
  { text: " 60–120 minutes in advance.", options: { bold: true, color: C.ink, highlight: C.hiAmber } },
], { x: MX, y: 1.72, w: CW, h: 0.55, fontFace: DISP, fontSize: 18, isTextBox: true });
[["01", "Predict", "Forecasts the next hyperglycemic event before it happens — a real window to act.", C.teal],
 ["02", "Explain", "Shows the doctor the wearable and record signals behind every single alert.", C.purple],
 ["03", "Simulate", "What-if levers — walk, meds, sleep, meal — turn each prediction into an action.", C.coral]].forEach((d, i) => {
  const y = 2.78 + i * 1.4;
  s.addText(d[0], { x: MX, y, w: 1.35, h: 1.1, fontFace: DISP, fontSize: 52, bold: true, color: d[3], isTextBox: true, margin: 0 });
  s.addText(d[1], { x: 2.35, y: y + 0.06, w: 3.0, h: 0.7, fontFace: DISP, fontSize: 27, bold: true, color: C.ink, isTextBox: true });
  s.addText(d[2], { x: 5.5, y: y + 0.1, w: 7.05, h: 1.0, fontFace: BODY, fontSize: 15.5, color: C.body, lineSpacingMultiple: 1.18, isTextBox: true });
  if (i < 2) rule(s, 2.35, y + 1.22, 10.2, C.rule, 1);
});
foot(s, 3);

// ======================================================================
// 4 · FUSION
s = p.addSlide(); s.background = { color: C.paper };
kicker(s, "The fusion", C.teal); title(s, "Two data streams — and why we need both");
panel(s, MX, 1.95, 4.5, 1.7, C.hiMint);
s.addText("THE HEALTH RECORD", { x: 1.03, y: 2.12, w: 4.0, h: 0.3, fontFace: BODY, fontSize: 12, bold: true, color: C.tealD, charSpacing: 1.5, isTextBox: true });
s.addText("HbA1c · labs · medications · comorbidities (CKD) · family history", { x: 1.03, y: 2.46, w: 4.0, h: 1.0, fontFace: BODY, fontSize: 13.5, color: C.body, lineSpacingMultiple: 1.15, isTextBox: true });
panel(s, MX, 3.95, 4.5, 1.7, C.hiAmber);
s.addText("THE WEARABLE + CGM", { x: 1.03, y: 4.12, w: 4.0, h: 0.3, fontFace: BODY, fontSize: 12, bold: true, color: "8A5A18", charSpacing: 1.5, isTextBox: true });
s.addText("continuous glucose · heart rate & HRV · steps · sleep · meals, every 15 min", { x: 1.03, y: 4.46, w: 4.0, h: 1.0, fontFace: BODY, fontSize: 13.5, color: C.body, lineSpacingMultiple: 1.15, isTextBox: true });
penArrow(s, 5.35, 2.75, 1.25, 1.0, 0); penArrow(s, 5.35, 4.85, 1.25, -1.0, 0);
dot(s, 6.75, 3.3, 1.55, C.coral);
s.addText("fused", { x: 6.75, y: 3.55, w: 1.55, h: 0.5, fontFace: DISP, fontSize: 19, bold: true, color: C.white, align: "center", isTextBox: true, margin: 0 });
s.addText("one signal", { x: 6.75, y: 4.02, w: 1.55, h: 0.4, fontFace: BODY, fontSize: 11, color: "FBE4DC", align: "center", isTextBox: true, margin: 0 });
penArrow(s, 8.45, 4.08, 0.95, 0, 0);
s.addText("the twin", { x: 9.5, y: 3.75, w: 3.05, h: 0.8, fontFace: DISP, fontSize: 23, bold: true, color: C.ink, valign: "middle", isTextBox: true });
rule(s, MX, 6.05, CW, C.rule, 1.2);
s.addText([
  { text: "Why the fusion is real:  ", options: { bold: true, color: C.coral } },
  { text: "whether a meal spikes past 180 is set by a hidden state — ", options: { color: C.body } },
  { text: " anchored by the record ", options: { color: C.ink, highlight: C.hiMint } },
  { text: " and ", options: { color: C.body } },
  { text: " swinging with what only the wearable sees. ", options: { color: C.ink, highlight: C.hiAmber } },
  { text: " Neither alone is enough — our ablation proves it.", options: { color: C.body } },
], { x: MX, y: 6.22, w: CW, h: 0.8, fontFace: BODY, fontSize: 14.5, lineSpacingMultiple: 1.15, isTextBox: true });
foot(s, 4);

// ======================================================================
// 5 · ARCHITECTURE
s = p.addSlide(); s.background = { color: C.paper };
kicker(s, "Architecture", C.teal); title(s, "From two streams to a clinician's screen");
s.addImage({ path: IMG("img/architecture.png"), x: 0.55, y: 1.62, w: 12.23, h: 5.3 });

// ======================================================================
// 6 · MODEL
s = p.addSlide(); s.background = { color: C.paper };
kicker(s, "The model", C.teal); title(s, "A hybrid twin — interpretable, deep-learning ready");
[["01", "Gradient-Boosted Trees", "The deployed predictor on the fused vector: interpretable, fast, SHAP-native — chosen over a Transformer on purpose.", C.teal],
 ["02", "Optional LSTM arm", "Encodes the raw window with the record joined at the dense head — the same late-fusion idea, as a sequence model.", C.tealD],
 ["03", "Glucose forecaster", "Predicts glucose +60 min, which powers the Clarke Error Grid clinical-safety check.", C.purple],
 ["04", "Counterfactual engine", "Perturbs levers and re-scores risk — this is what makes it a twin, not a classifier.", C.coral]].forEach((d, i) => {
  const x = MX + (i % 2) * 6.1, y = 2.0 + Math.floor(i / 2) * 2.3;
  s.addText(d[0], { x, y, w: 1.1, h: 0.9, fontFace: DISP, fontSize: 44, bold: true, color: d[3], isTextBox: true, margin: 0 });
  s.addText(d[1], { x: x + 1.15, y: y + 0.05, w: 4.55, h: 0.6, fontFace: DISP, fontSize: 19, bold: true, color: C.ink, isTextBox: true });
  s.addText(d[2], { x: x + 1.15, y: y + 0.66, w: 4.55, h: 1.35, fontFace: BODY, fontSize: 13.5, color: C.body, lineSpacingMultiple: 1.2, isTextBox: true });
});
s.addText("Target: probability of glucose exceeding 180 mg/dL in the next 60–120 minutes, from the last 2 hours of fused data.",
  { x: MX, y: 6.55, w: CW, h: 0.4, fontFace: BODY, fontSize: 13, italic: true, color: C.muted, isTextBox: true });
foot(s, 6);

// ======================================================================
// 7 · RESULTS (ablation + clinical)
s = p.addSlide(); s.background = { color: C.paper };
kicker(s, "Results", C.coral); title(s, "The proof — and the clinical numbers");
s.addImage({ path: IMG("../artifacts/plots/ablation.png"), x: L.x, y: 1.95, w: 5.95, h: 3.56 });
s.addText("Each added stream lifts performance — on held-out patients, no leakage.", { x: L.x, y: 5.58, w: 5.95, h: 0.6, fontFace: BODY, fontSize: 12.5, italic: true, color: C.muted, lineSpacingMultiple: 1.15, isTextBox: true });
// right column
s.addText([{ text: "0.77", options: { color: C.muted } }, { text: " → ", options: { color: C.muted } }, { text: "0.81", options: { color: C.tealD } }, { text: " → ", options: { color: C.muted } }, { text: "0.82", options: { color: C.teal, highlight: C.hiMint } }],
  { x: R.x, y: 1.9, w: R.w, h: 0.8, fontFace: DISP, fontSize: 36, bold: true, isTextBox: true });
s.addText("PR-AUC as we add CGM → wearable → record. Both streams carry signal the other can't.", { x: R.x, y: 2.75, w: R.w, h: 0.7, fontFace: BODY, fontSize: 14, color: C.body, lineSpacingMultiple: 1.18, isTextBox: true });
rule(s, R.x, 3.65, R.w, C.rule, 1.2);
[["0.95", "ROC-AUC", C.teal], ["0.82", "PR-AUC", C.tealD], ["84%", "caught @10% FAR", C.green], ["~50m", "lead time", C.amber]].forEach((d, i) => {
  const x = R.x + (i % 2) * 2.85, y = 3.9 + Math.floor(i / 2) * 1.15;
  s.addText(d[0], { x, y, w: 2.7, h: 0.7, fontFace: DISP, fontSize: 40, bold: true, color: d[2], isTextBox: true, margin: 0 });
  s.addText(d[1], { x, y: y + 0.68, w: 2.7, h: 0.35, fontFace: BODY, fontSize: 13, color: C.body, isTextBox: true });
});
s.addText([{ text: "95.8% of forecasts fall in Clarke Zones A + B", options: { bold: true, color: C.ink, highlight: C.hiMint } }, { text: "  — clinically safe.", options: { color: C.body } }],
  { x: R.x, y: 6.25, w: R.w, h: 0.5, fontFace: BODY, fontSize: 14.5, isTextBox: true });
foot(s, 7);

// ======================================================================
// 8 · EXPLAINABILITY
s = p.addSlide(); s.background = { color: C.paper };
kicker(s, "Trust", C.teal); title(s, "Explainable by design — the doctor sees why");
s.addImage({ path: IMG("../artifacts/plots/global_importance.png"), x: L.x, y: 1.95, w: 6.5, h: 4.26 });
s.addText([{ text: "“Why is this patient at risk ", options: { color: C.ink } }, { text: "right now", options: { italic: true, color: C.coral } }, { text: "?”", options: { color: C.ink } }],
  { x: R.x, y: 2.0, w: R.w, h: 1.0, fontFace: DISP, fontSize: 25, bold: true, lineSpacingMultiple: 1.1, isTextBox: true });
s.addText([
  { text: "SHAP attributes every risk score to its drivers — globally here, per patient in the dashboard. The top drivers ", options: { color: C.body } },
  { text: " blend both streams ", options: { color: C.ink, highlight: C.hiAmber } },
  { text: " —", options: { color: C.body } },
], { x: R.x, y: 3.1, w: R.w, h: 1.1, fontFace: BODY, fontSize: 15, lineSpacingMultiple: 1.25, isTextBox: true });
[["wearable — HRV, sleep, activity", C.tealD], ["CGM — glucose level & slope, time of day", C.teal], ["record — HbA1c, CKD, medications", C.coral]].forEach((d, i) => {
  const y = 4.45 + i * 0.55; dot(s, R.x, y + 0.07, 0.17, d[1]);
  s.addText(d[0], { x: R.x + 0.32, y, w: R.w - 0.32, h: 0.4, fontFace: BODY, fontSize: 14, color: C.body, isTextBox: true });
});
foot(s, 8);

// ======================================================================
// 9 · DASHBOARD (annotated)
s = p.addSlide(); s.background = { color: C.paper };
kicker(s, "The product", C.teal); title(s, "How a doctor meets the virtual patient");
s.addImage({ path: IMG("img/dash_hero.png"), x: MX, y: 1.72, w: 8.85, h: 5.02 });
[["Risk climbs before the spike —", "that gap is the early warning.", 2.25, C.coral],
 ["Live gauge & alert state", "", 3.75, C.teal],
 ["Every alert is explained", "by its SHAP drivers.", 5.15, C.purple]].forEach((d) => {
  penArrow(s, 9.85, d[2] + 0.1, -0.55, 0, 0, d[3]);
  s.addText([{ text: d[0], options: { bold: true, color: C.ink } }, ...(d[1] ? [{ text: "\n" + d[1], options: { color: C.body } }] : [])],
    { x: 10.4, y: d[2] - 0.18, w: 2.4, h: 0.9, fontFace: DISP, fontSize: 14, lineSpacingMultiple: 1.12, isTextBox: true });
});
foot(s, 9);

// ======================================================================
// 10 · WHAT-IF
s = p.addSlide(); s.background = { color: C.paper };
kicker(s, "The twin in action", C.coral); title(s, "Turning a prediction into a recommendation");
s.addText([
  { text: "At ", options: { color: C.body } }, { text: " 68% predicted risk ", options: { bold: true, color: C.ink, highlight: C.hiCoral } },
  { text: ", the doctor tries interventions on Meera's twin — and watches the risk fall:", options: { color: C.body } },
], { x: MX, y: 1.72, w: CW, h: 0.55, fontFace: DISP, fontSize: 17, isTextBox: true });
[["walking", "A 20-minute walk now", "68", "37"], ["moon", "Better sleep, less stress", "68", "31"],
 ["pills", "Take metformin", "68", "43"], ["apple", "A lighter, low-GI meal", "68", "55"]].forEach((d, i) => {
  const x = MX + (i % 2) * 6.1, y = 2.7 + Math.floor(i / 2) * 1.95;
  iconDot(s, x, y + 0.12, 0.85, C.teal, d[0]);
  s.addText(d[1], { x: x + 1.12, y: y - 0.08, w: 4.9, h: 0.5, fontFace: DISP, fontSize: 18, bold: true, color: C.ink, isTextBox: true });
  s.addText([{ text: d[2] + "%", options: { color: C.muted } }, { text: "  →  ", options: { color: C.muted } }, { text: d[3] + "%", options: { bold: true, color: C.green, highlight: C.hiMint } }],
    { x: x + 1.12, y: y + 0.46, w: 4.9, h: 0.75, fontFace: DISP, fontSize: 30, bold: true, isTextBox: true });
  if (i < 2) rule(s, MX, y + 1.58, CW, C.rule, 1);
});
s.addText("Context-aware: the engine edits the twin's state and re-scores — the same model, counterfactually.",
  { x: MX, y: 6.5, w: CW, h: 0.4, fontFace: BODY, fontSize: 12.5, italic: true, color: C.muted, isTextBox: true });
foot(s, 10);

// ======================================================================
// 11 · IMPACT + ROADMAP
s = p.addSlide(); s.background = { color: C.paper };
kicker(s, "Impact & roadmap", C.teal); title(s, "Why it matters — and where it goes next");
// ---- left: impact (icon rows) ----
s.addText("WHAT IT CHANGES FOR INDIA", { x: L.x, y: 1.82, w: L.w, h: 0.3, fontFace: BODY, fontSize: 12, bold: true, color: C.coral, charSpacing: 2, isTextBox: true });
[["hospital", "Remote monitoring & triage", "one clinician oversees hundreds, ranked by risk", C.teal],
 ["target", "Personalized coaching", "a concrete, evidence-based next action per patient", C.green],
 ["heartbeat", "Prevent complications", "catch excursions early — slow kidney, eye & heart disease", C.coral],
 ["globe", "Runs on data India already has", "wearables + CGM + records, with no new hardware", C.amber]].forEach((d, i) => {
  const y = 2.35 + i * 1.13;
  iconDot(s, L.x, y, 0.66, d[3], d[0]);
  s.addText(d[1], { x: L.x + 0.92, y: y - 0.04, w: L.w - 0.92, h: 0.4, fontFace: DISP, fontSize: 16.5, bold: true, color: C.ink, isTextBox: true });
  s.addText(d[2], { x: L.x + 0.92, y: y + 0.36, w: L.w - 0.92, h: 0.5, fontFace: BODY, fontSize: 12.5, color: C.body, lineSpacingMultiple: 1.12, isTextBox: true });
});
// ---- divider ----
s.addShape(p.ShapeType.line, { x: 6.55, y: 1.95, w: 0, h: 4.95, line: { color: C.rule, width: 1.2 } });
// ---- right: roadmap (connected vertical timeline) ----
s.addText("THE ROAD AHEAD", { x: 7.05, y: 1.82, w: R.w, h: 0.3, fontFace: BODY, fontSize: 12, bold: true, color: C.teal, charSpacing: 2, isTextBox: true });
const nodeX = 7.18, textX = 7.65;
const steps = [["NOW", "Proof of concept", "Fused model, dashboard & simulation on synthetic + open data.", C.teal],
  ["NEXT", "Real data", "Train & validate on ShanghaiT2DM, MIMIC-IV and wearable cohorts.", C.tealD],
  ["THEN", "Prospective pilot", "A silent-mode hospital pilot measuring real lead time & utility.", C.amber],
  ["LATER", "Regulation & scale", "Bias audits, a CDSCO pathway, clinician-in-the-loop trials.", C.coral]];
const topY = 2.55, stepH = 1.12;
// connecting line behind nodes
s.addShape(p.ShapeType.line, { x: nodeX, y: topY + 0.14, w: 0, h: stepH * 3, line: { color: C.rule, width: 2, dashType: "dash" } });
steps.forEach((d, i) => {
  const y = topY + i * stepH;
  s.addShape(p.ShapeType.ellipse, { x: nodeX - 0.16, y: y - 0.02, w: 0.32, h: 0.32, fill: { color: d[3] }, line: { color: C.paper, width: 2.5 } });
  s.addText(d[0], { x: textX, y: y - 0.1, w: 1.6, h: 0.3, fontFace: BODY, fontSize: 11, bold: true, color: d[3], charSpacing: 2, isTextBox: true });
  s.addText(d[1], { x: textX + 1.35, y: y - 0.12, w: 3.55, h: 0.34, fontFace: DISP, fontSize: 16, bold: true, color: C.ink, isTextBox: true });
  s.addText(d[2], { x: textX, y: y + 0.26, w: 4.85, h: 0.6, fontFace: BODY, fontSize: 12, color: C.body, lineSpacingMultiple: 1.12, isTextBox: true });
});
foot(s, 11);

// ======================================================================
// 12 · VISION + CLOSE (full-bleed)
s = p.addSlide(); s.background = { color: C.tealD };
s.addShape(p.ShapeType.ellipse, { x: 9.5, y: -2.3, w: 6.4, h: 6.4, fill: { color: "0C4A50" }, line: { type: "none" } });
iconDot(s, MX, 0.85, 0.85, C.coral, "heart");
s.addText([
  { text: "A gentle nudge ", options: {} }, { text: "before", options: { italic: true, color: "FFE1B0" } },
  { text: " the spike —\nnot a diagnosis ", options: {} }, { text: "after", options: { italic: true, color: "FFE1B0" } },
  { text: " the damage.", options: {} },
], { x: MX, y: 1.85, w: 11.5, h: 1.9, fontFace: DISP, fontSize: 34, bold: true, color: C.white, lineSpacingMultiple: 1.12, isTextBox: true });
rule(s, MX, 4.0, CW, "2A5A5F", 1);
s.addText("Thank you.", { x: MX, y: 4.1, w: 6, h: 0.7, fontFace: DISP, fontSize: 30, bold: true, color: C.white, isTextBox: true });
["Fuses record + wearable/CGM — both streams proven to add value",
 "Predicts ~50 min ahead · ROC-AUC 0.95 · 84% caught early",
 "Explains every alert & simulates the fix on a virtual twin",
 "Runs in 45 s, zero downloads — synthetic + real-data ready"].forEach((t, i) => {
  const y = 4.95 + i * 0.46; dot(s, MX, y + 0.05, 0.18, C.green);
  s.addText(t, { x: MX + 0.35, y, w: 11.3, h: 0.4, fontFace: BODY, fontSize: 14, color: "EAF2F1", isTextBox: true });
});
s.addText("Team Healthcure · IIT Kanpur", { x: MX, y: 6.95, w: CW, h: 0.35, fontFace: BODY, fontSize: 12, italic: true, color: "9FC2C3", isTextBox: true });

p.writeFile({ fileName: path.join(__dirname, "GlucoTwin_Deck.pptx") }).then((f) => console.log("saved", f));
