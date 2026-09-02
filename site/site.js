document.documentElement.classList.add("js");

const REPOSITORY_URL = "https://github.com/xiajiadi/dc-designer-core";
const INSTALL_PROMPT = [
  "请在当前工作区接入并启动 DC Designer v2，并用它协助我完成中国大陆 K12 信息科技 / 信息技术教学系统设计。",
  `项目仓库：${REPOSITORY_URL}`,
  "如果当前工作区还没有这个项目，请以项目级方式从上面的仓库地址读取或获取它；不要把项目复制到用户全局插件目录。",
  "请先读取 README.md、docs/agent-compatibility.md、docs/v1_plugin_contract.md 和对应的 skills/ 文件。",
  "如果宿主支持从远程来源安装，使用上面的仓库地址；如果只能从本地目录加载，先在当前工作区获取仓库并加载。优先按项目级方式接入：Codex 使用 .codex-plugin；Claude Code 使用 .claude-plugin；Gemini CLI 使用 gemini-extension.json；其他支持 MCP 的智能体接入 python mcp-server/server.py；其余智能体使用仓库内的本地脚本和 Skill。",
  "优先使用当前项目或工作区级别的插件、扩展、Skill 或 MCP 配置。不要在没有我明确授权时写入用户全局配置；如果宿主要求安装确认、登录或权限，请明确说明，不要假装已安装。",
  "接入后默认使用共享 Skill dc-info-tech-design 开始课标约束快速设计；需要评审或修订时使用 dc-info-tech-review 或 dc-info-tech-revise。",
  "接入成功后立即开始设计；如果接入没有完成，明确报告阻断原因和下一步。缺少信息时只问当前阶段最必要的 1 至 3 项。不得编造教材版本、学生数据或课堂效果。",
  "关键结论区分官方依据、教师输入、教材 / 学校资料、学习者数据、AI 推断和 AI 建议；没有教师确认时保持候选或草案状态。",
  "现在先完成接入检查，然后告诉我使用的接入方式、三个 Skill 是否可用、MCP 是否可用，以及开始设计还缺哪些信息。"
].join("\n");

function announce(message, source) {
  document.querySelectorAll("[data-copy-feedback]").forEach((target) => {
    target.textContent = message;
    if (source && source.closest("section")) {
      const local = source.closest("section").querySelector("[data-copy-feedback]");
      if (local) local.textContent = message;
    }
  });
}

function fallbackCopy(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  let copied = false;
  try { copied = document.execCommand("copy"); } catch { copied = false; }
  textarea.remove();
  return copied;
}

async function copyInstallPrompt(event) {
  const button = event.currentTarget;
  let copied = false;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(INSTALL_PROMPT);
      copied = true;
    }
  } catch { copied = false; }
  if (!copied) copied = fallbackCopy(INSTALL_PROMPT);
  button.classList.toggle("is-copied", copied);
  const label = button.querySelector("[data-copy-label]") || button.querySelector("span:last-child");
  const defaultLabel = button.dataset.copyLabel || "复制给任意智能体";
  label.textContent = copied ? "已复制" : "复制失败";
  announce(copied ? "通用启动提示词已复制到剪贴板。" : "无法自动复制，请手动选择启动提示词。", button);
  window.setTimeout(() => {
    button.classList.remove("is-copied");
    label.textContent = defaultLabel;
  }, 2600);
}

document.querySelectorAll("[data-copy-install]").forEach((button) => button.addEventListener("click", copyInstallPrompt));

document.querySelectorAll("[data-disclosure-button]").forEach((button) => {
  const panel = document.getElementById(button.getAttribute("aria-controls"));
  const owner = button.closest("[data-principle-visual], [data-work-mode]");
  if (!panel || !owner) return;
  panel.setAttribute("aria-hidden", "true");
  const setOpen = (open) => {
    button.setAttribute("aria-expanded", String(open));
    panel.setAttribute("aria-hidden", String(!open));
    owner.classList.toggle("is-open", open);
  };
  owner.addEventListener("pointerenter", (event) => {
    if (event.pointerType === "mouse") setOpen(true);
  });
  owner.addEventListener("pointerleave", (event) => {
    if (event.pointerType === "mouse" && !owner.matches(":focus-within")) setOpen(false);
  });
  button.addEventListener("click", () => {
    const open = button.getAttribute("aria-expanded") === "true";
    setOpen(!open);
  });
  owner.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    setOpen(false);
    button.focus();
  });
});

const menuToggle = document.querySelector(".menu-toggle");
const mobileNav = document.querySelector("#mobile-nav");
if (menuToggle && mobileNav) {
  menuToggle.addEventListener("click", () => {
    const open = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!open));
    mobileNav.hidden = open;
  });
  mobileNav.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => {
    menuToggle.setAttribute("aria-expanded", "false");
    mobileNav.hidden = true;
  }));
}

const revealItems = document.querySelectorAll(".reveal");
if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) {
  revealItems.forEach((item) => item.classList.add("is-visible"));
} else {
  const observer = new IntersectionObserver((entries, currentObserver) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
      currentObserver.unobserve(entry.target);
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -30px" });
  revealItems.forEach((item) => observer.observe(item));
}
