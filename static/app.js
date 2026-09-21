const form = document.getElementById('compress-form');
const input = document.getElementById('file-input');
const dropzone = document.getElementById('dropzone');
const selectedFile = document.getElementById('selected-file');
const selectedName = document.getElementById('selected-name');
const selectedSize = document.getElementById('selected-size');
const errorBox = document.getElementById('error-box');
const resultPanel = document.getElementById('result-panel');
const submitButton = document.getElementById('submit-button');
const downloadAgain = document.getElementById('download-again');
const estimateElements = {
  kuat: document.getElementById('estimate-kuat'),
  sedang: document.getElementById('estimate-sedang'),
  ringan: document.getElementById('estimate-ringan')
};
let file = null;
let downloadUrl = null;
let estimateController = null;
let selectionId = 0;

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
  resultPanel.hidden = true;
}

function resetEstimates(message = 'Pilih file untuk menghitung') {
  Object.values(estimateElements).forEach(element => {
    element.textContent = message;
    element.classList.remove('ready');
  });
}

async function loadEstimates(candidate, currentSelection) {
  if (estimateController) estimateController.abort();
  estimateController = new AbortController();
  resetEstimates('Menghitung ukuran…');
  const data = new FormData();
  data.append('file', candidate);
  try {
    const response = await fetch('/api/estimate', {
      method: 'POST', body: data, signal: estimateController.signal
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || 'Ukuran hasil tidak dapat dihitung.');
    if (currentSelection !== selectionId || file !== candidate) return;
    Object.entries(body.estimates).forEach(([level, estimate]) => {
      const percent = Number(estimate.saved_percent);
      const detail = estimate.used_original
        ? 'file asli dipakai'
        : percent > 0
          ? `hemat ${percent.toFixed(1)}%`
          : percent < 0
            ? `${Math.abs(percent).toFixed(1)}% lebih besar`
            : 'ukuran sama';
      estimateElements[level].textContent = `≈ ${formatSize(estimate.size)} · ${detail}`;
      estimateElements[level].classList.add('ready');
    });
  } catch (error) {
    if (error.name === 'AbortError' || currentSelection !== selectionId) return;
    resetEstimates('Tidak dapat dihitung');
    showError(error.message || 'Ukuran hasil tidak dapat dihitung.');
  }
}

function setFile(candidate) {
  errorBox.hidden = true;
  resultPanel.hidden = true;
  if (!candidate) return;
  if (candidate.size > 200 * 1024 * 1024) return showError('Ukuran file melebihi batas 200 MB.');
  if (!candidate.size) return showError('File kosong. Pilih file lain.');
  file = candidate;
  selectionId += 1;
  selectedName.textContent = candidate.name;
  selectedSize.textContent = formatSize(candidate.size);
  selectedFile.hidden = false;
  loadEstimates(candidate, selectionId);
}

dropzone.addEventListener('click', () => input.click());
dropzone.addEventListener('keydown', event => {
  if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); input.click(); }
});
input.addEventListener('change', () => setFile(input.files[0]));
document.getElementById('remove-file').addEventListener('click', () => {
  if (estimateController) estimateController.abort();
  selectionId += 1;
  file = null;
  input.value = '';
  selectedFile.hidden = true;
  resultPanel.hidden = true;
  errorBox.hidden = true;
  resetEstimates();
});
['dragenter', 'dragover'].forEach(name => dropzone.addEventListener(name, event => {
  event.preventDefault();
  dropzone.classList.add('drag-over');
}));
['dragleave', 'drop'].forEach(name => dropzone.addEventListener(name, event => {
  event.preventDefault();
  dropzone.classList.remove('drag-over');
}));
dropzone.addEventListener('drop', event => setFile(event.dataTransfer.files[0]));

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!file) return showError('Pilih file yang ingin dikompres.');
  errorBox.hidden = true;
  resultPanel.hidden = true;
  submitButton.disabled = true;
  submitButton.querySelector('.button-label').textContent = 'Sedang memproses…';
  const data = new FormData();
  data.append('file', file);
  data.append('level', form.elements.level.value);
  try {
    const response = await fetch('/api/compress', { method: 'POST', body: data });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.error || 'File gagal diproses. Coba lagi.');
    }
    const blob = await response.blob();
    const name = decodeURIComponent(response.headers.get('X-Result-Name') || 'hasil-kompres');
    const originalSize = Number(response.headers.get('X-Original-Size'));
    const resultSize = Number(response.headers.get('X-Result-Size'));
    const usedOriginal = response.headers.get('X-Used-Original') === 'true';
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = URL.createObjectURL(blob);
    downloadAgain.href = downloadUrl;
    downloadAgain.download = name;
    downloadAgain.click();
    const percent = originalSize > 0 ? Math.round((1 - resultSize / originalSize) * 100) : 0;
    document.getElementById('result-title').textContent = usedOriginal ? 'File asli siap diunduh' : 'File berhasil diproses';
    document.getElementById('result-detail').textContent = usedOriginal
      ? `Hasil kompresi lebih besar, jadi file asli (${formatSize(originalSize)}) dipakai.`
      : `${formatSize(originalSize)} → ${formatSize(resultSize)}${percent > 0 ? ` · ${percent}% lebih kecil` : ''}`;
    resultPanel.hidden = false;
  } catch (error) {
    showError(error.message || 'Terjadi kesalahan. Coba lagi.');
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector('.button-label').textContent = 'Kompres & Unduh';
  }
});

fetch('/api/status').then(response => response.json()).then(status => {
  const missing = [];
  if (!status.ghostscript) missing.push('Ghostscript belum ditemukan (diperlukan untuk PDF)');
  if (missing.length) {
    const note = document.getElementById('dependency-note');
    note.textContent = `Catatan: ${missing.join('; ')}. Lihat README untuk instalasi.`;
    note.hidden = false;
  }
}).catch(() => {});
