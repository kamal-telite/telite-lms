import { SectionTitle } from "../../layouts/DashboardLayout";
import { IconButton, Button, Badge } from "../../components/common/ui";
import { formatPercent, titleize } from "../../utils/formatters";

export default function CategoriesSection({ 
  dashboard, 
  setCategoryModal, 
  setCategoryDeleteId, 
  categoryDeleteId, 
  handleDeleteCategory, 
  navigate,
  showToast 
}) {
  return (
    <section id="section-categories">
      <SectionTitle label="Learning Categories" />
      <div className="grid-3">
        {dashboard.categories.map((category) => (
          <article className="category-card" key={category.id}>
            <span className="category-card__bar" style={{ background: category.accent_color }} />
            <div className="category-card__actions">
              <IconButton
                label="Edit category"
                icon="pencil"
                onClick={() => setCategoryModal({ open: true, item: category })}
              />
              <IconButton
                label="Delete category"
                icon="trash"
                onClick={() => setCategoryDeleteId((value) => (value === category.id ? null : category.id))}
              />
            </div>
            <div className="category-card__name">{category.name}</div>
            <div className="category-card__meta">
              {category.slug} · {category.total_courses} courses ·{" "}
              {`${category.courses_count || 0} courses`}
            </div>
            <div className="stat-pair">
              <div className="stat-pair__card">
                <span>Learners</span>
                <strong style={{ color: category.accent_color }}>{category.total_learners}</strong>
              </div>
              <div className="stat-pair__card">
                <span>Avg PAL</span>
                <strong style={{ color: category.accent_color }}>
                  {formatPercent(category.avg_pal)}
                </strong>
              </div>
            </div>
            <div className="category-card__footer">
              <Badge tone={category.status === "active" ? "success" : "warn"}>
                {category.status === "active" ? "Active" : titleize(category.status)}
              </Badge>
              <button
                className="panel-link"
                type="button"
                onClick={() => {
                  showToast(`Opening ${category.name} dashboard...`, "info");
                  navigate(`/categories/${category.slug}/admin`);
                }}
              >
                View dashboard →
              </button>
            </div>
            {categoryDeleteId === category.id ? (
              <div className="inline-confirm">
                <span>Archive this category?</span>
                <div className="split-actions">
                  <Button tone="danger" onClick={() => handleDeleteCategory(category.id)}>
                    Confirm delete
                  </Button>
                  <Button tone="ghost" onClick={() => setCategoryDeleteId(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
