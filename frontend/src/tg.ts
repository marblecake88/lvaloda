// Telegram WebApp helpers with full layout wiring.
// Exposes CSS custom properties for safe-area insets and viewport height so
// the layout can use them from styles.css without having to pass data down.

export const tg = (window as any).Telegram?.WebApp;

type Insets = { top: number; right: number; bottom: number; left: number };

function writeInsetVars(prefix: string, insets: Insets | undefined) {
  if (!insets) return;
  const root = document.documentElement;
  root.style.setProperty(`${prefix}-top`, `${insets.top}px`);
  root.style.setProperty(`${prefix}-right`, `${insets.right}px`);
  root.style.setProperty(`${prefix}-bottom`, `${insets.bottom}px`);
  root.style.setProperty(`${prefix}-left`, `${insets.left}px`);
}

function syncInsets() {
  if (!tg) return;
  writeInsetVars("--safe", tg.safeAreaInset);
  writeInsetVars("--content-safe", tg.contentSafeAreaInset);
  const root = document.documentElement;
  if (tg.viewportStableHeight) {
    root.style.setProperty("--viewport", `${tg.viewportStableHeight}px`);
  }
}

function applyTheme() {
  if (!tg) return;
  const root = document.documentElement;
  root.dataset.scheme = tg.colorScheme || "light";
  const params = tg.themeParams || {};
  for (const [k, v] of Object.entries(params)) {
    root.style.setProperty(`--tg-${k.replaceAll("_", "-")}`, v as string);
  }
}

export function bootstrapTelegram() {
  if (!tg) {
    // Browser fallback for local dev outside Telegram
    document.documentElement.dataset.scheme = "light";
    return;
  }
  tg.ready();
  tg.expand();

  // Fullscreen only on native mobile clients — on desktop/web it just makes
  // the app ugly and breaks the native window chrome.
  const platform = (tg.platform as string | undefined)?.toLowerCase() || "";
  const isMobile = platform === "android" || platform === "ios";
  if (isMobile) {
    try {
      tg.requestFullscreen?.();
    } catch {}
  }

  try {
    tg.disableVerticalSwipes?.();
  } catch {}

  // Paint native chrome in-tone with the app background.
  try {
    tg.setHeaderColor?.("secondary_bg_color");
    tg.setBackgroundColor?.("bg_color");
    tg.setBottomBarColor?.("bg_color");
  } catch {}

  applyTheme();
  syncInsets();

  tg.onEvent?.("viewportChanged", syncInsets);
  tg.onEvent?.("safeAreaChanged", syncInsets);
  tg.onEvent?.("contentSafeAreaChanged", syncInsets);
  tg.onEvent?.("themeChanged", applyTheme);
  tg.onEvent?.("fullscreenChanged", syncInsets);
}

export function getInitData(): string {
  return tg?.initData || "";
}

export function haptic(type: "light" | "medium" | "heavy" | "soft" | "rigid" = "light") {
  try {
    tg?.HapticFeedback?.impactOccurred(type);
  } catch {}
}

export function notify(type: "success" | "error" | "warning") {
  try {
    tg?.HapticFeedback?.notificationOccurred(type);
  } catch {}
}

export function showBackButton(onClick: () => void) {
  if (!tg?.BackButton) return () => {};
  tg.BackButton.show();
  tg.BackButton.onClick(onClick);
  return () => {
    tg.BackButton.offClick(onClick);
    tg.BackButton.hide();
  };
}
