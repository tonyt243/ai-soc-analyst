import ReactMarkdown from "react-markdown";

export function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        strong: ({ children }) => <strong className="font-semibold text-inherit">{children}</strong>,
        em: ({ children }) => <em className="italic text-inherit">{children}</em>,
        code: ({ children }) => (
          <code className="rounded bg-void/60 px-1 py-0.5 font-mono text-[0.85em] text-accent">{children}</code>
        ),
        ul: ({ children }) => <ul className="mb-2 ml-4 list-disc space-y-1 last:mb-0">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal space-y-1 last:mb-0">{children}</ol>,
        li: ({ children }) => <li>{children}</li>,
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
