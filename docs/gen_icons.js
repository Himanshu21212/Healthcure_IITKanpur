// Render react-icons to crisp white PNG glyphs for the deck.
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fs = require("fs");
const path = require("path");
const fa = require("react-icons/fa");
const fi = require("react-icons/fi");
const md = require("react-icons/md");

const OUT = path.join(__dirname, "img", "icons");
fs.mkdirSync(OUT, { recursive: true });

// name -> component.  All rendered as white glyphs (placed on colored circles).
const ICONS = {
  heartbeat: fa.FaHeartbeat, eye: fi.FiEye, zap: fi.FiZap, sliders: fi.FiSliders,
  clipboard: fa.FaRegClipboard, watch: md.MdWatch, merge: fi.FiGitMerge, brain: fa.FaBrain,
  bars: fi.FiBarChart2, shield: fa.FaShieldAlt, user: fa.FaUser, walking: fa.FaWalking,
  moon: fa.FaMoon, pills: fa.FaPills, apple: fa.FaAppleAlt, hospital: fa.FaHospital,
  target: fi.FiTarget, globe: fi.FiGlobe, clock: fi.FiClock, activity: fi.FiActivity,
  lock: fi.FiLock, check: fi.FiCheck, arrow: fi.FiArrowRight, heart: fa.FaHeart,
  database: fi.FiDatabase, trending: fi.FiTrendingUp, award: fi.FiAward, cpu: fi.FiCpu,
};

async function render(name, Comp, color) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Comp, { color: color || "#ffffff", size: 256 })
  );
  const file = path.join(OUT, `${name}${color ? "_" + color : ""}.png`);
  await sharp(Buffer.from(svg)).resize(256, 256, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toFile(file);
}

(async () => {
  for (const [name, Comp] of Object.entries(ICONS)) {
    await render(name, Comp, "#ffffff");       // white for colored circles
  }
  // a few colored variants for light/tinted chips
  await render("check", fi.FiCheck, "#1B9E77");
  await render("heart", fa.FaHeart, "#E8615A");
  console.log("icons written to", OUT);
})();
