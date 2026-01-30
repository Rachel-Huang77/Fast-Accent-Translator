import React, { useState, useEffect } from 'react';
import { batchGenerateKeys, listLicenseKeys, deleteLicenseKey } from '../../api/admin.js';
import styles from './AdminKeyManagement.module.css';
import MessageBox from "../../components/MessageBox";

export default function AdminKeyManagement() {
  const [generating, setGenerating] = useState(false);
  const [generatedKeys, setGeneratedKeys] = useState([]);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const [msgType, setMsgType] = useState('info');
  const [detailMsg, setDetailMsg] = useState('');
  const [detailMsgType, setDetailMsgType] = useState('info');


  // Form state - keyType and prefix are fixed, not shown to user
  const [formData, setFormData] = useState({
    count: 1,
    expireDays: '',
  });

  // License key list state
  const [keys, setKeys] = useState([]);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [keysError, setKeysError] = useState('');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalKeys, setTotalKeys] = useState(0);
  const pageSize = 20;

  // Filter state
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'used', 'unused'

  // ====== helper: render masked preview for list table ======
  const renderKeyPreview = (item) => {
    // 1) If backend directly provides preview / keyPreview (recommended)
    if (item.preview) return item.preview;
    if (item.keyPreview) return item.keyPreview;

    // 2) If backend provides prefix + last 4 characters
    if (item.keyPrefix && item.keySuffixLast4) {
      return `${item.keyPrefix}-****-****-${item.keySuffixLast4}`;
    }

    // 3) Fallback: use first few characters of id to prevent page crash
    if (item.id) {
      return `${item.id.slice(0, 16)}...`;
    }

    return 'N/A';
  };

  // Load license keys list
  const loadKeys = async (page = 1, status = 'all') => {
    setLoadingKeys(true);
    setKeysError('');

    const offset = (page - 1) * pageSize;

    // Build API params
    const params = {
      offset,
      limit: pageSize,
      key_type: 'paid', // Only show paid keys
    };

    // Add status filter if not 'all'
    if (status === 'used') {
      params.is_used = true;
    } else if (status === 'unused') {
      params.is_used = false;
    }

    const result = await listLicenseKeys(params);

    if (result.ok) {
      setKeys(result.data.items);
      setTotalKeys(result.data.total);
      setCurrentPage(page);
    } else {
      setKeysError(result.message || 'Failed to load license keys');
    }

    setLoadingKeys(false);
  };

  // Initial load - Load all keys on component mount
  useEffect(() => {
    loadKeys(1, 'all');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle form input
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value,
    });
  };

  // Generate keys
  const handleGenerate = async () => {
    setError('');

    // Validate input
    const count = parseInt(formData.count, 10);
    if (isNaN(count) || count < 1 || count > 200) {
      setError('Count must be between 1-200');
      return;
    }

    const expireDays = formData.expireDays ? parseInt(formData.expireDays, 10) : null;
    if (expireDays !== null && (isNaN(expireDays) || expireDays < 1 || expireDays > 3650)) {
      setError('Expiry days must be between 1-3650');
      return;
    }

    setGenerating(true);

    const result = await batchGenerateKeys({
      count,
      keyType: 'paid', // Fixed as paid
      expireDays,
      prefix: 'FAT', // Fixed prefix
    });

    setGenerating(false);

    if (result.ok) {
      setGeneratedKeys(result.data.keys);
      setError('');
      // Reload key list to show newly generated keys
      loadKeys(currentPage, statusFilter);
    } else {
      setError(result.message || 'Failed to generate keys');
    }
  };

    // Delete a single key
  const handleDeleteKey = async (keyId) => {
    setDetailMsg('');

    const result = await deleteLicenseKey(keyId);

    if (result.ok) {
      setDetailMsgType('success');
      setDetailMsg('License key deleted successfully.');
      // Reload current page, keep filter conditions
      loadKeys(currentPage, statusFilter);
    } else {
      setDetailMsgType('error');
      setDetailMsg(result.message || 'Failed to delete license key.');
    }
  };


  // Copy single key (for newly generated keys)
  const handleCopyKey = (key) => {
    navigator.clipboard
      .writeText(key)
      .then(() => {
        setMsgType('success');
        setMsg('Key copied to clipboard.');
      })
      .catch(() => {
        setMsgType('error');
        setMsg('Failed to copy, please copy manually.');
      });
  };

  // Copy all generated keys
  const handleCopyAllGenerated = () => {
    if (!generatedKeys.length) return;

    const text = generatedKeys.map((item, idx) => {
      const expires = item.expiresAt ? new Date(item.expiresAt).toLocaleString('en-US') : 'Never';
      return `${idx + 1}. ${item.key}  (Type: ${item.keyType}, Expires: ${expires})`;
    }).join('\n');

    navigator.clipboard
      .writeText(text)
      .then(() => {
        setMsgType('success');
        setMsg('All generated keys copied to clipboard.');
      })
      .catch(() => {
        setMsgType('error');
        setMsg('Failed to copy, please copy manually.');
      });
  };

  // Export generated keys to CSV
  const handleExportGeneratedCSV = () => {
    if (!generatedKeys.length) return;

    // CSV header
    const header = ['Index', 'Key', 'KeyType', 'ExpiresAt'];
    const rows = generatedKeys.map((item, idx) => [
      idx + 1,
      item.key,
      item.keyType,
      item.expiresAt || ''
    ]);

    const csvContent = [header, ...rows]
      .map(cols => cols.map(v => `"${(v ?? '').toString().replace(/"/g, '""')}"`).join(','))
      .join('\r\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const ts = new Date().toISOString().replace(/[:.]/g, '-');

    a.href = url;
    a.download = `generated_keys_${ts}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setMsgType('success');
    setMsg('CSV file exported for generated keys.');
  };

  // Clear results
  const handleClear = () => {
    setGeneratedKeys([]);
    setError('');
  };

  // Handle status filter change
  const handleStatusFilterChange = (status) => {
    setStatusFilter(status);
    loadKeys(1, status);
  };

  // Pagination
  const totalPages = Math.ceil(totalKeys / pageSize);
  const canPrevPage = currentPage > 1;
  const canNextPage = currentPage < totalPages;

  return (
    <div className={styles.container}>
      {/* Section 1: Batch Generate Keys */}
      <div className={styles.section}>
        <div className={styles.header}>
          <h2>Batch Generate License Keys</h2>
          <p className={styles.subtitle}>Generated keys are displayed only once, please save them immediately</p>
        </div>
        {msg && (
          <div style={{ marginBottom: '12px' }}>
            <MessageBox
              type={msgType}
              message={msg}
              onClose={() => setMsg('')}
            />
          </div>
        )}
        <div className={styles.form}>
          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label>Quantity *</label>
              <input
                type="number"
                name="count"
                value={formData.count}
                onChange={handleInputChange}
                min="1"
                max="200"
                className={styles.input}
                placeholder="1-200"
              />
              <span className={styles.hint}>Generate up to 200 keys</span>
            </div>

            <div className={styles.formGroup}>
              <label>Expiry Days</label>
              <input
                type="number"
                name="expireDays"
                value={formData.expireDays}
                onChange={handleInputChange}
                min="1"
                max="3650"
                className={styles.input}
                placeholder="Leave empty for permanent"
              />
              <span className={styles.hint}>Leave empty for permanent, max 3650 days (10 years)</span>
            </div>
          </div>

          <div className={styles.formActions}>
            <button
              className={styles.btnGenerate}
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating ? 'Generating...' : 'Generate Keys'}
            </button>
          </div>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        {generatedKeys.length > 0 && (
          <div className={styles.results}>
            <div className={styles.resultsHeader}>
              <h3>Successfully Generated {generatedKeys.length} Keys</h3>
              <div className={styles.resultsActions}>
                <button
                  className={styles.btnCopyAll}
                  onClick={handleCopyAllGenerated}
                >
                  Copy All
                </button>
                <button
                  className={styles.btnExport}
                  onClick={handleExportGeneratedCSV}
                >
                  Export CSV
                </button>
                <button className={styles.btnClear} onClick={handleClear}>
                  Clear
                </button>
              </div>
            </div>

            <div className={styles.warning}>
              ⚠️ Keys are displayed only once and cannot be viewed again after leaving this page! Please save them immediately.
            </div>

            <div className={styles.keysContainer}>
              {generatedKeys.map((item, index) => (
                <div key={item.id} className={styles.keyItem}>
                  <div className={styles.keyIndex}>{index + 1}</div>
                  <div className={styles.keyContent}>
                    <div className={styles.keyText}>{item.key}</div>
                    <div className={styles.keyMeta}>
                      {item.expiresAt ? (
                        <span className={styles.keyExpiry}>
                          Expires: {new Date(item.expiresAt).toLocaleString('en-US')}
                        </span>
                      ) : (
                        <span className={styles.keyPermanent}>Never expires</span>
                      )}
                    </div>
                  </div>
                  <button
                    className={styles.btnCopy}
                    onClick={() => handleCopyKey(item.key)}
                  >
                    Copy
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className={styles.info}>
          <h4>Usage Instructions</h4>
          <ul>
            <li>Each key can only be activated once and will be automatically invalidated after activation</li>
            <li>Key format: <code>FAT-XXXX-XXXX-XXXX-XXXX</code></li>
            <li>Save immediately after generation, the system does not store plaintext keys</li>
            <li>Regularly check key usage and clean up expired keys</li>
          </ul>
        </div>
      </div>

      {/* Section 2: License Key List */}
      <div className={styles.section} style={{ marginTop: '40px' }}>
        <div className={styles.header}>
          <h2>License Key List</h2>
          <p className={styles.subtitle}>View and manage all generated license keys</p>
        </div>
        {detailMsg && (
          <div style={{ marginBottom: '12px' }}>
            <MessageBox
              type={detailMsgType}
              message={detailMsg}
              onClose={() => setDetailMsg('')}
            />
          </div>
        )}
        {/* Filters */}
        <div className={styles.filters}>
          <div className={styles.filterGroup}>
            <label>Status:</label>
            <div className={styles.filterButtons}>
              <button
                className={`${styles.filterBtn} ${statusFilter === 'all' ? styles.filterBtnActive : ''}`}
                onClick={() => handleStatusFilterChange('all')}
              >
                All
              </button>
              <button
                className={`${styles.filterBtn} ${statusFilter === 'used' ? styles.filterBtnActive : ''}`}
                onClick={() => handleStatusFilterChange('used')}
              >
                Used
              </button>
              <button
                className={`${styles.filterBtn} ${statusFilter === 'unused' ? styles.filterBtnActive : ''}`}
                onClick={() => handleStatusFilterChange('unused')}
              >
                Unused
              </button>
            </div>
          </div>
        </div>

        {keysError && <div className={styles.error}>{keysError}</div>}

        {loadingKeys ? (
          <div className={styles.loading}>Loading...</div>
        ) : (
          <>
            <div className={styles.tableContainer}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Key</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Created At</th>
                    <th>Expires At</th>
                    <th>Actions</th>  
                  </tr>
                </thead>
                <tbody>
                  {keys.length === 0 ? (
                    <tr>
                      <td colSpan="5" className={styles.emptyMessage}>
                        No license keys found
                      </td>
                    </tr>
                  ) : (
                    keys.map((item) => (
                      <tr key={item.id}>
                        <td className={styles.keyCell}>
                          <span className={styles.keyPreview}>
                            {renderKeyPreview(item)}
                          </span>
                        </td>
                        <td>
                          <span className={styles.badgePaid}>Paid</span>
                        </td>
                        <td>
                          <span className={item.isUsed ? styles.badgeUsed : styles.badgeUnused}>
                            {item.isUsed ? 'Used' : 'Unused'}
                          </span>
                        </td>
                        <td>{item.createdAt ? new Date(item.createdAt).toLocaleString('en-US') : '-'}</td>
                        <td>
                          {item.expiresAt ? (
                            new Date(item.expiresAt).toLocaleString('en-US')
                          ) : (
                            <span className={styles.neverExpires}>Never expires</span>
                          )}
                        </td>
                        <td>
                          <button
                            className={styles.btnDelete}
                            onClick={() => handleDeleteKey(item.id)}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {keys.length > 0 && (
              <div className={styles.pagination}>
                <button
                  disabled={!canPrevPage}
                  onClick={() => loadKeys(currentPage - 1, statusFilter)}
                  className={styles.paginationBtn}
                >
                  Previous
                </button>
                <span className={styles.paginationInfo}>
                  Page {currentPage} / {totalPages} (Total: {totalKeys} keys)
                </span>
                <button
                  disabled={!canNextPage}
                  onClick={() => loadKeys(currentPage + 1, statusFilter)}
                  className={styles.paginationBtn}
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
