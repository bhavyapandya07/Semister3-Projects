/**
 * ownsCourse needs a DB lookup per request (that's the whole point of
 * relationship-based auth), but re-fetching the same course document on
 * every single marks-entry request is wasteful for a faculty member
 * hammering one course. Cache the (courseId -> facultyId) pair briefly.
 *
 * Invalidation contract: any write that can change Course.faculty MUST
 * call invalidate(courseId) in the same request. That is the only place
 * staleness can be introduced, so it's the only place we guard.
 */
const TTL_MS = 60 * 1000;
const cache = new Map(); // courseId -> { facultyId, department, expiresAt }

function get(courseId) {
  const hit = cache.get(courseId);
  if (!hit) return null;
  if (Date.now() > hit.expiresAt) {
    cache.delete(courseId);
    return null;
  }
  return hit;
}

function set(courseId, { facultyId, department }) {
  cache.set(courseId, { facultyId, department, expiresAt: Date.now() + TTL_MS });
}

function invalidate(courseId) {
  cache.delete(String(courseId));
}

module.exports = { get, set, invalidate };
