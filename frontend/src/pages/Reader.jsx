import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Volume2, VolumeX, Bookmark, BookmarkCheck, Settings, List, X, Loader2, Clock, AlertCircle } from 'lucide-react';
import axios from 'axios';

const THEMES = {
  beige: { canvas:'#FAF7F0', surface:'#F5F0E8', text:'#1C0A0E', accent:'#6B1020', border:'#E8DDD8', label:'Beige' },
  dark:  { canvas:'#141010', surface:'#1E1518', text:'#EDE0D8', accent:'#D4A843', border:'#2E1F22', label:'Dark' },
  sepia: { canvas:'#EFE4C8', surface:'#E5D8B5', text:'#3B2010', accent:'#8B1A2A', border:'#D5C8A5', label:'Sepia' }
};
const FONT_SIZES = [
  {label:'XS',size:'15px'},{label:'S',size:'17px'},
  {label:'M',size:'19px'},{label:'L',size:'21px'}
];
const LOW_BALANCE_THRESHOLD = 300;
const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function wrapWordsInSpans(html) {
  if (typeof document === 'undefined') return { html: html || '', totalWords: 0 };
  const div = document.createElement('div');
  div.innerHTML = html || '';
  let wordIndex = 0;
  function processNode(node) {
    if (node.nodeType === 3) {
      const text = node.textContent;
      if (!text || !text.trim()) return;
      const wrapper = document.createElement('span');
      let lastIndex = 0;
      let html = '';
      const re = /\S+/g;
      let m;
      while ((m = re.exec(text)) !== null) {
        html += text.slice(lastIndex, m.index);
        html += `<span class="tts-word" data-word="${wordIndex}">${m[0]}</span>`;
        wordIndex += 1;
        lastIndex = m.index + m[0].length;
      }
      html += text.slice(lastIndex);
      wrapper.innerHTML = html;
      const parent = node.parentNode;
      while (wrapper.firstChild) parent.insertBefore(wrapper.firstChild, node);
      parent.removeChild(node);
    } else if (node.nodeType === 1) {
      const tag = node.tagName?.toUpperCase();
      if (tag === 'SCRIPT' || tag === 'STYLE') return;
      Array.from(node.childNodes).forEach(processNode);
    }
  }
  Array.from(div.childNodes).forEach(processNode);
  return { html: div.innerHTML, totalWords: wordIndex };
}

function formatWalletTime(seconds) {
  const s = Math.max(0, Math.floor(seconds || 0));
  if (s >= 3600) {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h ${m}m`;
  }
  if (s >= 60) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}m ${sec}s`;
  }
  return `${s}s`;
}

