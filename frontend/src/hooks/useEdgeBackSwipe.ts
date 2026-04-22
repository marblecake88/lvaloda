import { useEffect } from "react";

/**
 * iOS-style edge-swipe-from-left → go back.
 *
 * Attaches passive document-level listeners. A gesture counts only when
 * the touch begins within `edge` px of the left edge (default 24) and
 * moves clearly to the right. This narrow trigger zone keeps it from
 * clashing with in-screen horizontal swipes (flashcards, carousel, tabs),
 * which always start from the middle of the screen.
 */
export function useEdgeBackSwipe(
  onBack: () => void,
  opts: { enabled?: boolean; edge?: number; distance?: number; velocity?: number } = {},
) {
  const { enabled = true, edge = 24, distance = 60, velocity = 0.4 } = opts;

  useEffect(() => {
    if (!enabled) return;

    let startX = 0;
    let startY = 0;
    let startT = 0;
    let tracking = false;

    function onStart(e: TouchEvent) {
      const t = e.touches[0];
      if (!t) return;
      if (t.clientX > edge) return;
      startX = t.clientX;
      startY = t.clientY;
      startT = Date.now();
      tracking = true;
    }

    function onEnd(e: TouchEvent) {
      if (!tracking) return;
      tracking = false;
      const t = e.changedTouches[0];
      if (!t) return;
      const dx = t.clientX - startX;
      const dy = Math.abs(t.clientY - startY);
      const dt = Math.max(Date.now() - startT, 1);
      const vx = dx / dt;
      const axisLock = dx > dy * 1.5;
      const far = dx >= distance;
      const fast = dx >= 30 && vx >= velocity;
      if (axisLock && (far || fast)) onBack();
    }

    function onCancel() {
      tracking = false;
    }

    document.addEventListener("touchstart", onStart, { passive: true });
    document.addEventListener("touchend", onEnd, { passive: true });
    document.addEventListener("touchcancel", onCancel, { passive: true });
    return () => {
      document.removeEventListener("touchstart", onStart);
      document.removeEventListener("touchend", onEnd);
      document.removeEventListener("touchcancel", onCancel);
    };
  }, [onBack, enabled, edge, distance, velocity]);
}
