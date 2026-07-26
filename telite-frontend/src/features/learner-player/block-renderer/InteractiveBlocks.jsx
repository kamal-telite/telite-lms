import React from 'react';
import { api, fetchQuizStats } from "../../../services/client";
import { postLearnerEvents } from './events';

export function PollBlock({ blockId, courseId: _courseId, moduleId: _moduleId, settings }) {
  const [loading, setLoading] = React.useState(true);
  const [voted, setVoted] = React.useState(false);
  const [results, setResults] = React.useState({});
  const [totalVotes, setTotalVotes] = React.useState(0);
  const [selectedOptions, setSelectedOptions] = React.useState([]);
  const [isVoting, setIsVoting] = React.useState(false);

  const fetchResults = async () => {
    try {
      const { data } = await api.get(`/api/v1/learner/blocks/${blockId}/poll-results`);
      setResults(data.results || {});
      setTotalVotes(data.total_votes || 0);
      if (data.my_vote && data.my_vote.length > 0) {
        setVoted(true);
        setSelectedOptions(data.my_vote);
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  // fetchResults closes over the current block state; polling starts only when the block id changes.
  React.useEffect(() => {
    if (blockId) fetchResults();
    else setLoading(false);
  }, [blockId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleVote = async () => {
    if (selectedOptions.length === 0) return;
    setIsVoting(true);
    try {
      const optionId = selectedOptions[0];
      await api.post(`/api/v1/learner/blocks/${blockId}/poll/vote`, { option_id: optionId });
      await fetchResults();
      setVoted(true);
    } catch (err) {
      if (err?.response?.status === 409) {
        // Already voted — refresh results to show current state
        await fetchResults();
        setVoted(true);
      } else {
        console.error(err);
      }
    }
    setIsVoting(false);
  };

  const toggleOption = (optId) => {
    if (settings?.allow_multiple) {
      setSelectedOptions(prev => prev.includes(optId) ? prev.filter(id => id !== optId) : [...prev, optId]);
    } else {
      setSelectedOptions([optId]);
    }
  };

  if (loading) return <div style={{ padding: "18px" }}>Loading poll...</div>;

  const showResults = settings?.show_results === "always" || (voted && settings?.show_results === "after_vote");
  const options = settings?.options || [];

  return (
    <div style={{ padding: "18px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", margin: "1em 0" }}>
      <div style={{ fontWeight: 600, fontSize: "16px", marginBottom: "16px" }}>
        {settings?.question || "Poll"}
      </div>

      {(!voted || settings?.allow_vote_change) ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: showResults ? "24px" : "0" }}>
          {options.map((opt) => {
            const isSelected = selectedOptions.includes(opt.id);
            return (
              <label key={opt.id} style={{ 
                display: "flex", alignItems: "center", gap: "12px", cursor: "pointer",
                padding: "12px 16px", borderRadius: "8px", border: "1px solid",
                background: isSelected ? "var(--primary-bg)" : "var(--surface-sunken)",
                borderColor: isSelected ? "var(--border-strong)" : "var(--border-subtle)",
                transition: "all 0.2s"
              }}>
                <input
                  type={settings?.allow_multiple ? "checkbox" : "radio"}
                  name={`poll_${blockId}`}
                  checked={isSelected}
                  onChange={() => toggleOption(opt.id)}
                  style={{ margin: 0, cursor: "pointer" }}
                />
                <span style={{ fontSize: "14px", color: "var(--text-primary)", lineHeight: "1.4" }}>{opt.text}</span>
              </label>
            );
          })}
          <div style={{ marginTop: "8px" }}>
            <button
              onClick={handleVote}
              disabled={selectedOptions.length === 0 || isVoting}
              style={{ padding: "8px 16px", background: "var(--primary)", color: "#fff", border: "none", borderRadius: "4px", cursor: selectedOptions.length === 0 ? "not-allowed" : "pointer" }}
            >
              {isVoting ? "Voting..." : (voted ? "Change Vote" : "Submit Vote")}
            </button>
            {settings?.allow_vote_change && voted && !isVoting && <span style={{ marginLeft: "12px", fontSize: "13px", color: "var(--success)" }}>Your vote is recorded.</span>}
          </div>
        </div>
      ) : (
        !showResults && <div style={{ color: "var(--success)", fontWeight: 500 }}>Thank you for voting!</div>
      )}

      {showResults && (
        <div style={{ borderTop: (!voted || settings?.allow_vote_change) ? "1px solid var(--border)" : "none", paddingTop: (!voted || settings?.allow_vote_change) ? "16px" : "0" }}>
          <div style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "12px" }}>Results ({totalVotes} votes)</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {options.map((opt) => {
              const count = results[opt.id] || 0;
              const percent = totalVotes > 0 ? Math.round((count / totalVotes) * 100) : 0;
              return (
                <div key={opt.id}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "14px", marginBottom: "4px" }}>
                    <span>{opt.text}</span>
                    <span>{percent}%</span>
                  </div>
                  <div style={{ height: "8px", background: "var(--border-subtle)", borderRadius: "4px", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: `${percent}%`, background: "var(--primary)", transition: "width 0.3s ease" }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export function FlashcardBlock({ blockId, courseId, moduleId, settings }) {
  const [cards, setCards] = React.useState([]);
  const [currentIndex, setCurrentIndex] = React.useState(0);
  const [isFlipped, setIsFlipped] = React.useState(false);
  const [viewedIndices, setViewedIndices] = React.useState(new Set([0]));
  const [completed, setCompleted] = React.useState(false);

  React.useEffect(() => {
    let deck = [...(settings?.cards || [])];
    if (settings?.randomize_order) {
      for (let i = deck.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [deck[i], deck[j]] = [deck[j], deck[i]];
      }
    }
    setCards(deck);
  }, [settings?.cards, settings?.randomize_order]);

  const emitEvent = (eventType, payload = {}) => {
    postLearnerEvents([{
      event_type: eventType,
      course_id: courseId,
      module_id: moduleId,
      block_id: blockId,
      payload_json: payload
    }]).catch(err => console.error(err));
  };

  const handleFlip = () => {
    if (!isFlipped) {
      emitEvent("FLASHCARD_FLIPPED", { card_id: cards[currentIndex]?.id });
    }
    setIsFlipped(!isFlipped);
  };

  const handleNext = () => {
    if (currentIndex < cards.length - 1) {
      const nextIdx = currentIndex + 1;
      setCurrentIndex(nextIdx);
      setIsFlipped(false);
      
      const newViewed = new Set(viewedIndices);
      newViewed.add(nextIdx);
      setViewedIndices(newViewed);

      if (!completed && newViewed.size === cards.length) {
        setCompleted(true);
        emitEvent("BLOCK_COMPLETED");
      }
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      setIsFlipped(false);
    }
  };

  if (cards.length === 0) return null;

  const currentCard = cards[currentIndex];

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", margin: "2em 0" }}>
      <div 
        onClick={handleFlip}
        style={{
          width: "100%",
          maxWidth: "500px",
          height: "300px",
          perspective: "1000px",
          cursor: "pointer",
          marginBottom: "24px"
        }}
      >
        <div style={{
          position: "relative",
          width: "100%",
          height: "100%",
          transition: "transform 0.6s",
          transformStyle: "preserve-3d",
          transform: isFlipped ? "rotateY(180deg)" : "rotateY(0deg)"
        }}>
          {/* Front */}
          <div style={{
            position: "absolute",
            width: "100%",
            height: "100%",
            backfaceVisibility: "hidden",
            background: "var(--surface-raised)",
            border: "2px solid var(--border-subtle)",
            borderRadius: "12px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            boxShadow: "var(--shadow-card)",
            fontSize: "20px",
            textAlign: "center",
            color: "var(--text-primary)",
            whiteSpace: "pre-wrap"
          }}>
            {currentCard?.front_text || "Empty Card"}
          </div>
          {/* Back */}
          <div style={{
            position: "absolute",
            width: "100%",
            height: "100%",
            backfaceVisibility: "hidden",
            background: "var(--surface-sunken)",
            border: "2px solid var(--border-strong)",
            borderRadius: "12px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "24px",
            boxShadow: "var(--shadow-card)",
            fontSize: "20px",
            textAlign: "center",
            color: "var(--text-primary)",
            transform: "rotateY(180deg)",
            whiteSpace: "pre-wrap"
          }}>
            {currentCard?.back_text || "Empty Card"}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
        <button 
          onClick={handlePrev} 
          disabled={currentIndex === 0}
          style={{ padding: "12px 24px", fontWeight: 500, background: currentIndex === 0 ? "var(--surface-sunken)" : "var(--primary)", color: currentIndex === 0 ? "var(--text-muted)" : "#fff", border: "none", borderRadius: "24px", cursor: currentIndex === 0 ? "not-allowed" : "pointer", transition: "all 0.2s" }}
        >
          Previous
        </button>
        <span style={{ fontSize: "14px", color: "var(--text-muted)", fontWeight: 500, minWidth: "40px", textAlign: "center" }}>
          {currentIndex + 1} / {cards.length}
        </span>
        <button 
          onClick={handleNext} 
          disabled={currentIndex === cards.length - 1}
          style={{ padding: "12px 24px", fontWeight: 500, background: currentIndex === cards.length - 1 ? "var(--surface-sunken)" : "var(--primary)", color: currentIndex === cards.length - 1 ? "var(--text-muted)" : "#fff", border: "none", borderRadius: "24px", cursor: currentIndex === cards.length - 1 ? "not-allowed" : "pointer", transition: "all 0.2s" }}
        >
          Next
        </button>
      </div>
      
      {completed && <div style={{ marginTop: "16px", color: "var(--success)", fontSize: "14px", fontWeight: 500 }}>All cards viewed!</div>}
    </div>
  );
}

export function ResourceCollectionBlock({ blockId, courseId, moduleId, settings }) {
  const [downloadedIndices, setDownloadedIndices] = React.useState(new Set());
  const [completed, setCompleted] = React.useState(false);
  const resources = settings?.resources || [];
  const completionMode = settings?.completion_mode || "view";

  const emitEvent = React.useCallback((eventType, payload = {}) => {
    postLearnerEvents([{
      event_type: eventType,
      course_id: courseId,
      module_id: moduleId,
      block_id: blockId,
      payload_json: payload
    }]).catch(err => console.error(err));
  }, [courseId, moduleId, blockId]);

  React.useEffect(() => {
    if (completionMode === "view" && !completed) {
      setCompleted(true);
      emitEvent("BLOCK_COMPLETED");
    }
  }, [completionMode, completed, emitEvent]);

  const handleDownload = async (assetId, index) => {
    try {
      const { data } = await api.get(`/api/v1/learner/blocks/${blockId}/resources/${assetId}/download`);
        // Since backend triggers RESOURCE_DOWNLOADED automatically, we don't need to emit it here.
        // We trigger the browser download:
        window.open(data.url, '_blank');
        
        const newDownloaded = new Set(downloadedIndices);
        newDownloaded.add(index);
        setDownloadedIndices(newDownloaded);

        if (!completed) {
          if (completionMode === "download_any" && newDownloaded.size >= 1) {
            setCompleted(true);
            emitEvent("BLOCK_COMPLETED");
          } else if (completionMode === "download_all" && newDownloaded.size >= resources.length) {
            setCompleted(true);
            emitEvent("BLOCK_COMPLETED");
          }
        }
    } catch (err) {
      console.error(err);
      alert("Error downloading resource.");
    }
  };

  if (resources.length === 0) {
    return <div style={{ padding: "16px", color: "var(--text-muted)", fontStyle: "italic" }}>No resources attached.</div>;
  }

  return (
    <div style={{ padding: "18px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", margin: "1em 0" }}>
      <div style={{ fontWeight: 600, fontSize: "16px", marginBottom: "16px", color: "var(--text-primary)" }}>
        Resource Collection
      </div>
      
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {resources.map((res, idx) => (
          <div key={res.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", border: "1px solid var(--border-subtle)", borderRadius: "6px", background: downloadedIndices.has(idx) ? "var(--success-bg)" : "var(--surface-sunken)" }}>
            <div>
              <div style={{ fontWeight: 500, fontSize: "14px", color: "var(--text-primary)" }}>{res.title}</div>
              <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>{res.description}</div>
            </div>
            <button
              onClick={() => handleDownload(res.asset_id, idx)}
              style={{ padding: "8px 16px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", borderRadius: "4px", cursor: "pointer", fontWeight: 500, fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              {downloadedIndices.has(idx) ? "Downloaded" : "Download"}
            </button>
          </div>
        ))}
      </div>

      {completed && completionMode !== "view" && completionMode !== "manual_complete" && (
        <div style={{ marginTop: "16px", color: "var(--success)", fontSize: "14px", fontWeight: 500 }}>
          {completionMode === "download_any" ? "Resource downloaded!" : "All resources downloaded!"}
        </div>
      )}
    </div>
  );
}

export function QuizBlock({ blockId, courseId: _courseId, moduleId: _moduleId, settings }) {
  const [answers, setAnswers] = React.useState({});
  const [submitted, setSubmitted] = React.useState(false);
  const [result, setResult] = React.useState(null);
  const [stats, setStats] = React.useState(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [loadingStats, setLoadingStats] = React.useState(false);

  const questions = settings?.questions || [];
  const passingScore = settings?.passing_score || 80;
  const maxAttempts = Number(settings?.max_attempts || 0);
  const effectiveMaxAttempts = stats?.maximum_attempts ?? (maxAttempts > 0 ? maxAttempts : null);
  const attemptsUsed = stats?.attempts_used ?? 0;
  const attemptsRemaining = stats?.attempts_remaining ?? (effectiveMaxAttempts ? Math.max(effectiveMaxAttempts - attemptsUsed, 0) : null);
  const questionResults = React.useMemo(() => {
    const byQuestion = {};
    (result?.question_results || []).forEach((item) => {
      byQuestion[item.question_id] = item;
    });
    return byQuestion;
  }, [result]);

  React.useEffect(() => {
    let cancelled = false;
    setLoadingStats(true);
    fetchQuizStats(blockId)
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch(() => {
        if (!cancelled) setStats(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingStats(false);
      });
    return () => { cancelled = true; };
  }, [blockId]);

  const handleOptionSelect = (qId, optId) => {
    if (submitted) return;
    setAnswers(prev => ({ ...prev, [qId]: optId }));
  };

  const handleSubmit = async () => {
    // Basic validation: ensure all questions are answered
    if (Object.keys(answers).length < questions.length) {
      alert("Please answer all questions before submitting.");
      return;
    }

    setIsSubmitting(true);
    try {
      const { data } = await api.post(`/api/v1/learner/blocks/${blockId}/quiz/submit`, { answers });
      setResult(data);
      setStats({
        ...(stats || {}),
        maximum_attempts: data.max_attempts,
        max_attempts: data.max_attempts,
        attempts_used: data.attempts_used,
        attempts_remaining: data.attempts_remaining,
        highest_score: data.highest_score,
        latest_score: data.latest_score,
        best_attempt: data.best_attempt,
        attempt_history: data.attempt_history || [],
      });
      setSubmitted(true);
    } catch (err) {
      const detail = err?.response?.data?.detail || "Error submitting quiz.";
      alert(detail);
    }
    setIsSubmitting(false);
  };

  const allAnswered = Object.keys(answers).length === questions.length;
  const attemptsExhausted = attemptsRemaining === 0 && effectiveMaxAttempts !== null && !result?.passed;
  const history = stats?.attempt_history || result?.attempt_history || [];

  return (
    <div style={{ padding: "24px", borderRadius: "8px", background: "var(--surface-raised)", border: "1px solid var(--border-subtle)", margin: "1em 0" }}>
      <div style={{ fontWeight: 600, fontSize: "20px", marginBottom: "8px", color: "var(--text-primary)", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "12px" }}>
        Quiz
      </div>
      <div style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "24px" }}>
        Passing Score: {passingScore}%{maxAttempts > 0 ? ` · Max Attempts: ${maxAttempts}` : " · Unlimited Attempts"}
        {loadingStats ? " · Loading attempts..." : effectiveMaxAttempts ? ` · Attempts Left: ${attemptsRemaining} / ${effectiveMaxAttempts}` : " · Attempts Left: Unlimited"}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {questions.map((q, idx) => {
          const questionResult = questionResults[q.id];
          const isCorrect = Boolean(questionResult?.is_correct);
          const showFeedback = submitted && result;
          
          return (
            <div key={q.id} style={{ 
              padding: "16px", 
              borderRadius: "6px", 
              border: showFeedback ? (isCorrect ? "1px solid var(--success)" : "1px solid var(--error)") : "1px solid var(--border-subtle)",
              background: showFeedback ? (isCorrect ? "var(--success-bg)" : "var(--error-bg)") : "var(--surface-sunken)"
            }}>
              <div style={{ fontWeight: 500, fontSize: "15px", marginBottom: "12px", color: "var(--text-primary)" }}>
                {idx + 1}. {q.text}
                <span style={{ fontSize: "13px", color: "var(--text-muted)", marginLeft: "8px", fontWeight: "normal" }}>({q.points || 10} pts)</span>
              </div>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {(q.options || []).map(opt => {
                  const isSelected = answers[q.id] === opt.id;
                  
                  let optStyle = {
                    display: "flex", alignItems: "center", gap: "8px", padding: "10px", 
                    borderRadius: "4px", border: "1px solid var(--border-subtle)", cursor: submitted ? "default" : "pointer",
                    background: isSelected ? "var(--primary-bg)" : "var(--surface-raised)",
                    borderColor: isSelected ? "var(--border-strong)" : "var(--border-subtle)",
                    transition: "all 0.2s"
                  };

                  if (showFeedback) {
                    if (isSelected && isCorrect) {
                      optStyle.background = "var(--success-bg)";
                      optStyle.borderColor = "var(--success)";
                    } else if (isSelected && !isCorrect) {
                      optStyle.background = "var(--error-bg)";
                      optStyle.borderColor = "var(--error)";
                    }
                  }

                  return (
                    <div 
                      key={opt.id} 
                      style={optStyle}
                      onClick={() => handleOptionSelect(q.id, opt.id)}
                    >
                      <input 
                        type="radio" 
                        name={`q_${q.id}`} 
                        checked={isSelected}
                        onChange={() => {}} // Handle via parent div onClick
                        disabled={submitted}
                        style={{ margin: 0, cursor: submitted ? "default" : "pointer" }}
                      />
                      <span style={{ color: "var(--text-primary)", fontSize: "14px" }}>{opt.text}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        {!submitted ? (
          attemptsExhausted ? (
            <div style={{ padding: "10px 14px", color: "var(--error)", background: "var(--error-bg)", border: "1px solid var(--error)", borderRadius: "6px", fontWeight: 500 }}>
              You have reached the maximum number of allowed attempts.
            </div>
          ) : (
          <button
            onClick={handleSubmit}
            disabled={!allAnswered || isSubmitting}
            style={{ 
              padding: "10px 24px", 
              background: (!allAnswered || isSubmitting) ? "var(--surface-sunken)" : "var(--primary)", 
              color: (!allAnswered || isSubmitting) ? "var(--text-muted)" : "#fff", 
              border: "none", 
              borderRadius: "4px", 
              cursor: (!allAnswered || isSubmitting) ? "not-allowed" : "pointer",
              fontWeight: 500
            }}
          >
            {isSubmitting ? "Submitting..." : "Submit Quiz"}
          </button>
          )
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "16px", width: "100%" }}>
            <div style={{ flex: "1 1 auto", minWidth: "200px" }}>
              <div style={{ fontSize: "18px", fontWeight: 600, color: result?.passed ? "var(--success)" : "var(--error)" }}>
                Score: {result?.score}% {result?.passed ? "(Passed)" : "(Failed)"}
              </div>
              <div style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
                {result?.passed ? "Great job! Your score meets the passing requirement." : "You did not meet the passing score requirement."}
                {effectiveMaxAttempts ? ` Attempts remaining: ${attemptsRemaining}.` : ""}
              </div>
            </div>
            {!result?.passed && !attemptsExhausted && (
              <button
                onClick={() => { setAnswers({}); setSubmitted(false); setResult(null); }}
                style={{ padding: "10px 20px", background: "var(--surface-sunken)", border: "1px solid var(--border-subtle)", borderRadius: "6px", cursor: "pointer", fontWeight: 500, flexShrink: 0 }}
              >
                Retake Quiz
              </button>
            )}
            {attemptsExhausted && (
              <div style={{ padding: "10px 14px", color: "var(--error)", background: "var(--error-bg)", border: "1px solid var(--error)", borderRadius: "6px", fontWeight: 500 }}>
                Maximum attempts reached
              </div>
            )}
          </div>
        )}
      </div>
      {history.length > 0 && (
        <div style={{ marginTop: "18px", paddingTop: "16px", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={{ fontWeight: 600, marginBottom: "10px" }}>Attempt History</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Attempt</th>
                  <th>Date</th>
                  <th style={{ textAlign: "right" }}>Score</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {history.map((attempt) => (
                  <tr key={attempt.attempt_id || attempt.attempt_number}>
                    <td className="mono">{attempt.attempt_number}</td>
                    <td>{attempt.attempt_date ? new Date(attempt.attempt_date).toLocaleString() : "-"}</td>
                    <td className="mono" style={{ textAlign: "right" }}>{Math.round(attempt.score)}%</td>
                    <td>{attempt.status === "passed" ? "Passed" : "Failed"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
