import React, { useState, useEffect, useRef } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import { StarterKit } from '@tiptap/starter-kit';
import { Underline } from '@tiptap/extension-underline';
import { TextAlign } from '@tiptap/extension-text-align';
import { TextStyle } from '@tiptap/extension-text-style';
import { Color } from '@tiptap/extension-color';
import { Highlight } from '@tiptap/extension-highlight';
import { Superscript } from '@tiptap/extension-superscript';
import { Subscript } from '@tiptap/extension-subscript';
import { Link } from '@tiptap/extension-link';
import { Table } from '@tiptap/extension-table';
import { TableRow } from '@tiptap/extension-table-row';
import { TableHeader } from '@tiptap/extension-table-header';
import { TableCell } from '@tiptap/extension-table-cell';
import { TaskList } from '@tiptap/extension-task-list';
import { TaskItem } from '@tiptap/extension-task-item';
import { FontFamily } from '@tiptap/extension-font-family';
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import * as Icons from 'lucide-react';

// --- CUSTOM EXTENSIONS ---

// Font Size Extension
const FontSize = Extension.create({
  name: 'fontSize',
  addOptions() {
    return { types: ['textStyle'] };
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          fontSize: {
            default: null,
            parseHTML: element => element.style.fontSize,
            renderHTML: attributes => {
              if (!attributes.fontSize) return {};
              return { style: `font-size: ${attributes.fontSize}` };
            },
          },
        },
      },
    ];
  },
  addCommands() {
    return {
      setFontSize: fontSize => ({ chain }) => {
        return chain().setMark('textStyle', { fontSize }).run();
      },
      unsetFontSize: () => ({ chain }) => {
        return chain().setMark('textStyle', { fontSize: null }).run();
      },
    };
  },
});

// Line Height (Line Spacing) Extension
const LineHeight = Extension.create({
  name: 'lineHeight',
  addOptions() {
    return { types: ['paragraph', 'heading'] };
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          lineHeight: {
            default: null,
            parseHTML: element => element.style.lineHeight,
            renderHTML: attributes => {
              if (!attributes.lineHeight) return {};
              return { style: `line-height: ${attributes.lineHeight}` };
            },
          },
        },
      },
    ];
  },
  addCommands() {
    return {
      setLineHeight: lineHeight => ({ commands }) => {
        return this.options.types.every(type =>
          commands.updateAttributes(type, { lineHeight })
        );
      },
    };
  },
});

// Paragraph Spacing Extension
const ParagraphSpacing = Extension.create({
  name: 'paragraphSpacing',
  addOptions() {
    return { types: ['paragraph', 'heading'] };
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          paragraphSpacing: {
            default: null,
            parseHTML: element => element.style.marginBottom,
            renderHTML: attributes => {
              if (!attributes.paragraphSpacing) return {};
              return { style: `margin-bottom: ${attributes.paragraphSpacing}; margin-top: 0px;` };
            },
          },
        },
      },
    ];
  },
  addCommands() {
    return {
      setParagraphSpacing: spacing => ({ commands }) => {
        return this.options.types.every(type =>
          commands.updateAttributes(type, { paragraphSpacing: spacing })
        );
      },
    };
  },
});

// Indentation Extension
const Indent = Extension.create({
  name: 'indent',
  addOptions() {
    return {
      types: ['paragraph', 'heading', 'listItem'],
      minLevel: 0,
      maxLevel: 10,
    };
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          indent: {
            default: null,
            parseHTML: element => {
              const paddingLeft = element.style.paddingLeft;
              return paddingLeft ? parseInt(paddingLeft, 10) / 24 : null;
            },
            renderHTML: attributes => {
              if (!attributes.indent) return {};
              return { style: `padding-left: ${attributes.indent * 24}px` };
            },
          },
        },
      },
    ];
  },
  addCommands() {
    return {
      indent: () => ({ tr, state, commands }) => {
        const { selection } = state;
        let indentLevel = 0;
        state.doc.nodesBetween(selection.from, selection.to, node => {
          if (this.options.types.includes(node.type.name)) {
            indentLevel = Math.min((node.attrs.indent || 0) + 1, this.options.maxLevel);
          }
        });
        return this.options.types.every(type =>
          commands.updateAttributes(type, { indent: indentLevel })
        );
      },
      outdent: () => ({ tr, state, commands }) => {
        const { selection } = state;
        let indentLevel = 0;
        state.doc.nodesBetween(selection.from, selection.to, node => {
          if (this.options.types.includes(node.type.name)) {
            indentLevel = Math.max((node.attrs.indent || 0) - 1, this.options.minLevel);
          }
        });
        return this.options.types.every(type =>
          commands.updateAttributes(type, { indent: indentLevel || null })
        );
      },
    };
  },
});

