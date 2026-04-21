import { useCallback, useEffect, useRef, useState } from "react";

const BAR_COUNT = 22;

export interface RecorderAPI {
  recording: boolean;
  duration: number;                // seconds since recording started
  levels: number[];                // BAR_COUNT bars, 0..1
  start: () => Promise<void>;
  stop: () => Promise<Blob>;
  cancel: () => void;
  error: string | null;
}

export function useRecorder(): RecorderAPI {
  const [recording, setRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [levels, setLevels] = useState<number[]>(() => Array(BAR_COUNT).fill(0));
  const [error, setError] = useState<string | null>(null);

  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<BlobPart[]>([]);
  const stream = useRef<MediaStream | null>(null);
  const audioCtx = useRef<AudioContext | null>(null);
  const analyser = useRef<AnalyserNode | null>(null);
  const sourceNode = useRef<MediaStreamAudioSourceNode | null>(null);
  const rafId = useRef<number | null>(null);
  const startedAt = useRef<number>(0);
  const cancelled = useRef<boolean>(false);

  const cleanup = useCallback(() => {
    if (rafId.current) {
      cancelAnimationFrame(rafId.current);
      rafId.current = null;
    }
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    sourceNode.current?.disconnect();
    sourceNode.current = null;
    analyser.current = null;
    audioCtx.current?.close().catch(() => {});
    audioCtx.current = null;
    setLevels(Array(BAR_COUNT).fill(0));
    setDuration(0);
  }, []);

  useEffect(() => () => cleanup(), [cleanup]);

  const tickLevels = useCallback(() => {
    const a = analyser.current;
    if (!a) return;
    const freq = new Uint8Array(a.frequencyBinCount);
    a.getByteFrequencyData(freq);
    const bars: number[] = [];
    const bucket = Math.floor(freq.length / BAR_COUNT);
    for (let i = 0; i < BAR_COUNT; i++) {
      let sum = 0;
      for (let j = 0; j < bucket; j++) sum += freq[i * bucket + j];
      // normalize to 0..1, apply mild curve for more visual range
      const v = Math.min(1, Math.pow(sum / bucket / 255, 0.7));
      bars.push(v);
    }
    setLevels(bars);
    setDuration((Date.now() - startedAt.current) / 1000);
    rafId.current = requestAnimationFrame(tickLevels);
  }, []);

  const start = useCallback(async () => {
    setError(null);
    cancelled.current = false;
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
    } catch (e: any) {
      setError(e?.message || "Нет доступа к микрофону");
      throw e;
    }

    // Analyser for level meter
    const ctx = new (window.AudioContext ||
      (window as any).webkitAudioContext)();
    const src = ctx.createMediaStreamSource(stream.current);
    const ana = ctx.createAnalyser();
    ana.fftSize = 512;
    ana.smoothingTimeConstant = 0.6;
    src.connect(ana);
    audioCtx.current = ctx;
    sourceNode.current = src;
    analyser.current = ana;

    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : MediaRecorder.isTypeSupported("audio/webm")
      ? "audio/webm"
      : MediaRecorder.isTypeSupported("audio/mp4")
      ? "audio/mp4"
      : "";
    const mr = new MediaRecorder(
      stream.current,
      mimeType ? { mimeType } : undefined
    );
    mediaRecorder.current = mr;
    chunks.current = [];
    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.current.push(e.data);
    };
    mr.start(100);
    startedAt.current = Date.now();
    setRecording(true);
    tickLevels();
  }, [tickLevels]);

  const stop = useCallback((): Promise<Blob> => {
    return new Promise((resolve) => {
      const mr = mediaRecorder.current;
      if (!mr || mr.state === "inactive") {
        cleanup();
        setRecording(false);
        return resolve(new Blob());
      }
      mr.onstop = () => {
        const blob = new Blob(chunks.current, {
          type: mr.mimeType || "audio/webm",
        });
        setRecording(false);
        cleanup();
        resolve(cancelled.current ? new Blob() : blob);
      };
      mr.stop();
    });
  }, [cleanup]);

  const cancel = useCallback(() => {
    cancelled.current = true;
    const mr = mediaRecorder.current;
    if (mr && mr.state !== "inactive") mr.stop();
    chunks.current = [];
    setRecording(false);
    cleanup();
  }, [cleanup]);

  return { recording, duration, levels, start, stop, cancel, error };
}
