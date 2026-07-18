"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  chooseRecordingMimeType,
  DEFAULT_STT_MAX_BYTES,
  DEFAULT_STT_MAX_DURATION_SECONDS,
  parsePositiveLimit,
  resolveAudioMimeType,
} from "@/lib/stt";

type SpeechPhase = "idle" | "requesting" | "recording" | "transcribing";

interface SpeechToTextStatusResponse {
  enabled?: unknown;
  max_bytes?: unknown;
  max_duration_seconds?: unknown;
}

interface SpeechToTextResponse {
  error?: string | { message?: string };
  message?: string;
  text?: unknown;
}

interface UseSpeechToTextOptions {
  active: boolean;
  onTranscript: (transcript: string) => void;
}

interface SpeechToTextController {
  canRecord: boolean;
  checking: boolean;
  clearError: () => void;
  enabled: boolean;
  error: string | null;
  maxDurationSeconds: number;
  microphoneSupported: boolean;
  phase: SpeechPhase;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  transcribeFile: (file: File) => Promise<void>;
}

function stopStream(stream: MediaStream | null) {
  stream?.getTracks().forEach((track) => track.stop());
}

function getBrowserRecordingMimeType() {
  if (
    typeof window === "undefined" ||
    !window.isSecureContext ||
    typeof MediaRecorder === "undefined" ||
    typeof MediaRecorder.isTypeSupported !== "function" ||
    !navigator.mediaDevices?.getUserMedia
  ) {
    return null;
  }
  return chooseRecordingMimeType((mimeType) => MediaRecorder.isTypeSupported(mimeType));
}

function getReadableError(error: unknown) {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError" || error.name === "SecurityError") {
      return "Trình duyệt chưa cho phép dùng mic. Bạn có thể chọn một tệp âm thanh thay thế.";
    }
    if (error.name === "NotFoundError") {
      return "Không tìm thấy mic trên thiết bị. Bạn có thể chọn một tệp âm thanh thay thế.";
    }
    if (error.name === "AbortError") return null;
  }
  if (error instanceof Error && error.message) return error.message;
  return "Không thể chuyển giọng nói thành văn bản. Vui lòng thử lại.";
}

async function getResponseError(response: Response) {
  let payload: SpeechToTextResponse | null = null;
  try {
    payload = (await response.json()) as SpeechToTextResponse;
  } catch {
    // The UI uses a stable local error when an upstream proxy returns non-JSON.
  }

  const upstreamMessage =
    typeof payload?.error === "string"
      ? payload.error
      : typeof payload?.error?.message === "string"
        ? payload.error.message
        : typeof payload?.message === "string"
          ? payload.message
          : null;
  if (upstreamMessage) return upstreamMessage;

  if (response.status === 413) return "Tệp âm thanh vượt quá dung lượng cho phép.";
  if (response.status === 415) return "Định dạng âm thanh này chưa được hỗ trợ.";
  if (response.status === 429) return "Bạn đang gửi quá nhiều bản ghi. Vui lòng chờ rồi thử lại.";
  if (response.status === 504) return "Máy nhận dạng giọng nói phản hồi quá lâu. Vui lòng thử lại.";
  return "Không thể chuyển giọng nói thành văn bản. Vui lòng thử lại.";
}

function readAudioDurationMs(file: File) {
  return new Promise<number>((resolve, reject) => {
    if (typeof Audio === "undefined" || typeof URL.createObjectURL !== "function") {
      reject(new Error("Trình duyệt không đọc được thời lượng của tệp âm thanh này."));
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    const audio = new Audio();
    let settled = false;
    const finish = (value?: number, error?: Error) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeoutId);
      audio.removeAttribute("src");
      audio.load();
      URL.revokeObjectURL(objectUrl);
      if (error || value === undefined) {
        reject(error ?? new Error("Không đọc được thời lượng của tệp âm thanh."));
      } else {
        resolve(value);
      }
    };
    const timeoutId = window.setTimeout(
      () => finish(undefined, new Error("Không đọc được thời lượng của tệp âm thanh.")),
      10_000,
    );

    audio.preload = "metadata";
    audio.onloadedmetadata = () => {
      const durationMs = Math.round(audio.duration * 1_000);
      if (!Number.isFinite(durationMs) || durationMs <= 0) {
        finish(undefined, new Error("Tệp âm thanh không có thời lượng hợp lệ."));
        return;
      }
      finish(durationMs);
    };
    audio.onerror = () => {
      finish(undefined, new Error("Không đọc được tệp âm thanh đã chọn."));
    };
    audio.src = objectUrl;
  });
}

