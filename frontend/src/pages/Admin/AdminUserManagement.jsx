// frontend/src/pages/Admin/AdminUserManagement.jsx
// User Management Page

import React, { useState, useEffect } from "react";
import { listUsers, updateUser, deleteUser, resetUserPassword } from "../../api/admin.js";
import MessageBox from "../../components/MessageBox";
import styles from "./AdminUserManagement.module.css";
import { validatePasswordComplexity, validateEmailFormat } from "../../utils/validators";



export default function AdminUserManagement() {
  const [users, setUsers] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);

  // Global messages
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const pageSize = 20;

  // Edit modal state
  const [editingUser, setEditingUser] = useState(null);
  const [editForm, setEditForm] = useState({
    username: "",
    email: "",
  });

  // Delete confirmation modal
  const [deletingUser, setDeletingUser] = useState(null);

  // Reset password modal
  const [resetPasswordUser, setResetPasswordUser] = useState(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetLoading, setResetLoading] = useState(false);
  const [editMsg, setEditMsg] = useState({ type: "", text: "" });
  const [resetMsg, setResetMsg] = useState({ type: "", text: "" });

  // Load user list
  const loadUsers = async (page = 1, query = "") => {
    setLoading(true);
    setError("");

    const offset = (page - 1) * pageSize;
    const result = await listUsers({ q: query, offset, limit: pageSize });

    if (result.ok) {
      setUsers(result.data.items);
      setTotalUsers(result.data.total);
      setCurrentPage(page);
    } else {
      setError(result.message || "Failed to load user list.");
    }

    setLoading(false);
  };

  // Initial load - Load all users on component mount
  useEffect(() => {
    loadUsers(1, "");
  }, []);

  // Search handler
  const handleSearch = (e) => {
    const query = e.target.value;
    setSearchQuery(query);
    loadUsers(1, query);
  };

  // Open edit modal
  const openEditModal = (user) => {
    setEditingUser(user);
    setEditForm({
      username: user.username,
      email: user.email || "",
    });
    setError("");
    setSuccess("");
  };

  // Close edit modal
  const closeEditModal = () => {
    setEditingUser(null);
    setEditForm({ username: "", email: "" });
  };

  // Submit edit
  const handleEditSubmit = async () => {
  // Clear previous message
  setEditMsg({ type: "", text: "" });

  const username = editForm.username.trim();
  const email = (editForm.email || "").trim();

  // Username is required
  if (!username) {
    setEditMsg({
      type: "error",
      text: "Username cannot be empty.",
    });
    return;
  }

  // Email format validation (allow empty)
  if (email) {
    const emailErr = validateEmailFormat(email);
    if (emailErr) {
      setEditMsg({
        type: "error",
        text: emailErr,
      });
      return;
    }
  }

  const result = await updateUser(editingUser.id, {
    username,
    email: email || null,
  });

  if (result.ok) {
    setEditMsg({
      type: "success",
      text: "User information updated successfully.",
    });

    // Delay closing to let user see the message
    setTimeout(() => {
      closeEditModal();
      loadUsers(currentPage, searchQuery);
    }, 500);
  } else {
    setEditMsg({
      type: "error",
      text: result.message || "Update failed.",
    });
  }
};




  // Open delete confirmation
  const openDeleteConfirm = (user) => {
    setDeletingUser(user);
    setError("");
    setSuccess("");
  };

  // Close delete confirmation
  const closeDeleteConfirm = () => {
    setDeletingUser(null);
  };

  // Confirm delete
  const handleDeleteConfirm = async () => {
    setError("");
    setSuccess("");

    const result = await deleteUser(deletingUser.id);

    if (result.ok) {
      setSuccess("User deleted successfully.");
      closeDeleteConfirm();
      loadUsers(currentPage, searchQuery);
    } else {
      setError(result.message || "Delete failed.");
    }
  };

  // Open reset password modal
  const openResetPasswordModal = (user) => {
    setResetPasswordUser(user);
    setNewPassword("");
    setError("");
    setSuccess("");
  };

  // Close reset password modal
  const closeResetPasswordModal = () => {
    setResetPasswordUser(null);
    setNewPassword("");
    setResetLoading(false);
  };

  // Submit reset password
  const handleResetPasswordSubmit = async () => {
  setResetMsg({ type: "", text: "" });

  const pwd = newPassword;
  const err = validatePasswordComplexity(pwd);
  if (err) {
    setResetMsg({
      type: "error",
      text: err,
    });
    return;
  }

  const result = await resetUserPassword(resetPasswordUser.id, pwd);

  if (result.ok) {
    
    closeResetPasswordModal();
  } else {
    setResetMsg({
      type: "error",
      text: result.message || "Reset failed.",
    });
  }
};

  

  // Pagination handling
  const totalPages = Math.ceil(totalUsers / pageSize) || 1;
  const canPrevPage = currentPage > 1;
  const canNextPage = currentPage < totalPages;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2>User Management</h2>
        <div className={styles.searchBox}>
          <input
            type="text"
            placeholder="Search users (Username/Email)"
            value={searchQuery}
            onChange={handleSearch}
            className={styles.searchInput}
          />
        </div>
      </div>

      {/* Global message notifications */}
      <MessageBox
        type="error"
        message={error}
        onClose={() => setError("")}
      />
      <MessageBox
        type="success"
        message={success}
        onClose={() => setSuccess("")}
      />

      {loading ? (
        <div className={styles.loading}>Loading...</div>
      ) : (
        <>
          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Created At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className={styles.idCell}>{user.id.slice(0, 8)}...</td>
                    <td>{user.username}</td>
                    <td>{user.email || "-"}</td>
                    <td>
                      <span
                        className={
                          user.role === "admin"
                            ? styles.badgeAdmin
                            : styles.badgeUser
                        }
                      >
                        {user.role === "admin" ? "Admin" : "User"}
                      </span>
                    </td>
                    <td>
                      {new Date(user.created_at).toLocaleString("en-US")}
                    </td>
                    <td className={styles.actions}>
                      <button
                        className={styles.btnEdit}
                        onClick={() => openEditModal(user)}
                      >
                        Edit
                      </button>
                      <button
                        className={styles.btnReset}
                        onClick={() => openResetPasswordModal(user)}
                      >
                        Reset Password
                      </button>
                      <button
                        className={styles.btnDelete}
                        onClick={() => openDeleteConfirm(user)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan={6} className={styles.empty}>
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className={styles.pagination}>
            <button
              disabled={!canPrevPage}
              onClick={() => loadUsers(currentPage - 1, searchQuery)}
              className={styles.paginationBtn}
            >
              Previous
            </button>
            <span className={styles.paginationInfo}>
              Page {currentPage} / {totalPages} (Total {totalUsers})
            </span>
            <button
              disabled={!canNextPage}
              onClick={() => loadUsers(currentPage + 1, searchQuery)}
              className={styles.paginationBtn}
            >
              Next
            </button>
          </div>
        </>
      )}

      {/* Edit User Modal */}
      {editingUser && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h3>Edit User</h3>

            {/* Display format error / success message inside modal */}
            <MessageBox
              type={editMsg.type || "error"}
              message={editMsg.text}
              onClose={() => setEditMsg({ type: "", text: "" })}
            />

            <div className={styles.formGroup}>
              <label>Username</label>
              <input
                type="text"
                value={editForm.username}
                onChange={(e) =>
                  setEditForm({ ...editForm, username: e.target.value })
                }
                className={styles.input}
              />
            </div>
            <div className={styles.formGroup}>
              <label>Email</label>
              <input
                type="email"
                value={editForm.email}
                onChange={(e) =>
                  setEditForm({ ...editForm, email: e.target.value })
                }
                className={styles.input}
              />
            </div>
            <div className={styles.modalActions}>
              <button className={styles.btnSubmit} onClick={handleEditSubmit}>
                Submit
              </button>
              <button
                className={styles.btnCancel}
                onClick={() => {
                  setEditMsg({ type: "", text: "" });
                  closeEditModal();
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      

      {/* Delete Confirmation Modal */}
      {deletingUser && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h3>Confirm Delete</h3>
            <p>
              Are you sure you want to delete user{" "}
              <strong>{deletingUser.username}</strong>?
            </p >
            <p className={styles.warning}>This action cannot be undone!</p >
            <div className={styles.modalActions}>
              <button
                className={styles.btnDelete}
                onClick={handleDeleteConfirm}
              >
                Confirm Delete
              </button>
              <button className={styles.btnCancel} onClick={closeDeleteConfirm}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {/* Reset Password Modal */}
      {resetPasswordUser && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h3>Reset Password</h3>

            {/* Display complexity/error message inside modal */}
            <MessageBox
              type={resetMsg.type || "error"}
              message={resetMsg.text}
              onClose={() => setResetMsg({ type: "", text: "" })}
            />

            <p>
              Set new password for user{" "}
              <strong>{resetPasswordUser.username}</strong>
            </p>
            <div className={styles.formGroup}>
              <label>
                New Password (at least 8 chars & two of: upper/lower/number/special)
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className={styles.input}
                placeholder="Enter new password"
              />
            </div>
            <div className={styles.modalActions}>
              <button
                className={styles.btnSubmit}
                onClick={handleResetPasswordSubmit}
                disabled={resetLoading}
              >
                {resetLoading ? "Saving..." : "Confirm Reset"}
              </button>
              <button
                className={styles.btnCancel}
                onClick={() => {
                  setResetMsg({ type: "", text: "" });
                  closeResetPasswordModal();
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}


      
    </div>
  );
}
