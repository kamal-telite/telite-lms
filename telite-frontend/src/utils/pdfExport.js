let pdfModulesPromise = null;

/** Lazy-load jsPDF + autotable only when the user exports a PDF. */
export function loadPdfModules() {
  if (!pdfModulesPromise) {
    pdfModulesPromise = Promise.all([
      import("jspdf"),
      import("jspdf-autotable"),
    ]).then(([jspdfMod, autotableMod]) => ({
      jsPDF: jspdfMod.default,
      autoTable: autotableMod.default,
    }));
  }
  return pdfModulesPromise;
}
