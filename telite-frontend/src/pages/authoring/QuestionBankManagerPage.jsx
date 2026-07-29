import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { DashboardShell } from "../../layouts/DashboardLayout";
import { useToast, Button, Panel, Badge, IconButton, EmptyState, Modal } from "../../components/common/ui";
import { getInitials, formatShortDate } from "../../utils/formatters";
import { useDebounce } from "../../hooks/useDebounce";
import { useDashboardStore } from "../../store/dashboardStore";
import {
  QUESTION_BANK_SORT_FIELDS,
  QUESTION_BANK_VERSION_STATES,
  createNewDraft,
  createQuestionBank,
  fetchQuestionCategories,
  fetchQuestionBanks,
  fetchQuestionTags,
  fetchQuestions,
  publishQuestion,
} from "../../api/questionBank";
import QuestionEditorModal from "../../components/authoring/QuestionEditorModal";
import QuestionImportWizard from "../../components/authoring/QuestionImportWizard";
import TaxonomyManager from "../../components/authoring/TaxonomyManager";
import VersionHistoryModal from "../../components/authoring/VersionHistoryModal";
import { flattenCategoryOptions } from "../../utils/questionTaxonomy";
import {
  DEFAULT_QUESTION_BANK_URL_QUERY,
  buildQuestionBankUrlParams,
  parseQuestionBankUrlState,
} from "../../utils/questionBankUrlState";

const PAGE_SIZE_OPTIONS = [25, 50, 100];
const DEFAULT_QUERY = DEFAULT_QUESTION_BANK_URL_QUERY;

function normalizeState(value) {
  return String(value || "").toUpperCase();
}

function getStateTone(value) {
  const normalized = normalizeState(value);
  if (normalized === "PUBLISHED") return "success";
  if (normalized === "DRAFT") return "warn";
  if (normalized === "ARCHIVED") return "danger";
  return "neutral";
}

function getRowActions(question) {
  const actions = ["history"];
  if (question.current_draft_version_id || normalizeState(question.version_state) === "DRAFT") {
    return ["edit", "publish", ...actions];
  }
  if (question.current_published_version_id && normalizeState(question.version_state) !== "ARCHIVED") {
    return ["createDraft", ...actions];
  }
  return actions;
}

