import React, { useEffect, useMemo, useState } from "react";
import { Modal, Button, useToast, Badge, EmptyState } from "../common/ui";
import {
  QUESTION_BANK_SORT_FIELDS,
  fetchQuestionBanks,
  fetchQuestionCategories,
  fetchQuestionTags,
  fetchQuestions,
} from "../../api/questionBank";
import { getQuestionBankErrorMessage } from "../../api/questionBankErrors";
import { flattenCategoryOptions } from "../../utils/questionTaxonomy";
import { buildBankReferenceItems } from "../../utils/questionBankReferences";

const DEFAULT_QUERY = {
  search: "",
  categoryId: "",
  tagId: "",
  questionType: "",
  versionState: "PUBLISHED",
  page: 1,
  pageSize: 25,
  sortBy: "updated_at",
  sortOrder: "desc",
};

function formatFieldLabel(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function QuestionBankPicker({ open, onClose, onImport, slug }) {
  const { showToast } = useToast();
  const [banks, setBanks] = useState([]);
  const [activeBankId, setActiveBankId] = useState(null);
  const [categories, setCategories] = useState([]);
  const [tags, setTags] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, total: 0, total_pages: 0 });
  const [selectedQuestions, setSelectedQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [searchInput, setSearchInput] = useState("");

  const flatCategories = useMemo(() => flattenCategoryOptions(categories), [categories]);
  const categoryById = useMemo(() => new Map(flatCategories.map((category) => [category.id, category])), [flatCategories]);
  const tagById = useMemo(() => new Map(tags.map((tag) => [tag.id, tag])), [tags]);

  useEffect(() => {
    if (!open) return;

    setSelectedQuestions([]);
    setQuery(DEFAULT_QUERY);
    setSearchInput("");
    Promise.all([
      fetchQuestionBanks(slug),
      fetchQuestionCategories({ tree: true }),
      fetchQuestionTags(),
    ])
      .then(([bankData, categoryData, tagData]) => {
        setBanks(bankData);
        setActiveBankId(bankData[0]?.id || null);
        setCategories(categoryData.items || []);
        setTags(tagData.items || []);
      })
      .catch((error) => showToast(getQuestionBankErrorMessage(error, "Failed to load Question Bank data"), "error"));
  }, [open, slug, showToast]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery((current) => ({ ...current, search: searchInput, page: 1 }));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    setQuery((current) => ({ ...current, page: 1, versionState: "PUBLISHED" }));
    setSelectedQuestions([]);
  }, [activeBankId]);

  useEffect(() => {
    if (!open || !activeBankId) {
      setQuestions([]);
      return;
    }

    let cancelled = false;
    setLoading(true);
    fetchQuestions({
      bankId: activeBankId,
      search: query.search,
      categoryId: query.categoryId,
      tagId: query.tagId,
      questionType: query.questionType,
      versionState: "PUBLISHED",
      page: query.page,
      pageSize: query.pageSize,
      sortBy: query.sortBy,
      sortOrder: query.sortOrder,
    })
      .then((data) => {
        if (cancelled) return;
        setQuestions(data.items || []);
        setPagination({
          page: data.page || query.page,
          total: data.total || 0,
          total_pages: data.total_pages || 0,
        });
      })
      .catch((error) => {
        if (!cancelled) {
          showToast(getQuestionBankErrorMessage(error, "Failed to load questions"), "error");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, activeBankId, query, showToast]);

  const updateQuery = (patch) => {
    setQuery((current) => ({
      ...current,
      ...patch,
      versionState: "PUBLISHED",
      page: patch.page || 1,
    }));
  };

  const isSelected = (question) => selectedQuestions.some((selected) => selected.id === question.id);

  const toggleSelection = (question) => {
    if (isSelected(question)) {
      setSelectedQuestions((current) => current.filter((selected) => selected.id !== question.id));
      return;
    }
    setSelectedQuestions((current) => [...current, question]);
  };

  const handleImport = () => {
    const references = buildBankReferenceItems(selectedQuestions);
    onImport(references);
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="Import from Question Bank" width={1120}>
      <div className="question-picker">
        <aside className="question-picker-banks">
          <div className="row-title">Question Banks</div>
          {banks.length === 0 ? (
            <div className="row-subtitle">No banks available</div>
          ) : (
            banks.map((bank) => (
              <button
                key={bank.id}
                type="button"
                className={`question-picker-bank ${String(activeBankId) === String(bank.id) ? "is-active" : ""}`}
                onClick={() => setActiveBankId(bank.id)}
              >
                <span>{bank.name}</span>
              </button>
            ))
          )}
        </aside>

        <section className="question-picker-main">
          <div className="question-picker-toolbar">
            <div className="field question-bank-search">
              <label className="field__label" htmlFor="picker-search">Search</label>
              <input
                id="picker-search"
                className="field__input"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Search published questions"
              />
            </div>
            <div className="field">
              <label className="field__label" htmlFor="picker-category">Category</label>
              <select id="picker-category" className="field__input" value={query.categoryId} onChange={(event) => updateQuery({ categoryId: event.target.value })}>
                <option value="">All categories</option>
                {flatCategories.map((category) => (
                  <option key={category.id} value={category.id}>{category.label}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="picker-tag">Tag</label>
              <select id="picker-tag" className="field__input" value={query.tagId} onChange={(event) => updateQuery({ tagId: event.target.value })}>
                <option value="">All tags</option>
                {tags.map((tag) => (
                  <option key={tag.id} value={tag.id}>{tag.name}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="picker-type">Type</label>
              <select id="picker-type" className="field__input" value={query.questionType} onChange={(event) => updateQuery({ questionType: event.target.value })}>
                <option value="">All types</option>
                <option value="multiple_choice">Multiple Choice</option>
                <option value="true_false">True / False</option>
                <option value="short_answer">Short Answer</option>
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="picker-sort">Sort By</label>
              <select id="picker-sort" className="field__input" value={query.sortBy} onChange={(event) => updateQuery({ sortBy: event.target.value })}>
                {QUESTION_BANK_SORT_FIELDS.map((field) => (
                  <option key={field} value={field}>{formatFieldLabel(field)}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field__label" htmlFor="picker-order">Order</label>
              <select id="picker-order" className="field__input" value={query.sortOrder} onChange={(event) => updateQuery({ sortOrder: event.target.value })}>
                <option value="desc">Desc</option>
                <option value="asc">Asc</option>
              </select>
            </div>
          </div>

          <div className="question-picker-status">
            <Badge tone="success">Published only</Badge>
            {selectedQuestions.length > 0 ? <Badge tone="brand">{selectedQuestions.length} selected</Badge> : null}
          </div>

          <div className="table-wrap question-picker-results">
            {loading ? (
              <div className="question-bank-loading">Loading questions...</div>
            ) : questions.length === 0 ? (
              <EmptyState title="No published questions" body="Adjust filters or publish questions before importing." />
            ) : (
              <table className="question-bank-table">
                <thead>
                  <tr>
                    <th style={{ width: 44 }}>
                      <input
                        type="checkbox"
                        checked={questions.length > 0 && questions.every((question) => isSelected(question))}
                        onChange={(event) => setSelectedQuestions(event.target.checked ? questions : [])}
                      />
                    </th>
                    <th>Question</th>
                    <th>Category</th>
                    <th>Tags</th>
                    <th>Type</th>
                    <th>Version</th>
                    <th>State</th>
                  </tr>
                </thead>
                <tbody>
                  {questions.map((question) => (
                    <tr
                      key={`${question.id}-${question.active_version_id}`}
                      className={isSelected(question) ? "is-selected" : ""}
                      onClick={() => toggleSelection(question)}
                    >
                      <td>
                        <input
                          type="checkbox"
                          checked={isSelected(question)}
                          onChange={() => toggleSelection(question)}
                          onClick={(event) => event.stopPropagation()}
                        />
                      </td>
                      <td className="question-bank-question-cell">
                        <div className="row-title">{question.question_text || "Untitled question"}</div>
                        <div className="row-subtitle">ID {question.id}</div>
                      </td>
                      <td>{question.category_id ? categoryById.get(question.category_id)?.label || `#${question.category_id}` : "--"}</td>
                      <td>
                        <div className="question-bank-tag-list">
                          {(question.tag_ids || []).length === 0 ? "--" : question.tag_ids.map((tagId) => (
                            <Badge key={tagId} tone="neutral">{tagById.get(tagId)?.name || `#${tagId}`}</Badge>
                          ))}
                        </div>
                      </td>
                      <td>{formatFieldLabel(question.question_type)}</td>
                      <td>Version {question.version_number || "--"}</td>
                      <td><Badge tone="success">Published</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="question-bank-pagination">
            <div className="row-subtitle">
              {pagination.total === 0
                ? "No questions"
                : `Page ${pagination.page} of ${Math.max(pagination.total_pages, 1)} | ${pagination.total} total`}
            </div>
            <div className="split-actions">
              <Button tone="ghost" disabled={query.page <= 1 || loading} onClick={() => updateQuery({ page: Math.max(1, query.page - 1) })}>
                Previous
              </Button>
              <Button tone="ghost" disabled={query.page >= Math.max(pagination.total_pages, 1) || loading} onClick={() => updateQuery({ page: query.page + 1 })}>
                Next
              </Button>
              <Button tone="ghost" onClick={onClose}>Cancel</Button>
              <Button tone="primary" onClick={handleImport} disabled={selectedQuestions.length === 0}>
                Import Selected
              </Button>
            </div>
          </div>
        </section>
      </div>
    </Modal>
  );
}
