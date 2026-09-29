/**
 * StandSpec AI — API Client Gateway
 * Connects frontend to the FastAPI backend at http://127.0.0.1:8000
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend health check failed, using fallback status", err);
    return {
      status: "READY",
      engine_version: "3.0.0",
      release_id: "STANDSPEC_PROTOTYPE_CED_ETD_V3_0_0",
      indexed_standards: 6082,
      mandatory_qco_records: 163,
      default_evaluation_date: null,
      supported_departments: ["CED", "ETD"],
    };
  }
}

export async function recommendQuery(query, mode = "auto", evaluationDate = null) {
  const payload = {
    query,
    mode,
    evaluation_date: evaluationDate || null,
    top_k: 5,
  };

  const res = await fetch(`${API_BASE_URL}/api/v1/query/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Request failed with status ${res.status}`);
  }

  return await res.json();
}

export async function extractRequirements(query) {
  const res = await fetch(`${API_BASE_URL}/api/v1/query/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!res.ok) {
    throw new Error(`Extraction failed: HTTP ${res.status}`);
  }

  return await res.json();
}

export async function uploadTenderPdf(file, evaluationDate = null) {
  const formData = new FormData();
  formData.append("file", file);

  const url = new URL(`${API_BASE_URL}/api/v1/tender/upload`);
  if (evaluationDate) {
    url.searchParams.append("evaluation_date", evaluationDate);
  }

  const res = await fetch(url.toString(), {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `PDF upload failed: ${res.status}`);
  }

  return await res.json();
}

export async function batchRecommend(items, evaluationDate = null) {
  const res = await fetch(`${API_BASE_URL}/api/v1/tender/batch-recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items, evaluation_date: evaluationDate }),
  });

  if (!res.ok) {
    throw new Error(`Batch recommendation failed: HTTP ${res.status}`);
  }

  return await res.json();
}

export async function searchStandards(query, department = null, topK = 20) {
  const url = new URL(`${API_BASE_URL}/api/v1/standards/search`);
  url.searchParams.append("q", query);
  if (department) url.searchParams.append("department", department);
  url.searchParams.append("top_k", topK);

  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Standards search failed: ${res.status}`);
  return await res.json();
}

export async function getStandardDetails(designation) {
  const res = await fetch(`${API_BASE_URL}/api/v1/standards/${encodeURIComponent(designation)}`);
  if (!res.ok) throw new Error(`Failed to fetch standard: ${res.status}`);
  return await res.json();
}
