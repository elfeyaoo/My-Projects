/**
 * FBL Data Anonymization Tool - Frontend JavaScript
 * Handles file upload, preview, and anonymization
 */

(() => {
  const API_BASE = "http://localhost:5000"; // Same origin

  class FBLAnonymizer {
    constructor() {
      this.initElements();
      this.bindEvents();
      this.initUI();
    }

    initElements() {
      this.form = document.getElementById("anonymizeForm");
      this.fileInput = document.getElementById("fileInput");
      this.modeSelect = document.getElementById("modeSelect");
      this.percentageSlider = document.getElementById("percentageSlider");
      this.percentageInput = document.getElementById("percentageInput");
      this.percentageValue = document.getElementById("percentageValue");
      this.dpEnabled = document.getElementById("dpEnabled");
      this.epsilonContainer = document.getElementById("epsilonContainer");
      this.epsilonInput = document.getElementById("epsilonInput");
      this.submitBtn = document.getElementById("submitBtn");
      this.previewBtn = document.getElementById("previewBtn"); // ✅ New Preview Button

      this.statusContainer = document.getElementById("statusContainer");
      this.resultsSection = document.getElementById("resultsSection");
      this.rawPreview = document.getElementById("rawPreview");
      this.anonPreview = document.getElementById("anonPreview");
      this.downloadBtn = document.getElementById("downloadBtn");

      const loadingModalEl = document.getElementById("loadingModal");
      this.loadingModal = loadingModalEl
        ? new bootstrap.Modal(loadingModalEl)
        : null;
    }

    bindEvents() {
      if (this.form) {
        this.form.addEventListener("submit", (e) => this.onSubmit(e));
      }
      if (this.percentageSlider) {
        this.percentageSlider.addEventListener("input", (e) =>
          this.syncPercentage(e.target.value)
        );
      }
      if (this.percentageInput) {
        this.percentageInput.addEventListener("input", (e) =>
          this.syncPercentage(e.target.value)
        );
      }
      if (this.dpEnabled) {
        this.dpEnabled.addEventListener("change", (e) =>
          this.toggleEpsilon(e.target.checked)
        );
      }
      if (this.fileInput) {
        this.fileInput.addEventListener("change", (e) =>
          this.validateFile(e.target)
        );
      }
      if (this.previewBtn) {
        this.previewBtn.addEventListener("click", () => this.onPreview()); // ✅ Preview button click
      }
    }

    initUI() {
      this.syncPercentage(this.percentageSlider?.value || 50);
      this.toggleEpsilon(false);
      const container = document.querySelector(".container");
      if (container) container.classList.add("fade-in");
    }

    syncPercentage(value) {
      const v = Math.max(10, Math.min(100, parseInt(value || 50, 10)));
      if (this.percentageSlider) this.percentageSlider.value = v;
      if (this.percentageInput) this.percentageInput.value = v;
      if (this.percentageValue) {
        this.percentageValue.textContent = `${v}%`;
        this.percentageValue.className = "badge ms-2";
        if (v <= 30) this.percentageValue.classList.add("bg-success");
        else if (v <= 60) this.percentageValue.classList.add("bg-warning");
        else this.percentageValue.classList.add("bg-danger");
      }
    }

    toggleEpsilon(enabled) {
      if (!this.epsilonContainer) return;
      if (enabled) {
        this.epsilonContainer.classList.remove("d-none");
        if (this.epsilonInput) this.epsilonInput.required = true;
      } else {
        this.epsilonContainer.classList.add("d-none");
        if (this.epsilonInput) this.epsilonInput.required = false;
      }
    }

    validateFile(input) {
      const file = input.files && input.files[0];
      if (!file) return;
      const allowedExt = [".csv", ".xlsx"];
      const name = file.name.toLowerCase();
      const ext = name.slice(name.lastIndexOf("."));
      if (!allowedExt.includes(ext)) {
        this.alert("Please select a CSV or XLSX file.", "danger");
        input.value = "";
        return;
      }
      this.alert(`Selected: ${file.name}`, "info");
    }

    async onPreview() {
      if (!this.fileInput || !this.fileInput.files.length) {
        this.alert("Please select a file to preview.", "warning");
        return;
      }
      const formData = new FormData();
      formData.append("file", this.fileInput.files[0]);

      try {
        this.loadingModal?.show();
        const response = await fetch(`${API_BASE}/preview`, {
          method: "POST",
          body: formData,
        });
        this.loadingModal?.hide();

        if (!response.ok) {
          this.alert("Failed to preview data.", "danger");
          return;
        }
        const result = await response.json();
        this.rawPreview.innerHTML =
          result.raw_preview_html || "<p>No preview available.</p>";
        this.resultsSection.classList.remove("d-none");
        this.alert("Preview loaded.", "success");
      } catch (err) {
        this.loadingModal?.hide();
        this.alert("Error loading preview.", "danger");
        console.error(err);
      }
    }

    async onSubmit(e) {
      e.preventDefault();
      if (!this.fileInput || !this.fileInput.files.length) {
        this.alert("Please select a file to anonymize.", "danger");
        return;
      }

      const formData = new FormData();
      formData.append("file", this.fileInput.files[0]);
      formData.append("mode", this.modeSelect.value);
      formData.append("percentage", this.percentageInput.value);
      if (this.dpEnabled.checked) {
        formData.append("dp", "true");
        formData.append("epsilon", this.epsilonInput.value);
      }

      try {
        this.setLoading(true);
        const response = await fetch(`${API_BASE}/anonymize`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errText = await response.text();
          throw new Error(`Server error (${response.status}): ${errText}`);
        }

        const result = await response.json();
        if (result.error) {
          this.alert(result.error, "danger");
          return;
        }

        this.rawPreview.innerHTML =
          result.raw_preview_html || "<p>No raw preview available.</p>";
        this.anonPreview.innerHTML =
          result.anon_preview_html ||
          "<p>No anonymized preview available.</p>";
        this.downloadBtn.href = result.download_url || "#";
        this.downloadBtn.style.display = result.download_url
          ? "inline-block"
          : "none";

        this.resultsSection.classList.remove("d-none");
        this.alert("Anonymization complete!", "success");
      } catch (err) {
        this.alert("Error during anonymization.", "danger");
        console.error(err);
      } finally {
        this.setLoading(false);
      }
    }

    setLoading(loading) {
      if (this.submitBtn) this.submitBtn.disabled = loading;
      if (this.submitBtn) {
        this.submitBtn.innerHTML = loading
          ? '<i class="bi bi-hourglass-split me-2"></i>Processing...'
          : '<i class="bi bi-shield-check me-2"></i>Anonymize';
      }
      if (this.loadingModal) {
        loading ? this.loadingModal.show() : this.loadingModal.hide();
      }
    }

    alert(message, type = "info") {
      if (!this.statusContainer) return;
      this.statusContainer.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
          ${message}
          <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
      `;
    }
  }

  document.addEventListener("DOMContentLoaded", () => new FBLAnonymizer());
})();
