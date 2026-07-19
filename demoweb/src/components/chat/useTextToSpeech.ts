"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  DEFAULT_TTS_MAX_AUDIO_BYTES,
  getNextTtsSegmentIndex,
  isMpegAudioContentType,
  parseTtsContentLength,
  parseTtsSegmentMetadata,
} from "@/lib/tts";

export type TextToSpeechPhase =
  | "idle"
  | "loading"
  | "playing"
  | "paused"
  | "completed";

interface UseTextToSpeechOptions {
  active: boolean;
  disabled?: boolean;
}

interface TtsCapabilityResponse {
  enabled?: unknown;
}

interface TtsApiError {
  error?: { message?: unknown };
}

export interface TextToSpeechError {
  assistantIndex: number;
  message: string;
}

export interface TextToSpeechController {
  activeAssistantIndex: number | null;
  checking: boolean;
  enabled: boolean;
  error: TextToSpeechError | null;
  phase: TextToSpeechPhase;
  pause: () => void;
  play: (assistantIndex: number) => Promise<void>;
  resume: () => Promise<void>;
  stop: () => void;
}

const GENERIC_TTS_ERROR = "Chưa thể tạo giọng đọc. Vui lòng thử lại sau.";
const TTS_CONSENT_SESSION_KEY = "vneguide_tts_third_party_consent";

class TtsUserError extends Error {}

function confirmSpeechProviderUse(): boolean {
  try {
    if (window.sessionStorage.getItem(TTS_CONSENT_SESSION_KEY) === "1") return true;
  } catch {
    // Continue with an explicit confirmation when session storage is unavailable.
  }

  const accepted = window.confirm(
    "Để tạo giọng đọc, nội dung câu trả lời này sẽ được gửi tới dịch vụ tạo giọng nói. " +
      "Không tiếp tục nếu câu trả lời chứa thông tin cá nhân mà bạn không muốn gửi. Bạn có đồng ý không?",
  );
  if (accepted) {
    try {
      window.sessionStorage.setItem(TTS_CONSENT_SESSION_KEY, "1");
    } catch {
      // Consent remains valid for this click even when storage is unavailable.
    }
  }
  return accepted;
}

function readablePlaybackError(error: unknown): string {
  if (error instanceof DOMException && error.name === "NotAllowedError") {
    return "Trình duyệt đang chặn phát âm thanh. Hãy bấm Tiếp tục để nghe.";
  }
  return error instanceof TtsUserError && error.message ? error.message : GENERIC_TTS_ERROR;
}

function prepareAudioElement(
  audio: HTMLAudioElement,
  objectUrl: string,
  onEnded: () => void,
  onError: () => void,
) {
  audio.src = objectUrl;
  audio.preload = "auto";
  audio.onended = onEnded;
  audio.onerror = onError;
}

async function readApiError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as TtsApiError;
    const message = payload.error?.message;
    return typeof message === "string" && message.trim() ? message : GENERIC_TTS_ERROR;
  } catch {
    return GENERIC_TTS_ERROR;
  }
}

