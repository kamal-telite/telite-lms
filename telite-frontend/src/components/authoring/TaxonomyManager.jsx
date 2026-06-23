import React, { useMemo, useState } from "react";
import { Badge, Button, EmptyState, IconButton, Modal, useToast } from "../common/ui";
import {
  createQuestionCategory,
  createQuestionTag,
  deleteQuestionCategory,
  deleteQuestionTag,
  updateQuestionCategory,
  updateQuestionTag,
} from "../../api/questionBank";
import { getQuestionBankErrorMessage } from "../../api/questionBankErrors";

function flattenCategories(categories = [], depth = 0) {
  return categories.flatMap((category) => [
    { ...category, depth },
    ...flattenCategories(category.children || [], depth + 1),
  ]);
}

function CategoryRow({ category, depth = 0, onEdit, onDelete }) {
  if (depth > 2) {
    return null;
  }

  return (
    <>
      <div className="taxonomy-row" style={{ paddingLeft: depth * 18 }}>
        <div className="taxonomy-row__main">
          <div className="row-title">{category.name}</div>
          <div className="row-subtitle">ID {category.id}</div>
        </div>
        <div className="split-actions taxonomy-row__actions">
          <IconButton icon="pencil" label={`Edit ${category.name}`} onClick={() => onEdit(category)} />
          <IconButton icon="trash" label={`Delete ${category.name}`} onClick={() => onDelete(category)} />
        </div>
      </div>
      {(category.children || []).slice(0, depth < 2 ? undefined : 0).map((child) => (
        <CategoryRow key={child.id} category={child} depth={depth + 1} onEdit={onEdit} onDelete={onDelete} />
      ))}
    </>
  );
}

function TaxonomyModal({ open, title, item, parentOptions, onClose, onSubmit, type }) {
  const [name, setName] = useState(item?.name || "");
  const [parentId, setParentId] = useState(item?.parent_id || "");

  React.useEffect(() => {
    setName(item?.name || "");
    setParentId(item?.parent_id || "");
  }, [item, open]);

  const isCategory = type === "category";

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <div className="taxonomy-form">
        <div className="field">
          <label className="field__label" htmlFor={`${type}-name`}>Name</label>
          <input
            id={`${type}-name`}
            className="field__input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={isCategory ? "e.g. Physics" : "e.g. board-exam"}
          />
        </div>
        {isCategory ? (
          <div className="field">
            <label className="field__label" htmlFor="category-parent">Parent Category</label>
            <select
              id="category-parent"
              className="field__input"
              value={parentId}
              onChange={(event) => setParentId(event.target.value)}
            >
              <option value="">Top level</option>
              {parentOptions
                .filter((category) => category.id !== item?.id && category.depth < 2)
                .map((category) => (
                  <option key={category.id} value={category.id}>
                    {"--".repeat(category.depth)} {category.name}
                  </option>
                ))}
            </select>
          </div>
        ) : null}
        <div className="split-actions taxonomy-modal-actions">
          <Button tone="ghost" onClick={onClose}>Cancel</Button>
          <Button
            tone="primary"
            disabled={!name.trim()}
            onClick={() => onSubmit({
              name: name.trim(),
              parent_id: isCategory && parentId ? Number(parentId) : null,
            })}
          >
            Save
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default function TaxonomyManager({ categories, tags, loading, onRefresh }) {
  const { showToast } = useToast();
  const [modal, setModal] = useState({ open: false, type: "category", item: null });
  const [saving, setSaving] = useState(false);
  const flatCategories = useMemo(() => flattenCategories(categories), [categories]);

  const closeModal = () => setModal({ open: false, type: "category", item: null });

  const handleSave = async (payload) => {
    setSaving(true);
    try {
      if (modal.type === "category") {
        if (modal.item?.id) {
          await updateQuestionCategory(modal.item.id, payload);
        } else {
          await createQuestionCategory(payload);
        }
      } else if (modal.item?.id) {
        await updateQuestionTag(modal.item.id, { name: payload.name });
      } else {
        await createQuestionTag({ name: payload.name });
      }
      showToast(`${modal.type === "category" ? "Category" : "Tag"} saved`, "success");
      closeModal();
      await onRefresh();
    } catch (error) {
      showToast(getQuestionBankErrorMessage(error), "error");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteCategory = async (category) => {
    if (!window.confirm(`Delete category "${category.name}"?`)) return;
    try {
      await deleteQuestionCategory(category.id);
      showToast("Category deleted", "success");
      await onRefresh();
    } catch (error) {
      showToast(getQuestionBankErrorMessage(error), "error");
    }
  };

  const handleDeleteTag = async (tag) => {
    if (!window.confirm(`Delete tag "${tag.name}"?`)) return;
    try {
      await deleteQuestionTag(tag.id);
      showToast("Tag deleted", "success");
      await onRefresh();
    } catch (error) {
      showToast(getQuestionBankErrorMessage(error), "error");
    }
  };

  return (
    <div className="taxonomy-manager">
      <div className="taxonomy-section">
        <div className="taxonomy-section__header">
          <div>
            <h4>Categories</h4>
            <p>Display supports three visible levels for V1.</p>
          </div>
          <Button
            tone="ghost"
            icon="plus"
            onClick={() => setModal({ open: true, type: "category", item: null })}
            disabled={loading || saving}
          >
            Category
          </Button>
        </div>
        <div className="taxonomy-list">
          {loading ? (
            <div className="question-bank-loading">Loading categories...</div>
          ) : categories.length === 0 ? (
            <EmptyState title="No categories" body="Create a category to organize question banks." />
          ) : (
            categories.map((category) => (
              <CategoryRow
                key={category.id}
                category={category}
                onEdit={(item) => setModal({ open: true, type: "category", item })}
                onDelete={handleDeleteCategory}
              />
            ))
          )}
        </div>
      </div>

      <div className="taxonomy-section">
        <div className="taxonomy-section__header">
          <div>
            <h4>Tags</h4>
            <p>Normalized tag IDs are used by questions and filters.</p>
          </div>
          <Button
            tone="ghost"
            icon="plus"
            onClick={() => setModal({ open: true, type: "tag", item: null })}
            disabled={loading || saving}
          >
            Tag
          </Button>
        </div>
        <div className="taxonomy-tag-grid">
          {loading ? (
            <div className="question-bank-loading">Loading tags...</div>
          ) : tags.length === 0 ? (
            <EmptyState title="No tags" body="Create tags for reusable filtering later." />
          ) : (
            tags.map((tag) => (
              <div key={tag.id} className="taxonomy-tag-card">
                <div>
                  <Badge tone="neutral">{tag.name}</Badge>
                  <div className="row-subtitle">ID {tag.id}</div>
                </div>
                <div className="split-actions taxonomy-row__actions">
                  <IconButton icon="pencil" label={`Edit ${tag.name}`} onClick={() => setModal({ open: true, type: "tag", item: tag })} />
                  <IconButton icon="trash" label={`Delete ${tag.name}`} onClick={() => handleDeleteTag(tag)} />
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <TaxonomyModal
        open={modal.open}
        title={`${modal.item ? "Edit" : "Create"} ${modal.type === "category" ? "Category" : "Tag"}`}
        item={modal.item}
        type={modal.type}
        parentOptions={flatCategories}
        onClose={closeModal}
        onSubmit={handleSave}
      />
    </div>
  );
}
