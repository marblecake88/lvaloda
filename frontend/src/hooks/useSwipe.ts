import { TouchEvent as ReactTouchEvent, useRef } from "react";

interface SwipeOptions {
  onLeft?: () => void;
  onRight?: () => void;
  onUp?: () => void;
  onDown?: () => void;
  /** Minimum absolute delta (px) to trigger. Default 50. */
  threshold?: number;
  /** Fast-flick escape: below threshold but above this velocity (px/ms) still triggers. Default 0.35. */
  velocityThreshold?: number;
  /** Axis-lock ratio: a horizontal swipe needs |dx| > |dy| * this. Default 1.3. */
  axisRatio?: number;
}

/**
 * Lightweight swipe detection on a DOM element.
 *
 * Spread the returned handlers on the target:
 *   const bind = useSwipe({ onLeft: ..., onRight: ... });
 *   <div {...bind}>...</div>
 *
 * Plays well with vertical scrolling because it only fires when the swipe is
 * clearly biased along the other axis (axisRatio). Vertical swipes are
 * suppressed by Telegram WebApp's disableVerticalSwipes() for app-close, but
 * in-app vertical gestures still work for scrolling — we do not preventDefault
 * on touchmove.
 */
export function useSwipe({
  onLeft,
  onRight,
  onUp,
  onDown,
  threshold = 50,
  velocityThreshold = 0.35,
  axisRatio = 1.3,
}: SwipeOptions) {
  const start = useRef({ x: 0, y: 0, t: 0, active: false });

  function handleStart(e: ReactTouchEvent) {
    const t = e.touches[0];
    if (!t) return;
    start.current = { x: t.clientX, y: t.clientY, t: Date.now(), active: true };
  }

  function handleEnd(e: ReactTouchEvent) {
    if (!start.current.active) return;
    start.current.active = false;
    const t = e.changedTouches[0];
    if (!t) return;
    const dx = t.clientX - start.current.x;
    const dy = t.clientY - start.current.y;
    const dt = Math.max(Date.now() - start.current.t, 1);
    const adx = Math.abs(dx);
    const ady = Math.abs(dy);
    const vx = adx / dt;
    const vy = ady / dt;

    const horizontal = adx >= threshold || (adx > 15 && vx >= velocityThreshold);
    const vertical = ady >= threshold || (ady > 15 && vy >= velocityThreshold);

    if (horizontal && adx > ady * axisRatio) {
      if (dx > 0) onRight?.();
      else onLeft?.();
      return;
    }
    if (vertical && ady > adx * axisRatio) {
      if (dy > 0) onDown?.();
      else onUp?.();
    }
  }

  return {
    onTouchStart: handleStart,
    onTouchEnd: handleEnd,
    onTouchCancel: () => {
      start.current.active = false;
    },
  };
}