export default function Reader() {
  const { bookId, chapterId } = useParams();
  const navigate = useNavigate();

  const [book, setBook] = useState(null);
  const [chapter, setChapter] = useState(null);
  const [chapters, setChapters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState('beige');
  const [fontSizeIdx, setFontSizeIdx] = useState(1);
  const [showSettings, setShowSettings] = useState(false);
  const [showTOC, setShowTOC] = useState(false);
  const [toolbarVisible, setToolbarVisible] = useState(true);
  const [bookmarked, setBookmarked] = useState(false);
  const [ttsActive, setTtsActive] = useState(false);
  const [ttsPaused, setTtsPaused] = useState(false);
  const [ttsWordIndex, setTtsWordIndex] = useState(-1);
  const [ttsSpeed, setTtsSpeed] = useState(1);
  const [processedHtml, setProcessedHtml] = useState('');
  const [totalWords, setTotalWords] = useState(0);
  const [readProgress, setReadProgress] = useState(0);
  const [contentBlurred, setContentBlurred] = useState(false);
  const [walletSeconds, setWalletSeconds] = useState(0);
  const [showLowBalanceWarning, setShowLowBalanceWarning] = useState(false);
  const [showTopUpModal, setShowTopUpModal] = useState(false);
  const [savedScrollPosition, setSavedScrollPosition] = useState(0);
  const [topUpPacks, setTopUpPacks] = useState([]);
  const [selectedPack, setSelectedPack] = useState(1);
  const [topUpProcessing, setTopUpProcessing] = useState(false);
  const [showTopUpSuccess, setShowTopUpSuccess] = useState(false);
  const [topUpSuccessMinutes, setTopUpSuccessMinutes] = useState(0);
  const [sessionId, setSessionId] = useState(null);

  const contentRef = useRef(null);
  const utteranceRef = useRef(null);
  const synthRef = useRef(window.speechSynthesis);
  const lastScrollY = useRef(0);
  const wordsRef = useRef([]);
  const pulseIntervalRef = useRef(null);
  const scrollContainerRef = useRef(null);

  useEffect(() => {
    const id = crypto.randomUUID();
    setSessionId(id);
    document.addEventListener('contextmenu', (e) => e.preventDefault());
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && ['s','u','a','p','S','U','A','P'].includes(e.key) || e.key === 'F12' || e.key === 'PrintScreen') {
        e.preventDefault();
        e.stopPropagation();
      }
    });
    document.addEventListener('copy', (e) => {
      e.preventDefault();
      e.clipboardData.setData('text/plain', 'Content is protected © Earnalism');
    });
    const interval = setInterval(() => {
      if (window.outerWidth - window.innerWidth > 160 || window.outerHeight - window.innerHeight > 160) {
        setContentBlurred(true);
      } else {
        setContentBlurred(false);
      }
    }, 1000);
    const onVisibilityChange = () => {
      if (document.hidden) {
        setContentBlurred(true);
      } else {
        setContentBlurred(false);
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      document.removeEventListener('contextmenu', (e) => {});
      document.removeEventListener('keydown', (e) => {});
      document.removeEventListener('copy', (e) => {});
      document.removeEventListener('visibilitychange', onVisibilityChange);
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    setLoading(true);
    const token = localStorage.getItem('token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    Promise.all([
      axios.get(`${API}/books/${bookId}`, { headers }),
      axios.get(`${API}/books/${bookId}/chapters/${chapterId}`, { headers }),
      axios.get(`${API}/books/${bookId}/chapters`, { headers }),
      axios.get(`${API}/users/me/wallet`, { headers }),
      axios.get(`${API}/reading/packs`, { headers }),
    ]).then(([bookRes, chapterRes, chaptersRes, walletRes, packsRes]) => {
      setBook(bookRes.data);
      setChapter(chapterRes.data);
      setChapters(chaptersRes.data);
      setWalletSeconds(walletRes.data.wallet_seconds);
      setTopUpPacks(packsRes.data);
      const wrapped = wrapWordsInSpans(chapterRes.data.content);
      setProcessedHtml(wrapped.html);
      setTotalWords(wrapped.totalWords);
      if (sessionId) {
        axios.post(`${API}/reading/session/start`, { session_id: sessionId, book_id: bookId, chapter_id: chapterId }, { headers });
      }
      setLoading(false);
    }).catch((err) => {
      setError(err.message);
      setLoading(false);
    });
    return () => {
      if (sessionId) {
        const token = localStorage.getItem('token');
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        axios.post(`${API}/reading/session/end`, { session_id: sessionId }, { headers });
      }
      if (pulseIntervalRef.current) clearInterval(pulseIntervalRef.current);
      const synth = synthRef.current;
      if (synth) synth.cancel();
      setTtsActive(false);
      setTtsPaused(false);
      setTtsWordIndex(-1);
      wordsRef.current.forEach(w => w.classList.remove('active'));
    };
  }, [bookId, chapterId, sessionId]);

  useEffect(() => {
    if (chapter && processedHtml && sessionId) {
      clearInterval(pulseIntervalRef.current);
      pulseIntervalRef.current = setInterval(sendPulse, 30000);
    }
    return () => clearInterval(pulseIntervalRef.current);
  }, [chapter, processedHtml, sessionId, sendPulse]);

  useEffect(() => {
    wordsRef.current = Array.from(contentRef.current?.querySelectorAll('.tts-word') || []);
  }, [processedHtml]);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const onScroll = () => {
      const max = el.scrollHeight - el.clientHeight;
      const pct = max > 0 ? (el.scrollTop / max) * 100 : 0;
      setReadProgress(Math.min(100, Math.round(pct)));
      if (el.scrollTop > lastScrollY.current + 10) setToolbarVisible(false);
      else if (el.scrollTop < lastScrollY.current - 5) setToolbarVisible(true);
      lastScrollY.current = el.scrollTop;
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, [loading]);

  const sendPulse = useCallback(async () => {
    const token = localStorage.getItem('token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    try {
      const response = await axios.post(`${API}/reading/pulse`, { session_id: sessionId }, { headers });
      const { status, wallet_seconds } = response.data;
      switch (status) {
        case 'ok':
          setWalletSeconds(wallet_seconds);
          break;
        case 'low_balance':
          setWalletSeconds(wallet_seconds);
          setShowLowBalanceWarning(true);
          break;
        case 'wallet_empty':
          setWalletSeconds(0);
          clearInterval(pulseIntervalRef.current);
          setSavedScrollPosition(scrollContainerRef.current?.scrollTop || 0);
          setShowTopUpModal(true);
          break;
        case 'session_invalid':
          clearInterval(pulseIntervalRef.current);
          alert('Your reading session was opened on another device');
          break;
      }
    } catch (err) {
    }
  }, [sessionId]);

  const handleTopUp = async (pack) => {
    setTopUpProcessing(true);
    const token = localStorage.getItem('token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    try {
      const orderRes = await axios.post(`${API}/payments/create-order`, { pack_id: pack._id }, { headers });
      const orderData = orderRes.data;
      const options = {
        key: orderData.key_id,
        amount: orderData.amount,
        currency: orderData.currency,
        order_id: orderData.order_id,
        name: 'Earnalism',
        description: `Top up ${pack.minutes} minutes`,
        handler: async (response) => {
          const verifyRes = await axios.post(`${API}/payments/verify`, {
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          }, { headers });
          const { wallet_seconds } = verifyRes.data;
          setWalletSeconds(wallet_seconds);
          setShowTopUpModal(false);
          setTopUpProcessing(false);
          setShowTopUpSuccess(true);
          setTopUpSuccessMinutes(pack.minutes);
          setShowLowBalanceWarning(false);
          setTimeout(() => {
            setShowTopUpSuccess(false);
            if (scrollContainerRef.current) {
              scrollContainerRef.current.scrollTop = savedScrollPosition;
            }
            pulseIntervalRef.current = setInterval(sendPulse, 30000);
          }, 1500);
        },
        modal: {
          ondismiss: () => setTopUpProcessing(false),
        },
      };
      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch (err) {
      setTopUpProcessing(false);
    }
  };

  const buildUtterance = useCallback(() => {
    const plainText = contentRef.current?.innerText || '';
    const utter = new SpeechSynthesisUtterance(plainText);
    utter.rate = ttsSpeed;
    utter.pitch = 1;
    utter.lang = 'en-US';
    const voices = synthRef.current.getVoices();
    const preferred = voices.find(v => /Samantha|Karen|Moira|Daniel/i.test(v.name)) || voices.find(v => v.lang === 'en-US') || voices[0];
    if (preferred) utter.voice = preferred;
    let wordCount = 0;
    utter.onboundary = (e) => {
      if (e.name === 'word') {
        wordsRef.current.forEach(w => w.classList.remove('active'));
        const current = wordsRef.current[wordCount];
        if (current) {
          current.classList.add('active');
          current.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        setTtsWordIndex(wordCount);
        wordCount++;
      }
    };
    utter.onend = () => {
      setTtsActive(false);
      setTtsPaused(false);
      setTtsWordIndex(-1);
      wordsRef.current.forEach(w => w.classList.remove('active'));
    };
    utter.onerror = () => {
      setTtsActive(false);
      setTtsPaused(false);
      setTtsWordIndex(-1);
      wordsRef.current.forEach(w => w.classList.remove('active'));
    };
    return utter;
  }, [ttsSpeed]);

  const startTTS = useCallback(() => {
    synthRef.current.cancel();
    const utter = buildUtterance();
    if (!utter) return;
    utteranceRef.current = utter;
    synthRef.current.speak(utter);
    setTtsActive(true);
    setTtsPaused(false);
  }, [buildUtterance]);

  const pauseTTS = () => {
    synthRef.current.pause();
    setTtsPaused(true);
  };
  const resumeTTS = () => {
    synthRef.current.resume();
    setTtsPaused(false);
  };
  const stopTTS = useCallback(() => {
    synthRef.current.cancel();
    setTtsActive(false);
    setTtsPaused(false);
    setTtsWordIndex(-1);
    wordsRef.current.forEach(w => w.classList.remove('active'));
  }, []);

  const handleVoiceToggle = () => {
    if (!ttsActive) startTTS();
    else if (ttsPaused) resumeTTS();
    else pauseTTS();
  };

  const currentIdx = useMemo(() => chapters.findIndex(c => c._id === chapterId), [chapters, chapterId]);
  const prevChapter = chapters[currentIdx - 1];
  const nextChapter = chapters[currentIdx + 1];
  const goToChapter = (id) => {
    stopTTS();
    navigate(`/read/${bookId}/${id}`);
  };

  const toggleBookmark = async () => {
    const token = localStorage.getItem('token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    await axios.post(`${API}/bookmarks`, { bookId, chapterId }, { headers });
    setBookmarked(b => !b);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen" style={{ background: THEMES.beige.canvas }}>
        <Loader2 size={32} className="animate-spin" color="#6B1020" />
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 17, color: "#7A5C62" }}>
          Opening chapter…
        </div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 px-6 text-center min-h-screen" style={{ background: THEMES.beige.canvas }}>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 18, color: "#6B1020" }}>
          {error}
        </div>
        <button onClick={() => navigate(-1)} className="px-6 py-2 rounded-full" style={{ background: "#6B1020", color: "#FAF7F0", fontFamily: "Inter", fontSize: 14 }}>
          Back
        </button>
      </div>
    );
  }

  const colors = THEMES[theme];
  return (
    <div ref={scrollContainerRef} className="relative flex flex-col min-h-screen overflow-y-auto reader-scroll" style={{ background: colors.canvas, color: colors.text, transition: 'background 400ms ease, color 300ms ease' }}>
      <div className="fixed top-0 left-0 right-0 z-50 h-2" style={{ background: colors.border }}>
        <div style={{ width: `${readProgress}%`, height: '100%', background: '#6B1020', transition: 'width 300ms' }} />
      </div>
      <div aria-hidden="true" className="watermark">
        <span className="watermark-text">
          {localStorage.getItem('userEmail') || 'earnalism.com'}
          {' · '}{new Date().toLocaleDateString()}
          {' · '}{sessionId?.slice(0,8)}
        </span>
      </div>
      <header className="fixed top-0.5 left-0 right-0 z-40" style={{ background: colors.canvas + 'EE', backdropFilter: 'blur(12px)', borderBottom: `1px solid ${colors.border}`, transform: toolbarVisible ? 'translateY(0)' : 'translateY(-100%)', transition: 'transform 300ms ease' }}>
        <div className="flex items-center justify-between px-4 py-3">
          <button onClick={() => navigate(`/book/${bookId}`)} className="flex items-center gap-2" style={{ color: colors.accent, fontFamily: 'Inter', fontSize: 13 }}>
            <ChevronLeft size={16} />
            <span className="hidden sm:inline">{book?.title}</span>
          </button>
          <div className="flex flex-col items-center text-center min-w-0 px-2">
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, color: colors.text, maxWidth: 180 }} className="truncate">
              {chapter?.title}
            </div>
            <div style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F' }}>
              Ch. {currentIdx + 1} of {chapters.length}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {walletSeconds > 0 && (
              <div className={walletSeconds <= LOW_BALANCE_THRESHOLD ? 'wallet-low flex items-center gap-1' : 'flex items-center gap-1'} style={{ fontFamily: 'Inter', fontSize: 12, color: walletSeconds <= LOW_BALANCE_THRESHOLD ? '#D4A843' : '#A88A8F' }}>
                <Clock size={14} />
                {formatWalletTime(walletSeconds)}
              </div>
            )}
            <button onClick={toggleBookmark}>
              {bookmarked ? <BookmarkCheck size={18} color="#6B1020" /> : <Bookmark size={18} color="#A88A8F" />}
            </button>
            <button onClick={() => setShowTOC(true)}>
              <List size={18} color="#A88A8F" />
            </button>
            <button onClick={() => setShowSettings(s => !s)}>
              <Settings size={18} color="#A88A8F" />
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 px-5 pt-20 pb-36 page-enter">
        <div className="reader-canvas mx-auto">
          <h2 style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, fontWeight: 500, textAlign: 'center', color: colors.accent, letterSpacing: '-0.01em', lineHeight: 1.4, marginBottom: 24 }}>
            {chapter?.title}
          </h2>
          <div className="flex items-center gap-3 mb-10 justify-center">
            <div className="flex-1 h-1" style={{ background: colors.border }} />
            <span style={{ color: colors.accent, fontSize: 20 }}>❧</span>
            <div className="flex-1 h-1" style={{ background: colors.border }} />
          </div>
          <div ref={contentRef} className="drop-cap reader-content" style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: FONT_SIZES[fontSizeIdx].size, lineHeight: 1.75, color: colors.text, filter: contentBlurred ? 'blur(12px)' : 'none', transition: 'filter 300ms ease', userSelect: 'none', WebkitUserSelect: 'none' }} dangerouslySetInnerHTML={{ __html: processedHtml }} />
        </div>
      </main>
      <div className="fixed bottom-0 left-0 right-0 z-40" style={{ background: colors.canvas + 'F5', backdropFilter: 'blur(16px)', borderTop: `1px solid ${colors.border}`, transform: toolbarVisible ? 'translateY(0)' : 'translateY(100%)', transition: 'transform 300ms ease' }}>
        {ttsActive && (
          <div style={{ height: 2, background: colors.border }}>
            <div style={{ width: (totalWords > 0 ? (ttsWordIndex / totalWords) * 100 : 0) + '%', height: '100%', background: '#D4A843', transition: 'width 200ms' }} />
          </div>
        )}
        <div className="flex items-center justify-between px-6 py-3 max-w-xl mx-auto">
          <button disabled={!prevChapter} onClick={() => prevChapter && goToChapter(prevChapter._id)} className="flex items-center gap-1" style={{ color: colors.accent, fontFamily: 'Inter', fontSize: 12, opacity: prevChapter ? 1 : 0.3 }}>
            <ChevronLeft size={16} />
            <span className="hidden sm:inline">Prev</span>
          </button>
          <div className="flex flex-col items-center gap-1">
            <div className="p-3 rounded-full" style={{ background: ttsActive && !ttsPaused ? '#6B1020' : colors.surface, color: ttsActive && !ttsPaused ? '#FAF7F0' : colors.accent, transition: 'all 250ms ease', boxShadow: ttsActive && !ttsPaused ? '0 0 0 4px rgba(107,16,32,0.15)' : 'none', display: 'inline-flex' }}>
              {ttsActive && !ttsPaused ? <Volume2 size={20} /> : <VolumeX size={20} />}
            </div>
            <span style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F' }}>
              {!ttsActive ? 'Listen' : ttsPaused ? 'Resume' : 'Pause'}
            </span>
            <button onClick={handleVoiceToggle} />
          </div>
          {ttsActive && (
            <button onClick={stopTTS} className="px-3 py-1 rounded-full" style={{ background: colors.surface, color: '#A88A8F', fontFamily: 'Inter', fontSize: 11 }}>
              Stop
            </button>
          )}
          <button disabled={!nextChapter} onClick={() => nextChapter && goToChapter(nextChapter._id)} className="flex items-center gap-1" style={{ color: colors.accent, fontFamily: 'Inter', fontSize: 12, opacity: nextChapter ? 1 : 0.3 }}>
            <span className="hidden sm:inline">Next</span>
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
      {showLowBalanceWarning && walletSeconds > 0 && (
        <div className="fixed bottom-64 left-0 right-0 z-45 animate-slide-up" style={{ background: '#E8C97A', borderTop: '1px solid #D4A843' }}>
          <div className="flex items-center justify-between px-4 py-3 max-w-xl mx-auto">
            <div className="flex items-center gap-2">
              <Clock size={16} color="#6B1020" />
              <span style={{ fontFamily: 'Inter', fontSize: 13, color: '#6B1020' }}>
                {formatWalletTime(walletSeconds)} of reading time remaining
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => { setSavedScrollPosition(scrollContainerRef.current?.scrollTop || 0); setShowTopUpModal(true); }} className="px-3 py-1 rounded-full" style={{ background: '#6B1020', color: '#FAF7F0', fontFamily: 'Inter', fontSize: 12 }}>
                Top Up
              </button>
              <button onClick={() => setShowLowBalanceWarning(false)} style={{ color: '#6B1020', fontFamily: 'Inter', fontSize: 16 }}>
                ✕
              </button>
            </div>
          </div>
        </div>
      )}
      {showTopUpModal && (
        <div className="fixed inset-0 z-60 flex items-end justify-center">
          <div className="absolute inset-0 bg-black/50" style={{ backdropFilter: 'blur(4px)' }} />
          <div className="relative rounded-t-2xl p-6 w-full max-w-lg animate-slide-up" style={{ background: '#FAF7F0', boxShadow: '0 -8px 40px rgba(107,16,32,0.15)' }}>
            <div className="text-center">
              <div style={{ fontSize: 32 }}>⏸</div>
              <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 26, color: '#6B1020', marginTop: 3 }}>
                Reading Paused
              </div>
              <p style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 16, color: '#7A5C62', marginTop: 2 }}>
                You've used all your reading time.
              </p>
              <p style={{ fontFamily: 'Inter', fontSize: 12, color: '#D4A843', marginTop: 1, marginBottom: 5 }}>
                Your place is saved — top up to continue from where you left off.
              </p>
            </div>
            <div className="space-y-2">
              {topUpPacks.map((pack, index) => {
                const selected = index === selectedPack;
                return (
                  <div key={pack._id} onClick={() => setSelectedPack(index)} className="rounded-xl p-4 cursor-pointer transition-all" style={{ borderWidth: 2, borderStyle: 'solid', borderColor: selected ? '#6B1020' : '#E8DDD8', background: selected ? 'rgba(107,16,32,0.06)' : 'white' }}>
                    <div className="flex justify-between items-center">
                      <div>
                        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 17, color: '#1C0A0E' }}>
                          {pack.minutes} min
                        </div>
                        {pack.label && (
                          <div style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F' }}>
                            {pack.label}
                          </div>
                        )}
                      </div>
                      <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 20, color: '#6B1020' }}>
                        ₹{pack.price}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <button onClick={() => handleTopUp(topUpPacks[selectedPack])} disabled={topUpProcessing} className="w-full mt-4 rounded-xl py-3 flex items-center justify-center gap-2" style={{ background: '#6B1020', color: '#FAF7F0', fontFamily: 'Inter', fontSize: 15, fontWeight: 500, opacity: topUpProcessing ? 0.7 : 1 }}>
              {topUpProcessing && <Loader2 className="animate-spin" size={16} />}
              Complete Payment →
            </button>
            <button onClick={() => setShowTopUpModal(false)} className="w-full mt-3 text-center" style={{ fontFamily: 'Inter', fontSize: 12, color: '#A88A8F' }}>
              I'll top up later
            </button>
          </div>
        </div>
      )}
      {showTopUpSuccess && (
        <div className="fixed inset-0 z-70 flex items-center justify-center animate-fade-in" style={{ background: 'rgba(250,247,240,0.96)', backdropFilter: 'blur(8px)' }}>
          <div className="flex flex-col items-center gap-4">
            <div className="rounded-full w-16 h-16 bg-[#6B1020] flex items-center justify-center">
              <span style={{ color: 'white', fontSize: 24 }}>✓</span>
            </div>
            <div style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 28, color: '#6B1020' }}>
              {topUpSuccessMinutes} minutes added
            </div>
            <div style={{ fontFamily: 'Inter', fontSize: 13, color: '#A88A8F' }}>
              Resuming your chapter…
            </div>
          </div>
        </div>
      )}
      {showSettings && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 rounded-2xl p-5 w-80 shadow-book animate-slide-up" style={{ background: colors.surface, border: `1px solid ${colors.border}` }}>
          <div className="flex justify-between items-center mb-4">
            <span style={{ fontFamily: 'Inter', fontSize: 13, fontWeight: 500, color: colors.text }}>
              Reading Settings
            </span>
            <button onClick={() => setShowSettings(false)}>
              <X size={16} color="#A88A8F" />
            </button>
          </div>
          <div className="mb-4">
            <div style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F', marginBottom: 8 }}>
              Font Size
            </div>
            <div className="flex gap-2">
              {FONT_SIZES.map((f, i) => {
                const active = fontSizeIdx === i;
                return (
                  <button onClick={() => setFontSizeIdx(i)} className="flex-1 py-2 rounded-lg" style={{ background: active ? '#6B1020' : colors.canvas, color: active ? '#FAF7F0' : colors.text, border: active ? 'none' : `1px solid ${colors.border}`, fontFamily: 'Inter', fontSize: 12, fontWeight: 500 }}>
                    {f.label}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="mb-4">
            <div style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F', marginBottom: 8 }}>
              Theme
            </div>
            <div className="flex gap-2">
              {Object.entries(THEMES).map(([key, t]) => {
                const active = theme === key;
                return (
                  <button onClick={() => setTheme(key)} className="flex-1 py-2 rounded-lg capitalize" style={{ background: t.canvas, color: t.text, border: active ? `2px solid #6B1020` : `1px solid ${colors.border}`, fontFamily: 'Inter', fontSize: 11 }}>
                    {t.label}
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <div style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F', marginBottom: 8 }}>
              Speed: {ttsSpeed}×
            </div>
            <input type="range" min="0.7" max="1.8" step="0.1" value={ttsSpeed} onChange={(e) => { setTtsSpeed(parseFloat(e.target.value)); if (ttsActive) { stopTTS(); setTimeout(startTTS, 150); } }} style={{ accentColor: '#6B1020', width: '100%' }} />
          </div>
        </div>
      )}
      {showTOC && (
        <div className="fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/40" style={{ backdropFilter: 'blur(4px)' }} onClick={() => setShowTOC(false)} />
          <div className="relative right-0 ml-auto w-72 h-full overflow-y-auto py-6 px-5 animate-slide-up" style={{ background: colors.surface }}>
            <div className="flex justify-between items-center mb-6">
              <span style={{ fontFamily: "'Cormorant Garamond', serif", fontSize: 20, color: colors.text }}>
                Contents
              </span>
              <button onClick={() => setShowTOC(false)}>
                <X size={18} color="#A88A8F" />
              </button>
            </div>
            <div className="space-y-1">
              {chapters.map((ch, index) => {
                const current = index === currentIdx;
                return (
                  <button onClick={() => { setShowTOC(false); goToChapter(ch._id); }} className="w-full text-left px-3 py-2.5 rounded-lg transition-all" style={{ background: current ? 'rgba(107,16,32,0.08)' : 'transparent', borderLeft: current ? '2px solid #6B1020' : '2px solid transparent', color: current ? '#6B1020' : colors.text, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 15 }}>
                    <span style={{ fontFamily: 'Inter', fontSize: 11, color: '#A88A8F', marginRight: 6 }}>
                      {index + 1}.
                    </span>
                    {ch.title}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}