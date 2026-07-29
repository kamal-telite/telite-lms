import test from 'node:test';
import assert from 'node:assert/strict';
import { buildCategoryAdminNavGroups } from './constants.js';

test('category admin navigation omits the Verifications entry', () => {
  const navGroups = buildCategoryAdminNavGroups({
    kpis: { total_courses: 2, active_learners: 3, pending_enrollment: 1 },
    tasks: [],
  }, { stats: { pending: 4 } });

  const allItems = navGroups.flatMap((group) => group.items);
  assert.ok(!allItems.some((item) => item.id === 'verifications'));
  assert.ok(allItems.some((item) => item.id === 'assignment_verification'));
});
