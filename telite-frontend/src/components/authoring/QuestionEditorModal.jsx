import React, { useState, useEffect } from "react";
import { Modal, Button, useToast, IconButton, Badge } from "../common/ui";
import { createQuestion, updateDraftQuestion, publishQuestion, createNewDraft } from "../../services/client";
import { fetchQuestionCategories, fetchQuestionTags } from "../../api/questionBank";
import { getQuestionBankErrorMessage } from "../../api/questionBankErrors";
import { flattenCategoryOptions, toggleTagId } from "../../utils/questionTaxonomy";

export default function QuestionEditorModal({ open, onClose, bankId, existingQuestion, onSaved }) {
  const { showToast } = useToast();
  const [saving, setSaving] = useState(false);
  const [taxonomyLoading, setTaxonomyLoading] = useState(false);
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [tags, setTags] = useState([]);
  
  const [formData, setFormData] = useState({
    question_type: "multiple_choice",
    question_text: "",
    points: 1,
    category_id: null,
    tag_ids: [],
    options_json: [{ text: "Option A" }, { text: "Option B" }],
    correct_answer_json: ["Option A"]
  });

  useEffect(() => {
    if (!open) return;

    let cancelled = false;
    setTaxonomyLoading(true);
    Promise.all([
      fetchQuestionCategories({ tree: true }),
      fetchQuestionTags(),
    ])
      .then(([categoryData, tagData]) => {
        if (cancelled) return;
        setCategoryOptions(flattenCategoryOptions(categoryData.items || []));
        setTags(tagData.items || []);
      })
      .catch((error) => {
        if (!cancelled) {
          showToast(getQuestionBankErrorMessage(error, "Failed to load taxonomy"), "error");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setTaxonomyLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open, showToast]);

  useEffect(() => {
    if (existingQuestion) {
      setFormData({
        question_type: existingQuestion.question_type || "multiple_choice",
        question_text: existingQuestion.question_text || "",
        points: existingQuestion.points || 1,
        category_id: existingQuestion.category_id || null,
        tag_ids: existingQuestion.tag_ids || [],
        options_json: existingQuestion.options_json || [{ text: "Option A" }, { text: "Option B" }],
        correct_answer_json: existingQuestion.correct_answer_json || ["Option A"]
      });
    } else {
      setFormData({
        question_type: "multiple_choice",
        question_text: "",
        points: 1,
        category_id: null,
        tag_ids: [],
        options_json: [{ text: "Option A" }, { text: "Option B" }],
        correct_answer_json: ["Option A"]
      });
    }
  }, [existingQuestion, open]);

  const handleSave = async () => {
    if (!formData.question_text.trim()) {
      showToast("Question text is required", "warning");
      return;
    }
    
    setSaving(true);
    try {
      if (existingQuestion) {
        if (existingQuestion.current_published_version_id && !existingQuestion.current_draft_version_id) {
          // It's a published question with no draft. We must create a new draft first.
          const draftRes = await createNewDraft(bankId, existingQuestion.id);
          // Now update that draft
          await updateDraftQuestion(bankId, existingQuestion.id, formData);
          showToast("New draft created and updated successfully", "success");
        } else {
          // There's an active draft, just update it
          await updateDraftQuestion(bankId, existingQuestion.id, formData);
          showToast("Draft updated successfully", "success");
        }
      } else {
        await createQuestion(bankId, formData);
        showToast("Question created successfully", "success");
      }
      onSaved();
      onClose();
    } catch (err) {
      showToast(getQuestionBankErrorMessage(err, "Failed to save question"), "error");
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!existingQuestion) return;
    setSaving(true);
    try {
      await publishQuestion(bankId, existingQuestion.id);
      showToast("Question published successfully", "success");
      onSaved();
      onClose();
    } catch (err) {
      showToast(err.message || "Failed to publish question", "error");
    } finally {
      setSaving(false);
    }
  };

  const updateOption = (index, value) => {
    const newOptions = [...formData.options_json];
    const oldText = newOptions[index].text;
    newOptions[index].text = value;
    
    // Update correct answer if it was the old text
    let newCorrect = [...formData.correct_answer_json];
    if (newCorrect.includes(oldText)) {
      newCorrect = newCorrect.filter(c => c !== oldText);
      newCorrect.push(value);
    }
    
    setFormData({ ...formData, options_json: newOptions, correct_answer_json: newCorrect });
  };

  const addOption = () => {
    setFormData({
      ...formData,
      options_json: [...formData.options_json, { text: `Option ${formData.options_json.length + 1}` }]
    });
  };

  const toggleCorrect = (text) => {
    let newCorrect = [...formData.correct_answer_json];
    if (newCorrect.includes(text)) {
      newCorrect = newCorrect.filter(c => c !== text);
    } else {
      newCorrect.push(text);
    }
    setFormData({ ...formData, correct_answer_json: newCorrect });
  };

  const isPublished = existingQuestion?.current_published_version_id && !existingQuestion?.current_draft_version_id;

  return (
    <Modal open={open} onClose={onClose} title={existingQuestion ? "Edit Question" : "Create Question"} size="large">
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        
        {isPublished && (
          <div style={{ padding: 16, background: "var(--surface-sunken)", borderLeft: "4px solid var(--color-warn)", borderRadius: 4 }}>
            This question is currently published. Saving changes will create a new draft version.
          </div>
        )}

        <div className="field">
          <label className="field__label">Question Text</label>
          <textarea 
            className="field__input" 
            rows={3}
            value={formData.question_text} 
            onChange={e => setFormData({ ...formData, question_text: e.target.value })} 
            placeholder="Enter your question here..." 
          />
        </div>

        <div className="grid-2">
          <div className="field">
            <label className="field__label">Question Type</label>
            <select 
              className="field__input"
              value={formData.question_type}
              onChange={e => setFormData({ ...formData, question_type: e.target.value })}
            >
              <option value="multiple_choice">Multiple Choice</option>
              <option value="true_false">True / False</option>
              <option value="short_answer">Short Answer</option>
            </select>
          </div>
          <div className="field">
            <label className="field__label">Points</label>
            <input 
              type="number"
              className="field__input"
              value={formData.points}
              onChange={e => setFormData({ ...formData, points: parseInt(e.target.value) || 0 })}
            />
          </div>
        </div>

        <div className="grid-2">
          <div className="field">
            <label className="field__label">Category</label>
            <select
              className="field__input"
              value={formData.category_id || ""}
              disabled={taxonomyLoading}
              onChange={(e) => setFormData({
                ...formData,
                category_id: e.target.value ? Number(e.target.value) : null,
              })}
            >
              <option value="">No category</option>
              {categoryOptions.map((category) => (
                <option key={category.id} value={category.id}>{category.label}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field__label">Tags</label>
            <div className="question-editor-tag-select">
              {taxonomyLoading ? (
                <div className="row-subtitle">Loading tags...</div>
              ) : tags.length === 0 ? (
                <div className="row-subtitle">No tags available</div>
              ) : (
                tags.map((tag) => {
                  const selected = formData.tag_ids.includes(tag.id);
                  return (
                    <button
                      key={tag.id}
                      type="button"
                      className={`question-editor-tag ${selected ? "is-selected" : ""}`}
                      onClick={() => setFormData({
                        ...formData,
                        tag_ids: toggleTagId(formData.tag_ids, tag.id),
                      })}
                    >
                      <Badge tone={selected ? "brand" : "neutral"}>{tag.name}</Badge>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {(formData.question_type === "multiple_choice" || formData.question_type === "true_false") && (
          <div className="soft-card">
            <div className="row-title" style={{ marginBottom: 12 }}>Answer Options</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {formData.options_json.map((opt, i) => (
                <div key={i} style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <input 
                    type={formData.question_type === "multiple_choice" ? "checkbox" : "radio"}
                    checked={formData.correct_answer_json.includes(opt.text)}
                    onChange={() => {
                      if (formData.question_type === "true_false") {
                        setFormData({ ...formData, correct_answer_json: [opt.text] });
                      } else {
                        toggleCorrect(opt.text);
                      }
                    }}
                  />
                  <input 
                    className="field__input"
                    value={opt.text}
                    onChange={(e) => updateOption(i, e.target.value)}
                    style={{ flex: 1 }}
                  />
                  {formData.options_json.length > 2 && (
                    <IconButton 
                      icon="trash" 
                      onClick={() => {
                        const newOptions = formData.options_json.filter((_, idx) => idx !== i);
                        setFormData({ ...formData, options_json: newOptions });
                      }} 
                    />
                  )}
                </div>
              ))}
            </div>
            {formData.question_type === "multiple_choice" && (
              <Button tone="ghost" size="small" onClick={addOption} style={{ marginTop: 12 }}>+ Add Option</Button>
            )}
          </div>
        )}

        <div className="split-actions" style={{ justifyContent: "space-between", marginTop: 16 }}>
          <div>
            {existingQuestion && existingQuestion.current_draft_version_id && (
              <Button tone="success" onClick={handlePublish} disabled={saving}>Publish Draft</Button>
            )}
          </div>
          <div className="split-actions">
            <Button tone="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
            <Button tone="primary" onClick={handleSave} disabled={saving}>
              {isPublished ? "Create New Draft" : "Save Draft"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