export function useTextToSpeech({
  active,
  disabled = false,
}: UseTextToSpeechOptions): TextToSpeechController {
  const [capability, setCapability] = useState<boolean | null>(null);
  const [phase, setPhase] = useState<TextToSpeechPhase>("idle");
  const [activeAssistantIndex, setActiveAssistantIndex] = useState<number | null>(null);
  const [error, setError] = useState<TextToSpeechError | null>(null);

  const mountedRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  const requestAbortRef = useRef<AbortController | null>(null);
  const generationRef = useRef(0);
  const loadSegmentRef = useRef<
    ((assistantIndex: number, segmentIndex: number, generation: number) => Promise<void>) | null
  >(null);

  const releaseObjectUrl = useCallback(() => {
    if (!objectUrlRef.current) return;
    URL.revokeObjectURL(objectUrlRef.current);
    objectUrlRef.current = null;
  }, []);

  const stopResources = useCallback(() => {
    generationRef.current += 1;
    requestAbortRef.current?.abort();
    requestAbortRef.current = null;

    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.onended = null;
      audio.onerror = null;
      audio.removeAttribute("src");
      audio.load();
    }
    releaseObjectUrl();
  }, [releaseObjectUrl]);

  const stop = useCallback(() => {
    stopResources();
    if (!mountedRef.current) return;
    setPhase("idle");
    setActiveAssistantIndex(null);
    setError(null);
  }, [stopResources]);

  const fail = useCallback(
    (assistantIndex: number, message: string, generation: number) => {
      if (!mountedRef.current || generation !== generationRef.current) return;
      generationRef.current += 1;
      requestAbortRef.current = null;
      const audio = audioRef.current;
      if (audio) {
        audio.pause();
        audio.onended = null;
        audio.onerror = null;
        audio.removeAttribute("src");
        audio.load();
      }
      releaseObjectUrl();
      setPhase("idle");
      setActiveAssistantIndex(null);
      setError({ assistantIndex, message });
    },
    [releaseObjectUrl],
  );

  const loadSegment = useCallback(
    async (assistantIndex: number, segmentIndex: number, generation: number) => {
      if (!mountedRef.current || generation !== generationRef.current) return;

      const controller = new AbortController();
      requestAbortRef.current?.abort();
      requestAbortRef.current = controller;
      setPhase("loading");

      try {
        const response = await fetch("/api/tts/speech", {
          body: JSON.stringify({
            assistant_index: assistantIndex,
            segment_index: segmentIndex,
          }),
          cache: "no-store",
          headers: { "Content-Type": "application/json" },
          method: "POST",
          signal: controller.signal,
        });
        if (!response.ok) throw new TtsUserError(await readApiError(response));
        if (!isMpegAudioContentType(response.headers.get("Content-Type"))) {
          throw new TtsUserError("Dịch vụ giọng đọc trả về định dạng âm thanh không hợp lệ.");
        }

        const metadata = parseTtsSegmentMetadata(response.headers, segmentIndex);
        if (!metadata) {
          throw new TtsUserError("Dịch vụ giọng đọc trả về thứ tự đoạn không hợp lệ.");
        }
        const declaredLength = response.headers.get("Content-Length");
        if (declaredLength && parseTtsContentLength(declaredLength) === null) {
          throw new TtsUserError("Đoạn giọng đọc vượt quá giới hạn cho phép.");
        }

        const audioBlob = await response.blob();
        if (
          audioBlob.size <= 0 ||
          audioBlob.size > DEFAULT_TTS_MAX_AUDIO_BYTES ||
          !isMpegAudioContentType(audioBlob.type)
        ) {
          throw new TtsUserError("Dữ liệu giọng đọc không hợp lệ.");
        }
        if (!mountedRef.current || generation !== generationRef.current) return;

        requestAbortRef.current = null;
        releaseObjectUrl();
        const objectUrl = URL.createObjectURL(audioBlob);
        objectUrlRef.current = objectUrl;
        const audio = audioRef.current ?? new Audio();
        audioRef.current = audio;
        prepareAudioElement(
          audio,
          objectUrl,
          () => {
            if (!mountedRef.current || generation !== generationRef.current) return;
            const nextSegmentIndex = getNextTtsSegmentIndex(metadata);
            if (nextSegmentIndex === null) {
              releaseObjectUrl();
              audio.removeAttribute("src");
              audio.load();
              setPhase("completed");
              return;
            }
            void loadSegmentRef.current?.(assistantIndex, nextSegmentIndex, generation);
          },
          () => {
            fail(assistantIndex, "Không thể phát đoạn giọng đọc này.", generation);
          },
        );

        try {
          await audio.play();
          if (mountedRef.current && generation === generationRef.current) {
            setPhase("playing");
          }
        } catch (playbackError) {
          if (mountedRef.current && generation === generationRef.current) {
            setPhase("paused");
            setError({
              assistantIndex,
              message: readablePlaybackError(playbackError),
            });
          }
        }
      } catch (requestError) {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        fail(assistantIndex, readablePlaybackError(requestError), generation);
      } finally {
        if (requestAbortRef.current === controller) requestAbortRef.current = null;
      }
    },
    [fail, releaseObjectUrl],
  );

  useEffect(() => {
    loadSegmentRef.current = loadSegment;
  }, [loadSegment]);

  const play = useCallback(
    async (assistantIndex: number) => {
      if (capability !== true || disabled || !Number.isSafeInteger(assistantIndex) || assistantIndex < 0) {
        return;
      }
      if (!confirmSpeechProviderUse()) return;
      stopResources();
      const generation = generationRef.current;
      setActiveAssistantIndex(assistantIndex);
      setError(null);
      await loadSegment(assistantIndex, 0, generation);
    },
    [capability, disabled, loadSegment, stopResources],
  );

  const pause = useCallback(() => {
    if (phase !== "playing") return;
    audioRef.current?.pause();
    setPhase("paused");
  }, [phase]);

  const resume = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio || phase !== "paused" || disabled) return;
    const generation = generationRef.current;
    try {
      await audio.play();
      if (mountedRef.current && generation === generationRef.current) {
        setError(null);
        setPhase("playing");
      }
    } catch (playbackError) {
      if (
        mountedRef.current &&
        generation === generationRef.current &&
        activeAssistantIndex !== null
      ) {
        setError({
          assistantIndex: activeAssistantIndex,
          message: readablePlaybackError(playbackError),
        });
      }
    }
  }, [activeAssistantIndex, disabled, phase]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      stopResources();
    };
  }, [stopResources]);

  useEffect(() => {
    if (!active || disabled) stop();
  }, [active, disabled, stop]);

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    void fetch("/api/tts/speech", {
      cache: "no-store",
      method: "GET",
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) return { enabled: false };
        return (await response.json()) as TtsCapabilityResponse;
      })
      .then((payload) => {
        if (mountedRef.current) setCapability(payload.enabled === true);
      })
      .catch((capabilityError: unknown) => {
        if (
          mountedRef.current &&
          !(capabilityError instanceof DOMException && capabilityError.name === "AbortError")
        ) {
          setCapability(false);
        }
      });
    return () => controller.abort();
  }, [active]);

  return {
    activeAssistantIndex,
    checking: active && capability === null,
    enabled: capability === true,
    error,
    phase,
    pause,
    play,
    resume,
    stop,
  };
}