function formatFieldLabel(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export default function QuestionBankManagerPage({ session, onLogout, embedded = false }) {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialUrlState = useMemo(() => parseQuestionBankUrlState(searchParams), []);
  const { showToast } = useToast();
  const { dashboard, fetchDashboardData } = useDashboardStore();
  const [banks, setBanks] = useState([]);
  const [activeBankId, setActiveBankId] = useState(initialUrlState.bankId);
  const [categories, setCategories] = useState([]);
  const [tags, setTags] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: DEFAULT_QUERY.pageSize,
    total: 0,
    total_pages: 0,
  });
  const [loadingBanks, setLoadingBanks] = useState(true);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [loadingTaxonomy, setLoadingTaxonomy] = useState(false);
  const [query, setQuery] = useState(initialUrlState.query);
  const [searchInput, setSearchInput] = useState(initialUrlState.query.search);
  const skipSearchDebounceRef = useRef(true);
  const syncingFromUrlRef = useRef(false);
  
  const [questionModal, setQuestionModal] = useState({ open: false, item: null });
  const [historyModal, setHistoryModal] = useState({ open: false, questionId: null });
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [bankModalOpen, setBankModalOpen] = useState(false);
  const [newBankName, setNewBankName] = useState("");

  const activeBank = useMemo(
    () => banks.find((bank) => String(bank.id) === String(activeBankId)),
    [banks, activeBankId]
  );
  const flatCategories = useMemo(() => flattenCategoryOptions(categories), [categories]);

  useEffect(() => {
    if (!dashboard) {
      fetchDashboardData(slug);
    }
  }, [slug, dashboard, fetchDashboardData]);

  const fetchBanks = async () => {
    setLoadingBanks(true);
    try {
      const data = await fetchQuestionBanks(slug);
      setBanks(data);
      if (data.length > 0 && !activeBankId) {
        setActiveBankId(data[0].id);
      } else if (data.length > 0 && activeBankId && !data.some((bank) => String(bank.id) === String(activeBankId))) {
        setActiveBankId(data[0].id);
      }
    } catch (err) {
      showToast("Failed to load question banks", "error");
    } finally {
      setLoadingBanks(false);
    }
  };

  useEffect(() => {
    fetchBanks();
  }, [slug]);

  useEffect(() => {
    const parsed = parseQuestionBankUrlState(searchParams);
    const nextBankId = parsed.bankId || activeBankId;
    const currentUrl = buildQuestionBankUrlParams({ bankId: activeBankId, query }).toString();
    const browserUrl = searchParams.toString();
    if (currentUrl === browserUrl) {
      return;
    }

    if (parsed.bankId && String(parsed.bankId) !== String(activeBankId || "")) {
      setActiveBankId(parsed.bankId);
    }
    syncingFromUrlRef.current = true;
    setQuery(parsed.query);
    skipSearchDebounceRef.current = true;
    setSearchInput(parsed.query.search);

    if (!parsed.bankId && nextBankId) {
      setSearchParams(buildQuestionBankUrlParams({ bankId: nextBankId, query: parsed.query }), { replace: true });
    }
  }, [searchParams]);

  const fetchTaxonomy = async () => {
    setLoadingTaxonomy(true);
    try {
      const [categoryData, tagData] = await Promise.all([
        fetchQuestionCategories({ tree: true }),
        fetchQuestionTags(),
      ]);
      setCategories(categoryData.items || []);
      setTags(tagData.items || []);
    } catch (err) {
      showToast(err.message || "Failed to load taxonomy", "error");
    } finally {
      setLoadingTaxonomy(false);
    }
  };

  useEffect(() => {
    fetchTaxonomy();
  }, []);

  const debouncedSearchInput = useDebounce(searchInput, 400);

  useEffect(() => {
    if (skipSearchDebounceRef.current) {
      skipSearchDebounceRef.current = false;
      return undefined;
    }

    setQuery((current) => ({
      ...current,
      search: debouncedSearchInput,
      page: 1,
    }));
  }, [debouncedSearchInput]);

  useEffect(() => {
    if (syncingFromUrlRef.current) {
      syncingFromUrlRef.current = false;
      return;
    }

    const nextParams = buildQuestionBankUrlParams({ bankId: activeBankId, query });
    if (nextParams.toString() !== searchParams.toString()) {
      setSearchParams(nextParams);
    }
  }, [activeBankId, query, searchParams, setSearchParams]);

  const fetchBankQuestions = async () => {
    if (!activeBankId) {
      setQuestions([]);
      setPagination({
        page: 1,
        page_size: query.pageSize,
        total: 0,
        total_pages: 0,
      });
      return;
    }

    setLoadingQuestions(true);
    try {
      const data = await fetchQuestions({
        bankId: activeBankId,
        search: query.search,
        categoryId: query.categoryId,
        tagId: query.tagId,
        questionType: query.questionType,
        versionState: query.versionState,
        page: query.page,
        pageSize: query.pageSize,
        sortBy: query.sortBy,
        sortOrder: query.sortOrder,
      });
      setQuestions(data.items || []);
      setPagination({
        page: data.page || query.page,
        page_size: data.page_size || query.pageSize,
        total: data.total || 0,
        total_pages: data.total_pages || 0,
      });
    } catch (err) {
      showToast(err.message || "Failed to load questions", "error");
    } finally {
      setLoadingQuestions(false);
    }
  };

  useEffect(() => {
    fetchBankQuestions();
  }, [activeBankId, query]);

  const updateQuery = (patch) => {
    setQuery((current) => ({
      ...current,
      ...patch,
      page: patch.page || 1,
    }));
  };

  const handleBankChange = (event) => {
    setActiveBankId(event.target.value ? Number(event.target.value) : null);
    setQuery((current) => ({ ...current, page: 1 }));
  };

  const handleCreateBank = async () => {
    if (!newBankName.trim()) return;
    try {
      const bank = await createQuestionBank(slug, newBankName);
      showToast("Bank created successfully", "success");
      setBankModalOpen(false);
      setNewBankName("");
      await fetchBanks();
      setActiveBankId(bank.id);
    } catch (err) {
      showToast("Failed to create bank", "error");
    }
  };

  const handlePublish = async (question) => {
    try {
      await publishQuestion(activeBankId, question.id);
      showToast("Question published", "success");
      fetchBankQuestions();
    } catch (err) {
      showToast(err.message || "Failed to publish question", "error");
    }
  };

  const handleCreateDraft = async (question) => {
    try {
      await createNewDraft(activeBankId, question.id);
      showToast("Draft created", "success");
      await fetchBankQuestions();
      setQuestionModal({ open: true, item: { ...question, current_draft_version_id: true } });
    } catch (err) {
      showToast(err.message || "Failed to create draft", "error");
    }
  };

  const renderActions = (question) => {
    const actions = getRowActions(question);
    return (
      <div className="split-actions question-bank-actions">
        {actions.includes("edit") ? (
          <IconButton icon="pencil" label="Edit draft" onClick={() => setQuestionModal({ open: true, item: question })} />
        ) : null}
        {actions.includes("publish") ? (
          <IconButton icon="check" label="Publish" onClick={() => handlePublish(question)} />
        ) : null}
        {actions.includes("createDraft") ? (
          <IconButton icon="copy" label="Create draft" onClick={() => handleCreateDraft(question)} />
        ) : null}
        <IconButton icon="history" label="Version history" onClick={() => setHistoryModal({ open: true, questionId: question.id })} />
      </div>
    );
  };

  const navGroups = [
    {
      label: "Authoring",
      items: [
        { id: "back", label: "Back to Dashboard", icon: "arrow-left" },
        { id: "banks", label: "Question Banks", icon: "database", badge: String(banks.length), badgeTone: "brand" }
      ],
    }
  ];

  const pageContent = (
    <>
      <div className="dashboard-stack">
        <Panel
          title="Question Bank"
        subtitle={activeBank ? activeBank.name : "Select a bank to manage questions"}
        action={
          <div className="split-actions question-bank-header-actions">
            <select
              className="field__input question-bank-select"
              value={activeBankId || ""}
              onChange={handleBankChange}
              disabled={loadingBanks || banks.length === 0}
            >
              {banks.length === 0 ? <option value="">No banks</option> : null}
              {banks.map((bank) => (
                <option key={bank.id} value={bank.id}>{bank.name}</option>
              ))}
            </select>
            <Button tone="ghost" icon="plus" onClick={() => setBankModalOpen(true)}>New Bank</Button>
            <Button tone="ghost" icon="upload" disabled={!activeBankId} onClick={() => setImportModalOpen(true)}>Import Questions</Button>
            <Button tone="primary" icon="plus" disabled={!activeBankId} onClick={() => setQuestionModal({ open: true, item: null })}>
              Create Question
            </Button>
          </div>
        }
      >
          {loadingBanks ? (
            <div className="question-bank-loading">Loading question banks...</div>
          ) : banks.length === 0 ? (
            <EmptyState
              title="No question banks"
              body="Create a question bank to start building reusable assessment content."
              action={<Button tone="primary" onClick={() => setBankModalOpen(true)}>Create Bank</Button>}
            />
          ) : (
            <div className="question-bank-manager">
              <div className="question-bank-filters" role="search">
                <div className="field question-bank-search">
                  <label className="field__label" htmlFor="question-bank-search">Search</label>
                  <input
                    id="question-bank-search"
                    className="field__input"
                    value={searchInput}
                    onChange={(event) => setSearchInput(event.target.value)}
                    placeholder="Search question text"
                  />
                </div>
                <div className="field">
                  <label className="field__label" htmlFor="question-bank-category">Category</label>
                  <select
                    id="question-bank-category"
                    className="field__input"
                    value={query.categoryId}
                    onChange={(event) => updateQuery({ categoryId: event.target.value })}
                    disabled={loadingTaxonomy}
                  >
                    <option value="">All categories</option>
                    {flatCategories.map((category) => (
                      <option key={category.id} value={category.id}>{category.label}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label className="field__label" htmlFor="question-bank-tag">Tag</label>
                  <select
                    id="question-bank-tag"
                    className="field__input"
                    value={query.tagId}
                    onChange={(event) => updateQuery({ tagId: event.target.value })}
                    disabled={loadingTaxonomy}
                  >
                    <option value="">All tags</option>
                    {tags.map((tag) => (
                      <option key={tag.id} value={tag.id}>{tag.name}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label className="field__label" htmlFor="question-bank-question-type">Question Type</label>
                  <select
                    id="question-bank-question-type"
                    className="field__input"
                    value={query.questionType}
                    onChange={(event) => updateQuery({ questionType: event.target.value })}
                  >
                    <option value="">All types</option>
                    <option value="multiple_choice">Multiple Choice</option>
                    <option value="true_false">True / False</option>
                    <option value="short_answer">Short Answer</option>
                  </select>
                </div>
                <div className="field">
                  <label className="field__label" htmlFor="question-bank-version-state">Version State</label>
                  <select
                    id="question-bank-version-state"
                    className="field__input"
                    value={query.versionState}
                    onChange={(event) => updateQuery({ versionState: event.target.value })}
                  >
                    <option value="">All states</option>
                    {QUESTION_BANK_VERSION_STATES.map((state) => (
                      <option key={state} value={state}>{formatFieldLabel(state)}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label className="field__label" htmlFor="question-bank-sort-by">Sort By</label>
                  <select
                    id="question-bank-sort-by"
                    className="field__input"
                    value={query.sortBy}
                    onChange={(event) => updateQuery({ sortBy: event.target.value })}
                  >
                    {QUESTION_BANK_SORT_FIELDS.map((field) => (
                      <option key={field} value={field}>{formatFieldLabel(field)}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label className="field__label" htmlFor="question-bank-sort-order">Direction</label>
                  <select
                    id="question-bank-sort-order"
                    className="field__input"
                    value={query.sortOrder}
                    onChange={(event) => updateQuery({ sortOrder: event.target.value })}
                  >
                    <option value="desc">Descending</option>
                    <option value="asc">Ascending</option>
                  </select>
                </div>
              </div>

              <div className="table-wrap">
                <table className="question-bank-table">
                  <thead>
                    <tr>
                      <th>Question</th>
                      <th>Type</th>
                      <th>Category</th>
                      <th>Tags</th>
                      <th>Version</th>
                      <th>State</th>
                      <th>Updated</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loadingQuestions ? (
                      <tr>
                        <td colSpan="8" className="question-bank-empty-cell">Loading questions...</td>
                      </tr>
                    ) : questions.length === 0 ? (
                      <tr>
                        <td colSpan="8">
                          <EmptyState title="No questions found" body="Adjust the server-side filters or create a new question." />
                        </td>
                      </tr>
                    ) : (
                      questions.map(q => (
                        <tr key={q.id}>
                          <td className="question-bank-question-cell">
                            <div className="row-title">{q.question_text || "Untitled question"}</div>
                            <div className="row-subtitle">ID {q.id} · {q.points || 0} pts</div>
                          </td>
                          <td>{formatFieldLabel(q.question_type)}</td>
                          <td>{q.category_id ? `#${q.category_id}` : "--"}</td>
                          <td>
                            <div className="question-bank-tag-list">
                              {(q.tag_ids || []).length === 0 ? "--" : q.tag_ids.map((tagId) => (
                                <Badge key={tagId} tone="neutral">#{tagId}</Badge>
                              ))}
                            </div>
                          </td>
                          <td>{q.version_number || "--"}</td>
                          <td><Badge tone={getStateTone(q.version_state || q.status)}>{formatFieldLabel(q.version_state || q.status || "Unknown")}</Badge></td>
                          <td>{formatShortDate(q.updated_at || q.created_at)}</td>
                          <td>{renderActions(q)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <div className="question-bank-pagination">
                <div className="row-subtitle">
                  {pagination.total === 0
                    ? "No questions"
                    : `Showing page ${pagination.page} of ${Math.max(pagination.total_pages, 1)} · ${pagination.total} total`}
                </div>
                <div className="split-actions">
                  <select
                    className="field__input question-bank-page-size"
                    value={query.pageSize}
                    onChange={(event) => updateQuery({ pageSize: Number(event.target.value) })}
                  >
                    {PAGE_SIZE_OPTIONS.map((size) => (
                      <option key={size} value={size}>{size} / page</option>
                    ))}
                  </select>
                  <Button
                    tone="ghost"
                    icon="chevronLeft"
                    disabled={query.page <= 1 || loadingQuestions}
                    onClick={() => updateQuery({ page: Math.max(1, query.page - 1) })}
                  >
                    Previous
                  </Button>
                  <Button
                    tone="ghost"
                    icon="chevronRight"
                    disabled={query.page >= Math.max(pagination.total_pages, 1) || loadingQuestions}
                    onClick={() => updateQuery({ page: query.page + 1 })}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </div>
          )}
        </Panel>

        <Panel
          title="Taxonomy Management"
          subtitle="Create, edit, and protect reusable categories and tags"
        >
          <TaxonomyManager
            categories={categories}
            tags={tags}
            loading={loadingTaxonomy}
            onRefresh={fetchTaxonomy}
          />
        </Panel>
      </div>

      <QuestionEditorModal 
        open={questionModal.open}
        onClose={() => setQuestionModal({ open: false, item: null })}
        bankId={activeBankId}
        existingQuestion={questionModal.item}
        onSaved={() => fetchBankQuestions()}
      />

      <VersionHistoryModal
        open={historyModal.open}
        onClose={() => setHistoryModal({ open: false, questionId: null })}
        bankId={activeBankId}
        questionId={historyModal.questionId}
        categories={flatCategories}
        tags={tags}
      />

      <QuestionImportWizard
        open={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        categories={flatCategories}
        tags={tags}
        loadingTaxonomy={loadingTaxonomy}
      />

      <Modal open={bankModalOpen} onClose={() => setBankModalOpen(false)} title="Create Question Bank">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="field">
            <label className="field__label">Bank Name</label>
            <input 
              className="field__input" 
              value={newBankName} 
              onChange={e => setNewBankName(e.target.value)} 
              placeholder="e.g. Midterm 1 Questions" 
            />
          </div>
          <div className="split-actions" style={{ justifyContent: "flex-end", marginTop: 16 }}>
            <Button tone="ghost" onClick={() => setBankModalOpen(false)}>Cancel</Button>
            <Button tone="primary" onClick={handleCreateBank} disabled={!newBankName.trim()}>Create</Button>
          </div>
        </div>
      </Modal>
    </>
  );

  if (embedded) {
    return pageContent;
  }

  return (
    <DashboardShell
      variant={slug}
      brandMark={{ label: (dashboard?.category?.name || "LMS").substring(0, 3).toUpperCase(), background: dashboard?.category?.accent_color || "#2563EB" }}
      brandTitle="Telite LMS"
      brandSubtitle={`${dashboard?.category?.name || slug} · Authoring`}
      navGroups={navGroups}
      activeNav="banks"
      onNavClick={(item) => {
        if (item.id === "back") {
          navigate(`/categories/${slug}/admin`);
        }
      }}
      profile={{
        initials: getInitials(session?.user?.name || "Admin User"),
        gradient: ["#2563EB", "#059669"],
        name: session?.user?.name || "Admin User",
        roleLabel: "category-admin",
      }}
      onLogout={onLogout}
      title="Question Bank Manager"
      subtitle="Manage reusable questions and assessments"
    >
      {pageContent}
    </DashboardShell>
  );
}
