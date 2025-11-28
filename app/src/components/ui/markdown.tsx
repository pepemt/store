import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownProps {
  children: string;
  className?: string;
}

export function Markdown({ children, className = "" }: MarkdownProps) {
  return (
    <div className={`prose prose-sm max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
        // Headings
        h1: ({ children }) => (
          <h1 className="text-lg font-bold mt-3 mb-2 first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-base font-bold mt-3 mb-2 first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm font-bold mt-2 mb-1 first:mt-0">{children}</h3>
        ),
        // Paragraphs
        p: ({ children }) => (
          <p className="text-sm mb-2 last:mb-0 leading-relaxed">{children}</p>
        ),
        // Lists
        ul: ({ children }) => (
          <ul className="list-disc pl-4 mb-2 space-y-0.5 text-sm [&_p]:inline [&_p]:mb-0">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal pl-4 mb-2 space-y-0.5 text-sm [&_p]:inline [&_p]:mb-0">{children}</ol>
        ),
        li: ({ children }) => <li className="text-sm">{children}</li>,
        // Code
        code: ({ className, children, ...props }) => {
          const isInline = !className;
          if (isInline) {
            return (
              <code
                className="bg-gray-100 text-[#6e348d] px-1.5 py-0.5 rounded text-xs font-mono"
                {...props}
              >
                {children}
              </code>
            );
          }
          return (
            <code
              className="block bg-gray-900 text-gray-100 p-3 rounded-lg text-xs font-mono overflow-x-auto my-2"
              {...props}
            >
              {children}
            </code>
          );
        },
        pre: ({ children }) => <pre className="my-2">{children}</pre>,
        // Links
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#6e348d] hover:underline font-medium"
          >
            {children}
          </a>
        ),
        // Blockquote
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-[#6e348d] pl-3 my-2 italic text-gray-600 text-sm">
            {children}
          </blockquote>
        ),
        // Strong and emphasis
        strong: ({ children }) => (
          <strong className="font-semibold">{children}</strong>
        ),
        em: ({ children }) => <em className="italic">{children}</em>,
        // Horizontal rule
        hr: () => <hr className="my-3 border-gray-200" />,
        // Tables (GFM)
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="min-w-full text-sm border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-gray-100">{children}</thead>
        ),
        tbody: ({ children }) => <tbody>{children}</tbody>,
        tr: ({ children }) => (
          <tr className="border-b border-gray-200">{children}</tr>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left font-semibold text-gray-700">{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2 text-gray-600">{children}</td>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
    </div>
  );
}