// Border & Custom Cell Styling Commands for Table
const CustomTableStyles = Extension.create({
  name: 'customTableStyles',
  addCommands() {
    return {
      setCellBorder: borderStyle => ({ state, dispatch }) => {
        const { selection } = state;
        let tr = state.tr;
        state.doc.nodesBetween(selection.from, selection.to, (node, pos) => {
          if (node.type.name === 'tableCell' || node.type.name === 'tableHeader') {
            const attrs = { ...node.attrs };
            const style = attrs.style || '';
            const cleanStyle = style.replace(/border:[^;]+;?/g, '');
            attrs.style = `${cleanStyle} border: ${borderStyle};`.trim();
            tr = tr.setNodeMarkup(pos, null, attrs);
          }
        });
        if (dispatch) dispatch(tr);
        return true;
      },
      setCellAlignment: alignment => ({ state, dispatch }) => {
        const { selection } = state;
        let tr = state.tr;
        state.doc.nodesBetween(selection.from, selection.to, (node, pos) => {
          if (node.type.name === 'tableCell' || node.type.name === 'tableHeader') {
            const attrs = { ...node.attrs };
            const style = attrs.style || '';
            const cleanStyle = style.replace(/vertical-align:[^;]+;?/g, '');
            attrs.style = `${cleanStyle} vertical-align: ${alignment};`.trim();
            tr = tr.setNodeMarkup(pos, null, attrs);
          }
        });
        if (dispatch) dispatch(tr);
        return true;
      }
    };
  }
});

// Find and Replace Extension
const FindAndReplace = Extension.create({
  name: 'findAndReplace',
  addOptions() {
    return {
      searchTerm: '',
      replaceTerm: '',
    };
  },
  addCommands() {
    return {
      find: term => ({ editor }) => {
        this.options.searchTerm = term;
        editor.view.dispatch(editor.state.tr);
        return true;
      },
      replaceNext: (term, replaceTerm) => ({ editor, state, dispatch }) => {
        if (!term) return false;
        let found = false;
        state.doc.descendants((node, pos) => {
          if (node.isText && !found) {
            const text = node.text || '';
            const index = text.indexOf(term);
            if (index !== -1) {
              const start = pos + index;
              const end = start + term.length;
              const tr = state.tr.replaceWith(start, end, state.schema.text(replaceTerm));
              if (dispatch) dispatch(tr);
              found = true;
            }
          }
        });
        return found;
      },
      replaceAll: (term, replaceTerm) => ({ editor, state, dispatch }) => {
        if (!term) return false;
        let tr = state.tr;
        let offset = 0;
        state.doc.descendants((node, pos) => {
          if (node.isText) {
            const text = node.text || '';
            let index = text.indexOf(term);
            while (index !== -1) {
              const start = pos + index + offset;
              const end = start + term.length;
              tr = tr.replaceWith(start, end, state.schema.text(replaceTerm));
              offset += replaceTerm.length - term.length;
              index = text.indexOf(term, index + 1);
            }
          }
        });
        if (dispatch) dispatch(tr);
        return true;
      },
    };
  },
  addProseMirrorPlugins() {
    const extension = this;
    return [
      new Plugin({
        key: new PluginKey('findAndReplace'),
        state: {
          init() { return DecorationSet.empty; },
          apply(tr) {
            const searchTerm = extension.options.searchTerm;
            if (!searchTerm) return DecorationSet.empty;
            const doc = tr.doc;
            const decorations = [];
            doc.descendants((node, pos) => {
              if (node.isText) {
                const text = node.text || '';
                let index = text.indexOf(searchTerm);
                while (index !== -1) {
                  const start = pos + index;
                  const end = start + searchTerm.length;
                  decorations.push(
                    Decoration.inline(start, end, {
                      class: 'find-replace-highlight',
                      style: 'background-color: rgba(234, 179, 8, 0.4); border-bottom: 2px solid #eab308; color: inherit;',
                    })
                  );
                  index = text.indexOf(searchTerm, index + 1);
                }
              }
            });
            return DecorationSet.create(doc, decorations);
          },
        },
        props: {
          decorations(state) {
            return this.getState(state);
          },
        },
      }),
    ];
  },
});