export function useSpeechToText({
  active,
  onTranscript,
}: UseSpeechToTextOptions): SpeechToTextController {
  const [checking, setChecking] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [phase, setPhase] = useState<SpeechPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [microphoneBlocked, setMicrophoneBlocked] = useState(false);
  const [maxDurationSeconds, setMaxDurationSeconds] = useState(
    DEFAULT_STT_MAX_DURATION_SECONDS,
  );
  const [maxBytes, setMaxBytes] = useState(DEFAULT_STT_MAX_BYTES);
  const activeRef = useRef(active);
  const mountedRef = useRef(true);
  const onTranscriptRef = useRef(onTranscript);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingStartedAtRef = useRef(0);
  const recordingTimerRef = useRef<number | null>(null);
  const capturePendingRef = useRef(false);
  const requestAbortRef = useRef<AbortController | null>(null);
  const recordingMimeType = getBrowserRecordingMimeType();

  const clearRecordingTimer = useCallback(() => {
    if (recordingTimerRef.current !== null) {
      window.clearTimeout(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
  }, []);

  const releaseStream = useCallback(() => {
    stopStream(mediaStreamRef.current);
    mediaStreamRef.current = null;
  }, []);

  const discardRecording = useCallback(() => {
    capturePendingRef.current = false;
    clearRecordingTimer();
    const recorder = mediaRecorderRef.current;
    mediaRecorderRef.current = null;
    if (recorder) {
      recorder.ondataavailable = null;
      recorder.onerror = null;
      recorder.onstop = null;
      if (recorder.state !== "inactive") {
        try {
          recorder.stop();
        } catch {
          // The stream is released below even if a browser already stopped it.
        }
      }
    }
    audioChunksRef.current = [];
    releaseStream();
  }, [clearRecordingTimer, releaseStream]);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      activeRef.current = false;
      discardRecording();
      requestAbortRef.current?.abort();
      requestAbortRef.current = null;
    };
  }, [discardRecording]);

  useEffect(() => {
    activeRef.current = active;
    if (!active) {
      discardRecording();
      requestAbortRef.current?.abort();
      requestAbortRef.current = null;
      queueMicrotask(() => {
        if (mountedRef.current && !activeRef.current) setPhase("idle");
      });
      return;
    }

    const controller = new AbortController();
    queueMicrotask(() => {
      if (mountedRef.current && activeRef.current) setChecking(true);
    });
    void fetch("/api/stt/transcribe", {
      cache: "no-store",
      headers: { Accept: "application/json" },
      method: "GET",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(await getResponseError(response));
        return (await response.json()) as SpeechToTextStatusResponse;
      })
      .then((payload) => {
        if (controller.signal.aborted || !activeRef.current) return;
        setEnabled(payload.enabled === true);
        setMaxDurationSeconds(
          parsePositiveLimit(
            payload.max_duration_seconds,
            DEFAULT_STT_MAX_DURATION_SECONDS,
            DEFAULT_STT_MAX_DURATION_SECONDS,
          ),
        );
        setMaxBytes(
          parsePositiveLimit(payload.max_bytes, DEFAULT_STT_MAX_BYTES, 25 * 1024 * 1024),
        );
      })
      .catch((statusError: unknown) => {
        if (statusError instanceof DOMException && statusError.name === "AbortError") return;
        if (controller.signal.aborted || !activeRef.current) return;
        setEnabled(false);
      })
      .finally(() => {
        if (!controller.signal.aborted && activeRef.current) setChecking(false);
      });

    return () => controller.abort();
  }, [active, discardRecording]);

  const transcribeAudio = useCallback(
    async (audio: Blob, mimeType: string, durationMs: number) => {
      if (!enabled || !activeRef.current) return;
      if (!Number.isInteger(durationMs) || durationMs <= 0) {
        setError("Không đọc được thời lượng hợp lệ của bản ghi âm.");
        setPhase("idle");
        return;
      }
      if (durationMs > maxDurationSeconds * 1_000) {
        setError(`Bản ghi âm chỉ được dài tối đa ${maxDurationSeconds} giây.`);
        setPhase("idle");
        return;
      }
      if (audio.size <= 0) {
        setError("Bản ghi âm không có dữ liệu. Vui lòng thử lại.");
        setPhase("idle");
        return;
      }
      if (audio.size > maxBytes) {
        setError(`Tệp âm thanh vượt quá giới hạn ${Math.ceil(maxBytes / 1024 / 1024)} MB.`);
        setPhase("idle");
        return;
      }

      requestAbortRef.current?.abort();
      const controller = new AbortController();
      requestAbortRef.current = controller;
      setError(null);
      setPhase("transcribing");
      try {
        const response = await fetch("/api/stt/transcribe", {
          body: audio,
          headers: {
            "Content-Type": mimeType,
            "X-VNeGuide-Audio-Duration-Ms": String(durationMs),
          },
          method: "POST",
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(await getResponseError(response));
        const payload = (await response.json()) as SpeechToTextResponse;
        if (typeof payload.text !== "string" || !payload.text.trim()) {
          throw new Error("Không nhận dạng được lời nói trong bản ghi âm.");
        }
        if (mountedRef.current && activeRef.current) {
          onTranscriptRef.current(payload.text);
        }
      } catch (transcriptionError) {
        const readableError = getReadableError(transcriptionError);
        if (readableError && mountedRef.current && activeRef.current) {
          setError(readableError);
        }
      } finally {
        if (requestAbortRef.current === controller) requestAbortRef.current = null;
        if (mountedRef.current && activeRef.current) setPhase("idle");
      }
    },
    [enabled, maxBytes, maxDurationSeconds],
  );

  const startRecording = useCallback(async () => {
    if (!enabled || phase !== "idle" || capturePendingRef.current) return;
    const safeMimeType = getBrowserRecordingMimeType();
    if (!safeMimeType) {
      setError(
        "Trình duyệt không thể ghi âm tại địa chỉ này. Bạn có thể chọn một tệp âm thanh thay thế.",
      );
      return;
    }

    setError(null);
    capturePendingRef.current = true;
    setPhase("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
        video: false,
      });
      if (!mountedRef.current || !activeRef.current) {
        capturePendingRef.current = false;
        stopStream(stream);
        return;
      }

      mediaStreamRef.current = stream;
      const recorder = new MediaRecorder(stream, { mimeType: safeMimeType });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];
      recordingStartedAtRef.current = Date.now();
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        discardRecording();
        if (mountedRef.current && activeRef.current) {
          setError("Không thể tiếp tục ghi âm. Vui lòng thử lại hoặc chọn một tệp âm thanh.");
          setPhase("idle");
        }
      };
      recorder.onstop = () => {
        clearRecordingTimer();
        const chunks = audioChunksRef.current;
        audioChunksRef.current = [];
        mediaRecorderRef.current = null;
        releaseStream();
        if (!mountedRef.current || !activeRef.current) return;

        const elapsedMs = Math.max(1, Date.now() - recordingStartedAtRef.current);
        const durationMs = Math.min(maxDurationSeconds * 1_000, elapsedMs);
        const outputMimeType =
          resolveAudioMimeType(recorder.mimeType || safeMimeType) ??
          resolveAudioMimeType(safeMimeType);
        if (!outputMimeType) {
          setError("Trình duyệt đã tạo một định dạng âm thanh chưa được hỗ trợ.");
          setPhase("idle");
          return;
        }
        const audio = new Blob(chunks, { type: outputMimeType });
        void transcribeAudio(audio, outputMimeType, durationMs);
      };

      recorder.start(1_000);
      capturePendingRef.current = false;
      setMicrophoneBlocked(false);
      setPhase("recording");
      recordingTimerRef.current = window.setTimeout(() => {
        const currentRecorder = mediaRecorderRef.current;
        if (currentRecorder?.state === "recording") currentRecorder.stop();
      }, maxDurationSeconds * 1_000);
    } catch (recordingError) {
      discardRecording();
      const readableError = getReadableError(recordingError);
      if (recordingError instanceof DOMException) {
        if (recordingError.name === "NotAllowedError" || recordingError.name === "SecurityError") {
          setMicrophoneBlocked(true);
        }
      }
      if (readableError && mountedRef.current && activeRef.current) setError(readableError);
      if (mountedRef.current) setPhase("idle");
    }
  }, [
    clearRecordingTimer,
    discardRecording,
    enabled,
    maxDurationSeconds,
    phase,
    releaseStream,
    transcribeAudio,
  ]);

  const stopRecording = useCallback(() => {
    clearRecordingTimer();
    const recorder = mediaRecorderRef.current;
    if (recorder?.state === "recording" || recorder?.state === "paused") recorder.stop();
  }, [clearRecordingTimer]);

  const transcribeFile = useCallback(
    async (file: File) => {
      if (!enabled || phase !== "idle") return;
      setError(null);
      const mimeType = resolveAudioMimeType(file.type, file.name);
      if (!mimeType) {
        setError("Định dạng tệp này chưa được hỗ trợ. Hãy chọn WebM, OGG, WAV, MP3, M4A, MP4, AAC hoặc FLAC.");
        return;
      }
      if (file.size <= 0 || file.size > maxBytes) {
        setError(`Tệp âm thanh phải nhỏ hơn ${Math.ceil(maxBytes / 1024 / 1024)} MB.`);
        return;
      }

      setPhase("transcribing");
      try {
        const durationMs = await readAudioDurationMs(file);
        if (durationMs > maxDurationSeconds * 1_000) {
          throw new Error(`Tệp âm thanh chỉ được dài tối đa ${maxDurationSeconds} giây.`);
        }
        await transcribeAudio(file, mimeType, durationMs);
      } catch (fileError) {
        const readableError = getReadableError(fileError);
        if (readableError && mountedRef.current && activeRef.current) setError(readableError);
        if (mountedRef.current && activeRef.current) setPhase("idle");
      }
    },
    [enabled, maxBytes, maxDurationSeconds, phase, transcribeAudio],
  );

  return {
    canRecord: enabled && Boolean(recordingMimeType) && !microphoneBlocked,
    checking,
    clearError: () => setError(null),
    enabled,
    error,
    maxDurationSeconds,
    microphoneSupported: Boolean(recordingMimeType) && !microphoneBlocked,
    phase,
    startRecording,
    stopRecording,
    transcribeFile,
  };
}
