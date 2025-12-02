import React, { useEffect, useRef, useState } from "react";
import { Mic, Square } from "lucide-react";
import { Button, type ButtonProps } from "./button";

type MicButtonProps = Omit<ButtonProps, "onClick"> & {
  apiUrl: string;                // p.ej. `${import.meta.env.VITE_API_BASE_URL}/transcribe`
  modelName?: string;            // p.ej. "medium"
  language?: string;             // p.ej. "es"
  maxMs?: number;                // p.ej. 45000
  onTranscribed: (text: string) => void;
  onError?: (message: string) => void;
  xApiKey?: string;            
};

export default function MicButton({
  apiUrl,
  modelName = (import.meta as any).env?.VITE_STT_DEFAULT_LANG || "medium",
  language = (import.meta as any).env?.VITE_STT_DEFAULT_LANG || "es",
  maxMs = Number((import.meta as any).env?.VITE_STT_MAX_RECORDING_MS || 45000),
  onTranscribed,
  onError,
  xApiKey,
  className,
  variant = "outline",
  size = "icon",
  ...btnProps
}: MicButtonProps) {
  const [status, setStatus] = useState<"idle"|"recording"|"uploading">("idle");
  const [elapsed, setElapsed] = useState(0);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (status === "recording") {
      const started = Date.now();
      timerRef.current = window.setInterval(() => {
        const ms = Date.now() - started;
        setElapsed(ms);
        if (ms >= maxMs) stopRecording();
      }, 100);
      return () => {
        if (timerRef.current) window.clearInterval(timerRef.current);
      };
    } else {
      setElapsed(0);
    }
  }, [status, maxMs]);

  async function startRecording() {
    try {
      if (status !== "idle") return;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType: mime });
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        try {
          setStatus("uploading");
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
          await sendToApi(blob);
        } catch (err: any) {
          onError?.(err?.message || "Error al subir/transcribir");
        } finally {
          cleanupStream();
          setStatus("idle");
        }
      };

      recorder.start(100); // recolecta cada 100ms
      setStatus("recording");
    } catch (err: any) {
      onError?.(err?.message || "No se pudo acceder al micrófono");
      cleanupStream();
      setStatus("idle");
    }
  }

  function stopRecording() {
    try {
      if (recorderRef.current && status === "recording") {
        recorderRef.current.stop();
      } else {
        cleanupStream();
        setStatus("idle");
      }
    } catch {
      cleanupStream();
      setStatus("idle");
    }
  }

  function cleanupStream() {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    recorderRef.current?.stream.getTracks().forEach((t) => t.stop());
    recorderRef.current = null;
    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;
    chunksRef.current = [];
  }

  async function sendToApi(blob: Blob) {
    const form = new FormData();
    const file = new File([blob], "audio.webm", { type: blob.type || "audio/webm" });
    form.append("file", file);
    if (modelName) form.append("model_name", modelName);
    if (language) form.append("language", language);

    const headers: Record<string,string> = {};
    if (xApiKey) headers["X-API-KEY"] = xApiKey;

    const res = await fetch(apiUrl, {
      method: "POST",
      body: form,
      headers,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(text || `HTTP ${res.status}`);
    }
    const data = await res.json();
    const text = (data?.text || "").trim();
    if (!text) throw new Error("Transcripción vacía");
    onTranscribed(text);
  }

  const isRecording = status === "recording";
  const isUploading = status === "uploading";

  const label =
    isUploading ? "Enviando…" :
    isRecording ? `${Math.min(Math.round(elapsed/100)/10, Math.round(maxMs/100)/10)}s` :
    "Hablar";

  return (
    <Button
      type="button"
      onClick={() => (isRecording ? stopRecording() : startRecording())}
      disabled={isUploading}
      className={className}
      variant={variant}
      size={size}
      title={isRecording ? "Detener" : "Grabar audio"}
      {...btnProps}
    >
      {isRecording ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
      <span className="sr-only">{label}</span>
    </Button>
  );
}
