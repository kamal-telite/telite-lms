import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { fetchSignupRoles, submitSignupRequest, getErrorMessage, fetchOrganizations } from "../../services/client";
import "./Signup.css";

/* ── Per-role field definitions ───────────────────────────────────────────── */
const ROLE_FIELDS = {
  Student: [
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
  Teacher: [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "College Email", type: "email", required: true },
    { name: "organization_name", label: "College Name", type: "select", required: true },
    { name: "program", label: "Program", type: "text", required: true },
    { name: "branch", label: "Branch", type: "text", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: true },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  "College Admin": [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Admin Email", type: "email", required: true },
    { name: "organization_name", label: "College Name", type: "select", required: true },
    { name: "program", label: "Program", type: "text", required: true },
    { name: "branch", label: "Branch", type: "text", required: true },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  "College Super Admin": [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Official Email", type: "email", required: true },
    { name: "organization_name", label: "College Name", type: "select", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: true },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  Intern: [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Company Email", type: "email", required: true, placeholder: "you@company.com" },
    { name: "organization_name", label: "Company Name", type: "select", required: true },
    { name: "id_number", label: "Intern ID", type: "text", required: true },
    { name: "branch", label: "Department / Team", type: "text", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: false },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  Employee: [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Company Email", type: "email", required: true },
    { name: "organization_name", label: "Company Name", type: "select", required: true },
    { name: "id_number", label: "Employee ID", type: "text", required: true },
    { name: "branch", label: "Department", type: "text", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: false },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  "Project Admin": [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Company Email", type: "email", required: true },
    { name: "organization_name", label: "Company Name", type: "select", required: true },
    { name: "id_number", label: "Employee ID", type: "text", required: true },
    { name: "branch", label: "Project / Division", type: "text", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: true },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
  "Company Admin": [
    { name: "full_name", label: "Full Name", type: "text", required: true },
    { name: "email", label: "Company Email", type: "email", required: true },
    { name: "organization_name", label: "Company Name", type: "select", required: true },
    { name: "phone", label: "Phone Number", type: "tel", required: true },
    { name: "password", label: "Password", type: "password", required: true },
    { name: "confirm_password", label: "Confirm Password", type: "password", required: true },
  ],
};

const ROLE_SUBS = {
  'Student': 'Enrolled student at the college',
  'Teacher': 'Faculty member',
  'College Admin': 'Administrative staff',
  'College Super Admin': 'Top-level college administrator',
  'Intern': 'Internship program participant',
  'Employee': 'Full-time or part-time employee',
  'Project Admin': 'Project-level administrator',
  'Company Admin': 'Top-level company administrator'
};

/* ── Minimal math-based CAPTCHA ──────────────────────────────────────────── */
function generateCaptcha() {
  const a = Math.floor(Math.random() * 15) + 1;
  const b = Math.floor(Math.random() * 15) + 1;
  return { question: `${a} + ${b} = ?`, answer: String(a + b) };
}

/* ── Main Signup page ────────────────────────────────────────────────────── */
export default function Signup() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
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

  const vantaRef = useRef(null);
  const cardRef = useRef(null);
  const cardWrapRef = useRef(null);
  const cursorRef = useRef(null);
  const trailRef = useRef(null);
  const typeTargetRef = useRef(null);

  const typingIntervalRef = useRef(null);

  // Typewriter effect
  const typewrite = useCallback((text, speed = 55) => {
    if (!typeTargetRef.current) return;
    if (typingIntervalRef.current) clearInterval(typingIntervalRef.current);
    typeTargetRef.current.textContent = "";
    let i = 0;
    typingIntervalRef.current = setInterval(() => {
      if (!typeTargetRef.current) {
        clearInterval(typingIntervalRef.current);
        return;
      }
      typeTargetRef.current.textContent += text[i++];
      if (i >= text.length) clearInterval(typingIntervalRef.current);
    }, speed);
  }, []);

  // Initial animations and Vanta setup
  useEffect(() => {
    document.body.classList.add("signup-active");

    let vantaEffect = null;
    let ctx = null;
    let typeTimeout = null;
    const gsap = window.gsap;

    if (window.VANTA && window.VANTA.NET) {
      vantaEffect = window.VANTA.NET({
        el: vantaRef.current,
        mouseControls: true,
        touchControls: true,
        gyroControls: false,
        minHeight: 200,
        minWidth: 200,
        scale: 1.0,
        color: 0x6040d0,
        backgroundColor: 0x050510,
        points: 8,
        maxDistance: 18,
        spacing: 15,
        showDots: false
      });
    }

    if (gsap) {
      ctx = gsap.context(() => {
        gsap.from(cardRef.current, { duration: 1, y: 60, opacity: 0, scale: 0.95, ease: 'expo.out', delay: 0.1 });
        gsap.from('.logo-row', { duration: 0.8, y: 20, opacity: 0, ease: 'power3.out', delay: 0.4 });
        gsap.from('.stepper', { duration: 0.8, y: 16, opacity: 0, ease: 'power3.out', delay: 0.55 });
        gsap.from('#step1', { duration: 0.7, y: 12, opacity: 0, ease: 'power3.out', delay: 0.65 });
      });
    }

    typeTimeout = setTimeout(() => typewrite("organization type"), 100);

    return () => {
      document.body.classList.remove("signup-active");
      if (vantaEffect) vantaEffect.destroy();
      if (ctx) ctx.revert();
      if (typeTimeout) clearTimeout(typeTimeout);
      if (typingIntervalRef.current) clearInterval(typingIntervalRef.current);
    };
  }, [typewrite]);

  // Global mouse handlers for cursor, card shine, and 3D tilt
  useEffect(() => {
    const gsap = window.gsap;

    const onMouseMove = (e) => {
      const mx = e.clientX;
      const my = e.clientY;

      if (cursorRef.current && trailRef.current) {
        cursorRef.current.style.left = mx + 'px';
        cursorRef.current.style.top = my + 'px';
        setTimeout(() => {
          if (trailRef.current) {
            trailRef.current.style.left = mx + 'px';
            trailRef.current.style.top = my + 'px';
          }
        }, 80);
      }

      if (cardRef.current && cardWrapRef.current) {
        // Card shine
        const r = cardRef.current.getBoundingClientRect();
        const px = ((mx - r.left) / r.width * 100).toFixed(1);
        const py = ((my - r.top) / r.height * 100).toFixed(1);
        cardRef.current.style.setProperty('--mx', px + '%');
        cardRef.current.style.setProperty('--my', py + '%');

        // 3D Tilt
        if (gsap) {
          const wr = cardWrapRef.current.getBoundingClientRect();
          const cx = wr.left + wr.width / 2;
          const cy = wr.top + wr.height / 2;
          const dx = (mx - cx) / wr.width;
          const dy = (my - cy) / wr.height;
          const tiltX = dy * -10;
          const tiltY = dx * 10;
          gsap.to(cardRef.current, { duration: 0.6, ease: 'power2.out', rotationX: tiltX, rotationY: tiltY, transformPerspective: 900 });
        }
      }
    };

    const onMouseLeave = () => {
      if (gsap && cardRef.current) {
        gsap.to(cardRef.current, { duration: 0.8, ease: 'elastic.out(1,0.4)', rotationX: 0, rotationY: 0 });
      }
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseleave', onMouseLeave);

    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseleave', onMouseLeave);
    };
  }, []);

  // Fetch Roles and Orgs when domainType changes
  useEffect(() => {
    if (!domainType) return;

    let cancelled = false;

    async function loadSignupData() {
      setLoadingSignupData(true);
      setRoleLoadError("");
      setOrganizationLoadError("");

      const [rolesResult, organizationsResult] = await Promise.allSettled([
        fetchSignupRoles(domainType),
        fetchOrganizations(domainType),
      ]);

      if (cancelled) return;

      if (rolesResult.status === "fulfilled") {
        setRoles(rolesResult.value.roles || []);
      } else {
        setRoles([]);
        setRoleLoadError(
          getErrorMessage(rolesResult.reason, "We couldn't load the available signup roles. Please try again.")
        );
      }

      if (organizationsResult.status === "fulfilled") {
        setOrganizations(Array.isArray(organizationsResult.value) ? organizationsResult.value : []);
      } else {
        setOrganizations([]);
        setOrganizationLoadError(
          getErrorMessage(organizationsResult.reason, "We couldn't load the organization list. Please try again.")
        );
      }

      setLoadingSignupData(false);
    }

    loadSignupData();

    return () => {
      cancelled = true;
    };
  }, [domainType, reloadToken]);

  // Transition to step wrapper
  const goStep = useCallback((n) => {
    setStep(n);
    if (window.gsap) {
      window.gsap.from('#step' + n, { duration: 0.35, y: 10, opacity: 0, ease: 'power2.out' });
    }
  }, []);

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
    
    // Animate role grid entrance
    if (window.gsap) {
      setTimeout(() => {
        window.gsap.from('#roles-grid > div', { duration: 0.3, y: 10, opacity: 0, stagger: 0.06, ease: 'power2.out' });
      }, 50);
    }
    setTimeout(() => goStep(2), 220);
  }

  function handleRoleSelect(role) {
    setSelectedRole(role);
    setFormData({});
    setErrors({});
    setCaptchaInput("");
    setCaptcha(generateCaptcha());
    goStep(3);

    // Animate form fields entrance
    if (window.gsap) {
      setTimeout(() => {
        window.gsap.from('#form-fields > label', { duration: 0.3, y: 8, opacity: 0, stagger: 0.05, ease: 'power2.out' });
      }, 50);
    }
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

  const validateEmailDomain = useCallback(
    (emailValue, orgNameValue) => {
      const email = (emailValue || "").trim().toLowerCase();
      const orgName = (orgNameValue || "").trim().toLowerCase();
      if (!email || !orgName) return null;

      const selectedOrg = organizations.find((org) => String(org.name || "").trim().toLowerCase() === orgName);
      const domainRaw = String(selectedOrg?.domain || "").trim().toLowerCase();
      const normalizedDomain = domainRaw.replace(/^@+/, "");

      if (!normalizedDomain) return null;

      return email.endsWith(`@${normalizedDomain}`)
        ? null
        : `Email domain must match the organization domain (@${normalizedDomain}).`;
    },
    [organizations]
  );

  function validate() {
    // If backend mapping isn't directly available, we fall back to local ROLE_FIELDS by display name.
    const roleKey = roles.find(r => r.value === selectedRole)?.label || selectedRole;
    const fields = ROLE_FIELDS[roleKey] || ROLE_FIELDS[selectedRole] || [];
    const nextErrors = {};

    for (const field of fields) {
      const value = (formData[field.name] || "").trim();
      if (field.required && !value) {
        nextErrors[field.name] = `${field.label} is required`;
      }
    }

    const email = (formData.email || "").trim();
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      nextErrors.email = "Enter a valid email address";
    }

    const orgDomainError = validateEmailDomain(formData.email, formData.organization_name);
    if (orgDomainError) {
      nextErrors.email = orgDomainError;
    }

    const password = formData.password || "";
    if (password && password.length < 6) {
      nextErrors.password = "Password must be at least 6 characters";
    }

    if (password && formData.confirm_password && password !== formData.confirm_password) {
      nextErrors.confirm_password = "Passwords do not match";
    }

    if (!captchaInput.trim()) {
      nextErrors.captcha = "Please solve the security check";
    } else if (captchaInput.trim() !== captcha.answer) {
      nextErrors.captcha = "Incorrect answer — please try again";
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit() {
    if (!validate()) {
      if (window.gsap && cardRef.current) {
        window.gsap.to(cardRef.current, { x: -8, duration: 0.06, repeat: 5, yoyo: true, ease: 'none', onComplete: () => window.gsap.set(cardRef.current, { x: 0 }) });
      }
      return;
    }

    setSubmitting(true);
    setSubmitError("");

    if (window.gsap && cardRef.current) {
      window.gsap.to(cardRef.current, { scale: 1.02, duration: 0.15, yoyo: true, repeat: 1, ease: 'power2.inOut' });
    }

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
      goStep(4);
    } catch (err) {
      setSubmitError(getErrorMessage(err, "Registration failed. Please try again."));
      setCaptcha(generateCaptcha());
      setCaptchaInput("");
      if (window.gsap && cardRef.current) {
        window.gsap.to(cardRef.current, { x: -8, duration: 0.06, repeat: 5, yoyo: true, ease: 'none', onComplete: () => window.gsap.set(cardRef.current, { x: 0 }) });
      }
    } finally {
      setSubmitting(false);
    }
  }

  const handleMouseEnter = () => {
    if (cursorRef.current) {
      cursorRef.current.style.transform = 'translate(-50%,-50%) scale(2.5)';
      cursorRef.current.style.background = 'rgba(139,124,248,.4)';
    }
  };
  const handleMouseLeave = () => {
    if (cursorRef.current) {
      cursorRef.current.style.transform = 'translate(-50%,-50%) scale(1)';
      cursorRef.current.style.background = 'var(--accent)';
    }
  };

  const handleMagneticMove = (e, targetRef) => {
    if (window.gsap && targetRef.current) {
      const r = targetRef.current.getBoundingClientRect();
      const dx = e.clientX - r.left - r.width / 2;
      const dy = e.clientY - r.top - r.height / 2;
      window.gsap.to(targetRef.current, { duration: 0.3, x: dx * 0.25, y: dy * 0.25, ease: 'power2.out' });
    }
  };

  const handleMagneticLeave = (targetRef) => {
    if (window.gsap && targetRef.current) {
      window.gsap.to(targetRef.current, { duration: 0.5, x: 0, y: 0, ease: 'elastic.out(1,0.4)' });
    }
  };

  // Refs for magnetic buttons
  const signinBtnRef = useRef(null);
  const submitBtnRef = useRef(null);

  const currentRoleLabel = roles.find((r) => r.value === selectedRole)?.label || selectedRole;
  const currentFields = ROLE_FIELDS[currentRoleLabel] || ROLE_FIELDS[selectedRole] || [];
  const needsOrganizationSelect = currentFields.some((field) => field.type === "select");
  const orgLabel = domainType === "college" ? "College" : "Company";

  return (
    <>
      <div id="vanta-bg" ref={vantaRef}></div>
      <div className="custom-cursor" id="cursor" ref={cursorRef}></div>
      <div className="custom-cursor-trail" id="cursor-trail" ref={trailRef}></div>

      <div className="signup-page-wrap" id="page">
        <div className="card-wrap" id="card-wrap" ref={cardWrapRef}>
          <div className="signup-card" id="main-card" ref={cardRef}>
            <div className="card-shine" id="card-shine"></div>

            {/* LOGO ROW */}
            <div className="logo-row">
              <div className="logo-wordmark">Telite LMS<span>New account registration</span></div>
              <div className="magnetic-wrap" style={{ marginLeft: "auto" }}>
                <button
                  className="sign-in-btn"
                  ref={signinBtnRef}
                  onClick={() => navigate("/login")}
                  onMouseEnter={handleMouseEnter}
                  onMouseLeave={(e) => { handleMouseLeave(); handleMagneticLeave(signinBtnRef); }}
                  onMouseMove={(e) => handleMagneticMove(e, signinBtnRef)}
                >
                  Sign in instead
                </button>
              </div>
            </div>

            {/* STEPPER */}
            {step < 4 && (
              <div className="stepper" id="stepper">
                <div className={`step ${step > 1 ? 'done' : 'active'}`}>
                  {step > 1 ? '' : <span>1</span>}
                </div>
                <div className="step-line"></div>
                <div className={`step ${step > 2 ? 'done' : step === 2 ? 'active' : ''}`}>
                  {step > 2 ? '' : <span>2</span>}
                </div>
                <div className="step-line"></div>
                <div className={`step ${step === 3 ? 'active' : ''}`}>
                  <span>3</span>
                </div>
              </div>
            )}

            {/* STEP 1: Org Type */}
            {step === 1 && (
              <div className="section active" id="step1">
                <div className="heading">Choose your <span className="type-target" ref={typeTargetRef}></span><span className="type-cursor"></span></div>
                <div className="sub">Select the type of organization you belong to</div>
                <div className="grid2">
                  <div className={`card-option ${domainType === 'college' ? 'selected' : ''}`}
                    onClick={() => handleDomainSelect('college')}
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleMouseLeave}
                  >
                    <div className="opt-title">College</div>
                    <div className="opt-sub">Student, Teacher, or College Admin</div>
                  </div>
                  <div className={`card-option ${domainType === 'company' ? 'selected' : ''}`}
                    onClick={() => handleDomainSelect('company')}
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleMouseLeave}
                  >
                    <div className="opt-title">Company</div>
                    <div className="opt-sub">Intern, Employee, or Company Admin</div>
                  </div>
                </div>
              </div>
            )}

            {/* STEP 2: Role */}
            {step === 2 && (
              <div className="section active" id="step2">
                <div className="section-head">
                  <button className="back-arrow" onClick={() => { goStep(1); typewrite("organization type"); }} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>←</button>
                  <div className="heading">Select your role — {orgLabel}</div>
                </div>
                
                {loadingSignupData ? (
                  <div className="sub">Loading roles...</div>
                ) : roleLoadError ? (
                  <div className="form-alert">{roleLoadError}</div>
                ) : (
                  <div className="grid2" id="roles-grid">
                    {roles.map(r => (
                      <div key={r.value} className="card-option" onClick={() => handleRoleSelect(r.value)} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
                        <div className="opt-title">{r.label}</div>
                        <div className="opt-sub">{ROLE_SUBS[r.label] || "Registration for " + r.label}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* STEP 3: Form */}
            {step === 3 && (
              <div className="section active" id="step3">
                <div className="section-head">
                  <button className="back-arrow" onClick={() => goStep(2)} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>←</button>
                  <div>
                    <div className="heading">Register as {currentRoleLabel}</div>
                    <div className="breadcrumb">
                      <span className="bc-tag">{orgLabel}</span>
                      <span className="bc-arr">→</span>
                      <span className="bc-tag active">{currentRoleLabel}</span>
                    </div>
                  </div>
                </div>

                {submitError && <div className="form-alert">{submitError}</div>}
                {organizationLoadError && needsOrganizationSelect && (
                  <div className="form-alert">{organizationLoadError}</div>
                )}

                <div className="form-scroll">
                  <div className="field-grid" id="form-fields">
                    {currentFields.map((field) => (
                      <label key={field.name} className={`field ${['organization_name'].includes(field.name) ? 'full' : ''}`}>
                        <span>{field.label} {field.required && <span style={{color:'var(--accent)'}}>*</span>}</span>
                        {field.type === 'select' ? (
                          <select
                            className={errors[field.name] ? 'is-invalid' : ''}
                            value={formData[field.name] || ''}
                            onChange={(e) => handleFieldChange(field.name, e.target.value)}
                            onMouseEnter={handleMouseEnter}
                            onMouseLeave={handleMouseLeave}
                          >
                            <option value="" disabled>Select {field.label}</option>
                            {organizations.map(org => (
                              <option key={org.id} value={org.name}>{org.name}</option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type={field.type}
                            className={errors[field.name] ? 'is-invalid' : ''}
                            value={formData[field.name] || ''}
                            onChange={(e) => handleFieldChange(field.name, e.target.value)}
                            onBlur={field.name === "email" ? () => {
                              const message = validateEmailDomain(formData.email, formData.organization_name);
                              if (message) setErrors(prev => ({ ...prev, email: message }));
                            } : undefined}
                            placeholder={field.placeholder || ""}
                            onMouseEnter={handleMouseEnter}
                            onMouseLeave={handleMouseLeave}
                            autoComplete={field.type === "password" ? "new-password" : field.type === "email" ? "email" : "off"}
                          />
                        )}
                        {errors[field.name] && <div className="field-error-text">{errors[field.name]}</div>}
                      </label>
                    ))}
                    
                    <div className="captcha-row field full">
                      <div>
                        <label>Security Check <span style={{color:'var(--accent)'}}>*</span></label>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                          <div className="captcha-box">{captcha.question}</div>
                          <input
                            className={`captcha-input ${errors.captcha ? 'is-invalid' : ''}`}
                            type="number"
                            value={captchaInput}
                            onChange={(e) => setCaptchaInput(e.target.value)}
                            onMouseEnter={handleMouseEnter}
                            onMouseLeave={handleMouseLeave}
                            style={{ width: '90px' }}
                            placeholder="Answer"
                          />
                        </div>
                        {errors.captcha && <div className="field-error-text">{errors.captcha}</div>}
                      </div>
                    </div>
                  </div>
                  
                  <div className="actions">
                    <button className="btn-ghost" onClick={() => goStep(2)} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>Back</button>
                    <button className="btn-reload" onClick={() => setCaptcha(generateCaptcha())} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>Reload Captcha</button>
                    <div className="magnetic-wrap" style={{ marginLeft: "auto" }}>
                      <button
                        className="btn-primary"
                        ref={submitBtnRef}
                        disabled={submitting}
                        onClick={handleSubmit}
                        onMouseEnter={handleMouseEnter}
                        onMouseLeave={(e) => { handleMouseLeave(); handleMagneticLeave(submitBtnRef); }}
                        onMouseMove={(e) => handleMagneticMove(e, submitBtnRef)}
                      >
                        {submitting ? "Submitting..." : "Submit Registration"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* STEP 4: Success */}
            {step === 4 && (
              <div className="section active signup-success" id="step4">
                <h2>Registration Submitted!</h2>
                <p>Your registration has been submitted successfully and is now pending admin approval. You will receive an email once your account has been reviewed.</p>
                <div className="magnetic-wrap" style={{ marginTop: '16px' }}>
                  <button className="btn-primary" onClick={() => navigate("/login")} onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
                    Go to Login
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
