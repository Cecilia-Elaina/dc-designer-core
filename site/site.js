const INSTALL_PROMPT = "请在当前 Codex 工作区的 Plugins 设置中从 GitHub 仓库 https://github.com/Cecilia-Elaina/dc-designer-core 导入 marketplace 并安装 dc-designer-core，安装后调用 /dc-designer-core:dc-info-tech-design；若当前账户无权限，请说明需要的管理员设置。";

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
  button.querySelector("span:last-child").textContent = copied ? "已复制" : "复制失败";
  announce(copied ? "安装指令已复制到剪贴板。" : "无法自动复制，请手动选择安装提示。", button);
  window.setTimeout(() => {
    button.classList.remove("is-copied");
    button.querySelector("span:last-child").textContent = "复制给 Codex";
  }, 2600);
}

document.querySelectorAll("[data-copy-install]").forEach((button) => button.addEventListener("click", copyInstallPrompt));

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
