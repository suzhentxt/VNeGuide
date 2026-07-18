"use client";

import { Check, Pencil, X } from "lucide-react";
import { useState } from "react";

import type { ChatSuggestion, JsonValue } from "@/types/chat";

function displayValue(value: JsonValue) {
  if (value === null) return "Chưa có";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function parseEditedValue(value: string, original: JsonValue): JsonValue {
  if (typeof original === "number") {
    const number = Number(value);
    return Number.isFinite(number) ? number : value;
  }
  if (typeof original === "boolean") {
    if (value.toLowerCase() === "true") return true;
    if (value.toLowerCase() === "false") return false;
  }
  if (typeof original === "object" && original !== null) {
    try {
      return JSON.parse(value) as JsonValue;
    } catch {
      return value;
    }
  }
  return value;
}

interface SuggestionCardProps {
  suggestion: ChatSuggestion;
  disabled: boolean;
  fieldLocked?: boolean;
  onResolve: (
    suggestion: ChatSuggestion,
    action: "accept" | "reject" | "edit",
    value?: JsonValue,
  ) => Promise<void>;
}

export function SuggestionCard({
  suggestion,
  disabled,
  fieldLocked = false,
  onResolve,
}: SuggestionCardProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(displayValue(suggestion.suggested_value));
  const pending = suggestion.status === "pending";

  return (
    <article className="rounded-lg border border-[#e6c6b9] bg-[#fffdfa] p-3 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold tracking-wide text-[#903938] uppercase">
            Đề xuất thông tin
          </p>
          <h4 className="mt-1 font-bold text-[#1e2f41]">{suggestion.label}</h4>
        </div>
        {!pending ? (
          <span className="rounded-full bg-[#eef6f1] px-2 py-1 text-xs font-semibold text-[#25633f]">
            {suggestion.status === "accepted"
              ? "Đã chấp nhận"
              : suggestion.status === "edited"
                ? "Đã chỉnh sửa"
                : "Đã từ chối"}
          </span>
        ) : null}
      </div>

      {editing ? (
        <SuggestionEditor
          disabled={disabled}
          label={suggestion.label}
          onChange={setValue}
          originalValue={suggestion.suggested_value}
          value={value}
        />
      ) : (
        <p className="mt-3 whitespace-pre-wrap rounded-md bg-white px-3 py-2 font-semibold text-[#1e2f41]">
          {displayValue(suggestion.suggested_value)}
        </p>
      )}

      {suggestion.evidence ? (
        <p className="mt-2 text-sm text-[#667085]">
          <span className="font-semibold">Từ nội dung:</span> “{suggestion.evidence}”
        </p>
      ) : null}

      {fieldLocked && pending ? (
        <p className="mt-2 rounded-md bg-[#fff4e5] px-3 py-2 text-sm text-[#7a4b00]">
          Bạn đã sửa field này trực tiếp trên form. Có thể từ chối đề xuất, nhưng AI không được ghi đè giá trị hiện tại.
        </p>
      ) : null}

      {pending ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {editing ? (
            <>
              <button
                className="inline-flex min-h-10 items-center gap-1.5 rounded-md bg-[#903938] px-3 text-sm font-bold text-white hover:bg-[#762b2b] disabled:opacity-50"
                disabled={disabled || fieldLocked || !value.trim()}
                onClick={() =>
                  void onResolve(
                    suggestion,
                    "edit",
                    parseEditedValue(value, suggestion.suggested_value),
                  ).then(() => setEditing(false))
                }
                type="button"
              >
                <Check className="size-4" aria-hidden="true" />
                Lưu chỉnh sửa
              </button>
              <button
                className="min-h-10 rounded-md border border-[#c9cdcf] bg-white px-3 text-sm font-semibold hover:bg-[#f5f5f5]"
                disabled={disabled || fieldLocked}
                onClick={() => setEditing(false)}
                type="button"
              >
                Hủy
              </button>
            </>
          ) : (
            <>
              <button
                className="inline-flex min-h-10 items-center gap-1.5 rounded-md bg-[#903938] px-3 text-sm font-bold text-white hover:bg-[#762b2b] disabled:opacity-50"
                disabled={disabled || fieldLocked}
                onClick={() => void onResolve(suggestion, "accept")}
                type="button"
              >
                <Check className="size-4" aria-hidden="true" />
                Chấp nhận
              </button>
              <button
                className="inline-flex min-h-10 items-center gap-1.5 rounded-md border border-[#ce7a58] bg-white px-3 text-sm font-semibold text-[#903938] hover:bg-[#fff4ef] disabled:opacity-50"
                disabled={disabled || fieldLocked}
                onClick={() => setEditing(true)}
                type="button"
              >
                <Pencil className="size-4" aria-hidden="true" />
                Sửa
              </button>
              <button
                className="inline-flex min-h-10 items-center gap-1.5 rounded-md border border-[#d8dee8] bg-white px-3 text-sm font-semibold text-[#5b6573] hover:bg-[#f5f5f5] disabled:opacity-50"
                disabled={disabled}
                onClick={() => void onResolve(suggestion, "reject")}
                type="button"
              >
                <X className="size-4" aria-hidden="true" />
                Từ chối
              </button>
            </>
          )}
        </div>
      ) : null}
    </article>
  );
}

