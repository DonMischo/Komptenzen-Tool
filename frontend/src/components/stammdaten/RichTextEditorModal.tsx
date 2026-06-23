"use client";

import { useEffect } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import TextAlign from "@tiptap/extension-text-align";
import Underline from "@tiptap/extension-underline";
import { Table, TableRow, TableHeader, TableCell } from "@tiptap/extension-table";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  AlignLeft,
  AlignCenter,
  AlignRight,
  List,
  ListOrdered,
  Table as TableIcon,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  title: string;
  initialHtml: string;
  open: boolean;
  saving?: boolean;
  onSave: (html: string) => void;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------

export function RichTextEditorModal({
  title,
  initialHtml,
  open,
  saving,
  onSave,
  onClose,
}: Props) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      TextAlign.configure({ types: ["heading", "paragraph"] }),
      Underline,
      Table.configure({ resizable: false }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content: initialHtml,
    editorProps: {
      attributes: { class: "focus:outline-none min-h-[200px] px-1" },
      transformPastedHTML(html) {
        // Strip Word/Office conditional comments and namespace tags
        let clean = html
          .replace(/<!--\[if[^>]*>[\s\S]*?<!\[endif\]-->/gi, "")
          .replace(/<\/?o:[^>]*>/gi, "")
          .replace(/<\/?w:[^>]*>/gi, "")
          .replace(/<\/?m:[^>]*>/gi, "");

        // Remove mso-* inline style properties
        clean = clean.replace(/\s*mso-[^;:"']+:[^;]+;?/gi, "");

        // Strip invisible Unicode: zero-width chars, soft hyphen, BOM
        clean = clean.replace(/[­​-‏﻿�]/g, "");
        // Non-breaking space → regular space
        clean = clean.replace(/ /g, " ");

        // Unwrap Word frame tables: single-cell <table> → just the cell content
        const div = document.createElement("div");
        div.innerHTML = clean;
        div.querySelectorAll("table").forEach((table) => {
          const cells = Array.from(table.querySelectorAll("td, th"));
          if (cells.length === 1) {
            const frag = document.createDocumentFragment();
            while (cells[0].firstChild) frag.appendChild(cells[0].firstChild);
            table.parentNode?.replaceChild(frag, table);
          }
        });
        return div.innerHTML;
      },
      transformPastedText(text) {
        // Strip invisible chars from plain-text paste too
        return text.replace(/[­​-‏﻿�]/g, "").replace(/ /g, " ");
      },
    },
  });

  // Re-sync content whenever the modal opens for a different student
  useEffect(() => {
    if (editor && open) {
      editor.commands.setContent(initialHtml, { emitUpdate: false });
    }
  }, [open, initialHtml, editor]);

  const handleSave = () => {
    if (!editor) return;
    onSave(editor.getHTML());
  };

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50
                     bg-white rounded-xl shadow-xl
                     w-[820px] max-w-[95vw] max-h-[90vh]
                     flex flex-col"
          onInteractOutside={(e) => e.preventDefault()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b shrink-0">
            <Dialog.Title className="font-semibold text-base truncate pr-4">
              {title}
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="text-muted-foreground hover:text-foreground shrink-0">
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          {/* Toolbar */}
          <div className="flex flex-wrap items-center gap-0.5 px-3 py-2 border-b bg-muted/30 shrink-0">
            <ToolBtn
              onClick={() => editor?.chain().focus().toggleBold().run()}
              active={!!editor?.isActive("bold")}
              title="Fett (Strg+B)"
            >
              <Bold className="h-4 w-4" />
            </ToolBtn>
            <ToolBtn
              onClick={() => editor?.chain().focus().toggleItalic().run()}
              active={!!editor?.isActive("italic")}
              title="Kursiv (Strg+I)"
            >
              <Italic className="h-4 w-4" />
            </ToolBtn>
            <ToolBtn
              onClick={() => editor?.chain().focus().toggleUnderline().run()}
              active={!!editor?.isActive("underline")}
              title="Unterstrichen (Strg+U)"
            >
              <UnderlineIcon className="h-4 w-4" />
            </ToolBtn>

            <Divider />

            <ToolBtn
              onClick={() => editor?.chain().focus().setTextAlign("left").run()}
              active={!!editor?.isActive({ textAlign: "left" })}
              title="Linksbündig"
            >
              <AlignLeft className="h-4 w-4" />
            </ToolBtn>
            <ToolBtn
              onClick={() => editor?.chain().focus().setTextAlign("center").run()}
              active={!!editor?.isActive({ textAlign: "center" })}
              title="Zentriert"
            >
              <AlignCenter className="h-4 w-4" />
            </ToolBtn>
            <ToolBtn
              onClick={() => editor?.chain().focus().setTextAlign("right").run()}
              active={!!editor?.isActive({ textAlign: "right" })}
              title="Rechtsbündig"
            >
              <AlignRight className="h-4 w-4" />
            </ToolBtn>

            <Divider />

            <ToolBtn
              onClick={() => editor?.chain().focus().toggleBulletList().run()}
              active={!!editor?.isActive("bulletList")}
              title="Aufzählung"
            >
              <List className="h-4 w-4" />
            </ToolBtn>
            <ToolBtn
              onClick={() => editor?.chain().focus().toggleOrderedList().run()}
              active={!!editor?.isActive("orderedList")}
              title="Nummerierte Liste"
            >
              <ListOrdered className="h-4 w-4" />
            </ToolBtn>

            <Divider />

            <ToolBtn
              onClick={() =>
                editor
                  ?.chain()
                  .focus()
                  .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
                  .run()
              }
              active={false}
              title="Tabelle einfügen (3×3)"
            >
              <TableIcon className="h-4 w-4" />
            </ToolBtn>
          </div>

          {/* Editor area */}
          <div className="flex-1 overflow-y-auto px-5 py-4 min-h-0">
            <EditorContent editor={editor} />
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 px-5 py-4 border-t shrink-0">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm border rounded-md hover:bg-muted transition-colors"
            >
              Schließen
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 text-sm bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {saving ? "Speichern…" : "Speichern"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function ToolBtn({
  onClick,
  active,
  title,
  children,
}: {
  onClick: () => void;
  active: boolean;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      // mousedown prevents the editor from losing focus
      onMouseDown={(e) => {
        e.preventDefault();
        onClick();
      }}
      title={title}
      className={cn(
        "p-1.5 rounded text-sm transition-colors",
        active
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      )}
    >
      {children}
    </button>
  );
}

function Divider() {
  return <div className="w-px h-5 bg-border mx-1" />;
}
