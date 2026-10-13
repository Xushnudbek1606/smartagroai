import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Check, CheckCheck, ImagePlus, MessageCircle, Search, Send, Wifi, WifiOff, X } from 'lucide-react';
import { api, extractError, wsUrl } from '../services/api';
import { useAuthStore } from '../store/auth';
import { EmptyState, LoadingBlock, showToast } from '../components/ui';
import { formatDateTime, formatRelative } from '../utils/format';
import type { ChatMessage, Conversation, Page } from '../types';

const MAX_CHAT_IMAGE_BYTES = 6 * 1024 * 1024;
const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp'];

export default function ChatPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as never;
  const user = useAuthStore((s) => s.user);
  const { conversationId } = useParams<{ conversationId: string }>();

  const [convs, setConvs] = useState<Conversation[] | null>(null);
  const [search, setSearch] = useState('');
  const [active, setActive] = useState<string | null>(conversationId || null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [text, setText] = useState('');
  const [connected, setConnected] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [pendingImage, setPendingImage] = useState<File | null>(null);
  const [pendingPreview, setPendingPreview] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const reconnectRef = useRef(0);
  const fileRef = useRef<HTMLInputElement>(null);

  function pickImage(f: File | null | undefined) {
    if (!f) return;
    if (!ACCEPTED.includes(f.type)) {
      showToast(t('chat.imageUnsupported'), 'error');
      return;
    }
    if (f.size > MAX_CHAT_IMAGE_BYTES) {
      showToast(t('chat.imageTooLarge', { max: 6 }), 'error');
      return;
    }
    setPendingImage(f);
    setPendingPreview(URL.createObjectURL(f));
  }

  function clearPendingImage() {
    setPendingImage(null);
    if (pendingPreview) URL.revokeObjectURL(pendingPreview);
    setPendingPreview(null);
  }

  async function sendImage() {
    const img = pendingImage;
    if (!img || !active || sending) return;
    setSending(true);
    try {
      const dataUrl: string = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(img);
      });
      wsRef.current?.send(
        JSON.stringify({ event: 'message.send_image', image: dataUrl, text: text.trim() })
      );
      clearPendingImage();
      setText('');
    } catch {
      showToast(t('errors.unexpected'), 'error');
    } finally {
      setSending(false);
    }
  }

  const loadConvs = useCallback(() => {
    api
      .get<Conversation[]>('/conversations')
      .then((r) => setConvs(r.data))
      .catch(() => setConvs([]));
  }, []);

  useEffect(loadConvs, [loadConvs, conversationId]);

  useEffect(() => {
    if (conversationId) setActive(conversationId);
  }, [conversationId]);

  const loadMessages = useCallback((convId: string, p: number) => {
    setHistoryLoading(true);
    api
      .get<Page<ChatMessage>>(`/conversations/${convId}/messages`, { params: { page: p, page_size: 30 } })
      .then((r) => {
        setTotal(r.data.total);
        setPage(p);
        setMessages((prev) => (p === 1 ? r.data.items : [...r.data.items, ...prev]));
      })
      .catch(() => undefined)
      .finally(() => setHistoryLoading(false));
  }, []);

  // WebSocket lifecycle
  useEffect(() => {
    if (!active) return;
    const convId: string = active;
    let closed = false;
    let ws: WebSocket | null = null;

    function connect() {
      if (closed) return;
      try {
        ws = new WebSocket(wsUrl(convId));
        wsRef.current = ws;
      } catch {
        return;
      }
      ws.onopen = () => {
        setConnected(true);
        reconnectRef.current = 0;
        ws?.send(JSON.stringify({ event: 'message.read' }));
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closed) {
          const delay = Math.min(1000 * 2 ** reconnectRef.current, 15000);
          reconnectRef.current += 1;
          window.setTimeout(connect, delay);
        }
      };
      ws.onerror = () => ws?.close();
      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.event === 'message.created' && data.conversation_id === convId) {
            setMessages((prev) => (prev.some((m) => m.id === data.message.id) ? prev : [...prev, data.message]));
            ws?.send(JSON.stringify({ event: 'message.read' }));
            loadConvs();
          } else if (data.event === 'message.read' && data.conversation_id === convId) {
            setMessages((prev) => prev.map((m) => ({ ...m, read_at: m.read_at || data.read_at })));
          }
        } catch {
          /* ignore malformed frames */
        }
      };
    }

    connect();
    loadMessages(convId, 1);

    return () => {
      closed = true;
      wsRef.current = null;
      ws?.close();
    };
  }, [active, loadMessages, loadConvs]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'auto' });
  }, [messages.length]);

  function send() {
    if (pendingImage) {
      void sendImage();
      return;
    }
    const value = text.trim();
    if (!value || !active) return;
    if (value.length > 4000) return;
    wsRef.current?.send(JSON.stringify({ event: 'message.send', text: value }));
    setText('');
  }

  const activeConv = convs?.find((c) => c.id === active) || null;
  const filtered = (convs || []).filter((c) =>
    search ? (c.partner?.full_name || '').toLowerCase().includes(search.toLowerCase()) : true,
  );

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">{t('chat.title')}</h1>
        <p className="text-sm text-textSecondary">{t('chat.subtitle')}</p>
      </div>

      <div className="grid lg:grid-cols-[320px_1fr] gap-4 h-[calc(100vh-240px)] min-h-[420px]">
        {/* conversation list */}
        <div className="card flex flex-col overflow-hidden">
          <div className="p-3 border-b border-borderc relative">
            <Search size={15} className="absolute left-6 top-1/2 -translate-y-1/2 text-textSecondary" />
            <input
              className="input !pl-9 !py-2"
              placeholder={t('chat.searchPlaceholder')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {!convs ? (
              <LoadingBlock />
            ) : filtered.length === 0 ? (
              <EmptyState title={t('chat.empty')} hint={t('chat.emptyHint')} />
            ) : (
              filtered.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setActive(c.id)}
                  className={`w-full text-left rounded-xl p-3 flex items-center gap-3 transition-colors ${
                    active === c.id ? 'bg-primary/10 border border-primary/30' : 'hover:bg-surface2 border border-transparent'
                  }`}
                >
                  <div className="w-10 h-10 rounded-xl bg-accent/15 text-accent flex items-center justify-center font-bold shrink-0">
                    {(c.partner?.full_name || '?').charAt(0)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{c.partner?.full_name}</p>
                    <p className="text-xs text-textSecondary truncate">{c.last_message_preview || '—'}</p>
                  </div>
                  {c.unread_count > 0 && (
                    <span className="min-w-[18px] h-[18px] px-1 rounded-full bg-danger text-[10px] font-bold flex items-center justify-center shrink-0">
                      {c.unread_count}
                    </span>
                  )}
                </button>
              ))
            )}
          </div>
        </div>

        {/* messages */}
        <div className="card flex flex-col overflow-hidden">
          {!activeConv ? (
            <EmptyState
              icon={<MessageCircle size={28} />}
              title={t('chat.selectConversation')}
              hint={t('chat.selectConversationHint')}
            />
          ) : (
            <>
              <div className="px-5 py-3.5 border-b border-borderc flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-lg bg-accent/15 text-accent flex items-center justify-center font-bold shrink-0">
                    {(activeConv.partner?.full_name || '?').charAt(0)}
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold text-sm truncate">{activeConv.partner?.full_name}</p>
                    <p className="text-[11px] text-textSecondary flex items-center gap-1">
                      {connected ? <Wifi size={11} className="text-primary" /> : <WifiOff size={11} className="text-warning" />}
                      {connected ? t('chat.online') : t('chat.onlineHint')}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
                {total > messages.length && (
                  <div className="text-center">
                    <button
                      type="button"
                      className="btn-secondary !py-1 text-xs"
                      onClick={() => active && loadMessages(active, page + 1)}
                      disabled={historyLoading}
                    >
                      {historyLoading ? t('common.loading') : t('chat.loadHistory')}
                    </button>
                  </div>
                )}
                {messages.length === 0 && <EmptyState title={t('chat.noMessages')} />}
                {messages.map((m) => {
                  const mine = m.sender_id === user?.id;
                  return (
                    <div key={m.id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
                      <div
                        className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-sm break-words ${
                          mine ? 'bg-primary/15 border border-primary/25 rounded-br-md' : 'bg-surface2 border border-borderc rounded-bl-md'
                        }`}
                        title={formatDateTime(m.created_at, lang)}
                      >
                        {m.attachment_url ? (
                          m.attachment_url.match(/\.(jpg|jpeg|png|webp)$/i) ? (
                            <a href={m.attachment_url} target="_blank" rel="noreferrer" className="block">
                              <img
                                src={m.attachment_url}
                                alt={m.attachment_name || 'image'}
                                className="max-w-[220px] max-h-48 rounded-xl border border-borderc object-cover"
                              />
                            </a>
                          ) : (
                            <a href={m.attachment_url} target="_blank" rel="noreferrer" className="text-accent underline block">
                              {m.attachment_name || m.attachment_url}
                            </a>
                          )
                        ) : null}
                        {m.message_text && <p className="whitespace-pre-wrap">{m.message_text}</p>}
                        <div className="flex items-center justify-end gap-1 mt-1 text-[10px] text-textSecondary">
                          {formatRelative(m.created_at, lang)}
                          {mine && (m.read_at ? <CheckCheck size={12} className="text-accent" /> : <Check size={12} />)}
                        </div>
                      </div>
                    </div>
                  );
                })}
                <div ref={bottomRef} />
              </div>

              {pendingPreview && (
                <div className="px-3 pt-3">
                  <div className="relative inline-block">
                    <img src={pendingPreview} alt="" className="h-20 rounded-lg border border-borderc object-cover" />
                    <button
                      type="button"
                      onClick={clearPendingImage}
                      className="absolute -top-1.5 -right-1.5 rounded-full bg-danger text-white p-1"
                      aria-label={t('common.cancel')}
                    >
                      <X size={12} />
                    </button>
                  </div>
                </div>
              )}

              <div
                className="p-3 border-t border-borderc flex gap-2"
                onPaste={(e) => {
                  // allow pasting screenshots directly from the clipboard
                  const item = Array.from(e.clipboardData?.items || []).find((it) =>
                    it.type.startsWith('image/'),
                  );
                  if (item) {
                    const f = item.getAsFile();
                    if (f) {
                      e.preventDefault();
                      pickImage(f);
                    }
                  }
                }}
              >
                <input
                  ref={fileRef}
                  type="file"
                  accept={ACCEPTED.join(',')}
                  className="hidden"
                  onChange={(e) => {
                    pickImage(e.target.files?.[0]);
                    e.target.value = '';
                  }}
                />
                <button
                  type="button"
                  className="btn-secondary !px-3.5"
                  onClick={() => fileRef.current?.click()}
                  aria-label={t('chat.attachImage')}
                >
                  <ImagePlus size={17} />
                </button>
                <input
                  className="input !py-2.5"
                  placeholder={pendingImage ? t('chat.captionPlaceholder') : t('chat.typeMessage')}
                  value={text}
                  maxLength={4000}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      send();
                    }
                  }}
                />
                <button
                  type="button"
                  className="btn-primary !px-4"
                  onClick={send}
                  disabled={(!text.trim() && !pendingImage) || sending}
                >
                  <Send size={16} />
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