interface SuggestionEditorProps {
  disabled: boolean;
  label: string;
  onChange: (value: string) => void;
  originalValue: JsonValue;
  value: string;
}

function SuggestionEditor({
  disabled,
  label,
  onChange,
  originalValue,
  value,
}: SuggestionEditorProps) {
  const isBoolean = typeof originalValue === "boolean";
  const isNumber = typeof originalValue === "number";
  const isObject = typeof originalValue === "object" && originalValue !== null;
  const isLongText = !isBoolean && !isNumber && !isObject && value.length > 60;

  if (isBoolean) {
    return (
      <div className="mt-3 flex gap-2">
        {[
          { label: "Có", val: "true" },
          { label: "Không", val: "false" },
        ].map((opt) => (
          <button
            aria-pressed={value.toLowerCase() === opt.val}
            className={`inline-flex min-h-10 flex-1 items-center justify-center rounded-md border-2 px-3 text-sm font-bold transition-colors disabled:opacity-50 ${
              value.toLowerCase() === opt.val
                ? "border-[#903938] bg-[#903938] text-white"
                : "border-[#ce7a58] bg-white text-[#762b2b] hover:bg-[#fff4ef]"
            }`}
            disabled={disabled}
            key={opt.val}
            onClick={() => onChange(opt.val)}
            type="button"
          >
            {opt.label}
          </button>
        ))}
      </div>
    );
  }

  if (isNumber) {
    return (
      <input
        aria-label={`Sửa ${label}`}
        className="mt-3 min-h-10 w-full rounded-md border border-[#c9cdcf] bg-white px-3 py-2 text-sm focus:border-[#ce7a58] focus:outline-none focus:ring-2 focus:ring-[#ce7a58]/25"
        disabled={disabled}
        inputMode="decimal"
        onChange={(event) => onChange(event.target.value)}
        type="number"
        value={value}
      />
    );
  }

  if (isLongText || isObject) {
    return (
      <textarea
        aria-label={`Sửa ${label}`}
        className="mt-3 min-h-20 w-full resize-y rounded-md border border-[#c9cdcf] bg-white px-3 py-2 text-sm focus:border-[#ce7a58] focus:outline-none focus:ring-2 focus:ring-[#ce7a58]/25"
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      />
    );
  }

  return (
    <input
      aria-label={`Sửa ${label}`}
      className="mt-3 min-h-10 w-full rounded-md border border-[#c9cdcf] bg-white px-3 py-2 text-sm focus:border-[#ce7a58] focus:outline-none focus:ring-2 focus:ring-[#ce7a58]/25"
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      type="text"
      value={value}
    />
  );
}