// --- EDITOR COMPONENT ---

export default function RichTextEditor({ value, onChange, disabled }) {
  const [fontFamily, setFontFamily] = useState('Inter');
  const [fontSize, setFontSize] = useState('16px');
  const [headingLevel, setHeadingLevel] = useState('p');
  const [lineSpacing, setLineSpacing] = useState('1.5');
  const [paragraphSpacing, setParagraphSpacing] = useState('16px');
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // Color Pickers
  const [showTextColor, setShowTextColor] = useState(false);
  const [showBgColor, setShowBgColor] = useState(false);
  const [showCellColor, setShowCellColor] = useState(false);
  
  // Find and Replace Panel
  const [showFindReplace, setShowFindReplace] = useState(false);
  const [findText, setFindText] = useState('');
  const [replaceText, setReplaceText] = useState('');

  // Dropdowns
  const [showTableMenu, setShowTableMenu] = useState(false);
  const [showBordersMenu, setShowBordersMenu] = useState(false);

  const colors = [
    '#000000', '#4b5563', '#9ca3af', '#ffffff', 
    '#ef4444', '#f97316', '#eab308', '#22c55e', 
    '#3b82f6', '#6366f1', '#a855f7', '#ec4899'
  ];

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        bulletList: { keepMarks: true },
        orderedList: { keepMarks: true },
      }),
      Underline,
      TextAlign.configure({
        types: ['heading', 'paragraph', 'tableCell', 'tableHeader'],
      }),
      TextStyle,
      Color,
      Highlight.configure({ multicolor: true }),
      Superscript,
      Subscript,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          style: 'color: var(--primary); text-decoration: underline; cursor: pointer;'
        }
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
      TaskList,
      TaskItem.configure({
        nested: true,
      }),
      FontFamily,
      FontSize,
      LineHeight,
      ParagraphSpacing,
      Indent,
      CustomTableStyles,
      FindAndReplace,
    ],
    content: value || '',
    editable: !disabled,
    onUpdate({ editor }) {
      onChange({ target: { value: editor.getHTML() } });
    },
  });

  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.commands.setContent(value || '');
    }
  }, [value, editor]);

  if (!editor) return null;

  const addLink = () => {
    const url = window.prompt('Enter URL:');
    if (url) {
      editor.chain().focus().setLink({ href: url }).run();
    } else {
      editor.chain().focus().unsetLink().run();
    }
  };

  const insertTable = () => {
    editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
    setShowTableMenu(false);
  };

  const handleFind = () => {
    editor.commands.find(findText);
  };

  const handleReplace = () => {
    editor.commands.replaceNext(findText, replaceText);
  };

  const handleReplaceAll = () => {
    editor.commands.replaceAll(findText, replaceText);
  };

  return (
    <div className={`word-editor-wrapper ${isFullscreen ? 'word-editor-fullscreen' : ''}`}>
      {/* WORD OFFICE STYLE TOOLBAR */}
      <div className="word-editor-toolbar">
        {/* ROW 1 */}
        <div className="word-toolbar-row">
          {/* Undo/Redo & Basic Editing */}
          <div className="word-toolbar-group">
            <button 
              type="button" 
              title="Undo"
              onClick={() => editor.chain().focus().undo().run()}
              disabled={!editor.can().undo()}
              className="word-toolbar-btn"
            >
              <Icons.Undo2 size={16} />
            </button>
            <button 
              type="button" 
              title="Redo"
              onClick={() => editor.chain().focus().redo().run()}
              disabled={!editor.can().redo()}
              className="word-toolbar-btn"
            >
              <Icons.Redo2 size={16} />
            </button>
          </div>

          {/* Heading & Font Family & Size Dropdowns */}
          <div className="word-toolbar-group">
            <select
              value={headingLevel}
              onChange={(e) => {
                const val = e.target.value;
                setHeadingLevel(val);
                if (val === 'p') {
                  editor.chain().focus().setParagraph().run();
                } else {
                  editor.chain().focus().toggleHeading({ level: parseInt(val, 10) }).run();
                }
              }}
              className="word-toolbar-select"
              title="Heading Style"
            >
              <option value="p">Paragraph</option>
              <option value="1">Heading 1</option>
              <option value="2">Heading 2</option>
              <option value="3">Heading 3</option>
              <option value="4">Heading 4</option>
              <option value="5">Heading 5</option>
              <option value="6">Heading 6</option>
            </select>

            <select
              value={fontFamily}
              onChange={(e) => {
                setFontFamily(e.target.value);
                editor.chain().focus().setFontFamily(e.target.value).run();
              }}
              className="word-toolbar-select font-family-select"
              title="Font Family"
            >
              <option value="Inter">Inter</option>
              <option value="Arial">Arial</option>
              <option value="Calibri">Calibri</option>
              <option value="Georgia">Georgia</option>
              <option value="Times New Roman">Times New Roman</option>
              <option value="Courier New">Courier New</option>
              <option value="Verdana">Verdana</option>
            </select>

            <select
              value={fontSize}
              onChange={(e) => {
                setFontSize(e.target.value);
                editor.chain().focus().setFontSize(e.target.value).run();
              }}
              className="word-toolbar-select font-size-select"
              title="Font Size"
            >
              {['8px', '10px', '12px', '14px', '16px', '18px', '20px', '24px', '28px', '32px', '36px', '48px'].map(sz => (
                <option key={sz} value={sz}>{sz}</option>
              ))}
            </select>
          </div>

          {/* Text Formatting: Bold, Italic, Underline, Strike, Super, Sub */}
          <div className="word-toolbar-group">
            <button
              type="button"
              title="Bold"
              onClick={() => editor.chain().focus().toggleBold().run()}
              className={`word-toolbar-btn ${editor.isActive('bold') ? 'active' : ''}`}
            >
              <Icons.Bold size={16} />
            </button>
            <button
              type="button"
              title="Italic"
              onClick={() => editor.chain().focus().toggleItalic().run()}
              className={`word-toolbar-btn ${editor.isActive('italic') ? 'active' : ''}`}
            >
              <Icons.Italic size={16} />
            </button>
            <button
              type="button"
              title="Underline"
              onClick={() => editor.chain().focus().toggleUnderline().run()}
              className={`word-toolbar-btn ${editor.isActive('underline') ? 'active' : ''}`}
            >
              <Icons.Underline size={16} />
            </button>
            <button
              type="button"
              title="Strikethrough"
              onClick={() => editor.chain().focus().toggleStrike().run()}
              className={`word-toolbar-btn ${editor.isActive('strike') ? 'active' : ''}`}
            >
              <Icons.Strikethrough size={16} />
            </button>
            <button
              type="button"
              title="Superscript"
              onClick={() => editor.chain().focus().toggleSuperscript().run()}
              className={`word-toolbar-btn ${editor.isActive('superscript') ? 'active' : ''}`}
            >
              <Icons.Superscript size={16} />
            </button>
            <button
              type="button"
              title="Subscript"
              onClick={() => editor.chain().focus().toggleSubscript().run()}
              className={`word-toolbar-btn ${editor.isActive('subscript') ? 'active' : ''}`}
            >
              <Icons.Subscript size={16} />
            </button>
          </div>

          {/* Colors & Format Clearing */}
          <div className="word-toolbar-group">
            <div className="word-popover-anchor">
              <button
                type="button"
                title="Text Color"
                onClick={() => { setShowTextColor(!showTextColor); setShowBgColor(false); }}
                className="word-toolbar-btn color-picker-btn"
              >
                <Icons.Type size={16} />
                <div className="color-strip" style={{ backgroundColor: editor.getAttributes('textStyle').color || '#000' }} />
              </button>
              {showTextColor && (
                <div className="word-color-picker-popover">
                  {colors.map(color => (
                    <div 
                      key={color} 
                      className="color-picker-cell" 
                      style={{ backgroundColor: color }}
                      onClick={() => {
                        editor.chain().focus().setColor(color).run();
                        setShowTextColor(false);
                      }}
                    />
                  ))}
                  <button 
                    type="button" 
                    className="clear-color-btn"
                    onClick={() => {
                      editor.chain().focus().unsetColor().run();
                      setShowTextColor(false);
                    }}
                  >
                    Reset
                  </button>
                </div>
              )}
            </div>

            <div className="word-popover-anchor">
              <button
                type="button"
                title="Highlight Color"
                onClick={() => { setShowBgColor(!showBgColor); setShowTextColor(false); }}
                className="word-toolbar-btn color-picker-btn"
              >
                <Icons.Highlighter size={16} />
              </button>
              {showBgColor && (
                <div className="word-color-picker-popover">
                  {colors.map(color => (
                    <div 
                      key={color} 
                      className="color-picker-cell" 
                      style={{ backgroundColor: color }}
                      onClick={() => {
                        editor.chain().focus().setHighlight({ color }).run();
                        setShowBgColor(false);
                      }}
                    />
                  ))}
                  <button 
                    type="button" 
                    className="clear-color-btn"
                    onClick={() => {
                      editor.chain().focus().unsetHighlight().run();
                      setShowBgColor(false);
                    }}
                  >
                    Reset
                  </button>
                </div>
              )}
            </div>

            <button
              type="button"
              title="Clear Formatting"
              onClick={() => editor.chain().focus().clearNodes().unsetAllMarks().run()}
              className="word-toolbar-btn"
            >
              <Icons.Baseline size={16} />
            </button>
          </div>
        </div>

        {/* ROW 2 */}
        <div className="word-toolbar-row">
          {/* Alignments */}
          <div className="word-toolbar-group">
            <button
              type="button"
              title="Align Left"
              onClick={() => editor.chain().focus().setTextAlign('left').run()}
              className={`word-toolbar-btn ${editor.isActive({ textAlign: 'left' }) ? 'active' : ''}`}
            >
              <Icons.AlignLeft size={16} />
            </button>
            <button
              type="button"
              title="Align Center"
              onClick={() => editor.chain().focus().setTextAlign('center').run()}
              className={`word-toolbar-btn ${editor.isActive({ textAlign: 'center' }) ? 'active' : ''}`}
            >
              <Icons.AlignCenter size={16} />
            </button>
            <button
              type="button"
              title="Align Right"
              onClick={() => editor.chain().focus().setTextAlign('right').run()}
              className={`word-toolbar-btn ${editor.isActive({ textAlign: 'right' }) ? 'active' : ''}`}
            >
              <Icons.AlignRight size={16} />
            </button>
            <button
              type="button"
              title="Justify"
              onClick={() => editor.chain().focus().setTextAlign('justify').run()}
              className={`word-toolbar-btn ${editor.isActive({ textAlign: 'justify' }) ? 'active' : ''}`}
            >
              <Icons.AlignJustify size={16} />
            </button>
          </div>

          {/* Lists */}
          <div className="word-toolbar-group">
            <button
              type="button"
              title="Bullet List"
              onClick={() => editor.chain().focus().toggleBulletList().run()}
              className={`word-toolbar-btn ${editor.isActive('bulletList') ? 'active' : ''}`}
            >
              <Icons.List size={16} />
            </button>
            <button
              type="button"
              title="Numbered List"
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              className={`word-toolbar-btn ${editor.isActive('orderedList') ? 'active' : ''}`}
            >
              <Icons.ListOrdered size={16} />
            </button>
            <button
              type="button"
              title="Checklist"
              onClick={() => editor.chain().focus().toggleTaskList().run()}
              className={`word-toolbar-btn ${editor.isActive('taskList') ? 'active' : ''}`}
            >
              <Icons.CheckSquare size={16} />
            </button>
          </div>

          {/* Indents */}
          <div className="word-toolbar-group">
            <button
              type="button"
              title="Decrease Indent"
              onClick={() => editor.chain().focus().outdent().run()}
              className="word-toolbar-btn"
            >
              <Icons.Outdent size={16} />
            </button>
            <button
              type="button"
              title="Increase Indent"
              onClick={() => editor.chain().focus().indent().run()}
              className="word-toolbar-btn"
            >
              <Icons.Indent size={16} />
            </button>
          </div>

          {/* Spacing Selectors */}
          <div className="word-toolbar-group">
            <select
              value={lineSpacing}
              onChange={(e) => {
                setLineSpacing(e.target.value);
                editor.chain().focus().setLineHeight(e.target.value).run();
              }}
              className="word-toolbar-select spacing-select"
              title="Line Spacing"
            >
              <option value="1.0">1.0 Spacing</option>
              <option value="1.15">1.15 Spacing</option>
              <option value="1.5">1.5 Spacing</option>
              <option value="2.0">2.0 Spacing</option>
            </select>

            <select
              value={paragraphSpacing}
              onChange={(e) => {
                setParagraphSpacing(e.target.value);
                editor.chain().focus().setParagraphSpacing(e.target.value).run();
              }}
              className="word-toolbar-select spacing-select"
              title="Paragraph Spacing"
            >
              <option value="0px">Spacing: None</option>
              <option value="8px">Spacing: Small (8px)</option>
              <option value="16px">Spacing: Medium (16px)</option>
              <option value="24px">Spacing: Large (24px)</option>
            </select>
          </div>

          {/* Hyperlinks */}
          <div className="word-toolbar-group">
            <button
              type="button"
              title="Insert Link"
              onClick={addLink}
              className={`word-toolbar-btn ${editor.isActive('link') ? 'active' : ''}`}
            >
              <Icons.Link2 size={16} />
            </button>
            <button
              type="button"
              title="Remove Link"
              onClick={() => editor.chain().focus().unsetLink().run()}
              disabled={!editor.isActive('link')}
              className="word-toolbar-btn"
            >
              <Icons.Link2Off size={16} />
            </button>
          </div>

          {/* Tables & Dividers */}
          <div className="word-toolbar-group">
            <div className="word-popover-anchor">
              <button
                type="button"
                title="Table Controls"
                onClick={() => { setShowTableMenu(!showTableMenu); setShowTextColor(false); setShowBgColor(false); }}
                className={`word-toolbar-btn ${editor.isActive('table') ? 'active' : ''}`}
              >
                <Icons.Table size={16} />
              </button>

              {showTableMenu && (
                <div className="word-table-dropdown-menu">
                  {!editor.isActive('table') ? (
                    <button type="button" className="word-dropdown-item" onClick={insertTable}>
                      <Icons.Plus size={14} /> Insert Table (3x3)
                    </button>
                  ) : (
                    <>
                      <button type="button" className="word-dropdown-item" onClick={() => editor.chain().focus().addRowBefore().run()}>
                        Add Row Above
                      </button>
                      <button type="button" className="word-dropdown-item" onClick={() => editor.chain().focus().addRowAfter().run()}>
                        Add Row Below
                      </button>
                      <button type="button" className="word-dropdown-item" onClick={() => editor.chain().focus().deleteRow().run()}>
                        <Icons.Trash2 size={14} /> Delete Row
                      </button>
                      <hr className="menu-divider" />
                      <button type="button" className="word-dropdown-item" onClick={() => editor.chain().focus().addColumnBefore().run()}>
                        Add Column Left
                      </button>
                      <button type="button" className="word-dropdown-item" onClick={() => editor.chain().focus().addColumnAfter().run()}>
                        Add Column Right
                      </button>
                      <button type="button" className="word-dropdown-item" onClick={() => editor.chain().focus().deleteColumn().run()}>
                        <Icons.Trash2 size={14} /> Delete Column
                      </button>
                      <hr className="menu-divider" />
                      <button type="button" className="word-dropdown-item" onClick={() => editor.chain().focus().mergeCells().run()}>
                        Merge Cells
                      </button>
                      <button type="button" className="word-dropdown-item" onClick={() => editor.chain().focus().splitCell().run()}>
                        Split Cells
                      </button>
                      <button type="button" className="word-dropdown-item" onClick={() => editor.chain().focus().toggleHeaderCell().run()}>
                        Toggle Header Cell
                      </button>
                      <hr className="menu-divider" />
                      
                      {/* Cell Alignment */}
                      <div className="nested-option-group">
                        <span className="nested-label">Vertical Alignment:</span>
                        <div className="nested-btns">
                          <button type="button" className="nested-btn" onClick={() => editor.commands.setCellAlignment('top')}>Top</button>
                          <button type="button" className="nested-btn" onClick={() => editor.commands.setCellAlignment('middle')}>Middle</button>
                          <button type="button" className="nested-btn" onClick={() => editor.commands.setCellAlignment('bottom')}>Bottom</button>
                        </div>
                      </div>

                      {/* Cell Border Styling */}
                      <div className="nested-option-group">
                        <span className="nested-label" onClick={() => setShowBordersMenu(!showBordersMenu)}>
                          Borders &gt;
                        </span>
                        {showBordersMenu && (
                          <div className="double-popover">
                            <button type="button" className="word-dropdown-item" onClick={() => editor.commands.setCellBorder('none')}>None</button>
                            <button type="button" className="word-dropdown-item" onClick={() => editor.commands.setCellBorder('1px solid var(--border-subtle)')}>Thin Solid</button>
                            <button type="button" className="word-dropdown-item" onClick={() => editor.commands.setCellBorder('3px solid var(--border-strong)')}>Thick Solid</button>
                            <button type="button" className="word-dropdown-item" onClick={() => editor.commands.setCellBorder('1px dashed var(--border-strong)')}>Dashed</button>
                            <button type="button" className="word-dropdown-item" onClick={() => editor.commands.setCellBorder('3px double var(--border-strong)')}>Double</button>
                          </div>
                        )}
                      </div>

                      {/* Cell Background Picker */}
                      <div className="nested-option-group">
                        <span className="nested-label" onClick={() => setShowCellColor(!showCellColor)}>
                          Cell BG Color &gt;
                        </span>
                        {showCellColor && (
                          <div className="double-popover color-grid">
                            {colors.map(color => (
                              <div 
                                key={color} 
                                className="color-picker-cell" 
                                style={{ backgroundColor: color }}
                                onClick={() => {
                                  editor.chain().focus().setCellAttribute('backgroundColor', color).run();
                                  setShowCellColor(false);
                                }}
                              />
                            ))}
                            <button 
                              type="button" 
                              className="clear-color-btn"
                              onClick={() => {
                                editor.chain().focus().setCellAttribute('backgroundColor', null).run();
                                setShowCellColor(false);
                              }}
                            >
                              Reset
                            </button>
                          </div>
                        )}
                      </div>

                      <hr className="menu-divider" />
                      <button type="button" className="word-dropdown-item text-danger" onClick={() => editor.chain().focus().deleteTable().run()}>
                        <Icons.Trash2 size={14} /> Delete Entire Table
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>

            <button
              type="button"
              title="Horizontal Divider"
              onClick={() => editor.chain().focus().setHorizontalRule().run()}
              className="word-toolbar-btn"
            >
              <Icons.Minus size={16} />
            </button>
          </div>

          {/* Fullscreen Expand & Find */}
          <div className="word-toolbar-group">
            <button
              type="button"
              title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
              onClick={() => setIsFullscreen(!isFullscreen)}
              className={`word-toolbar-btn ${isFullscreen ? 'active' : ''}`}
            >
              <Icons.Maximize2 size={16} />
            </button>
            <button 
              type="button" 
              title="Find & Replace"
              onClick={() => setShowFindReplace(!showFindReplace)}
              className={`word-toolbar-btn ${showFindReplace ? 'active' : ''}`}
            >
              <Icons.Search size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* FIND & REPLACE EXPANDABLE PANEL */}
      {showFindReplace && (
        <div className="find-replace-panel">
          <div className="find-replace-row">
            <input 
              type="text" 
              placeholder="Find text..." 
              value={findText}
              onChange={(e) => {
                setFindText(e.target.value);
                editor.commands.find(e.target.value);
              }}
              className="find-replace-input"
            />
            <button type="button" className="find-replace-btn" onClick={handleFind}>Find</button>
          </div>
          <div className="find-replace-row">
            <input 
              type="text" 
              placeholder="Replace with..." 
              value={replaceText}
              onChange={(e) => setReplaceText(e.target.value)}
              className="find-replace-input"
            />
            <button type="button" className="find-replace-btn" onClick={handleReplace}>Replace</button>
            <button type="button" className="find-replace-btn" onClick={handleReplaceAll}>Replace All</button>
          </div>
        </div>
      )}

      {/* EDITING CANVAS */}
      <div className="word-editor-canvas">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}
