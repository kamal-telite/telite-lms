import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { fetchSignupRoles, submitSignupRequest, getErrorMessage, fetchOrganizations } from "../../services/client";

const DOMAIN_CARDS = [
  {
    value: "college",
    label: "College",
    emoji: "🎓",
    description: "Student, Teacher, or College Admin registration",
    gradient: "linear-gradient(135deg, #7c3aed, #2563eb)",
  },
  {
    value: "company",
    label: "Company",
    emoji: "🏢",
    description: "Intern, Employee, or Company Admin registration",
    gradient: "linear-gradient(135deg, #0891b2, #059669)",
  },
];

/* ── Per-role field definitions ───────────────────────────────────────────── */
const ROLE_FIELDS = {
  student: [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "College Email", type: "email", required: true, placeholder: "you@college.edu" },
    { name: "organization_name", label: "College Name", type: "select", required: true },
    { name: "id_number", label: "Enrollment Number", type: "text", required: true },
    { name: "program", label: "Program (B.Tech / M.Tech)", type: "text", required: true },
    { name: "branch", label: "Branch", type: "text", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: true },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  teacher: [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "College Email", type: "email", required: true },
    { name: "organization_name", label: "College Name", type: "select", required: true },
    { name: "program", label: "Program", type: "text", required: true },
    { name: "branch", label: "Branch", type: "text", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: true },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  admin: [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Admin Email", type: "email", required: true },
    { name: "organization_name", label: "College Name", type: "select", required: true },
    { name: "program", label: "Program", type: "text", required: true },
    { name: "branch", label: "Branch", type: "text", required: true },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  college_admin: [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Official Email", type: "email", required: true },
    { name: "organization_name", label: "College Name", type: "select", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: true },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  intern: [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Company Email", type: "email", required: true, placeholder: "you@company.com" },
    { name: "organization_name", label: "Company Name", type: "select", required: true },
    { name: "id_number", label: "Intern ID", type: "text", required: true },
    { name: "branch", label: "Department / Team", type: "text", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: false },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  employee: [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Company Email", type: "email", required: true },
    { name: "organization_name", label: "Company Name", type: "select", required: true },
    { name: "id_number", label: "Employee ID", type: "text", required: true },
    { name: "branch", label: "Department", type: "text", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: false },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  project_admin: [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Company Email", type: "email", required: true },
    { name: "organization_name", label: "Company Name", type: "select", required: true },
    { name: "id_number", label: "Employee ID", type: "text", required: true },
    { name: "branch", label: "Project / Division", type: "text", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: true },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  company_admin: [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Company Email", type: "email", required: true },
    { name: "organization_name", label: "Company Name", type: "select", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: true },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
};

/* ── Minimal math-based CAPTCHA ──────────────────────────────────────────── */
function generateCaptcha() {
  const a = Math.floor(Math.random() * 20) + 1;
  const b = Math.floor(Math.random() * 20) + 1;
  return { question: `${a} + ${b} = ?`, answer: String(a + b) };
}

/* ── Sub-components ──────────────────────────────────────────────────────── */

function StepIndicator({ current, total }) {
  return (
    <div className="signup-steps">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`signup-steps__dot ${i < current ? "is-done" : ""} ${i === current ? "is-active" : ""}`}
        >
          {i < current ? "✓" : i + 1}
        </div>
      ))}
    </div>
  );
}

function DomainStep({ onSelect }) {
  return (
    <div className="signup-domain-grid">
      {DOMAIN_CARDS.map((card) => (
        <button
          key={card.value}
          className="signup-domain-card"
          onClick={() => onSelect(card.value)}
          type="button"
        >
          <div className="signup-domain-card__icon" style={{ background: card.gradient }}>
            <span>{card.emoji}</span>
          </div>
          <div className="signup-domain-card__label">{card.label}</div>
          <div className="signup-domain-card__desc">{card.description}</div>
        </button>
      ))}
    </div>
  );
}

function RoleStep({ roles, onSelect, domainType }) {
  const gradient = domainType === "college"
    ? "linear-gradient(135deg, #7c3aed, #2563eb)"
    : "linear-gradient(135deg, #0891b2, #059669)";

  return (
    <div className="signup-role-grid">
      {roles.map((role) => (
        <button
          key={role.value}
          className="signup-role-card"
          onClick={() => onSelect(role.value)}
          type="button"
        >
          <div className="signup-role-card__indicator" style={{ background: gradient }} />
          <div className="signup-role-card__label">{role.label}</div>
          <div className="signup-role-card__desc">{role.description}</div>
        </button>
      ))}
    </div>
  );
}

function FormStep({
  fields,
  formData,
  onChange,
  errors,
  organizations,
  captcha,
  captchaInput,
  onCaptchaChange,
  onEmailBlur,
}) {
  return (
    <div className="signup-form-grid">
      {fields.map((field) => (
        <label key={field.name} className="field">
          <span className="field__label">
            {field.label}
            {field.required && <span style={{ color: "var(--red)" }}> *</span>}
          </span>
          {field.type === "select" ? (
            <select
              className={`field__input ${errors[field.name] ? "is-invalid" : ""}`}
              value={formData[field.name] || ""}
              onChange={(e) => onChange(field.name, e.target.value)}
              required={field.required}
            >
              <option value="" disabled>Select {field.label}</option>
              {organizations.map(org => (
                <option key={org.id} value={org.name}>{org.name}</option>
              ))}
            </select>
          ) : (
            <input
              className={`field__input ${errors[field.name] ? "is-invalid" : ""}`}
              type={field.type}
              value={formData[field.name] || ""}
              onChange={(e) => onChange(field.name, e.target.value)}
              onBlur={field.name === "email" ? onEmailBlur : undefined}
              placeholder={field.placeholder || ""}
              required={field.required}
              autoComplete={
                field.type === "password" ? "new-password"
                  : field.type === "email" ? "email" : "off"
              }
            />
          )}
          {errors[field.name] && <span className="field__error">{errors[field.name]}</span>}
        </label>
      ))}

      {/* CAPTCHA field — always shown at the end */}
      <label className="field signup-captcha-field">
        <span className="field__label">
          Security Check <span style={{ color: "var(--red)" }}> *</span>
        </span>
        <div className="signup-captcha-row">
          <div className="signup-captcha-question">{captcha.question}</div>
          <input
            className={`field__input signup-captcha-input ${errors.captcha ? "is-invalid" : ""}`}
            type="text"
            value={captchaInput}
            onChange={(e) => onCaptchaChange(e.target.value)}
            placeholder="Answer"
            autoComplete="off"
          />
        </div>
        {errors.captcha && <span className="field__error">{errors.captcha}</span>}
      </label>
    </div>
  );
}

function SuccessStep() {
  const navigate = useNavigate();
  return (
    <div className="signup-success">
      <div className="signup-success__icon">✓</div>
      <h2>Registration Submitted!</h2>
      <p>
        Your registration has been submitted successfully and is now pending admin approval.
        You will receive an email once your account has been reviewed.
      </p>
      <button className="btn btn--primary" onClick={() => navigate("/login")} type="button">
        Go to Login
      </button>
    </div>
  );
}

/* ── Main Signup page ────────────────────────────────────────────────────── */
export default function Signup() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [domainType, setDomainType] = useState("");
  const [roles, setRoles] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [selectedRole, setSelectedRole] = useState("");
  const [formData, setFormData] = useState({});
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [loadingSignupData, setLoadingSignupData] = useState(false);
  const [roleLoadError, setRoleLoadError] = useState("");
  const [organizationLoadError, setOrganizationLoadError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);
  const [captcha, setCaptcha] = useState(() => generateCaptcha());
  const [captchaInput, setCaptchaInput] = useState("");

  useEffect(() => {
    if (!domainType) {
      setRoles([]);
      setOrganizations([]);
      setLoadingSignupData(false);
      setRoleLoadError("");
      setOrganizationLoadError("");
      return;
    }

    let cancelled = false;

    async function loadSignupData() {
      setLoadingSignupData(true);
      setRoleLoadError("");
      setOrganizationLoadError("");

      const [rolesResult, organizationsResult] = await Promise.allSettled([
        fetchSignupRoles(domainType),
        fetchOrganizations(domainType),
      ]);

      if (cancelled) {
        return;
      }

      if (rolesResult.status === "fulfilled") {
        setRoles(rolesResult.value.roles || []);
      } else {
        setRoles([]);
        setRoleLoadError(
          getErrorMessage(
            rolesResult.reason,
            "We couldn't load the available signup roles. Please try again."
          )
        );
      }

      if (organizationsResult.status === "fulfilled") {
        setOrganizations(Array.isArray(organizationsResult.value) ? organizationsResult.value : []);
      } else {
        setOrganizations([]);
        setOrganizationLoadError(
          getErrorMessage(
            organizationsResult.reason,
            "We couldn't load the organization list. Please try again."
          )
        );
      }

      setLoadingSignupData(false);
    }

    loadSignupData();

    return () => {
      cancelled = true;
    };
  }, [domainType, reloadToken]);

  function handleDomainSelect(domain) {
    setDomainType(domain);
    setRoles([]);
    setOrganizations([]);
    setSelectedRole("");
    setFormData({});
    setErrors({});
    setRoleLoadError("");
    setOrganizationLoadError("");
    setCaptchaInput("");
    setCaptcha(generateCaptcha());
    setStep(1);
  }

  function handleRoleSelect(role) {
    setSelectedRole(role);
    setFormData({});
    setErrors({});
    setCaptchaInput("");
    setCaptcha(generateCaptcha());
    setStep(2);
  }

  function handleFieldChange(name, value) {
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
    if (submitError) setSubmitError("");
  }

  const handleCaptchaChange = useCallback((value) => {
    setCaptchaInput(value);
    if (errors.captcha) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next.captcha;
        return next;
      });
    }
  }, [errors.captcha]);

  const validateEmailDomain = useCallback(
    (emailValue, orgNameValue) => {
      const email = (emailValue || "").trim().toLowerCase();
      const orgName = (orgNameValue || "").trim().toLowerCase();
      if (!email || !orgName) {
        return null;
      }

      const selectedOrg = organizations.find((org) => String(org.name || "").trim().toLowerCase() === orgName);
      const domainRaw = String(selectedOrg?.domain || "").trim().toLowerCase();
      const normalizedDomain = domainRaw.replace(/^@+/, "");

      if (!normalizedDomain) {
        return null;
      }

      return email.endsWith(`@${normalizedDomain}`)
        ? null
        : `Email domain must match the organization domain (@${normalizedDomain}).`;
    },
    [organizations]
  );

  function validate() {
    const fields = ROLE_FIELDS[selectedRole] || [];
    const nextErrors = {};

    for (const field of fields) {
      const value = (formData[field.name] || "").trim();
      if (field.required && !value) {
        nextErrors[field.name] = `${field.label} is required`;
      }
    }

    // Email validation
    const email = (formData.email || "").trim();
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      nextErrors.email = "Enter a valid email address";
    }

    // Email domain must match selected organization domain (when org selected)
    const orgDomainError = validateEmailDomain(formData.email, formData.organization_name);
    if (orgDomainError) {
      nextErrors.email = orgDomainError;
    }

    // Password validation
    const password = formData.password || "";
    if (password && password.length < 6) {
      nextErrors.password = "Password must be at least 6 characters";
    }

    // Password match
    if (password && formData.confirm_password && password !== formData.confirm_password) {
      nextErrors.confirm_password = "Passwords do not match";
    }

    // CAPTCHA validation
    if (!captchaInput.trim()) {
      nextErrors.captcha = "Please solve the security check";
    } else if (captchaInput.trim() !== captcha.answer) {
      nextErrors.captcha = "Incorrect answer — please try again";
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    setSubmitError("");

    try {
      const payload = {
        domain_type: domainType,
        role_name: selectedRole,
        email: formData.email,
        full_name: formData.full_name,
        password: formData.password,
        organization_name: formData.organization_name || "",
        phone: formData.phone || "",
        id_number: formData.id_number || "",
        program: formData.program || "",
        branch: formData.branch || "",
        captcha: captchaInput,
      };

      await submitSignupRequest(payload);
      setStep(3);
    } catch (err) {
      setSubmitError(getErrorMessage(err, "Registration failed. Please try again."));
      // Regenerate CAPTCHA on failure
      setCaptcha(generateCaptcha());
      setCaptchaInput("");
    } finally {
      setSubmitting(false);
    }
  }

  function goBack() {
    if (step === 1) {
      setDomainType("");
      setStep(0);
    } else if (step === 2) {
      setSelectedRole("");
      setStep(1);
    }
  }

  const currentFields = ROLE_FIELDS[selectedRole] || [];
  const needsOrganizationSelect = currentFields.some((field) => field.type === "select");
  const currentRoleLabel = roles.find((r) => r.value === selectedRole)?.label || selectedRole;
  const domainLabel = domainType === "college" ? "College" : "Company";

  function retrySignupData() {
    setReloadToken((value) => value + 1);
  }

  const stepTitles = [
    "Choose your organization type",
    `Select your role — ${domainLabel}`,
    `Register as ${currentRoleLabel}`,
    "Registration Complete",
  ];

  return (
    <div className="signup-page" data-theme="super">
      <div className="signup-page__glow signup-page__glow--1" />
      <div className="signup-page__glow signup-page__glow--2" />
      <div className="signup-page__glow signup-page__glow--3" />

      <div className="signup-shell">
        {/* Header */}
        <header className="signup-header">
          <div className="signup-header__brand" onClick={() => navigate("/login")}>
            <div className="signup-header__mark">TS</div>
            <div>
              <div className="signup-header__title">Telite Systems LMS</div>
              <div className="signup-header__sub">New account registration</div>
            </div>
          </div>
          <button className="btn" onClick={() => navigate("/login")} type="button">
            Sign in instead
          </button>
        </header>

        {/* Steps */}
        {step < 3 && <StepIndicator current={step} total={3} />}

        {/* Step title */}
        <div className="signup-step-title">
          {step > 0 && step < 3 && (
            <button className="signup-back-btn" onClick={goBack} type="button">
              ←
            </button>
          )}
          <h1>{stepTitles[step]}</h1>
        </div>

        {/* Content */}
        <div className="signup-content">
          {step === 0 && <DomainStep onSelect={handleDomainSelect} />}

          {step === 1 && (
            loadingSignupData ? (
              <div className="signup-state-panel">
                <h2>Loading roles...</h2>
                <p>Fetching the available signup roles for this organization type.</p>
              </div>
            ) : roleLoadError ? (
              <div className="signup-state-panel">
                <div className="form-alert form-alert--error">{roleLoadError}</div>
                <div className="signup-state-panel__actions">
                  <button className="btn" onClick={retrySignupData} type="button">
                    Retry
                  </button>
                </div>
              </div>
            ) : roles.length > 0 ? (
              <RoleStep roles={roles} onSelect={handleRoleSelect} domainType={domainType} />
            ) : (
              <div className="signup-state-panel">
                <h2>No roles available</h2>
                <p>We couldn't find any signup roles for this organization type yet.</p>
                <div className="signup-state-panel__actions">
                  <button className="btn" onClick={retrySignupData} type="button">
                    Try Again
                  </button>
                </div>
              </div>
            )
          )}

          {step === 2 && (
            <form className="signup-form-wrapper" onSubmit={handleSubmit}>
              {/* Breadcrumb */}
              <div className="signup-breadcrumb">
                <span className="signup-breadcrumb__chip" style={{
                  background: domainType === "college" ? "var(--violet-light)" : "var(--teal-light)",
                  color: domainType === "college" ? "var(--violet)" : "var(--teal)",
                  borderColor: domainType === "college" ? "var(--violet-mid)" : "var(--teal-mid)",
                }}>
                  {domainType === "college" ? "🎓" : "🏢"} {domainLabel}
                </span>
                <span className="signup-breadcrumb__arrow">→</span>
                <span className="signup-breadcrumb__chip" style={{
                  background: "var(--brand-light)",
                  color: "var(--brand)",
                  borderColor: "var(--brand-mid)",
                }}>
                  {currentRoleLabel}
                </span>
              </div>

              {submitError && (
                <div className="form-alert form-alert--error">{submitError}</div>
              )}

              {organizationLoadError && needsOrganizationSelect ? (
                <div className="form-alert form-alert--error signup-inline-alert">
                  {organizationLoadError}
                </div>
              ) : null}

              {!organizationLoadError && needsOrganizationSelect && organizations.length === 0 ? (
                <div className="form-alert signup-inline-alert">
                  Organization options are still loading. If the dropdown stays empty, reload the options.
                </div>
              ) : null}

              <FormStep
                fields={currentFields}
                formData={formData}
                onChange={handleFieldChange}
                errors={errors}
                organizations={organizations}
                captcha={captcha}
                captchaInput={captchaInput}
                onCaptchaChange={handleCaptchaChange}
                onEmailBlur={() => {
                  const message = validateEmailDomain(formData.email, formData.organization_name);
                  if (message) {
                    setErrors((prev) => ({ ...prev, email: message }));
                  }
                }}
              />

              <div className="signup-form-actions">
                <button className="btn" type="button" onClick={goBack}>
                  Back
                </button>
                <button className="btn" type="button" onClick={retrySignupData}>
                  Reload Options
                </button>
                <button
                  className="btn btn--primary"
                  type="submit"
                  disabled={submitting}
                >
                  {submitting ? "Submitting..." : "Submit Registration"}
                </button>
              </div>
            </form>
          )}

          {step === 3 && <SuccessStep />}
        </div>
      </div>
    </div>
  );
}
