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
let file = null;
let downloadUrl = null;

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

function setFile(candidate) {
  errorBox.hidden = true;
  resultPanel.hidden = true;
  if (!candidate) return;
  if (candidate.size > 200 * 1024 * 1024) return showError('Ukuran file melebihi batas 200 MB.');
  if (!candidate.size) return showError('File kosong. Pilih file lain.');
  file = candidate;
  selectedName.textContent = candidate.name;
  selectedSize.textContent = formatSize(candidate.size);
  selectedFile.hidden = false;
}

dropzone.addEventListener('click', () => input.click());
dropzone.addEventListener('keydown', event => {
  if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); input.click(); }
});
input.addEventListener('change', () => setFile(input.files[0]));
document.getElementById('remove-file').addEventListener('click', () => {
  file = null;
  input.value = '';
  selectedFile.hidden = true;
  resultPanel.hidden = true;
  errorBox.hidden = true;
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
  if (!status.ghostscript) missing.push('Ghostscript belum ditemukan (diperlukan untuk PDF dan file Office)');
  if (missing.length) {
    const note = document.getElementById('dependency-note');
    note.textContent = `Catatan: ${missing.join('; ')}. Lihat README untuk instalasi.`;
    note.hidden = false;
  }
}).catch(() => {});
