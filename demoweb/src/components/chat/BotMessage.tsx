"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";

import type { ChatSource } from "@/types/chat";

interface BotMessageProps {
  content: string;
  sources?: ChatSource[];
}

const CITATION_RE = /\[(\d+)\]/g;

function linkifyCitations(content: string, sources: ChatSource[]) {
  if (!sources.length) return content;
  return content.replace(CITATION_RE, (match, n) => {
    const source = sources[Number(n) - 1];
    return source ? `[${match}](${source.url})` : match;
  });
}

function isCitationNode(children: unknown): children is string {
  return typeof children === "string" && /^\[\d+\]$/.test(children);
}

export function BotMessage({ content, sources = [] }: BotMessageProps) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable
    }
  }

  const linked = linkifyCitations(content, sources);

  return (
    <div className="group relative max-w-[92%] whitespace-pre-wrap rounded-2xl rounded-tl-sm border border-[#e2e6ea] bg-white px-4 py-3 text-base leading-7 text-[#334155] shadow-sm">
      <div className="prose-chat">
        <ReactMarkdown
          components={{
            p: ({ children }) => <p className="leading-7">{children}</p>,
            ul: ({ children }) => <ul className="my-1 list-disc space-y-1 pl-5">{children}</ul>,
            ol: ({ children }) => <ol className="my-1 list-decimal space-y-1 pl-5">{children}</ol>,
            li: ({ children }) => <li className="leading-6">{children}</li>,
            a: ({ href, children }) =>
              isCitationNode(children) ? (
                <sup>
                  <a
                    className="ms-0.5 font-semibold text-[#903938] no-underline"
                    href={href}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {children}
                  </a>
                </sup>
              ) : (
                <a
                  className="font-semibold text-[#903938] underline decoration-[#ce7a58] underline-offset-2"
                  href={href}
                  rel="noreferrer"
                  target="_blank"
                >
                  {children}
                </a>
              ),
            strong: ({ children }) => <strong className="font-bold text-[#1e2f41]">{children}</strong>,
            code: ({ children }) => (
              <code className="rounded bg-[#f5f5f5] px-1 py-0.5 text-sm font-mono">{children}</code>
            ),
          }}
          rehypePlugins={[[rehypeSanitize]]}
          remarkPlugins={[remarkGfm]}
        >
          {linked}
        </ReactMarkdown>
      </div>

      {sources.length ? (
        <ol className="mt-2 space-y-1 border-t border-[#eee] pt-2 text-xs text-[#667085]">
          {sources.map((source, index) => (
            <li key={source.id}>
              <span className="font-semibold text-[#762b2b]">[{index + 1}]</span>{" "}
              <a
                className="font-semibold text-[#903938] underline decoration-[#ce7a58] underline-offset-2"
                href={source.url}
                rel="noreferrer"
                target="_blank"
              >
                {source.title}
              </a>
              <span className="block text-[10px]">
                {source.publisher} · kiểm chứng {source.verified_at}
              </span>
            </li>
          ))}
        </ol>
      ) : null}

      <button
        aria-label="Sao chép câu trả lời"
        className="absolute -top-2 right-1 flex size-7 items-center justify-center rounded-full border border-[#e2e6ea] bg-white text-[#5b6573] opacity-0 shadow-sm transition-opacity hover:bg-[#f5f5f5] focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ffc251] group-hover:opacity-100"
        onClick={() => void copy()}
        type="button"
      >
        {copied ? <Check className="size-3.5 text-[#28543a]" aria-hidden="true" /> : <Copy className="size-3.5" aria-hidden="true" />}
      </button>
    </div>
  );
}
