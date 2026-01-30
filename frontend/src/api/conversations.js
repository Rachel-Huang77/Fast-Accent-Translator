// src/api/conversations.js
// Conversation API - Uses unified API configuration

import { apiRequest } from '../config/api.js';

/**
 * listConversations
 * Returns: Array<{ id, title, createdAt }>
 */
export async function listConversations() {
  const result = await apiRequest(`/conversations?offset=0&limit=100`);

  if (!result.ok) {
    console.error('Failed to list conversations:', result.message);
    return [];
  }

  const items = (result.data.items || []).map(c => ({
    id: c.id,
    title: c.title || "",
    createdAt: c.startedAt ? Date.parse(c.startedAt) : Date.now(),
  }));

  return items;
}

/**
 * createConversation({ title? })
 * Returns: { id, title, createdAt, segments: [] }
 */
export async function createConversation({ title } = {}) {
  const result = await apiRequest(`/conversations`, {
    method: "POST",
    body: { title }
  });

  if (!result.ok) {
    throw new Error(result.message || 'Failed to create conversation');
  }

  const d = result.data;
  return {
    id: d.id,
    title: d.title || "",
    createdAt: d.createdAtMs ?? Date.now(),
    segments: [],
  };
}

/**
 * getConversation(id) / loadConversation(id)
 * Returns: { id, title, createdAt, segments: [...] }
 */
export async function getConversation(id) {
  const result = await apiRequest(`/conversations/${id}`);

  if (!result.ok) {
    throw new Error(result.message || 'Failed to get conversation');
  }

  const d = result.data;
  const conv = d.conversation || {};
  const segments = (d.transcripts || []).map(t => ({
    id: `s_${t.seq}`,
    start: t.startMs ?? Date.now(),
    end: t.endMs ?? Date.now(),
    transcript: t.text || "",
    audioUrl: t.audioUrl || null,
    speakerId: t.speakerId || null,  // ✅ Add speakerId field
  }));

  return {
    id: conv.id,
    title: conv.title || "",
    createdAt: conv.startedAt ? Date.parse(conv.startedAt) : Date.now(),
    segments,
  };
}

// Compatibility alias
export const loadConversation = getConversation;

/**
 * renameConversation(id, title)
 * Returns: true
 */
export async function renameConversation(id, title) {
  const result = await apiRequest(`/conversations/${id}`, {
    method: "PATCH",
    body: { title }
  });

  if (!result.ok) {
    throw new Error(result.message || 'Failed to rename conversation');
  }

  return true;
}

/**
 * deleteConversation(id)
 * Returns: true
 */
export async function deleteConversation(id) {
  const result = await apiRequest(`/conversations/${id}`, {
    method: "DELETE"
  });

  if (!result.ok) {
    throw new Error(result.message || 'Failed to delete conversation');
  }

  return true;
}

/**
 * appendSegment(id, seg)
 * seg: { start, end, transcript, audioUrl }
 * Returns: { id, start, end, transcript, audioUrl }
 */
export async function appendSegment(id, seg) {
  const result = await apiRequest(`/conversations/${id}/segments`, {
    method: "POST",
    body: {
      startMs: seg.start ?? null,
      endMs: seg.end ?? null,
      text: seg.transcript ?? "",
      audioUrl: seg.audioUrl ?? null,
    },
  });

  if (!result.ok) {
    throw new Error(result.message || 'Failed to append segment');
  }

  const d = result.data;
  return {
    id: d.id,
    start: d.startMs ?? Date.now(),
    end: d.endMs ?? Date.now(),
    transcript: d.text || "",
    audioUrl: d.audioUrl || null,
  };
}

/**
 * getComparisons(id)
 * Returns: { comparisons: [...], count: number }
 */
export async function getComparisons(id) {
  const result = await apiRequest(`/conversations/${id}/comparisons`);

  if (!result.ok) {
    throw new Error(result.message || 'Failed to get comparisons');
  }

  return result.data;
}
